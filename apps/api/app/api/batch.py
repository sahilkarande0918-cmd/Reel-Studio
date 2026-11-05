"""Bulk Shorts: render many clips of one recording with one setting, follow each clip's real job state, download a ZIP.

POST /recordings/{id}/render-batch  → selects the clips and queues one render each (an identical finished render is
                                       reused, so nothing is exported twice); optional campaign brief checks per clip
GET  /recordings/{id}/batch         → every clip with its render and job status (no invented percentages)
GET  /recordings/{id}/batch-zip-url → signed link; GET /recordings/{id}/batch.zip → MP4s + SRTs + metadata.json
"""

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import Field
from starlette.background import BackgroundTask

from app.api.renders import RenderRequest, enqueue_highlight_render
from app.core import signing
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.config import get_settings
from app.core.db import service_client
from app.core.storage import recording_dir
from app.services.clips import campaign_brief
from app.services.rendering import captions

router = APIRouter(prefix="/recordings")
MB_PER_CLIP_S = 1.2  # ~10 Mbit/s H.264 + AAC; disk check before queueing a batch
DISK_MARGIN = 2 * 1024**3


class BatchRequest(RenderRequest):
    highlight_ids: list[str] | None = Field(default=None, max_length=100)  # None = every proposed/selected clip
    campaign: campaign_brief.Brief | None = None


def _clips(rec_id: str, ids: list[str] | None) -> list[dict]:
    q = service_client().table("highlight_candidates").select("*").eq("recording_id", rec_id).neq("status", "rejected")
    rows = q.order("start_s").execute().data
    return [r for r in rows if ids is None or r["id"] in ids]


def _history(rec: dict) -> Path:
    return recording_dir(rec["organization_id"], rec["id"]) / "batches.json"


@router.post("/{rec_id}/render-batch", status_code=202)
def render_batch(rec_id: str, body: BatchRequest, user: User = Depends(current_user)) -> dict:
    rec = get_owned("source_recordings", rec_id, user, write=True)
    clips = _clips(rec_id, body.highlight_ids)
    if not clips:
        raise HTTPException(409, "No clips to render: analyse the recording first")
    need = sum((c["end_s"] - c["start_s"]) * MB_PER_CLIP_S * 1024**2 for c in clips) + DISK_MARGIN
    if shutil.disk_usage(get_settings().data_dir).free < need:
        raise HTTPException(507, f"Not enough free disk space for {len(clips)} exports (needs ~{need / 1024**3:.1f} GB)")
    hist_path = _history(rec)
    history = json.loads(hist_path.read_text()) if hist_path.exists() else []
    settings = body.model_dump(exclude={"highlight_ids", "campaign"})
    req = RenderRequest(**settings)
    db = service_client()
    out, skipped = [], []
    for h in clips:
        dur = h["end_s"] - h["start_s"]
        check = None
        if body.campaign:
            feats = h.get("features") or {}
            cap = campaign_brief.caption(body.campaign, h["title"], (h.get("summary") or "")[:300])
            transformed = req.captions or req.pace != "original" or req.hook_title
            check = campaign_brief.check(body.campaign, dur, h.get("transcript_excerpt") or "", cap, transformed,
                                         history, h["start_s"], h["end_s"])
            check["caption"] = cap
            check["topic"] = feats.get("topic")
            if not check["ok"]:
                skipped.append({"highlight_id": h["id"], "title": h["title"], "campaign": check})
                continue
        if h["status"] != "selected":
            db.table("highlight_candidates").update({"status": "selected"}).eq("id", h["id"]).execute()
            h["status"] = "selected"
        r = enqueue_highlight_render(h, req, user.id)
        out.append({"highlight_id": h["id"], "title": h["title"], **r, **({"campaign": check} if check else {})})
        if body.campaign:
            history.append({"campaign": body.campaign.name, "start_s": h["start_s"], "end_s": h["end_s"],
                            "render_id": r["render_id"]})
    hist_path.write_text(json.dumps(history[-500:]))
    return {"renders": out, "skipped": skipped, "settings": settings}


@router.get("/{rec_id}/batch")
def batch_status(rec_id: str, user: User = Depends(current_user)) -> dict:
    """Each clip with its latest render and that render's job (stage, progress, error), straight from the database."""
    get_owned("source_recordings", rec_id, user)
    db = service_client()
    clips = _clips(rec_id, None)
    renders = db.table("render_jobs").select("id,highlight_id,job_id,status,error,duration_s,size_bytes,render_s,created_at") \
        .eq("recording_id", rec_id).order("created_at", desc=True).execute().data
    latest: dict[str, dict] = {}
    for r in renders:
        latest.setdefault(r["highlight_id"], r)
    job_ids = [r["job_id"] for r in latest.values() if r.get("job_id")]
    jobs = {j["id"]: j for j in (db.table("jobs").select("id,status,current_stage,progress,attempts,error")
                                 .in_("id", job_ids).execute().data if job_ids else [])}
    items = []
    for c in clips:
        r = latest.get(c["id"])
        j = jobs.get(r["job_id"]) if r and r.get("job_id") else None
        f = c.get("features") or {}
        items.append({"highlight_id": c["id"], "title": c["title"], "start_s": c["start_s"], "end_s": c["end_s"],
                      "status": c["status"], "score": f.get("editorial", {}).get("score"), "topic": f.get("topic"),
                      "render": r, "job": j})
    counts: dict[str, int] = {}
    for i in items:
        s = (i["render"] or {}).get("status", "not rendered")
        counts[s] = counts.get(s, 0) + 1
    return {"clips": items, "counts": counts}


@router.get("/{rec_id}/batch-zip-url")
def batch_zip_url(rec_id: str, user: User = Depends(current_user)) -> dict:
    get_owned("source_recordings", rec_id, user)
    q, exp = signing.query("batch-zip", rec_id)
    return {"url": f"/recordings/{rec_id}/batch.zip?{q}", "expires_at": exp}


@router.get("/{rec_id}/batch.zip")
def batch_zip(rec_id: str, exp: int, sig: str) -> FileResponse:
    """Every finished export of the recording's clips (latest render per clip): MP4, SRT and one metadata.json."""
    if not signing.valid("batch-zip", rec_id, exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    db = service_client()
    clips = {c["id"]: c for c in _clips(rec_id, None)}
    renders = db.table("render_jobs").select("*").eq("recording_id", rec_id).eq("status", "ready") \
        .order("created_at", desc=True).execute().data
    seen, data_dir = set(), get_settings().data_dir
    tmp = Path(tempfile.mkstemp(suffix=".zip")[1])
    meta = []
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:  # MP4 is already compressed
        for r in renders:
            c = clips.get(r["highlight_id"])
            if not c or r["highlight_id"] in seen or not r.get("output_path"):
                continue
            path = data_dir / r["output_path"]
            if not path.is_file():
                continue
            seen.add(r["highlight_id"])
            n = len(meta) + 1
            stem = f"{n:02d}-" + "".join(ch if ch.isalnum() else "-" for ch in c["title"].lower())[:50].strip("-")
            z.write(path, f"{stem}.mp4")
            z.writestr(f"{stem}.srt", captions.srt(r["timeline"]))
            f = c.get("features") or {}
            meta.append({"file": f"{stem}.mp4", "title": c["title"], "description": c.get("summary") or "",
                         "source_start_s": c["start_s"], "source_end_s": c["end_s"], "duration_s": r.get("duration_s"),
                         "editorial_score": f.get("editorial", {}).get("score"), "topic": f.get("topic"),
                         "hook_quote": f.get("hook_quote"), "ending_quote": f.get("ending_quote")})
        z.writestr("metadata.json", json.dumps(meta, indent=2, ensure_ascii=False))
    if not meta:
        tmp.unlink(missing_ok=True)
        raise HTTPException(404, "No finished exports yet")
    return FileResponse(tmp, filename=f"shorts-{rec_id[:8]}.zip", media_type="application/zip",
                        background=BackgroundTask(tmp.unlink, missing_ok=True))
