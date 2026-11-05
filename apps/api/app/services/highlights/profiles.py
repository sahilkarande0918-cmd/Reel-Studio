"""Clip selection profiles: what a recording is (class, business podcast, interview, story, creator talk) decides which
conversation parts the outline looks for, how much each part is worth on its own, and how the 100-point editorial score
is weighted. Weights are editorial starting points (inspectable, tunable per profile), never a virality probability.

`education` is the original teaching-step profile and keeps its own scoring path in `candidates.py` unchanged.
"""

EDU_KINDS = ("introduction", "concept", "example", "demonstration", "question", "recap", "conclusion", "digression")
TALK_KINDS = (
    "introduction", "question", "answer", "story", "lesson", "claim", "insight", "problem", "solution", "example",
    "debate", "reveal", "conclusion", "advice", "filler", "sponsor", "tangent",
)
# parts that never make a clip on their own (and are reported as such)
LOW_VALUE = {"filler", "sponsor", "tangent", "digression"}
# parts that close a thought: a clip ending on one has its payoff
PAYOFF_KINDS = {"conclusion", "lesson", "advice", "solution", "reveal", "answer", "insight", "recap"}
# parts that open with interest: a clip starting on one has a hook
HOOK_KINDS = {"question", "claim", "problem", "story", "reveal", "insight", "debate", "introduction"}

_TALK_VALUE = {
    "lesson": 1.0, "advice": 1.0, "insight": 1.0, "solution": 0.9, "story": 0.9, "reveal": 0.9, "claim": 0.8,
    "problem": 0.8, "example": 0.8, "debate": 0.8, "answer": 0.75, "conclusion": 0.75, "question": 0.5,
    "introduction": 0.35, "filler": 0.0, "sponsor": 0.0, "tangent": 0.1,
}


def _value(**over: float) -> dict:
    return {**_TALK_VALUE, **over}


PROFILES: dict[str, dict] = {
    "education": {
        "label": "Educational / technical",
        "kinds": EDU_KINDS,
        "weights": None,  # candidates.WEIGHTS (original five-component score)
    },
    "business": {
        "label": "Business / entrepreneurship",
        "kinds": TALK_KINDS,
        "value": _value(lesson=1.0, advice=1.0, problem=0.9, solution=1.0, story=0.8, claim=0.85),
        "weights": {"hook": 20, "context": 25, "payoff": 20, "value": 15, "delivery": 10, "visual": 5, "relevance": 5},
        "brief": "a business podcast or interview: founders, investors, sales, money, strategy and their lessons",
    },
    "podcast": {
        "label": "Podcast / interview",
        "kinds": TALK_KINDS,
        "value": _value(story=1.0, reveal=1.0, debate=0.95, insight=1.0, answer=0.85),
        "weights": {"hook": 20, "context": 25, "payoff": 20, "value": 15, "delivery": 10, "visual": 5, "relevance": 5},
        "brief": "a long-form podcast or interview conversation between a host and guests",
    },
    "motivational": {
        "label": "Motivational / storytelling",
        "kinds": TALK_KINDS,
        "value": _value(story=1.0, lesson=1.0, reveal=1.0, claim=0.9, advice=0.9, problem=0.7),
        "weights": {"hook": 25, "context": 20, "payoff": 25, "value": 10, "delivery": 15, "visual": 3, "relevance": 2},
        "brief": "a motivational talk or personal story with a lesson",
    },
    "general": {
        "label": "General creator clips",
        "kinds": TALK_KINDS,
        "value": _value(),
        "weights": {"hook": 20, "context": 22, "payoff": 20, "value": 15, "delivery": 13, "visual": 5, "relevance": 5},
        "brief": "a creator video, livestream or talk",
    },
}

# requested duration presets → (min, max, ideal) seconds; "auto" = shortest length that keeps the thought whole
DURATIONS: dict[str, tuple[float, float, float]] = {
    "15-30": (15.0, 30.0, 24.0),
    "30-45": (30.0, 45.0, 38.0),
    "45-60": (45.0, 60.0, 52.0),
    "30-60": (30.0, 60.0, 45.0),  # the original Mode A range
    "60-90": (60.0, 90.0, 75.0),
    "90-180": (90.0, 180.0, 120.0),  # YouTube Shorts allow up to 3 min; many clipping campaigns do not
    "auto": (20.0, 90.0, 40.0),
}


def get(name: str | None) -> dict:
    return PROFILES.get(name or "education", PROFILES["education"])


def duration(name: str | None) -> tuple[float, float, float]:
    return DURATIONS.get(name or "30-60", DURATIONS["30-60"])
