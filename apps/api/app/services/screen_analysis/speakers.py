"""Speaker-aware 9:16 framing for podcasts and interviews (CPU only, no extra model besides a 0.2 MB face detector).

1. Faces: OpenCV YuNet (MIT, opencv_zoo) every 0.5 s on a 480-px-wide decode at 6 fps; Haar cascade fallback.
2. Seats: face centres clustered along x into "slots" (host, guest, ...) over the whole recording.
3. Active speaker: while there is speech (audio level), the slot whose mouth region moves most, normalised per slot,
   smoothed with a 1 s majority window and a minimum shot length (hysteresis): no switching on every syllable.
4. Plan: per clip, cuts between speakers (each shot >= MIN_SHOT_S); rapid back-and-forth becomes a stable split
   screen (both speakers stacked); two people close enough to share one 9:16 window stay in one wide shot.
   With no faces, the centred crop is used. Only real camera pixels are shown (no fabricated angles).
"""

import os
import subprocess
import wave
from collections import Counter
from pathlib import Path

import numpy as np

STEP_S = 1 / 6
DETECT_EVERY = 3  # frames: one detection every 0.5 s, boxes held in between
DECODE_W = 480
MIN_SHOT_S = 2.0
SMOOTH_S = 1.0
SPLIT_SWITCHES, SPLIT_WINDOW_S = 3, 8.0  # >= 3 changes inside 8 s → split screen for that stretch
FACE_MODEL = Path(os.environ.get("FACE_MODEL", r"D:\ReelStudio\models\yunet\face_detection_yunet_2023mar.onnx"))


def _detector(w: int, h: int):
    import cv2

    if FACE_MODEL.is_file():
        det = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (w, h), 0.7, 0.3, 50)

        def yunet(img):
            faces = det.detect(img)[1]
            return [] if faces is None else [tuple(map(float, f[:4])) for f in faces]

        return yunet
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return lambda img: [tuple(map(float, b)) for b in
                        cascade.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.15, 5, minSize=(24, 24))]


def _levels(wav: Path, n: int) -> np.ndarray:
    """Audio RMS (dB) per STEP_S frame."""
    try:
        with wave.open(str(wav), "rb") as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    except (OSError, wave.Error):
        return np.full(n, -30.0)
    hop = int(sr * STEP_S)
    m = min(n, len(x) // hop)
    rms = np.sqrt(np.mean(x[: m * hop].reshape(m, hop) ** 2, axis=1))
    out = np.full(n, -80.0)
    out[:m] = 20 * np.log10(np.maximum(rms, 1e-4))
    return out


def _slots(dets: list[list[tuple]], k: int, width: float) -> list[float]:
    """1-D k-means of face centres (x)."""
    xs = np.array([d[0] + d[2] / 2 for fr in dets for d in fr])
    if not len(xs):
        return []
    c = np.quantile(xs, np.linspace(0.1, 0.9, k)) if k > 1 else np.array([np.median(xs)])
    for _ in range(15):
        lab = np.argmin(np.abs(xs[:, None] - c[None, :]), axis=1)
        c = np.array([xs[lab == i].mean() if (lab == i).any() else c[i] for i in range(k)])
    c = sorted(c)
    merged = [c[0]]
    for v in c[1:]:  # two "seats" closer than 12 % of the width are one person moving
        if v - merged[-1] > 0.12 * width:
            merged.append(v)
    return merged


def analyze(src: Path, wav: Path, W: int, H: int, duration_s: float) -> dict:
    """Face slots and the active speaker per 1/6 s for the whole recording (cached by the caller)."""
    import cv2

    dh = int(round(H * DECODE_W / W / 2) * 2)
    scale = W / DECODE_W
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps=6,scale={DECODE_W}:{dh}",
                             "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE,
                            stdin=subprocess.DEVNULL)
    detect = _detector(DECODE_W, dh)
    size = DECODE_W * dh * 3
    dets: list[list[tuple]] = []
    motion: list[list[float]] = []
    prev_gray, boxes, i = None, [], 0
    assert proc.stdout
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        img = np.frombuffer(buf, np.uint8).reshape(dh, DECODE_W, 3)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if i % DETECT_EVERY == 0:
            boxes = [b for b in detect(img) if b[2] >= 18]
        mv = []
        for x, y, w, h in boxes:  # mouth: lower third, middle half of the face box
            x0, x1 = int(x + w * 0.25), int(x + w * 0.75)
            y0, y1 = int(y + h * 0.62), int(min(dh, y + h * 0.98))
            if prev_gray is None or x1 <= x0 or y1 <= y0:
                mv.append(0.0)
                continue
            a = gray[y0:y1, max(0, x0):x1].astype(np.int16)
            b = prev_gray[y0:y1, max(0, x0):x1].astype(np.int16)
            mv.append(float(np.mean(np.abs(a - b))) if a.size else 0.0)
        dets.append([(x * scale, y * scale, w * scale, h * scale) for x, y, w, h in boxes])
        motion.append(mv)
        prev_gray, i = gray, i + 1
    proc.wait()
    n = len(dets)
    counts = Counter(len(d) for d in dets if d)
    k = min(3, max(counts, key=counts.get)) if counts else 0
    centres = _slots(dets, max(k, 1), W) if k else []
    S = len(centres)
    present = np.zeros((n, S), bool)
    mot = np.zeros((n, S))
    box_acc: list[list[tuple]] = [[] for _ in range(S)]
    for t, (fr, mv) in enumerate(zip(dets, motion, strict=True)):
        for d, m in zip(fr, mv, strict=True):
            cx = d[0] + d[2] / 2
            s = int(np.argmin([abs(cx - c) for c in centres]))
            if abs(cx - centres[s]) < 0.15 * W and (not present[t, s] or m > mot[t, s]):
                present[t, s], mot[t, s] = True, m
                box_acc[s].append(d)
    levels = _levels(wav, n)
    speech = levels > max(np.percentile(levels, 35) + 6, -45) if n else np.zeros(0, bool)
    active = np.full(n, -1)
    if S >= 2:
        z = np.zeros_like(mot)
        for s in range(S):
            on = mot[present[:, s], s]
            if len(on):
                med, iqr = np.median(on), max(np.subtract(*np.percentile(on, [75, 25])), 1e-3)
                z[:, s] = np.where(present[:, s], (mot[:, s] - med) / iqr, -9)
        best = np.argmax(z, axis=1)
        active = np.where(speech & (z.max(axis=1) > 0.3), best, -1)
        active = smooth(active, int(SMOOTH_S / STEP_S), int(MIN_SHOT_S / STEP_S))
    elif S == 1:
        active = np.where(present[:, 0], 0, -1)
    slots = []
    for s in range(S):
        b = np.array(box_acc[s]) if box_acc[s] else np.zeros((1, 4))
        x, y, w, h = np.median(b, axis=0)
        slots.append({"cx": round(float(x + w / 2)), "cy": round(float(y + h / 2)), "w": round(float(w)),
                      "h": round(float(h)), "share": round(float(present[:, s].mean()) if n else 0.0, 3)})
    return {"step": STEP_S, "W": W, "H": H, "frames": n, "slots": slots,
            "present": ["".join("1" if p else "0" for p in row) for row in present] if S else [],
            "active": "".join("-" if a < 0 else str(int(a)) for a in active),
            "detector": "yunet" if FACE_MODEL.is_file() else "haar"}


def smooth(active: np.ndarray, win: int, min_len: int) -> np.ndarray:
    """Majority vote over `win` frames (unknown frames keep the last speaker), then runs shorter than `min_len`
    are absorbed by the previous speaker: a cut only happens for a real turn."""
    a = active.copy()
    last = -1
    for i, v in enumerate(a):  # carry the speaker through pauses and unknown frames
        if v < 0:
            a[i] = last
        else:
            last = v
    out = a.copy()
    h = max(1, win // 2)
    for i in range(len(a)):
        seg = a[max(0, i - h) : i + h + 1]
        seg = seg[seg >= 0]
        if len(seg):
            out[i] = Counter(seg.tolist()).most_common(1)[0][0]
    runs, i = [], 0
    while i < len(out):
        j = i
        while j + 1 < len(out) and out[j + 1] == out[i]:
            j += 1
        runs.append([i, j, out[i]])
        i = j + 1
    for r in range(1, len(runs)):
        if runs[r][1] - runs[r][0] + 1 < min_len:
            runs[r][2] = runs[r - 1][2]
    for s, e, v in runs:
        out[s : e + 1] = v
    return out


def visual_score(track: dict, a: float, b: float) -> float:
    """Share of the clip with a visible face (0.3..1); 0.6 when the recording has no faces at all."""
    if not track or not track.get("slots"):
        return 0.6
    i0, i1 = int(a / track["step"]), max(int(a / track["step"]) + 1, int(b / track["step"]))
    rows = track["present"][i0:i1]
    return round(0.3 + 0.7 * (sum("1" in r for r in rows) / max(len(rows), 1)), 3)


def _crop_on(slot: dict, W: int, H: int, cw: int, ch: int) -> tuple[int, int]:
    x = int(min(max(slot["cx"] - cw / 2, 0), W - cw))
    y = int(min(max(slot["cy"] - ch * 0.4, 0), H - ch))  # face a little above the centre
    return x - x % 2, y - y % 2


def _kf(t: float, x: int, y: int, w: int, h: int, mode: str, layout: str = "crop", region: str = "speaker",
        second: dict | None = None) -> dict:
    k = {"t": round(t, 3), "crop_x": x, "crop_y": y, "crop_width": w, "crop_height": h, "layout": layout,
         "region": region, "transition_mode": mode}
    if second:
        k["second"] = second
    return k


def plan(track: dict, start: float, end: float, W: int, H: int) -> list[dict]:
    """Crop keyframes (clip clock) for one clip. [] means the centred default crop."""
    if not track or not track.get("slots") or W * 16 <= H * 9:
        return []
    cw = int(round(H * 9 / 16 / 2) * 2)
    slots = track["slots"]
    if len(slots) == 1 or (max(s["cx"] + s["w"] / 2 for s in slots) - min(s["cx"] - s["w"] / 2 for s in slots)
                           <= 0.9 * cw):
        mid = {"cx": (max(s["cx"] for s in slots) + min(s["cx"] for s in slots)) / 2, "cy": H / 2}
        x, _ = _crop_on(mid, W, H, cw, H)
        return [_kf(0, x, 0, cw, H, "start", region="speakers" if len(slots) > 1 else "speaker")]
    step = track["step"]
    i0, i1 = int(start / step), max(int(start / step) + 1, int(end / step))
    act = [int(c) if c != "-" else -1 for c in track["active"][i0:i1]]
    if not act or all(a < 0 for a in act):  # nobody identified: the most present person
        s = max(range(len(slots)), key=lambda i: slots[i]["share"])
        act = [s] * max(1, i1 - i0)
    first_known = next(a for a in act if a >= 0)
    act = [first_known if a < 0 else a for a in act]
    runs, i = [], 0
    while i < len(act):
        j = i
        while j + 1 < len(act) and act[j + 1] == act[i]:
            j += 1
        runs.append((i * step, (j + 1) * step, act[i]))
        i = j + 1
    # rapid back-and-forth → split screen of the two seats that talk most in that stretch
    sh = int(min(H, max(s["h"] for s in slots) * 3.2)) // 2 * 2  # each half of the split: head and shoulders, 9:8
    sw = min(int(round(sh * 9 / 8 / 2) * 2), W - W % 2)
    sh = min(sh, int(sw * 8 / 9) // 2 * 2)
    split = [False] * len(runs)
    for r in range(len(runs)):
        window = [q for q in runs if runs[r][0] <= q[0] < runs[r][0] + SPLIT_WINDOW_S]
        if len(window) > SPLIT_SWITCHES:
            for q in range(r, min(len(runs), r + len(window))):
                split[q] = True
    talk = Counter(a for a in act)
    pair = sorted([s for s, _ in talk.most_common(2)] + ([] if len(talk) > 1 else [1 - act[0] if len(slots) > 1 else 0]))
    out, last = [], None
    for (a, _b, s), is_split in zip(runs, split, strict=True):
        if is_split:
            top, bot = slots[pair[0]], slots[pair[-1]]
            x1, y1 = _crop_on(top, W, H, sw, sh)
            x2, y2 = _crop_on(bot, W, H, sw, sh)
            key = ("split", pair[0], pair[-1])
            k = _kf(a, x1, y1, sw, sh, "cut", "split", "speakers",
                    {"crop_x": x2, "crop_y": y2, "crop_width": sw, "crop_height": sh})
        else:
            x, _ = _crop_on(slots[s], W, H, cw, H)
            key = ("crop", s)
            k = _kf(a, x, 0, cw, H, "cut", region=f"speaker-{s}")
        if key != last:
            if not out:
                k["transition_mode"] = "start"
                k["t"] = 0.0
            out.append(k)
            last = key
    return out
