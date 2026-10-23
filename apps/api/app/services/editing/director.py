"""AI Editing Director: prompt + footage/music/reference analysis → a validated creative directive.

The LLM (local Qwen by default, optional external endpoint) only makes *decisions*: style, pacing, look, which
transitions/effects suit the material, which clips matter, on-screen text and motion-graphic scenes. Every choice is
constrained to the registries (effects, transitions, templates) by the JSON schema and validated again here. The
deterministic planner then turns the directive into frame-exact, beat-snapped segments, so an LLM can never produce
an unrenderable timeline. If no model answers, a rule-based director decides from the same inputs (recorded as such).
"""

import re
from dataclasses import replace
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.services import llm
from app.services.editing import effects, pacing

Pace = Literal["very_slow", "slow", "medium", "fast", "very_fast"]
Look = Literal["neutral", "warm", "cool", "teal_orange", "high_contrast", "black_white", "vintage", "moody"]
PACE_SCALE = {"very_slow": 2.0, "slow": 1.5, "medium": 1.0, "fast": 0.75, "very_fast": 0.5}
LOOKS: dict[str, tuple[tuple[str, dict], ...]] = {
    "neutral": (),
    "warm": (("grade", {"warmth": 0.35, "contrast": 1.08, "saturation": 1.1}),),
    "cool": (("grade", {"warmth": -0.35, "contrast": 1.08, "saturation": 0.95}),),
    "teal_orange": (("grade", {"warmth": 0.2, "contrast": 1.15, "saturation": 1.2}), ("vignette", {"angle": 0.45})),
    "high_contrast": (("grade", {"warmth": -0.1, "contrast": 1.3, "saturation": 0.9}), ("vignette", {"angle": 0.6})),
    "black_white": (("black_white", {}), ("grade", {"warmth": 0, "contrast": 1.25, "saturation": 0}), ("grain", {"amount": 8})),
    "vintage": (("grade", {"warmth": 0.4, "contrast": 0.95, "saturation": 0.8}), ("grain", {"amount": 12}), ("vignette", {"angle": 0.6})),
    "moody": (("grade", {"warmth": -0.3, "contrast": 1.2, "saturation": 0.75}), ("vignette", {"angle": 0.7}), ("grain", {"amount": 6})),
}
HIT_EFFECTS = sorted(e.id for e in effects.EFFECTS.values() if "beat" in e.tags or e.id in ("push_in", "pull_out", "glow", "blur_reveal", "whip_pan", "motion_blur", "pan"))
TRANSITION_IDS = sorted(effects.TRANSITIONS)


def _share(v):
    """Models drift between 0-1, 0-10 and 0-100 scales; anything above 1 is read as the larger scale, then clamped."""
    v = float(v)
    return min(max(v / 100 if v > 10 else v / 10 if v > 1 else v, 0.0), 1.0)


class Text(BaseModel):
    at: float = Field(ge=0, le=1, description="position in the edit, 0 = start, 1 = end")
    _at = field_validator("at", mode="before")(_share)
    text: str = Field(min_length=1, max_length=48)
    role: Literal["hook", "point", "cta"]


class Graphic(BaseModel):
    template: str
    at: float = Field(ge=0, le=1)
    _at = field_validator("at", mode="before")(_share)
    duration_s: float = Field(ge=1, le=8)
    fields: dict[str, str] = Field(default_factory=dict)


class Directive(BaseModel):
    style: str
    treatment: str = Field(max_length=400)
    pacing: Pace
    intensity: float = Field(ge=0, le=1)
    look: Look
    transitions: list[str] = Field(min_length=1, max_length=4)
    hit_effects: list[str] = Field(max_length=5)
    speed_ramps: bool
    sound_effects: bool
    hero_clips: list[int] = Field(default_factory=list, max_length=60)
    skip_clips: list[int] = Field(default_factory=list, max_length=300)
    open_with: int = 0
    close_with: int = 0
    on_screen_text: list[Text] = Field(default_factory=list, max_length=6)
    graphics: list[Graphic] = Field(default_factory=list, max_length=6)
    narration: str = Field(default="", max_length=1200)
    reasons: list[str] = Field(default_factory=list, max_length=12)
    _intensity = field_validator("intensity", mode="before")(_share)

    @field_validator("style")
    @classmethod
    def _style(cls, v: str) -> str:
        if v not in pacing.PROFILES:
            raise ValueError(f"unknown style {v}")
        return v

    @field_validator("transitions")
    @classmethod
    def _tr(cls, v: list[str]) -> list[str]:
        bad = [x for x in v if x not in effects.TRANSITIONS]
        if bad:
            raise ValueError(f"unknown transitions {bad}")
        return v

    @field_validator("hit_effects")
    @classmethod
    def _fx(cls, v: list[str]) -> list[str]:
        bad = [x for x in v if x not in effects.EFFECTS]
        if bad:
            raise ValueError(f"unknown effects {bad}")
        return v


def schema(n_clips: int, templates: dict[str, dict]) -> dict:
    clip = {"type": "integer", "minimum": 0, "maximum": n_clips}
    return {
        "type": "object",
        "properties": {
            "style": {"type": "string", "enum": list(pacing.PROFILES)},
            "treatment": {"type": "string", "description": "the creative idea in 1-2 sentences"},
            "pacing": {"type": "string", "enum": list(PACE_SCALE)},
            "intensity": {"type": "number", "description": "0 calm .. 1 aggressive"},
            "look": {"type": "string", "enum": list(LOOKS)},
            "transitions": {"type": "array", "items": {"type": "string", "enum": TRANSITION_IDS}, "minItems": 1, "maxItems": 4},
            "hit_effects": {"type": "array", "items": {"type": "string", "enum": HIT_EFFECTS}, "maxItems": 5},
            "speed_ramps": {"type": "boolean"},
            "sound_effects": {"type": "boolean"},
            "hero_clips": {"type": "array", "items": clip, "description": "clip numbers, most important first"},
            "skip_clips": {"type": "array", "items": clip, "description": "unusable clip numbers"},
            "open_with": {**clip, "description": "clip number for the opening shot, 0 = let the planner choose"},
            "close_with": {**clip, "description": "clip number for the final shot, 0 = let the planner choose"},
            "on_screen_text": {
                "type": "array",
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "at": {"type": "number"},
                        "text": {"type": "string"},
                        "role": {"type": "string", "enum": ["hook", "point", "cta"]},
                    },
                    "required": ["at", "text", "role"],
                },
            },
            "graphics": {
                "type": "array",
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "template": {"type": "string", "enum": list(templates) or ["none"]},
                        "at": {"type": "number"},
                        "duration_s": {"type": "number"},
                        "fields": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                    "required": ["template", "at", "duration_s", "fields"],
                },
            },
            "narration": {"type": "string"},
            "reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        },
        "required": ["style", "treatment", "pacing", "intensity", "look", "transitions", "hit_effects", "speed_ramps",
                     "sound_effects", "hero_clips", "skip_clips", "open_with", "close_with", "on_screen_text",
                     "graphics", "narration", "reasons"],
    }


def _clip_line(n: int, name: str, a: dict) -> str:
    vlm = a.get("vlm") or {}
    seen = f"; looks like: {vlm.get('shot', '')} {vlm.get('subject', '')} in {vlm.get('setting', '')}" if vlm else ""
    if a.get("kind") == "image":
        return f"{n}. {name}: still image{seen}{' (product)' if vlm.get('is_product') else ''}"
    best = max((m["score"] for m in a.get("moments") or []), default=0)
    return (
        f"{n}. {name}: {a.get('duration_s', 0):.1f}s {a.get('orientation', '')}, motion {a.get('motion_mean', 0):.2f}, "
        f"best-moment score {best:.2f}, brightness {a.get('brightness', 0):.0f}{seen}"
        f"{' (product)' if vlm.get('is_product') else ''}"
    )


PROMPT = """You are the editing director of a professional short-video studio. Decide how to edit the user's own
footage into a {duration:.0f}-second {aspect} video. Choose only what suits THIS footage and request; do not add
effects just to look busy. Cinematic = restrained motion, smooth transitions. Phonk/aggressive = velocity ramps, punch
zooms, flashes, shake, rapid beat cuts. Premium/SaaS ads = clean transitions, editorial text, motion graphics.
Educational = calm pacing, clear text. Vague requests ("edit it professionally") = sensible defaults for the footage.

User request: \"\"\"{prompt}\"\"\"
{style_line}
Footage ({n} files, numbered; descriptions after "looks like" come from a vision model and may be wrong):
{clips}
{more}
Music: {music}
Reference reel: {reference}
Motion-graphic templates available (use only when the request or footage calls for designed scenes): {templates}
Narration requested: {voice}

graphics: designed scenes from the templates above, each with "fields" filled for that template (short text) and
optionally "media": "N" (a clip/image number) for templates that show media. Use designed scenes when the request asks
for motion graphics, an advertisement, mockups or infographics; for pure footage edits (phonk, cinematic) use none or
only overlays. Scenes play one after another; together they may cover the whole video.
Rules: on_screen_text is short (max 6 words each), only claims supported by the request (no invented prices, offers,
names or numbers). If the request names a brand, product or offer, you may use it. narration is only written when
narration is requested and the user gave no script; otherwise "". Use clip numbers exactly as listed.
Give 3-8 short reasons naming the evidence for your main choices. Return JSON only."""


def describe_inputs(clips: list[tuple[str, dict]], music: dict | None, reference: dict | None) -> tuple[str, str, str, str]:
    order = sorted(range(len(clips)), key=lambda i: -max((m["score"] for m in clips[i][1].get("moments") or []), default=0))
    shown = sorted(order[:40])
    lines = "\n".join(_clip_line(i + 1, clips[i][0], clips[i][1]) for i in shown)
    more = f"(+{len(clips) - len(shown)} more clips of lower measured quality not listed)" if len(clips) > len(shown) else ""
    if music and music.get("has_music"):
        m = f"{music['tempo_bpm']} BPM, {music['duration_s']:.0f}s, drops at {music.get('drops') or 'none detected'} s"
    else:
        m = "none uploaded (an original score matching the style is synthesized, or footage audio)"
    ref = "none"
    if reference:
        ref = "; ".join(reference.get("techniques") or []) or "measured, no strong techniques"
        ref += f"; median shot {reference.get('pacing', {}).get('median_shot_s')} s"
    return lines, more, m, ref


def rules(prompt: str, style: str, clips: list[tuple[str, dict]], has_voice: bool) -> Directive:
    """Deterministic director: keyword intent + measured clip quality. Used when no model answers."""
    p = prompt.lower()
    sid = style if style in pacing.PROFILES else pacing.guess(prompt)
    prof = pacing.PROFILES[sid]
    pace: Pace = "fast" if re.search(r"\b(fast|quick|rapid|aggressive|hype)\b", p) else "slow" if re.search(r"\b(slow|calm|relax(ed|ing)?)\b", p) else "medium"
    look: Look = next((lk for lk, words in {
        "black_white": ("black and white", "b&w", "monochrome"), "vintage": ("vintage", "retro", "film look"),
        "warm": ("warm", "golden", "cozy"), "cool": ("cool", "cold", "blue"), "moody": ("moody", "dark", "phonk"),
        "teal_orange": ("cinematic", "teal"), "high_contrast": ("aggressive", "punchy", "contrast"),
    }.items() if any(w in p for w in words)), "neutral")
    ranked = sorted(range(len(clips)), key=lambda i: -max((m["score"] for m in clips[i][1].get("moments") or []), default=0))
    dark = [i + 1 for i, (_, a) in enumerate(clips) if a.get("kind") != "image" and a.get("brightness", 99) < 20]
    hero = [i + 1 for i in ranked if i + 1 not in dark][:5]
    return Directive(
        style=sid,
        treatment=f"{prof.label} edit chosen from the request's wording; clips ranked by measured sharpness and motion.",
        pacing=pace,
        intensity=prof.intensity,
        look=look,
        transitions=[t for t in prof.transitions][:4],
        hit_effects=list(prof.hit_fx)[:5],
        speed_ramps=prof.ramps,
        sound_effects=prof.sfx,
        hero_clips=hero,
        skip_clips=dark if len(dark) < len(clips) else [],
        open_with=hero[0] if hero else 0,
        close_with=hero[1] if len(hero) > 1 else 0,
        narration="" if not has_voice else "",
        reasons=[f"style '{sid}' from keywords in the request", f"look '{look}'", f"pace '{pace}'",
                 f"{len(dark)} near-black clip(s) skipped" if dark else "all clips usable"],
    )


def direct(
    prompt: str,
    settings: dict,
    clips: list[tuple[str, dict]],
    music: dict | None,
    reference: dict | None,
    templates: dict[str, dict] | None = None,
) -> tuple[Directive, dict]:
    """(directive, provenance). The user's explicit style choice always wins over the model's."""
    templates = templates or {}
    style = settings.get("style", "auto")
    has_voice = settings.get("voice", "none") != "none"
    lines, more, m, ref = describe_inputs(clips, music, reference)
    text = PROMPT.format(
        duration=settings.get("duration_s", 15), aspect=settings.get("aspect", "9:16"), prompt=prompt,
        style_line=f"The user chose the style '{style}'; keep it." if style != "auto" else "",
        n=len(clips), clips=lines, more=more, music=m, reference=ref,
        templates="; ".join(f"{k} [fields: {', '.join(v['fields']) or 'none'}] = {v['description']}" for k, v in templates.items()) or "none",
        voice=("yes, script given by the user" if settings.get("narration") else "yes, write a short script") if has_voice else "no",
    )
    errors = []
    for attempt in range(2):
        try:
            raw, engine = llm.chat_json(text + ("\nYour previous answer was invalid: " + errors[-1] if errors else ""),
                                        schema(len(clips), templates), temperature=0.2 + 0.2 * attempt)
            d = Directive.model_validate(raw)
            d = _sanitise(d, len(clips), templates, style)
            return d, {"engine": engine, "attempts": attempt + 1, "errors": errors}
        except llm.LLMUnavailable as e:
            errors.append(str(e))
            break
        except ValidationError as e:
            errors.append(str(e.errors()[:3])[:400])
    d = rules(prompt, style, clips, has_voice)
    return d, {"engine": "rules", "attempts": len(errors), "errors": errors}


def _sanitise(d: Directive, n: int, templates: dict, style: str) -> Directive:
    ok = lambda xs: [x for x in dict.fromkeys(xs) if 1 <= x <= n]  # noqa: E731
    skip = ok(d.skip_clips)
    if n - len(skip) < 3:  # with few clips every clip is needed for variety; skipping one makes the edit loop
        skip = []
    return d.model_copy(update={
        "style": style if style in pacing.PROFILES else d.style,
        "hero_clips": [x for x in ok(d.hero_clips) if x not in skip],
        "skip_clips": skip,
        "open_with": d.open_with if 1 <= d.open_with <= n and d.open_with not in skip else 0,
        "close_with": d.close_with if 1 <= d.close_with <= n and d.close_with not in skip else 0,
        "graphics": [g for g in d.graphics if g.template in templates],
        "on_screen_text": sorted(d.on_screen_text, key=lambda t: t.at),
    })


def profile_for(d: Directive) -> pacing.Profile:
    """Directive → pacing profile for the deterministic planner."""
    base = pacing.PROFILES[d.style]
    k = PACE_SCALE[d.pacing]
    # whole beats only: a scaled 1.5-beat shot would put every other cut on the off-beat
    cut = tuple(float(max(1, round(b * k))) for b in base.cut_beats)
    return replace(
        base,
        cut_beats=cut,
        transitions=tuple(d.transitions),
        hit_fx=tuple(d.hit_effects),
        hit_every=1 if d.intensity >= 0.7 else 2 if d.intensity >= 0.35 else 3,
        base_fx=LOOKS[d.look],
        ramps=d.speed_ramps,
        sfx=d.sound_effects,
        # half the style's calibrated intensity, half the model's: a "calm cinematic" never ends up at full strength
        intensity=round((base.intensity + d.intensity) / 2, 2),
    )


def clip_weights(d: Directive, n: int) -> list[float]:
    """Hero clips are preferred, skipped clips never used (planner multiplies moment scores by these)."""
    w = [1.0] * n
    for rank, c in enumerate(d.hero_clips):
        w[c - 1] = 1.6 - 0.1 * min(rank, 5)
    for c in d.skip_clips:
        w[c - 1] = 0.0
    return w
