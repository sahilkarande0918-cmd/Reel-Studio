"""Headless Blender renderer for genuine 3D shots (renderer router: only when a scene needs real 3D).

The worker runs Blender with `--factory-startup` and our own fixed script (`blender_scene.py`); requests carry only
validated data — a template id, short texts, hex colours, timing, size and optionally an image the worker copies in.
No user-supplied Python ever reaches Blender. When Blender is not installed the router substitutes the closest
Hyperframes template and records it.

Blender path: BLENDER_PATH, else `blender` on PATH, else the Microsoft Store execution alias (blender-launcher.exe,
which returns before Blender finishes — so completion is detected by the done/error file the script writes).
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SCRIPT = Path(__file__).with_name("blender_scene.py")
HEX = r"^#[0-9a-fA-F]{6}$"
TEMPLATES = {
    "text_3d": "extruded 3D title rising onto a reflective floor, orbiting camera, accent rim light",
    "product_turntable": "an uploaded product/screenshot on a bevelled 3D card turning on a glowing plinth",
}


class Scene3D(BaseModel):
    template: Literal["text_3d", "product_turntable"]
    text: str = Field(default="", max_length=40)
    subtitle: str = Field(default="", max_length=60)
    accent: str = Field(default="#C8E06B", pattern=HEX)
    text_color: str = Field(default="#FCF9F4", pattern=HEX)
    background: str = Field(default="#141810", pattern=HEX)
    duration: float = Field(default=4.0, ge=1.0, le=8.0)
    orbit: float = Field(default=30, ge=0, le=90)
    fps: Literal[24, 30] = 30
    width: int = Field(default=1080, ge=256, le=1920)
    height: int = Field(default=1920, ge=256, le=1920)
    portrait: bool = True


def executable() -> list[str] | None:
    env = os.environ.get("BLENDER_PATH")
    if env and Path(env).is_file():
        return [env]
    if found := shutil.which("blender"):
        return [found]
    alias = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "blender-launcher.exe"
    return [str(alias)] if alias.is_file() else None


def available() -> bool:
    return executable() is not None


def render(scene: Scene3D, work: Path, out_mp4: Path, image: Path | None = None, timeout_s: int = 900) -> dict:
    """Renders the validated scene to an H.264 MP4 (no audio). Raises RuntimeError with Blender's traceback."""
    exe = executable()
    if not exe:
        raise RuntimeError("Blender is not installed on the processing machine")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    params = {**scene.model_dump(), "out_dir": str(work)}
    if image:
        local = work / f"image{image.suffix.lower()}"
        shutil.copyfile(image, local)
        params["image"] = str(local)
    (work / "params.json").write_text(json.dumps(params), encoding="utf-8")
    started = time.monotonic()
    proc = subprocess.Popen([*exe, "-b", "--factory-startup", "--python", str(SCRIPT), "--", str(work / "params.json")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while time.monotonic() - started < timeout_s:
        if (work / "error.json").exists():
            raise RuntimeError("Blender scene failed: " + json.loads((work / "error.json").read_text())["error"])
        if (work / "done.json").exists():
            break
        time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError(f"Blender did not finish within {timeout_s} s")
    info = json.loads((work / "done.json").read_text())
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(scene.fps), "-i", str(work / "f_%04d.png"),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(out_mp4)],
                       capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    return {**info, "render_s": round(time.monotonic() - started, 1), "output": str(out_mp4)}
