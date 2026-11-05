"""Automatic caption decisions: which of the 100 presets fits a clip, and which spoken words deserve emphasis.

Emphasis is chosen from the content (numbers, money, strong claims, contrasts, acronyms/business terms), rate-limited
so the screen never flashes: at most one emphasised word per ~7 words and never two within 1.2 s.
"""

import re

EMPH = re.compile(
    r"^(\d[\d,.]*%?|₹?\$?\d.*|percent|million|billion|crore|lakh|thousand|never|always|biggest|mistake|secret|truth|"
    r"wrong|failed|failure|lost|profit|revenue|money|sales|customers|growth|lesson|problem|solution|best|worst|"
    r"but|however|instead|actually|lekin|magar|sabse|galti|kabhi|zero|double|half|first|only|why)$", re.I)
ACRONYM = re.compile(r"^[A-Z]{2,6}s?$")
MIN_GAP_WORDS, MIN_GAP_S = 7, 1.2

# profile → preset: business is clean and bold with a restrained highlight; motivation is kinetic; classes calm
AUTO = {
    "business": {"natural": "modern-grotesk", "engaging": "brand-bold", "fast": "creator-yellow"},
    "podcast": {"natural": "modern-grotesk", "engaging": "karaoke-classic", "fast": "creator-yellow"},
    "motivational": {"natural": "kinetic-drop", "engaging": "bold-impact", "fast": "bold-impact"},
    "education": {"natural": "learning-clear", "engaging": "learning-clear", "fast": "learning-underline"},
    "general": {"natural": "creator-pop", "engaging": "creator-pop", "fast": "creator-yellow"},
}


def auto_preset(profile: str | None, pace: str | None = None, brand_preset: str | None = None) -> str:
    """A brand kit's own caption look wins; otherwise the profile × pace choice."""
    if brand_preset and brand_preset not in ("highlight-word", "karaoke", "boxed"):
        return brand_preset
    return AUTO.get(profile or "general", AUTO["general"]).get(pace or "natural", "modern-grotesk")


def emphasise(words: list[dict]) -> list[dict]:
    """Caption words with `emphasis` set on the few that carry the point."""
    out, last_i, last_t = [], -99, -99.0
    for i, w in enumerate(words):
        t = w["text"].strip(".,!?;:\"'()")
        hit = bool(t) and (EMPH.match(t) or ACRONYM.match(t)) and len(t) > 1 or bool(re.search(r"\d", t))
        ok = hit and i - last_i >= MIN_GAP_WORDS and w["start"] - last_t >= MIN_GAP_S
        out.append({**w, "emphasis": bool(ok)})
        if ok:
            last_i, last_t = i, w["start"]
    return out
