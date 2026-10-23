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


SCHEMA = {
    "type": "object",
    "properties": {
        "concept": {"type": "string"}, "strategy": {"type": "string"},
        "pillars": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "reels": {"type": "array", "minItems": 4, "maxItems": 6, "items": {"type": "object", "properties": {
            "key": {"type": "string", "description": "short id like r1"}, "title": {"type": "string"}, "hook": {"type": "string"},
            "script": {"type": "string"}, "caption": {"type": "string"}, "hashtags": {"type": "array", "items": {"type": "string"}},
            "cta": {"type": "string"}, "mode": {"type": "string", "enum": ["edit", "recording"]},
            "style": {"type": "string", "enum": list(PROFILES)}, "duration_s": {"type": "integer"},
            "shots": {"type": "array", "items": {"type": "string"}}},
            "required": ["key", "title", "hook", "script", "caption", "hashtags", "cta", "mode", "style", "duration_s", "shots"]}},
        "series": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "reel_keys": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "reel_keys"]}},
        "schedule": {"type": "array", "items": {"type": "object", "properties": {
            "day": {"type": "integer", "description": "1 = first posting day"}, "reel_key": {"type": "string"},
            "time": {"type": "string", "description": "HH:MM local time"}}, "required": ["day", "reel_key", "time"]}},
    },
    "required": ["concept", "strategy", "pillars", "reels", "series", "schedule"],
}

PROMPT = """You are a social media strategist for small local businesses in India. Plan a short Instagram Reels campaign.

Business (facts given by the owner; use only these facts):
- Name: {name}
- Industry: {industry}
- City/area: {city}
- Audience: {audience}
- Goal: {goal}
- Offer: {offer}
- Footage/photos they already have: {footage}
- Brand words to keep exactly as written: {terms}

Write all customer-facing text (hooks, scripts, captions, CTAs, titles) in {language}. Hashtags may be English.
Rules: do NOT invent prices, discounts, numbers, awards, reviews, testimonials or results; mention the offer only as
written above (if there is no offer, do not make one up). Spell the business name exactly "{name}". Hooks must work in
the first 2 seconds. Scripts are short voiceover/on-screen lines for 15-30 s reels. mode "edit" = made from clips
with a prompt; mode "recording" = cut from a longer talking video. Choose style from the list. The CTA should invite a
WhatsApp message or a visit{website_note}. Schedule 2-3 reels per week over two weeks. Return JSON only."""


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
    for r in raw.get("reels") or []:
        if isinstance(r, dict):
            r["key"] = _key(r.get("key", ""))
            r["duration_s"] = min(60, max(8, int(float(r.get("duration_s") or 20))))
    for s in raw.get("schedule") or []:
        if isinstance(s, dict):
            s["reel_key"] = _key(s.get("reel_key", ""))
    for s in raw.get("series") or []:
        if isinstance(s, dict):
            s["reel_keys"] = [_key(k) for k in s.get("reel_keys") or []]
    return raw


def plan(b: Business, language: str) -> tuple[dict, dict]:
    """(validated plan, provenance)."""
    text = PROMPT.format(name=b.name, industry=b.industry, city=b.city or "not given", audience=b.audience, goal=b.goal,
                         offer=b.offer or "none", footage=b.footage or "not described", terms=", ".join([b.name, *b.brand_terms]),
                         language=LANG_NAME[language], website_note=" or the website" if b.website else "")
    errors = []
    raw, engine = None, "rules"
    for _ in range(2):
        try:
            raw, engine = llm.chat_json(text + (f"\nPrevious answer was invalid: {errors[-1]}" if errors else ""), SCHEMA, temperature=0.5)
            raw = normalise(raw)
            Plan.model_validate(raw)
            break
        except llm.LLMUnavailable as e:
            errors.append(str(e))
            raw = None
            break
        except Exception as e:  # noqa: BLE001 — validation errors go back to the model once
            errors.append(str(e)[:300])
            raw = None
    if raw is None:
        raw, engine = rules_plan(b, language), "rules"
        if language != "en":
            errors.append("rule-based fallback writes English only")
    p = Plan.model_validate(raw).model_dump()
    notes = []
    names = [b.name, *b.brand_terms]
    for r in p["reels"]:
        for k in ("hook", "script", "caption", "cta", "title"):
            r[k], n = ground(_restore_name(r[k], names), b)
            notes += [f"{r['key']} {k}: {x}" for x in n]
        r["hashtags"] = ["#" + re.sub(r"[^\w]", "", h.lstrip("#")) for h in r["hashtags"] if re.sub(r"[^\w]", "", h)][:12]
    keys = {r["key"] for r in p["reels"]}
    p["schedule"] = [s for s in p["schedule"] if s.get("reel_key") in keys and 1 <= int(s.get("day", 0)) <= 30] or \
        [{"day": 1 + 3 * i, "reel_key": r["key"], "time": "19:00"} for i, r in enumerate(p["reels"])]
    start = date.today() + timedelta(days=1)
    for s in p["schedule"]:
        s["date"] = (start + timedelta(days=int(s["day"]) - 1)).isoformat()
        if not re.match(r"^\d{2}:\d{2}$", str(s.get("time", ""))):
            s["time"] = "19:00"
    p["series"] = [{"name": str(s.get("name", ""))[:80], "reel_keys": [k for k in s.get("reel_keys", []) if k in keys]}
                   for s in p["series"] if s.get("reel_keys")]
    return p, {"engine": engine, "errors": errors, "grounding": notes}


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
