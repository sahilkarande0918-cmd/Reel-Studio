"""Bulk clipping: conversation map, hook/payoff features, quality-first diverse selection, speech cuts, speaker
smoothing, caption emphasis, campaign checks and the fast renderer's ASS captions."""

import numpy as np

from app.services.clips import campaign_brief, speech_cuts
from app.services.highlights import bulk, profiles
from app.services.highlights.candidates import Candidate, Sentence
from app.services.highlights.outline import Unit
from app.services.rendering import caption_auto
from app.services.screen_analysis import speakers


def _talk():
    """question → answer (lesson) ×3 topics, a sponsor read, then the first idea repeated in other words."""
    texts, kinds, topics = [], [], []
    blocks = [
        ("question", "pricing", "How do you decide what price to charge?"),
        ("answer", "pricing", "Most founders price on cost and that is the biggest mistake."),
        ("lesson", "pricing", "So price on the value you create, that's why sales went up 40 percent."),
        ("sponsor", "sponsor", "This episode is brought to you by Cloud Notes, use code SHOW."),
        ("question", "hiring", "How do you hire your first employees?"),
        ("answer", "hiring", "I hire for slope, not intercept, because the job changes every three months."),
        ("lesson", "hiring", "The lesson is that the person who learns fastest wins."),
        ("question", "cash", "What is the most common financial mistake?"),
        ("answer", "cash", "Founders confuse revenue with cash and run out of money."),
        ("lesson", "cash", "That's why you check your runway every Monday, cash is survival."),
    ]
    sents, t = [], 0.0
    for n, (k, top, txt) in enumerate(blocks):
        d = 12.0
        sents.append(Sentence(n * 10, n * 10 + 9, t, t + d, 0.6, 0.6))
        texts.append(txt)
        kinds.append(k)
        topics.append(top)
        t += d + 0.6
    units = [Unit(i, i, s.start_s, s.end_s, kinds[i], texts[i][:30], "llm", topics[i]) for i, s in enumerate(sents)]
    return texts, sents, units


def _cands(texts, sents, units, prof="business", min_s=20, max_s=45):
    p = profiles.get(prof)
    out = []
    for a, b in bulk.spans(units, sents, min_s, max_s):
        a, b = bulk.refine(a, b, texts, sents, min_s)
        c = Candidate(sents[a].start_s, sents[b].end_s, a, b, " ".join(texts[a : b + 1]))
        c.features = bulk.features(a, b, units, sents, texts, p, 38, {})
        c.score = bulk.score(c.features, p["weights"])
        out.append(c)
    return out


def test_conversation_map_links_questions_to_answers():
    texts, sents, units = _talk()
    m = bulk.conversation_map(units, texts)
    assert [q["question"] for q in m["qa"]] == [0, 4, 7]
    assert m["qa"][0]["answers"] == [1, 2]
    assert m["parts"][1]["answers_question"] == 0
    assert m["counts"]["sponsor"] == 1 and len(m["topics"]) == 4


def test_answer_without_its_question_loses_context_and_ending_before_lesson_loses_payoff():
    texts, sents, units = _talk()
    p = profiles.get("business")
    whole = bulk.features(0, 2, units, sents, texts, p, 38, {})
    orphan = bulk.features(1, 2, units, sents, texts, p, 38, {})
    cut = bulk.features(0, 1, units, sents, texts, p, 38, {})
    assert whole["complete"] and whole["components"]["context"] > orphan["components"]["context"]
    assert any("without showing it" in x for x in orphan["limitations"])
    assert whole["components"]["payoff"] > cut["components"]["payoff"] or cut["ends_whole"]


def test_selection_is_distinct_skips_sponsor_and_reports_shortfall_honestly():
    texts, sents, units = _talk()
    cands = _cands(texts, sents, units)
    kept, report = bulk.select(cands, target=15, duration_s=sents[-1].end_s)
    assert 1 <= len(kept) <= 3  # three Q→A→lesson topics: never padded to 15
    assert len({k.features["topic"] for k in kept}) == len(kept)
    assert all("sponsor" not in k.features["kinds"] for k in kept)
    assert "Only" in report["shortfall"] and report["requested"] == 15
    for a in kept:
        for b in kept:
            assert a is b or bulk.overlap(a, b) <= bulk.DUP_TIME


def test_questions_rebuild_parts_and_rhetorical_questions_stay_inside_answers():
    texts = ["Why did your startup fail?", "We built what nobody wanted.", "What happened?", "We never asked anyone.",
             "Quick word from our sponsor.", "This show is brought to you by Notes, use code SHOW.", "Okay, back to it.",
             "How do you price?", "On value, not on cost.", "That is why sales went up."]
    labels = ["S1", "S2", "S2", "S2", "S1", "S1", "S1", "S1", "S2", "S2"]
    sents = [Sentence(i * 10, i * 10 + 9, i * 6.0, i * 6.0 + 5.5, 0.5, 0.5) for i in range(len(texts))]
    one = [Unit(0, 9, 0, sents[-1].end_s, "lesson", "Startup lessons", "llm", "startups")]  # LLM fused everything
    parts = bulk.split_questions(one, texts, sents, labels=labels)
    kinds = [(p.first, p.kind) for p in parts]
    assert (0, "question") in kinds and (7, "question") in kinds
    assert not any(p.first == 2 and p.kind == "question" for p in parts)  # guest's rhetorical "What happened?"
    assert any(p.kind == "sponsor" and p.first <= 5 <= p.last for p in parts)
    assert not any(p.kind == "sponsor" and p.first <= 7 <= p.last for p in parts)


def test_near_duplicate_by_meaning_is_rejected():
    a = Candidate(0, 30, 0, 9, "talk to twenty customers before you write code")
    b = Candidate(300, 330, 100, 109, "before building, go and talk to about twenty customers first")
    a.features, b.features = {"_vec": [1.0, 0.1, 0.0]}, {"_vec": [0.98, 0.12, 0.01]}
    assert bulk.duplicate(a, b) == "repeats the same idea"
    b.features["_vec"] = [0.0, 0.0, 1.0]
    assert bulk.duplicate(a, b) is None


def test_llm_veto_frees_the_slot_for_the_next_clip():
    texts, sents, units = _talk()
    cands = _cands(texts, sents, units)
    first = max(cands, key=lambda c: c.score)
    kept, report = bulk.select(cands, target=1, judge=lambda c: c is not first, duration_s=200)
    assert len(kept) == 1 and kept[0] is not first and report["llm_rejected"] >= 1


def test_hooks_and_weak_openings():
    assert bulk.hook_strength("Why did your first startup fail?") > bulk.hook_strength("Yeah, exactly, as I said.")
    assert bulk.leans_back("As I was saying, the plan worked")
    assert bulk.unresolved_referent("He told me the plan worked")
    assert bulk.is_talk_filler("Yeah.") and not bulk.is_talk_filler("Yeah, we lost 2 crore.")


def test_education_profile_keeps_the_original_scoring():
    assert profiles.get("education")["weights"] is None and profiles.get(None) is profiles.get("education")
    for name, p in profiles.PROFILES.items():
        if p["weights"]:
            assert sum(p["weights"].values()) == 100, name


def _words(spec):
    out, t = [], 0.0
    for i, (text, dur, gap) in enumerate(spec):
        out.append({"idx": i, "start_s": t, "end_s": t + dur, "corrected_text": text, "raw_text": text})
        t += dur + gap
    return out


def test_pace_presets_shorten_pauses_progressively_and_keep_meaningful_words():
    ws = _words([("So", .2, .1), ("um", .3, .1), ("the", .2, 1.4), ("the", .2, .05), ("price", .3, .9), ("matters.", .4, 1.2),
                 ("Always", .3, .2), ("check", .3, 0)])
    end = ws[-1]["end_s"]
    plans = {p: speech_cuts.plan(ws, 0, end, p) for p in ("natural", "engaging", "fast")}
    kept = {p: sum(b - a for a, b in v["spans"]) for p, v in plans.items()}
    assert kept["natural"] > kept["engaging"] > kept["fast"] > 0
    assert any(r["text"] == "um" for r in plans["engaging"]["removed"])
    assert not any(r["text"] == "um" for r in plans["natural"]["removed"])
    for p, v in plans.items():  # every content word still plays
        kept_words = {w["corrected_text"] for w in speech_cuts.remap(ws, v["spans"])}
        assert {"price", "matters.", "Always", "check"} <= kept_words, p
        assert len(v["spans"]) >= 2 or p == "natural"


def test_speaker_smoothing_ignores_syllable_flicker():
    a = np.array([0] * 30 + [1, 0, 1, 0] + [0] * 20 + [1] * 30)
    out = speakers.smooth(a, 6, 12)
    switches = int(np.sum(out[1:] != out[:-1]))
    assert switches == 1 and out[0] == 0 and out[-1] == 1


def test_speaker_plan_cuts_between_two_seats_and_falls_back_without_faces():
    W, H = 1920, 1080
    track = {"step": 1 / 6, "slots": [{"cx": 480, "cy": 400, "w": 160, "h": 200, "share": .9},
                                     {"cx": 1440, "cy": 400, "w": 160, "h": 200, "share": .9}],
             "present": ["11"] * 120, "active": "0" * 60 + "1" * 60}
    ks = speakers.plan(track, 0, 20, W, H)
    assert [k["region"] for k in ks] == ["speaker-0", "speaker-1"]
    assert ks[1]["transition_mode"] == "cut" and ks[0]["crop_x"] < ks[1]["crop_x"]
    assert all(k["crop_width"] == 608 and k["crop_x"] + 608 <= W for k in ks)
    assert speakers.plan({"slots": []}, 0, 10, W, H) == []
    rapid = {**track, "active": ("0" * 8 + "1" * 8) * 8}
    assert any(k["layout"] == "split" and k.get("second") for k in speakers.plan(rapid, 0, 20, W, H))


def test_caption_emphasis_is_content_based_and_rate_limited():
    words = [{"text": t, "start": i * 0.3, "end": i * 0.3 + 0.25}
             for i, t in enumerate("we grew 40 percent and then 50 percent in a year but".split())]
    out = caption_auto.emphasise(words)
    hits = [w["text"] for w in out if w["emphasis"]]
    assert hits and hits[0] == "40" and len(hits) <= 2
    assert caption_auto.auto_preset("business", "natural") == "modern-grotesk"
    assert caption_auto.auto_preset("business", "fast", "bold-impact") == "bold-impact"


def test_campaign_brief_checks_length_tags_and_mentions():
    b = campaign_brief.Brief(name="Founders", source_rights_confirmed=True, min_s=20, max_s=60,
                             hashtags=["founders"], mentions=["thepod"], required_text="Full episode on YouTube")
    cap = campaign_brief.caption(b, "Price on value", "")
    ok = campaign_brief.check(b, 40, "price value", cap, True)
    assert ok["ok"] and "#founders" in cap and "@thepod" in cap
    bad = campaign_brief.check(b, 75, "x", "Price on value", False)
    assert not bad["ok"] and any("Too long" in i for i in bad["issues"]) and bad["warnings"]
    dup = campaign_brief.check(b, 40, "x", cap, True, [{"campaign": "Founders", "start_s": 0, "end_s": 40}], 5, 45)
    assert any("duplicate" in w for w in dup["warnings"])


def test_fast_renderer_captions_use_the_same_pages_as_the_preview():
    from app.services.rendering import caption_presets, compose, fast

    words = [{"text": t, "start": i * 0.4, "end": i * 0.4 + 0.35, "isCode": False, "emphasis": t == "40"}
             for i, t in enumerate("price on value and sales grew 40 percent".split())]
    style = caption_presets.style_for("creator-yellow", {"fontSize": 60, "maxCharsPerLine": 26, "maxLines": 2,
                                                          "safeTop": 1350, "safeBottom": 1650}, 1920)
    doc = {"captionStyle": style, "brand": {"fonts": {"body": "Archivo"}, "colors": {"accent": "#FFD43B",
           "background": "#000000"}},
           "tracks": [{"items": [{"type": "caption", "start": 0, "duration": 4, "words": words}]}]}
    pages = compose.paginate(words, 26, 2, 4)
    text = fast.ass(doc)
    events = [ln for ln in text.splitlines() if ln.startswith("Dialogue:")]
    assert len(events) == sum(len([w for ln in p["lines"] for w in ln]) for p in pages)
    assert "PRICE" in text and "\\fscx115" in text  # uppercase look, scale highlight on the spoken word
