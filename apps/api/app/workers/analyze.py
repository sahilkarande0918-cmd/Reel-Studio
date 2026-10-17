"""analyze job: screen activity → OCR → screen-evidence term correction → highlight candidates →
local-LLM judgment → code-aware 9:16 reframing → persist. Cached per recording on disk."""

import hashlib
import json
import logging
import time
from pathlib import Path

from app.core.db import service_client, transcript_words
from app.core.storage import recording_dir, source_path
from app.services import feedback
from app.services.highlights import audio_features, candidates, llm, outline
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


def _outline(rdir: Path, texts: list[str], sents, ranker) -> list[outline.Unit]:
    """Teaching units, cached until the transcript text changes."""
    key = hashlib.sha1("\n".join(texts).encode()).hexdigest()
    path = rdir / "outline.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("key") == key and cached.get("units") and cached.get("source") == "llm":
            return [outline.Unit(**u) for u in cached["units"]]
    units = outline.outline(texts, sents, ranker, llm.units)
    source = units[0].source if units else "none"
    path.write_text(json.dumps({"key": key, "source": source, "units": [u.to_json() for u in units]}))
    return units


def pick(ctx, rdir: Path, fixed: list[dict], samples: list[dict], seen, org_id: str, timings: dict):
    """Teaching-unit outline → scored 30-60 s windows → LLM-checked, de-duplicated final highlights."""
    ctx.stage("outline", 0.55, "Mapping the class into teaching units (local LLM)")
    t0 = time.perf_counter()
    db_levels = audio_features.rms_db(rdir / "audio16k.wav")
    terms = set(glossary.BUILTIN) | {tok for _, tok in seen}
    sents = candidates.sentences(fixed)
    texts = candidates.sentence_texts(fixed, sents)
    ranker = candidates.pause_ranker(sents)
    whisper.unload()  # free VRAM for the LLM
    units = _outline(rdir, texts, sents, ranker)
    timings["outline_s"] = round(time.perf_counter() - t0, 1)

    ctx.stage("highlights", 0.65, "Scoring complete explanations")
    learned_ideal = feedback.ideal_duration(org_id)
    scored = []
    for a, b in candidates.windows(sents):
        if outline.is_filler(texts[a]):
            continue  # never open on "Thik hai?"; the same window one sentence later is a candidate too
        s0, s1 = sents[a], sents[b]
        span = [w for w in fixed if s0.start <= w["idx"] <= s1.end and w["corrected_text"]]
        # breathe a little into the surrounding pauses so the first and last syllables are never clipped
        lead = min(0.2, s0.pause_before / 2, s0.start_s)
        tail = max(0.0, min(0.3, s1.pause_after / 2, candidates.MAX_S - (s1.end_s - s0.start_s) - lead))
        c = candidates.Candidate(
            s0.start_s - lead, s1.end_s + tail, s0.start, s1.end, " ".join(texts[a : b + 1])
        )
        act = [s for s in samples if c.start_s <= s["t"] <= c.end_s]
        spoken_ids = {w["corrected_text"].strip(".,?!") for w in span} & {tok for _, tok in seen}
        extras = {
            **audio_features.energy_profile(db_levels, c.start_s, c.end_s),
            "words_per_s": audio_features.speech_rate(span, c.start_s, c.end_s),
            "screen_activity": sum(s["change"] for s in act if not s["cut"]) / max(len(act), 1),
            "typing_samples": sum(1 for s in act if s["box"] and 0.0004 < s["change"] < 0.05),
            "tech_terms": sum(1 for w in span if w["corrected_text"].strip(".,?!") in terms),
            "spoken_screen_ids": len(spoken_ids),
            "ideal_s": learned_ideal,
        }
        cx = candidates.context_features(a, b, units, sents, texts, ranker)
        c.features.update({k: round(v, 4) if isinstance(v, float) else v for k, v in extras.items()})
        c.features["context"] = cx
        candidates.score(c, cx, extras)
        scored.append((c, cx, extras, a, b))
    scored.sort(key=lambda x: -x[0].score)

    ctx.stage("llm_judge", 0.72, "Local LLM checks each highlight stands on its own")
    outline_txt = "\n".join(f"{candidates._ts(u.start_s)} {u.kind}: {u.title}" for u in units[:60])
    judged, dropped, kept, rejected = 0, 0, [], []
    for c, cx, extras, a, b in scored:
        if len(kept) >= KEEP or judged >= LLM_BUDGET:
            break
        # a rejected window frees its slot for an alternative; only accepted clips block duplicates
        if any(candidates.same_explanation(c, k) for k in kept) or any(
            candidates.overlap(c, r) > 0.6 for r in rejected
        ):
            continue
        ctx.check_cancel()
        j = llm.judge(
            c.text,
            c.duration_s,
            before=" ".join(texts[max(0, a - 2) : a]),
            after=" ".join(texts[b + 1 : b + 3]),
            outline=outline_txt,
        )
        c.features["llm"] = j
        if not j:  # LLM offline: deterministic score only, said so in score_kind
            kept.append(c)
            continue
        judged += 1
        if not j["complete_start"] and not j["complete_end"] and not cx["complete"]:
            dropped += 1  # LLM and the outline agree it starts and ends mid-thought: not a reel
            rejected.append(c)
            continue
        c.features["deterministic_score"] = c.score
        candidates.score(c, cx, extras, j)
        kept.append(c)
    llm.unload()
    final = sorted(kept, key=lambda c: -c.score)[:KEEP]
    stats = {"windows_scored": len(scored), "llm_judged": judged, "llm_dropped": dropped}
    return final, units, stats


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

    final, units, stats = pick(ctx, rdir, fixed, samples, seen, rec["organization_id"], timings)

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
                "score_kind": "context+llm" if j else "context",
                "title": j.get("title")
                or units[c.features["context"]["core_unit"]].title
                or " ".join(c.text.split()[:7]) + "…",
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
    complete = sum(1 for c in final if c.features["context"]["complete"])
    return {
        "candidates": len(rows),
        "complete_explanations": complete,
        "limitation": None
        if complete or not rows
        else "No complete teaching unit in this class fits a 30–60 s reel; every clip is marked as partial.",
        "outline": [u.to_json() for u in units],
        **stats,
        "screen_term_fixes": len(changed),
        "ocr_frames": len(frames),
        **timings,
    }
