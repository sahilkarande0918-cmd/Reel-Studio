"""Highlight candidates: 30-60 s windows that start and end on complete thoughts, ranked by context.

Boundaries are always sentence edges, so a clip never cuts through a word or sentence. Each window is
compared with the lecture outline (teaching units, `outline.py`) and scored from named, deterministic
signals (a ranking aid out of 100, never a probability):

- context: starts where a teaching unit starts, ends where one ends, and is made of whole units
- educational: what kinds of units it covers (concept/example/demonstration > recap > digression),
  technical terms and on-screen identifiers that are spoken, code/screen activity
- opening: first sentence is a strong start (cue, question, long pause) and does not lean on earlier talk
- ending: last sentence concludes (cue, unit end, long pause) and does not stop before an answer
- engagement: voice energy, comfortable pace, length close to what this audience watches

The local LLM's judgment, when it runs, is blended into context and educational and shown separately.
"""

import re
from dataclasses import dataclass, field

from app.services.highlights import outline as ol

MIN_S, MAX_S, IDEAL_S = 30.0, 60.0, 45.0
SENT_END = re.compile(r"[.?!।]$")
WEIGHTS = {"context": 0.35, "educational": 0.25, "opening": 0.15, "ending": 0.15, "engagement": 0.10}


@dataclass
class Sentence:
    start: int  # word index
    end: int  # inclusive
    start_s: float
    end_s: float
    pause_before: float
    pause_after: float


@dataclass
class Candidate:
    start_s: float
    end_s: float
    first_word: int
    last_word: int
    text: str
    features: dict = field(default_factory=dict)
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


def sentences(words: list[dict], pause_split_s: float = 0.9) -> list[Sentence]:
    """Split on terminal punctuation, or on a long pause even without punctuation."""
    ws = [w for w in words if w.get("corrected_text", w["raw_text"])]
    out, s = [], 0
    for i, w in enumerate(ws):
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        gap = (nxt["start_s"] - w["end_s"]) if nxt else 9.0
        text = (w.get("corrected_text") or w["raw_text"]).strip()
        if SENT_END.search(text) or gap >= pause_split_s or nxt is None:
            before = ws[s]["start_s"] - ws[s - 1]["end_s"] if s > 0 else 9.0
            out.append(Sentence(ws[s]["idx"], w["idx"], ws[s]["start_s"], w["end_s"], before, gap))
            s = i + 1
    return out


def sentence_texts(words: list[dict], sents: list[Sentence]) -> list[str]:
    by_idx = {w["idx"]: (w.get("corrected_text") or w["raw_text"]) for w in words}
    return [" ".join(by_idx[i] for i in range(s.start, s.end + 1) if by_idx.get(i)) for s in sents]


def windows(sents: list[Sentence], min_s: float = MIN_S, max_s: float = MAX_S) -> list[tuple[int, int]]:
    """(first_sentence, last_sentence) pairs spanning min_s..max_s."""
    out = []
    for a in range(len(sents)):
        for b in range(a, len(sents)):
            d = sents[b].end_s - sents[a].start_s
            if d > max_s:
                break
            if d >= min_s:
                out.append((a, b))
    return out


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _quote(t: str, n: int = 110) -> str:
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def _ts(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def context_features(
    a: int, b: int, units: list[ol.Unit], sents: list[Sentence], texts: list[str], ranker
) -> dict:
    """How completely sentences a..b cover the lecture's teaching units, and how they open and end."""
    s0, s1 = sents[a], sents[b]
    ua, ub = ol.unit_of(units, a), ol.unit_of(units, b)
    first_u, last_u = units[ua], units[ub]
    # a unit "starts" at its first sentence that carries meaning (skip "Thik hai?" lead-ins), likewise its end
    start_ok = a == first_u.first or all(ol.is_filler(texts[i]) for i in range(first_u.first, a))
    end_ok = b == last_u.last or all(ol.is_filler(texts[i]) for i in range(b + 1, last_u.last + 1))
    rb, ra = ranker(s0.pause_before), ranker(s1.pause_after)
    dur = max(s1.end_s - s0.start_s, 1e-6)
    inside = []
    for u in units[ua : ub + 1]:
        ov = max(0.0, min(u.end_s, s1.end_s) - max(u.start_s, s0.start_s))
        whole = (u is not first_u or start_ok) and (u is not last_u or end_ok)
        inside.append((u, ov, whole))
    whole_share = min(sum(ov for _, ov, w in inside if w) / dur, 1.0)
    start_part = 1.0 if start_ok else 0.5 * rb  # a long pause inside a unit is a weaker sub-boundary
    end_part = 1.0 if end_ok else 0.5 * ra

    first, last = texts[a], texts[b]
    weak_open = ol.leans_back(first)
    cue_open = (
        ol.has_cue(first, ol.OPEN_CUES)
        or ol.open_question(first)
        or (first_u.kind == "introduction" and a == first_u.first)
    )
    # starting on a recap/conclusion shows an answer without its setup
    late_open = first_u.kind in ("recap", "conclusion") and a == first_u.first
    opening = (0.4 * start_part + 0.3 * rb + 0.3 * cue_open) * (
        0.4 if weak_open else 0.7 if late_open else 1.0
    )
    nxt = texts[b + 1] if b + 1 < len(texts) else ""
    cliff = ol.open_question(last) and bool(nxt) and not ol.is_filler(nxt)
    cue_end = not ol.open_question(last) and (
        ol.has_cue(last, ol.CLOSE_CUES) or last_u.kind in ("conclusion", "recap")
    )
    # ending on a step that poses a question or introduces something leaves the point open
    opens_up = last_u.kind in ("question", "introduction") and b == last_u.last
    ending = (0.4 * end_part + 0.3 * ra + 0.3 * cue_end) * (0.3 if cliff else 0.6 if opens_up else 1.0)

    teach = sum(ol.TEACH_VALUE[u.kind] * ov for u, ov, _ in inside) / dur
    core = max(inside, key=lambda x: x[1])[0]
    complete = start_ok and end_ok
    ta, tb = ol.topic_span(units, units.index(core))
    topic_whole = (ua < ta or (ua == ta and start_ok)) and (ub > tb or (ub == tb and end_ok))
    topic_s = units[tb].end_s - units[ta].start_s
    # whole steps first; covering the instructor's whole topic (not just steps of it) is the best case
    context = 0.3 * start_part + 0.3 * end_part + 0.25 * whole_share + 0.15 * topic_whole
    limitation = None
    if not start_ok:
        limitation = f"Partial explanation: starts inside “{first_u.title}”."
    elif not end_ok:
        limitation = f"Partial explanation: stops before “{last_u.title}” is finished."
    elif not topic_whole and topic_s > MAX_S:
        limitation = (
            f"Whole steps, but the topic “{core.topic}” runs {topic_s:.0f} s in total "
            f"({_ts(units[ta].start_s)}–{_ts(units[tb].end_s)}), longer than a 60 s reel."
        )
    return {
        "units": [
            {
                "title": u.title,
                "kind": u.kind,
                "start_s": round(u.start_s, 2),
                "end_s": round(u.end_s, 2),
                "whole": w,
            }
            for u, ov, w in inside
            if ov >= min(8.0, 0.5 * u.duration_s)
        ],
        "core_unit": units.index(core),
        "topic": core.topic,
        "covers_topic": topic_whole,
        "starts_at_unit": start_ok,
        "ends_at_unit": end_ok,
        "complete": complete,
        "whole_unit_share": round(whole_share, 3),
        "opens_with": _quote(first),
        "ends_with": _quote(last),
        "weak_open": weak_open,
        "open_cue": bool(cue_open),
        "close_cue": bool(cue_end),
        "cut_before_answer": cliff,
        "ends_on_open_step": opens_up,
        "limitation": limitation,
        "parts": {
            k: round(v, 3)
            for k, v in (("context", context), ("opening", opening), ("ending", ending), ("teach", teach))
        },
    }


def score(c: Candidate, ctx: dict, extras: dict, llm: dict | None = None) -> None:
    """Weighted sum of the five named components (0..1 each); sets c.score, components and reasons."""
    p = ctx["parts"]
    tech = _clip01(extras.get("tech_terms", 0) / 6 + extras.get("spoken_screen_ids", 0) / 4)
    screen = _clip01(extras.get("screen_activity", 0) * 8 + min(extras.get("typing_samples", 0), 20) / 40)
    voice = _clip01(0.5 + 0.25 * extras.get("level_z", 0) + 0.25 * (extras.get("variation_z", 1) - 1))
    pace = _clip01(1 - abs(extras.get("words_per_s", 2.5) - 2.6) / 2.0)
    ideal = extras.get("ideal_s") or IDEAL_S  # learned from this workspace's published reels when available
    length = _clip01(1 - abs(c.duration_s - ideal) / (MAX_S - MIN_S) * 2)
    comp = {
        "context": p["context"],
        "educational": 0.6 * p["teach"] + 0.25 * tech + 0.15 * screen,
        "opening": p["opening"],
        "ending": p["ending"],
        "engagement": 0.45 * voice + 0.25 * pace + 0.30 * length,
    }
    if llm:  # the local LLM's reading of the text itself, blended in and kept visible in features.llm
        whole = (llm["standalone"] + llm["complete_start"] + llm["complete_end"]) / 3
        comp["context"] = 0.65 * comp["context"] + 0.35 * whole
        comp["educational"] = 0.65 * comp["educational"] + 0.35 * llm["educational"]
    comp = {k: round(_clip01(v), 3) for k, v in comp.items()}
    c.features["components"] = comp
    c.features["signals"] = {
        k: round(v, 3)
        for k, v in (
            ("technical", tech),
            ("screen", screen),
            ("voice", voice),
            ("pace", pace),
            ("length", length),
        )
    }
    c.score = round(sum(WEIGHTS[k] * comp[k] for k in WEIGHTS), 4)
    c.reasons = reasons(c, ctx, extras, llm)


def explain(ctx: dict) -> str:
    """One grounded sentence: which teaching units the clip covers and where it starts and stops."""
    us = ctx["units"]
    steps = [f"{u['kind']} “{u['title']}”" for u in us] or ["one stretch of explanation"]
    covered = steps[0] if len(steps) == 1 else ", ".join(steps[:-1]) + " and " + steps[-1]
    start = "starts where the instructor begins" if ctx["starts_at_unit"] else "starts at a pause inside"
    if ctx["ends_at_unit"]:
        end = "ends as that point is concluded"
    elif ctx["cut_before_answer"]:
        end = "stops before the answer that follows"
    else:
        end = "ends at a pause before the point is finished"
    first = us[0]["title"] if us else "this part"
    return f"Selected because it {start} “{first}”, covers the {covered}, and {end}."


def reasons(c: Candidate, ctx: dict, extras: dict, llm: dict | None) -> list[str]:
    out = [explain(ctx)]
    if ctx["weak_open"]:
        out.append(f"Check the start: “{ctx['opens_with']}” refers back to earlier talk")
    elif ctx["open_cue"]:
        out.append(f"Opens on a clear start: “{ctx['opens_with']}”")
    if ctx["cut_before_answer"]:
        out.append(f"Check the end: “{ctx['ends_with']}” is answered only after the clip")
    elif ctx.get("ends_on_open_step"):
        out.append("Check the end: it stops after the instructor poses the point, before it is worked out")
    elif ctx["close_cue"]:
        out.append(f"Ends on a conclusion: “{ctx['ends_with']}”")
    if ctx["limitation"]:
        out.append(ctx["limitation"])
    if extras.get("tech_terms"):
        out.append(f"{extras['tech_terms']} technical terms explained")
    if extras.get("spoken_screen_ids"):
        out.append(f"Mentions {extras['spoken_screen_ids']} identifiers visible on screen")
    if extras.get("typing_samples", 0) >= 6:
        out.append("Code is being typed or changed on screen")
    if extras.get("ideal_s") and abs(c.duration_s - extras["ideal_s"]) <= 5:
        out.append(f"Close to the length your audience engages with most ({extras['ideal_s']:.0f} s)")
    if c.features["signals"]["voice"] >= 0.6:
        out.append("Livelier delivery than the rest of the class")
    if llm:
        for ok, edge, hint in (
            (llm["complete_start"], "start", "begin earlier"),
            (llm["complete_end"], "end", "continue after"),
        ):
            if not ok:
                out.append(f"Check the {edge}: the local LLM thinks the thought may {hint} this point")
        out.append(f"Local LLM: {llm['reason']}")
    return out


def pause_ranker(sents: list[Sentence]):
    """Percentile of a pause among all sentence pauses of the recording (0..1)."""
    pauses = sorted(min(x.pause_after, 9.0) for x in sents)

    def rank(p: float) -> float:
        if not pauses:
            return 0.0
        below = sum(1 for q in pauses if q < min(p, 9.0))
        return below / len(pauses)

    return rank


def overlap(a: Candidate, b: Candidate) -> float:
    inter = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
    return inter / min(a.duration_s, b.duration_s)


def same_explanation(a: Candidate, b: Candidate) -> bool:
    """Duplicates: overlapping in time, centred on the same teaching unit, or mostly the same words
    (an instructor repeating an explanation later in the class)."""
    if overlap(a, b) > 0.35:
        return True
    ca, cb = a.features.get("context", {}).get("core_unit"), b.features.get("context", {}).get("core_unit")
    if ca is not None and ca == cb:
        return True
    wa, wb = ol.content_words(a.text), ol.content_words(b.text)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.55


def select(cands: list[Candidate], k: int = 8) -> list[Candidate]:
    """Greedy non-maximum suppression: best first, drop windows that duplicate a kept one."""
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda c: -c.score):
        if not any(same_explanation(c, k_) for k_ in kept):
            kept.append(c)
        if len(kept) == k:
            break
    return kept
