"""Auto B-roll: short cutaways over the speaker where a picture helps (OpusClip-style), grounded in what is said.

1. The local LLM reads the clip's sentences and picks at most two moments where a visual helps understanding, with a
   2-4 word English search phrase for a real-world scene (never people's identities, logos or brands).
2. Media, free sources only, credited, in this order:
   - Pexels stock video, when the owner sets a free PEXELS_API_KEY (no payment; https://www.pexels.com/api/)
   - Openverse photos under commercial-use licences (no key) whose own title/tags contain every query word, shown
     with a slow push-in (Ken Burns); no loose matches: a wrong picture is worse than none
   - mode "ai": the found image animated by the local LTX-Video model (free, ≈2 min per cutaway, labelled AI)
3. The renderer overlays each cutaway full-frame for ≈2.4 s; the speaker's audio and the captions continue.
Found pictures illustrate the topic; they are never presented as the speaker's own footage.
"""

import hashlib
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger(__name__)
CUT_S = 2.4
UA = {"User-Agent": "ReelStudio/2.0 (local video editor; b-roll search)"}
PROMPT = """You edit a short vertical video. Below are its subtitle sentences with start times (seconds).
Pick at most {n} sentences where a short cutaway picture would help a viewer understand what is said. Skip greetings,
opinions with nothing to show, and the first sentence. For each, give a 2-4 word English search phrase for a concrete
thing a camera could film, e.g. "laptop analytics dashboard", "store checkout counter", "office team meeting",
"stack of cash". Never abstract words alone (process, strategy, demo, idea), never real people, logos or brands.

{lines}

Return JSON only."""
SCHEMA = {"type": "object", "properties": {"picks": {"type": "array", "maxItems": 3, "items": {
    "type": "object", "properties": {"sentence": {"type": "integer"}, "query": {"type": "string", "maxLength": 40}},
    "required": ["sentence", "query"]}}}, "required": ["picks"]}


def _get(url: str, headers: dict | None = None, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — fixed https hosts below
        return r.read()


def moments(words: list[dict], duration: float, n: int = 2, avoid: list[tuple[float, float]] | None = None) -> list[dict]:
    """[{at, duration, query}] on the clip clock, chosen by the local LLM from the caption sentences."""
    from app.services.highlights import llm
    from app.services.rendering.translate import sentences

    groups = sentences(words)
    if len(groups) < 3:
        return []
    lines = "\n".join(f"{i}. ({g[0]['start']:.1f}s) {' '.join(w['text'] for w in g)}" for i, g in enumerate(groups))
    try:
        picks = llm._chat(PROMPT.format(n=n, lines=lines), SCHEMA, None, "5m", max_tokens=200)["picks"]
    except Exception as e:  # noqa: BLE001 — no B-roll rather than a failed render
        log.warning("b-roll planning unavailable: %s", e)
        return []
    out = []
    for p in picks:
        i = int(p.get("sentence", -1))
        q = re.sub(r"[^\w\s-]", "", str(p.get("query", ""))).strip()[:40]
        if not 0 < i < len(groups) or not q:
            continue
        at = groups[i][0]["start"] + 0.3
        if at + CUT_S > duration - 0.5 or any(a - 0.5 < at < b + 0.5 for a, b in (avoid or [])):
            continue
        if any(abs(at - o["at"]) < CUT_S + 2 for o in out):
            continue
        out.append({"at": round(at, 3), "duration": CUT_S, "query": q})
    return out[:n]


def _pexels(query: str, portrait: bool, dest: Path) -> dict | None:
    key = os.environ.get("PEXELS_API_KEY") or getattr(get_settings(), "pexels_api_key", "")
    if not key:
        return None
    q = urllib.parse.urlencode({"query": query, "per_page": 8, "orientation": "portrait" if portrait else "landscape"})
    try:
        data = json.loads(_get(f"https://api.pexels.com/videos/search?{q}", {"Authorization": key}))
        for v in data.get("videos", []):
            if v.get("duration", 0) < 3:
                continue
            files = sorted((f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and (f.get("height") or 0) <= 1920),
                           key=lambda f: -(f.get("height") or 0))
            if files:
                dest.write_bytes(_get(files[0]["link"], timeout=60))
                return {"kind": "video", "credit": f"Video by {v.get('user', {}).get('name', 'Pexels')} on Pexels",
                        "source": v.get("url"), "license": "Pexels License"}
    except Exception as e:  # noqa: BLE001
        log.warning("pexels search failed: %s", e)
    return None


def _openverse(query: str, dest: Path) -> dict | None:
    q = urllib.parse.urlencode({"q": query, "license_type": "commercial", "page_size": 20, "mature": "false",
                                "category": "photograph"})
    want = {w for w in re.findall(r"[a-z]{3,}", query.lower())}
    try:
        data = json.loads(_get(f"https://api.openverse.org/v1/images/?{q}"))
        def match(r: dict) -> float:  # share of the query's words in the picture's own title and tags
            have = set(re.findall(r"[a-z]{3,}", ((r.get("title") or "") + " " + " ".join(
                t.get("name", "") for t in r.get("tags") or [])).lower()))
            return len(want & have) / max(len(want), 1)

        for r in sorted(data.get("results", []), key=lambda r: (-match(r), -((r.get("width") or 0) * (r.get("height") or 0)))):
            if (r.get("width") or 0) < 1000 or not r.get("url") or match(r) < 1.0:  # every query word, in its own tags
                continue
            try:
                blob = _get(r["url"], timeout=30)
            except Exception:  # noqa: BLE001 — try the next result
                continue
            if blob[:3] == b"\xff\xd8\xff" or blob[:8] == b"\x89PNG\r\n\x1a\n":
                dest.write_bytes(blob)
                lic = f"{(r.get('license') or '').upper()} {r.get('license_version') or ''}".strip()
                return {"kind": "image", "credit": f"“{(r.get('title') or 'Image')[:60]}” by {r.get('creator') or 'unknown'} ({lic})",
                        "source": r.get("foreign_landing_url") or r.get("url"), "license": lic}
    except Exception as e:  # noqa: BLE001
        log.warning("openverse search failed: %s", e)
    return None


def fetch(plan: list[dict], project: Path, portrait: bool, mode: str = "stock") -> list[dict]:
    """Download media for planned moments into the render project. [{src, at, duration, kind, credit, ai, ...}]"""
    cache = get_settings().data_dir / "cache" / "broll"
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for n, m in enumerate(plan):
        key = hashlib.sha1(f"{m['query']}|{portrait}".encode()).hexdigest()[:12]
        meta = None
        vid, img = cache / f"{key}.mp4", cache / f"{key}.jpg"
        info = cache / f"{key}.json"
        if info.exists():
            meta = json.loads(info.read_text(encoding="utf-8"))
        else:
            # no single-word fallbacks: "demo" alone found a political protest photo. No match → no cutaway.
            meta = _pexels(m["query"], portrait, vid) or _openverse(m["query"], img)
            if meta:
                info.write_text(json.dumps(meta), encoding="utf-8")
        if not meta:
            continue
        file = vid if meta["kind"] == "video" else img
        ai = False
        if mode == "ai" and meta["kind"] == "image":
            try:
                from app.services import i2v

                prompt = (f"{m['query']}. A realistic, natural scene. Gentle, cinematic camera push-in, subtle real "
                          "motion, natural light, no text, no logos.")
                file = i2v.animate([(img, prompt)], cache / "ai", portrait=portrait)[0]
                meta = {**meta, "kind": "video", "credit": meta["credit"] + " · animated with AI (LTX-Video)"}
                ai = True
            except Exception as e:  # noqa: BLE001 — keep the still with a push-in
                log.warning("AI b-roll animation failed, using the still: %s", e)
        name = f"broll{n}{Path(file).suffix}"
        (project / name).write_bytes(Path(file).read_bytes())
        out.append({"src": name, "at": m["at"], "duration": m["duration"], "kind": meta["kind"], "query": m["query"],
                    "credit": meta["credit"][:200], "source": meta.get("source"), "ai": ai})
    return out
