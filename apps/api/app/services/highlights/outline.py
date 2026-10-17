"""Lecture outline: the class split into teaching steps, grouped into topics.

The local LLM reads the numbered, timed transcript sentences and returns contiguous steps (introduction,
concept, example, demonstration, question, recap, conclusion, digression), each with the broader topic it
belongs to; long classes are read in overlapping chunks. Its output is repaired into a gap-free, in-order
cover of the sentences, and any step longer than a reel is split at its strongest internal boundary.
Without the LLM, a deterministic lexical segmentation (TextTiling-style vocabulary shift + this speaker's
long pauses) stands in and is labelled as such. The phrase lists here (filler, back-references, opening
and closing cues) are shared with clip scoring in `candidates.py`.
"""

import math
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

KINDS = (
    "introduction",
    "concept",
    "example",
    "demonstration",
    "question",
    "recap",
    "conclusion",
    "digression",
)
# how much a step of this kind teaches on its own (educational value of the time it fills)
TEACH_VALUE = {
    "concept": 1.0,
    "example": 1.0,
    "demonstration": 1.0,
    "question": 0.8,
    "conclusion": 0.8,
    "recap": 0.6,
    "introduction": 0.6,
    "digression": 0.0,
}
CHUNK = 150  # sentences per LLM call; ~8k tokens of Hinglish
MAX_STEP_S, MIN_STEP_S = 60.0, 12.0

STOP = set(
    """hai hain ho hota hoti hote tha thi the to toh ki ka ke ko se mein me main ham hum aap tum aur ya na nahin nahi
    bhi yah yeh vah woh wo ye is us isko usko iska uska iske uske ek kya kar karo karte karna kiya thik theek bhai
    ab phir jo jab tab aise kaise kahan kahaan yahan vahan apan apna hamen hamse mere mera tumhen bola boloon dekho
    lo do de diya gaya gai gaye aaya aai aa raha rahi rahe sab koi kuchh bahut badhiya matlab saahab yaar na chalo
    a an the of to and or is are was were be in on at it this that these those for with as by from so then if
    but not no yes ok okay right we you i they he she my our your can will just also very now here there what""".split()
)
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]+")
# a sentence made only of these says nothing a viewer needs ("Thik hai?", "Hai na bhai?", "Bahut badhiya.")
FILLER_WORDS = set(
    "thik theek hai na bhai ok okay haan achha acha bahut badhiya hmm right so chalo ji kya samajh mein aaya aai"
    " sahi baat".split()
)
TAG_QUESTION = re.compile(r"(thik|theek|hai na|samajh|clear|right|ok|okay|na bhai|badhiya)[\w\s]*\?$", re.I)
# a first word that leans on what was just said ("Phir ...", "Isko ...", "Tabhi ...") makes a weak opening
LEANS_BACK = set(
    """phir fir uske iske isko usko isse usse iska uska same then which minus plus tabhi islie isliye lautkar
    aur and lekin but par yahi vahi wahi matlab also too vaise waise yah ye yeh vah woh""".split()
)
OPEN_CUES = tuple(
    (
        "kya hai|kya hota|what is|aaj |today|let's|let us|chalo|samajhte|samjhate|samajhaate|dekhte hain|suppose|"
        "maan lo|maano|savaal|sawal|question|example|pehle|pahle|first|ab hum|ab ham|aaie|aaiye|hello|namaste"
    ).split("|")
)
CLOSE_CUES = tuple(
    (
        "isliye|islie|therefore|proof ho|clear ho|samajh|answer|yahi|that's why|tabhi|ho gaya|ho gai|fark hai|"
        "difference|so this|matlab yah|to yah"
    ).split("|")
)


@dataclass
class Unit:
    first: int  # sentence index, inclusive
    last: int
    start_s: float
    end_s: float
    kind: str
    title: str
    source: str  # "llm" | "llm+split" | "lexical"
    topic: str = ""  # broader concept; consecutive units with the same topic form one topic segment

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    def to_json(self) -> dict:
        return {
            "first": self.first,
            "last": self.last,
            "start_s": round(self.start_s, 2),
            "end_s": round(self.end_s, 2),
            "kind": self.kind,
            "title": self.title,
            "topic": self.topic,
            "source": self.source,
        }


def content_words(text: str) -> set[str]:
    return {w.lower() for w in WORD.findall(text) if w.lower() not in STOP and len(w) > 2}


def is_filler(text: str) -> bool:
    toks = re.findall(r"[a-z0-9]+", text.lower())  # digits count: "0 aaya hai." is an answer, not filler
    return not toks or all(t in FILLER_WORDS for t in toks)


def leans_back(text: str) -> bool:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    return bool(toks) and (toks[0] in LEANS_BACK or toks[0][0].isdigit() or toks[:2] == ["to", "yah"])


def has_cue(text: str, cues: tuple[str, ...]) -> bool:
    t = f" {text.lower()} "
    return any(c in t for c in cues)


def open_question(text: str) -> bool:
    """A real question (not a tag like "thik hai?") that the next sentence is about to answer."""
    return text.rstrip().endswith("?") and not TAG_QUESTION.search(text.strip()) and not is_filler(text)


def repair(raw: list[dict], lo: int, hi: int, sents, source: str = "llm") -> list[Unit]:
    """LLM units → contiguous, in-order cover of sentences lo..hi (gaps join the next unit)."""
    items = []
    for u in raw:
        try:
            f, last = int(u["first"]), int(u["last"])
        except (KeyError, TypeError, ValueError):
            continue
        title, topic = str(u.get("title", "")).strip()[:80], str(u.get("topic", "")).strip()[:80]
        items.append((max(lo, min(f, hi)), max(lo, min(last, hi)), u.get("kind"), title, topic))
    out: list[Unit] = []
    nxt = lo
    for _, last, kind, title, topic in sorted(items):
        if last < nxt:
            continue
        kind = kind if kind in KINDS else "concept"
        out.append(
            Unit(nxt, last, sents[nxt].start_s, sents[last].end_s, kind, title, source, topic or title)
        )
        nxt = last + 1
    if out and nxt <= hi:  # trailing sentences the LLM left out belong to the last unit
        out[-1].last, out[-1].end_s = hi, sents[hi].end_s
    return out


def boundary_strength(i: int, texts: list[str], sents, ranker) -> float:
    """How good a step boundary the gap after sentence i is: a long pause for this speaker, a closing
    sentence before it, a fresh start after it; never right before the answer to a question."""
    nxt = texts[i + 1]
    return (
        0.5 * ranker(sents[i].pause_after)
        + 0.25 * has_cue(texts[i], CLOSE_CUES)
        + 0.25 * (has_cue(nxt, OPEN_CUES) or open_question(nxt))
        - 0.4 * leans_back(nxt)
        - 0.5 * open_question(texts[i])
        - 0.3 * is_filler(nxt)
    )


def split_long(units: list[Unit], texts: list[str], sents, ranker) -> list[Unit]:
    """A step longer than a reel is cut at its strongest internal boundary until every piece fits."""
    out: list[Unit] = []
    todo = list(units)
    while todo:
        u = todo.pop(0)
        cuts = [
            i
            for i in range(u.first, u.last)
            if sents[i].end_s - u.start_s >= MIN_STEP_S and u.end_s - sents[i + 1].start_s >= MIN_STEP_S
        ]
        if u.duration_s <= MAX_STEP_S or not cuts:
            out.append(u)
            continue
        i = max(cuts, key=lambda i: boundary_strength(i, texts, sents, ranker))
        src = "llm+split" if u.source.startswith("llm") else u.source
        a = Unit(u.first, i, u.start_s, sents[i].end_s, u.kind, u.title, src, u.topic)
        b = Unit(i + 1, u.last, sents[i + 1].start_s, u.end_s, u.kind, u.title, src, u.topic)
        todo[:0] = [a, b]
    # parts of one split step are numbered so the outline stays readable
    for key in {(x.title, x.topic) for x in out if x.source == "llm+split"}:
        parts = [x for x in out if (x.title, x.topic) == key and x.source == "llm+split"]
        for n, x in enumerate(parts, 1):
            x.title = f"{key[0]} (part {n} of {len(parts)})"
    return out


def outline(
    texts: list[str], sents, ranker, llm_units: Callable[[list[str]], list[dict] | None]
) -> list[Unit]:
    """Teaching steps over all sentences. `llm_units` gets numbered, timed lines for one chunk."""
    n = len(texts)
    if not n:
        return []
    units: list[Unit] = []
    i = 0
    while i < n:
        j = min(n, i + CHUNK)
        raw = llm_units([f"[{k}] {_mmss(sents[k].start_s)} {texts[k]}" for k in range(i, j)])
        us = repair(raw, i, j - 1, sents) if raw else []
        if not us:
            return split_long(lexical(texts, sents, ranker), texts, sents, ranker)
        if j < n and len(us) > 1:
            us = us[:-1]  # the chunk's last unit may continue: read it again at the start of the next chunk
        units += us
        i = us[-1].last + 1
    return split_long(units, texts, sents, ranker)


def lexical(texts: list[str], sents, ranker, k: int = 5, min_s: float = 15.0) -> list[Unit]:
    """Deterministic fallback: a boundary where the vocabulary shifts and the speaker pauses long."""
    n = len(texts)
    bags = [Counter(content_words(t)) for t in texts]

    def cos(a: Counter, b: Counter) -> float:
        dot = sum(a[w] * b[w] for w in a)
        na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    gap: list[float] = []
    mu = sd = 0.0
    for i in range(n - 1):
        left, right = Counter(), Counter()
        for b in bags[max(0, i - k + 1) : i + 1]:
            left.update(b)
        for b in bags[i + 1 : i + 1 + k]:
            right.update(b)
        gap.append(0.6 * (1 - cos(left, right)) + 0.4 * ranker(sents[i].pause_after))
    if gap:
        mu = sum(gap) / len(gap)
        sd = math.sqrt(sum((g - mu) ** 2 for g in gap) / len(gap))
    cuts, start = [], 0
    for i, g in enumerate(gap):
        peak = g >= (gap[i - 1] if i else 0) and g >= (gap[i + 1] if i + 1 < len(gap) else 0)
        if peak and g >= mu + 0.5 * sd and sents[i].end_s - sents[start].start_s >= min_s:
            cuts.append(i)
            start = i + 1
    out, f = [], 0
    for last in [*cuts, n - 1]:
        words: Counter = Counter()
        for b in bags[f : last + 1]:
            words.update(b)
        title = ", ".join(w for w, _ in words.most_common(3)).title() or "Untitled part"
        qs = sum(open_question(t) for t in texts[f : last + 1])
        kind = "question" if qs * 2 > last - f + 1 else "concept"
        out.append(Unit(f, last, sents[f].start_s, sents[last].end_s, kind, title, "lexical", title))
        f = last + 1
    return out


def topic_span(units: list[Unit], i: int) -> tuple[int, int]:
    """Indices of the first and last unit of the topic segment that unit i belongs to."""
    a = b = i
    while a > 0 and units[a - 1].topic == units[i].topic:
        a -= 1
    while b + 1 < len(units) and units[b + 1].topic == units[i].topic:
        b += 1
    return a, b


def _mmss(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def unit_of(units: list[Unit], sentence: int) -> int:
    for i, u in enumerate(units):
        if u.first <= sentence <= u.last:
            return i
    return len(units) - 1
