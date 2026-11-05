"""Lightweight speaker labels per sentence (CPU, numpy + scikit-learn, no extra model or download).

Each sentence's voice is summarised by MFCC statistics (mean and spread over its voiced frames); sentences are clustered
(Ward) into 1–4 voices, the number chosen by silhouette score. Good enough to tell a host from a guest in a studio
podcast and to stop a rhetorical question inside an answer from being read as the host's next question. It is not a
diarization benchmark model: crosstalk, very short interjections and similar voices can be mislabelled (pyannote would
be the upgrade, at the cost of a gated model download and GPU time).
"""

import wave
from pathlib import Path

import numpy as np

SR = 16000
N_FFT, HOP, N_MEL, N_MFCC = 512, 160, 40, 20


def _mel_bank() -> np.ndarray:
    def hz2mel(h):
        return 2595 * np.log10(1 + h / 700)

    def mel2hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    pts = mel2hz(np.linspace(hz2mel(80), hz2mel(7600), N_MEL + 2))
    bins = np.floor((N_FFT + 1) * pts / SR).astype(int)
    fb = np.zeros((N_MEL, N_FFT // 2 + 1))
    for m in range(1, N_MEL + 1):
        a, c, b = bins[m - 1], bins[m], bins[m + 1]
        fb[m - 1, a:c] = (np.arange(a, c) - a) / max(c - a, 1)
        fb[m - 1, c:b] = (b - np.arange(c, b)) / max(b - c, 1)
    return fb


def mfcc(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(frames × N_MFCC-1 coefficients without c0, frame log energy) for 16 kHz mono float audio."""
    if len(x) < N_FFT:
        return np.zeros((0, N_MFCC - 1)), np.zeros(0)
    n = 1 + (len(x) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[idx] * np.hamming(N_FFT)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    logmel = np.log(np.maximum(power @ _mel_bank().T, 1e-10))
    k = np.arange(N_MEL)
    dct = np.cos(np.pi / N_MEL * (k[None, :] + 0.5) * np.arange(N_MFCC)[:, None])
    c = logmel @ dct.T
    return c[:, 1:], np.log(np.maximum(power.sum(axis=1), 1e-10))


def features(wav: Path, spans: list[tuple[float, float]]) -> np.ndarray:
    with wave.open(str(wav), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    out = []
    for a, b in spans:
        c, e = mfcc(x[int(a * SR) : int(b * SR)])
        if len(c) < 10:
            out.append(np.zeros(2 * (N_MFCC - 1)))
            continue
        voiced = c[e >= np.percentile(e, 40)]  # louder frames carry the voice, quieter ones the room
        out.append(np.concatenate([voiced.mean(axis=0), voiced.std(axis=0)]))
    return np.array(out)


def label(wav: Path, spans: list[tuple[float, float]], max_k: int = 4) -> list[str]:
    """"S1", "S2", ... per span (numbered by first appearance); all "S1" when one voice explains the audio best."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import silhouette_score

    n = len(spans)
    if n < 6:
        return ["S1"] * n
    X = features(wav, spans)
    X = (X - X.mean(axis=0)) / np.maximum(X.std(axis=0), 1e-6)
    weight = np.array([b - a for a, b in spans])
    best, best_k = np.zeros(n, int), 1
    best_s = 0.08  # below this the "speakers" are noise of one voice
    fit = X[weight >= 1.0] if (weight >= 1.0).sum() >= 6 else X  # short interjections are unreliable to cluster on
    for k in range(2, min(max_k, len(fit) - 1) + 1):
        model = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(fit)
        s = silhouette_score(fit, model.labels_)
        if s > best_s:
            cent = np.array([fit[model.labels_ == i].mean(axis=0) for i in range(k)])
            best = np.argmin(((X[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2), axis=1)
            best_s, best_k = s, k
    if best_k == 1:
        return ["S1"] * n
    names: dict[int, str] = {}
    return [names.setdefault(int(c), f"S{len(names) + 1}") for c in best]
