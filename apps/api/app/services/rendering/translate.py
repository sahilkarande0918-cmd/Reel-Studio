"""Caption translation with the local LLM (Ollama, free): each spoken sentence is translated as a whole, keeps its
own time span, and its translated words are spread over that span by length. Meaning-preserving, no added content.
"""

import json
import logging

from app.services.highlights import llm

log = logging.getLogger(__name__)
LANGUAGES = {
    "en": "English", "hi": "Hindi in Devanagari script", "hinglish": "Hinglish (Hindi in Roman script mixed with English)",
    "mr": "Marathi in Devanagari script", "bn": "Bengali", "ta": "Tamil", "te": "Telugu", "gu": "Gujarati",
    "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese", "it": "Italian", "id": "Indonesian",
    "ar": "Arabic", "ja": "Japanese", "ko": "Korean", "zh": "Simplified Chinese", "ru": "Russian", "tr": "Turkish",
}
PROMPT = """Translate each numbered subtitle line into {lang}. Keep the meaning, tone and numbers exactly; do not add,
explain or merge lines; keep names and brand names as they are. Return one translation per line, same order.

{lines}

Return JSON only."""


def sentences(words: list[dict]) -> list[list[dict]]:
    """Caption words grouped into sentences (terminal punctuation or a pause over 0.6 s), at most 18 words each."""
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > 0.6 or cur[-1]["text"][-1:] in ".?!।" or len(cur) >= 18):
            out.append(cur)
            cur = []
        cur.append(w)
    return [*out, cur] if cur else out


def translate(words: list[dict], lang: str) -> list[dict]:
    """Translated caption words (same clip clock). Unchanged words when the LLM is unavailable."""
    if lang not in LANGUAGES or not words:
        return words
    groups = sentences(words)
    lines = [" ".join(w["text"] for w in g) for g in groups]
    schema = {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "string", "maxLength": 400},
                                                         "minItems": len(lines), "maxItems": len(lines)}},
              "required": ["lines"]}
    prompt = PROMPT.format(lang=LANGUAGES[lang], lines="\n".join(f"{i + 1}. {t}" for i, t in enumerate(lines)))
    try:
        got = llm._chat(prompt, schema, None, "5m", max_tokens=min(4000, 60 * len(lines) + 200))["lines"]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError, Exception) as e:  # noqa: BLE001 — keep the original
        log.warning("caption translation unavailable: %s", e)
        return words
    out = []
    for g, text in zip(groups, got, strict=False):
        toks = (text or "").split() or [w["text"] for w in g]
        a, b = g[0]["start"], g[-1]["end"]
        total = sum(len(t) + 1 for t in toks)
        t = a
        for tok in toks:
            d = (b - a) * (len(tok) + 1) / total
            out.append({"text": tok, "start": round(t, 3), "end": round(min(t + d * 0.95, b), 3), "isCode": False,
                        "emphasis": False})
            t += d
    return out
