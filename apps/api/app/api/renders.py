"""Render a selected highlight to a branded 9:16 MP4 and serve the result through signed URLs.

POST /highlights/{id}/render → builds + validates the canonical timeline now (bad input fails fast),
reuses an identical finished render (cache keyed by timeline hash) or queues a `render` job.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from app.core import signing
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.config import get_settings
from app.core.db import service_client, transcript_words
from app.core.storage import render_dir
from app.services.rendering import captions, compose, timeline

router = APIRouter()
FILES = {"video": "output_path", "thumb": "thumbnail_path"}


class RenderRequest(BaseModel):
    quality: Literal["draft", "looks", "delivery"] = "looks"
    # None → the organisation's default kit (if any); "none" → render without branding
    brand_kit_id: str | None = None
    style: Literal["focus", "energy", "story", "signature"] = "focus"


def _brand_kit(org_id: str, kit_id: str | None) -> dict | None:
    if kit_id == "none":
        return None
    if kit_id:
        try:
            uuid.UUID(kit_id)
        except ValueError as e:
            raise HTTPException(422, 'brand_kit_id must be a UUID or "none"') from e
    q = service_client().table("brand_kits").select("*").eq("organization_id", org_id)
    rows = (q.eq("id", kit_id) if kit_id else q.eq("is_default", True)).limit(1).execute().data
    if kit_id and not rows:
        raise HTTPException(404, "Brand kit not found")  # also hides other organisations' kits
    return rows[0] if rows else None


def _inputs(h: dict) -> tuple[dict, list[dict]]:
    """The highlight's recording and its latest transcript's words."""
    db = service_client()
    rec = db.table("source_recordings").select("*").eq("id", h["recording_id"]).single().execute().data
    tr_id = h.get("transcript_id") or (
        db.table("transcripts")
        .select("id")
        .eq("recording_id", rec["id"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or [{}]
    )[0].get("id")
    return rec, transcript_words(tr_id) if tr_id else []


@router.get("/highlights/{highlight_id}/preview")
def preview_highlight(
    highlight_id: str, brand_kit_id: str | None = None, user: User = Depends(current_user)
) -> dict:
    """Subtitle preview: the exact caption pages, zone and panel placement a render would use (same
    timeline builder and paginator), so the studio preview and the export stay in sync."""
    h = get_owned("highlight_candidates", highlight_id, user)
    rec, words = _inputs(h)
    kit = _brand_kit(h["organization_id"], brand_kit_id)
    doc = timeline.build(h, rec, words, "preview", kit=kit)
    item = next(i for t in doc["tracks"] for i in t["items"] if i["type"] == "caption")
    style = doc["captionStyle"]
    pages = compose.paginate(item["words"], style["maxCharsPerLine"], style["maxLines"], item["duration"])
    return {
        "pages": pages,  # clip-relative seconds
        "captionStyle": style,
        "colors": doc["brand"]["colors"],
        "fonts": doc["brand"]["fonts"],
        "panelCenter": compose.panel_center(style, doc["height"]),
        "brandKit": kit["name"] if kit else None,
    }


@router.post("/highlights/{highlight_id}/render", status_code=202)
def render_highlight(highlight_id: str, body: RenderRequest, user: User = Depends(current_user)) -> dict:
    h = get_owned("highlight_candidates", highlight_id, user, write=True)
    if h["status"] != "selected":
        raise HTTPException(409, "Select this highlight before rendering it")
    db = service_client()
    rec, words = _inputs(h)
    render_id = str(uuid.uuid4())
    kit = _brand_kit(h["organization_id"], body.brand_kit_id)
    logo = None
    if kit and kit.get("logo"):
        try:
            logo = timeline.logo_file(kit["logo"])
        except ValueError as e:
            raise HTTPException(422, f"Brand kit logo: {e}") from e
    doc = timeline.build(h, rec, words, render_id, body.quality, kit=kit, logo_src=logo[0] if logo else None)
    doc["stylePreset"] = body.style
    digest = timeline.timeline_hash(doc)

    previous = (
        db.table("render_jobs")
        .select("id, job_id, status, output_path")
        .eq("highlight_id", h["id"])
        .eq("timeline_hash", digest)
        .in_("status", ["queued", "rendering", "ready"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if previous:
        p = previous[0]
        if p["status"] != "ready" or (get_settings().data_dir / p["output_path"]).exists():
            return {"render_id": p["id"], "job_id": p["job_id"], "cached": p["status"] == "ready"}

    if logo:  # the snapshot's logo file lives with the render, so later kit edits never change it
        (render_dir(h["organization_id"], render_id) / logo[0]).write_bytes(logo[1])
    db.table("render_jobs").insert(
        {
            "id": render_id,
            "brand_kit_id": kit["id"] if kit else None,
            "organization_id": h["organization_id"],
            "project_id": h["project_id"],
            "recording_id": rec["id"],
            "highlight_id": h["id"],
            "created_by": user.id,
            "quality": body.quality,
            "timeline": doc,
            "timeline_hash": digest,
        }
    ).execute()
    job = (
        db.table("jobs")
        .insert(
            {
                "organization_id": h["organization_id"],
                "project_id": h["project_id"],
                "job_type": "render",
                "payload": {"render_id": render_id},
                "created_by": user.id,
                "current_stage": "queued",
            }
        )
        .execute()
        .data[0]
    )
    db.table("render_jobs").update({"job_id": job["id"]}).eq("id", render_id).execute()
    return {"render_id": render_id, "job_id": job["id"], "cached": False}


@router.get("/renders/{render_id}/urls")
def render_urls(render_id: str, user: User = Depends(current_user)) -> dict:
    r = get_owned("render_jobs", render_id, user)
    if r["status"] != "ready":
        raise HTTPException(409, "This render is not finished")
    out = {}
    for kind in FILES:
        q, exp = signing.query(f"render-{kind}", r["id"])
        out[kind] = f"/renders/{r['id']}/file/{kind}?{q}"
        out["expires_at"] = exp
    out["download"] = out["video"] + "&download=1"
    return out


@router.get("/renders/{render_id}/file/{kind}")
def render_file(
    render_id: str, kind: Literal["video", "thumb", "instagram"], exp: int, sig: str, download: int = 0
) -> FileResponse:
    if not signing.valid(f"render-{kind}", render_id, exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    rows = service_client().table("render_jobs").select("*").eq("id", render_id).limit(1).execute().data
    rel = rows[0][FILES["video" if kind == "instagram" else kind]] if rows else None
    path = get_settings().data_dir / rel if rel else None
    if path and kind == "instagram":  # the Instagram delivery copy written by the publish worker
        path = path.with_name("instagram.mp4")
    if not path or not path.is_file():
        raise HTTPException(404, "Not found")
    name = f"reel-{render_id[:8]}.mp4" if download and kind == "video" else None
    return FileResponse(path, filename=name)


@router.get("/renders/{render_id}/captions")
def render_captions(
    render_id: str, format: Literal["srt", "vtt"] = "srt", user: User = Depends(current_user)
):
    """Subtitles for the exported MP4 (same cues as the burned-in captions, intro offset included)."""
    r = get_owned("render_jobs", render_id, user, columns="id, organization_id, timeline")
    body = captions.srt(r["timeline"]) if format == "srt" else captions.vtt(r["timeline"])
    return PlainTextResponse(
        body,
        media_type="text/vtt" if format == "vtt" else "application/x-subrip",
        headers={"Content-Disposition": f'attachment; filename="reel-{render_id[:8]}.{format}"'},
    )
