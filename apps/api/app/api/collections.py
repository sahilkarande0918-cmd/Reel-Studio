"""AI clip collections: group a class's highlights into educational series by the topics of its lecture outline.

Grounded by construction: series titles are outline topics (derived from the transcript), episode titles are the
highlights' own titles, every episode carries its source timestamps, teaching steps and a transcript quote, and a topic
only becomes a series when the class actually has two or more highlights about it. No language model invents anything
here, so a series can never name a concept the recording does not contain.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.publishing import PublishBody
from app.api.publishing import schedule as schedule_post
from app.api.renders import RenderRequest, enqueue_highlight_render
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.db import service_client
from app.core.storage import recording_dir

router = APIRouter()


def _ts(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def build(highlights: list[dict], units: list[dict]) -> list[dict]:
    """Highlights (lecture order) + outline units → [{title, topic, description, episodes}] (pure, unit-tested)."""
    def topic_of(h: dict) -> tuple[str, list[str]]:
        over = [(min(h["end_s"], u["end_s"]) - max(h["start_s"], u["start_s"]), u) for u in units]
        inside = [u for o, u in over if o > 0]
        best = max(over, key=lambda x: x[0], default=(0, {}))[1]
        return (best.get("topic") or best.get("title") or "").strip(), [u["title"] for u in inside]

    eps = []
    for h in sorted(highlights, key=lambda h: h["start_s"]):
        topic, steps = topic_of(h)
        eps.append({"highlight_id": h["id"], "title": (h.get("title") or (steps[0] if steps else "Clip"))[:120],
                    "start_s": round(h["start_s"], 2), "end_s": round(h["end_s"], 2), "topic": topic, "steps": steps[:6],
                    "quote": (h.get("transcript_excerpt") or "")[:180]})
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for e in eps:
        if e["topic"]:
            by_topic[e["topic"]].append(e)
    out = []
    for topic, items in by_topic.items():
        if len(items) >= 2:
            out.append({"title": topic[:1].upper() + topic[1:120], "topic": topic, "episodes": items,
                        "description": f"{len(items)} clips from {_ts(items[0]['start_s'])} to {_ts(items[-1]['end_s'])} of the class, "
                                       f"in teaching order: " + "; ".join(e["title"] for e in items)[:400]})
    if len(eps) >= 2:  # the whole class as one ordered series
        topics = list(dict.fromkeys(e["topic"] for e in eps if e["topic"]))
        out.append({"title": "Full class series", "topic": "", "episodes": eps,
                    "description": f"{len(eps)} clips in class order" + (f", covering {', '.join(topics[:6])}" if topics else "")})
    return out


def _units(rec: dict) -> list[dict]:
    p = recording_dir(rec["organization_id"], rec["id"]) / "outline.json"
    return json.loads(p.read_text(encoding="utf-8")).get("units", []) if p.exists() else []


@router.post("/recordings/{rec_id}/collections")
def generate(rec_id: str, user: User = Depends(current_user)) -> list[dict]:
    rec = get_owned("source_recordings", rec_id, user, write=True)
    db = service_client()
    hs = db.table("highlight_candidates").select("id,start_s,end_s,title,transcript_excerpt,status").eq("recording_id", rec_id) \
        .neq("status", "rejected").execute().data
    units = _units(rec)
    if not hs:
        raise HTTPException(409, "Analyse the recording first: collections are built from its highlights")
    db.table("clip_collections").delete().eq("recording_id", rec_id).eq("edited", False).execute()
    rows = [{"organization_id": rec["organization_id"], "project_id": rec["project_id"], "recording_id": rec_id,
             "created_by": user.id, **c} for c in build(hs, units)]
    if rows:
        db.table("clip_collections").insert(rows).execute()
    return rows


class Patch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    order: list[str] | None = Field(default=None, max_length=100)  # highlight ids: reorder or drop episodes
    episode_titles: dict[str, str] = Field(default_factory=dict)


@router.patch("/collections/{cid}")
def edit(cid: str, body: Patch, user: User = Depends(current_user)) -> dict:
    c = get_owned("clip_collections", cid, user, write=True)
    eps = {e["highlight_id"]: e for e in c["episodes"]}
    if body.order is not None:
        if any(h not in eps for h in body.order):
            raise HTTPException(422, "An episode is not part of this collection")
        eps_list = [eps[h] for h in body.order]
    else:
        eps_list = c["episodes"]
    eps_list = [{**e, "title": body.episode_titles.get(e["highlight_id"], e["title"])[:120]} for e in eps_list]
    patch = {"episodes": eps_list, "edited": True}
    if body.title is not None:
        patch["title"] = body.title
    if body.description is not None:
        patch["description"] = body.description
    return service_client().table("clip_collections").update(patch).eq("id", cid).execute().data[0]


@router.post("/collections/{cid}/render", status_code=202)
def render_all(cid: str, body: RenderRequest, user: User = Depends(current_user)) -> dict:
    """Batch export: selects each episode's highlight and queues its render with one brand/style/caption setting."""
    c = get_owned("clip_collections", cid, user, write=True)
    db = service_client()
    out = []
    for e in c["episodes"]:
        rows = db.table("highlight_candidates").select("*").eq("id", e["highlight_id"]).limit(1).execute().data
        if not rows:
            continue
        h = rows[0]
        if h["status"] != "selected":
            db.table("highlight_candidates").update({"status": "selected"}).eq("id", h["id"]).execute()
            h["status"] = "selected"
        r = enqueue_highlight_render(h, body, user.id)
        e["render_id"] = r["render_id"]
        out.append({"highlight_id": h["id"], **r})
    db.table("clip_collections").update({"episodes": c["episodes"]}).eq("id", cid).execute()
    return {"renders": out}


class SeriesSchedule(BaseModel):
    account_id: UUID
    first_at: datetime  # timezone required (validated by PublishBody)
    every_days: int = Field(default=2, ge=1, le=14)
    hashtags: str = Field(default="", max_length=300)


@router.post("/collections/{cid}/schedule", status_code=202)
def schedule_series(cid: str, body: SeriesSchedule, user: User = Depends(current_user)) -> dict:
    """Queue the series as Instagram posts, one every N days, in episode order. Only finished episode exports are
    scheduled; the rest are listed as skipped. Posting runs through the normal queue (cancel any post before it goes)."""
    c = get_owned("clip_collections", cid, user, write=True)
    db = service_client()
    n, done, skipped = len(c["episodes"]), [], []
    for i, e in enumerate(c["episodes"]):
        r = db.table("render_jobs").select("id,status").eq("id", e.get("render_id") or "00000000-0000-0000-0000-000000000000").limit(1).execute().data
        if not r or r[0]["status"] != "ready":
            skipped.append({"highlight_id": e["highlight_id"], "reason": "export not finished"})
            continue
        caption = f"{c['title']} · Part {i + 1}/{n}: {e['title']}" + (f"\n\n{body.hashtags}" if body.hashtags else "")
        when = body.first_at + timedelta(days=body.every_days * len(done))
        res = schedule_post(PublishBody(render_id=r[0]["id"], account_id=body.account_id, caption=caption[:2200], scheduled_at=when), user)
        done.append({"highlight_id": e["highlight_id"], "scheduled_at": when.isoformat(), **res})
    return {"scheduled": done, "skipped": skipped}
