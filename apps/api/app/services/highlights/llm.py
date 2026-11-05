"""Local LLM judgment of highlight candidates via Ollama (no paid API)."""

import json
import logging
import time

import httpx

from app.core.config import get_settings
from app.services.highlights.outline import KINDS

log = logging.getLogger(__name__)
NUM_CTX = 12288  # a 150-sentence outline chunk fits; the judge prompt is far smaller

SCHEMA = {
    "type": "object",
    "properties": {
        "standalone": {"type": "number", "description": "0-1: understandable without the rest of the class"},
        "complete_start": {"type": "boolean", "description": "starts at the beginning of a thought"},
        "complete_end": {"type": "boolean", "description": "ends after the thought is concluded"},
        "educational": {"type": "number", "description": "0-1: teaches something useful"},
        "title": {
            "type": "string",
            "description": "short reel title, max 8 words, in English, naming what is taught",
        },
        "summary": {"type": "string", "description": "one sentence summary in English"},
        "reason": {"type": "string", "description": "one sentence on why this works or not as a reel"},
    },
    "required": ["standalone", "complete_start", "complete_end", "educational", "title", "summary", "reason"],
}

PROMPT = """You review an excerpt from a recorded class (Hinglish: Hindi and English mixed, Roman script) to
decide whether it works as a standalone 30-60 second educational reel for someone who did not attend.
Judge only from the text. Do not invent content that is not in it.

Lecture outline (the parts of the class, for context):
{outline}

Said just BEFORE the excerpt: \"\"\"{before}\"\"\"

Excerpt ({duration:.0f} s):
\"\"\"{text}\"\"\"

Said just AFTER the excerpt: \"\"\"{after}\"\"\"

complete_start is false if the excerpt depends on the sentences before it to make sense.
complete_end is false if the point is still unfinished, or its answer only comes after the excerpt.
summary: only what the instructor actually says in the excerpt; no conclusions they do not state.

Return JSON only."""

UNITS_SCHEMA = {
    "type": "object",
    "properties": {
        "units": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "first": {"type": "integer"},
                    "last": {"type": "integer"},
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "title": {"type": "string"},
                    "topic": {"type": "string"},
                },
                "required": ["first", "last", "topic", "kind", "title"],
            },
        }
    },
    "required": ["units"],
}

UNITS_PROMPT = """Below are numbered sentences from a recorded class (Hinglish: Hindi and English mixed, Roman script),
each with its start time (m:ss). Split them into teaching steps: contiguous runs of sentences that each make ONE
point from its start to its end, usually 10 to 60 seconds long. A new step starts where the instructor moves to the
next point, the next stage of a calculation, or a different idea.
kind is one of: introduction, concept (an explanation), example (a worked example or story), demonstration (code
or a calculation being done), question (a question posed to the students), recap, conclusion, digression.
topic: the broader concept the step belongs to, a few English words; consecutive steps about the same concept
use exactly the same topic text, and it changes only where the class moves to a different concept.
title: what this step teaches, at most 7 words, in English, only from what is said.
Steps cover the sentences in order without gaps or overlaps; use the sentence numbers exactly as given.

Sentences:
{text}

Return JSON only."""


TALK_UNITS_PROMPT = """Below are numbered sentences from {brief}, each with its start time (m:ss){speakers}.
The speech may be English, Hindi or Hinglish. Split them into conversation parts: contiguous runs of sentences that each
make ONE point from its start to its end, usually 10 to 90 seconds long.
kind is one of: introduction (a topic or guest is introduced), question (the host asks something), answer (the reply to
the question just asked), story (a personal story or anecdote), lesson (the takeaway someone draws), claim (a strong
statement or opinion), insight (a surprising observation), problem, solution, example, debate (speakers disagree or
argue it out), reveal (an important point or result is disclosed), conclusion, advice (actionable advice), filler (chit-chat,
greetings, thanks, banter that says nothing), sponsor (an advertisement or sponsor read), tangent (an off-topic aside).
Every question the host asks is its own part of kind question; the reply starts a new part. Never put two different
questions, or a question and the previous answer, in one part.
topic: the specific subject being discussed right now, 1 to 4 English words (for example "pricing", "hiring", "cash
flow"), never the show's overall theme; the question and its answer share the same topic text.
Never invent facts or quotes. For each part give only the number of its first sentence, its kind and its topic.
Parts cover the sentences in order without gaps or overlaps; use the sentence numbers exactly as given.

Sentences:
{text}

Return JSON only."""

TALK_SCHEMA = {
    "type": "object",
    # order matters for a small model: it states the point first, then judges (reasoning before verdicts);
    # maxLength is enforced by Ollama's JSON grammar (the model ignores word limits otherwise)
    "properties": {
        "insight": {"type": "string", "maxLength": 140, "description": "the main point, only what the speaker says"},
        "title": {"type": "string", "maxLength": 60, "description": "short title, max 8 words, English, only what is said"},
        "starts_mid_thought": {"type": "boolean"},
        "ends_mid_thought": {"type": "boolean"},
        "standalone": {"type": "integer", "minimum": 1, "maximum": 5},
        "hook": {"type": "integer", "minimum": 1, "maximum": 5},
        "value": {"type": "integer", "minimum": 1, "maximum": 5},
        "limitation": {"type": "string", "maxLength": 90},
    },
    "required": ["insight", "title", "starts_mid_thought", "ends_mid_thought", "standalone", "hook", "value",
                 "limitation"],
}

TALK_PROMPT = """You are a short-form video editor reviewing an excerpt from {brief}. Decide whether it works as a
standalone {duration:.0f}-second Short for someone who never watched the full recording. Judge only from the text.

Conversation outline (for context):
{outline}

Said just BEFORE the excerpt: \"\"\"{before}\"\"\"

EXCERPT ({duration:.0f} s):
\"\"\"{text}\"\"\"

Said just AFTER the excerpt: \"\"\"{after}\"\"\"

Answer:
- insight: the main point the speaker makes in the excerpt (their words, no new facts).
- title: a short title for the Short, only from what is said.
- starts_mid_thought: true ONLY if the excerpt's first sentence continues something said before it (for example it
  answers a question that is not in the excerpt, or says "this/he/that" about something not named). An excerpt that
  opens with a question and then answers it does NOT start mid-thought.
- ends_mid_thought: true ONLY if the speaker is cut off before finishing the answer, story or lesson.
- standalone (1-5): 5 = fully understandable alone, 1 = meaningless without the rest.
- hook (1-5): 5 = the first sentence makes a viewer want to keep watching.
- value (1-5): 5 = a genuine insight, lesson or story; 1 = greetings, thanks, a sponsor read or small talk.
- limitation: concrete missing context a viewer would need, or "" if none.

Return JSON only."""


def _chat(prompt: str, schema: dict, model: str | None, keep_alive: str, max_tokens: int | None = None) -> dict:
    """One context size for every call: a different num_ctx forces a model reload, and a reload right
    after an unload could fail with a 500 on this 8 GB GPU. A server error is retried once."""
    s = get_settings()
    opts = {"temperature": 0, "seed": 7, "num_ctx": NUM_CTX}
    if max_tokens:
        opts["num_predict"] = max_tokens  # short judgments: the answer is a few fields, not an essay
    for attempt in range(2):
        r = httpx.post(
            f"{s.ollama_url}/api/chat",
            json={
                "model": model or s.ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "format": schema,
                "stream": False,
                "keep_alive": keep_alive,
                "options": opts,
            },
            timeout=600,
        )
        if r.status_code < 500 or attempt:
            break
        log.warning("Ollama returned %s; retrying once", r.status_code)
        time.sleep(5)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def units(lines: list[str], model: str | None = None, profile: dict | None = None,
          speakers: bool = False) -> list[dict] | None:
    """Teaching units (class) or conversation parts (talk profiles) for numbered sentence lines (`outline.outline`)."""
    try:
        if profile and profile.get("brief"):
            # parts are contiguous, so only each part's first sentence is asked for (its end is the next start), and
            # its topic doubles as its title: about half the output tokens of the class outline (speed)
            item = {"type": "object", "properties": {
                "first": {"type": "integer"}, "kind": {"type": "string", "enum": list(profile["kinds"])},
                "topic": {"type": "string", "maxLength": 40}}, "required": ["first", "kind", "topic"]}
            schema = {"type": "object", "properties": {"units": {"type": "array", "items": item}}, "required": ["units"]}
            prompt = TALK_UNITS_PROMPT.format(brief=profile["brief"], text="\n".join(lines),
                                              speakers=" and speaker label" if speakers else "")
            # bounded answer (a few tokens per part): a runaway generation once ran into the 10-minute timeout
            raw = sorted(_chat(prompt, schema, model, "10m", max_tokens=1800)["units"], key=lambda u: int(u["first"]))
            last_line = int(lines[-1][1 : lines[-1].index("]")])
            return [{**u, "last": (int(raw[i + 1]["first"]) - 1 if i + 1 < len(raw) else last_line),
                     "title": u["topic"]} for i, u in enumerate(raw)]
        return _chat(UNITS_PROMPT.format(text="\n".join(lines)), UNITS_SCHEMA, model, "10m")["units"]
    except (httpx.HTTPError, KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        log.warning("LLM outline unavailable: %s", e)
        return None


def judge(
    text: str,
    duration_s: float,
    before: str = "",
    after: str = "",
    outline: str = "",
    model: str | None = None,
    keep_alive: str = "5m",
) -> dict | None:
    prompt = PROMPT.format(
        text=text,
        duration=duration_s,
        before=before or "(start of class)",
        after=after or "(end of class)",
        outline=outline or "(not available)",
    )
    try:
        data = _chat(prompt, SCHEMA, model, keep_alive)
        for k in ("standalone", "educational"):
            data[k] = max(0.0, min(1.0, float(data.get(k, 0))))
        return data
    except (httpx.HTTPError, KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        log.warning("LLM judge unavailable: %s", e)
        return None


def judge_talk(text: str, duration_s: float, brief: str, before: str = "", after: str = "", outline: str = "",
               model: str | None = None) -> dict | None:
    """Standalone/hook/payoff judgment of a conversation clip (talk profiles)."""
    prompt = TALK_PROMPT.format(text=text, duration=duration_s, brief=brief, before=before or "(start of recording)",
                                after=after or "(end of recording)", outline=outline or "(not available)")
    """Returns None only when the LLM is unreachable; an unusable answer is retried once, then {"invalid": True}
    (the caller rejects the clip rather than accepting it unchecked)."""
    for attempt in range(2):
        try:
            d = _chat(prompt, TALK_SCHEMA, model, "5m", max_tokens=400)
            scale = {k: max(0.0, min(1.0, (int(d[k]) - 1) / 4)) for k in ("standalone", "hook", "value")}
            return {**d, **scale, "complete_start": not d["starts_mid_thought"],
                    "complete_end": not d["ends_mid_thought"]}
        except httpx.HTTPError as e:
            log.warning("LLM judge unavailable: %s", e)
            return None
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            log.warning("LLM judge answer unusable (attempt %d): %s", attempt + 1, e)
    return {"invalid": True}


EMBED_MODEL = "nomic-embed-text"


def embed(texts: list[str]) -> list[list[float]] | None:
    """Sentence embeddings from Ollama (nomic-embed-text, Apache-2.0, ~0.3 GB, runs beside the 7B model); None when
    the model is not installed, so callers fall back to TF-IDF."""
    if not texts:
        return []
    try:
        r = httpx.post(f"{get_settings().ollama_url}/api/embed",
                       json={"model": EMBED_MODEL, "input": [t[:2000] for t in texts], "keep_alive": "2m"}, timeout=300)
        r.raise_for_status()
        out = r.json().get("embeddings")
        return out if out and len(out) == len(texts) else None
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("embeddings unavailable: %s", e)
        return None


def unload(model: str | None = None) -> None:
    """Free VRAM before the next GPU stage."""
    s = get_settings()
    try:
        httpx.post(
            f"{s.ollama_url}/api/generate",
            json={"model": model or s.ollama_model, "keep_alive": 0},
            timeout=30,
        )
    except httpx.HTTPError:
        pass
