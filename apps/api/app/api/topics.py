"""Topic-to-video requests enqueue durable work; inference never runs in the request."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.renders import _brand_kit
from app.core.access import get_owned
from app.core.auth import User, current_user
from app.core.db import service_client
from app.services.generation import TopicRequest
from app.services.generation.models import Storyboard

router = APIRouter()


class GenerateRequest(TopicRequest):
    quality: Literal["draft", "looks", "delivery"] = "looks"
    brand_kit_id: str | None = None
    style: Literal["focus", "energy", "story", "signature"] = "focus"
    # An edited storyboard skips the LLM; it is syntax-checked here and narrated/rendered as written.
    storyboard: Storyboard | None = None


@router.post("/projects/{project_id}/generate", status_code=202)
def generate(project_id: UUID, body: GenerateRequest, user: User = Depends(current_user)) -> dict:
    project = get_owned("projects", str(project_id), user, write=True)
    if project["mode"] != "topic":
        raise HTTPException(409, "Create a Topic project to generate a video")
    kit = _brand_kit(project["organization_id"], body.brand_kit_id)
    return (
        service_client()
        .rpc(
            "enqueue_topic_generation",
            {
                "p_project": str(project_id),
                "p_user": user.id,
                "p_topic": body.topic,
                "p_settings": body.model_dump(),
                "p_brand": kit,
            },
        )
        .execute()
        .data
    )


@router.get("/projects/{project_id}/generations")
def generations(project_id: UUID, user: User = Depends(current_user)) -> list:
    get_owned("projects", str(project_id), user)
    return (
        service_client()
        .table("topic_generations")
        .select("id,project_id,status,topic,settings,storyboard,timeline,render_id,job_id,error,created_at")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(30)
        .execute()
        .data
    )
