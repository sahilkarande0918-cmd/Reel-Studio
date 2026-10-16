"""Highlight candidates: 30-60 s windows that start and end on complete thoughts.

Boundaries come only from sentence ends that are followed by a pause, so a clip never starts or
stops mid-sentence. Each window gets transparent features and a weighted HEURISTIC score
(labelled as such; it is not a calibrated probability). An optional LLM pass adds a judgment of
standalone completeness plus a title and summary.
"""

import re
from dataclasses import dataclass, field

MIN_S, MAX_S, IDEAL_S = 30.0, 60.0, 45.0
SENT_END = re.compile(r"[.?!।]$")
OPENERS = {
    "toh",
    "to",
    "ab",
    "chalo",
    "so",
    "now",
    "dekho",
    "sabse",
    "pehle",
    "pahle",
    "iska",
    "lekin",
    "aur",
    "ek",
    "yeh",
    "yah",
    "agar",
    "namaste",
}
DEFAULT_WEIGHTS = {
    "boundary": 0.35,  # pauses at both ends (speaker-relative), opener word
    "length": 0.10,  # closeness to 45 s
    "voice": 0.15,  # energy level and variation
    "pace": 0.10,  # comfortable speech rate
    "screen": 0.15,  # typing / on-screen change while explaining
    "technical": 0.15,  # technical terms and on-screen identifiers that are also spoken
}


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


def score_window(c: Candidate, s0: Sentence, s1: Sentence, extras: dict, weights: dict) -> None:
    f = c.features
    first = re.sub(r"\W", "", c.text.split()[0].lower()) if c.text else ""
    f["pause_before_s"] = round(min(s0.pause_before, 3.0), 2)
    f["pause_after_s"] = round(min(s1.pause_after, 3.0), 2)
    f["opener"] = first in OPENERS
    # Pauses are ranked against this speaker's own sentence pauses: a topic change is a pause that is
    # long *for this instructor*, whatever their pace.
    ranks = extras.get("pause_ranks")
    rb = ranks(s0.pause_before) if ranks else _clip01(s0.pause_before / 1.2)
    ra = ranks(s1.pause_after) if ranks else _clip01(s1.pause_after / 1.2)
    f["pause_rank_before"], f["pause_rank_after"] = round(rb, 3), round(ra, 3)
    boundary = rb * 0.4 + ra * 0.4 + (0.2 if f["opener"] else 0.0)
    ideal = extras.get("ideal_s") or IDEAL_S  # learned from this workspace's published reels when available
    length = 1 - abs(c.duration_s - ideal) / (MAX_S - MIN_S) * 2
    voice = _clip01(0.5 + 0.25 * extras.get("level_z", 0) + 0.25 * (extras.get("variation_z", 1) - 1))
    wps = extras.get("words_per_s", 2.5)
    pace = _clip01(1 - abs(wps - 2.6) / 2.0)
    screen = _clip01(extras.get("screen_activity", 0) * 8 + min(extras.get("typing_samples", 0), 20) / 40)
    tech = _clip01(extras.get("tech_terms", 0) / 6 + extras.get("spoken_screen_ids", 0) / 4)
    parts = {
        "boundary": boundary,
        "length": _clip01(length),
        "voice": voice,
        "pace": pace,
        "screen": screen,
        "technical": tech,
    }
    f["components"] = {k: round(v, 3) for k, v in parts.items()}
    c.score = round(sum(weights[k] * parts[k] for k in weights) / sum(weights.values()), 4)
    if s0.pause_before >= 0.5 and s1.pause_after >= 0.5:
        c.reasons.append(
            f"Starts after a {s0.pause_before:.1f} s pause and ends before a {s1.pause_after:.1f} s pause"
        )
    if f["opener"]:
        c.reasons.append(f"Opens with “{c.text.split()[0]}”, a typical start of a new point")
    if extras.get("tech_terms"):
        c.reasons.append(f"{extras['tech_terms']} technical terms explained")
    if extras.get("spoken_screen_ids"):
        c.reasons.append(f"Mentions {extras['spoken_screen_ids']} identifiers visible on screen")
    if extras.get("typing_samples", 0) >= 6:
        c.reasons.append("Code is being typed or changed on screen")
    if extras.get("ideal_s") and abs(c.duration_s - extras["ideal_s"]) <= 5:
        c.reasons.append(f"Close to the length your audience engages with most ({extras['ideal_s']:.0f} s)")
    if voice >= 0.6:
        c.reasons.append("Livelier delivery than the rest of the class")


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


def select(cands: list[Candidate], k: int = 8, max_overlap: float = 0.35) -> list[Candidate]:
    """Greedy non-maximum suppression: best first, drop windows overlapping a kept one."""
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda c: -c.score):
        if all(overlap(c, k_) <= max_overlap for k_ in kept):
            kept.append(c)
        if len(kept) == k:
            break
    return kept
