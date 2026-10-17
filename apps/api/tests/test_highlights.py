from app.services.highlights.candidates import Candidate, select, sentences, windows


def speech(spec: list[tuple[str, float]], t0: float = 0.0) -> list[dict]:
    """spec: (sentence text, pause after). Words 0.4 s each."""
    out, t = [], t0
    for text, pause in spec:
        toks = text.split()
        for j, tok in enumerate(toks):
            out.append(
                {"idx": len(out), "raw_text": tok, "corrected_text": tok, "start_s": t, "end_s": t + 0.35}
            )
            t += 0.4
        t += pause
    return out


def test_sentences_split_on_punctuation_and_long_pauses():
    ws = speech(
        [("ab hum hook banayenge.", 0.2), ("phir state banayenge", 1.2), ("aur effect likhenge.", 0.3)]
    )
    ss = sentences(ws)
    assert [(s.start, s.end) for s in ss] == [(0, 3), (4, 6), (7, 9)]
    assert ss[1].pause_after >= 1.2


def test_windows_respect_30_to_60_seconds_and_sentence_boundaries():
    # 20 sentences of ~4.8 s (12 words) separated by 0.6 s pauses
    ws = speech([("w " * 11 + "end.", 0.6)] * 20)
    ss = sentences(ws)
    for a, b in windows(ss):
        d = ss[b].end_s - ss[a].start_s
        assert 30 <= d <= 60
        # every window begins at a sentence start and ends at a sentence end
        assert ws[ss[a].start]["start_s"] == ss[a].start_s and ws[ss[b].end]["corrected_text"].endswith(".")


def test_nms_keeps_best_non_overlapping():
    a = Candidate(0, 45, 0, 0, "a", score=0.9)
    b = Candidate(5, 50, 0, 0, "b", score=0.8)  # mostly overlaps a
    c = Candidate(60, 100, 0, 0, "c", score=0.5)
    assert [x.text for x in select([a, b, c])] == ["a", "c"]


# --- context-aware selection (outline + completeness) ---
from app.services.highlights import outline as ol  # noqa: E402
from app.services.highlights.candidates import (  # noqa: E402
    context_features,
    pause_ranker,
    same_explanation,
    sentence_texts,
)


def lecture():
    """Two topics: recursion (intro, concept, example, conclusion) then a digression about the exam."""
    ws = speech(
        [
            ("Aaj hum recursion samajhte hain.", 1.5),
            ("Recursion matlab function apne aap ko call karta hai " + "w " * 20 + "base case.", 0.4),
            ("Thik hai?", 0.4),
            ("Example dekho factorial ka " + "x " * 30 + "return n.", 0.4),
            ("Isliye recursion ko base case chahiye.", 1.6),
            ("Ab exam ki baat karte hain " + "y " * 25 + "date.", 0.5),
            ("Exam kab hai?", 0.3),
            ("Monday ko hai.", 2.0),
        ]
    )
    ss = sentences(ws)
    return ws, ss, sentence_texts(ws, ss)


def units_for(ss):
    raw = [
        {"first": 0, "last": 0, "kind": "introduction", "title": "Recursion", "topic": "recursion"},
        {"first": 1, "last": 2, "kind": "concept", "title": "What recursion is", "topic": "recursion"},
        # the LLM skipped sentence 3 and overlapped 4: repair must still give a gap-free cover
        {"first": 4, "last": 4, "kind": "conclusion", "title": "Base case", "topic": "recursion"},
        {"first": 4, "last": 7, "kind": "digression", "title": "Exam", "topic": "exam"},
    ]
    return ol.repair(raw, 0, len(ss) - 1, ss)


def test_repair_gives_contiguous_cover():
    _, ss, _ = lecture()
    us = units_for(ss)
    assert [(u.first, u.last) for u in us] == [(0, 0), (1, 2), (3, 4), (5, 7)]
    assert us[2].kind == "conclusion" and us[3].first == 5


def test_whole_explanation_is_complete_and_partial_is_flagged():
    _, ss, texts = lecture()
    us, rank = units_for(ss), pause_ranker(ss)
    whole = context_features(0, 4, us, ss, texts, rank)  # intro → conclusion of recursion
    assert whole["complete"] and whole["covers_topic"] and whole["limitation"] is None
    assert whole["open_cue"] and whole["close_cue"]
    part = context_features(4, 7, us, ss, texts, rank)  # starts in the middle of a unit
    assert part["starts_at_unit"] is False and part["limitation"].startswith("Partial explanation")
    assert whole["parts"]["context"] > part["parts"]["context"]


def test_clip_ending_on_a_question_before_its_answer_is_penalised():
    _, ss, texts = lecture()
    us, rank = units_for(ss), pause_ranker(ss)
    cliff = context_features(5, 6, us, ss, texts, rank)  # stops at "Exam kab hai?" before "Monday ko hai."
    answered = context_features(5, 7, us, ss, texts, rank)
    assert cliff["cut_before_answer"] and not answered["cut_before_answer"]
    assert answered["parts"]["ending"] > cliff["parts"]["ending"]
    # digressions teach nothing on their own
    assert answered["parts"]["teach"] == 0


def test_filler_and_back_references():
    assert ol.is_filler("Thik hai na bhai?") and not ol.is_filler("0 aaya hai.")
    assert ol.leans_back("Phir isko integrate karo.") and not ol.leans_back(
        "Aaj hum recursion samajhte hain."
    )
    assert ol.open_question("Exam kab hai?") and not ol.open_question("Thik hai?")


def test_long_step_is_split_at_its_strongest_boundary():
    ws = speech(
        [
            ("a " * 40 + "end.", 0.3),
            ("Isliye yah clear ho gaya.", 2.5),
            ("Ab dekhte hain " + "b " * 120 + "end.", 0.3),
        ]
    )
    ss = sentences(ws)
    texts = sentence_texts(ws, ss)
    long = [ol.Unit(0, 2, ss[0].start_s, ss[2].end_s, "concept", "Long", "llm", "t")]
    parts = ol.split_long(long, texts, ss, pause_ranker(ss))
    assert [(u.first, u.last) for u in parts] == [(0, 1), (2, 2)]
    assert parts[0].title == "Long (part 1 of 2)" and parts[0].source == "llm+split"


def test_lexical_fallback_finds_the_topic_change():
    ws = speech(
        [("recursion function call stack base " * 3, 0.3)] * 4 + [("exam monday hall ticket " * 4, 0.3)] * 4
    )
    ws[0]["raw_text"] = ws[0]["corrected_text"] = "recursion."
    ss = sentences(ws, pause_split_s=0.25)
    us = ol.lexical(sentence_texts(ws, ss), ss, pause_ranker(ss), min_s=5)
    assert len(us) >= 2 and all(u.source == "lexical" for u in us)
    assert any("Exam" in u.title or "Monday" in u.title for u in us)


def test_same_teaching_unit_is_a_duplicate():
    a = Candidate(0, 40, 0, 0, "recursion base case factorial", features={"context": {"core_unit": 2}})
    b = Candidate(100, 140, 0, 0, "exam monday", features={"context": {"core_unit": 2}})
    c = Candidate(200, 240, 0, 0, "exam monday hall", features={"context": {"core_unit": 5}})
    assert same_explanation(a, b) and not same_explanation(a, c)
