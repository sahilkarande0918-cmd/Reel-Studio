"""Subject tracks for tracked overlays (a label that follows the subject).

Runs on the rendered base picture, so the path is already in output-frame coordinates (after crop, zoom and speed).
The start box is the U²-Netp subject mask's bounding box when the model is installed, else a centred box. OpenCV's
MIL tracker follows it (no extra model files); when it loses the subject the last good point is held, never guessed.
"""

from pathlib import Path

import cv2
import numpy as np

from app.services.editing import composite

RATE = 8  # points per second (GSAP eases between them)


def _start_box(frame: np.ndarray) -> tuple[int, int, int, int]:
    h, w = frame.shape[:2]
    if composite.available("u2netp"):
        ys, xs = np.nonzero(composite.subject_mask(frame) > 0.5)
        if xs.size > 0.01 * w * h:
            return int(xs.min()), int(ys.min()), int(xs.max() - xs.min()), int(ys.max() - ys.min())
    s = int(min(w, h) * 0.3)
    return (w - s) // 2, (h - s) // 2, s, s


def track(video: Path, start: float, duration: float, width: int = 360) -> list[list[float]]:
    """[[t, x, y], ...] with t from `start` and x/y the box centre as 0–1 of the frame; [] when the video can't be read."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    ok, frame = cap.read()
    if not ok:
        cap.release()
        return []
    scale = width / frame.shape[1]
    small = cv2.resize(frame, None, fx=scale, fy=scale)
    sh, sw = small.shape[:2]
    tracker = cv2.TrackerMIL_create()
    box = _start_box(small)
    tracker.init(small, box)
    pts, step, n = [], max(1, round(fps / RATE)), 0
    last = (box[0] + box[2] / 2, box[1] + box[3] / 2)
    while n / fps <= duration:
        if n % step == 0:
            pts.append([round(n / fps, 3), round(min(max(last[0] / sw, 0), 1), 4), round(min(max(last[1] / sh, 0), 1), 4)])
        ok, frame = cap.read()
        if not ok:
            break
        n += 1
        found, b = tracker.update(cv2.resize(frame, (sw, sh)))
        if found:
            last = (b[0] + b[2] / 2, b[1] + b[3] / 2)
    cap.release()
    return pts[:900]


if __name__ == "__main__":  # self-check on a synthetic clip: a white square moving right is followed
    import tempfile

    out = Path(tempfile.mkdtemp()) / "move.mp4"
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 30, (360, 640))
    for i in range(60):
        img = np.zeros((640, 360, 3), np.uint8)
        cv2.rectangle(img, (60 + 3 * i, 270), (160 + 3 * i, 370), (255, 255, 255), -1)
        vw.write(img)
    vw.release()
    p = track(out, 0, 1.9)
    assert len(p) >= 12 and p[-1][1] > p[0][1] + 0.15, p
    print("ok", p[0], p[-1])
