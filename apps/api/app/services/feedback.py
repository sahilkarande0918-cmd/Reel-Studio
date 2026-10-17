"""Performance feedback: what this workspace's own published reels (real Instagram metrics) say about
length, style and mode. Needs MIN_POSTS reels with reach before it concludes anything; the learned ideal
length is fed back into highlight scoring (`candidates.score` via `extras["ideal_s"]`)."""

import json
import logging
from collections import defaultdict
from statistics import mean, median

import httpx

from app.core.config import get_settings
from app.core.db import service_client

log = logging.getLogger(__name__)
MIN_POSTS = 3


def collect(org_id: str) -> list[dict]:
    """One row per reel published from Reel Studio that has Instagram reach in the latest insights refresh."""
    db = service_client()
    posts = (db.table("publish_jobs").select("id,render_id,platform_post_id,platform_url,caption,created_at")
             .eq("organization_id", org_id).eq("status", "published").execute().data)
    if not posts:
        return []
    media = {m["id"]: m for row in db.table("platform_metrics").select("media").eq("organization_id", org_id).execute().data
             for m in (row.get("media") or [])}
    renders = {r["id"]: r for r in db.table("render_jobs").select("id,duration_s,timeline,recording_id")
               .in_("id", [p["render_id"] for p in posts]).execute().data}
    rows = []
    for p in posts:
        m, r = media.get(p["platform_post_id"] or ""), renders.get(p["render_id"])
        ins = (m or {}).get("insights") or {}
        reach = ins.get("reach")
        if not r or not reach:
            continue
        interactions = ins.get("total_interactions")
        if interactions is None:
            interactions = sum(ins.get(k) or 0 for k in ("likes", "comments", "shares", "saved"))
        watch = ins.get("ig_reels_avg_watch_time")
        rows.append({
            "post_id": p["platform_post_id"], "permalink": p.get("platform_url"),
            "title": r["timeline"].get("title") or (p["caption"] or "")[:60],
            "duration_s": round(r["duration_s"] or 0, 1), "style": r["timeline"].get("stylePreset", "focus"),
            "mode": "recording" if r.get("recording_id") else "topic",
            "views": ins.get("views"), "reach": reach, "interactions": interactions,
            "engagement": round(interactions / reach, 4), "avg_watch_s": round(watch / 1000, 1) if watch else None,
        })
    return rows


def _bucket(d: float) -> str:
    return "under 35 s" if d < 35 else "35–50 s" if d <= 50 else "over 50 s"


def _groups(rows: list[dict], key) -> list[dict]:
    g = defaultdict(list)
    for r in rows:
        g[key(r)].append(r["engagement"])
    return sorted(({"group": k, "posts": len(v), "engagement": round(mean(v), 4)} for k, v in g.items()),
                  key=lambda x: -x["engagement"])


def learn(rows: list[dict]) -> dict:
    if len(rows) < MIN_POSTS:
        return {"enough": False, "posts": len(rows),
                "message": f"Feedback needs at least {MIN_POSTS} published reels with Instagram reach. "
                           f"{len(rows)} so far. Publish more and refresh analytics; nothing is guessed meanwhile."}
    ranked = sorted(rows, key=lambda r: -r["engagement"])
    top = ranked[: max(1, len(ranked) // 2)]
    ideal = round(min(60.0, max(30.0, median(r["duration_s"] for r in top))), 1)
    by_duration = _groups(rows, lambda r: _bucket(r["duration_s"]))
    by_style = _groups(rows, lambda r: r["style"])
    by_mode = _groups(rows, lambda r: r["mode"])
    findings = [f"Your most engaging reels average {ideal:.0f} s; new highlight suggestions now favour that length."]
    for name, groups in (("length", by_duration), ("style", by_style), ("type", by_mode)):
        if len(groups) > 1 and groups[0]["posts"] >= 2:
            findings.append(f"By {name}, “{groups[0]['group']}” reels engage best "
                            f"({groups[0]['engagement'] * 100:.1f}% of reached accounts interact, "
                            f"vs {groups[-1]['engagement'] * 100:.1f}% for “{groups[-1]['group']}”).")
    return {"enough": True, "posts": len(rows), "ideal_duration_s": ideal, "by_duration": by_duration,
            "by_style": by_style, "by_mode": by_mode, "top": ranked[:3], "findings": findings}


def explain(summary: dict) -> list[str] | None:
    """Plain-language advice from the local LLM, grounded only in the computed numbers (None if offline)."""
    s = get_settings()
    facts = {k: summary[k] for k in ("posts", "ideal_duration_s", "by_duration", "by_style", "by_mode", "top")}
    schema = {"type": "object", "properties": {"recommendations": {"type": "array", "items": {"type": "string"}}},
              "required": ["recommendations"]}
    try:
        r = httpx.post(f"{s.ollama_url}/api/chat", timeout=180, json={
            "model": s.ollama_model, "stream": False, "format": schema, "keep_alive": 0,
            "options": {"temperature": 0, "seed": 7},
            "messages": [{"role": "user", "content":
                "You advise a teacher who posts short educational reels. Using ONLY these measured results from "
                "their own Instagram reels, write 3 short, specific recommendations for their next reels "
                "(hook, length, style or topic). Do not invent numbers or facts not present.\n" + json.dumps(facts)}],
        })
        r.raise_for_status()
        recs = json.loads(r.json()["message"]["content"]).get("recommendations", [])
        return [str(x)[:300] for x in recs if str(x).strip()][:3] or None
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.warning("feedback explanation unavailable: %s", e)
        return None


def ideal_duration(org_id: str) -> float | None:
    rows = (service_client().table("performance_feedback").select("ideal_duration_s")
            .eq("organization_id", org_id).execute().data)
    return rows[0]["ideal_duration_s"] if rows else None
