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
from app.services.highlights import audio_features, bulk, candidates, llm, outline, profiles
from app.services.screen_analysis import activity, ocr, reframe
from app.services.transcription import diarize, glossary, whisper
from app.workers.jobs import JobContext, Permanent

log = logging.getLogger(__name__)
OCR_EVERY_S = 6.0
OCR_MAX_FRAMES = 90
LLM_BUDGET = 10
KEEP = 6  # education profile only (original Mode A reels); talk profiles select by quality (bulk.select)


def _cached(path: Path, build, valid=lambda d: True):
    if path.exists():
        data = json.loads(path.read_text())
        if valid(data):
            return data
    data = build()
    path.write_text(json.dumps(data))
    return data


def _outline(rdir: Path, texts: list[str], sents, ranker, profile: str = "education", max_s: float = 60.0,
             labels: list[str] | None = None, on_chunk=None) -> list[outline.Unit]:
    """Teaching units (class) or conversation parts (talk profiles), cached per profile until the transcript text
    changes, so a new clip count or duration reuses the map instead of asking the LLM again."""
    if profile == "education":
        key = hashlib.sha1("\n".join(texts).encode()).hexdigest()  # unchanged key: existing caches stay valid
        path = rdir / "outline.json"
    else:
        key = hashlib.sha1(("\n".join(texts) + f"|{max_s}|{bool(labels)}").encode()).hexdigest()
        path = rdir / f"outline-{profile}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("key") == key and cached.get("units") and cached.get("source") == "llm":
            (rdir / "outline-current.json").write_text(path.read_text())
            return [outline.Unit(**u) for u in cached["units"]]
    p = profiles.get(profile)
    if profile == "education":
        units = outline.outline(texts, sents, ranker, llm.units)
    else:
        units = outline.outline(texts, sents, ranker, lambda lines: llm.units(lines, profile=p, speakers=bool(labels)),
                                kinds=p["kinds"], max_s=max_s, labels=labels, chunk=80, per_chunk_fallback=True,
                                on_chunk=on_chunk)
    source = units[0].source if units else "none"
    body = json.dumps({"key": key, "source": source, "profile": profile, "units": [u.to_json() for u in units]})
    path.write_text(body)
    (rdir / "outline-current.json").write_text(body)
    return units


def _auto_render(ctx, db, rec: dict, inserted: list[dict]) -> list[dict]:
    """One-click recipe (set at upload/import): every clip found is selected and rendered with the recipe's look,
    straight after the automatic analysis. Identical clips reuse their finished export (no duplicates)."""
    recipe = (rec.get("probe") or {}).get("recipe") or {}
    if not ctx.payload.get("auto_render") or not recipe.get("render") or not inserted:
        return []
    from app.api.renders import RenderRequest, enqueue_highlight_render

    req = RenderRequest(**recipe["render"])
    out = []
    ctx.stage("auto_render", 0.95, f"Queueing {len(inserted)} clip renders from the recipe")
    for h in inserted:
        db.table("highlight_candidates").update({"status": "selected"}).eq("id", h["id"]).execute()
        try:
            out.append({"highlight_id": h["id"], **enqueue_highlight_render({**h, "status": "selected"}, req, rec["created_by"])})
        except Exception as e:  # noqa: BLE001 — one bad clip never blocks the others
            log.warning("auto render of %s failed to queue: %s", h["id"], e)
            out.append({"highlight_id": h["id"], "error": f"{type(e).__name__}: {e}"[:300]})
    return out


def _json_cache(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        return {}


def _h(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:20]


def embeddings(rdir: Path, texts: list[str]) -> list[list[float]]:
    """Embeddings for texts, cached per text on disk; TF-IDF when the embedding model is not installed."""
    path = rdir / "embeddings.json"
    cache = _json_cache(path)
    missing = [t for t in dict.fromkeys(texts) if _h(t) not in cache]
    if missing:
        vecs = llm.embed(missing)
        if vecs is None:
            return bulk.tfidf(texts)
        cache.update({_h(t): [round(x, 4) for x in v] for t, v in zip(missing, vecs, strict=True)})
        path.write_text(json.dumps(cache))
    return [cache[_h(t)] for t in texts]


def pick_talk(ctx, rdir: Path, fixed: list[dict], opts: dict, duration_s: float, timings: dict,
              labels: list[str] | None = None, visual=None):
    """Conversation map → every standalone span → 100-point editorial score → LLM-checked, deduplicated,
    topic-diverse selection of as many clips as the recording supports (up to the requested count)."""
    prof_name = opts.get("profile") or "podcast"
    prof = profiles.get(prof_name)
    min_s, max_s, ideal = profiles.duration(opts.get("duration"))
    target = opts.get("count")  # None = auto
    ctx.stage("outline", 0.55, "Mapping the whole conversation: questions, answers, stories, lessons (local LLM)")
    t0 = time.perf_counter()
    db_levels = audio_features.rms_db(rdir / "audio16k.wav")
    sents = candidates.sentences(fixed, talk=True)
    texts = candidates.sentence_texts(fixed, sents)
    ranker = candidates.pause_ranker(sents)
    whisper.unload()
    if labels is None:  # who speaks each sentence (CPU voice clustering), cached with the sentence layout
        key = _h(len(sents), sents[0].start_s if sents else 0, sents[-1].end_s if sents else 0)
        lab = _json_cache(rdir / "speakers-audio.json")
        if lab.get("key") != key:
            lab = {"key": key, "labels": diarize.label(rdir / "audio16k.wav", [(s.start_s, s.end_s) for s in sents])}
            (rdir / "speakers-audio.json").write_text(json.dumps(lab))
        labels = lab["labels"] if len(set(lab["labels"])) > 1 else None
    units = _outline(rdir, texts, sents, ranker, prof_name, max_s=max(60.0, min(max_s, 90.0)), labels=labels,
                     on_chunk=lambda i, n: ctx.stage("outline", 0.55 + 0.09 * i / n,
                                                     f"Mapping the conversation: {i} of {n} sentences read (local LLM)"))
    units = bulk.split_questions(units, texts, sents, labels=labels)
    bulk.merge_topics(units, lambda names: embeddings(rdir, names))
    cmap = bulk.conversation_map(units, texts, labels)
    (rdir / f"conversation-{prof_name}.json").write_text(json.dumps(cmap))
    timings["outline_s"] = round(time.perf_counter() - t0, 1)

    ctx.stage("highlights", 0.65, "Scoring every complete moment (hook, context, payoff)")
    t0 = time.perf_counter()
    brief_terms = outline.content_words(opts.get("brief") or "")
    scored = {}
    for a0, b0 in bulk.spans(units, sents, min_s, max_s, texts):
        a, b = bulk.refine(a0, b0, texts, sents, min_s)
        if (a, b) in scored or bulk.is_talk_filler(texts[a]):
            continue
        s0, s1 = sents[a], sents[b]
        lead = min(0.25, s0.pause_before / 2, s0.start_s)
        tail = max(0.0, min(0.35, s1.pause_after / 2))
        c = candidates.Candidate(s0.start_s - lead, s1.end_s + tail, s0.start, s1.end, " ".join(texts[a : b + 1]))
        span = [w for w in fixed if s0.start <= w["idx"] <= s1.end and w["corrected_text"]]
        extras = {**audio_features.energy_profile(db_levels, c.start_s, c.end_s),
                  "words_per_s": audio_features.speech_rate(span, c.start_s, c.end_s), "brief_terms": brief_terms,
                  "max_s": max_s}
        if visual:
            extras["visual"] = visual(c.start_s, c.end_s)
        f = bulk.features(a, b, units, sents, texts, prof, ideal, extras)
        f["sentences"] = [a, b]
        c.features = f
        c.score = bulk.score(f, prof["weights"])
        scored[(a, b)] = c
    cands = list(scored.values())
    for c, v in zip(cands, embeddings(rdir, [c.text for c in cands]), strict=True):
        c.features["_vec"] = v
    timings["scoring_s"] = round(time.perf_counter() - t0, 1)

    ctx.stage("llm_judge", 0.72, "Local LLM checks each clip stands on its own")
    t0 = time.perf_counter()
    jpath = rdir / f"judgments-{prof_name}.json"
    jcache = _json_cache(jpath)
    outline_txt = "\n".join(f"{candidates._ts(u.start_s)} {u.kind}: {u.title}" for u in units[:80])

    def judge(c) -> bool:
        ctx.check_cancel()
        a, b = c.features["sentences"]
        key = _h(c.text, prof_name)
        j = jcache.get(key)
        if j is None:
            j = llm.judge_talk(c.text, c.duration_s, prof["brief"], before=" ".join(texts[max(0, a - 2) : a]),
                               after=" ".join(texts[b + 1 : b + 3]), outline=outline_txt)
            if j is None:
                return True  # LLM offline: deterministic score only (score_kind says so)
            if j.get("invalid"):
                return False  # never accept a clip the check could not read
            jcache[key] = j
        c.features["llm"] = j
        c.features["deterministic_score"] = c.score
        bulk.blend_llm(c.features, j)
        c.score = bulk.score(c.features, prof["weights"])
        if j["value"] < 0.25 or not (j["complete_start"] or j["complete_end"]):
            return False
        if not c.features["complete"] and not (j["complete_start"] and j["complete_end"]):
            return False
        return c.score >= bulk.MIN_SCORE

    final, report = bulk.select(cands, target, judge, budget=2 * (target or 25) + 8, duration_s=duration_s)
    jpath.write_text(json.dumps(jcache))
    llm.unload()
    timings["llm_judge_s"] = round(time.perf_counter() - t0, 1)
    for c in final:
        a, b = c.features["sentences"]
        c.features["hook_teaser"] = bulk.hook_teaser(a, b, texts, sents)
        c.features["recommendations"] = bulk.recommendations(c.features, fixed, c.start_s, c.end_s)
        c.features["editorial"] = bulk.editorial(c.score)
        c.features["profile"] = prof_name
        q = texts[a] if outline.open_question(texts[a]) else ""
        c.features["title"] = bulk.grounded_title((c.features.get("llm") or {}).get("title", ""), c.text,
                                                  q.rstrip("?")[:80] or units[c.features["core_unit"]].title)
        c.reasons = [bulk.why(c.features, prof), *c.features["limitations"]]
    return final, units, {**report, "conversation": cmap["counts"], "profile": prof_name,
                          "duration_pref": opts.get("duration") or "30-60"}


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
    opts = {k: ctx.payload.get(k) for k in ("profile", "count", "duration", "brief", "range_start_s", "range_end_s")}
    if (opts["profile"] or "education") != "education":
        return _analyze_talk(ctx, db, rec, tr, src, rdir, opts, timings)

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
    inserted = db.table("highlight_candidates").insert(rows).execute().data if rows else []
    renders = _auto_render(ctx, db, rec, inserted)
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
        "auto_renders": len([r for r in renders if "render_id" in r]),
    }


def _genre(rdir: Path, words: list[dict]) -> str:
    """Auto genre: a conversation between two or more voices is clipped as a podcast, one voice as general talk."""
    sents = candidates.sentences(words)[:240]
    if len(sents) < 6:
        return "general"
    labels = diarize.label(rdir / "audio16k.wav", [(s.start_s, s.end_s) for s in sents])
    return "podcast" if len(set(labels)) > 1 else "general"


def _analyze_talk(ctx, db, rec: dict, tr: dict, src: Path, rdir: Path, opts: dict, timings: dict) -> dict:
    """Bulk clipping for podcasts/interviews/talks: no screen OCR (nothing to read), speaker-aware framing, and as
    many distinct standalone clips as the conversation supports. Every stage reads its cache when it has one."""
    from app.services.screen_analysis import speakers

    W, H, dur = rec["width"], rec["height"], rec["duration_s"]
    words = transcript_words(tr["id"])
    lo, hi = opts.get("range_start_s") or 0.0, opts.get("range_end_s") or dur
    if lo > 0 or hi < dur:  # "adjust range": only this stretch is clipped (the transcript stays whole)
        words = [w for w in words if lo <= w["start_s"] and w["end_s"] <= hi]
    if opts.get("profile") == "auto":
        opts["profile"] = _genre(rdir, words)
    ctx.stage("speakers", 0.1, "Finding faces and who is speaking (local, CPU)")
    t0 = time.perf_counter()
    track = _cached(rdir / "faces.json", lambda: speakers.analyze(src, rdir / "audio16k.wav", W, H, dur),
                    valid=lambda d: d.get("version") == speakers.VERSION)
    timings["faces_s"] = round(time.perf_counter() - t0, 1)
    final, units, stats = pick_talk(ctx, rdir, words, opts, dur, timings,
                                    visual=lambda a, b: speakers.visual_score(track, a, b))

    ctx.stage("reframe", 0.88, "Planning speaker-aware 9:16 framing")
    rows = []
    for rank, c in enumerate(final, 1):
        j = c.features.get("llm") or {}
        core = units[c.features["core_unit"]]
        rows.append({
            "organization_id": rec["organization_id"], "project_id": rec["project_id"], "recording_id": rec["id"],
            "transcript_id": tr["id"], "rank": rank, "start_s": round(c.start_s, 2), "end_s": round(c.end_s, 2),
            "score": round(c.score / 100, 4),  # 0..1 like the education score; the 100-point view is in features
            "score_kind": "editorial+llm" if j else "editorial",
            "title": (c.features.get("title") or core.title or " ".join(c.text.split()[:7]) + "…")[:120],
            "summary": j.get("insight", ""),
            "transcript_excerpt": c.text,
            "reasons": c.reasons,
            "features": c.features,
            "llm": j or None,
            "crop_keyframes": speakers.plan(track, c.start_s, c.end_s, W, H),
        })
    db.table("highlight_candidates").delete().eq("recording_id", rec["id"]).eq("status", "proposed").execute()
    inserted = db.table("highlight_candidates").insert(rows).execute().data if rows else []
    renders = _auto_render(ctx, db, rec, inserted)
    db.table("projects").update({"status": "highlights ready"}).eq("id", rec["project_id"]).execute()
    return {"candidates": len(rows), **stats, "outline": [u.to_json() for u in units], **timings,
            "auto_renders": len([r for r in renders if "render_id" in r])}
