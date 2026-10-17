"""Run highlight selection on an analysed recording WITHOUT writing anything (manual tool).

    python tests/dryrun_highlights.py RECORDING_ID [--fresh]

Uses the recording's cached screen activity and OCR plus its stored transcript, then prints the lecture
outline and the highlights the current algorithm would propose, with their score breakdown and reasons.
`--fresh` ignores a cached outline.json.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.core.db import service_client, transcript_words  # noqa: E402
from app.core.storage import recording_dir  # noqa: E402
from app.services.screen_analysis import ocr  # noqa: E402
from app.workers import analyze  # noqa: E402


class Ctx:
    def stage(self, name, p, msg):
        print(f"[{time.strftime('%X')}] {msg}", flush=True)

    def check_cancel(self):
        pass


def main(rec_id: str, fresh: bool) -> None:
    db = service_client()
    rec = db.table("source_recordings").select("*").eq("id", rec_id).single().execute().data
    tr = (
        (
            db.table("transcripts")
            .select("id")
            .eq("recording_id", rec_id)
            .order("created_at", desc=True)
            .limit(1)
        )
        .execute()
        .data[0]
    )
    rdir = recording_dir(rec["organization_id"], rec_id)
    if fresh and (rdir / "outline.json").exists():
        (rdir / "outline.json").unlink()
    samples = json.loads((rdir / "activity.json").read_text())
    seen = ocr.screen_tokens(json.loads((rdir / "ocr.json").read_text()))
    timings: dict = {}
    final, units, stats = analyze.pick(
        Ctx(), rdir, transcript_words(tr["id"]), samples, seen, rec["organization_id"], timings
    )
    print("\nOUTLINE")
    for u in units:
        print(f"  {u.start_s:6.1f}-{u.end_s:6.1f} ({u.duration_s:5.1f}s) {u.kind:13} {u.title}  [{u.source}]")
    print("\nHIGHLIGHTS", stats, timings)
    for r, c in enumerate(final, 1):
        cx, j = c.features["context"], c.features.get("llm") or {}
        print(
            f"\n#{r} {c.start_s:6.1f}-{c.end_s:6.1f} ({c.duration_s:4.1f}s) {round(c.score * 100)}/100 "
            f"complete={cx['complete']} | {j.get('title') or units[cx['core_unit']].title}"
        )
        print("   ", c.features["components"])
        for x in c.reasons:
            print("   -", x)
        print("    opens:", cx["opens_with"])
        print("    ends: ", cx["ends_with"])


if __name__ == "__main__":
    main(sys.argv[1], "--fresh" in sys.argv)
