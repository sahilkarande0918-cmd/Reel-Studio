"""Local Kokoro narration and ASR-measured word timing, cached per scene."""

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import soundfile as sf

from app.services.generation.models import Storyboard, TopicRequest
from app.services.rendering.timeline import is_code
from app.services.transcription import whisper


@dataclass
class NarratedScene:
    audio_path: Path
    duration_s: float
    words: list[dict]


def align_words(script: str, measured: list[dict], duration_s: float) -> list[dict]:
    """Correct ASR orthography against known narration, retaining only measured time boundaries.

    One written token may merge several measured tokens (e.g. XML -> X M L). Missing words or
    many-to-one recognition are rejected; inventing evenly spaced word timestamps is forbidden.
    """
    expected = script.split()
    normalize = lambda word: re.sub(r"[^\w]", "", word).casefold()  # noqa: E731
    def plausible(w: dict) -> bool:  # zero-length or out-of-range words are recogniser hallucinations
        s, e = float(w["start_s"]), float(w["end_s"])
        return math.isfinite(s + e) and 0 <= s < e <= duration_s + .05
    detected = [w for w in measured if str(w.get("raw_text", "")).strip() and plausible(w)]
    if not expected or not detected:
        raise ValueError("Could not align narration: no measured words")
    matcher = SequenceMatcher(None, [normalize(w) for w in expected],
                              [normalize(w["raw_text"]) for w in detected], autojunk=False)
    # (text, start, end) with None times for script words the recogniser missed
    spans: list[list] = []
    measured_words = 0
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == "insert":
            continue  # extra recognised words (e.g. a stray "forward") are not in the script: drop them
        if tag == "delete":
            spans += [[expected[k], None, None] for k in range(a, b)]
            continue
        if b - a == d - c:  # equal, or one-for-one corrections such as "jaison" -> JSON
            spans += [[expected[a + k], float(detected[c + k]["start_s"]), float(detected[c + k]["end_s"])]
                      for k in range(b - a)]
        else:  # e.g. XML heard as "X M L": share the measured span by written length
            lo, hi = float(detected[c]["start_s"]), float(detected[d - 1]["end_s"])
            weights = [len(expected[k]) + 1 for k in range(a, b)]
            t = lo
            for k, wgt in zip(range(a, b), weights, strict=True):
                step = (hi - lo) * wgt / sum(weights)
                spans.append([expected[k], t, t + step])
                t += step
        measured_words += b - a
    # ponytail: a missed word takes the measured gap between its neighbours (bounded, never the whole
    # scene); scenes where the recogniser lost >15 % of the script are rejected instead.
    if measured_words / len(expected) < 0.85:
        raise ValueError("Could not align narration to measured speech; too many words were not recognised")
    i = 0
    while i < len(spans):
        if spans[i][1] is not None:
            i += 1
            continue
        j = i
        while j < len(spans) and spans[j][1] is None:
            j += 1
        lo = spans[i - 1][2] if i else 0.0
        hi = spans[j][1] if j < len(spans) else duration_s
        width = max(hi - lo, 0.05 * (j - i)) / (j - i)
        for k in range(i, j):
            spans[k][1], spans[k][2] = lo + width * (k - i), lo + width * (k - i + 1)
        i = j
    result, prev_end = [], 0.0
    for text, start, end in spans:
        start = max(start, prev_end - .02, 0.0)
        end = min(max(end, start + .05), duration_s)
        if end <= start:
            raise ValueError("Invalid measured speech alignment times")
        result.append({"text": text, "start": round(start, 3), "end": round(end, 3), "isCode": is_code(text)})
        prev_end = end
    return result


def _cli() -> list[str]:
    """Prefer the pinned locally cached CLI; never fetch packages while running a job."""
    override = os.environ.get("HYPERFRAMES_CLI")
    candidates = [Path(override)] if override else []
    caches = [Path.home() / "AppData/Local/npm-cache/_npx", Path.home() / ".npm/_npx"]
    for cache in caches:
        if cache.is_dir():
            candidates.extend(cache.glob("*/node_modules/hyperframes/bin/hyperframes.mjs"))
    node = shutil.which("node")
    for path in candidates:
        if path.is_file() and node:
            package = path.parent.parent / "package.json"
            if package.is_file() and json.loads(package.read_text())["version"] == "0.8.164":
                return [node, str(path)]
    raise RuntimeError("Local Hyperframes 0.8.164 CLI missing; install it before generating narration")


def _synthesize(text: str, voice: str, output: Path) -> None:
    script = output.with_suffix(".txt")
    script.write_text(text, encoding="utf-8")
    tmp = output.with_suffix(".tmp.wav")
    env = {**os.environ, "HYPERFRAMES_PYTHON": sys.executable,
           "HYPERFRAMES_TELEMETRY": "0", "DO_NOT_TRACK": "1", "ORT_DISABLE_TELEMETRY": "1"}
    result = subprocess.run(_cli() + ["tts", "--text-file", str(script), "--voice", voice,
                                     "--lang", "en-us", "--output", str(tmp), "--json"],
                            env=env, capture_output=True, text=True, encoding="utf-8", timeout=360)
    if result.returncode or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Local Kokoro narration failed: " + (result.stdout + result.stderr)[-1000:])
    tmp.replace(output)


def synthesize_narration(storyboard: Storyboard, request: TopicRequest | dict, output_dir: Path,
                        on_progress: Callable[[float], None] | None = None) -> list[NarratedScene]:
    request = TopicRequest.model_validate(request)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = []
    try:
        for idx, scene in enumerate(storyboard.scenes):
            digest = hashlib.sha256((scene.narration + request.voice + request.language).encode()).hexdigest()[:16]
            audio = output_dir / f"scene-{idx}-{digest}.wav"
            cache = audio.with_suffix(".words.json")
            if not audio.exists():
                _synthesize(scene.narration, request.voice, audio)
            info = sf.info(str(audio))
            duration = info.frames / info.samplerate
            if not math.isfinite(duration) or not 0 < duration <= 90:
                raise ValueError("Narration audio duration is invalid")
            if cache.exists():
                measured = json.loads(cache.read_text(encoding="utf-8"))
            else:
                measured = whisper.transcribe(audio, hotwords=scene.narration, language="en").words
                tmp = cache.with_suffix(".tmp.json")
                tmp.write_text(json.dumps(measured), encoding="utf-8")
                tmp.replace(cache)
            words = align_words(scene.narration, measured, duration)
            result.append(NarratedScene(audio, duration, words))
            if on_progress:
                on_progress((idx + 1) / len(storyboard.scenes))
    finally:
        whisper.unload()
    return result

