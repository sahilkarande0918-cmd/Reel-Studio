"""ingest job: analyse one Mode B upload so the director can reason about it.

clip/image → motion, sharpness, framing, best moments + thumbnail + a short local-VLM description of the subject
(model text, may be wrong); audio → tempo, beat grid, accents, drops; reference → reference style profile."""

import subprocess
from pathlib import Path

import cv2

from app.core.db import service_client
from app.core.storage import asset_dir, asset_path
from app.services import llm
from app.services.clips.analysis import analyze_clip, analyze_image
from app.services.music import beats
from app.services.reference.analyzer import analyze_reference
from app.workers.jobs import JobContext, Permanent

SUBJECT = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "the main visible subject in a few words"},
        "setting": {"type": "string", "description": "where it is, a few words"},
        "is_product": {"type": "boolean", "description": "a product is the hero of the frame"},
        "shot": {"type": "string", "enum": ["close-up", "medium", "wide", "screen", "text", "other"]},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
    },
    "required": ["subject", "setting", "is_product", "shot", "tags"],
}
LOOK = (
    "One frame from a raw clip a user uploaded for a short video edit. Describe only what is visible. "
    "Do not identify people or guess brand names that are not readable. Return JSON."
)


def thumbnail(src: Path, out: Path, t: float | None) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if t is not None:
        cmd += ["-ss", f"{max(t, 0):.2f}"]
    cmd += ["-i", str(src), "-frames:v", "1", "-vf", "scale=360:-2", str(out)]
    subprocess.run(cmd, check=True, timeout=120)


def ingest(asset: dict) -> dict:
    """Analysis dict for one asset (also used inline by the edit job when an ingest job has not run yet)."""
    p = asset_path(asset)
    d = asset_dir(asset["organization_id"], asset["id"])
    kind = asset["kind"]
    if kind == "audio":
        return beats.analyze(p)
    if kind == "reference":
        profile = analyze_reference(p, out_dir=d)
        thumbnail(p, d / "thumb.jpg", min(1.0, (asset.get("duration_s") or 2) / 2))
        return profile
    a = analyze_image(p) if kind == "image" else analyze_clip(p)
    best = max(a["moments"], key=lambda m: m["score"]) if a.get("moments") else None
    at = None if kind == "image" or not best else (best["start_s"] + best["end_s"]) / 2
    thumbnail(p, d / "thumb.jpg", at)
    img = cv2.imread(str(d / "thumb.jpg"))
    if img is not None:
        ok, jpg = cv2.imencode(".jpg", img)
        a["vlm"] = llm.look(jpg.tobytes(), LOOK, SUBJECT) if ok else None
    return a


def run_ingest(ctx: JobContext) -> dict:
    db = service_client()
    rows = db.table("media_assets").select("*").eq("id", ctx.payload["asset_id"]).limit(1).execute().data
    if not rows:
        raise Permanent("asset was deleted")
    asset = rows[0]
    db.table("media_assets").update({"status": "analyzing", "error": None}).eq("id", asset["id"]).execute()
    ctx.stage("analyze", 0.1, f"Analysing {asset['filename']}")
    try:
        analysis = ingest(asset)
    except Exception as e:
        db.table("media_assets").update({"status": "failed", "error": f"{type(e).__name__}: {e}"[:500]}).eq("id", asset["id"]).execute()
        raise
    db.table("media_assets").update({"status": "ready", "analysis": analysis}).eq("id", asset["id"]).execute()
    return {"asset_id": asset["id"], "kind": asset["kind"]}
