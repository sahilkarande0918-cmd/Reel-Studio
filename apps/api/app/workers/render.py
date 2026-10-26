"""render job: canonical timeline → Hyperframes project → `hyperframes render` → ffprobe-verified MP4
+ thumbnail. Progress comes from the CLI's structured `@hf-progress` lines."""

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.db import service_client
from app.core.storage import render_dir, source_path
from app.services import media
from app.services.generation.narration import _cli as hyperframes_command
from app.services.rendering import compose, sync, timeline
from app.workers.jobs import Cancelled, JobContext, Permanent

log = logging.getLogger(__name__)
ENV = {**os.environ, "HYPERFRAMES_TELEMETRY": "0", "DO_NOT_TRACK": "1"}
RENDER_SPAN = (0.06, 0.94)  # share of job progress covered by the CLI


def _update(render_id: str, **fields) -> None:
    service_client().table("render_jobs").update(fields).eq("id", render_id).execute()


def _link_source(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)  # same volume: no copy of a multi-GB recording
    except OSError:
        shutil.copyfile(src, dst)


STALL_S = 300  # no renderer output this long = hung (seen: 8 Chrome workers never starting under memory pressure)


def _workers() -> str:
    """8 capture workers measured fastest (111 s vs 123 s auto for a 28 s reel); with under 10 GB free RAM they could
    all hang at "Starting browsers", so the count drops to 4."""
    try:
        import ctypes

        class Mem(ctypes.Structure):
            _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                        ("avail", ctypes.c_ulonglong), ("pt", ctypes.c_ulonglong), ("pa", ctypes.c_ulonglong),
                        ("vt", ctypes.c_ulonglong), ("va", ctypes.c_ulonglong), ("ve", ctypes.c_ulonglong)]

        m = Mem(len=ctypes.sizeof(Mem))
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return "8" if m.avail >= 10 * 2**30 else "4"
    except (AttributeError, OSError):  # not Windows
        return "4"


def _render(ctx: JobContext, project: Path, quality: str) -> None:
    cmd = hyperframes_command() + ["render", "--quality", quality, "--video-frame-format", "png", "--workers", _workers()]
    cmd += ["--output", "out.mp4", "."]
    log_path = project / "render.log"
    with log_path.open("w", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            cmd,
            cwd=project,
            env=ENV,
            stdin=subprocess.DEVNULL,  # never the console: under a headless console Node/Chrome blocked on it forever
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        assert proc.stdout
        last = 0.0
        seen = [time.monotonic()]

        def watchdog() -> None:  # a hung renderer is killed so the job fails and retries instead of waiting forever
            while proc.poll() is None:
                if time.monotonic() - seen[0] > STALL_S:
                    logf.write(f"\n[reel-studio] no renderer output for {STALL_S} s: stopping the render\n")
                    logf.flush()
                    if os.name == "nt":  # the whole tree: a Chrome child holding the pipe kept the job waiting
                        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
                    proc.kill()
                    return
                time.sleep(5)

        threading.Thread(target=watchdog, daemon=True).start()
        try:
            for line in proc.stdout:
                seen[0] = time.monotonic()
                logf.write(line)
                if line.startswith("@hf-progress ") and time.monotonic() - last > 2:
                    pct = json.loads(line[len("@hf-progress ") :]).get("pct", 0)
                    ctx.progress(RENDER_SPAN[0] + (RENDER_SPAN[1] - RENDER_SPAN[0]) * pct / 100)
                    ctx.check_cancel()
                    last = time.monotonic()
        except Cancelled:
            proc.kill()
            raise
        if proc.wait() != 0:
            tail = log_path.read_text(encoding="utf-8")[-1500:]
            raise RuntimeError(f"hyperframes render exited {proc.returncode}: {tail}")


def fade_expression(doc: dict) -> str | None:
    """ffmpeg volume expression for editor audio fades, at composition time.
    ponytail: fades scale the whole mix at those moments (one audible source at a time in practice);
    per-source fades would need Hyperframes to animate element volume."""
    parts = []
    for item in (i for t in doc["tracks"] for i in t["items"] if i["type"] in ("video", "audio")):
        a, b = item["start"], item["start"] + item["duration"]
        if (f := item.get("fadeIn", 0)) > 0:
            parts.append(f"if(between(t,{a:.3f},{a + f:.3f}),(t-{a:.3f})/{f:.3f},1)")
        if (f := item.get("fadeOut", 0)) > 0:
            parts.append(f"if(between(t,{b - f:.3f},{b:.3f}),({b:.3f}-t)/{f:.3f},1)")
    return "*".join(parts) or None


def apply_fades(out: Path, doc: dict) -> None:
    expr = fade_expression(doc)
    if not expr:
        return
    tmp = out.with_name("faded.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-c:v", "copy", "-af",
                    f"volume='{expr}':eval=frame", "-c:a", "aac", "-b:a", "192k", str(tmp)], check=True, timeout=600)
    tmp.replace(out)


def peak_db(path: Path) -> float:
    """Loudest audio sample in dBFS (-inf for digital silence), measured by ffmpeg's volumedetect."""
    out = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-map", "0:a:0", "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", timeout=300).stderr
    m = re.search(r"max_volume: (-?inf|-?[\d.]+) dB", out)
    return float(m.group(1)) if m else float("-inf")


def expects_sound(doc: dict) -> bool:
    return any(i["type"] in ("audio", "video") and i.get("volume", 1) > 0 for t in doc["tracks"] for i in t["items"])


def verify(path: Path, expected_s: float, width: int, height: int, audible: bool = False) -> dict:
    """The output must be what the timeline asked for: size, duration (±0.1 s), H.264 + audio."""
    info = media.probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    dur = float(info["format"]["duration"])
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    problems = []
    if (v["width"], v["height"]) != (width, height):
        problems.append(f"size {v['width']}x{v['height']}")
    if abs(dur - expected_s) > 0.1:
        problems.append(f"duration {dur:.3f}s vs {expected_s:.3f}s")
    if v["codec_name"] != "h264" or not has_audio:
        problems.append(f"codec {v['codec_name']}, audio={has_audio}")
    # A narrated or recorded timeline must not export silent (e.g. media not found by the renderer).
    if audible and has_audio and (peak := peak_db(path)) < -45:
        problems.append(f"no audible sound (peak {peak} dB) although the timeline has narration/audio")
    if problems:
        raise Permanent("Rendered file failed verification: " + "; ".join(problems))
    return {"duration_s": dur, "width": v["width"], "height": v["height"], "fps": num / den}


def run_render(ctx: JobContext) -> dict:
    db = service_client()
    rid = ctx.payload["render_id"]
    render = (db.table("render_jobs").select("*").eq("id", rid).limit(1).execute().data or [None])[0]
    if not render:
        raise Permanent("render row not found")
    rec = (
        (
            db.table("source_recordings").select("*").eq("id", render["recording_id"]).limit(1).execute().data
            or [None]
        )[0]
        if render.get("recording_id")
        else None
    )
    if render.get("recording_id") and (not rec or not source_path(rec).exists()):
        raise Permanent("source recording is missing on this machine")
    doc = render["timeline"]
    try:
        timeline.validate(doc)
        _update(rid, status="rendering", error=None)
        started = time.monotonic()
        ctx.stage("compose", 0.02, "Compiling the timeline into a Hyperframes composition")
        project = render_dir(render["organization_id"], rid)
        compose.write_project(doc, project)
        if rec:
            _link_source(source_path(rec), project / doc["assets"]["source"]["src"])
        for asset in doc["assets"].values():
            if asset["kind"] in ("video", "audio", "image") and not (project / asset["src"]).is_file():
                raise Permanent(f"Render asset is missing: {asset['id']}")

        ctx.stage("lint", 0.04, "Checking the composition")
        lint = subprocess.run(
            hyperframes_command() + ["lint", "--json", "."],
            cwd=project,
            env=ENV,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        try:
            errors = json.loads(lint.stdout).get("errorCount", 0)
        except json.JSONDecodeError:
            errors = 0 if lint.returncode == 0 else 1
        if errors:
            raise Permanent(f"composition lint failed: {lint.stdout[-1500:]}")

        ctx.stage("render", RENDER_SPAN[0], "Rendering frames")
        _render(ctx, project, render["quality"])

        ctx.stage("verify", 0.95, "Verifying the MP4")
        out = project / "out.mp4"
        apply_fades(out, doc)
        meta = verify(out, doc["duration"], doc["width"], doc["height"], audible=expects_sound(doc))
        thumb = project / "thumb.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{min(doc['duration'] / 3, 10):.2f}",
                "-i",
                str(out),
                "-frames:v",
                "1",
                "-vf",
                "scale=540:-2",
                str(thumb),
            ],
            check=True,
            timeout=120,
        )
        data_dir = get_settings().data_dir
        fields = {
            **meta,
            "status": "ready",
            "output_path": out.relative_to(data_dir).as_posix(),
            "thumbnail_path": thumb.relative_to(data_dir).as_posix(),
            "size_bytes": out.stat().st_size,
            "render_s": round(time.monotonic() - started, 1),
        }
        _update(rid, **fields)
        ctx.stage("sync_check", 0.98, "Checking caption and audio timing")
        try:
            videos = [i for t in doc["tracks"] for i in t["items"] if i["type"] == "video"]
            timing = (
                sync.check(source_path(rec), out, doc)
                if rec and len(videos) == 1
                else {
                    "ok": None,
                    "note": "Recording correlation check does not apply to generated/multiclip audio",
                }
            )
        except Exception as e:  # noqa: BLE001 — a failed check is reported, never discards a good render
            log.warning("timing check failed: %s", e)
            timing = {"ok": None, "error": f"{type(e).__name__}: {e}"[:300]}
        return {"render_id": rid, **fields, "timing": timing}
    except Cancelled:
        _update(rid, status="cancelled")
        raise
    except Exception as e:
        _update(rid, status="failed", error=f"{type(e).__name__}: {e}"[:2000])
        raise
