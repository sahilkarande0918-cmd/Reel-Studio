"""Frame-level composites that FFmpeg filters cannot express, drawn with OpenCV + small local ONNX models (CPU).

- subject_pop: salient-subject cutout (U²-Netp, Apache-2.0) per frame → the subject stays sharp and bright, the
  background is blurred/darkened, and an optional glowing outline traces the subject (product highlight).
- depth_parallax: 2.5D camera move on a still from a monocular depth map (Depth-Anything-V2-Small, Apache-2.0):
  near pixels shift more than far ones as the virtual camera moves.

Models live in DATA_DIR/models/onnx (downloaded once, see docs/OPEN_SOURCE_TOOL_AUDIT.md). When a model file is missing
the caller substitutes an FFmpeg effect and records the substitution; nothing pretends to have run.
"""

import subprocess
from functools import cache
from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings

MODELS = {"u2netp": "u2netp.onnx", "depth": "depth-anything-v2-small.onnx"}
MEAN, STD = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])


def model_path(name: str) -> Path:
    return get_settings().data_dir / "models" / "onnx" / MODELS[name]


def available(name: str) -> bool:
    return model_path(name).is_file()


@cache
def _session(name: str):
    import onnxruntime as ort

    return ort.InferenceSession(str(model_path(name)), providers=["CPUExecutionProvider"])


def _blob(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    x = cv2.cvtColor(cv2.resize(frame, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB) / 255.0
    return ((x - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)


def subject_mask(frame: np.ndarray) -> np.ndarray:
    """0..1 float mask of the most salient subject, frame-sized."""
    s = _session("u2netp")
    out = s.run(None, {s.get_inputs()[0].name: _blob(frame, (320, 320))})[0][0, 0]
    m = (out - out.min()) / max(float(out.max() - out.min()), 1e-6)
    return cv2.resize(m, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)


def depth_map(frame: np.ndarray) -> np.ndarray:
    """0..1 relative inverse depth (1 = near), frame-sized."""
    s = _session("depth")
    h, w = frame.shape[:2]
    sw, sh = 518, max(14, round(518 * h / w / 14) * 14)
    d = s.run(None, {"pixel_values": _blob(frame, (sw, sh))})[0][0]
    d = (d - d.min()) / max(float(d.max() - d.min()), 1e-6)
    return cv2.resize(d.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _frames(p: Path) -> tuple[list[np.ndarray], float]:
    cap = cv2.VideoCapture(str(p))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    return out, fps


def _write(frames: list[np.ndarray], fps: float, out: Path) -> None:
    h, w = frames[0].shape[:2]
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps:g}", "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(out)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    assert proc.stdin
    for f in frames:
        proc.stdin.write(np.ascontiguousarray(f).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"composite encode failed for {out.name}")


def subject_pop(frames: list[np.ndarray], p: dict, accent=(107, 224, 200)) -> list[np.ndarray]:
    out, prev = [], None
    for f in frames:
        m = subject_mask(f)
        prev = m if prev is None else 0.6 * m + 0.4 * prev  # temporal smoothing: no flickering matte edges
        m3 = cv2.GaussianBlur(prev, (0, 0), 2)[..., None]
        bg = cv2.GaussianBlur(f, (0, 0), p.get("blur", 9)) * (1 - p.get("darken", 0.45))
        comp = f * m3 + bg * (1 - m3)
        if p.get("outline", 1) >= 0.5:
            edge = cv2.morphologyEx((prev > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)).astype(np.float32)
            glow = cv2.GaussianBlur(edge, (0, 0), 6)[..., None] * np.array(accent, np.float32)[None, None] * 2.2
            comp = comp + glow + edge[..., None] * np.array(accent, np.float32)
        out.append(np.clip(comp, 0, 255).astype(np.uint8))
    return out


def depth_parallax(frames: list[np.ndarray], p: dict) -> list[np.ndarray]:
    """Moves a virtual camera across the first frame using its depth (stills; video shots use frame 0's depth)."""
    base = frames[0]
    h, w = base.shape[:2]
    d = cv2.GaussianBlur(depth_map(base), (0, 0), 3)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    amp = p.get("amount", 0.04) * w
    n = len(frames)
    out = []
    for i in range(n):
        u = i / max(n - 1, 1)
        e = u * u * (3 - 2 * u)
        dx, dy = (e - 0.5) * amp * p.get("direction", 1), (e - 0.5) * amp * 0.35
        zoom = 1 + 0.06 * e
        mx = (xs - w / 2) / zoom + w / 2 - dx * d
        my = (ys - h / 2) / zoom + h / 2 - dy * d
        out.append(cv2.remap(base, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
    return out


APPLY = {"subject_pop": ("u2netp", subject_pop), "depth_parallax": ("depth", depth_parallax)}


def apply(src: Path, out: Path, effects: list[tuple[str, dict]]) -> list[str]:
    """Runs the composites in order; returns the ids that could not run (model missing) for substitution notes."""
    frames, fps = _frames(src)
    skipped = []
    for eid, params in effects:
        model, fn = APPLY[eid]
        if not available(model):
            skipped.append(eid)
            continue
        frames = fn(frames, params)
    _write(frames, fps, out)
    return skipped
