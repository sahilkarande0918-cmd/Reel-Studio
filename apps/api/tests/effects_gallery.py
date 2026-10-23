"""Render every registered effect and transition on real footage and measure that each one changes the picture.

    python tests/effects_gallery.py SOURCE_VIDEO OUT_DIR [START_S]

Per effect: a 1.5 s 540x960 segment with the effect at 0.3 s, compared frame by frame with the same segment rendered
without effects (mean absolute pixel difference, 0-255). Per transition: two segments joined; the output must have
exactly the planned number of frames. Writes gallery.json and a contact sheet.
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.services.editing import base, effects as fx  # noqa: E402

W, H, FPS = 540, 960, 30


def read_frames(p: Path) -> list[np.ndarray]:
    cap, out = cv2.VideoCapture(str(p)), []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(f.astype(np.int16))


def nframes(p: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True,
    )  # fmt: skip
    return int(r.stdout.strip() or 0)


def main(src: str, out: str, start: float = 60.0) -> None:
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    seg = lambda **k: base.Segment(Path(src), start, start + 1.5, 1.5, **k)  # noqa: E731
    ref_p = o / "none.mp4"
    base.render_segment(seg(), ref_p, W, H, FPS)
    ref = read_frames(ref_p)
    rows, sheet = [], []
    for eid, e in fx.EFFECTS.items():
        p = o / f"fx_{eid}.mp4"
        try:
            base.render_segment(seg(effects=[(eid, {"at": 0.3})]), p, W, H, FPS)
            got = read_frames(p)
            diffs = [float(np.abs(a - b).mean()) for a, b in zip(got, ref, strict=False)]
            peak = int(np.argmax(diffs))
            rows.append(
                {
                    "effect": eid,
                    "category": e.category,
                    "frames": len(got),
                    "mean_diff": round(float(np.mean(diffs)), 2),
                    "peak_diff": round(max(diffs), 2),
                    "peak_frame": peak,
                    "ok": len(got) == 45 and max(diffs) > 2.0,
                }
            )
            sheet.append(
                cv2.putText(
                    cv2.resize(got[peak].astype(np.uint8), (180, 320)),
                    eid[:16],
                    (4, 16),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255),
                    1,
                )
            )
        except RuntimeError as err:
            rows.append({"effect": eid, "category": e.category, "ok": False, "error": str(err)[-300:]})
        print(rows[-1], flush=True)
    for tid in fx.TRANSITIONS:
        if tid == "cut":
            continue
        segs = [
            base.Segment(Path(src), start, start + 1.0, 1.0, transition_out=tid, transition_dur=0.4),
            base.Segment(Path(src), start + 20, start + 21.0, 1.0),
        ]
        out_p = o / f"tr_{tid}.mp4"
        try:
            base.render_base(segs, o / f"tr_{tid}", W, H, FPS)
            (o / f"tr_{tid}" / "base.mp4").replace(out_p)
            n, want = nframes(out_p), round(base.total_duration(segs) * FPS)
            rows.append(
                {
                    "transition": tid,
                    "xfade": fx.TRANSITIONS[tid],
                    "frames": n,
                    "expected": want,
                    "ok": n == want,
                }
            )
        except RuntimeError as err:
            rows.append({"transition": tid, "ok": False, "error": str(err)[-300:]})
        print(rows[-1], flush=True)
    (o / "gallery.json").write_text(json.dumps(rows, indent=1))
    while len(sheet) % 8:
        sheet.append(np.zeros_like(sheet[0]))
    cv2.imwrite(
        str(o / "effects-sheet.jpg"),
        np.vstack([np.hstack(sheet[i : i + 8]) for i in range(0, len(sheet), 8)]),
    )
    bad = [r for r in rows if not r["ok"]]
    print(f"{len(rows) - len(bad)}/{len(rows)} ok", [r.get("effect") or r.get("transition") for r in bad])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 60.0)
