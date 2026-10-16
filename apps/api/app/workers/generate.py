"""One durable Mode B job, reusing storyboard/audio files after restart."""

from app.core.db import service_client
from app.core.storage import render_dir
from app.services.generation import TopicRequest, build_timeline, cached_storyboard, synthesize_narration
from app.services.generation.models import Storyboard
from app.services.rendering import timeline
from app.workers.jobs import JobContext
from app.workers.render import run_render


class RenderProgress:
    def __init__(self, ctx: JobContext, render_id: str):
        self.ctx = ctx
        self.payload = {"render_id": render_id}

    def check_cancel(self):
        self.ctx.check_cancel()

    def stage(self, name, progress, message=None):
        self.ctx.stage(name, 0.45 + 0.55 * progress, message)

    def progress(self, progress):
        self.ctx.progress(0.45 + 0.55 * progress)


def run_generate(ctx: JobContext) -> dict:
    db = service_client()
    gid = ctx.payload["generation_id"]
    row = db.table("topic_generations").select("*").eq("id", gid).single().execute().data
    # Deterministic folder identity makes audio reusable even before a render row exists.
    rid = row.get("render_id") or gid
    project = render_dir(row["organization_id"], rid)
    request = TopicRequest.model_validate(
        {k: v for k, v in row["settings"].items() if k in TopicRequest.model_fields}
    )
    db.table("topic_generations").update({"status": "generating", "error": None}).eq("id", gid).execute()
    ctx.stage("storyboard", 0.02, "Writing and syntax-checking the educational storyboard locally")
    edited = row["settings"].get("storyboard")
    board = Storyboard.model_validate(edited) if edited else cached_storyboard(request, project)
    db.table("topic_generations").update({"storyboard": board.model_dump()}).eq("id", gid).execute()
    ctx.stage("narration", 0.12, "Generating local narration and measuring caption timing")
    narration = synthesize_narration(
        board,
        request,
        project,
        on_progress=lambda p: ctx.stage(
            "narration", 0.12 + 0.30 * p, "Synthesizing and aligning scene narration"
        ),
    )
    kit = row.get("brand_snapshot")
    logo = timeline.logo_file(kit["logo"]) if kit and kit.get("logo") else None
    if logo:
        (project / logo[0]).write_bytes(logo[1])
    doc = build_timeline(
        board,
        narration,
        rid,
        kit=kit,
        logo_src=logo[0] if logo else None,
        quality=row["settings"].get("quality", "looks"),
    )
    doc["stylePreset"] = row["settings"].get("style", "focus")
    db.table("render_jobs").upsert(
        {
            "id": rid,
            "organization_id": row["organization_id"],
            "project_id": row["project_id"],
            "created_by": row["created_by"],
            "job_id": ctx.id,
            "quality": doc["renderSettings"]["quality"],
            "timeline": doc,
            "timeline_hash": timeline.timeline_hash(doc),
            "status": "queued",
        }
    ).execute()
    db.table("topic_generations").update({"timeline": doc, "render_id": rid, "status": "rendering"}).eq(
        "id", gid
    ).execute()
    result = run_render(RenderProgress(ctx, rid))
    db.table("topic_generations").update({"status": "ready", "error": None}).eq("id", gid).execute()
    db.table("projects").update({"status": "video ready"}).eq("id", row["project_id"]).execute()
    return {"generation_id": gid, **result}
