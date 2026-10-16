"""Phase 06 editor endpoints. The editor edits a copy of a render's canonical timeline (autosaved as a
draft through RLS); these routes preview it with the export compiler and render it as a new render."""

import os
import shutil
import uuid
from pathlib import Path
from typing import Literal

import jsonschema
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.renders import _brand_kit
from app.core import signing
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.db import service_client
from app.core.storage import render_dir, source_path
from app.services.rendering import preview, timeline

router = APIRouter()


class TimelineBody(BaseModel):
    timeline: dict


class EditRender(TimelineBody):
    quality: Literal["draft", "looks", "delivery"] = "looks"


class BrandBody(BaseModel):
    brand_kit_id: str | None = None


def _checked(doc: dict) -> dict:
    try:
        timeline.validate(doc)
    except jsonschema.ValidationError as e:
        raise HTTPException(422, f"The edit is not valid yet: {e.message}") from e
    return doc


def _link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def _source(render: dict) -> Path | None:
    """The original class recording behind a Mode A render (assets with id `source`)."""
    if not render.get("recording_id"):
        return None
    rows = service_client().table("source_recordings").select("*").eq("id", render["recording_id"]).limit(1).execute().data
    return source_path(rows[0]) if rows else None


def _materialise(render: dict, doc: dict, target: Path) -> None:
    """Every media asset of `doc` must exist in `target`: the recording is linked, the rest (narration,
    logo) come from the edited render's own folder. Asset names are schema-restricted file names."""
    base = render_dir(render["organization_id"], render["id"])
    source = _source(render)
    for asset in doc["assets"].values():
        if asset["kind"] == "font":
            continue
        dst = target / asset["src"]
        if asset["id"] == "source" and source and source.exists():
            _link(source, dst)
        elif (base / asset["src"]).is_file():
            if target != base:
                _link(base / asset["src"], dst)
        elif not dst.is_file():
            raise HTTPException(422, f"Media for '{asset['id']}' is missing on the processing machine")


@router.post("/renders/{render_id}/preview")
def preview_timeline(render_id: str, body: TimelineBody, user: User = Depends(current_user)) -> dict:
    r = get_owned("render_jobs", render_id, user)
    doc = _checked(body.timeline)
    project = render_dir(r["organization_id"], r["id"])
    _materialise(r, doc, project)
    page = preview.write_preview(doc, project)
    q, exp = signing.query("render-dir", r["id"])
    sig = q.split("sig=")[1]
    return {"base": f"/renders/{r['id']}/p/{exp}/{sig}/", "page": page, "expires_at": exp}


@router.get("/renders/{render_id}/p/{exp}/{sig}/{path:path}")
def preview_file(render_id: str, exp: int, sig: str, path: str) -> FileResponse:
    """Signed folder URL so the preview's relative URLs (media, fonts, GSAP) authorise themselves."""
    if not signing.valid("render-dir", render_id, exp, sig) or not preview.SAFE_PATH.match(path):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    rows = service_client().table("render_jobs").select("organization_id").eq("id", render_id).limit(1).execute().data
    if not rows:
        raise HTTPException(404, "Not found")
    file = render_dir(rows[0]["organization_id"], render_id) / path
    if not file.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(file)


@router.post("/renders/{render_id}/edit", status_code=202)
def render_edit(render_id: str, body: EditRender, user: User = Depends(current_user)) -> dict:
    r = get_owned("render_jobs", render_id, user, write=True)
    new_id = str(uuid.uuid4())
    doc = {**body.timeline, "id": new_id, "renderSettings": {"quality": body.quality}}
    _checked(doc)
    _materialise(r, doc, render_dir(r["organization_id"], new_id))
    db = service_client()
    db.table("render_jobs").insert({
        "id": new_id, "organization_id": r["organization_id"], "project_id": r["project_id"],
        "recording_id": r.get("recording_id"), "highlight_id": r.get("highlight_id"), "parent_render_id": r["id"],
        "brand_kit_id": r.get("brand_kit_id"), "created_by": user.id, "quality": body.quality,
        "timeline": doc, "timeline_hash": timeline.timeline_hash(doc),
    }).execute()
    job = db.table("jobs").insert({
        "organization_id": r["organization_id"], "project_id": r["project_id"], "job_type": "render",
        "payload": {"render_id": new_id}, "created_by": user.id, "current_stage": "queued",
    }).execute().data[0]
    db.table("render_jobs").update({"job_id": job["id"]}).eq("id", new_id).execute()
    return {"render_id": new_id, "job_id": job["id"]}


@router.post("/renders/{render_id}/brand")
def brand_for_edit(render_id: str, body: BrandBody, user: User = Depends(current_user)) -> dict:
    """A brand kit as a timeline brand snapshot; its logo file is written next to the edited render."""
    r = get_owned("render_jobs", render_id, user, write=True)
    kit = _brand_kit(r["organization_id"], body.brand_kit_id)
    brand, preset = timeline.brand_snapshot(kit, r["timeline"].get("title", ""))
    brand = {**brand}
    asset = None
    if kit and kit.get("logo"):
        try:
            name, data = timeline.logo_file(kit["logo"])
        except ValueError as e:
            raise HTTPException(422, f"Brand kit logo: {e}") from e
        (render_dir(r["organization_id"], r["id"]) / name).write_bytes(data)
        asset = {"id": "logo", "kind": "image", "src": name}
        brand["logoAssetId"] = "logo"
    return {"brand": brand, "logoAsset": asset, "captionPreset": preset}
