"""Music analysis for beat-synchronised editing (librosa, local, no paid API).

`analyze(path)` → tempo, beat grid, estimated downbeats, onsets, strong accents, an energy curve and likely drops.
Times are seconds from the start of the file. `snap`/`cut_offsets` relate edit points to the grid.
"""

import subprocess
from pathlib import Path

import numpy as np

SR = 22050
HOP = 512


def load_audio(path: Path, sr: int = SR) -> np.ndarray:
    """Mono float32 via ffmpeg (handles mp4/m4a/mp3/wav alike)."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True,
        timeout=600,
    )
    if r.returncode != 0:
        raise ValueError(f"cannot decode audio: {r.stderr.decode(errors='ignore')[:200]}")
    return np.frombuffer(r.stdout, dtype=np.float32)


def analyze(path: Path) -> dict:
    import librosa

    y = load_audio(path)
    dur = len(y) / SR
    if dur < 1.0 or float(np.abs(y).max(initial=0)) < 1e-4:
        return {"duration_s": round(dur, 3), "has_music": False}
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    # Tempo from the kick band: hats and melodic hits pulled full-band estimates to 2:3 multiples (92 for 140 BPM).
    low = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, fmax=200, n_mels=64)
    src = low if low.max(initial=0) > 0.2 * env.max(initial=1) else env
    tempo = float(librosa.feature.tempo(onset_envelope=src, sr=SR, hop_length=HOP)[0])
    while tempo and tempo < 80:  # reels sit in 80-160 BPM; fold octave errors into that range
        tempo *= 2
    while tempo > 160:
        tempo /= 2
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=env, sr=SR, hop_length=HOP, bpm=tempo)
    beats = librosa.frames_to_time(beat_frames, sr=SR, hop_length=HOP)
    onset_frames = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP)
    onsets = librosa.frames_to_time(onset_frames, sr=SR, hop_length=HOP)
    strength = env[onset_frames] if len(onset_frames) else np.array([])
    accents = onsets[strength >= np.percentile(strength, 80)] if len(strength) else np.array([])

    # downbeats: the 4-beat phase whose beats carry the most onset energy (ponytail: assumes 4/4)
    downbeats: list[float] = []
    if len(beat_frames) >= 8:
        phase = max(range(4), key=lambda p: float(env[beat_frames[p::4]].sum()))
        downbeats = beats[phase::4].tolist()

    # energy per 0.5 s, normalised 0..1, and drops: a jump after a quieter stretch
    win = int(SR * 0.5)
    rms = np.sqrt(np.mean(y[: len(y) // win * win].reshape(-1, win) ** 2, axis=1))
    energy = (rms / (rms.max() or 1)).round(3)
    # a drop = the next 2 s sit clearly above the previous 4 s (sustained, not a single hit); snapped to a beat
    gain = np.array(
        [
            energy[i : i + 4].mean() - energy[max(0, i - 8) : i].mean() if 3 <= i <= len(energy) - 4 else 0
            for i in range(len(energy))
        ]
    )
    drops: list[float] = []
    for i in np.argsort(-gain):
        t = i * 0.5
        if gain[i] < 0.15 or energy[i : i + 4].mean() < 0.6:
            break
        if all(abs(t - d) > 6 for d in drops):
            drops.append(t)
    near = lambda t: float(min(beats, key=lambda b: abs(b - t))) if len(beats) else t  # noqa: E731
    drops = sorted(round(near(t), 3) for t in drops[:3])
    return {
        "duration_s": round(dur, 3),
        "has_music": True,
        "tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 1),
        "beats": [round(float(t), 3) for t in beats],
        "downbeats": [round(float(t), 3) for t in downbeats],
        "onsets": [round(float(t), 3) for t in onsets],
        "accents": [round(float(t), 3) for t in accents],
        "energy": {"hop_s": 0.5, "values": energy.tolist()},
        "drops": drops,
    }


def snap(t: float, grid: list[float], fps: float = 30.0, max_shift: float = 0.12) -> float:
    """Move t onto the nearest grid time if within max_shift, then onto the frame grid."""
    if grid:
        g = min(grid, key=lambda x: abs(x - t))
        if abs(g - t) <= max_shift:
            t = g
    return round(round(t * fps) / fps, 4)


def cut_offsets(cuts: list[float], grid: list[float]) -> list[dict]:
    """Signed offset (ms) from every cut to its nearest grid time; negative = cut before the beat."""
    if not grid:
        return []
    out = []
    for c in cuts:
        g = min(grid, key=lambda x: abs(x - c))
        out.append({"cut": round(c, 3), "beat": round(g, 3), "offset_ms": round((c - g) * 1000)})
    return out


if __name__ == "__main__":  # self-check: a 120 BPM click track must read as ~120 BPM with snapped cuts
    import tempfile
    import wave

    sr, bpm = SR, 120
    t = np.arange(sr * 8) / sr
    y = np.zeros_like(t)
    for k in range(int(8 * bpm / 60)):
        i = int(k * 60 / bpm * sr)
        y[i : i + 400] += np.hanning(400) * (1.0 if k % 4 == 0 else 0.6)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "click.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((y * 30000).astype(np.int16).tobytes())
        a = analyze(p)
    assert abs(a["tempo_bpm"] - 120) < 3, a["tempo_bpm"]
    nearest = min(a["beats"], key=lambda b: abs(b - 1.03))
    assert snap(1.03, a["beats"]) == round(round(nearest * 30) / 30, 4)
    print("beats self-check ok", a["tempo_bpm"])
