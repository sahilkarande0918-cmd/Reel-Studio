"""Sound for an edit, rendered separately from the picture and muxed at the end (no A/V drift).

- Synthesized SFX (numpy, royalty-free by construction): whoosh (peak at a known offset so it never lands inside a
  word), impact, riser, tick. `at` is the moment the effect should hit; a whoosh is placed so its PEAK is at `at`.
- `mix`: music (trimmed, faded, ducked ~6 dB under voice with a sidechain compressor), voice, SFX (≤ +3 dB over voice
  by default gains) → two-pass loudnorm to −14 LUFS integrated, −1.5 dBTP.
- `mux`: copy the picture, encode AAC 48 kHz, shortest.
"""

import json
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 48000


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1.0) * np.exp(-t / decay)


def whoosh(length: float = 0.6, peak_at: float = 0.45, seed: int = 3) -> np.ndarray:
    n = int(length * SR)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n)
    t = np.arange(n) / SR
    # brightness sweeps up into the peak: running mean with a shrinking window ≈ rising low-pass
    out = np.empty(n)
    for i in range(0, n, 512):
        k = int(2 + 40 * (1 - min(t[i] / peak_at, 1)))
        seg = noise[i : i + 512 + k]
        out[i : i + 512] = np.convolve(seg, np.ones(k) / k, mode="same")[: len(out[i : i + 512])]
    env = np.where(t < peak_at, (t / peak_at) ** 2, np.exp(-(t - peak_at) / 0.06))
    return out * env * 0.5


def impact(length: float = 0.7) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t * 25)) / SR) * _env(n, 0.001, 0.25)
    crack = np.random.default_rng(5).standard_normal(n) * _env(n, 0.0005, 0.03) * 0.5
    return (body + crack) * 0.8


def riser(length: float = 1.5) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    f = 200 + 1800 * (t / length) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    noise = np.random.default_rng(9).standard_normal(n) * 0.3
    return (tone * 0.4 + noise) * (t / length) ** 2 * 0.35


def tick(length: float = 0.08) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * _env(n, 0.0005, 0.01) * 0.4


SFX = {"whoosh": (whoosh, 0.45), "impact": (impact, 0.0), "riser": (riser, 1.5), "tick": (tick, 0.0)}


def write_wav(path: Path, y: np.ndarray, sr: int = SR) -> Path:
    y = np.clip(y, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    return path


@dataclass
class Cue:
    kind: str  # whoosh | impact | riser | tick
    at: float  # when it should hit (peak for whoosh, end for riser)
    gain_db: float = -6.0


def sfx_track(cues: list[Cue], duration: float, path: Path) -> Path:
    buf = np.zeros(int(duration * SR) + SR)
    for c in cues:
        gen, hit = SFX[c.kind]
        x = gen() * 10 ** (c.gain_db / 20)
        i = int((c.at - hit) * SR)
        a, b = max(i, 0), min(len(buf), i + len(x))
        if b > a:
            buf[a:b] += x[a - i : b - i]
    return write_wav(path, buf[: int(duration * SR)])


def _run(cmd: list[str], what: str) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"{what} failed: {r.stderr[-1200:]}")
    return r.stderr


def mix(
    duration: float,
    out: Path,
    music: Path | None = None,
    music_start: float = 0.0,
    music_gain_db: float = 0.0,
    voice: Path | None = None,
    sfx: Path | None = None,
    lufs: float = -14.0,
    true_peak: float = -2.5,  # AAC encoding overshoots ~1 dB; this keeps the delivered file under -1.5 dBTP
) -> Path:
    """Render the final stereo mix of exactly `duration` seconds."""
    inputs, chains, labels = [], [], []
    k = 0
    fade = min(1.0, duration / 4)
    if music:
        inputs += ["-ss", f"{music_start:.3f}", "-i", str(music)]
        chains.append(
            f"[{k}:a]aresample={SR},atrim=end={duration:.3f},asetpts=PTS-STARTPTS,volume={music_gain_db:.1f}dB,"
            f"afade=t=out:st={max(duration - fade, 0):.3f}:d={fade:.3f}[mus]"
        )
        k += 1
    if voice:
        inputs += ["-i", str(voice)]
        chains.append(f"[{k}:a]aresample={SR},apad,atrim=end={duration:.3f}[voc]")
        k += 1
    if music and voice:
        # duck music ~6 dB while the voice talks (sidechain)
        chains.append(
            "[voc]asplit[voc][key];[mus][key]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=300[mus]"
        )
    if music:
        labels.append("[mus]")
    if voice:
        labels.append("[voc]")
    if sfx:
        inputs += ["-i", str(sfx)]
        chains.append(f"[{k}:a]aresample={SR},apad,atrim=end={duration:.3f}[sfx]")
        labels.append("[sfx]")
        k += 1
    if not labels:  # silent edit: a real silent track so players and Instagram accept the file
        inputs += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"anullsrc=r={SR}:cl=stereo"]
        labels.append(f"[{k}:a]")
    mixed = (
        f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=end={duration:.3f}"
        if len(labels) > 1
        else f"{labels[0]}atrim=end={duration:.3f}"
    )
    pre = out.with_suffix(".pre.wav")
    graph = ";".join([*chains, f"{mixed},aformat=channel_layouts=stereo[mix]"])
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            graph,
            "-map",
            "[mix]",
            "-ar",
            str(SR),
            str(pre),
        ],
        "mix",
    )
    # two-pass loudness normalisation to the platform target
    stats = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(pre),
            "-af",
            f"loudnorm=I={lufs}:TP={true_peak}:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        "loudness scan",
    )
    m = json.loads(stats[stats.rindex("{") : stats.rindex("}") + 1])
    if float(m["input_i"]) < -70:  # silence: nothing to normalise
        pre.replace(out)
        return out
    _run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(pre), "-af",
            f"loudnorm=I={lufs}:TP={true_peak}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
            f"aresample={SR}",
            "-ar", str(SR), str(out),
        ],
        "loudnorm",
    )  # fmt: skip
    pre.unlink(missing_ok=True)
    return out


def measure(path: Path) -> dict:
    """Integrated loudness (LUFS) and true peak (dBTP) of a file's audio, EBU R128."""
    err = _run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        "loudness measure",
    )
    tail = err[err.rindex("Summary:") :]
    pick = lambda key: float(tail.split(key)[1].split()[0])  # noqa: E731
    return {"integrated_lufs": pick("I:"), "true_peak_dbtp": pick("Peak:")}


def mux(video: Path, audio: Path, out: Path, max_true_peak: float = -1.0) -> Path:
    """Mux picture + sound; if the encoded AAC still peaks above `max_true_peak`, lower it and mux again."""
    gain = 0.0
    for _ in range(2):
        _run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-af", f"volume={gain:.2f}dB", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
             "-shortest", "-movflags", "+faststart", str(out)],
            "mux",
        )  # fmt: skip
        tp = measure(out)["true_peak_dbtp"]
        if tp <= max_true_peak:
            break
        gain -= tp - max_true_peak + 0.3
    return out
