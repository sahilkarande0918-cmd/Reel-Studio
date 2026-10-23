"""Chunked, resumable uploads straight to local disk, plus signed media playback URLs.

Flow: POST /recordings → PUT /recordings/{id}/chunk?offset=N (repeat) → POST /recordings/{id}/complete.
GET /recordings/{id} reports received bytes, so a client resumes from where the disk says it stopped.
"""

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core import signing
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.db import service_client
from app.core.storage import source_path
from app.core.upload import CHUNK_MAX, append_chunk
from app.services import media

router = APIRouter(prefix="/recordings")
PROGRESS_EVERY = 64 * 1024 * 1024  # persist received_bytes every 64 MB (the file size on disk is the truth)
# ponytail: per-process cache of (recording, user) → row for the duration of an upload; drop if several API
# processes ever serve one upload.
_uploads: dict[tuple[str, str], tuple[float, dict]] = {}


def _upload_row(rec_id: str, user: User) -> dict:
    """Ownership + row for chunk uploads without a database round trip per chunk (checked once per 10 min)."""
    key = (rec_id, user.id)
    hit = _uploads.get(key)
    if hit and time.monotonic() - hit[0] < 600:
        return hit[1]
    rec = get_owned("source_recordings", rec_id, user, write=True)
    _uploads[key] = (time.monotonic(), rec)
    return rec


class CreateRecording(BaseModel):
    project_id: str
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0, le=media.MAX_BYTES)


@router.post("", status_code=201)
def create(body: CreateRecording, user: User = Depends(current_user)) -> dict:
    ext = Path(body.filename).suffix.lower()
    if ext not in media.ALLOWED_EXT:
        raise HTTPException(
            422, f"Unsupported file type {ext or '(none)'}. Use {', '.join(sorted(media.ALLOWED_EXT))}."
        )
    project = get_owned("projects", body.project_id, user, write=True, columns="id, organization_id, mode")
    if project["mode"] != "recording":
        raise HTTPException(422, "This project is a Topic → Video project")
    row = (
        service_client()
        .table("source_recordings")
        .insert(
            {
                "organization_id": project["organization_id"],
                "project_id": project["id"],
                "created_by": user.id,
                "filename": Path(body.filename).name,
                "size_bytes": body.size_bytes,
            }
        )
        .execute()
        .data[0]
    )
    source_path(row).touch()
    return {"id": row["id"], "chunk_size": CHUNK_MAX, "received_bytes": 0}


@router.get("/{rec_id}")
def status_of(rec_id: str, user: User = Depends(current_user)) -> dict:
    rec = get_owned("source_recordings", rec_id, user)
    p = source_path(rec)
    return {
        "id": rec["id"],
        "status": rec["status"],
        "size_bytes": rec["size_bytes"],
        "received_bytes": p.stat().st_size if p.exists() else 0,
    }


@router.put("/{rec_id}/chunk")
async def put_chunk(
    rec_id: str, request: Request, offset: int = Query(ge=0), user: User = Depends(current_user)
) -> dict:
    rec = _upload_row(rec_id, user)
    if rec["status"] != "uploading":
        raise HTTPException(409, "Upload already completed")
    have, received = await append_chunk(source_path(rec), offset, request, rec["size_bytes"])
    if received // PROGRESS_EVERY != have // PROGRESS_EVERY or received == rec["size_bytes"]:
        service_client().table("source_recordings").update({"received_bytes": received}).eq(
            "id", rec_id
        ).execute()
    return {"received_bytes": received}


@router.post("/{rec_id}/complete")
def complete(rec_id: str, user: User = Depends(current_user)) -> dict:
    rec = get_owned("source_recordings", rec_id, user, write=True)
    if rec["status"] != "uploading":
        raise HTTPException(409, "Upload already completed")
    _uploads.pop((rec_id, user.id), None)
    p = source_path(rec)
    if p.stat().st_size != rec["size_bytes"]:
        raise HTTPException(409, detail={"message": "upload incomplete", "received_bytes": p.stat().st_size})
    db = service_client()
    try:
        info = media.probe(p)
        summary = media.summarize(info)
    except media.MediaError as e:
        db.table("source_recordings").update({"status": "failed", "error": str(e)}).eq("id", rec_id).execute()
        p.unlink(missing_ok=True)  # invalid uploads are not kept
        raise HTTPException(422, str(e)) from e
    db.table("source_recordings").update(
        {
            **summary,
            "status": "uploaded",
            "storage_path": str(p.relative_to(p.parents[4])),
            "probe": info["format"],
        }
    ).eq("id", rec_id).execute()
    job = (
        db.table("jobs")
        .insert(
            {
                "organization_id": rec["organization_id"],
                "project_id": rec["project_id"],
                "job_type": "transcribe",
                "payload": {"recording_id": rec_id},
                "idempotency_key": f"transcribe:{rec_id}",
                "created_by": user.id,
                "current_stage": "queued",
            }
        )
        .execute()
        .data[0]
    )
    return {"recording": {**rec, **summary, "status": "uploaded"}, "job_id": job["id"]}


@router.post("/{rec_id}/transcribe")
def retranscribe(rec_id: str, user: User = Depends(current_user)) -> dict:
    """Retry / re-run transcription (e.g. after a failure or glossary change)."""
    rec = get_owned("source_recordings", rec_id, user, write=True)
    if rec["status"] in ("uploading",):
        raise HTTPException(409, "Upload not finished")
    db = service_client()
    active = (
        db.table("jobs")
        .select("id")
        .eq("job_type", "transcribe")
        .contains("payload", {"recording_id": rec_id})
        .in_("status", ["queued", "running"])
        .execute()
        .data
    )
    if active:
        return {"job_id": active[0]["id"]}
    job = (
        db.table("jobs")
        .insert(
            {
                "organization_id": rec["organization_id"],
                "project_id": rec["project_id"],
                "job_type": "transcribe",
                "payload": {"recording_id": rec_id},
                "created_by": user.id,
                "current_stage": "queued",
            }
        )
        .execute()
        .data[0]
    )
    return {"job_id": job["id"]}


@router.post("/{rec_id}/analyze")
def reanalyze(rec_id: str, user: User = Depends(current_user)) -> dict:
    """Re-run highlight detection and reframing (keeps selected highlights)."""
    rec = get_owned("source_recordings", rec_id, user, write=True)
    if rec["status"] != "ready":
        raise HTTPException(409, "Transcribe the recording first")
    db = service_client()
    active = (
        db.table("jobs")
        .select("id")
        .eq("job_type", "analyze")
        .contains("payload", {"recording_id": rec_id})
        .in_("status", ["queued", "running"])
        .execute()
        .data
    )
    if active:
        return {"job_id": active[0]["id"]}
    job = (
        db.table("jobs")
        .insert(
            {
                "organization_id": rec["organization_id"],
                "project_id": rec["project_id"],
                "job_type": "analyze",
                "payload": {"recording_id": rec_id},
                "created_by": user.id,
                "current_stage": "queued",
            }
        )
        .execute()
        .data[0]
    )
    return {"job_id": job["id"]}


@router.get("/{rec_id}/media-url")
def media_url(rec_id: str, request: Request, user: User = Depends(current_user)) -> dict:
    rec = get_owned("source_recordings", rec_id, user)
    q, exp = signing.query("recording", rec["id"])
    return {"path": f"/recordings/{rec['id']}/media?{q}", "expires_at": exp}


@router.get("/{rec_id}/media")
def media_file(rec_id: str, exp: int, sig: str) -> FileResponse:
    """<video> cannot send an Authorization header, so playback uses a short-lived HMAC-signed URL."""
    if not signing.valid("recording", rec_id, exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    rows = service_client().table("source_recordings").select("*").eq("id", rec_id).limit(1).execute().data
    if not rows or rows[0]["status"] == "uploading":
        raise HTTPException(404, "Not found")
    return FileResponse(source_path(rows[0]))  # Starlette FileResponse serves HTTP Range requests
