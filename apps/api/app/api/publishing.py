from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.access import get_owned, require_role
from app.core.auth import User, current_user
from app.core.db import service_client

router = APIRouter()


class PublishBody(BaseModel):
    render_id: UUID
    account_id: UUID
    caption: str = Field(default="", max_length=2200)
    scheduled_at: datetime | None = None
    cover_ms: int | None = Field(default=None, ge=0, le=900_000)

    @field_validator("scheduled_at")
    @classmethod
    def timezone_required(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("Schedule must include a timezone")
        return value


@router.get("/publishing")
def queue(organization_id: UUID, user: User = Depends(current_user)) -> list:
    require_role(str(organization_id), user)
    return (
        service_client()
        .table("publish_jobs")
        .select("*")
        .eq("organization_id", str(organization_id))
        .order("scheduled_at", desc=True)
        .limit(100)
        .execute()
        .data
    )


@router.get("/publishing/exports")
def exports(organization_id: UUID, user: User = Depends(current_user)) -> list:
    require_role(str(organization_id), user)
    rows = (
        service_client()
        .table("render_jobs")
        .select("id,duration_s,created_at,timeline,projects(name)")
        .eq("organization_id", str(organization_id))
        .eq("status", "ready")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )
    return [
        {
            "id": r["id"],
            "duration_s": r["duration_s"],
            "created_at": r["created_at"],
            "title": r["timeline"].get("title", "Reel"),
            "project_name": (r.get("projects") or {}).get("name", "Project"),
        }
        for r in rows
    ]


@router.post("/publishing", status_code=202)
def schedule(body: PublishBody, user: User = Depends(current_user)) -> dict:
    render = get_owned("render_jobs", str(body.render_id), user, write=True)
    account = get_owned("social_accounts", str(body.account_id), user, write=True)
    if account["organization_id"] != render["organization_id"]:
        raise HTTPException(404, "Not found")
    if render["status"] != "ready" or account["status"] != "connected":
        raise HTTPException(409, "Choose a finished export and connected account")
    if account["platform"] != "instagram":
        raise HTTPException(409, "YouTube publishing is not configured yet")
    when = body.scheduled_at or datetime.now(UTC)
    if body.scheduled_at and when < datetime.now(UTC):
        raise HTTPException(422, "Choose a future schedule time")
    if body.cover_ms is not None and render.get("duration_s") and body.cover_ms > render["duration_s"] * 1000:
        raise HTTPException(422, "The cover frame must be inside the video")
    db = service_client()
    result = (
        db.rpc(
            "enqueue_publication",
            {
                "p_render": str(body.render_id),
                "p_account": str(body.account_id),
                "p_user": user.id,
                "p_caption": body.caption,
                "p_when": when.astimezone(UTC).isoformat(),
            },
        )
        .execute()
        .data
    )
    proj = db.table("projects").select("campaign_id").eq("id", render["project_id"]).limit(1).execute().data
    pid = result.get("id") or result.get("publish_id")
    if pid:  # cover and campaign only on a post this request created (a duplicate keeps what it had)
        db.table("publish_jobs").update({"cover_ms": body.cover_ms, "campaign_id": (proj or [{}])[0].get("campaign_id")})             .eq("id", pid).eq("status", "scheduled").execute()
    return result


@router.get("/publishing/suggest")
def suggest(render_id: UUID, user: User = Depends(current_user)) -> dict:
    """Caption + hashtag suggestion from what the system already knows about this video (never invented):
    the campaign Reel it was made for, else the AI director's treatment and on-screen lines, else the highlight."""
    r = get_owned("render_jobs", str(render_id), user)
    db = service_client()
    proj = (db.table("projects").select("name,campaign_id,campaign_reel").eq("id", r["project_id"]).limit(1).execute().data or [{}])[0]
    if proj.get("campaign_id"):
        c = (db.table("campaigns").select("plan,code").eq("id", proj["campaign_id"]).limit(1).execute().data or [{}])[0]
        reel = next((x for x in ((c.get("plan") or {}).get("reels") or []) if x["key"] == proj.get("campaign_reel")), None)
        if reel:
            links = db.table("tracked_links").select("slug,kind").eq("campaign_id", proj["campaign_id"]).eq("reel_key", reel["key"]).execute().data
            return {"source": "campaign", "caption": f"{reel['caption']}\n\n{reel['cta']} (link in bio)", "hashtags": reel["hashtags"],
                    "link_slugs": [x["slug"] for x in links]}
    edit = (db.table("edit_generations").select("director").eq("render_id", r["id"]).limit(1).execute().data or [{}])[0].get("director")
    if edit:
        lines = [t["text"] for t in edit.get("on_screen_text") or []]
        caption = " ".join(lines) or edit.get("treatment", "")
        if edit.get("ai_generated"):  # AI-animated photos must be disclosed as machine-generated (LTXV licence)
            caption += "\n\nSome shots are AI-generated video made from photos."
        return {"source": "director", "caption": caption, "hashtags": ["#aigenerated"] if edit.get("ai_generated") else [],
                "link_slugs": []}
    if r.get("highlight_id"):
        h = (db.table("highlight_candidates").select("title,summary").eq("id", r["highlight_id"]).limit(1).execute().data or [{}])[0]
        return {"source": "highlight", "caption": f"{h.get('title', '')}\n\n{h.get('summary', '')}".strip(), "hashtags": [], "link_slugs": []}
    return {"source": "none", "caption": "", "hashtags": [], "link_slugs": []}


@router.post("/publishing/{publish_id}/cancel")
def cancel(publish_id: UUID, user: User = Depends(current_user)) -> dict:
    get_owned("publish_jobs", str(publish_id), user, write=True)
    result = (
        service_client()
        .rpc("change_publication", {"p_id": str(publish_id), "p_action": "cancel", "p_user": user.id})
        .execute()
        .data
    )
    if not result:
        raise HTTPException(409, "Only queued posts can be cancelled")
    return result


@router.post("/publishing/{publish_id}/retry", status_code=202)
def retry(publish_id: UUID, user: User = Depends(current_user)) -> dict:
    get_owned("publish_jobs", str(publish_id), user, write=True)
    result = (
        service_client()
        .rpc("change_publication", {"p_id": str(publish_id), "p_action": "retry", "p_user": user.id})
        .execute()
        .data
    )
    if not result:
        raise HTTPException(409, "This post cannot safely be retried. Check its platform status first.")
    return result
