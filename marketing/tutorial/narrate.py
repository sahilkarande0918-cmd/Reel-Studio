"""Tutorial narration: local Kokoro TTS (via the Hyperframes CLI, same as Mode B) + faster-whisper word timings.

Run from apps/api with the project venv:
    python ../../marketing/tutorial/narrate.py
Writes marketing/tutorial/build/narration.json and scene-*.wav (cached by text).
"""

import hashlib
import json
import sys
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
from app.services.generation.narration import _synthesize, align_words  # noqa: E402
from app.services.transcription import whisper  # noqa: E402

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"


def main() -> None:
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    BUILD.mkdir(exist_ok=True)
    out = []
    try:
        for scene in script["scenes"]:
            digest = hashlib.sha256((scene["text"] + script["voice"]).encode()).hexdigest()[:10]
            wav = BUILD / f"scene-{scene['id']}-{digest}.wav"
            cache = wav.with_suffix(".words.json")
            if not wav.exists():
                _synthesize(scene["text"], script["voice"], wav)
            info = sf.info(str(wav))
            duration = info.frames / info.samplerate
            if not cache.exists():
                measured = whisper.transcribe(wav, hotwords=scene["text"], language="en").words
                cache.write_text(json.dumps(measured), encoding="utf-8")
            words = align_words(scene["text"], json.loads(cache.read_text(encoding="utf-8")), duration)
            out.append({**scene, "audio": wav.name, "audio_s": round(duration, 3), "words": words})
            print(f"{scene['id']:<11} {duration:5.2f} s  {len(words)} words")
    finally:
        whisper.unload()
    (BUILD / "narration.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
