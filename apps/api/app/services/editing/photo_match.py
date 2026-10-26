"""Photos that sit with the uploaded clips.

Before an image becomes a shot, its colour, contrast, sharpness and grain are matched to the video clips of the same
edit: Reinhard colour transfer in LAB toward the clips' average (blended, so the photo keeps its own character),
softened when it is much crisper than the footage, and given the footage's grain. The camera move on the photo follows
the clips' motion level (planner). An edit with only photos is left as it is. Deterministic, CPU, no model needed.
"""

from pathlib import Path

import cv2
import numpy as np

WIDTH = 540  # stats are measured at one width so sharpness/noise compare across resolutions
STRENGTH = 0.6  # how far the photo's colour moves toward the clips (1 = full transfer)


def _small(img: np.ndarray) -> np.ndarray:
    return cv2.resize(img, (WIDTH, max(1, round(img.shape[0] * WIDTH / img.shape[1]))), interpolation=cv2.INTER_AREA)


def _stats(img: np.ndarray) -> dict:
    s = _small(img)
    lab = cv2.cvtColor(s, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    gray = cv2.cvtColor(s, cv2.COLOR_BGR2GRAY).astype(np.float32)
    noise = gray - cv2.GaussianBlur(gray, (0, 0), 1.2)
    return {"mean": lab.mean(0), "std": lab.std(0) + 1e-3, "sharp": float(cv2.Laplacian(gray, cv2.CV_32F).var()),
            "noise": float(np.median(np.abs(noise)) * 1.4826)}


def clip_stats(videos: list[Path]) -> dict | None:
    """Average look of the clips, from frames at 25/50/75 % of each."""
    found = []
    for v in videos:
        cap = cv2.VideoCapture(str(v))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        for f in (0.25, 0.5, 0.75):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * f))
            ok, frame = cap.read()
            if ok:
                found.append(_stats(frame))
        cap.release()
    if not found:
        return None
    return {"mean": np.mean([x["mean"] for x in found], 0), "std": np.mean([x["std"] for x in found], 0),
            "sharp": float(np.median([x["sharp"] for x in found])), "noise": float(np.median([x["noise"] for x in found]))}


def match(image: Path, target: dict, out: Path, seed: int = 0) -> Path:
    img = cv2.imread(str(image), cv2.IMREAD_COLOR)
    if img is None:
        return image
    src = _stats(img)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    moved = (lab - src["mean"]) * (target["std"] / src["std"]) + target["mean"]
    lab = np.clip(lab + STRENGTH * (moved - lab), 0, 255)
    img = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
    scale = img.shape[1] / WIDTH  # stats were taken at WIDTH; blur/grain act at full size
    if src["sharp"] > 1.6 * target["sharp"] > 0:  # much crisper than the footage: soften toward it
        sigma = min(2.5, 0.5 * np.log2(src["sharp"] / target["sharp"])) * scale
        img = cv2.GaussianBlur(img, (0, 0), max(sigma, 0.3))
    extra = max(0.0, target["noise"] - src["noise"])
    if extra > 0.3:  # footage grain the photo lacks (luma-only, fixed seed: same photo, same grain)
        g = np.random.default_rng(seed).normal(0, extra, img.shape[:2]).astype(np.float32)
        img = np.clip(img.astype(np.float32) + g[..., None], 0, 255).astype(np.uint8)
    cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return out


def match_photos(assets: list[tuple[str, Path]], work: Path) -> list[Path]:
    """[(kind, path)] in edit order → paths to use (matched copies for images when the edit has clips)."""
    target = clip_stats([p for k, p in assets if k != "image"])
    if target is None:
        return [p for _, p in assets]
    work.mkdir(parents=True, exist_ok=True)
    return [match(p, target, work / f"photo-{i:02d}.jpg", seed=i) if k == "image" else p for i, (k, p) in enumerate(assets)]


if __name__ == "__main__":  # self-check: a crisp, cool photo moves toward warm, soft, grainy footage
    import tempfile

    d = Path(tempfile.mkdtemp())
    rng = np.random.default_rng(1)
    vid = d / "clip.mp4"
    vw = cv2.VideoWriter(str(vid), cv2.VideoWriter_fourcc(*"mp4v"), 30, (360, 640))
    for _ in range(30):
        f = np.full((640, 360, 3), (60, 120, 200), np.uint8)  # warm (BGR)
        vw.write(cv2.GaussianBlur(np.clip(f + rng.normal(0, 6, f.shape), 0, 255).astype(np.uint8), (0, 0), 2))
    vw.release()
    photo = np.full((1280, 720, 3), (200, 120, 60), np.uint8)  # cool
    cv2.putText(photo, "SALE", (60, 640), cv2.FONT_HERSHEY_SIMPLEX, 6, (255, 255, 255), 20)
    cv2.imwrite(str(d / "p.jpg"), photo)
    out = match_photos([("video", vid), ("image", d / "p.jpg")], d / "m")[1]
    before, after = _stats(photo), _stats(cv2.imread(str(out)))
    tgt = clip_stats([vid])
    assert np.abs(after["mean"] - tgt["mean"]).sum() < np.abs(before["mean"] - tgt["mean"]).sum() * 0.6
    assert after["sharp"] < before["sharp"]
    print("ok", before["mean"].round(), "->", after["mean"].round(), "target", tgt["mean"].round())
