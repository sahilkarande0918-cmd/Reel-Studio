"""Mode B (prompt → professional edit) requests enqueue one durable `edit` job; nothing heavy runs in the request."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.renders import _brand_kit
from app.core import signing
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.db import service_client
from app.services.editing.pacing import PROFILES
from app.services.rendering import caption_presets

router = APIRouter()
Style = Literal["auto", *PROFILES.keys()]  # type: ignore[valid-type]


class EditRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    duration_s: float = Field(default=15, ge=5, le=60)
    aspect: Literal["9:16", "1:1", "4:5", "16:9"] = "9:16"
    style: Style = "auto"
    # upload = the project's music track, score = original synthesized score, none = footage audio only
    music: Literal["upload", "score", "none"] = "upload"
    use_reference: bool = True
    captions: bool = False
    caption_preset: str = Field(default="creator-pop", pattern=r"^[a-z0-9-]{2,40}$")
    caption_overrides: caption_presets.Overrides = Field(default_factory=caption_presets.Overrides)
    # "none", "kokoro" (built-in local voice) or a saved voice profile id
    voice: str = Field(default="none", max_length=64)
    narration: str | None = Field(default=None, max_length=1500)
    language: Literal["en", "hi", "hinglish"] = "en"
    quality: Literal["draft", "looks", "delivery"] = "looks"
    brand_kit_id: str | None = None


@router.post("/projects/{project_id}/edit", status_code=202)
def edit(project_id: UUID, body: EditRequest, user: User = Depends(current_user)) -> dict:
    project = get_owned("projects", str(project_id), user, write=True)
    if project["mode"] != "edit":
        raise HTTPException(409, "Create a Prompt → Edit project to generate an edit")
    db = service_client()
    assets = db.table("media_assets").select("kind,status").eq("project_id", str(project_id)).execute().data
    if not any(a["kind"] in ("clip", "image") and a["status"] in ("uploaded", "analyzing", "ready") for a in assets):
        raise HTTPException(409, "Upload at least one clip or image first")
    if body.music == "upload" and not any(a["kind"] == "audio" and a["status"] != "failed" for a in assets):
        body.music = "score"  # recorded in settings, so the UI shows what was actually used
    kit = _brand_kit(project["organization_id"], body.brand_kit_id)
    return (
        db.rpc(
            "enqueue_edit_generation",
            {
                "p_project": str(project_id),
                "p_user": user.id,
                "p_prompt": body.prompt,
                "p_settings": body.model_dump(),
                "p_brand": kit,
            },
        )
        .execute()
        .data
    )


@router.get("/projects/{project_id}/edits")
def edits(project_id: UUID, user: User = Depends(current_user)) -> list:
    get_owned("projects", str(project_id), user)
    rows = (
        service_client()
        .table("edit_generations")
        .select("id,status,prompt,settings,director,plan,qa,render_id,job_id,error,created_at")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
    )
    for r in rows:  # storyboard stills live in the render folder; one signed folder URL serves them
        if r["render_id"]:
            q, exp = signing.query("render-dir", r["render_id"])
            r["files"] = f"/renders/{r['render_id']}/p/{exp}/{q.split('sig=')[1]}/"
    return rows
