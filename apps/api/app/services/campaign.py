"""AI campaign agent for local businesses: business facts → campaign concept, strategy, Reel ideas with hooks, scripts,
captions, CTAs, a series and a posting schedule, in English, Hindi or Hinglish.

Grounding rules enforced after generation (not just asked of the model):
- the business name is restored to its exact spelling wherever the model wrote a variant (brand vocabulary);
- prices, discounts and numbers that are not in the user's own offer text are removed from customer-facing copy;
- no testimonials, ratings or results are allowed (sentences claiming them are dropped).
A deterministic planner writes a smaller plan when no language model answers (recorded in provenance).
"""

import re
import secrets
from datetime import date, timedelta
from typing import Literal
from urllib.parse import quote, urlencode

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.services import llm
from app.services.editing.pacing import PROFILES

Goal = Literal["awareness", "leads", "footfall", "sales", "followers"]
LANG_NAME = {"en": "English", "hi": "Hindi in Devanagari script", "hinglish": "Hinglish (Hindi in Roman script mixed with English)"}


class Business(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    industry: str = Field(min_length=2, max_length=80)
    audience: str = Field(min_length=2, max_length=200)
    goal: Goal = "leads"
    offer: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=60)
    whatsapp: str = Field(default="", pattern=r"^(\+?\d{10,15})?$")
    website: str = Field(default="", pattern=r"^(https://[^\s]{4,200})?$")
    footage: str = Field(default="", max_length=300, description="what footage/photos the business already has")
    brand_terms: list[str] = Field(default_factory=list, max_length=20)


class Reel(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9-]{1,20}$")
    title: str = Field(max_length=80)
    hook: str = Field(max_length=120)
    script: str = Field(max_length=900)
    caption: str = Field(max_length=900)
    hashtags: list[str] = Field(default_factory=list, max_length=12)
    cta: str = Field(max_length=120)
    mode: Literal["edit", "recording"] = "edit"
    style: str = "clean_commercial"
    duration_s: int = Field(default=20, ge=8, le=60)
    shots: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("style")
    @classmethod
    def _style(cls, v: str) -> str:
        return v if v in PROFILES else "clean_commercial"


class Plan(BaseModel):
    concept: str = Field(max_length=300)
    strategy: str = Field(max_length=900)
    pillars: list[str] = Field(max_length=5)
    reels: list[Reel] = Field(min_length=3, max_length=8)
    series: list[dict] = Field(default_factory=list, max_length=4)
    schedule: list[dict] = Field(default_factory=list, max_length=30)


def _restore_name(text: str, names: list[str]) -> str:
    for n in names:
        if n:
            text = re.sub(re.escape(n).replace(r"\ ", r"\s*"), n, text, flags=re.IGNORECASE)
    return text


NUM = re.compile(r"(₹|rs\.?|inr|\$)\s?\d[\d,]*|\d+\s?%|\d+\s?(?:% )?off\b|\bflat\s+\d+", re.IGNORECASE)
CLAIM = re.compile(r"\b(rated|reviews?|testimonial|5[- ]star|best in|no\.? ?1|#1|award|guaranteed|customers? love)\b", re.IGNORECASE)


def ground(text: str, b: Business) -> tuple[str, list[str]]:
    """Drop sentences with numbers/prices not in the owner's offer, or with invented social proof."""
    allowed = {m.group(0).lower().replace(" ", "") for m in NUM.finditer(b.offer)}
    notes, keep = [], []
    for s in re.split(r"(?<=[.!?।])\s+", text):
        bad = [m.group(0) for m in NUM.finditer(s) if m.group(0).lower().replace(" ", "") not in allowed]
        if bad:
            notes.append(f"removed unverified number {bad[0]!r}")
        elif CLAIM.search(s):
            notes.append(f"removed unverified claim {CLAIM.search(s).group(0)!r}")
        else:
            keep.append(s)
    return " ".join(keep).strip(), notes


def rules_plan(b: Business, language: str) -> dict:
    """Deterministic fallback (English): one reel per proven local-business format."""
    offer = f" {b.offer}." if b.offer else ""
    where = f" in {b.city}" if b.city else ""
    ideas = [
        ("r1", "Meet us", f"This is {b.name}{where}.", "product_showcase", f"Who we are and what we do for {b.audience}.{offer}"),
        ("r2", "Behind the scenes", "Here's how we actually do it.", "cinematic", "A calm look at the work, the place and the people."),
        ("r3", "Most asked question", "You asked, we answer.", "educational", f"One common question from {b.audience}, answered simply."),
        ("r4", "The offer", f"Something for {b.audience}.", "energetic", f"What {b.name} offers.{offer}"),
    ]
    reels = [{"key": k, "title": t, "hook": hook, "script": script, "caption": f"{hook} {script} Message us on WhatsApp.",
              "hashtags": [re.sub(r"\W", "", b.industry.title()), re.sub(r"\W", "", b.city.title()) or "Local"], "cta": "Message us on WhatsApp",
              "mode": "edit", "style": style, "duration_s": 20, "shots": ["exterior or sign", "the product/service in use", "the team at work"]}
             for k, t, hook, style, script in ideas]
    return {"concept": f"Show {b.audience} what {b.name} does, up close and honestly.",
            "strategy": f"Four short reels over two weeks for {b.goal}: introduce, show the work, answer a question, present the offer.",
            "pillars": ["Introduce", "Show the work", "Answer questions"], "reels": reels,
            "series": [{"name": "Getting to know us", "reel_keys": ["r1", "r2"]}],
            "schedule": [{"day": d, "reel_key": k, "time": "19:00"} for d, k in ((1, "r1"), (3, "r2"), (6, "r3"), (9, "r4"))]}


def _key(v) -> str:
    return (re.sub(r"[^a-z0-9-]+", "-", str(v).lower()).strip("-") or "r")[:20]


def normalise(raw: dict) -> dict:
    """Models write ids like "Reel_1" and refer to them in the schedule/series: make them valid ids consistently."""
    limits = {"title": 80, "hook": 120, "script": 900, "caption": 900, "cta": 120}
    for r in raw.get("reels") or []:
        if isinstance(r, dict):
            r["key"] = _key(r.get("key", ""))
            for k, n in limits.items():  # models overshoot lengths: keep whole words instead of failing the plan
                if k in r:
                    r[k] = _clip(r[k], n)
            r["duration_s"] = min(60, max(8, int(float(r.get("duration_s") or 20))))
    for s in raw.get("schedule") or []:
        if isinstance(s, dict):
            s["reel_key"] = _key(s.get("reel_key", ""))
    for s in raw.get("series") or []:
        if isinstance(s, dict):
            s["reel_keys"] = [_key(k) for k in s.get("reel_keys") or []]
    return raw


HINGLISH = re.compile(r"\b(hai|hain|aur|ke|ki|ka|ko|yeh|ye|mein|se|ab|karo|lo|apna|apne|aaj|kya|bhi|nahi|wala|wale|sabse|chalo|dekho|abhi)\b", re.I)
DEVANAGARI = re.compile("[\u0900-\u097F]")


FORMATS = {
    "meet": ("Meet us", "introduce the business: who you are, where, what you offer and to whom"),
    "product": ("Product close-up", "one product or service up close: what it is, what makes it good, who it is for"),
    "faq": ("Question answered", "answer one real question the audience asks before buying or visiting"),
    "offer": ("The offer", "present the owner's current offer exactly as written (or the main reason to come now if there is none)"),
    "behind": ("Behind the scenes", "how the work is actually done: the place, the people, the care"),
    "tour": ("Visit us", "a short tour: how to find the place and what you see when you arrive"),
    "try_on": ("Try it", "a customer-style try-on or before/after of using the product or service"),
    "story": ("Our story", "why the business exists and what it cares about"),
    "trend": ("Trend moment", "a light, fun reel using a format people already enjoy, tied to the business"),
}
BY_GOAL = {
    "leads": ["meet", "product", "faq", "offer", "behind"],
    "footfall": ["meet", "tour", "product", "offer", "behind"],
    "sales": ["product", "offer", "try_on", "faq", "meet"],
    "awareness": ["meet", "behind", "product", "story", "faq"],
    "followers": ["behind", "trend", "product", "faq", "story"],
}
STRATEGY_SCHEMA = {
    "type": "object",
    "properties": {
        "concept": {"type": "string", "description": "one full sentence: the campaign idea"},
        "strategy": {"type": "string", "description": "2-3 sentences: how the reels work together toward the goal"},
        "pillars": {"type": "array", "items": {"type": "string", "description": "a theme of 2-5 words"}, "minItems": 3, "maxItems": 3},
    },
    "required": ["concept", "strategy", "pillars"],
}
REEL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "short title, max 6 words"},
        "hook": {"type": "string", "description": "the first 2 seconds, one short line"},
        "script": {"type": "string", "description": "voiceover/on-screen lines for a 15-30 s reel, 2-4 short sentences"},
        "caption": {"type": "string", "description": "Instagram caption, 1-3 sentences"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "cta": {"type": "string", "description": "one call to action"},
        "shots": {"type": "array", "items": {"type": "string"}, "description": "3-5 shots to film", "maxItems": 5},
        "style": {"type": "string", "enum": list(PROFILES)},
    },
    "required": ["title", "hook", "script", "caption", "hashtags", "cta", "shots", "style"],
}
FACTS = """Business (facts from the owner; use only these):
- Name: {name} (spell exactly like this)
- Industry: {industry}
- City/area: {city}
- Audience: {audience}
- Goal: {goal}
- Offer: {offer}
- Footage/photos they already have: {footage}
Rules: no invented prices, discounts, numbers, awards, reviews, testimonials or results. Mention the offer only as written.
Write customer-facing text in {language}. Hashtags may be English. Return JSON only."""


def _facts(b: Business, language: str) -> str:
    return FACTS.format(name=b.name, industry=b.industry, city=b.city or "not given", audience=b.audience, goal=b.goal,
                        offer=b.offer or "none (do not make one up)", footage=b.footage or "not described", language=LANG_NAME[language])


HINGLISH_EXAMPLE = (" Example of the style: 'Diwali ke liye naye sneakers chahiye? Kicks Corner pe aao, budget mein best "
                    "styles milenge!'")


def _clip(text: str, n: int) -> str:
    text = str(text).strip()
    return text if len(text) <= n else text[: text.rfind(" ", 0, n - 1)].rstrip(",;:- ") + "…"


def _ask(prompt: str, schema: dict, check, tries: int = 3, seed: int = 7) -> tuple[dict, list[str]]:
    """One focused model call with validation feedback; raises LLMUnavailable when no model answers."""
    errors: list[str] = []
    raw: dict = {}
    for attempt in range(tries):
        raw, _ = llm.chat_json(prompt + (f"\nYour previous answer had problems: {errors[-1]}. Fix them." if errors else ""),
                               schema, temperature=0.4 + 0.15 * attempt, seed=seed * 31 + attempt)
        issues = check(raw)
        if not issues:
            return raw, errors
        errors.append("; ".join(issues))
    return raw, errors + ["accepted with issues"]


def _lang_issue(text: str, language: str) -> list[str]:
    if language == "hinglish" and len(HINGLISH.findall(text)) < 2:
        return ["write in Hinglish: Hindi words in Roman script mixed with English (e.g. 'Diwali ke liye naye sneakers dekho')"]
    if language == "hi" and len(DEVANAGARI.findall(text)) < 15:
        return ["write in Hindi using Devanagari script"]
    return []


def plan(b: Business, language: str) -> tuple[dict, dict]:
    """(validated plan, provenance). One call for the strategy, then one call per reel format (distinct by design)."""
    facts = _facts(b, language)
    notes: list[str] = []
    try:
        def check_strategy(r: dict) -> list[str]:
            out = []
            if len(str(r.get("concept", ""))) < 25 or str(r.get("concept", "")).strip().lower() == b.name.lower():
                out.append("concept must be one full sentence describing the campaign idea")
            if any(":" in str(p) or len(str(p).split()) > 6 for p in r.get("pillars") or []):
                out.append("pillars are 3 short themes of 2-5 words, no labels")
            return out

        strat, errs = _ask(f"You are a social media strategist for small local businesses in India. Plan a two-week Instagram Reels "
                           f"campaign.\n\n{facts}", STRATEGY_SCHEMA, check_strategy)
        notes += errs
        reels, used = [], []
        for n, fmt in enumerate(BY_GOAL[b.goal], start=1):
            title, what = FORMATS[fmt]

            def check_reel(r: dict, used=used) -> list[str]:
                out = _lang_issue(f"{r.get('hook', '')} {r.get('script', '')} {r.get('caption', '')}", language)
                if str(r.get("hook", "")).strip().lower() in used:
                    out.append("this hook was already used by another reel; write a different one")
                return out

            prompt = (f"LANGUAGE: {LANG_NAME[language]}.{HINGLISH_EXAMPLE if language == 'hinglish' else ''}\n"
                      f"Write ONE Instagram Reel for this campaign. The hook is at most 12 words.\nCampaign idea: {strat.get('concept', '')}\n"
                      f"This reel's format: {title} — {what}.\n"
                      f"Hooks already used by other reels (do not repeat): {', '.join(used) or 'none'}\n\n{facts}")
            r, errs = _ask(prompt, REEL_SCHEMA, check_reel, seed=n)
            notes += [f"reel {n}: {e}" for e in errs]
            used.append(str(r.get("hook", "")).strip().lower())
            reels.append({**r, "key": f"r{n}", "mode": "recording" if fmt in ("faq", "story") else "edit",
                          "duration_s": 20, "format": fmt})
        raw = {**strat, "reels": reels, "series": [{"name": strat.get("pillars", ["Series"])[0] if strat.get("pillars") else "Series",
                                                     "reel_keys": [r["key"] for r in reels[:3]]}],
               "schedule": [{"day": 1 + 3 * i, "reel_key": r["key"], "time": "19:00"} for i, r in enumerate(reels)]}
        engine = f"ollama:{get_settings().ollama_model}" if not get_settings().director_api_url else "external"
    except llm.LLMUnavailable as e:
        raw, engine = rules_plan(b, language), "rules"
        notes.append(f"no model answered ({e}); rule-based fallback writes English only")
    p = Plan.model_validate(normalise(raw)).model_dump()
    grounding = []
    names = [b.name, *b.brand_terms]
    for r in p["reels"]:
        for k in ("hook", "script", "caption", "cta", "title"):
            r[k], g = ground(_restore_name(r[k], names), b)
            grounding += [f"{r['key']} {k}: {x}" for x in g]
        r["hashtags"] = ["#" + re.sub(r"[^\w]", "", h.lstrip("#")) for h in r["hashtags"] if re.sub(r"[^\w]", "", h)][:12]
    start = date.today() + timedelta(days=1)
    for s in p["schedule"]:
        s["date"] = (start + timedelta(days=int(s["day"]) - 1)).isoformat()
    return p, {"engine": engine, "errors": notes, "grounding": grounding}


def code_for(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "campaign"
    return f"{base}-{secrets.token_hex(2)}"


def links_for(b: Business, code: str, reel_key: str) -> list[dict]:
    """Tracked CTA destinations for one reel: a WhatsApp chat with a prefilled reference, and a UTM-tagged website."""
    out = []
    if b.whatsapp:
        msg = f"Hi {b.name}! I saw your reel ({code}/{reel_key}) and would like to know more."
        out.append({"kind": "whatsapp", "destination": f"https://wa.me/{b.whatsapp.lstrip('+')}?text={quote(msg, safe='')}"})
    if b.website:
        sep = "&" if "?" in b.website else "?"
        utm = urlencode({"utm_source": "instagram", "utm_medium": "reel", "utm_campaign": code, "utm_content": reel_key})
        out.append({"kind": "website", "destination": f"{b.website}{sep}{utm}"})
    return out


def new_slug() -> str:
    return secrets.token_hex(4)  # 8 lowercase hex chars
