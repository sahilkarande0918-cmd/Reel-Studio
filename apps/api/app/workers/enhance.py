"""enhance job: a finished reel → the same edit in 4K (2160×3840 for 9:16), AI-upscaled, upload-grade bitrate.

CapCut-style "Enhance quality → UHD" done locally and free:
1. base: the reel's picture without any text (crops, speaker framing, zooms, transitions, colour, B-roll and the final
   audio) rendered at the source's own pixel density (a 720p source gives 404×720, never an already-stretched image),
   capped at a quarter of the 4K size;
2. Real-ESRGAN (realesr-general-x4v3 + denoise blend, BSD-3) ×4 on the GPU (upscale_worker.py, torch env);
3. captions, hook titles, progress bar and emojis drawn fresh at 4K (vector text, not upscaled pixels), optional
   "vivid" look (CapCut's "HDR" look: a little contrast and colour; the file stays SDR BT.709 — no fake HDR), light
   adaptive sharpening, H.264 High ~45 Mbps (YouTube's 4K SDR recommendation), AAC.
A reel the fast renderer cannot rebuild (intro/outro cards, logos) is upscaled as it is, text included.
"""

import copy
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from app.core.db import service_client
from app.core.storage import render_dir, source_path
from app.services import i2v, media
from app.services.rendering import fast
from app.workers import render as rw
from app.workers.jobs import Cancelled, JobContext, Permanent

MODELS = Path(os.environ.get("UPSCALE_MODEL_DIR", r"D:\ReelStudio\models\realesrgan"))
WEIGHTS = [MODELS / "realesr-general-x4v3.pth", MODELS / "realesr-general-wdn-x4v3.pth"]
WORKER = Path(__file__).parents[1] / "services" / "upscale_worker.py"
ENCODE_4K = ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", "16", "-b:v", "45M",
             "-maxrate", "60M", "-bufsize", "120M", "-profile:v", "high", "-pix_fmt", "yuv420p"]
DENOISE = 0.75  # 1 = no denoising; 0.5 (Real-ESRGAN's default) looked waxy on faces in compressed YouTube footage
COLOR_TAGS = ["-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def available() -> str | None:
    """None when 4K enhancement can run on this engine; otherwise why not."""
    if not i2v.python().is_file():
        return "the local AI video environment (VIDEO_PYTHON) is not installed"
    if not all(w.is_file() for w in WEIGHTS):
        return f"Real-ESRGAN weights are missing in {MODELS}"
    return None


def _even(v: float) -> int:
    return max(2, int(round(v)) // 2 * 2)


def target_size(w: int, h: int) -> tuple[int, int]:
    """4K class: twice the reel's size (1080×1920 → 2160×3840, 1080×1080 → 2160×2160, 1920×1080 → 3840×2160)."""
    return w * 2, h * 2


def base_doc(doc: dict, src_h: int, src_fps: float | None = None) -> dict:
    """The reel's picture without text, at the source's native pixel density (≤ a quarter of the 4K size)."""
    W, H = doc["width"], doc["height"]
    crops = [k["crop_height"] for t in doc["tracks"] for i in t["items"] if i["type"] == "video"
             for k in i.get("cropKeyframes", []) if k.get("layout") == "crop"]
    native = max(crops) / H if crops else src_h / H
    s = min(native, 2 * H / 4 / H, 1.0)  # 4K target is 2×H; the ×4 model needs a quarter of it at most
    b = copy.deepcopy(doc)
    b["width"], b["height"] = _even(W * s), _even(H * s)
    if src_fps and src_fps < doc["fps"] - 0.5:  # a 24 fps film in a 30 fps reel: upscale only the real frames
        b["fps"] = round(src_fps, 3)
    for t in b["tracks"]:
        t["items"] = [i for i in t["items"] if i["type"] == "video"]
    rs = b.setdefault("renderSettings", {})
    rs["emojis"], rs["progressBar"] = [], False
    return b


def overlay_args(doc: dict, project: Path, W: int, H: int, vivid: bool) -> list[str]:
    """FFmpeg arguments after the upscaled picture (input 0): the reel's text and emojis at 4K, look, encode."""
    (project / "captions.ass").write_text(fast.ass(doc), encoding="utf-8")  # PlayRes 1080×1920: libass scales it
    fdir = project / "fonts"
    fdir.mkdir(exist_ok=True)
    for f in fast.fonts_dir().iterdir():
        shutil.copyfile(f, fdir / f.name)
    look = "eq=contrast=1.06:saturation=1.14:gamma=0.98," if vivid else ""
    g = f"[0:v]fps={doc['fps']},{look}cas=strength=0.4,subtitles=captions.ass:fontsdir=fonts"
    args = ["-i", "base/out.mp4"]
    stickers = []
    for e in (doc.get("renderSettings") or {}).get("emojis") or []:
        from app.services.rendering import emoji

        if (png := emoji.png(e["code"])) is not None:
            stickers.append((png, e))
    k = H / doc["height"]
    size = round(min(W, H) * 0.15)
    cy = max(0, round(doc["captionStyle"]["safeTop"] * k - size * 0.9))
    cur = "v0"
    g += f"[{cur}]"
    for n, (png, e) in enumerate(stickers):
        shutil.copyfile(png, project / f"emoji{n}.png")
        args += ["-loop", "1", "-t", f"{doc['duration']:.3f}", "-i", f"emoji{n}.png"]
        a, b = e["at"], e["at"] + e["duration"]
        g += (f";[{n + 2}:v]format=rgba,scale={size}:{size},fade=t=in:st={a:.3f}:d=0.15:alpha=1,"
              f"fade=t=out:st={max(b - 0.2, a):.3f}:d=0.2:alpha=1[em{n}]")
        g += f";[{cur}][em{n}]overlay=(W-w)/2:{cy}:enable='between(t,{a:.3f},{b:.3f})'[s{n}]"
        cur = f"s{n}"
    g += f";[{cur}]format=yuv420p[vout]"
    return [*args, "-filter_complex", g, "-map", "[vout]", "-map", "1:a?", *ENCODE_4K, *COLOR_TAGS,
            "-c:a", "copy", "-t", f"{doc['duration']:.3f}", "-movflags", "+faststart", "out.mp4"]


def upscale(ctx: JobContext, job: dict, project: Path, span: tuple[float, float]) -> dict:
    """Run the GPU worker; its "progress done total fps" lines drive the job's progress."""
    (project / "upscale.json").write_text(json.dumps(job), encoding="utf-8")
    proc = subprocess.Popen([str(i2v.python()), str(WORKER), str(project / "upscale.json")], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    result: dict = {}
    assert proc.stdout
    for line in proc.stdout:
        if line.startswith("progress "):
            _, done, total, fps = line.split()
            ctx.progress(span[0] + (span[1] - span[0]) * int(done) / max(int(total), 1))
            try:
                ctx.check_cancel()
            except Cancelled:
                proc.kill()
                raise
        elif line.startswith("{"):
            result = json.loads(line)
    err = proc.stderr.read() if proc.stderr else ""
    if proc.wait() != 0:
        raise RuntimeError(f"AI upscale failed: {err[-1500:]}")
    return result


def run_enhance(ctx: JobContext) -> dict:
    db = service_client()
    rid = ctx.payload["render_id"]
    render = (db.table("render_jobs").select("*").eq("id", rid).limit(1).execute().data or [None])[0]
    if not render or not render.get("parent_render_id"):
        raise Permanent("4K render row not found")
    parent = (db.table("render_jobs").select("*").eq("id", render["parent_render_id"]).limit(1).execute().data or [None])[0]
    if not parent or parent["status"] != "ready":
        raise Permanent("the original reel is not ready")
    if why := available():
        raise Permanent(f"4K enhancement is unavailable on this engine: {why}")
    rec = (db.table("source_recordings").select("*").eq("id", parent["recording_id"]).limit(1).execute().data
           or [None])[0] if parent.get("recording_id") else None
    doc = parent["timeline"]
    W4, H4 = target_size(doc["width"], doc["height"])
    project = render_dir(render["organization_id"], rid)
    pdir = render_dir(parent["organization_id"], parent["id"])
    started = time.monotonic()
    try:
        rw._update(rid, status="rendering", error=None)
        rebuild = rec is not None and source_path(rec).exists() and fast.supported(doc) is None
        base = project / "base"
        base.mkdir(exist_ok=True)
        if rebuild:
            ctx.stage("base", 0.03, "Rebuilding the reel's picture at the source's full detail (no text)")
            rs = doc.get("renderSettings") or {}
            for name in [rs.get("dubAudio"), *[c["src"] for c in rs.get("brollClips") or []]]:
                if name and (pdir / name).is_file() and not (base / name).exists():
                    (base / name).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(pdir / name, base / name)
            vs = next(x for x in media.probe(source_path(rec))["streams"] if x["codec_type"] == "video")
            num, den = (int(x) for x in vs["r_frame_rate"].split("/"))
            b = base_doc(doc, rec["height"], num / max(den, 1))
            try:
                fast.render(b, source_path(rec), base, enhance_audio=ctx.payload.get("enhance_audio", True), master=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"ffmpeg base render failed: {(e.stderr or b'').decode('utf-8', 'replace')[-1500:]}") from e
            encode = overlay_args(doc, project, W4, H4, bool(ctx.payload.get("vivid")))
        else:  # text is already in the picture: upscale the finished reel as it is
            ctx.stage("base", 0.03, "Preparing the finished reel for upscaling")
            bw, bh = _even(W4 / 4), _even(H4 / 4)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pdir / "out.mp4"), "-vf",
                            f"scale={bw}:{bh}:flags=lanczos", "-c:v", "libx264", "-crf", "12", "-preset", "veryfast",
                            "-c:a", "copy", str(base / "out.mp4")], check=True, capture_output=True, timeout=1800)
            look = "eq=contrast=1.06:saturation=1.14:gamma=0.98," if ctx.payload.get("vivid") else ""
            encode = ["-i", "base/out.mp4", "-filter_complex", f"[0:v]{look}cas=strength=0.4,format=yuv420p[vout]",
                      "-map", "[vout]", "-map", "1:a?", *ENCODE_4K, *COLOR_TAGS, "-c:a", "copy",
                      "-t", f"{doc['duration']:.3f}", "-movflags", "+faststart", "out.mp4"]
        ctx.stage("upscale", 0.1, "AI upscaling every frame to 4K on the GPU (Real-ESRGAN)")
        base_fps = b["fps"] if rebuild else doc["fps"]
        stats = upscale(ctx, {"input": str(base / "out.mp4"), "width": W4, "height": H4, "fps": base_fps,
                              "models": [str(w) for w in WEIGHTS], "denoise": DENOISE, "encode": encode,
                              "cwd": str(project)}, project, (0.1, 0.93))
        shutil.rmtree(base, ignore_errors=True)  # the master is only an intermediate
        out = rw._finish(ctx, rid, render, rec, {**doc, "width": W4, "height": H4}, project, started, "enhance-4k")
        return {**out, "upscale": stats, "rebuilt": rebuild}
    except Cancelled:
        rw._update(rid, status="cancelled")
        raise
    except Exception as e:
        rw._update(rid, status="failed", error=f"{type(e).__name__}: {e}"[:2000])
        raise
