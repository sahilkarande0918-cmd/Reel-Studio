"""import_url job: download a pasted YouTube link onto the engine, then continue exactly like a finished upload
(probe → validate → transcribe → analyze). Progress comes from yt-dlp's real byte counts."""

from app.core.db import service_client
from app.core.storage import source_path
from app.services import link_import, media
from app.workers.jobs import JobContext, Permanent


def run_import_url(ctx: JobContext) -> dict:
    from app.api.recordings import finalize

    db = service_client()
    rid = ctx.payload["recording_id"]
    rec = (db.table("source_recordings").select("*").eq("id", rid).limit(1).execute().data or [None])[0]
    if not rec:
        raise Permanent("recording not found")
    if rec["status"] != "uploading":
        return {"recording_id": rid, "skipped": "already imported"}
    dest = source_path(rec)  # source.mp4 in the recording's folder
    ctx.stage("download", 0.02, "Downloading the video onto the engine")
    try:
        meta = link_import.download(ctx.payload["url"], dest, media.MAX_BYTES, media.MAX_DURATION_S,
                                    on_progress=lambda p: ctx.progress(0.02 + 0.9 * p), check_cancel=ctx.check_cancel)
    except ValueError as e:
        db.table("source_recordings").update({"status": "failed", "error": str(e)}).eq("id", rid).execute()
        dest.unlink(missing_ok=True)
        raise Permanent(str(e)) from e
    title = (meta.get("title") or "youtube-import").strip()
    safe = "".join(c if c.isalnum() or c in " -_" else " " for c in title).strip()[:120] or "youtube-import"
    size = dest.stat().st_size
    patch = {"filename": f"{safe}.mp4", "size_bytes": size, "received_bytes": size,
             # keep the one-click recipe stored at import time (it decides how the clips are found and rendered)
             "probe": {**(rec.get("probe") or {}), "import": {"url": ctx.payload["url"], **meta}}}
    db.table("source_recordings").update(patch).eq("id", rid).execute()
    rec = {**rec, **patch}
    if source_path(rec) != dest:  # the file name follows the (new) filename's extension, still .mp4
        dest.replace(source_path(rec))
    ctx.stage("validate", 0.95, "Checking the video")
    try:
        out = finalize(rec, rec["created_by"])
    except media.MediaError as e:
        raise Permanent(str(e)) from e
    return {"recording_id": rid, "title": title, "size_bytes": size, "duration_s": meta.get("duration"),
            "license": meta.get("license"), "transcribe_job_id": out["job_id"]}
