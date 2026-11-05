"""Voice dubbing of a clip, local and free (the approach of pyVideoTrans / VideoLingo, written for Reel Studio):

1. the clip's sentences are translated once by the local LLM (the same lines become the captions);
2. each line is spoken by a built-in Kokoro voice for that language (male/female), or by the user's own saved,
   consented voice profile (Chatterbox). Voices of other people in the video are never cloned;
3. each line is time-fitted into its original sentence's slot (gentle 0.9–1.45× tempo, never chipmunk-fast) and placed
   at that sentence's start, so the dub follows the speaker's rhythm; the original voice is replaced.
For more languages or multi-speaker cloned voices, VoiceStudio (AGPL, separate local app) can be added as an engine.
"""

import hashlib
import subprocess
import wave
from pathlib import Path

from app.services.rendering import translate

# Kokoro language code and (male, female) voices per supported language
KOKORO = {
    "en": ("en-us", "am_adam", "af_heart"), "hi": ("hi", "hm_omega", "hf_alpha"), "es": ("es", "em_alex", "ef_dora"),
    "fr": ("fr-fr", "ff_siwis", "ff_siwis"), "it": ("it", "im_nicola", "if_sara"), "pt": ("pt-br", "pm_alex", "pf_dora"),
    "ja": ("ja", "jm_kumo", "jf_alpha"), "zh": ("cmn", "zm_yunjian", "zf_xiaobei"),
}
LANGS = sorted(KOKORO)


def _speak(text: str, lang: str, voice: str, out: Path) -> None:
    if voice.startswith("profile:"):
        from app.services import voice_profiles

        voice_profiles.speak(voice.split(":", 1)[1], text, lang, out)
        return
    import os
    import sys

    from app.services.generation.narration import _cli

    code, male, female = KOKORO[lang]
    script = out.with_suffix(".txt")
    script.write_text(text, encoding="utf-8")
    env = {**os.environ, "HYPERFRAMES_PYTHON": sys.executable, "HYPERFRAMES_TELEMETRY": "0", "DO_NOT_TRACK": "1"}
    r = subprocess.run(_cli() + ["tts", "--text-file", str(script), "--voice", female if voice == "female" else male,
                                 "--lang", code, "--output", str(out), "--json"],
                       env=env, capture_output=True, text=True, encoding="utf-8", timeout=360)
    if r.returncode or not out.exists():
        raise RuntimeError("Local voice for dubbing failed: " + (r.stdout + r.stderr)[-500:])


def _seconds(wav: Path) -> float:
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def dub(words: list[dict], lang: str, voice: str, project: Path, duration: float) -> tuple[Path, list[dict]] | None:
    """(dub.wav in the project, translated caption words) for caption words on the composition clock; None if the
    language is unsupported or translation is unavailable."""
    if lang not in KOKORO and not voice.startswith("profile:"):
        return None
    groups = translate.sentences(words)
    lines = translate.translate_lines([" ".join(w["text"] for w in g) for g in groups], lang)
    if not lines:
        return None
    work = project / "dub"
    work.mkdir(parents=True, exist_ok=True)
    inputs, filters = [], []
    for i, (g, text) in enumerate(zip(groups, lines, strict=False)):
        if not text.strip():
            continue
        raw = work / f"line-{hashlib.sha1(f'{lang}|{voice}|{text}'.encode()).hexdigest()[:12]}.wav"
        if not raw.exists():
            _speak(text, lang, voice, raw)
        start = g[0]["start"]
        end = groups[i + 1][0]["start"] if i + 1 < len(groups) else duration
        slot = max(end - start - 0.05, 0.4)
        tempo = min(max(_seconds(raw) / slot, 0.9), 1.45)
        n = len(inputs) // 2  # each input is "-i path"
        inputs += ["-i", str(raw)]
        filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=mono,atempo={tempo:.3f},"
                       f"atrim=end={slot + 0.25:.3f},adelay={round(start * 1000)}|{round(start * 1000)}[d{n}]")
    if not inputs:
        return None
    k = len(filters)
    graph = ";".join(filters) + ";" + "".join(f"[d{i}]" for i in range(k)) + \
        f"amix=inputs={k}:normalize=0:duration=longest,apad=whole_dur={duration:.3f},atrim=end={duration:.3f}[out]"
    out = project / "dub.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000",
                    str(out)], check=True, capture_output=True, timeout=600)
    return out, translate.distribute(groups, lines)
