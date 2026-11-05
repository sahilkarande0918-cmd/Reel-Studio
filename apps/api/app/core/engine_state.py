"""Processing on/off, set from the dashboard: a flag file in DATA_DIR read by the engine supervisor (app/serve.py).

Paused = the worker process is stopped (no GPU, renders or AI) and stays stopped across engine restarts; the API and
tunnel keep answering so the dashboard can switch processing back on. Jobs queue meanwhile; one interrupted mid-run
is requeued by the worker's stale-lock check when processing resumes.
"""

import json
import time
from pathlib import Path

import httpx

from app.core.config import get_settings


def _flag() -> Path:
    return get_settings().data_dir / "engine-paused"


def paused() -> bool:
    return _flag().exists()


def info() -> dict:
    f = _flag()
    if not f.exists():
        return {"processing": True}
    try:
        meta = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    return {"processing": False, "paused_at": meta.get("at"), "paused_by": meta.get("by")}


def set_processing(on: bool, by: str = "") -> dict:
    f = _flag()
    if on:
        f.unlink(missing_ok=True)
    else:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "by": by}), encoding="utf-8")
    return info()


def free_gpu() -> None:
    """Unload any Ollama model still holding VRAM (it would otherwise stay loaded for its keep-alive time)."""
    url = get_settings().ollama_url
    try:
        for m in httpx.get(f"{url}/api/ps", timeout=5).json().get("models", []):
            httpx.post(f"{url}/api/generate", json={"model": m["name"], "keep_alive": 0}, timeout=30)
    except (httpx.HTTPError, ValueError):
        pass
