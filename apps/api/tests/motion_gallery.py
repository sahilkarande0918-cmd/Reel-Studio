"""Render every motion-graphics template once (manual measured tool, like effects_gallery.py).

    python tests/motion_gallery.py OUT_DIR IMAGE_OR_CLIP [IMAGE_OR_CLIP ...] [--seconds 2.6] [--only a,b]

Builds one canonical timeline with the templates back to back (media slots filled from the given files), compiles it
with the export compiler, renders with the local Hyperframes CLI, then measures each template's window: the picture
must change during its animation (not a static or empty frame) and a contact sheet is written for visual review.
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
from app.services.rendering import compose, motion, timeline  # noqa: E402

SAMPLE = {
    "kinetic_title": {"text": "Edit like a studio", "emphasis": "studio"},
    "blur_reveal": {"text": "Reel Studio", "subtitle": "From raw clips to a finished reel"},
    "stagger_lines": {"lines": "Upload|Describe|Render"},
    "typewriter": {"text": "make a professional phonk edit"},
    "masked_text": {"text": "On beat"},
    "counter": {"value": "24", "suffix": " effects", "label": "built in"},
    "floating_cards": {"title": "Why creators switch", "cards": "Beat-synced|Runs locally|Free", "notes": "Cuts land on the music|Your files stay on your machine|No paid render cloud"},
    "browser_mockup": {"title": "Your studio in the browser", "url": "reelstudio.app", "headline": "Raw clips in. Reels out.", "button": "Start"},
    "phone_mockup": {"caption": "Made for 9:16"},
    "laptop_mockup": {"title": "Edit on the timeline"},
    "split_screen": {"left": "Raw", "right": "Edited"},
    "info_list": {"title": "How it works", "items": "Upload your clips|Describe the edit|Download the reel"},
    "chat_bubbles": {"messages": "Can you cut this to the beat?|Done. 16 seconds, on every beat.|Perfect"},
    "calendar": {"month": "POSTING PLAN", "day": "18", "note": "Reel goes live on the 18th"},
    "bar_chart": {"title": "Shots per edit", "labels": "Calm|Clean|Energetic|Phonk", "values": "4|8|14|27"},
    "stat_ring": {"percent": "100", "label": "cuts on the beat"},
    "logo_reveal": {"name": "Reel Studio", "tagline": "AI video studio"},
    "cta_button": {"headline": "Make your first edit", "button": "Try it free", "detail": "Runs on your own machine"},
    "pricing_card": {"plan": "Local", "price": "₹0", "features": "Unlimited edits|Beat-synced cuts|Instagram ready"},
    "lower_third": {"name": "Reel Studio", "role": "AI video studio"},
    "light_sweep": {},
    "glow_arc": {"text": "Light up your launch"},
    "shape_burst": {"text": "NEW"},
    "grid_gallery": {"title": "Your footage"},
    "notifications": {"app": "Reels", "items": "New follower|12 new comments|Your reel is trending"},
    "media_card": {"label": "Your clip, framed"},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("media", nargs="+")
    ap.add_argument("--seconds", type=float, default=2.6)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    names = [n for n in motion.TEMPLATES if not a.only or n in a.only.split(",")]
    assets, ids = {}, []
    for i, m in enumerate(a.media):
        p = Path(m)
        src = f"media-{i}{p.suffix.lower()}"
        shutil.copyfile(p, out / src)
        kind = "image" if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else "video"
        assets[f"media-{i}"] = {"id": f"media-{i}", "kind": kind, "src": src}
        ids.append(f"media-{i}")
    items = []
    for n, name in enumerate(names):
        k = motion.TEMPLATES[name]["media"]
        items.append({"id": f"t{n}", "type": "motion", "start": round(n * a.seconds, 3), "duration": a.seconds,
                      "template": name, "fields": SAMPLE.get(name, {}), "media": [ids[(n + j) % len(ids)] for j in range(k)], "intensity": 0.7})
    doc = {
        "id": "00000000-0000-0000-0000-000000000000", "schemaVersion": 1, "title": "motion gallery", "fps": 30,
        "width": 1080, "height": 1920, "duration": round(len(items) * a.seconds, 3), "assets": assets,
        "tracks": [{"id": "graphics", "kind": "overlay", "items": items}],
        "brand": {**timeline.brand_snapshot(None, "")[0], "name": "Reel Studio",
                  "colors": {"background": "#1F2618", "text": "#FCF9F4", "accent": "#C8E06B"}},
        "captionStyle": {**timeline.CAPTION_STYLE, "preset": "highlight-word"}, "stylePreset": "focus",
        "renderSettings": {"quality": "draft"},
    }
    doc = json.loads(json.dumps(doc))
    timeline.validate(doc)
    compose.write_project(doc, out)
    r = subprocess.run(_cli() + ["render", "--quality", "draft", "--workers", "8", "--output", "out.mp4", "."], cwd=out,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
    cap = cv2.VideoCapture(str(out / "out.mp4"))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.resize(f, (135, 240)))
    report, tiles = [], []
    for it in items:
        a0, a1 = int(it["start"] * 30), int((it["start"] + it["duration"]) * 30)
        win = frames[a0:a1]
        change = float(np.mean([np.abs(win[i].astype(int) - win[i - 1].astype(int)).mean() for i in range(1, len(win))])) if len(win) > 1 else 0
        mid = win[len(win) // 2] if win else np.zeros((240, 135, 3), np.uint8)
        report.append({"template": it["template"], "mean_change": round(change, 2), "animated": change > 0.15,
                       "not_blank": float(mid.std()) > 8})
        tiles.append(cv2.putText(mid.copy(), it["template"][:16], (4, 232), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1))
    while len(tiles) % 9:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(out / "sheet.jpg"), np.vstack([np.hstack(tiles[i:i + 9]) for i in range(0, len(tiles), 9)]))
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    print("all animated:", all(x["animated"] and x["not_blank"] for x in report))


if __name__ == "__main__":
    main()
