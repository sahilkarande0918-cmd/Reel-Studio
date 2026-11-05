"""Bulk clipping for talk profiles (business podcast, interview, story, creator talk): the whole recording's conversation
map → every standalone span that starts on a hook, carries its context and reaches its payoff → a diverse set of distinct
clips, as many as the recording genuinely supports (the requested count is a target, never a quota to fill).

Pipeline (pure functions; the analyze worker supplies the LLM, embeddings and caches):
1. `conversation_map`: the outline's parts (question, answer, story, lesson, ...) with question→answer links.
2. `merge_topics`: one canonical label per subject across the whole recording (chunked outlines name it differently).
3. `spans`: runs of whole parts within the requested duration; single long parts fall back to sentence windows.
4. `refine` + `features`: lead-in/out filler trimmed, then the explainable 100-point editorial score (profile weights).
5. `select`: best-first, deduplicated (time overlap, embeddings, shared words), topic- and timeline-diverse; each
   candidate the LLM rejects frees its slot; the report says how many good clips exist and why the rest were not made.

Scores are editorial ranking aids out of 100, never a probability of views.
"""

import math
import re
from collections import Counter

from app.services.highlights import outline as ol
from app.services.highlights import profiles as pf
from app.services.highlights.candidates import Candidate, Sentence, _quote, _ts

WORD = re.compile(r"[\w']+", re.U)
# openers that lean on what was just said ("Yeah, exactly.", "As I was saying...", "And that's why...")
LEAN_PHRASES = ("as i was saying", "coming back to", "going back to", "like i said", "that's why", "that is why",
                "and that's", "exactly", "yeah exactly", "right exactly", "same thing", "jaisa maine kaha", "wahi baat")
LEAN_FIRST = {"and", "but", "exactly", "yeah", "yes", "right", "also", "which", "because", "cause", "aur", "lekin",
              "par", "bilkul", "haan", "toh", "to", "isliye", "phir"}
PRONOUN_START = {"he", "she", "they", "it", "this", "that", "these", "those", "him", "her", "them", "his", "their",
                 "woh", "wo", "usne", "unhone", "ye", "yeh", "isne"}
TALK_FILLER = re.compile(r"^(yeah|yes|right|okay|ok|sure|exactly|totally|absolutely|wow|haha|hmm|mm|uh|um|thank you|"
                         r"thanks|great|cool|nice|true|indeed|haan|achha|accha|bilkul|sahi)[\s,.!?]*$", re.I)
HOOK_WORDS = re.compile(
    r"\b(mistake|biggest|never|always|secret|truth|most people|nobody|everyone|why|how to|the reason|failed|failure|"
    r"lost|million|billion|crore|lakh|lesson|wrong|stop|worst|best|first time|realised|realized|surprising|"
    r"shocking|actually|the problem|the key|nobody tells|galti|sabse|kabhi|sach|kyun|kyon|asli)\b", re.I)
CLOSE_WORDS = re.compile(
    r"(that's why|that is why|the lesson|the point is|bottom line|the key is|which is why|so if you|my advice|"
    r"in the end|the takeaway|that's the|that is the|so remember|so always|so never|isliye|yahi hai|matlab yeh)", re.I)
NUMBER = re.compile(r"\d|percent|%|₹|\$|crore|lakh|million|billion|thousand|hundred", re.I)
DUP_TIME, DUP_EMBED, DUP_WORDS = 0.3, 0.88, 0.5
MIN_SCORE = 55.0
PRACTICAL_MAX = 60  # "auto" still stops somewhere: a 3-hour stream rarely has more distinct standalone moments


def _toks(t: str) -> list[str]:
    return [w.lower() for w in WORD.findall(t)]


# greetings, thanks and segues: never the first or last line of a clip
SEGUE = re.compile(
    r"(welcome (back )?to|thanks for having me|thank you for having me|great to have you|happy to be here|"
    r"let's get into it|let's dive in|how are you|quick word from|brought to you by|back to it|by the way|"
    r"let's move on|moving on|before we go|that's all for|see you next|thank you so much for coming)", re.I)


SPONSOR = re.compile(r"(brought to you by|our sponsor|sponsored by|promo code|discount code|use (the )?code|"
                     r"percent off|% off|link in (the )?(description|bio)|check out .{0,30}\.com)", re.I)
TANGENT = re.compile(r"(by the way|off topic|random question|anyway,? we can talk about|some other time|"
                     r"another time|but anyway)", re.I)


def is_talk_filler(text: str) -> bool:
    return bool(TALK_FILLER.match(text.strip())) or ol.is_filler(text) or bool(SEGUE.search(text) and len(text) < 90)


def turn_question(k: int, texts: list[str], labels: list[str] | None) -> bool:
    """A real question that hands the turn over: with speaker labels, the voice changes before or after it, so a
    rhetorical question inside someone's answer ("What happened? ...") does not start a new part."""
    if not ol.open_question(texts[k]):
        return False
    if not labels:
        return True
    before = k == 0 or labels[k - 1] != labels[k]
    after = k + 1 >= len(texts) or labels[k + 1] != labels[k]
    return before or after


def split_questions(units: list[ol.Unit], texts: list[str], sents: list[Sentence], min_s: float = 4.0,
                    labels: list[str] | None = None) -> list[ol.Unit]:
    """Rebuild part boundaries around the questions: each real question is its own part and its reply starts the next
    (LLM outlines are often off by a sentence or fuse a question with the previous answer, or several Q&As). Kinds,
    titles and topics are taken from the LLM's parts by majority; tiny pieces merge into their neighbour. When the
    outline gave one topic to the whole show, each question→answer group gets its own topic (its answer's title)."""
    n = len(texts)
    if not n or not units:
        return units
    by_sent = [units[ol.unit_of(units, k)] for k in range(n)]
    qs = {k for k in range(n) if turn_question(k, texts, labels)}
    if labels:  # a short host turn between long answers is a prompt even without a "?" ("Coming back to X.")
        turns, s = [], 0
        for k in range(1, n + 1):
            if k == n or labels[k] != labels[s]:
                turns.append((s, k - 1))
                s = k
        for (pa, pb), (a, b), (na, nb) in zip(turns, turns[1:], turns[2:], strict=False):
            if (sents[pb].end_s - sents[pa].start_s >= 12 and b - a <= 1 and sents[nb].end_s - sents[na].start_s >= 10
                    and not SPONSOR.search(texts[a])):
                qs.add(a)
    # sponsor reads (with their "quick word from" / "back to it" segues) are their own parts, whatever the LLM said
    ads = {k for k in range(n) if SPONSOR.search(texts[k])}
    ads |= {k + d for k in ads for d in (-1, 1) if 0 <= k + d < n and SEGUE.search(texts[k + d]) and k + d not in qs}
    edges = {k for k in ads if k - 1 not in ads} | {k + 1 for k in ads if k + 1 not in ads and k + 1 < n}
    bounds = sorted({0, *(u.first for u in units), *qs, *(q + 1 for q in qs if q + 1 < n), *edges})
    pieces = [[a, b - 1] for a, b in zip(bounds, [*bounds[1:], n], strict=False)]
    merged: list[list[int]] = []
    for p in pieces:  # a short non-question piece is noise of the LLM's boundaries: join it to the previous answer
        short = sents[p[1]].end_s - sents[p[0]].start_s < min_s and p[0] not in qs and p[0] not in ads
        if merged and short and merged[-1][0] not in qs and merged[-1][0] not in ads:
            merged[-1][1] = p[1]
        else:
            merged.append(p)
    out: list[ol.Unit] = []
    for a, b in merged:
        weights: dict[tuple, float] = {}
        for k in range(a, b + 1):
            u = by_sent[k]
            key = (u.kind, u.title, u.topic, u.source)
            weights[key] = weights.get(key, 0.0) + sents[k].end_s - sents[k].start_s
        kind, title, topic, source = max(weights, key=weights.get)
        if a in ads:
            kind, title, topic = "sponsor", "Sponsor read", "sponsor"
        elif a in qs:
            kind = "tangent" if TANGENT.search(texts[a]) else "question"
        elif out and out[-1].kind == "tangent" and TANGENT.search(" ".join(texts[a : b + 1])):
            kind = "tangent"  # the reply to an off-topic aside ("..., but anyway, another time")
        elif kind in ("question", "introduction") and out and out[-1].kind == "question":
            kind = "answer"
        elif kind in pf.LOW_VALUE and any(x.kind == "question" for x in out):
            # an LLM "tangent/filler/sponsor" label inside an exchange stands only if the text agrees
            txt = " ".join(texts[a : b + 1])
            agrees = (SPONSOR.search(txt) if kind == "sponsor" else TANGENT.search(txt)) or all(
                is_talk_filler(texts[k]) for k in range(a, b + 1))
            if not agrees:
                kind = "answer"
                topic = next((x.topic for x in reversed(out) if x.kind not in pf.LOW_VALUE and x.topic), topic)
        if kind == "tangent":
            topic = "tangent"
        out.append(ol.Unit(a, b, sents[a].start_s, sents[b].end_s, kind, title, source, topic))
    questions = sum(x.kind == "question" for x in out)
    if questions >= 3 and len({x.topic for x in out}) * 3 <= questions:  # topic too coarse to tell subjects apart
        topic = None
        for i, x in enumerate(out):
            if x.kind == "question":
                nxt = next((y for y in out[i + 1 : i + 3] if y.kind != "question"), None)
                topic = (nxt or x).title
            if topic and x.kind not in pf.LOW_VALUE and x.kind != "introduction":
                x.topic = topic
    return out


def leans_back(text: str) -> bool:
    t = " ".join(_toks(text))
    toks = t.split()
    return bool(toks) and (toks[0] in LEAN_FIRST or any(t.startswith(p) for p in LEAN_PHRASES))


def unresolved_referent(text: str) -> bool:
    toks = _toks(text)
    return bool(toks) and toks[0] in PRONOUN_START


def hook_strength(text: str) -> float:
    """0..1 from the first sentence alone: a real question, a number, a strong claim; leaning back costs."""
    s = 0.25
    s += 0.3 * ol.open_question(text)
    s += 0.2 * bool(NUMBER.search(text))
    s += 0.3 * min(len(HOOK_WORDS.findall(text)), 2) / 2
    s *= 0.35 if leans_back(text) else 0.6 if unresolved_referent(text) else 1.0
    return max(0.0, min(1.0, s))


# ---------------------------------------------------------------- 1. conversation map


def qa_links(units: list[ol.Unit]) -> list[dict]:
    """Each question → the parts that answer it (until the next question or topic change, at most 4 parts)."""
    out = []
    for i, u in enumerate(units):
        if u.kind != "question":
            continue
        ans = []
        for j in range(i + 1, min(len(units), i + 5)):
            if units[j].kind in ("question", "introduction") or units[j].topic != u.topic and ans:
                break
            ans.append(j)
        if ans:
            out.append({"question": i, "answers": ans})
    return out


def conversation_map(units: list[ol.Unit], texts: list[str], labels: list[str] | None = None) -> dict:
    """Time-coded map of the whole recording: parts, topics and question→answer links, quotes verbatim."""
    links = qa_links(units)
    answered_by = {a: L["question"] for L in links for a in L["answers"]}
    parts = []
    for i, u in enumerate(units):
        sp = sorted({labels[k] for k in range(u.first, u.last + 1)}) if labels else []
        parts.append({"i": i, "kind": u.kind, "topic": u.topic, "title": u.title, "start_s": round(u.start_s, 2),
                      "end_s": round(u.end_s, 2), "speakers": sp, "opens_with": _quote(texts[u.first], 120),
                      "ends_with": _quote(texts[u.last], 120), "answers_question": answered_by.get(i)})
    topics: list[dict] = []
    for p in parts:
        if not topics or topics[-1]["topic"] != p["topic"]:
            topics.append({"topic": p["topic"], "start_s": p["start_s"], "end_s": p["end_s"], "parts": 0})
        topics[-1]["end_s"], topics[-1]["parts"] = p["end_s"], topics[-1]["parts"] + 1
    kinds = Counter(p["kind"] for p in parts)
    return {"parts": parts, "topics": topics, "qa": links, "counts": dict(kinds)}


def merge_topics(units: list[ol.Unit], embed=None, threshold: float = 0.83) -> None:
    """Give one label to the same subject named differently by separate outline chunks (in place)."""
    names = list(dict.fromkeys(u.topic.strip() for u in units if u.topic.strip()))
    if len(names) < 2:
        return
    vecs = embed(names) if embed else None
    canon: dict[str, str] = {}
    for i, n in enumerate(names):
        for m in names[:i]:
            if canon.get(m, m) != m:
                continue
            same = n.lower() == m.lower() or (vecs and _cos(vecs[i], vecs[names.index(m)]) >= threshold)
            if same:
                canon[n] = m
                break
    for u in units:
        u.topic = canon.get(u.topic.strip(), u.topic)


# ---------------------------------------------------------------- 2. spans


def spans(units: list[ol.Unit], sents: list[Sentence], min_s: float, max_s: float) -> list[tuple[int, int]]:
    """(first, last) sentence ranges: runs of whole parts within min..max; a part longer than max_s contributes its
    sentence windows instead, so a long story still yields its strongest complete stretch."""
    out = set()
    for i in range(len(units)):
        if units[i].kind in pf.LOW_VALUE:
            continue  # never open on a sponsor read, tangent or chit-chat
        for j in range(i, len(units)):
            d = units[j].end_s - units[i].start_s
            if d > max_s:
                break
            if d >= min_s and units[j].kind not in pf.LOW_VALUE:
                out.add((units[i].first, units[j].last))
        u = units[i]
        if u.duration_s > max_s:
            for a in range(u.first, u.last + 1):
                for b in range(a, u.last + 1):
                    d = sents[b].end_s - sents[a].start_s
                    if d > max_s:
                        break
                    if d >= min_s:
                        out.add((a, b))
    return sorted(out)


def refine(a: int, b: int, texts: list[str], sents: list[Sentence], min_s: float) -> tuple[int, int]:
    """Trim lead-in/out chit-chat ("Yeah.", greetings, "Quick word from our sponsor.") while the clip stays long
    enough."""
    while a < b and is_talk_filler(texts[a]) and sents[b].end_s - sents[a + 1].start_s >= min_s:
        a += 1
    while b > a and is_talk_filler(texts[b]) and sents[b - 1].end_s - sents[a].start_s >= min_s:
        b -= 1
    return a, b


# ---------------------------------------------------------------- 3. features + score


def features(a: int, b: int, units: list[ol.Unit], sents: list[Sentence], texts: list[str], profile: dict,
             ideal_s: float, extras: dict) -> dict:
    """The seven editorial components (0..1) with the evidence behind each, quotes verbatim."""
    ua, ub = ol.unit_of(units, a), ol.unit_of(units, b)
    inside = units[ua : ub + 1]
    first, last = texts[a], texts[b]
    dur = max(sents[b].end_s - sents[a].start_s, 1e-6)
    start_whole = a == units[ua].first or all(is_talk_filler(texts[k]) for k in range(units[ua].first, a))
    end_whole = b == units[ub].last or all(is_talk_filler(texts[k]) for k in range(b + 1, units[ub].last + 1))
    prev = units[ua - 1] if ua > 0 else None
    # an answer without its question (or a lesson without the story it closes) needs the earlier part
    orphan_answer = units[ua].kind == "answer" and start_whole and prev is not None and prev.kind == "question"
    # in a conversation the exchange (question + every part of its answer) is the unit a Short is cut from:
    # starting on a later part of an answer, or stopping before its last part, cuts the exchange
    gq = next((i for i in range(ua, -1, -1) if units[i].kind == "question"), None)
    mid_start = gq is not None and gq < ua - 1 and units[ua].kind not in pf.LOW_VALUE
    group_end = next((i - 1 for i in range(ub + 1, len(units)) if units[i].kind in ("question", "sponsor", "tangent")),
                     len(units) - 1)
    mid_end = ub < group_end and any(units[i].kind not in pf.LOW_VALUE for i in range(ub + 1, group_end + 1))
    if mid_start:
        start_whole = False
    if mid_end:
        end_whole = False
    nxt_unit = units[ub + 1] if ub + 1 < len(units) else None
    before_lesson = (units[ub].kind in ("story", "problem", "question", "example") and nxt_unit is not None
                     and nxt_unit.topic == units[ub].topic and nxt_unit.kind in pf.PAYOFF_KINDS)
    nxt_text = texts[b + 1] if b + 1 < len(texts) else ""
    cliff = ol.open_question(last) and bool(nxt_text) and not is_talk_filler(nxt_text)
    weak = leans_back(first)
    referent = unresolved_referent(first)

    subjects = list(dict.fromkeys(u.topic for u in inside if u.kind not in pf.LOW_VALUE and u.kind != "introduction"))
    inner = [u for u in inside[1:] if u.kind == "question"]
    if any(u.kind == "question" for u in inside):
        # in a conversation the exchanges count, not the topic strings (a question and its answer may be labelled
        # "finance" and "fundraising"; a second question is a second exchange even under one label)
        subjects = [units[ua].topic] + [f"question at {_ts(u.start_s)}" for u in inner]
    hook = 0.55 * hook_strength(first) + 0.45 * (units[ua].kind in pf.HOOK_KINDS and start_whole)
    context = (0.35 * start_whole + 0.25 * end_whole + 0.4) * (0.45 if orphan_answer else 1.0) * (
        0.6 if weak else 0.8 if referent else 1.0) * (0.55 if len(subjects) > 1 else 1.0)  # one Short, one idea
    payoff = (0.45 * end_whole + 0.35 * (units[ub].kind in pf.PAYOFF_KINDS) + 0.2 * bool(CLOSE_WORDS.search(last)))
    payoff *= 0.25 if cliff else 0.5 if before_lesson else 1.0
    vals = profile["value"]
    low = sum(min(u.end_s, sents[b].end_s) - max(u.start_s, sents[a].start_s) for u in inside if u.kind in pf.LOW_VALUE)
    kind_value = sum(vals.get(u.kind, 0.5) * max(0.0, min(u.end_s, sents[b].end_s) - max(u.start_s, sents[a].start_s))
                     for u in inside) / dur
    text = " ".join(texts[a : b + 1])
    specific = min(len(NUMBER.findall(text)), 3) / 3
    value = 0.8 * kind_value + 0.2 * specific
    voice = max(0.0, min(1.0, 0.5 + 0.25 * extras.get("level_z", 0) + 0.25 * (extras.get("variation_z", 1) - 1)))
    pace = max(0.0, min(1.0, 1 - abs(extras.get("words_per_s", 2.6) - 2.7) / 2.0))
    length = max(0.0, min(1.0, 1 - abs(dur - ideal_s) / max(ideal_s, 1)))
    delivery = 0.45 * voice + 0.3 * pace + 0.25 * length
    visual = extras.get("visual", 0.6)
    brief = extras.get("brief_terms") or set()
    relevance = 1.0 if not brief else min(1.0, len(brief & set(_toks(text))) / max(1, min(len(brief), 3)))
    comp = {"hook": hook, "context": context, "payoff": payoff, "value": value, "delivery": delivery,
            "visual": visual, "relevance": relevance}
    limits = []
    if orphan_answer:
        limits.append(f"Answers the question at {_ts(prev.start_s)} without showing it")
    elif mid_start:
        limits.append(f"Starts inside the answer to the question at {_ts(units[gq].start_s)}")
    if mid_end:
        limits.append(f"Stops before the answer finishes at {_ts(units[group_end].end_s)}")
    if weak:
        limits.append(f"Opens leaning on earlier talk: “{_quote(first, 80)}”")
    elif referent:
        limits.append(f"Opens on a pronoun whose referent may be earlier: “{_quote(first, 80)}”")
    if cliff:
        limits.append(f"Ends on a question answered only after the clip: “{_quote(last, 80)}”")
    if before_lesson:
        limits.append(f"Stops before the {nxt_unit.kind} at {_ts(nxt_unit.start_s)} that concludes it")
    if len(subjects) > 1:
        limits.append(f"Covers {len(subjects)} subjects ({', '.join(subjects[:3])}); a Short usually lands one idea")
    return {
        "components": {k: round(max(0.0, min(1.0, v)), 3) for k, v in comp.items()},
        "kinds": [u.kind for u in inside],
        "topic": max(inside, key=lambda u: u.duration_s).topic,
        "core_unit": units.index(max(inside, key=lambda u: u.duration_s)),
        "titles": [u.title for u in inside],
        "hook_quote": _quote(first, 140),
        "ending_quote": _quote(last, 140),
        "starts_whole": start_whole,
        "ends_whole": end_whole,
        "complete": start_whole and end_whole and not orphan_answer and not cliff,
        "low_value_share": round(low / dur, 3),
        "limitations": limits,
    }


def score(f: dict, weights: dict) -> float:
    return round(sum(weights[k] * f["components"][k] for k in weights), 1)


def blend_llm(f: dict, j: dict) -> None:
    """Fold the local LLM's reading of the text into the components (kept visible in features.llm)."""
    c = f["components"]
    c["hook"] = round(0.5 * c["hook"] + 0.5 * j["hook"], 3)
    c["context"] = round(0.55 * c["context"] + 0.45 * (0.6 * j["standalone"] + 0.4 * j["complete_start"]), 3)
    c["payoff"] = round(0.55 * c["payoff"] + 0.45 * j["complete_end"], 3)
    c["value"] = round(0.5 * c["value"] + 0.5 * j["value"], 3)
    if j.get("limitation") and not j["complete_start"] and not j["complete_end"]:  # only when it rejects both edges
        f["limitations"].append(f"LLM: {j['limitation']}"[:200])


def grounded_title(title: str, text: str, fallback: str) -> str:
    """The LLM's title only when most of its content words are spoken in the clip; otherwise the outline's title.
    Stops titles that promise something the clip never says."""
    tw, cw = ol.content_words(title), ol.content_words(text)
    if title.strip() and tw and len(tw & cw) / len(tw) >= 0.5:
        return title.strip()
    return fallback


def why(f: dict, profile: dict) -> str:
    kinds = list(dict.fromkeys(k for k in f["kinds"] if k not in pf.LOW_VALUE))
    kind_txt = " → ".join(kinds[:4]) or "conversation"
    start = "opens on a clear start" if f["starts_whole"] else "opens mid-part"
    end = "reaches its conclusion" if f["ends_whole"] and not f["limitations"] else "check the ending"
    return f"{profile['label']}: {kind_txt} about “{f['topic']}”; {start} and {end}."


def recommendations(f: dict, words: list[dict], start_s: float, end_s: float) -> list[str]:
    """Grounded editing suggestions: numbers worth a callout, a punch-in on the payoff, caption emphasis."""
    out = []
    nums = [w for w in words if start_s <= w["start_s"] <= end_s and NUMBER.search(w.get("corrected_text") or "")]
    for w in nums[:2]:
        out.append(f"Key-number callout on “{w['corrected_text']}” at {w['start_s'] - start_s:.1f} s")
    if f["components"]["payoff"] >= 0.6:
        out.append("Punch-in on the closing line to land the payoff")
    if f["components"]["hook"] >= 0.6:
        out.append("Hook title over the first 2 s (spoken words only)")
    return out


def hook_teaser(a: int, b: int, texts: list[str], sents: list[Sentence], max_s: float = 7.0) -> dict | None:
    """An authentic line from later in the same clip that would open stronger than its first sentence. Proposed only,
    never applied by default; the clip still plays in its original order after it (reversible, labelled)."""
    base = hook_strength(texts[a])
    best = None
    for k in range(a + 2, b + 1):
        d = sents[k].end_s - sents[k].start_s
        h = hook_strength(texts[k])
        if 2.0 <= d <= max_s and not leans_back(texts[k]) and not unresolved_referent(texts[k]) and h >= base + 0.25:
            if not best or h > best[0]:
                best = (h, k)
    if not best:
        return None
    k = best[1]
    return {"start_s": round(sents[k].start_s, 2), "end_s": round(sents[k].end_s, 2), "text": texts[k],
            "rearranged": True, "note": "Proposed opening quote from later in this clip (original words, not applied)"}


# ---------------------------------------------------------------- 4. selection


def _cos(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def tfidf(texts: list[str]) -> list[list[float]]:
    """Fallback embeddings when the embedding model is unavailable (scikit-learn, already installed)."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not texts:
        return []
    m = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True).fit_transform(texts)
    return m.toarray().tolist()


def overlap(a: Candidate, b: Candidate) -> float:
    inter = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
    return inter / max(min(a.duration_s, b.duration_s), 1e-6)


def duplicate(a: Candidate, b: Candidate) -> str | None:
    """Why two clips say the same thing, or None: overlapping time, near-identical meaning, mostly the same words."""
    if overlap(a, b) > DUP_TIME:
        return "overlaps in time"
    va, vb = a.features.get("_vec"), b.features.get("_vec")
    if va is not None and vb is not None and _cos(va, vb) >= DUP_EMBED:
        return "repeats the same idea"
    wa, wb = ol.content_words(a.text), ol.content_words(b.text)
    if wa and wb and len(wa & wb) / len(wa | wb) >= DUP_WORDS:
        return "mostly the same words"
    return None


def select(cands: list[Candidate], target: int | None, judge=None, budget: int = 40,
           min_score: float = MIN_SCORE, duration_s: float = 0.0) -> tuple[list[Candidate], dict]:
    """Best-first diverse selection. `judge(c) -> bool` (LLM) may veto a clip; a vetoed clip frees its slot.
    Returns the clips in recording order and an honest report of what was found and why the rest was not made."""
    want = min(target or PRACTICAL_MAX, PRACTICAL_MAX)
    rejected = Counter()
    eligible = []
    for c in cands:
        f = c.features
        if f["low_value_share"] > 0.5:
            rejected["filler, sponsor or off-topic"] += 1
        elif not f["complete"] and c.score < min_score + 10:
            rejected["incomplete (starts or ends mid-thought)"] += 1
        elif c.score < min_score:
            rejected["low editorial score"] += 1
        else:
            eligible.append(c)
    eligible.sort(key=lambda c: -c.score)
    kept: list[Candidate] = []
    topics: Counter = Counter()
    buckets: Counter = Counter()
    nb = max(4, min(12, int(duration_s // 300) or 4))  # timeline coverage buckets (~5 min each)
    judged = vetoed = 0
    dup_groups: dict[int, list[dict]] = {}
    pool = list(eligible)
    while pool and len(kept) < want:
        def eff(c: Candidate) -> float:  # diversity: repeat topics and crowded stretches cost a little
            bucket = int(c.start_s / max(duration_s, 1) * nb) if duration_s else 0
            return c.score - 5 * topics[c.features["topic"]] - 3 * buckets[bucket]

        c = max(pool, key=eff)
        pool.remove(c)
        dup = next(((k, r) for k in kept if (r := duplicate(c, k))), None)
        if dup:
            dup_groups.setdefault(id(dup[0]), []).append(
                {"start_s": round(c.start_s, 2), "end_s": round(c.end_s, 2), "why": dup[1], "score": c.score})
            continue
        if judge and judged < budget:
            judged += 1
            if not judge(c):
                vetoed += 1
                continue
        kept.append(c)
        topics[c.features["topic"]] += 1
        buckets[int(c.start_s / max(duration_s, 1) * nb) if duration_s else 0] += 1
    for k in kept:
        group = dup_groups.get(id(k))
        if group:
            k.features["duplicates"] = group
    dups = sum(len(g) for g in dup_groups.values())
    why_dup = Counter(d["why"] for g in dup_groups.values() for d in g)
    report = {
        "requested": target,
        "selected": len(kept),
        "candidates": len(cands),
        "eligible": len(eligible),
        "llm_judged": judged,
        "llm_rejected": vetoed,
        "duplicates_rejected": dups,
        "duplicate_reasons": dict(why_dup),
        "rejected": dict(rejected),
        "topics_covered": len({k.features["topic"] for k in kept}),
    }
    if target and len(kept) < target:
        alt = why_dup.get("overlaps in time", 0)
        rep = dups - alt
        why_not = [f"{n} {r}" for r, n in rejected.most_common()] + (
            [f"{rep} repeated an idea already selected"] if rep else []) + (
            [f"{alt} were alternative cuts of moments already selected"] if alt else []) + (
            [f"{vetoed} failed the standalone check"] if vetoed else [])
        report["shortfall"] = (
            f"Only {len(kept)} distinct standalone clips meet the quality bar (requested {target}). "
            "The rest were not produced rather than padded: " + ("; ".join(why_not) or "no further candidates") + ".")
    kept.sort(key=lambda c: c.start_s)
    for k in kept:
        k.features.pop("_vec", None)
    return kept, report


def editorial(score_: float) -> dict:
    """The label shown next to a score: what it is and what it is not."""
    return {"score": score_, "out_of": 100, "kind": "editorial ranking aid (not a view or virality prediction)"}
