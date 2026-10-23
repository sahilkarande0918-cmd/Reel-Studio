"""End-to-end beat-synced edit from local files (manual tool; the app runs the same code through the worker).

    python tests/auto_edit.py OUT_DIR --profile phonk --duration 16 [--music FILE | --score phonk] CLIP [CLIP ...]

Analyses clips (cached next to OUT_DIR), analyses the music, plans, renders, then measures the result: ffprobe,
exact frame count, loudness (EBU R128) and where the cuts actually landed relative to the beat grid.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.services.clips.analysis import analyze_clip  # noqa: E402
from app.services.editing import audio, pacing, planner, render  # noqa: E402
from app.services.music import beats, score  # noqa: E402
from app.services.reference.analyzer import shots  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--profile", default="phonk")
    ap.add_argument("--duration", type=float, default=16)
    ap.add_argument("--music")
    ap.add_argument("--score")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    infos = []
    for c in a.clips:
        key = hashlib.sha1(f"{Path(c).resolve()}|{Path(c).stat().st_size}".encode()).hexdigest()[:16]
        cache = out.parent / "clip-cache" / f"{key}.json"
        cache.parent.mkdir(exist_ok=True)
        if not cache.exists():
            cache.write_text(json.dumps(analyze_clip(Path(c))))
        infos.append(json.loads(cache.read_text()))
    prof = pacing.PROFILES[a.profile]
    music_path = Path(a.music) if a.music else None
    if a.score:
        music_path = score.write_wav(
            out / "score.wav", score.generate(a.score, prof.default_bpm, a.duration + 12)
        )
    music = beats.analyze(music_path) if music_path else None
    p = planner.plan(infos, prof, a.duration, music)
    (out / "plan.json").write_text(json.dumps(p, indent=1))
    t1 = time.perf_counter()
    res = render.render_plan(
        p,
        [Path(c) for c in a.clips],
        [i.get("duration_s") for i in infos],
        out / "work",
        out / "edit.mp4",
        music_path=music_path,
    )
    t2 = time.perf_counter()
    mp4 = out / "edit.mp4"
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "stream=codec_name,width,height,nb_read_frames,r_frame_rate:format=duration",
            "-of",
            "json",
            str(mp4),
        ],
        capture_output=True,
        text=True,
    ).stdout
    detected = [s for s, _ in shots(mp4)][1:]
    planned = [s["slot"][0] for s in p["segments"]][1:]
    offs = beats.cut_offsets(detected, p["beats"])
    report = {
        **res,
        "profile": a.profile,
        "bpm": p["bpm"],
        "planned_cuts": len(planned),
        "detected_cuts": len(detected),
        "detected_cut_beat_offsets_ms": [o["offset_ms"] for o in offs],
        "reused_shots": p["reused_shots"],
        "loudness": audio.measure(mp4),
        "ffprobe": json.loads(probe),
        "timing_s": {"analysis_plan": round(t1 - t0, 1), "render": round(t2 - t1, 1)},
    }
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
