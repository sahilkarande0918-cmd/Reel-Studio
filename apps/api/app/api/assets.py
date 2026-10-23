"""Mode B media: any practical number of clips, images, one music track and one reference reel per project.

Flow per file (same resumable protocol as recordings): POST /assets → PUT /assets/{id}/chunk?offset=N (repeat)
→ POST /assets/{id}/complete (ffprobe, duplicate check, queues an `ingest` analysis job).
Limits are explicit, not "unlimited": see LIMITS, also returned by GET /assets/limits.
"""

import hashlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core import signing
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.db import service_client
from app.core.storage import asset_dir, asset_path
from app.core.upload import CHUNK_MAX, append_chunk
from app.services import media

router = APIRouter(prefix="/assets")
Kind = Literal["clip", "image", "audio", "reference"]
VIDEO_EXT = media.ALLOWED_EXT
EXT = {
    "clip": VIDEO_EXT,
    "reference": VIDEO_EXT,
    "image": {".jpg", ".jpeg", ".png", ".webp"},
    "audio": {".mp3", ".mpeg", ".wav", ".m4a", ".aac", ".ogg", ".flac"},
}
LIMITS = {
    "file_bytes": {"clip": 2 * 1024**3, "reference": 1024**3, "image": 30 * 1024**2, "audio": 300 * 1024**2},
    "project_files": 300,
    "project_bytes": 40 * 1024**3,
    "clip_max_s": 20 * 60,
    "reference_max_s": 180,
    "audio_max_s": 15 * 60,
}


class CreateAsset(BaseModel):
    project_id: str
    kind: Kind
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)


def _rows(project_id: str) -> list[dict]:
    return (
        service_client()
        .table("media_assets")
        .select("id,kind,filename,size_bytes,status,sha256")
        .eq("project_id", project_id)
        .execute()
        .data
    )


@router.get("/limits")
def limits() -> dict:
    return {**LIMITS, "extensions": {k: sorted(v) for k, v in EXT.items()}, "chunk_size": CHUNK_MAX}


@router.post("", status_code=201)
def create(body: CreateAsset, user: User = Depends(current_user)) -> dict:
    ext = Path(body.filename).suffix.lower()
    if ext not in EXT[body.kind]:
        raise HTTPException(422, f"{ext or '(no extension)'} is not a supported {body.kind} file. Use {', '.join(sorted(EXT[body.kind]))}.")
    if body.size_bytes > LIMITS["file_bytes"][body.kind]:
        raise HTTPException(413, f"A {body.kind} file may be up to {LIMITS['file_bytes'][body.kind] // 1024**2} MB")
    project = get_owned("projects", body.project_id, user, write=True, columns="id, organization_id, mode")
    if project["mode"] != "edit":
        raise HTTPException(422, "Media uploads belong to a Prompt → Edit project")
    rows = [r for r in _rows(project["id"]) if r["status"] != "failed"]
    if len(rows) >= LIMITS["project_files"]:
        raise HTTPException(413, f"A project holds up to {LIMITS['project_files']} files")
    if sum(r["size_bytes"] for r in rows) + body.size_bytes > LIMITS["project_bytes"]:
        raise HTTPException(413, f"A project holds up to {LIMITS['project_bytes'] // 1024**3} GB of media")
    db = service_client()
    if body.kind in ("audio", "reference"):  # one soundtrack and one reference per project: a new one replaces it
        for old in (r for r in rows if r["kind"] == body.kind):
            _delete(db, {**old, "organization_id": project["organization_id"]})
    row = (
        db.table("media_assets")
        .insert(
            {
                "organization_id": project["organization_id"],
                "project_id": project["id"],
                "created_by": user.id,
                "kind": body.kind,
                "filename": Path(body.filename).name,
                "size_bytes": body.size_bytes,
                "position": len(rows),
            }
        )
        .execute()
        .data[0]
    )
    asset_path(row).touch()
    return {"id": row["id"], "chunk_size": CHUNK_MAX, "received_bytes": 0}


@router.get("/{asset_id}")
def status_of(asset_id: str, user: User = Depends(current_user)) -> dict:
    a = get_owned("media_assets", asset_id, user)
    p = asset_path(a)
    return {"id": a["id"], "status": a["status"], "size_bytes": a["size_bytes"], "received_bytes": p.stat().st_size if p.exists() else 0}


@router.put("/{asset_id}/chunk")
async def put_chunk(asset_id: str, request: Request, offset: int = Query(ge=0), user: User = Depends(current_user)) -> dict:
    a = get_owned("media_assets", asset_id, user, write=True, columns="id,organization_id,filename,size_bytes,status")
    if a["status"] != "uploading":
        raise HTTPException(409, "Upload already completed")
    _, received = await append_chunk(asset_path(a), offset, request, a["size_bytes"])
    return {"received_bytes": received}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _summary(kind: str, info: dict) -> dict:
    """Validated stored fields; MediaError carries a user-facing reason."""
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic") != 1), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(info.get("format", {}).get("duration") or 0)
    if kind == "image":
        if not video:
            raise media.MediaError("Not a readable image")
        return {"width": video.get("width"), "height": video.get("height")}
    if kind == "audio":
        if not audio:
            raise media.MediaError("No audio stream in this file")
        if not 3 <= dur <= LIMITS["audio_max_s"]:
            raise media.MediaError(f"Music must be 3 s to {LIMITS['audio_max_s'] // 60} min long")
        return {"duration_s": dur}
    if not video:
        raise media.MediaError("No video stream in this file")
    limit = LIMITS["reference_max_s" if kind == "reference" else "clip_max_s"]
    if not 0.3 <= dur <= limit:
        raise media.MediaError(f"{'Reference reels' if kind == 'reference' else 'Clips'} must be 0.3 s to {limit // 60} min long")
    num, den = (int(x) for x in (video.get("avg_frame_rate") or video.get("r_frame_rate") or "30/1").split("/"))
    return {"duration_s": dur, "width": video.get("width"), "height": video.get("height"), "fps": num / den if den else None}


@router.post("/{asset_id}/complete")
def complete(asset_id: str, user: User = Depends(current_user)) -> dict:
    a = get_owned("media_assets", asset_id, user, write=True)
    if a["status"] != "uploading":
        raise HTTPException(409, "Upload already completed")
    p = asset_path(a)
    if p.stat().st_size != a["size_bytes"]:
        raise HTTPException(409, detail={"message": "upload incomplete", "received_bytes": p.stat().st_size})
    db = service_client()
    digest = _sha256(p)
    dup = next((r for r in _rows(a["project_id"]) if r["sha256"] == digest and r["id"] != a["id"] and r["status"] != "failed"), None)
    if dup:  # the same file twice adds nothing to an edit
        _delete(db, a)
        return {"asset": dup, "duplicate": True}
    try:
        summary = _summary(a["kind"], media.probe(p))
    except media.MediaError as e:
        _delete(db, a)
        raise HTTPException(422, f"{a['filename']}: {e}") from e
    row = db.table("media_assets").update({**summary, "sha256": digest, "status": "uploaded"}).eq("id", a["id"]).execute().data[0]
    job = (
        db.table("jobs")
        .insert(
            {
                "organization_id": a["organization_id"],
                "project_id": a["project_id"],
                "job_type": "ingest",
                "payload": {"asset_id": a["id"]},
                "idempotency_key": f"ingest:{a['id']}",
                "created_by": user.id,
                "current_stage": "queued",
            }
        )
        .execute()
        .data[0]
    )
    return {"asset": row, "job_id": job["id"], "duplicate": False}


def _delete(db, a: dict) -> None:
    d = asset_dir(a["organization_id"], a["id"])
    for f in d.glob("*"):
        f.unlink(missing_ok=True)
    d.rmdir()
    db.table("media_assets").delete().eq("id", a["id"]).execute()


@router.delete("/{asset_id}", status_code=204)
def delete(asset_id: str, user: User = Depends(current_user)) -> None:
    _delete(service_client(), get_owned("media_assets", asset_id, user, write=True))


class Order(BaseModel):
    ids: list[str] = Field(max_length=300)


@router.post("/projects/{project_id}/order")
def reorder(project_id: str, body: Order, user: User = Depends(current_user)) -> dict:
    get_owned("projects", project_id, user, write=True)
    db = service_client()
    mine = {r["id"] for r in _rows(project_id)}
    for i, aid in enumerate(x for x in body.ids if x in mine):
        db.table("media_assets").update({"position": i}).eq("id", aid).execute()
    return {"ok": True}


@router.get("/{asset_id}/urls")
def urls(asset_id: str, user: User = Depends(current_user)) -> dict:
    a = get_owned("media_assets", asset_id, user, columns="id,organization_id")
    out = {}
    for kind in ("media", "thumb"):
        q, exp = signing.query(f"asset-{kind}", a["id"])
        out[kind] = f"/assets/{a['id']}/file/{kind}?{q}"
        out["expires_at"] = exp
    return out


@router.get("/{asset_id}/file/{kind}")
def file(asset_id: str, kind: Literal["media", "thumb"], exp: int, sig: str) -> FileResponse:
    if not signing.valid(f"asset-{kind}", asset_id, exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    rows = service_client().table("media_assets").select("*").eq("id", asset_id).limit(1).execute().data
    if not rows or rows[0]["status"] == "uploading":
        raise HTTPException(404, "Not found")
    p = asset_path(rows[0]) if kind == "media" else asset_dir(rows[0]["organization_id"], asset_id) / "thumb.jpg"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p)
