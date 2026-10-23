"""edit job (Mode B): assets → AI director → beat planner → FFmpeg base picture + separate audio → measured QA →
canonical timeline. Overlays (text, motion graphics, captions) are layered by the Hyperframes render on top of the
base picture; without overlays the verified base MP4 is the export (renderer router: simplest renderer that works)."""

import json
import shutil
import subprocess
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.db import service_client
from app.core.storage import asset_path, render_dir
from app.services import voice
from app.services.editing import director, overlay, planner, qa, render, style_transfer
from app.services.rendering import motion, timeline
from app.workers.ingest import ingest
from app.workers.jobs import JobContext, Permanent
from app.workers.render import run_render, verify

SIZES = {"9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "16:9": (1920, 1080)}


class Sub:
    """Maps a sub-step's 0..1 progress into a slice of this job's progress."""

    def __init__(self, ctx: JobContext, lo: float, hi: float, payload: dict):
        self.ctx, self.lo, self.hi, self.payload = ctx, lo, hi, payload

    def check_cancel(self):
        self.ctx.check_cancel()

    def stage(self, name, progress, message=None):
        self.ctx.stage(name, self.lo + (self.hi - self.lo) * progress, message)

    def progress(self, progress):
        self.ctx.progress(self.lo + (self.hi - self.lo) * progress)


def _assets(db, project_id: str) -> list[dict]:
    rows = db.table("media_assets").select("*").eq("project_id", project_id).order("position").order("created_at").execute().data
    for a in rows:
        if a["status"] in ("uploaded", "analyzing") or (a["status"] == "ready" and not a.get("analysis")):
            a["analysis"] = ingest(a)  # analysis job not run yet (or still queued): do it inline
            db.table("media_assets").update({"status": "ready", "analysis": a["analysis"]}).eq("id", a["id"]).execute()
            a["status"] = "ready"
    return [a for a in rows if a["status"] == "ready"]


def storyboard_stills(mp4: Path, plan: dict, out_dir: Path) -> list[str]:
    names = []
    for i, s in enumerate(plan["segments"]):
        t = (s["slot"][0] + s["slot"][1]) / 2
        name = f"sb-{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1",
                        "-vf", "scale=240:-2", str(out_dir / name)], check=True, timeout=60)
        names.append(name)
    return names


def finalize_base(rid: str, org: str, base: Path, doc: dict, started: float) -> dict:
    """No overlays: the muxed base picture is the export (verified like any render)."""
    project = render_dir(org, rid)
    out = project / "out.mp4"
    shutil.copyfile(base, out)
    meta = verify(out, doc["duration"], doc["width"], doc["height"], audible=True)
    thumb = project / "thumb.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(doc['duration'] / 3, 10):.2f}", "-i", str(out),
                    "-frames:v", "1", "-vf", "scale=540:-2", str(thumb)], check=True, timeout=120)
    data_dir = get_settings().data_dir
    fields = {**meta, "status": "ready", "output_path": out.relative_to(data_dir).as_posix(),
              "thumbnail_path": thumb.relative_to(data_dir).as_posix(), "size_bytes": out.stat().st_size,
              "render_s": round(time.monotonic() - started, 1)}
    service_client().table("render_jobs").update(fields).eq("id", rid).execute()
    return fields


def run_edit(ctx: JobContext) -> dict:
    db = service_client()
    gid = ctx.payload["generation_id"]
    g = db.table("edit_generations").select("*").eq("id", gid).single().execute().data
    st = g["settings"]
    rid = g.get("render_id") or gid  # deterministic folder: a retried job reuses its analysis and audio
    project = render_dir(g["organization_id"], rid)
    work = project / "work"
    started = time.monotonic()
    db.table("edit_generations").update({"status": "planning", "error": None}).eq("id", gid).execute()

    ctx.stage("analyze", 0.02, "Checking the analysis of your clips, music and reference")
    assets = _assets(db, g["project_id"])
    clips = [a for a in assets if a["kind"] in ("clip", "image")]
    if not clips:
        raise Permanent("No usable clips or images in this project")
    music_asset = next((a for a in assets if a["kind"] == "audio"), None) if st.get("music") == "upload" else None
    ref_asset = next((a for a in assets if a["kind"] == "reference"), None) if st.get("use_reference", True) else None
    music = music_asset["analysis"] if music_asset else None
    reference = ref_asset["analysis"] if ref_asset else None

    ctx.stage("direct", 0.08, "AI director is reading the footage, music and your request")
    d, provenance = director.direct(g["prompt"], st, [(a["filename"], a["analysis"]) for a in clips], music, reference,
                                    overlay.templates())
    profile = director.profile_for(d)
    evidence = []
    if reference:
        profile, evidence = style_transfer.from_reference(reference, profile)
    w, h = SIZES[st.get("aspect", "9:16")]
    duration = float(st.get("duration_s", 15))

    narration = None
    if st.get("voice", "none") != "none":
        script = (st.get("narration") or d.narration or "").strip()
        if script:
            ctx.stage("voice", 0.14, "Recording the narration and measuring word timing")
            work.mkdir(parents=True, exist_ok=True)
            wav, ndur, words = voice.narrate(script, st["voice"], work, st.get("language", "en"))
            narration = {"wav": wav, "duration": ndur, "words": words, "script": script}
            duration = max(duration, min(60.0, round(ndur + 1.0, 1)))  # never cut the narration off

    ctx.stage("plan", 0.2, "Planning cuts on the beat")
    ordered = [a["analysis"] | {"kind": "image" if a["kind"] == "image" else "video"} for a in clips]
    pl = planner.plan(ordered, profile, duration, music if music and music.get("has_music") else None, 30, w, h,
                      director.clip_weights(d, len(clips)),
                      d.open_with - 1 if d.open_with else None, d.close_with - 1 if d.close_with else None)
    if st.get("music") == "score" or (st.get("music") == "upload" and not music):
        pl["generate_score"] = profile.score
    motion_items = overlay.graphics(d, pl["duration"], [a for a in clips])
    if d.sound_effects or motion_items:  # sound design follows the designed scenes: whooshes, ticks, risers, hits
        pl["cues"] = sorted(pl["cues"] + motion.sfx_cues(motion_items), key=lambda c: c["at"])
    director_doc = {**d.model_dump(), "provenance": provenance, "reference_evidence": evidence,
                    "profile": profile.id, "clips": [a["filename"] for a in clips]}
    db.table("edit_generations").update({"director": director_doc, "plan": pl}).eq("id", gid).execute()

    ctx.stage("render_base", 0.25, "Rendering cuts, camera moves, effects and transitions")
    base = project / "base.mp4"
    res = render.render_plan(pl, [asset_path(a) for a in clips], [a["analysis"].get("duration_s") for a in clips],
                             work, base, music_path=asset_path(music_asset) if music_asset else None,
                             voice_path=narration["wav"] if narration else None, quality=st.get("quality", "looks"))

    ctx.stage("qa", 0.6, "Measuring the result: frames, cuts vs beats, black/frozen frames, loudness")
    report = qa.check(base, pl)
    stills = storyboard_stills(base, pl, project)

    doc = overlay.timeline(rid, pl, d, st, g.get("brand_snapshot"), narration, project, motion_items,
                           [(a, asset_path(a)) for a in clips])
    doc["source"] = {"editId": gid}
    timeline.validate(doc)
    db.table("render_jobs").upsert({
        "id": rid, "organization_id": g["organization_id"], "project_id": g["project_id"],
        "created_by": g["created_by"], "job_id": ctx.id, "quality": st.get("quality", "looks"),
        "timeline": doc, "timeline_hash": timeline.timeline_hash(doc), "status": "rendering",
    }).execute()
    db.table("edit_generations").update({
        "render_id": rid, "status": "rendering", "qa": {**report, "storyboard": stills, "render": res},
    }).eq("id", gid).execute()

    if overlay.has_overlays(doc):
        result = run_render(Sub(ctx, 0.64, 0.99, {"render_id": rid}))
    else:
        ctx.stage("verify", 0.95, "Verifying the MP4")
        result = finalize_base(rid, g["organization_id"], base, doc, started)
    db.table("edit_generations").update({"status": "ready", "error": None}).eq("id", gid).execute()
    db.table("projects").update({"status": "video ready"}).eq("id", g["project_id"]).execute()
    (project / "director.json").write_text(json.dumps(director_doc, indent=1), encoding="utf-8")
    return {"generation_id": gid, "render_id": rid, "engine": provenance["engine"], "qa_pass": report.get("pass"), **{
        k: result.get(k) for k in ("duration_s", "width", "height", "size_bytes")}}
