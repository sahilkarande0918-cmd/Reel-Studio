"""Narration for Mode B: text → speech WAV + measured word timing (for captions and ducking).

Voices: `kokoro:<id>` (built-in local Kokoro voices) or `profile:<uuid>` (a saved, consented voice profile — see
voice_profiles.py). Word times are measured by ASR on the generated audio and aligned to the script, never invented."""

import hashlib
import json
import math
from pathlib import Path

import soundfile as sf

from app.services.generation.narration import _synthesize, align_words
from app.services.transcription import whisper

KOKORO = ("af_heart", "af_bella", "am_adam")


def synthesize(text: str, voice: str, out_dir: Path, language: str = "en") -> Path:
    digest = hashlib.sha256(f"{voice}|{language}|{text}".encode()).hexdigest()[:16]
    wav = out_dir / f"narration-{digest}.wav"
    if wav.exists():
        return wav
    kind, _, vid = voice.partition(":")
    if kind == "kokoro" and vid in KOKORO:
        _synthesize(text, vid, wav)
    elif kind == "profile":
        from app.services import voice_profiles

        voice_profiles.speak(vid, text, language, wav)
    else:
        raise ValueError(f"unknown voice {voice}")
    return wav


def narrate(text: str, voice: str, out_dir: Path, language: str = "en") -> tuple[Path, float, list[dict]]:
    """(wav, duration, words with start/end on the narration clock)."""
    wav = synthesize(text, voice, out_dir, language)
    info = sf.info(str(wav))
    dur = info.frames / info.samplerate
    if not math.isfinite(dur) or not 0 < dur <= 120:
        raise ValueError("narration audio duration is invalid")
    cache = wav.with_suffix(".words.json")
    if cache.exists():
        measured = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            measured = whisper.transcribe(wav, hotwords=text[:200], language=None if language == "hinglish" else language[:2]).words
        finally:
            whisper.unload()
        cache.write_text(json.dumps(measured), encoding="utf-8")
    return wav, dur, align_words(text, measured, dur)
