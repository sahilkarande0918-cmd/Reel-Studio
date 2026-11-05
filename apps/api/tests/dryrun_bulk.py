"""Bulk clipping end to end on a local file WITHOUT the database (manual tool).

    python tests/dryrun_bulk.py VIDEO WORK_DIR [--profile business] [--count 10] [--duration auto] [--language en]
                                [--render N] [--paces natural,engaging,fast] [--sequential-asr]

Transcribes once (cached in WORK_DIR), maps the conversation, selects clips, prints the report, then renders the first
N clips with the fast renderer (one MP4 per pace) and ffprobes them. Changing --count reuses every cache.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.services.clips import speech_cuts  # noqa: E402
from app.services.rendering import caption_auto, caption_presets, fast, timeline  # noqa: E402
from app.services.screen_analysis import speakers  # noqa: E402
from app.services.transcription import cleanup, whisper  # noqa: E402
from app.workers import analyze  # noqa: E402


class Ctx:
    def stage(self, name, p, msg):
        print(f"[{time.strftime('%X')}] {msg}", flush=True)

    def check_cancel(self):
        pass


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height,r_frame_rate",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    return json.loads(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("work")
    ap.add_argument("--profile", default="business")
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--duration", default="auto")
    ap.add_argument("--language", default="en")
    ap.add_argument("--render", type=int, default=0)
    ap.add_argument("--paces", default="engaging")
    ap.add_argument("--preset", default="auto")
    ap.add_argument("--sequential-asr", action="store_true")
    ap.add_argument("--hook-style", default="classic")
    ap.add_argument("--polish", action="store_true", help="auto zoom + colour correction + SFX")
    a = ap.parse_args()
    src, rdir = Path(a.video), Path(a.work)
    rdir.mkdir(parents=True, exist_ok=True)
    timings: dict = {}
    wav = rdir / "audio16k.wav"
    if not wav.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(wav)], check=True)
    words_path = rdir / "words.json"
    if not words_path.exists():
        if a.sequential_asr:
            whisper.BATCH = 0
        t0 = time.perf_counter()
        r = whisper.transcribe(wav, language=a.language)
        timings["asr_s"] = round(time.perf_counter() - t0, 1)
        words = cleanup.remove_loops([{**w, "corrected_text": w["raw_text"], "metadata": {}} for w in r.words])
        words_path.write_text(json.dumps(words))
        whisper.unload()
    words = json.loads(words_path.read_text())
    info = probe(src)
    v = next(s for s in info["streams"] if s.get("width"))
    W, H, dur = v["width"], v["height"], float(info["format"]["duration"])
    t0 = time.perf_counter()
    track = analyze._cached(rdir / "faces.json", lambda: speakers.analyze(src, wav, W, H, dur))
    timings["faces_s"] = round(time.perf_counter() - t0, 1)
    opts = {"profile": a.profile, "count": a.count, "duration": a.duration, "brief": ""}
    final, units, report = analyze.pick_talk(Ctx(), rdir, words, opts, dur, timings,
                                             visual=lambda x, y: speakers.visual_score(track, x, y))
    print("\nCONVERSATION MAP")
    for u in units:
        print(f"  {u.start_s:6.1f}-{u.end_s:6.1f} {u.kind:11} [{u.topic}] {u.title}")
    print("\nREPORT", json.dumps(report, indent=1), "\nTIMINGS", timings)
    for n, c in enumerate(final, 1):
        f = c.features
        print(f"\n#{n} {c.start_s:6.1f}-{c.end_s:6.1f} ({c.duration_s:4.1f}s) {c.score:.0f}/100  {f.get('title')}  [{f['topic']}]")
        print("   ", {k: round(v * 100) for k, v in f["components"].items()})
        print("    hook:", f["hook_quote"])
        print("    end: ", f["ending_quote"])
        for r in c.reasons[1:]:
            print("    !", r)
    (rdir / "selection.json").write_text(json.dumps([{"start_s": c.start_s, "end_s": c.end_s, "title": c.features.get("title"),
                                                    "score": c.score, "features": {k: v for k, v in c.features.items() if k != "_vec"}}
                                                   for c in final], default=str))
    rec = {"id": "dryrun", "filename": src.name, "width": W, "height": H, "duration_s": dur}
    for n, c in enumerate(final[: a.render], 1):
        h = {"id": f"clip{n}", "start_s": c.start_s, "end_s": c.end_s, "title": c.features.get("title", ""),
             "crop_keyframes": speakers.plan(track, c.start_s, c.end_s, W, H), "features": {"profile": a.profile}}
        for pace in a.paces.split(","):
            spans = None if pace == "original" else speech_cuts.plan(words, c.start_s, c.end_s, pace)["spans"]
            doc = timeline.build(h, rec, words, f"clip{n}-{pace}", spans=spans, hook_title=h["title"] or None, emphasis=True,
                                 hook_style=a.hook_style, auto_zoom=a.polish, color_correct=a.polish, sfx=a.polish)
            preset = a.preset if a.preset != "auto" else caption_auto.auto_preset(a.profile, None if pace == "original" else pace)
            doc["captionStyle"] = caption_presets.style_for(preset, doc["captionStyle"], doc["height"], doc["brand"]["colors"])
            proj = rdir / "renders" / f"clip{n}-{pace}-{preset}-{a.hook_style}{'-polish' if a.polish else ''}"
            t0 = time.perf_counter()
            out = fast.render(doc, src, proj)
            took = time.perf_counter() - t0
            p = probe(out)
            print(f"RENDER clip{n} {pace:9} {preset:16} {doc['duration']:6.2f}s timeline → {float(p['format']['duration']):6.2f}s file, "
                  f"{[(s['codec_name'], s.get('width'), s.get('height')) for s in p['streams']]}, rendered in {took:.1f}s → {out}")


if __name__ == "__main__":
    main()
