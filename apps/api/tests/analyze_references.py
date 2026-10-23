"""Analyse reference reels into style profiles + contact sheets (manual tool, writes outside git).

python tests/analyze_references.py OUT_DIR VIDEO [VIDEO ...] [--describe N]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.services.reference.analyzer import analyze_reference  # noqa: E402


def main(args: list[str]) -> None:
    n = int(args[args.index("--describe") + 1]) if "--describe" in args else 0
    files = [a for a in args[1:] if a.endswith((".mp4", ".mov", ".webm"))]
    out = Path(args[0])
    for f in files:
        t0 = time.perf_counter()
        p = analyze_reference(Path(f), out / Path(f).stem.replace(" ", "-"), describe_frames=n)
        summary = {k: p[k] for k in ("pacing", "motion", "techniques")}
        summary["beat_sync"] = {k: v for k, v in (p.get("beat_sync") or {}).items() if k != "offsets"}
        print(f"== {Path(f).name} ({time.perf_counter() - t0:.0f}s)")
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
