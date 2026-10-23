"""Structured-output LLM calls for Mode B (director, clip tagging). Local Ollama by default; an optional
OpenAI-compatible endpoint (DIRECTOR_API_URL/KEY/MODEL) is used for text planning when configured. Never per frame."""

import base64
import json
import logging
import time

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)
NUM_CTX = 12288  # same context as the highlight stages: a different num_ctx forces a model reload


class LLMUnavailable(RuntimeError):
    pass


def _ollama(messages: list[dict], schema: dict, keep_alive: str, temperature: float, seed: int = 7) -> dict:
    s = get_settings()
    for attempt in range(2):
        try:
            r = httpx.post(
                f"{s.ollama_url}/api/chat",
                json={
                    "model": s.ollama_model,
                    "messages": messages,
                    "format": schema,
                    "stream": False,
                    "keep_alive": keep_alive,
                    "options": {"temperature": temperature, "seed": seed, "num_ctx": NUM_CTX},
                },
                timeout=600,
            )
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"Ollama unreachable: {e}") from e
        if r.status_code < 500 or attempt:
            break
        time.sleep(5)
    if r.status_code >= 400:
        raise LLMUnavailable(f"Ollama returned {r.status_code}")
    return json.loads(r.json()["message"]["content"])


def _external(prompt: str, schema: dict, temperature: float) -> dict:
    s = get_settings()
    r = httpx.post(
        s.director_api_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {s.director_api_key.get_secret_value()}"},
        json={
            "model": s.director_model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Reply with one JSON object matching this JSON schema:\n" + json.dumps(schema)},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def chat_json(prompt: str, schema: dict, temperature: float = 0.2, keep_alive: str = "5m", seed: int = 7) -> tuple[dict, str]:
    """(parsed JSON, engine name). Raises LLMUnavailable when no model answered with JSON."""
    s = get_settings()
    if s.director_api_url and s.director_api_key.get_secret_value() and s.director_model:
        try:
            return _external(prompt, schema, temperature), f"external:{s.director_model}"
        except (httpx.HTTPError, KeyError, ValueError) as e:
            log.warning("external director failed, using local model: %s", e)
    try:
        return _ollama([{"role": "user", "content": prompt}], schema, keep_alive, temperature, seed), f"ollama:{s.ollama_model}"
    except (KeyError, ValueError) as e:
        raise LLMUnavailable(f"model did not return JSON: {e}") from e


def look(jpg: bytes, prompt: str, schema: dict) -> dict | None:
    """Local vision model on one still (labelled as model text by callers). None when unavailable."""
    try:
        return _ollama(
            [{"role": "user", "content": prompt, "images": [base64.b64encode(jpg).decode()]}], schema, "5m", 0
        )
    except (LLMUnavailable, KeyError, ValueError) as e:
        log.warning("vision model unavailable: %s", e)
        return None


def unload() -> None:
    s = get_settings()
    try:
        httpx.post(f"{s.ollama_url}/api/generate", json={"model": s.ollama_model, "keep_alive": 0}, timeout=30)
    except httpx.HTTPError:
        pass
