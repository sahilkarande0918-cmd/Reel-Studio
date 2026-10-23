"""Per-clip analysis for editing: what is in each uploaded clip and which moments are worth using.

Streamed at 240 px (bounded memory). Per 0.25 s bucket: motion (optical-flow magnitude), sharpness (Laplacian
variance — blurry frames are poor picks), brightness, and the motion-weighted centre of action (for 9:16 framing).
`moments` are the best non-overlapping windows by a transparent score (sharp + lively, not dark). Images get one
"moment" covering the whole still.
"""

import subprocess
from pathlib import Path

import cv2
import numpy as np

from app.services.reference.analyzer import probe

W = 240
BUCKET = 0.25
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def analyze_image(path: Path) -> dict:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"unreadable image {path.name}")
    g = cv2.cvtColor(cv2.resize(img, (W, int(img.shape[0] * W / img.shape[1]))), cv2.COLOR_BGR2GRAY)
    sal = cv2.Laplacian(g, cv2.CV_64F)
    ys, xs = np.nonzero(np.abs(sal) > np.percentile(np.abs(sal), 95))
    return {
        "kind": "image",
        "width": img.shape[1],
        "height": img.shape[0],
        "duration_s": None,
        "orientation": "portrait"
        if img.shape[0] > img.shape[1]
        else "landscape"
        if img.shape[1] > img.shape[0]
        else "square",
        "focus": [
            round(float(xs.mean() / g.shape[1]), 3) if len(xs) else 0.5,
            round(float(ys.mean() / g.shape[0]), 3) if len(ys) else 0.5,
        ],
        "brightness": round(float(g.mean()), 1),
        "moments": [{"start_s": 0.0, "end_s": 0.0, "score": 0.5, "focus": [0.5, 0.5]}],
    }


def analyze_clip(path: Path, max_moments: int = 12) -> dict:
    if path.suffix.lower() in IMAGE_EXT:
        return analyze_image(path)
    meta = probe(path)
    fps = meta["fps"] or 30
    cap = cv2.VideoCapture(str(path))
    per = max(1, round(fps * BUCKET))
    prev, n = None, 0
    rows: list[list[float]] = []  # [t, motion, sharp, bright, cx, cy]
    acc: list[list[float]] = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h = int(frame.shape[0] * W / frame.shape[1])
        g = cv2.cvtColor(cv2.resize(frame, (W, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        if prev is not None and n % 2 == 0:  # flow on every 2nd frame is plenty for 0.25 s buckets
            f = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            mag = np.sqrt(f[..., 0] ** 2 + f[..., 1] ** 2)
            tot = mag.sum() or 1.0
            ys, xs = np.mgrid[0 : mag.shape[0], 0 : mag.shape[1]]
            acc.append([n / fps, float(mag.mean()), float(cv2.Laplacian(g, cv2.CV_64F).var()), float(g.mean()),
                        float((mag * xs).sum() / tot / mag.shape[1]), float((mag * ys).sum() / tot / mag.shape[0])])  # fmt: skip
        if n % per == per - 1 and acc:
            rows.append(list(np.mean(acc, axis=0)))
            acc = []
        prev = g
        n += 1
    cap.release()
    if not rows:
        raise ValueError(f"no decodable frames in {path.name}")
    a = np.array(rows)
    t, motion, sharp, bright, cx, cy = a.T
    sharp_n = np.clip(sharp / (np.percentile(sharp, 90) or 1), 0, 1)
    motion_n = np.clip(motion / (np.percentile(motion, 90) or 1), 0, 1)
    dark = (bright < 25).astype(float)
    score = 0.5 * sharp_n + 0.4 * motion_n + 0.1 - 0.6 * dark
    moments = []
    win = max(1, int(1.5 / BUCKET))  # 1.5 s windows
    used = np.zeros(len(score), bool)
    for _ in range(max_moments):
        s = np.convolve(np.where(used, -9, score), np.ones(win) / win, mode="valid")
        if not len(s) or s.max() < -1:
            break
        i = int(s.argmax())
        used[max(0, i - win // 2) : i + win + win // 2] = True
        sl = slice(i, i + win)
        moments.append(
            {
                "start_s": round(float(t[i]), 2),
                "end_s": round(float(min(t[min(i + win, len(t) - 1)] + BUCKET, meta["duration_s"])), 2),
                "score": round(float(s.max()), 3),
                "focus": [round(float(np.median(cx[sl])), 3), round(float(np.median(cy[sl])), 3)],
            }
        )
    w, h = meta["width"] or 1, meta["height"] or 1
    return {
        "kind": "video",
        **meta,
        "orientation": "portrait" if h > w else "landscape" if w > h else "square",
        "motion_mean": round(float(motion.mean()), 3),
        "brightness": round(float(bright.mean()), 1),
        "sharpness_median": round(float(np.median(sharp)), 1),
        "focus": [round(float(np.median(cx)), 3), round(float(np.median(cy)), 3)],
        "curve": {"bucket_s": BUCKET, "motion": motion.round(3).tolist(), "sharp": sharp_n.round(3).tolist()},
        "moments": sorted(moments, key=lambda m: m["start_s"]),
    }


def proxy(path: Path, out: Path, height: int = 540) -> Path:
    """Small H.264 proxy for previews and fast analysis of huge uploads."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", f"scale=-2:{height}", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)],
        capture_output=True, text=True, timeout=3600,
    )  # fmt: skip
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])
    return out
