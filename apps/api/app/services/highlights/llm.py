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


def _chat(prompt: str, schema: dict, model: str | None, keep_alive: str) -> dict:
    """One context size for every call: a different num_ctx forces a model reload, and a reload right
    after an unload could fail with a 500 on this 8 GB GPU. A server error is retried once."""
    s = get_settings()
    for attempt in range(2):
        r = httpx.post(
            f"{s.ollama_url}/api/chat",
            json={
                "model": model or s.ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "format": schema,
                "stream": False,
                "keep_alive": keep_alive,
                "options": {"temperature": 0, "seed": 7, "num_ctx": NUM_CTX},
            },
            timeout=600,
        )
        if r.status_code < 500 or attempt:
            break
        log.warning("Ollama returned %s; retrying once", r.status_code)
        time.sleep(5)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def units(lines: list[str], model: str | None = None) -> list[dict] | None:
    """Teaching units for numbered sentence lines (see `outline.outline`)."""
    try:
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
