"""Speaker-aware 9:16 face tracking for podcasts, interviews, films and any talking video (CPU only, 0.2 MB detector).

1. Faces: OpenCV YuNet (MIT, opencv_zoo) on EVERY frame of a 480-px-wide decode at 6 fps (Haar fallback); a missed
   detection keeps the last box for up to 1 s. Shot cuts: big jumps of a 64x36 thumbnail (camera cuts in edited video).
2. Per clip and per shot: faces are linked into tracks (position + size), the speaking face is the one whose mouth
   moves most while there is speech (normalised per track), smoothed with a 1 s majority window and a 1.5 s minimum
   (hysteresis: no switching on every syllable).
3. Camera: follows the speaking face inside each shot with a dead zone (holds still while the face stays well inside
   the frame, eases along when the person moves, never lets the face box leave the crop), cuts with the source at shot
   cuts and on a speaker change. People close enough to share one 9:16 window are framed together; rapid back-and-forth
   between two people who do not fit becomes a stable split screen (both stacked). No face → centred crop. Only real
   camera pixels are shown (no fabricated angles).
"""

import math
import os
import subprocess
import tempfile
import wave
from collections import Counter
from pathlib import Path

import numpy as np

VERSION = 3  # faces.json written by an older build is rebuilt (v1 only had fixed "seats", v2 no exact cuts)
STEP_S = 1 / 6
DECODE_W = 480
HOLD_S = 1.0
CUT_DIFF = 26.0  # mean |Δ| (0..255) of a 64x36 grey thumbnail between frames 1/6 s apart
MIN_SHOT_S = 1.5
SMOOTH_S = 1.0
PAN_S = 0.67
SPLIT_SWITCHES, SPLIT_WINDOW_S = 3, 8.0  # >= 3 speaker changes inside 8 s of one shot → split screen
FACE_MODEL = Path(os.environ.get("FACE_MODEL", r"D:\ReelStudio\models\yunet\face_detection_yunet_2023mar.onnx"))


def _detector(w: int, h: int):
    import cv2

    if FACE_MODEL.is_file():
        det = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (w, h), 0.6, 0.3, 50)

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


def shot_cuts(thumbs: np.ndarray, duration_s: float) -> list[float]:
    """Exact camera-cut times (s) from 64x36 grey thumbnails of EVERY source frame: a frame that differs a lot from
    the previous one and much more than the frames just before it (camera moves and flashes are not cuts)."""
    n = len(thumbs)
    if n < 3:
        return []
    d = np.abs(np.diff(thumbs.astype(np.int16), axis=0)).mean(axis=(1, 2))  # d[k]: frame k+1 vs frame k
    fdt = duration_s / n
    out: list[float] = []
    for k in range(len(d)):
        base = np.median(d[max(0, k - 8) : k]) if k else 0.0
        if d[k] > 18 and d[k] > 3 * base + 4 and (not out or (k + 1) * fdt - out[-1] >= 0.2):
            out.append(round((k + 1) * fdt, 3))
    return out


def analyze(src: Path, wav: Path, W: int, H: int, duration_s: float) -> dict:
    """Faces (centre x/y, w, h, mouth motion) per 1/6 s, exact shot cuts and speech for the whole recording (cached
    by the caller in faces.json). One decode: 6 fps for faces, every frame as a tiny thumbnail for cuts."""
    import cv2

    dh = int(round(H * DECODE_W / W / 2) * 2)
    scale = W / DECODE_W
    fd, name = tempfile.mkstemp(suffix=".gray")
    os.close(fd)  # ffmpeg writes it; Windows cannot delete a file this process still holds open
    tmp = Path(name)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex",
                             f"[0:v]split=2[a][b];[a]fps=6,scale={DECODE_W}:{dh}[fa];[b]scale=64:36,format=gray[fb]",
                             "-map", "[fa]", "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1",
                             "-map", "[fb]", "-fps_mode", "passthrough", "-f", "rawvideo", str(tmp)],
                            stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    detect = _detector(DECODE_W, dh)
    size = DECODE_W * dh * 3
    faces: list[list[list[float]]] = []
    cuts: list[int] = []
    prev_gray = prev_thumb = None
    last, last_i, i = [], -99, 0
    held_at: list[bool] = []
    assert proc.stdout
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        img = np.frombuffer(buf, np.uint8).reshape(dh, DECODE_W, 3)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thumb = cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA).astype(np.int16)
        cut = prev_thumb is not None and float(np.mean(np.abs(thumb - prev_thumb))) > CUT_DIFF
        if cut:
            cuts.append(i)
            last = []
        boxes = [b for b in detect(img) if b[2] >= 14]
        held = False
        if boxes:
            last, last_i = boxes, i
        elif last and i - last_i <= HOLD_S / STEP_S:
            boxes, held = last, True
        fr = []
        for x, y, w, h in boxes:  # mouth: lower third, middle half of the face box
            m = 0.0
            x0, x1 = max(0, int(x + w * 0.25)), int(x + w * 0.75)
            y0, y1 = max(0, int(y + h * 0.62)), int(min(dh, y + h * 0.98))
            if prev_gray is not None and not cut and not held and x1 > x0 and y1 > y0:
                a = gray[y0:y1, x0:x1].astype(np.int16)
                b = prev_gray[y0:y1, x0:x1].astype(np.int16)
                m = float(np.mean(np.abs(a - b))) if a.size else 0.0
            fr.append([round((x + w / 2) * scale), round((y + h / 2) * scale), round(w * scale), round(h * scale),
                       round(m, 2)])
        faces.append(fr)
        held_at.append(held)
        prev_gray, prev_thumb, i = gray, thumb, i + 1
    proc.wait()
    n = len(faces)
    try:
        thumbs = np.fromfile(tmp, np.uint8)
        thumbs = thumbs[: len(thumbs) // (64 * 36) * 64 * 36].reshape(-1, 36, 64)
        cuts_s = shot_cuts(thumbs, duration_s)
    finally:
        tmp.unlink(missing_ok=True)
    blocked = False
    after_cut = {math.ceil(c / STEP_S - 1e-6) for c in cuts_s}
    for k in range(n):  # a box held over a cut belongs to the previous shot; mouth motion across a cut is noise
        if k in after_cut:
            blocked = True
            faces[k] = [[*f[:4], 0.0] for f in faces[k]]
        if not held_at[k]:
            blocked = k in after_cut and not faces[k]
        elif blocked:
            faces[k] = []
    levels = _levels(wav, n)
    speech = levels > max(np.percentile(levels, 35) + 6, -45) if n else np.zeros(0, bool)
    return {"version": VERSION, "step": STEP_S, "W": W, "H": H, "frames": n, "cuts": cuts, "cuts_s": cuts_s,
            "faces": faces,
            "speech": "".join("1" if s else "0" for s in speech),
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
    first = next((v for v in a if v >= 0), -1)
    a[a < 0] = first  # frames before anyone is known take the first speaker
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
    if not track or track.get("version") != VERSION or not any(track["faces"]):
        return 0.6
    i0 = int(a / track["step"])
    rows = track["faces"][i0 : max(i0 + 1, int(b / track["step"]))]
    return round(0.3 + 0.7 * (sum(bool(r) for r in rows) / max(len(rows), 1)), 3)


def _tracks(frames: list[list[list[float]]]) -> list[dict[int, list[float]]]:
    """Faces of one shot linked over time: per frame {track id: face}. Greedy nearest match on position and size."""
    out: list[dict[int, list[float]]] = []
    last: dict[int, list[float]] = {}
    nxt = 0
    for fr in frames:
        cur: dict[int, list[float]] = {}
        for f in sorted(fr, key=lambda f: -f[2]):
            best, bd = None, 0.0
            for t, g in last.items():
                d = abs(f[0] - g[0]) + abs(f[1] - g[1])
                if t not in cur and d < 0.8 * max(f[2], g[2]) and 0.55 < f[2] / max(g[2], 1) < 1.8 and (best is None or d < bd):
                    best, bd = t, d
            if best is None:
                best, nxt = nxt, nxt + 1
            cur[best] = f
        out.append(cur)
        last = {**last, **cur}  # a face missing for a frame keeps its last place
    return out


def _even(v: float) -> int:
    return int(v) - int(v) % 2


def _x_for(cx: float, W: int, cw: int) -> int:
    return _even(min(max(cx - cw / 2, 0), W - cw))


def _kf(t: float, x: int, y: int, w: int, h: int, mode: str, layout: str = "crop", region: str = "speaker",
        second: dict | None = None) -> dict:
    k = {"t": round(max(t, 0.0), 3), "crop_x": x, "crop_y": y, "crop_width": w, "crop_height": h, "layout": layout,
         "region": region, "transition_mode": mode}
    if second:
        k["second"] = second
    return k


def _shot(track: dict, a: int, b: int, W: int, H: int, cw: int) -> list[tuple]:
    """Camera for frames [a, b) of one shot: [(frame, kind, x, extra)] with kind "cut" | "ease" | "split"."""
    tr = _tracks(track["faces"][a:b])
    n = b - a
    sizes: dict[int, list[float]] = {}
    for fr in tr:
        for t, f in fr.items():
            sizes.setdefault(t, []).append(f[2])
    if not sizes:
        return [(a, "cut", _x_for(W / 2, W, cw), "none")]
    big = max(np.median(v) for v in sizes.values())
    # people in the scene, not passers-by: big enough and on screen for a good part of the shot
    main = {t for t, v in sizes.items() if np.median(v) >= 0.5 * big and len(v) >= max(2, 0.25 * n)} or \
        {max(sizes, key=lambda t: len(sizes[t]))}
    speech = track["speech"][a:b]
    # mouth motion averaged over ~1 s per person (a talking mouth opens and closes; one frame says little)
    win = max(1, int(SMOOTH_S / STEP_S))
    mot: dict[int, np.ndarray] = {}
    for t in main:
        raw = np.array([fr[t][4] if t in fr else np.nan for fr in tr])
        ok = ~np.isnan(raw)
        csum, cnt = np.cumsum(np.where(ok, raw, 0.0)), np.cumsum(ok)
        lo = np.maximum(np.arange(n) - win // 2, 0)
        hi = np.minimum(np.arange(n) + win // 2, n - 1)
        tot = csum[hi] - np.where(lo > 0, csum[lo - 1], 0.0)
        num = cnt[hi] - np.where(lo > 0, cnt[lo - 1], 0)
        mot[t] = np.where(ok, tot / np.maximum(num, 1), np.nan)
    med = {t: float(np.nanmedian(mot[t])) if np.isfinite(mot[t]).any() else 0.0 for t in main}
    iqr = {t: max(float(np.subtract(*np.nanpercentile(mot[t], [75, 25]))) if np.isfinite(mot[t]).any() else 0.0, 0.3)
           for t in main}
    act = np.full(n, -1)
    prev = -1
    for k, fr in enumerate(tr):
        here = [t for t in main if t in fr]
        if len(here) == 1:
            act[k] = here[0]
        elif len(here) > 1:
            # the moving mouth while someone talks, weighted towards the larger (nearer) face: a guard in the
            # background has to be clearly speaking to take the camera from the person in front
            talk = k < len(speech) and speech[k] == "1"
            z = {t: (mot[t][k] - med[t]) / iqr[t] * talk + 2.0 * fr[t][2] / big for t in here}
            best = max(z, key=z.get)
            act[k] = prev if prev in z and z[prev] >= z[best] - 0.5 else best  # hysteresis: a clear winner only
        prev = act[k] if act[k] >= 0 else prev
    if (act < 0).all():
        act[:] = max(main, key=lambda t: len(sizes[t]))
    act = smooth(act, int(SMOOTH_S / STEP_S), int(MIN_SHOT_S / STEP_S))
    # desired camera centre per frame
    want, lastc = np.zeros(n), None
    for k, fr in enumerate(tr):
        here = [fr[t] for t in main if t in fr]
        span = (min(f[0] - f[2] / 2 for f in here), max(f[0] + f[2] / 2 for f in here)) if here else None
        if span and len(here) > 1 and span[1] - span[0] <= 0.8 * cw:
            c = (span[0] + span[1]) / 2  # everyone fits: frame the group, nothing to switch
        elif act[k] in fr:
            c = fr[act[k]][0]
        else:
            c = lastc if lastc is not None else (here[0][0] if here else W / 2)
        want[k] = lastc = c
    # split screen: two main people far apart and a rapid back-and-forth between them in this shot
    switches = [k for k in range(1, n) if act[k] != act[k - 1]]
    two = [t for t in main if sum(t in fr for fr in tr) >= 0.7 * n]
    if len(two) == 2 and n * STEP_S >= 6 and any(
            sum(1 for s in switches if k <= s < k + SPLIT_WINDOW_S / STEP_S) >= SPLIT_SWITCHES for k in switches):
        left, right = sorted(two, key=lambda t: np.median([fr[t][0] for fr in tr if t in fr]))
        pos = {t: np.median([fr[t] for fr in tr if t in fr], axis=0) for t in (left, right)}
        if abs(pos[right][0] - pos[left][0]) > 0.8 * cw:
            return [(a, "split", 0, (pos[left], pos[right]))]
    # dead-zone camera: hold still while the face stays well inside, ease along when the person moves, cut on a
    # speaker change; the face box never leaves the crop
    k_med = np.array([np.median(want[max(0, k - 2) : k + 3]) for k in range(n)])
    out = [(a, "cut", _x_for(k_med[0], W, cw), int(act[0]))]
    cam, k = k_med[0], 1
    pan_f = max(2, int(round(PAN_S / STEP_S)))
    while k < n:
        fr = tr[k]
        face_w = fr[act[k]][2] if act[k] in fr else 0.3 * cw
        dz = max(8.0, min(0.12 * cw, (cw - face_w) / 2 - 12))
        if act[k] != act[k - 1] and abs(k_med[k] - cam) > dz:
            cam = k_med[k]
            out.append((a + k, "cut", _x_for(cam, W, cw), int(act[k])))
        elif abs(k_med[k] - cam) > dz:
            e = min(n - 1, k + pan_f)
            out.append((a + k, "ease", _x_for(cam, W, cw), int(act[k])))  # hold until the move starts
            cam = k_med[e]
            out.append((a + e, "ease", _x_for(cam, W, cw), int(act[k])))
            k = e
        k += 1
    return out


def plan(track: dict, start: float, end: float, W: int, H: int) -> list[dict]:
    """Crop keyframes (clip clock) for one clip. [] means the centred default crop."""
    if not track or track.get("version") != VERSION or W * 16 <= H * 9:
        return []
    step = track["step"]
    i0 = int(start / step)
    i1 = min(track["frames"], max(i0 + 1, int(round(end / step))))
    if i1 <= i0 or not any(track["faces"][i0:i1]):
        return []
    cw = _even(round(H * 9 / 16))
    # shots between exact cut times; each uses the face frames sampled after its first source frame
    edges = [start, *[c for c in track["cuts_s"] if start < c < end], end]
    keys: list[dict] = []
    region, who = 0, None
    for s0, s1 in zip(edges, edges[1:], strict=False):
        a = min(max(math.ceil(s0 / step - 1e-6), i0), i1 - 1)
        b = max(a + 1, min(math.ceil(s1 / step - 1e-6), i1))
        for f, kind, x, extra in _shot(track, a, b, W, H, cw):
            t = (s0 if f == a else f * step) - start
            if kind == "split":
                fl, fr = extra
                sh = min(H, int(max(fl[3], fr[3]) * 3.2)) // 2 * 2  # each half: head and shoulders, 9:8
                sw = min(_even(round(sh * 9 / 8)), W - W % 2)
                sh = min(sh, int(sw * 8 / 9) // 2 * 2)
                ys = [_even(min(max(p[1] - sh * 0.4, 0), H - sh)) for p in (fl, fr)]
                keys.append(_kf(t, _x_for(fl[0], W, sw), ys[0], sw, sh, "cut", "split", "speakers",
                                {"crop_x": _x_for(fr[0], W, sw), "crop_y": ys[1], "crop_width": sw, "crop_height": sh}))
                who = None
                continue
            # a new speaker inside a shot is a virtual camera cut (may get a transition); a source shot cut keeps
            # the region so the renderer does not add a fade on top of the film's own cut
            if kind == "cut" and f != a and extra != who:
                region += 1
            who = extra
            keys.append(_kf(t, x, 0, cw, H, kind, region=f"speaker-{region}"))
    keys.sort(key=lambda k: k["t"])
    out: list[dict] = []
    for k in keys:  # one keyframe per instant (the later one wins, the earlier one's cut stays a cut)
        if out and k["t"] - out[-1]["t"] < 1e-3:
            out[-1] = {**k, "t": out[-1]["t"], "transition_mode": out[-1]["transition_mode"]}
        else:
            out.append(k)
    out[0] = {**out[0], "t": 0.0, "transition_mode": "start"}
    return out
