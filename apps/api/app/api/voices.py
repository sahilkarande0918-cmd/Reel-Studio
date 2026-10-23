"""Voice profiles: upload a sample once with explicit consent, preview, set pronunciations, delete.

A profile is usable only by the person who created it; other workspace members only see that it exists."""

import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core import signing
from app.core.access import get_owned, require_role
from app.core.auth import User, current_user
from app.core.db import service_client
from app.services import voice_profiles as vp

router = APIRouter(prefix="/voices")
MAX_SAMPLE = 25 * 1024 * 1024
BUILT_IN = [{"id": f"kokoro:{v}", "label": f"{n} (built-in voice)", "kind": "builtin"} for v, n in
            (("af_heart", "Heart"), ("af_bella", "Bella"), ("am_adam", "Adam"))]


def _mine(vid: str, user: User) -> dict:
    p = get_owned("voice_profiles", vid, user)
    if p["created_by"] != user.id:  # a voice belongs to the person who recorded it
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return p


@router.get("")
def list_voices(org_id: str | None = None, user: User = Depends(current_user)) -> list[dict]:
    q = service_client().table("voice_profiles").select("id,name,status,quality,created_at,organization_id").eq("created_by", user.id)
    if org_id:
        q = q.eq("organization_id", org_id)
    mine = [{"id": f"profile:{p['id']}", "label": f"{p['name']} (your voice)", "kind": "profile", "status": p["status"],
             "quality": p["quality"], "profile_id": p["id"]} for p in q.order("created_at", desc=True).execute().data]
    return [*mine, *BUILT_IN]


@router.get("/consent")
def consent_text() -> dict:
    return {"statement": vp.CONSENT, "engine_installed": vp.available()}


@router.post("", status_code=201)
async def create(
    org_id: str = Form(...),
    name: str = Form(..., min_length=1, max_length=60),
    consent: bool = Form(...),
    consent_statement: str = Form(...),
    sample: UploadFile = File(...),
    user: User = Depends(current_user),
) -> dict:
    require_role(org_id, user, write=True)
    if not consent or consent_statement.strip() != vp.CONSENT:
        raise HTTPException(422, "Confirm the consent statement to create a voice profile")
    vid = str(uuid.uuid4())
    d = vp.voice_dir(org_id, vid)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / f"upload{Path(sample.filename or 'a.wav').suffix.lower()[:6]}"
        size = 0
        with raw.open("wb") as f:
            while chunk := await sample.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_SAMPLE:
                    raise HTTPException(413, "Voice samples may be up to 25 MB")
                f.write(chunk)
        try:
            vp.normalise(raw, d / "sample.wav")
        except ValueError as e:
            shutil.rmtree(d, ignore_errors=True)
            raise HTTPException(422, str(e)) from e
    q = vp.quality(d / "sample.wav")
    if not q["ok"]:
        shutil.rmtree(d, ignore_errors=True)  # a rejected sample is not kept
        raise HTTPException(422, {"message": "The sample is not good enough to clone yet", "quality": q})
    row = service_client().table("voice_profiles").insert({
        "id": vid, "organization_id": org_id, "created_by": user.id, "name": name, "status": "ready",
        "consent_statement": vp.CONSENT, "consent_at": datetime.now(UTC).isoformat(), "sample_seconds": q["seconds"], "quality": q,
    }).execute().data[0]
    return {"id": row["id"], "quality": q}


class Pronunciations(BaseModel):
    rules: dict[str, str] = Field(default_factory=dict, max_length=100)


@router.put("/{vid}/pronunciations")
def set_pronunciations(vid: str, body: Pronunciations, user: User = Depends(current_user)) -> dict:
    _mine(vid, user)
    rules = {k.strip()[:40]: v.strip()[:80] for k, v in body.rules.items() if k.strip() and v.strip()}
    service_client().table("voice_profiles").update({"pronunciations": rules}).eq("id", vid).execute()
    return {"rules": rules}


class Preview(BaseModel):
    text: str = Field(default="Hi! This is my Reel Studio voice. Aaj hum ek naya reel banayenge.", min_length=3, max_length=300)
    language: Literal["en", "hi", "hinglish"] = "en"


@router.post("/{vid}/preview", status_code=202)
def preview(vid: str, body: Preview, user: User = Depends(current_user)) -> dict:
    p = _mine(vid, user)
    job = service_client().table("jobs").insert({
        "organization_id": p["organization_id"], "job_type": "voice_preview", "created_by": user.id, "current_stage": "queued",
        "payload": {"voice": f"profile:{vid}", "text": body.text, "language": body.language},
    }).execute().data[0]
    return {"job_id": job["id"]}


@router.get("/preview/{job_id}/url")
def preview_url(job_id: str, user: User = Depends(current_user)) -> dict:
    j = get_owned("jobs", job_id, user)
    if j["job_type"] != "voice_preview" or j["status"] != "succeeded":
        raise HTTPException(409, "Preview not ready")
    q, exp = signing.query("voice-preview", job_id)
    return {"path": f"/voices/preview/{job_id}/audio?{q}", "expires_at": exp, **(j.get("result") or {})}


@router.get("/preview/{job_id}/audio")
def preview_audio(job_id: str, exp: int, sig: str) -> FileResponse:
    if not signing.valid("voice-preview", job_id, exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    j = service_client().table("jobs").select("result").eq("id", job_id).limit(1).execute().data
    path = Path((j[0].get("result") or {}).get("path", "")) if j else None
    if not path or not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="audio/wav")


@router.delete("/{vid}", status_code=204)
def delete(vid: str, user: User = Depends(current_user)) -> None:
    p = _mine(vid, user)
    shutil.rmtree(vp.voice_dir(p["organization_id"], vid), ignore_errors=True)  # sample + previews
    service_client().table("voice_profiles").delete().eq("id", vid).execute()

