"""transcribe job: extract audio → faster-whisper → glossary correction → persist."""

import time
from pathlib import Path

from app.core.db import service_client
from app.core.storage import recording_dir, source_path
from app.services import media
from app.services.transcription import cleanup, glossary, whisper
from app.workers.jobs import JobContext, Permanent

BATCH = 500


def run_transcribe(ctx: JobContext) -> dict:
    db = service_client()
    rec_id = ctx.payload.get("recording_id")
    rows = db.table("source_recordings").select("*").eq("id", rec_id).limit(1).execute().data
    if not rows:
        raise Permanent("recording not found")
    rec = rows[0]
    src = source_path(rec)
    if not src.exists():
        raise Permanent("source file missing on the processing machine")
    db.table("source_recordings").update({"status": "processing", "error": None}).eq("id", rec_id).execute()
    try:
        return _run(ctx, db, rec, src)
    except Exception as e:
        db.table("source_recordings").update({"status": "failed", "error": str(e)[:500]}).eq(
            "id", rec_id
        ).execute()
        raise


def _run(ctx: JobContext, db, rec: dict, src) -> dict:
    audio = recording_dir(rec["organization_id"], rec["id"]) / "audio16k.wav"
    ctx.stage("extract_audio", 0.02, "Extracting and normalising audio")
    if not audio.exists():  # cached across retries
        try:
            media.extract_audio(src, audio)
        except media.MediaError as e:
            raise Permanent(str(e)) from e

    org_terms = (
        db.table("technical_glossaries")
        .select("term, aliases")
        .eq("organization_id", rec["organization_id"])
        .execute()
        .data
    )
    gl = glossary.Glossary.build(org_terms)

    t0 = time.perf_counter()
    recipe = (rec.get("probe") or {}).get("recipe") or {}
    subs = recording_dir(rec["organization_id"], rec["id"]) / "subtitles.srt"
    if subs.exists():  # the user's own subtitles: no speech recognition needed
        from app.services.transcription import srt

        ctx.stage("transcribe", 0.08, "Reading your subtitles (.srt)")
        segments, srt_words = srt.to_words(srt.parse(subs.read_text(encoding="utf-8")))
        result = whisper.Result(recipe.get("language") or "unknown", 1.0, rec.get("duration_s") or srt_words[-1]["end_s"],
                                segments, srt_words, model="srt-upload", device="none")
        timing = "srt-even"
    else:
        ctx.stage("transcribe", 0.08, "Transcribing speech on the local GPU")
        # one-click recipes and link imports: the speech model follows the spoken language (English podcasts need the
        # general model); plain class uploads keep the verified Hinglish path
        auto = bool(recipe) or bool((rec.get("probe") or {}).get("import"))
        lang = {"auto": None, "en": "en", "hi": "hinglish", "hinglish": "hinglish"}.get(recipe.get("language") or "auto")
        result = whisper.transcribe(
            audio, hotwords=gl.hotwords(), on_progress=lambda p: ctx.progress(0.08 + 0.8 * p),
            **({"language": lang, "auto_model": True} if auto else {}),
        )
        timing = "whisper-dtw"
    elapsed = time.perf_counter() - t0
    ctx.check_cancel()

    ctx.stage("correct_terms", 0.9, "Correcting technical vocabulary")
    words = cleanup.remove_loops(glossary.correct(result.words, gl))

    ctx.stage("save", 0.94, "Saving transcript")
    tr = (
        db.table("transcripts")
        .insert(
            {
                "organization_id": rec["organization_id"],
                "recording_id": rec["id"],
                "model": f"faster-whisper:{Path(result.model).name}@{result.device}",  # never a local path
                "language": result.language,
                "language_probability": result.language_probability,
                "duration_s": result.duration_s,
                "processing_s": round(elapsed, 2),
                "word_timing": timing,
            }
        )
        .execute()
        .data[0]
    )
    for seg in result.segments:
        seg["transcript_id"] = tr["id"]
    for w in words:
        w["transcript_id"] = tr["id"]
    for i in range(0, len(result.segments), BATCH):
        db.table("transcript_segments").insert(result.segments[i : i + BATCH]).execute()
    for i in range(0, len(words), BATCH):
        db.table("transcript_words").insert(words[i : i + BATCH]).execute()
    db.table("source_recordings").update({"status": "ready"}).eq("id", rec["id"]).execute()
    db.table("projects").update({"status": "transcribed"}).eq("id", rec["project_id"]).execute()
    db.table("jobs").insert(
        {  # Phase 03 analysis follows automatically
            "organization_id": rec["organization_id"],
            "project_id": rec["project_id"],
            "job_type": "analyze",
            "payload": {"recording_id": rec["id"], **(recipe.get("analyze") or {}),
                        **({"auto_render": True} if recipe.get("render") else {})},
            "current_stage": "queued",
            "created_by": rec["created_by"],
        }
    ).execute()
    corrected = sum(1 for w in words if "correction" in w["metadata"])
    return {
        "transcript_id": tr["id"],
        "words": len(words),
        "segments": len(result.segments),
        "corrections": corrected,
        "processing_s": round(elapsed, 2),
        "realtime_factor": round(result.duration_s / elapsed, 2) if elapsed else None,
        "language": result.language,
        "device": result.device,
    }
