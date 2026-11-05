"""AI emojis: a sticker above the captions where a spoken word clearly calls for one (money → 💰, growth → 📈 …).

Chosen from the words themselves (English, Hindi/Hinglish romanised), at most one every 4 s and never in the first
2.5 s (the hook headline's place). Images: Google Noto Emoji 128 px PNGs (Apache-2.0), downloaded once per emoji into
the data cache, overlaid by the fast renderer (libass cannot draw colour emoji).
"""

import re
import urllib.request
from pathlib import Path

from app.core.config import get_settings

SOURCE = "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/3D/png/128/emoji_u{code}.png"  # glossy 3D set
# keyword (whole word, lower case) → Noto codepoint name
MAP = {
    **dict.fromkeys("money cash dollars dollar rupees rupee paisa paise crore lakh revenue profit salary income".split(), "1f4b0"),
    **dict.fromkeys("growth grow grew growing scale scaled doubled".split(), "1f4c8"),
    **dict.fromkeys("lost loss losses failed failure fail crash declined".split(), "1f4c9"),
    **dict.fromkeys("idea ideas insight lesson learned learn realise realize".split(), "1f4a1"),
    **dict.fromkeys("mistake mistakes wrong problem problems danger warning careful".split(), "26a0"),
    **dict.fromkeys("fire crazy insane amazing incredible huge massive".split(), "1f525"),
    **dict.fromkeys("launch launched rocket fast faster speed".split(), "1f680"),
    **dict.fromkeys("deadline hours".split(), "23f0"),
    **dict.fromkeys("customer customers client clients users audience".split(), "1f465"),
    **dict.fromkeys("love loved heart passion".split(), "2764"),
    **dict.fromkeys("think thinking".split(), "1f914"),
    **dict.fromkeys("goal goals target win winning won success successful".split(), "1f3af"),
    **dict.fromkeys("data metric metrics numbers analytics retention".split(), "1f4ca"),
    **dict.fromkeys("phone app mobile".split(), "1f4f1"),
    **dict.fromkeys("team hire hiring job".split(), "1f4bc"),
    **dict.fromkeys("secret hidden truth".split(), "1f92b"),
    **dict.fromkeys("funny laugh joke haha".split(), "1f602"),
    **dict.fromkeys("strong power powerful".split(), "1f4aa"),
    **dict.fromkeys("paisa paise kamai munafa".split(), "1f4b0"),
    **dict.fromkeys("galti galtiyan".split(), "26a0"),
}
WORD = re.compile(r"[a-z]+")
MIN_GAP_S, SHOW_S, AVOID_START_S = 4.0, 1.4, 2.5


def choose(words: list[dict], duration: float) -> list[dict]:
    """[{code, at, duration}] on the clip clock from caption words ({text, start, end})."""
    out, last = [], -99.0
    for w in words:
        toks = WORD.findall(w["text"].lower())
        code = next((MAP[t] for t in toks if t in MAP), None)
        if code and w["start"] >= AVOID_START_S and w["start"] - last >= MIN_GAP_S and w["start"] + 0.4 < duration:
            out.append({"code": code, "at": round(w["start"], 3), "duration": round(min(SHOW_S, duration - w["start"]), 3)})
            last = w["start"]
    return out


def png(code: str) -> Path | None:
    """Local path of the emoji image (downloaded once); None when it cannot be fetched (the sticker is skipped)."""
    d = get_settings().data_dir / "cache" / "emoji"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"emoji_u{code}.png"
    if not p.exists():
        try:
            with urllib.request.urlopen(SOURCE.format(code=code), timeout=20) as r:  # noqa: S310 — fixed https host
                data = r.read()
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                p.write_bytes(data)
        except OSError:
            return None
    return p if p.exists() else None
