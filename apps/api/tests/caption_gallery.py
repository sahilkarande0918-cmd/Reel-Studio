"""Render caption presets with the export compiler (manual measured tool).

    python tests/caption_gallery.py OUT_DIR BACKGROUND.mp4 [--all]

One preset per family by default (23), or all 100 with --all. Each preset is a 2.4 s render of the same phrase with
evenly spaced SYNTHETIC word times (style check only, not speech alignment). Measures that the caption pixels change
while words are spoken and writes a labelled contact sheet.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.services.generation.narration import _cli  # noqa: E402
from app.services.rendering import caption_presets as cp  # noqa: E402
from app.services.rendering import compose, timeline  # noqa: E402

PHRASE = "Upload your clips and get a finished reel".split()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("background")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    presets = cp.PRESETS if a.all else [next(p for p in cp.PRESETS if p["family"] == f) for f in cp.FAMILIES]
    tiles, report = [], []
    for p in presets:
        d = out / p["id"]
        d.mkdir(exist_ok=True)
        shutil.copyfile(a.background, d / "bg.mp4")
        words = [{"text": w, "start": round(0.2 + i * 0.26, 3), "end": round(0.2 + i * 0.26 + 0.24, 3), "isCode": False}
                 for i, w in enumerate(PHRASE)]
        doc = {"id": "00000000-0000-0000-0000-000000000000", "schemaVersion": 1, "fps": 30, "width": 1080, "height": 1920,
               "duration": 2.4, "assets": {"bg": {"id": "bg", "kind": "video", "src": "bg.mp4", "width": 1080, "height": 1920, "duration": 2.4}},
               "tracks": [{"id": "v", "kind": "video", "items": [{"id": "v", "type": "video", "assetId": "bg", "start": 0, "duration": 2.4,
                           "sourceStart": 0, "sourceEnd": 2.4, "volume": 0, "cropKeyframes": [{"t": 0, "crop_x": 0, "crop_y": 0,
                           "crop_width": 1080, "crop_height": 1920, "layout": "crop", "region": "full", "transition_mode": "start"}]}]},
                          {"id": "c", "kind": "caption", "items": [{"id": "c", "type": "caption", "start": 0, "duration": 2.4, "words": words}]}],
               "brand": timeline.brand_snapshot(None, "")[0], "renderSettings": {"quality": "draft"},
               "captionStyle": cp.style_for(p["id"], dict(timeline.CAPTION_STYLE), 1920)}
        timeline.validate(doc)
        compose.write_project(doc, d)
        r = subprocess.run(_cli() + ["render", "--quality", "draft", "--workers", "6", "--output", "out.mp4", "."], cwd=d,
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            report.append({"id": p["id"], "error": (r.stdout + r.stderr)[-400:]})
            continue
        cap = cv2.VideoCapture(str(d / "out.mp4"))
        fr = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            fr.append(f)
        change = float(np.mean([np.abs(fr[i].astype(int) - fr[i - 1].astype(int)).mean() for i in range(1, len(fr))]))
        report.append({"id": p["id"], "frames": len(fr), "mean_change": round(change, 2)})
        tile = cv2.resize(fr[int(len(fr) * 0.75)], (180, 320))
        tiles.append(cv2.putText(tile, p["id"][:22], (4, 312), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1))
    while len(tiles) % 8:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(out / "sheet.jpg"), np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
