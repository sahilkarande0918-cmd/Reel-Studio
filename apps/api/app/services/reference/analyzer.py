"""Reference Style Analyzer: turn any reference reel into a structured, evidence-backed style profile.

Shots (PySceneDetect), per-frame motion (OpenCV Farneback optical flow at 240 px: magnitude, zoom = flow divergence,
pan = mean flow), flashes (luma spikes), palette (k-means per shot), on-screen text boxes (RapidOCR), music (librosa
beats) and how cuts sit on the beat. Every number is measured from the file; the optional local-VLM pass adds words
about composition and effects for a few key frames and is labelled as model description, not measurement.

Memory stays bounded: frames are streamed at 240 px wide, never held for the whole video.
"""

import base64
import json
import logging
import subprocess
from pathlib import Path

import cv2
import numpy as np

from app.services.music import beats

log = logging.getLogger(__name__)
W = 240  # analysis width


def probe(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), {})
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    return {
        "duration_s": float(d.get("format", {}).get("duration", 0)),
        "width": v.get("width"),
        "height": v.get("height"),
        "fps": round(int(num) / max(int(den), 1), 3),
        "has_audio": any(s["codec_type"] == "audio" for s in d.get("streams", [])),
    }


def shots(path: Path) -> list[tuple[float, float]]:
    from scenedetect import AdaptiveDetector, ContentDetector, detect

    found = detect(str(path), ContentDetector(threshold=27))
    if len(found) < 2:  # slow dissolves and moving-camera reels: adaptive threshold catches more
        found = detect(str(path), AdaptiveDetector())
    return [(s.get_seconds(), e.get_seconds()) for s, e in found]


def frame_series(path: Path, fps: float) -> dict:
    """Per-frame luma, flow magnitude, divergence (zoom) and mean flow (pan), streamed."""
    cap = cv2.VideoCapture(str(path))
    prev, out = None, {"luma": [], "mag": [], "div": [], "dx": [], "dy": []}
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h = int(frame.shape[0] * W / frame.shape[1])
        g = cv2.cvtColor(cv2.resize(frame, (W, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        out["luma"].append(float(g.mean()))
        if prev is None:
            for k in ("mag", "div", "dx", "dy"):
                out[k].append(0.0)
        else:
            f = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            fx, fy = f[..., 0], f[..., 1]
            out["mag"].append(float(np.sqrt(fx**2 + fy**2).mean()))
            # divergence > 0: content expands from the centre (zoom in / push)
            out["div"].append(float((np.gradient(fx, axis=1) + np.gradient(fy, axis=0)).mean()))
            out["dx"].append(float(fx.mean()))
            out["dy"].append(float(fy.mean()))
        prev = g
    cap.release()
    return {k: np.array(v) for k, v in out.items()}


def flashes(luma: np.ndarray, fps: float) -> list[dict]:
    """A frame much brighter (or darker) than both neighbours a few frames away: white/black flash."""
    out = []
    for i in range(2, len(luma) - 2):
        base = (luma[i - 2] + luma[i + 2]) / 2
        jump = luma[i] - base
        if abs(jump) > 45 and (not out or i / fps - out[-1]["t"] > 0.2):
            out.append(
                {
                    "t": round(i / fps, 3),
                    "kind": "white" if jump > 0 else "black",
                    "delta": round(float(jump)),
                }
            )
    return out


def palette(frame: np.ndarray, k: int = 5) -> list[str]:
    px = cv2.resize(frame, (64, 64)).reshape(-1, 3).astype(np.float32)
    _, labels, centers = cv2.kmeans(
        px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS
    )
    order = np.argsort(-np.bincount(labels.ravel(), minlength=k))
    return ["#%02x%02x%02x" % tuple(int(c) for c in centers[i][::-1]) for i in order]


def grab(path: Path, t: float) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    cap.release()
    return f if ok else None


def transition_kind(series: dict, i: int, fps: float, flash_ts: set[float]) -> str:
    """How the cut at frame i is made, from the frames around it."""
    t = i / fps
    if any(abs(t - f) <= 0.1 for f in flash_ts):
        return "flash"
    lo, hi = max(1, i - 3), min(len(series["mag"]), i + 3)
    around = series["mag"][lo:hi]
    if len(around) and around.max() > 6:
        return "whip/motion-blur"
    div = series["div"][lo:hi]
    if len(div) and abs(div).max() > 0.08:
        return "zoom-through"
    luma = series["luma"]
    if i > 6 and i + 6 < len(luma) and min(luma[i - 6 : i + 6]) < 25:
        return "dip-to-black"
    return "hard cut"


def describe(path: Path, times: list[float], model: str | None = None) -> list[dict]:
    """Optional local-VLM (Ollama, qwen2.5vl) description of key frames. Labelled as model text."""
    import httpx

    from app.core.config import get_settings

    s = get_settings()
    out = []
    for t in times:
        f = grab(path, t)
        if f is None:
            continue
        ok, jpg = cv2.imencode(
            ".jpg",
            cv2.resize(
                f, (int(f.shape[1] * 512 / max(f.shape[:2])), int(f.shape[0] * 512 / max(f.shape[:2])))
            ),
        )
        prompt = (
            "This is one frame of a short-form video used as an editing reference. In 2 short sentences describe the "
            "layout/composition, any graphics, cards, mockups or text treatment, and visible effects (blur, glow, "
            "split screen, zoom). Describe technique only; do not name people or brands."
        )
        try:
            r = httpx.post(
                f"{s.ollama_url}/api/chat",
                json={
                    "model": model or s.ollama_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [base64.b64encode(jpg.tobytes()).decode()],
                        }
                    ],
                    "stream": False,
                    "keep_alive": "2m",
                    "options": {"temperature": 0, "seed": 7, "num_ctx": 4096},
                },
                timeout=180,
            )
            r.raise_for_status()
            out.append({"t": round(t, 2), "text": r.json()["message"]["content"].strip()})
        except (httpx.HTTPError, KeyError) as e:
            log.warning("VLM description unavailable: %s", e)
            break
    return out


def techniques(p: dict) -> list[str]:
    """Transferable editing techniques implied by the measurements (rule-based, explainable)."""
    out = []
    med = p["pacing"]["median_shot_s"]
    if med and med < 0.9:
        out.append(f"Rapid montage: median shot {med:.2f} s")
    elif med and med > 3:
        out.append(f"Lingering shots / designed scenes: median shot {med:.1f} s")
    if p["flashes"]:
        out.append(f"Flash accents ({len(p['flashes'])}): white/black frames on hits")
    kinds = p["transitions"]
    for k in ("whip/motion-blur", "zoom-through", "dip-to-black"):
        n = sum(1 for x in kinds if x["kind"] == k)
        if n:
            out.append(f"{k} transitions: {n}")
    if p["motion"]["zoom_in_share"] > 0.25:
        out.append(f"Constant push-ins: content expands in {p['motion']['zoom_in_share']:.0%} of frames")
    if p["motion"]["mean_flow"] > 2.5:
        out.append("High camera/subject motion throughout")
    sync = p.get("beat_sync")
    if sync and sync["cuts_within_60ms"] >= 0.5:
        out.append(
            f"Cuts on the beat: {sync['cuts_within_60ms']:.0%} of cuts within 60 ms of a beat ({sync['tempo_bpm']} BPM)"
        )
    if p["text"]["frames_with_text"] >= 0.5:
        out.append(f"Text-led: on-screen text in {p['text']['frames_with_text']:.0%} of sampled shots")
    return out


def analyze_reference(path: Path, out_dir: Path | None = None, describe_frames: int = 0) -> dict:
    from app.services.screen_analysis import ocr

    meta = probe(path)
    fps = meta["fps"] or 30
    cuts = shots(path) or [(0.0, meta["duration_s"])]
    series = frame_series(path, fps)
    fl = flashes(series["luma"], fps)
    fl_ts = {f["t"] for f in fl}
    shot_rows, text_hits, transitions = [], 0, []
    for n, (a, b) in enumerate(cuts):
        i, j = int(a * fps), max(int(b * fps), int(a * fps) + 1)
        mid = grab(path, (a + b) / 2)
        texts = ocr.ocr_frame(mid, min_conf=0.75) if mid is not None else []
        text_hits += bool(texts)
        H = meta["height"] or 1
        shot_rows.append(
            {
                "n": n + 1,
                "start_s": round(a, 3),
                "end_s": round(b, 3),
                "duration_s": round(b - a, 3),
                "motion": round(float(series["mag"][i:j].mean()), 2) if j > i else 0,
                "zoom": round(float(series["div"][i:j].mean()) * 100, 2) if j > i else 0,
                "pan": [round(float(series["dx"][i:j].mean()), 2), round(float(series["dy"][i:j].mean()), 2)]
                if j > i
                else [0, 0],
                "brightness": round(float(series["luma"][i:j].mean()), 1) if j > i else 0,
                "palette": palette(mid) if mid is not None else [],
                "text": [
                    {"text": x["text"], "y": round(x["box"][1] / H, 2), "h": round(x["box"][3] / H, 3)}
                    for x in texts[:6]
                ],
            }
        )
        if n:
            transitions.append({"t": round(a, 3), "kind": transition_kind(series, i, fps, fl_ts)})
    durs = [r["duration_s"] for r in shot_rows]
    windows = np.arange(0, meta["duration_s"], 2.0)
    profile = {
        "file": path.name,
        "meta": meta,
        "shots": shot_rows,
        "transitions": transitions,
        "flashes": fl,
        "pacing": {
            "shots": len(durs),
            "median_shot_s": round(float(np.median(durs)), 3) if durs else None,
            "cuts_per_min": round(len(durs) / max(meta["duration_s"], 1e-6) * 60, 1),
            "curve_cuts_per_2s": [int(sum(1 for a, _ in cuts if w <= a < w + 2)) for w in windows],
        },
        "motion": {
            "mean_flow": round(float(series["mag"].mean()), 2),
            "zoom_in_share": round(float((series["div"] > 0.01).mean()), 3),
            "zoom_out_share": round(float((series["div"] < -0.01).mean()), 3),
            "peak_flow": round(float(series["mag"].max(initial=0)), 2),
        },
        "text": {"frames_with_text": round(text_hits / max(len(shot_rows), 1), 2)},
        "colour": {"palette": palette(grab(path, meta["duration_s"] / 2)) if meta["duration_s"] else []},
    }
    if meta["has_audio"]:
        music = beats.analyze(path)
        profile["music"] = {k: v for k, v in music.items() if k not in ("onsets",)}
        if music.get("beats"):
            offs = beats.cut_offsets([a for a, _ in cuts[1:]], music["beats"])
            within = sum(1 for o in offs if abs(o["offset_ms"]) <= 60) / max(len(offs), 1)
            profile["beat_sync"] = {
                "tempo_bpm": music["tempo_bpm"],
                "cuts_within_60ms": round(within, 2),
                "median_abs_offset_ms": int(np.median([abs(o["offset_ms"]) for o in offs])) if offs else None,
                "offsets": offs,
            }
    if describe_frames:
        key = sorted(shot_rows, key=lambda r: -r["duration_s"])[:describe_frames]
        profile["vlm_descriptions"] = describe(path, [(r["start_s"] + r["end_s"]) / 2 for r in key])
    profile["techniques"] = techniques(profile)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "style.json").write_text(json.dumps(profile, indent=1))
        contact_sheet(path, shot_rows, out_dir / "contact.jpg")
    return profile


def contact_sheet(path: Path, rows: list[dict], out: Path, cols: int = 8, tw: int = 160) -> None:
    tiles = []
    for r in rows[:64]:
        f = grab(path, (r["start_s"] + r["end_s"]) / 2)
        if f is None:
            continue
        th = int(f.shape[0] * tw / f.shape[1])
        f = cv2.resize(f, (tw, th))
        cv2.rectangle(f, (0, 0), (tw, 16), (0, 0, 0), -1)
        cv2.putText(
            f, f"{r['n']} {r['start_s']:.1f}s", (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1
        )
        tiles.append(f)
    if not tiles:
        return
    th = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, th - t.shape[0], 0, 0, cv2.BORDER_CONSTANT) for t in tiles]
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i : i + cols]) for i in range(0, len(tiles), cols)])
    cv2.imwrite(str(out), grid)
