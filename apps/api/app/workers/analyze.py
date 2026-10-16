"""analyze job: screen activity → OCR → screen-evidence term correction → highlight candidates →
local-LLM judgment → code-aware 9:16 reframing → persist. Cached per recording on disk."""

import json
import logging
import time
from pathlib import Path

from app.core.db import service_client, transcript_words
from app.core.storage import recording_dir, source_path
from app.services import feedback
from app.services.highlights import audio_features, candidates, llm
from app.services.screen_analysis import activity, ocr, reframe
from app.services.transcription import glossary, whisper
from app.workers.jobs import JobContext, Permanent

log = logging.getLogger(__name__)
OCR_EVERY_S = 6.0
OCR_MAX_FRAMES = 90
LLM_BUDGET = 10
KEEP = 6


def _cached(path: Path, build):
    if path.exists():
        return json.loads(path.read_text())
    data = build()
    path.write_text(json.dumps(data))
    return data


def run_analyze(ctx: JobContext) -> dict:
    db = service_client()
    rec = (
        db.table("source_recordings")
        .select("*")
        .eq("id", ctx.payload["recording_id"])
        .limit(1)
        .execute()
        .data
        or [None]
    )[0]
    if not rec:
        raise Permanent("recording not found")
    tr = (
        db.table("transcripts")
        .select("id")
        .eq("recording_id", rec["id"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or [None]
    )[0]
    if not tr:
        raise Permanent("no transcript yet")
    src, rdir = source_path(rec), recording_dir(rec["organization_id"], rec["id"])
    W, H, dur = rec["width"], rec["height"], rec["duration_s"]
    timings: dict[str, float] = {}

    ctx.stage("screen_activity", 0.05, "Measuring on-screen activity")
    t0 = time.perf_counter()
    samples = _cached(rdir / "activity.json", lambda: activity.to_json(activity.analyze(src, W, H)))
    timings["screen_activity_s"] = round(time.perf_counter() - t0, 1)

    ctx.stage("ocr", 0.2, "Reading code on screen (local OCR)")
    t0 = time.perf_counter()
    cuts = [s["t"] + 1.0 for s in samples if s["cut"]]
    times = sorted(
        {round(x * OCR_EVERY_S, 1) for x in range(int(dur // OCR_EVERY_S) + 1)} | {round(c, 1) for c in cuts}
    )
    times = times[:: max(1, len(times) // OCR_MAX_FRAMES + (len(times) % OCR_MAX_FRAMES > 0))][
        :OCR_MAX_FRAMES
    ]
    frames = _cached(rdir / "ocr.json", lambda: ocr.ocr_video(src, times))
    seen = ocr.screen_tokens(frames)
    timings["ocr_s"] = round(time.perf_counter() - t0, 1)

    ctx.stage("screen_terms", 0.45, "Correcting terms that are visible on screen")
    words = transcript_words(tr["id"])
    fixed = glossary.correct_with_screen(words, seen)
    changed = [
        w
        for w, o in zip(fixed, words, strict=True)
        if w["corrected_text"] != o["corrected_text"] or w["end_s"] != o["end_s"]
    ]
    for w in changed:
        db.table("transcript_words").update(
            {"corrected_text": w["corrected_text"], "end_s": w["end_s"], "metadata": w["metadata"]}
        ).eq("transcript_id", tr["id"]).eq("idx", w["idx"]).execute()

    ctx.stage("highlights", 0.55, "Finding complete-thought highlights")
    db_levels = audio_features.rms_db(rdir / "audio16k.wav")
    terms = set(glossary.BUILTIN) | {tok for _, tok in seen}
    sents = candidates.sentences(fixed)
    ranker = candidates.pause_ranker(sents)
    learned_ideal = feedback.ideal_duration(rec["organization_id"])
    cands = []
    for a, b in candidates.windows(sents):
        s0, s1 = sents[a], sents[b]
        span = [w for w in fixed if s0.start <= w["idx"] <= s1.end and w["corrected_text"]]
        text = " ".join(w["corrected_text"] for w in span)
        c = candidates.Candidate(s0.start_s, s1.end_s, s0.start, s1.end, text)
        act = [s for s in samples if c.start_s <= s["t"] <= c.end_s]
        spoken_ids = {w["corrected_text"].strip(".,?!") for w in span} & {tok for _, tok in seen}
        extras = {
            **audio_features.energy_profile(db_levels, c.start_s, c.end_s),
            "words_per_s": audio_features.speech_rate(span, c.start_s, c.end_s),
            "screen_activity": sum(s["change"] for s in act if not s["cut"]) / max(len(act), 1),
            "typing_samples": sum(1 for s in act if s["box"] and 0.0004 < s["change"] < 0.05),
            "tech_terms": sum(1 for w in span if w["corrected_text"].strip(".,?!") in terms),
            "spoken_screen_ids": len(spoken_ids),
            "pause_ranks": ranker,
            "ideal_s": learned_ideal,
        }
        candidates.score_window(c, s0, s1, extras, candidates.DEFAULT_WEIGHTS)
        c.features.update(
            {k: round(v, 4) if isinstance(v, float) else v for k, v in extras.items() if k != "pause_ranks"}
        )
        cands.append(c)
    # Complete thoughts: both boundaries must be pauses that are long for this speaker (top 40 %).
    strict = [
        c for c in cands if c.features["pause_rank_before"] >= 0.6 and c.features["pause_rank_after"] >= 0.6
    ]
    pool = strict if len(candidates.select(strict, k=3)) >= 3 else cands
    for c in pool:
        c.features["boundary_rule"] = "strict" if pool is strict else "relaxed (too few strong pauses)"
    ordered = sorted(pool, key=lambda c: -c.score)

    ctx.stage("llm_judge", 0.7, "Local LLM checks each highlight stands on its own")
    whisper.unload()  # free VRAM for the LLM
    judged, dropped, kept, rejected = 0, 0, [], []
    for c in ordered:
        if len(kept) >= KEEP or judged >= LLM_BUDGET:
            break
        # a rejected window frees its slot for an overlapping alternative; only accepted clips block
        if any(candidates.overlap(c, k) > 0.35 for k in kept) or any(
            candidates.overlap(c, r) > 0.6 for r in rejected
        ):
            continue
        ctx.check_cancel()
        j = llm.judge(c.text, c.duration_s)
        c.features["llm"] = j
        if not j:  # LLM offline: heuristic only, said so in score_kind
            kept.append(c)
            continue
        judged += 1
        strong = min(c.features["pause_rank_before"], c.features["pause_rank_after"]) >= 0.8
        if not j["complete_start"] and not j["complete_end"] and not strong:
            dropped += 1  # LLM and pauses agree it starts and ends mid-thought: not a reel
            rejected.append(c)
            continue
        q = (j["standalone"] + j["educational"] + j["complete_start"] + j["complete_end"]) / 4
        c.features["heuristic_score"] = c.score
        c.score = round(0.6 * c.score + 0.4 * q, 4)
        for ok, edge, hint in (
            (j["complete_start"], "start", "begin earlier"),
            (j["complete_end"], "end", "continue after"),
        ):
            if not ok:
                c.score = round(c.score - 0.05, 4)
                c.reasons.append(f"Check the {edge}: the local LLM thinks the thought may {hint} this point")
        c.reasons.append(f"Local LLM: {j['reason']}")
        kept.append(c)
    llm.unload()
    final = sorted(kept, key=lambda c: -c.score)[:KEEP]

    ctx.stage("reframe", 0.88, "Planning code-aware 9:16 framing")
    rows = []
    for rank, c in enumerate(final, 1):
        j = c.features.get("llm") or {}
        rows.append(
            {
                "organization_id": rec["organization_id"],
                "project_id": rec["project_id"],
                "recording_id": rec["id"],
                "transcript_id": tr["id"],
                "rank": rank,
                "start_s": round(c.start_s, 2),
                "end_s": round(c.end_s, 2),
                "score": c.score,
                "score_kind": "heuristic+llm" if j else "heuristic",
                "title": j.get("title") or " ".join(c.text.split()[:7]) + "…",
                "summary": j.get("summary", ""),
                "transcript_excerpt": c.text,
                "reasons": c.reasons,
                "features": c.features,
                "llm": j or None,
                "crop_keyframes": reframe.plan(samples, frames, c.start_s, c.end_s, W, H),
            }
        )
    db.table("highlight_candidates").delete().eq("recording_id", rec["id"]).eq("status", "proposed").execute()
    if rows:
        db.table("highlight_candidates").insert(rows).execute()
    db.table("projects").update({"status": "highlights ready"}).eq("id", rec["project_id"]).execute()
    return {
        "candidates": len(rows),
        "windows_scored": len(cands),
        "llm_judged": judged,
        "llm_dropped": dropped,
        "screen_term_fixes": len(changed),
        "ocr_frames": len(frames),
        **timings,
    }
