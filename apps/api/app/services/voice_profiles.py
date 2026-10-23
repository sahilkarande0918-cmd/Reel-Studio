"""Consented voice profiles: sample validation, storage and synthesis through the isolated voice environment.

Synthesis runs `voice_worker.py` in a separate Python (torch + Chatterbox Multilingual, MIT) as a subprocess per job, so
the API/worker process never loads torch and the GPU is free again afterwards. Chatterbox embeds Resemble's Perth
watermark in generated audio; the worker reports whether it is detectable (synthetic speech identification).
Quality varies with the sample: we never promise an identical copy of a voice.
"""

import json
import os
import re
import subprocess
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from app.core.config import get_settings

CONSENT = ("I confirm this recording is my own voice, or I have the speaker's explicit permission, and I authorise "
           "Reel Studio to create a synthetic voice from it for my own videos.")
WORKER = Path(__file__).with_name("voice_worker.py")
LANGS = {"en": "en", "hi": "hi", "hinglish": "hi"}  # Roman-script Hinglish is read with the Hindi model (tested)


def voice_dir(org_id: str, vid: str) -> Path:
    d = get_settings().data_dir / "orgs" / str(uuid.UUID(org_id)) / "voices" / str(uuid.UUID(vid))
    d.mkdir(parents=True, exist_ok=True)
    return d


def python() -> Path:
    return Path(os.environ.get("VOICE_PYTHON") or Path(os.environ.get("LOCALAPPDATA", "")) / "reel-studio" / "voice-venv" / "Scripts" / "python.exe")


def available() -> bool:
    return python().is_file()


def normalise(src: Path, dst: Path) -> None:
    """Any audio/video upload → 24 kHz mono WAV, at most 90 s."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "24000", "-t", "90", str(dst)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode or not dst.exists():
        raise ValueError("The file has no readable audio")


def quality(wav: Path) -> dict:
    """Objective checks on the sample (not a guarantee of clone quality)."""
    y, sr = sf.read(str(wav), dtype="float32")
    dur = len(y) / sr
    frames = y[: len(y) // 480 * 480].reshape(-1, 480)
    e = 10 * np.log10(np.mean(frames**2, axis=1) + 1e-10)
    floor, loud = float(np.percentile(e, 10)), float(np.percentile(e, 95))
    rms = float(10 * np.log10(np.mean(y**2) + 1e-10))
    out = {
        "seconds": round(dur, 1),
        "rms_dbfs": round(rms, 1),
        "clipped_pct": round(float(np.mean(np.abs(y) > 0.99) * 100), 3),
        "snr_db": round(loud - floor, 1),
        "speech_pct": round(float(np.mean(e > floor + 12) * 100), 1),
    }
    problems = []
    if dur < 8:
        problems.append("Record at least 8 seconds of speech (10–30 s works best).")
    if rms < -38:
        problems.append("The recording is too quiet; speak closer to the microphone.")
    if out["clipped_pct"] > 0.5:
        problems.append("The recording is distorted (clipping); lower the input volume.")
    if out["snr_db"] < 18:
        problems.append("Too much background noise; record in a quieter room.")
    if out["speech_pct"] < 35:
        problems.append("Mostly silence; read continuously for the whole sample.")
    out["problems"] = problems
    out["ok"] = not problems
    return out


def apply_pronunciations(text: str, rules: dict[str, str]) -> str:
    for term, spoken in sorted(rules.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)", spoken, text, flags=re.IGNORECASE)
    return text


def synthesize(sample: Path, items: list[dict], work: Path, timeout_s: int = 900) -> list[dict]:
    """items: [{"text", "language", "out"}] → [{"out", "seconds", "watermarked"}]. Frees the local LLM's VRAM first."""
    if not available():
        raise RuntimeError("The voice engine is not installed on the processing machine")
    from app.services import llm

    llm.unload()
    work.mkdir(parents=True, exist_ok=True)
    job = work / f"job-{uuid.uuid4().hex[:8]}.json"
    job.write_text(json.dumps({"sample": str(sample), "items": [{**i, "language": LANGS.get(i.get("language", "en"), "en")} for i in items]},
                              ensure_ascii=False), encoding="utf-8")
    env = {**os.environ, "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONIOENCODING": "utf-8", "HF_HUB_DISABLE_SYMLINKS_WARNING": "1"}
    r = subprocess.run([str(python()), str(WORKER), str(job)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout_s, env=env)
    result = job.parent / "result.json"
    if r.returncode or not result.exists():
        raise RuntimeError("Voice synthesis failed: " + (r.stderr or r.stdout)[-800:])
    data = json.loads(result.read_text(encoding="utf-8"))
    result.unlink()
    return data["items"]


def speak(vid: str, text: str, language: str, out: Path) -> None:
    """Narration with a saved profile (used by services/voice.py for Mode A/B)."""
    from app.core.db import service_client

    rows = service_client().table("voice_profiles").select("*").eq("id", vid).limit(1).execute().data
    if not rows or rows[0]["status"] != "ready":
        raise RuntimeError("Voice profile not found or not ready")
    p = rows[0]
    sample = voice_dir(p["organization_id"], p["id"]) / "sample.wav"
    synthesize(sample, [{"text": apply_pronunciations(text, p.get("pronunciations") or {}), "language": language, "out": str(out)}],
               out.parent)
