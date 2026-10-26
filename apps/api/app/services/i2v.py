"""AI image-to-video for Mode B ("animate my photos"): a photo becomes a ~4 s clip with real motion (water, hair, light,
people), generated locally by LTX-Video 2B distilled in the isolated video environment (`video_worker.py`).

Like voice synthesis, it runs as a subprocess per job (the API never loads torch; VRAM is free afterwards) and frees the
local LLM first. Results are cached by photo + prompt. Every animated shot is recorded as AI-generated so the edit,
editor and publishing caption can disclose it (LTXV licence, Attachment A (e)).
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path


FPS, FRAMES = 24, 97  # 97 = 8k+1 frames ≈ 4.0 s


def python() -> Path:
    return Path(os.environ.get("VIDEO_PYTHON") or "D:/ReelStudio/video-venv/Scripts/python.exe")


def model_dir() -> Path:
    return Path(os.environ.get("I2V_MODEL_DIR") or "D:/ReelStudio/models/ltxv")


def available() -> bool:
    d = model_dir()
    return python().is_file() and (d / "ltxv-2b-0.9.8-distilled.safetensors").is_file() and (d / "text_encoder" / "model.safetensors").is_file()


def motion_prompt(analysis: dict, look: str = "") -> str:
    """LTX follows long, literal descriptions: the photo's own content (from ingest's vision tags) + gentle, realistic motion.
    Nothing is invented beyond what the vision model saw in the photo."""
    vlm = (analysis or {}).get("vlm") or {}
    subject = (vlm.get("subject") or "the scene in the photo").rstrip(".")
    setting = (vlm.get("setting") or "").rstrip(".")
    parts = [f"{subject}.", f"{setting}." if setting else "",
             "The scene comes alive with subtle, natural, realistic motion: gentle movement of people, fabric, hair, "
             "water, light and background, while the main subject stays the same.",
             "The camera slowly pushes in with a smooth cinematic move.",
             f"{look} look." if look else "", "High quality, sharp, consistent lighting, no text changes."]
    return " ".join(p for p in parts if p)


def animate(items: list[tuple[Path, str]], work: Path, portrait: bool = True, timeout_s: int = 3600) -> list[Path]:
    """[(image, prompt)] → mp4 paths (cached). Raises RuntimeError when the engine is missing or generation fails."""
    if not available():
        raise RuntimeError("AI photo animation is not installed on the processing machine")
    work.mkdir(parents=True, exist_ok=True)
    w, h = (448, 800) if portrait else (800, 448)
    outs, todo = [], []
    for i, (img, prompt) in enumerate(items):
        key = hashlib.sha256(Path(img).read_bytes() + f"|{prompt}|{w}x{h}".encode()).hexdigest()[:16]
        out = work / f"anim-{key}.mp4"
        outs.append(out)
        if not out.exists():
            todo.append({"image": str(img), "prompt": prompt, "out": str(out), "seed": i + 7})
    if todo:
        from app.services import llm

        llm.unload()
        job = work / "i2v-job.json"
        job.write_text(json.dumps({"model_dir": str(model_dir()), "items": todo, "width": w, "height": h,
                                   "frames": FRAMES, "fps": FPS}), encoding="utf-8")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"}
        r = subprocess.run([str(python()), str(Path(__file__).with_name("video_worker.py")), str(job)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout_s, env=env)
        if r.returncode or any(not Path(t["out"]).exists() for t in todo):
            raise RuntimeError("Photo animation failed: " + (r.stderr or r.stdout)[-600:])
    return outs


def clip_analysis(photo: dict, portrait: bool = True) -> dict:
    """Analysis for an animated photo so the planner treats it as footage: the whole clip is one usable moment."""
    dur = FRAMES / FPS
    w, h = (448, 800) if portrait else (800, 448)
    return {**{k: v for k, v in (photo or {}).items() if k in ("vlm", "focus", "brightness")}, "kind": "video",
            "duration_s": round(dur, 3), "fps": FPS, "width": w, "height": h, "has_audio": False, "ai_generated": True,
            "motion_mean": 0.6, "moments": [{"start_s": 0.15, "end_s": round(dur - 0.1, 3), "score": 0.75,
                                             "focus": (photo or {}).get("focus", [0.5, 0.5])}]}
