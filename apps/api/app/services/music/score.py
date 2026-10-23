"""Original synthesized score (numpy): royalty-free by construction, used when the user supplies no music.

Styles: `phonk` (808 kick, cowbell riff, hats, distorted sub), `cinematic` (pads + slow pulse), `commercial` (clean
4-on-the-floor). The structure is intro → build → drop so beat sync has real accents to land on. Deterministic for a
given (style, bpm, duration, seed).
"""

import wave
from pathlib import Path

import numpy as np

SR = 44100


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1.0) * np.exp(-t / decay)


def kick(n=int(0.45 * SR)) -> np.ndarray:
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)  # pitch drop = 808 body
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.18) * 1.0


def cowbell(freq: float, n=int(0.22 * SR)) -> np.ndarray:
    t = np.arange(n) / SR
    tone = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + np.sign(np.sin(2 * np.pi * freq * 1.48 * t)) * 0.5
    return tone * _env(n, 0.001, 0.07) * 0.35


def hat(rng: np.random.Generator, n=int(0.05 * SR), open_=False) -> np.ndarray:
    noise = rng.standard_normal(n if not open_ else n * 4)
    hp = noise - np.convolve(noise, np.ones(8) / 8, mode="same")
    return hp * _env(len(hp), 0.0005, 0.012 if not open_ else 0.06) * 0.25


def snare(rng: np.random.Generator, n=int(0.25 * SR)) -> np.ndarray:
    t = np.arange(n) / SR
    return (rng.standard_normal(n) * 0.6 + np.sin(2 * np.pi * 190 * t) * 0.4) * _env(n, 0.001, 0.06) * 0.5


def sub(freq: float, n: int) -> np.ndarray:
    t = np.arange(n) / SR
    return np.tanh(np.sin(2 * np.pi * freq * t) * 3) * _env(n, 0.005, 0.5) * 0.35


def pad(freqs: list[float], n: int) -> np.ndarray:
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate(freqs)) / len(freqs)
    return s * np.minimum(t / 1.5, 1.0) * 0.18


def _place(buf: np.ndarray, x: np.ndarray, at: float) -> None:
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def generate(style: str = "phonk", bpm: float = 140, duration: float = 20.0, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros(int(duration * SR) + SR)
    beat = 60 / bpm
    n_beats = int(duration / beat) + 1
    intro = 8 if duration > 12 else 4  # beats before the drop
    riff = [880, 880, 1046, 880, 784, 880, 1174, 1046]
    for b in range(n_beats):
        t = b * beat
        drop = b >= intro
        if style == "phonk":
            if drop or b % 2 == 0:
                _place(out, kick(), t)
            if drop:
                _place(out, sub([55, 55, 49, 62][(b // 4) % 4], int(beat * SR)), t)
                if b % 2 == 1:
                    _place(out, snare(rng), t)
            for k in range(2):
                _place(out, cowbell(riff[(b * 2 + k) % len(riff)]), t + k * beat / 2)
            for k in range(4 if drop else 2):
                _place(out, hat(rng, open_=(k == 3 and b % 4 == 3)), t + k * beat / (4 if drop else 2))
        elif style == "cinematic":
            if b % 4 == 0:
                _place(out, pad([110, 165, 220, 277], int(4 * beat * SR)), t)
            if drop and b % 2 == 0:
                _place(out, kick() * 0.7, t)
        else:  # commercial
            _place(out, kick() * 0.8, t)
            if b % 2 == 1:
                _place(out, snare(rng) * 0.7, t)
            _place(out, hat(rng), t + beat / 2)
            if b % 4 == 0:
                _place(out, pad([220, 277, 330], int(4 * beat * SR)) * 0.8, t)
    out = out[: int(duration * SR)]
    fade = int(0.6 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return (out / (np.abs(out).max() or 1) * 0.9).astype(np.float32)


def write_wav(path: Path, y: np.ndarray) -> Path:
    stereo = np.repeat((y * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    return path


if __name__ == "__main__":  # self-check: the generated phonk track must be detected at its own tempo
    import tempfile

    from app.services.music import beats

    with tempfile.TemporaryDirectory() as d:
        p = write_wav(Path(d) / "phonk.wav", generate("phonk", 140, 16))
        a = beats.analyze(p)
    assert abs(a["tempo_bpm"] - 140) < 4 or abs(a["tempo_bpm"] - 70) < 2, a["tempo_bpm"]
    assert a["drops"], "the drop after the intro must be detected"
    print("score self-check ok", a["tempo_bpm"], "drops", a["drops"])
