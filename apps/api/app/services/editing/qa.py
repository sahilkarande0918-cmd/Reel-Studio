"""Measured quality checks on a rendered edit (the actual file, never the plan alone).

- frames: exact frame count = duration × fps
- cuts: for every planned hard cut, the frame with the largest picture change within ±3 frames must be the planned
  frame (offset in ms reported); transitions are checked for a visible change inside their window
- beats: planned cut times vs the beat grid
- black/frozen frames: runs of near-black or identical frames that the plan did not ask for
- loudness: integrated LUFS and true peak of the delivered audio
Results are numbers with pass/fail against stated thresholds; nothing is scored by opinion.
"""

import subprocess
from pathlib import Path

import cv2
import numpy as np

from app.services.editing import audio


def _frames(mp4: Path, size=(135, 240)) -> list[np.ndarray]:
    cap, out = cv2.VideoCapture(str(mp4)), []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(cv2.cvtColor(cv2.resize(f, size), cv2.COLOR_BGR2GRAY).astype(np.int16))


def check(mp4: Path, plan: dict) -> dict:
    fps, dur = plan["fps"], plan["duration"]
    fr = _frames(mp4)
    diff = [0.0] + [float(np.abs(fr[i] - fr[i - 1]).mean()) for i in range(1, len(fr))]
    cuts, transitions = [], []
    for s in plan["segments"][:-1]:
        t = s["slot"][1]
        n = round(t * fps)
        beat = min(plan["beats"], key=lambda b: abs(b - t)) if plan.get("beats") else t
        win = range(max(1, n - 3), min(len(diff), n + 4))
        if not win:
            continue
        if s["transition_out"] == "cut":
            k = max(win, key=lambda i: diff[i])
            cuts.append(
                {
                    "t": t,
                    "frame_offset_ms": round(1000 * (k / fps - t)),
                    "beat_offset_ms": round(1000 * (t - beat)),
                }
            )
        else:
            transitions.append(
                {
                    "t": t,
                    "kind": s["transition_out"],
                    "peak_change": round(max(diff[i] for i in win), 1),
                    "beat_offset_ms": round(1000 * (t - beat)),
                }
            )
    # black = the whole frame is dark (98th percentile), not a night shot whose street lights are bright
    black = sum(1 for f in fr if float(np.percentile(f, 98)) < 24)
    frozen_runs, run = 0, 0
    for d in diff[1:]:
        run = run + 1 if d < 0.05 else 0
        frozen_runs += run == int(fps)  # a full second with no change at all
    loud = audio.measure(mp4)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate:format=duration",
            "-of",
            "json",
            str(mp4),
        ],
        capture_output=True,
        text=True,
    ).stdout
    res = {
        "frames": len(fr),
        "expected_frames": round(dur * fps),
        "hard_cuts": cuts,
        "transitions": transitions,
        "black_frames": black,
        "frozen_seconds": frozen_runs,
        "loudness": loud,
        "probe": probe,
    }
    res["pass"] = {
        "exact_length": len(fr) == res["expected_frames"],
        "cuts_on_frame": all(abs(c["frame_offset_ms"]) <= 1000 / fps + 1 for c in cuts),
        "cuts_on_beat": all(abs(c["beat_offset_ms"]) <= 1000 / fps / 2 + 1 for c in cuts + transitions),
        "transitions_visible": all(t["peak_change"] > 3 for t in transitions),
        "no_unplanned_black": black
        <= sum(1 for s in plan["segments"] for e in s["effects"] if e[0] == "flash") * 3,
        "no_frozen_seconds": frozen_runs == 0,
        "loudness_-14": abs(loud["integrated_lufs"] + 14) <= 1.0,
        "true_peak_<=-1": loud["true_peak_dbtp"] <= -1.0,
    }
    return res
