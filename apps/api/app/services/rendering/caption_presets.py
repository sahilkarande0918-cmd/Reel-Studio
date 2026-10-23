"""100 caption presets in 23 families. A preset is a full caption *look* (timeline `captionStyle.look`): typeface, case,
colours, stroke, shadow/glow, how the spoken word is highlighted, how each word enters, box and position. Presets
differ in behaviour, not only colour; compose.py renders every field, so the gallery preview and the export match.

Colour values may be the brand tokens "accent", "text" or "bg"; `style_for` resolves them with the edit's brand.
All typefaces are bundled SIL OFL fonts (rendering/fonts).
"""

from typing import Literal

from pydantic import BaseModel, Field


class Overrides(BaseModel):
    """User customisation of a preset (validated at the API boundary)."""

    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    active: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    sizeScale: float | None = Field(default=None, ge=0.5, le=1.8)
    position: Literal["lower", "middle", "upper"] | None = None


FAMILIES = ["Minimal", "Creator", "Cinematic", "Learning", "Brand", "Karaoke", "Kinetic", "Glow", "Neon", "Outline",
            "Bold", "Retro", "Editorial", "Typewriter", "Gaming", "Phonk", "Pop", "Bounce", "Documentary", "Product",
            "Modern", "Handwritten", "Headline"]
ZONES = {"lower": (1350, 1650), "middle": (810, 1110), "upper": (260, 560)}  # on a 1920-high frame

W, K, Y, R = "#FFFFFF", "#000000", "#FFD43B", "#FF3B3B"


def P(family: str, slug: str, name: str, font: str, color: str = W, active: str = "accent", **look) -> dict:
    return {"id": f"{family.lower()}-{slug}", "name": name, "family": family,
            "look": {"id": f"{family.lower()}-{slug}", "font": font, "color": color, "active": active, **look}}


PRESETS: list[dict] = [
    # Minimal: quiet type, little or no highlight
    P("Minimal", "clean", "Clean", "Noto Sans", highlight="none", entrance="fade", shadow="soft", sizeScale=0.85),
    P("Minimal", "underline", "Underline", "Poppins", highlight="underline", sizeScale=0.85),
    P("Minimal", "mono", "Mono", "JetBrains Mono", highlight="fill", sizeScale=0.75, shadow="soft"),
    P("Minimal", "serif", "Serif", "Fraunces", highlight="fill", active="#E9E2C8", sizeScale=0.9),
    P("Minimal", "upper", "Small caps", "Archivo", uppercase=True, tracking=0.12, sizeScale=0.62, highlight="none", entrance="fade"),
    # Creator: bold social captions
    P("Creator", "pop", "Creator pop", "Poppins", uppercase=True, highlight="chip", chip="accent", entrance="pop", stroke=0),
    P("Creator", "yellow", "Yellow word", "Archivo", uppercase=True, active=Y, stroke=5, highlight="scale", shadow="hard"),
    P("Creator", "green", "Green chip", "Poppins", highlight="chip", chip="#2ECC71", active=K, entrance="pop"),
    P("Creator", "boxed", "Boxed", "Poppins", box=True, highlight="fill", active=Y),
    P("Creator", "bounce", "Bounce", "Archivo", uppercase=True, stroke=4, active=Y, entrance="bounce", highlight="fill"),
    P("Creator", "wave", "Wave", "Poppins", highlight="fill", active="#4DD4FF", entrance="wave", stroke=3),
    # Cinematic
    P("Cinematic", "serif", "Serif subtitle", "Fraunces", tracking=0.04, entrance="fade", highlight="none", position="middle", shadow="soft"),
    P("Cinematic", "letterbox", "Letterbox", "Bebas Neue", uppercase=True, tracking=0.18, highlight="none", entrance="fade", position="upper", sizeScale=1.1),
    P("Cinematic", "blur", "Blur in", "Fraunces", entrance="blur", highlight="fill", active="#F2E6C9"),
    P("Cinematic", "gold", "Gold underline", "Fraunces", highlight="underline", active="#D4AF37", shadow="soft"),
    P("Cinematic", "italic", "Italic", "Fraunces", italic=True, highlight="fill", active="#CFE3FF", entrance="fade"),
    # Learning: legible, code-aware, calm
    P("Learning", "clear", "Clear", "Noto Sans", highlight="chip", chip="accent"),
    P("Learning", "highlighter", "Highlighter", "Poppins", highlight="chip", chip=Y, active=K, shadow="none", box=True),
    P("Learning", "underline", "Underline", "Noto Sans", highlight="underline", active="#4DD4FF"),
    P("Learning", "mono", "Mono notes", "Fira Code", highlight="fill", active="#A7E3BC", entrance="typewriter", sizeScale=0.8),
    P("Learning", "card", "Card", "Noto Sans", box=True, highlight="chip", chip="accent", sizeScale=0.9),
    # Brand: uses the brand kit colours
    P("Brand", "chip", "Brand chip", "Poppins", highlight="chip", chip="accent", color="text"),
    P("Brand", "box", "Brand box", "Archivo", box=True, highlight="fill", color="text"),
    P("Brand", "underline", "Brand underline", "Poppins", highlight="underline", color="text", entrance="fade"),
    P("Brand", "bold", "Brand bold", "Archivo", uppercase=True, stroke=3, highlight="scale", color="text"),
    # Karaoke: words fill as they are spoken and stay filled
    P("Karaoke", "classic", "Classic", "Poppins", highlight="karaoke", active=Y, stroke=3),
    P("Karaoke", "neon", "Neon fill", "Bebas Neue", uppercase=True, highlight="karaoke", active="#39FF14", glow=14, sizeScale=1.2),
    P("Karaoke", "serif", "Serif fill", "Fraunces", highlight="karaoke", active="#F7C59F"),
    P("Karaoke", "condensed", "Condensed", "Bebas Neue", uppercase=True, highlight="karaoke", active="accent", sizeScale=1.25, tracking=0.03),
    P("Karaoke", "pixel", "Pixel fill", "Press Start 2P", highlight="karaoke", active="#7CFC00", sizeScale=0.55, shadow="hard"),
    # Kinetic: each word enters on its own beat
    P("Kinetic", "drop", "Drop", "Archivo", uppercase=True, entrance="drop", highlight="fill", active=Y, stroke=3),
    P("Kinetic", "swing", "Swing", "Poppins", entrance="swing", highlight="fill", active="accent", stroke=2),
    P("Kinetic", "zoom", "Zoom", "Archivo", uppercase=True, entrance="zoom", highlight="scale", active=Y),
    P("Kinetic", "slide", "Slide", "Poppins", entrance="slide", highlight="fill", active="#4DD4FF"),
    P("Kinetic", "wave", "Wave", "Bebas Neue", uppercase=True, entrance="wave", highlight="fill", sizeScale=1.2, active="accent"),
    # Glow
    P("Glow", "white", "White glow", "Poppins", glow=18, highlight="fill", active=W, color="#DDE6FF", shadow="none"),
    P("Glow", "cyan", "Cyan glow", "Archivo", glow=22, highlight="fill", active="#4DFFFF", shadow="none"),
    P("Glow", "pink", "Pink glow", "Poppins", glow=22, highlight="fill", active="#FF5FD2", shadow="none"),
    P("Glow", "gold", "Gold glow", "Fraunces", glow=20, highlight="fill", active="#FFD27A", shadow="none"),
    # Neon
    P("Neon", "tube", "Tube", "Bebas Neue", uppercase=True, color="#7DF9FF", active="#FF4FD8", glow=26, shadow="none", sizeScale=1.25),
    P("Neon", "pink", "Pink sign", "Bebas Neue", uppercase=True, color="#FF8AE2", active=W, glow=28, shadow="none", sizeScale=1.25, entrance="fade"),
    P("Neon", "green", "Green sign", "Press Start 2P", color="#39FF14", active=W, glow=18, shadow="none", sizeScale=0.55),
    P("Neon", "script", "Neon script", "Caveat", color="#FFB3F5", active="#7DF9FF", glow=24, shadow="none", sizeScale=1.4),
    # Outline
    P("Outline", "classic", "Black outline", "Archivo", stroke=6, strokeColor=K, highlight="fill", active=Y, shadow="none"),
    P("Outline", "yellow", "Yellow outline", "Poppins", stroke=5, strokeColor="#1A1A1A", color=Y, active=W, highlight="fill", shadow="none"),
    P("Outline", "thick", "Thick", "Archivo", uppercase=True, stroke=9, strokeColor=K, highlight="scale", active=Y, shadow="none"),
    P("Outline", "accent", "Accent outline", "Poppins", stroke=6, strokeColor="accent", color=W, active=W, highlight="scale", shadow="none"),
    # Bold
    P("Bold", "impact", "Impact", "Archivo", uppercase=True, stroke=6, highlight="scale", active=Y, shadow="hard", sizeScale=1.15),
    P("Bold", "red", "Red hit", "Archivo", uppercase=True, stroke=5, highlight="fill", active=R, shadow="hard"),
    P("Bold", "stack", "Big stack", "Archivo", uppercase=True, sizeScale=1.4, stroke=6, highlight="fill", active=Y, position="middle"),
    P("Bold", "black-chip", "Black chip", "Poppins", uppercase=True, highlight="chip", chip=K, active=W, shadow="none"),
    P("Bold", "bounce", "Bold bounce", "Archivo", uppercase=True, stroke=5, entrance="bounce", highlight="scale", active="accent"),
    # Retro
    P("Retro", "pixel", "8-bit", "Press Start 2P", color=W, active=Y, sizeScale=0.55, shadow="hard", highlight="fill"),
    P("Retro", "vhs", "VHS", "JetBrains Mono", uppercase=True, color="#E0E0E0", active="#FF5FD2", glow=8, highlight="fill", sizeScale=0.85),
    P("Retro", "seventies", "Seventies", "Fraunces", italic=True, color="#FFB347", active="#FF6F3C", shadow="hard", highlight="fill"),
    P("Retro", "arcade", "Arcade", "Press Start 2P", color="#39FF14", active=W, sizeScale=0.5, entrance="typewriter", highlight="fill"),
    # Editorial
    P("Editorial", "serif", "Magazine serif", "Fraunces", highlight="underline", active=W, sizeScale=0.95),
    P("Editorial", "caps", "Small caps", "Noto Sans", uppercase=True, tracking=0.2, sizeScale=0.62, highlight="fill", active="accent"),
    P("Editorial", "rule", "Rule", "Fraunces", italic=True, highlight="underline", active="accent", entrance="fade"),
    P("Editorial", "box", "Box quote", "Fraunces", box=True, highlight="none", entrance="fade", sizeScale=0.9),
    # Typewriter: letters of the page appear word by word
    P("Typewriter", "mono", "Mono", "JetBrains Mono", entrance="typewriter", highlight="none", sizeScale=0.8),
    P("Typewriter", "terminal", "Terminal", "Fira Code", color="#7CFC00", active=W, entrance="typewriter", highlight="fill", sizeScale=0.8, glow=6),
    P("Typewriter", "paper", "Paper", "JetBrains Mono", box=True, color=K, active="#B00020", entrance="typewriter", shadow="none", sizeScale=0.8),
    P("Typewriter", "amber", "Amber", "Fira Code", color="#FFBF00", active=W, entrance="typewriter", glow=8, sizeScale=0.8),
    # Gaming
    P("Gaming", "pixel", "Pixel yellow", "Press Start 2P", color=Y, active=W, sizeScale=0.55, entrance="pop", shadow="hard"),
    P("Gaming", "stroke", "Stroke", "Bebas Neue", uppercase=True, stroke=6, color=W, active="#00E5FF", sizeScale=1.3, highlight="scale"),
    P("Gaming", "zoom", "Zoom hit", "Archivo", uppercase=True, entrance="zoom", stroke=4, active="#A3FF12", highlight="fill"),
    P("Gaming", "health", "Health bar", "Poppins", uppercase=True, highlight="chip", chip=R, active=W, shadow="hard"),
    # Phonk
    P("Phonk", "red", "Red glow", "Bebas Neue", uppercase=True, color=W, active=R, glow=18, sizeScale=1.35, entrance="drop", shadow="none"),
    P("Phonk", "chrome", "Chrome", "Bebas Neue", uppercase=True, color="#E8E8E8", active=W, glow=28, sizeScale=1.35, tracking=0.05, shadow="none"),
    P("Phonk", "purple", "Purple haze", "Bebas Neue", uppercase=True, color="#C9A7FF", active="#FF4FD8", glow=20, sizeScale=1.3, entrance="zoom"),
    P("Phonk", "swing", "Swing hit", "Archivo", uppercase=True, stroke=5, active=R, entrance="swing", highlight="scale"),
    P("Phonk", "pixel", "Pixel drift", "Press Start 2P", color=W, active=R, sizeScale=0.55, glow=10, entrance="pop"),
    # Pop
    P("Pop", "candy", "Candy", "Poppins", highlight="chip", chip="#FF5FA2", active=W, entrance="pop", shadow="none"),
    P("Pop", "bubble", "Bubble", "Poppins", box=True, highlight="fill", active="#FF5FA2", entrance="pop"),
    P("Pop", "sticker", "Sticker", "Archivo", uppercase=True, color=K, stroke=7, strokeColor=W, active="#FF3EA5", highlight="scale", shadow="hard"),
    # Bounce
    P("Bounce", "yellow", "Yellow", "Archivo", uppercase=True, entrance="bounce", active=Y, stroke=4, highlight="scale", sizeScale=1.1),
    P("Bounce", "white", "White", "Poppins", entrance="bounce", highlight="none", shadow="hard"),
    P("Bounce", "chip", "Chip", "Poppins", entrance="bounce", highlight="chip", chip="accent"),
    P("Bounce", "big", "Big", "Archivo", uppercase=True, entrance="bounce", sizeScale=1.35, stroke=6, active=Y, position="middle"),
    # Documentary
    P("Documentary", "lower", "Lower strap", "Noto Sans", box=True, highlight="none", entrance="fade", sizeScale=0.8),
    P("Documentary", "serif", "Narrator", "Fraunces", italic=True, highlight="none", entrance="fade", sizeScale=0.85),
    P("Documentary", "subtitle", "Subtitle", "Noto Sans", highlight="none", shadow="hard", sizeScale=0.7),
    P("Documentary", "mono", "Field notes", "JetBrains Mono", highlight="none", entrance="fade", sizeScale=0.7, position="upper"),
    # Product showcase
    P("Product", "clean", "Clean", "Archivo", highlight="underline", active="accent", sizeScale=0.9),
    P("Product", "chip", "Chip", "Poppins", highlight="chip", chip="accent", entrance="pop", sizeScale=0.85, tracking=0.04, shadow="none"),
    P("Product", "luxe", "Luxe", "Fraunces", tracking=0.06, color="#F5E6C8", active="#D4AF37", glow=6, entrance="blur", highlight="fill"),
    P("Product", "caps", "Caps", "Archivo", uppercase=True, tracking=0.1, sizeScale=0.7, highlight="fill", active="accent", entrance="slide"),
    # Modern
    P("Modern", "grotesk", "Grotesk", "Archivo", highlight="fill", active="accent", sizeScale=0.95),
    P("Modern", "glow", "Soft glow", "Poppins", glow=10, highlight="fill", active="#B8F2FF", entrance="blur"),
    P("Modern", "blur", "Blur", "Noto Sans", entrance="blur", highlight="chip", chip="accent"),
    P("Modern", "spaced", "Spaced", "Poppins", uppercase=True, tracking=0.15, sizeScale=0.7, highlight="fill", active="accent", entrance="slide"),
    # Handwritten
    P("Handwritten", "white", "Note", "Caveat", sizeScale=1.4, highlight="fill", active=Y, shadow="soft"),
    P("Handwritten", "marker", "Marker", "Caveat", sizeScale=1.4, highlight="chip", chip=Y, active=K),
    P("Handwritten", "card", "Card", "Caveat", sizeScale=1.4, box=True, highlight="underline", active="accent"),
    P("Handwritten", "bounce", "Doodle", "Caveat", sizeScale=1.5, entrance="bounce", highlight="fill", active="#4DD4FF"),
    # Animated headline: big captions in the upper or middle zone
    P("Headline", "top", "Top headline", "Archivo", uppercase=True, sizeScale=1.3, position="upper", stroke=5, entrance="slide", active=Y),
    P("Headline", "stack", "Centre stack", "Bebas Neue", uppercase=True, sizeScale=1.6, position="middle", entrance="zoom", active="accent"),
    P("Headline", "serif", "Serif headline", "Fraunces", sizeScale=1.3, position="upper", entrance="blur", highlight="underline"),
    P("Headline", "drop", "Drop headline", "Archivo", uppercase=True, sizeScale=1.25, position="middle", entrance="drop", stroke=5, active=R),
]
BY_ID = {p["id"]: p for p in PRESETS}
DEFAULT = "creator-pop"


def resolve(look: dict, colors: dict) -> dict:
    """Brand tokens → hex colours."""
    tok = {"accent": colors["accent"], "text": colors["text"], "bg": colors["background"]}
    return {k: tok.get(v, v) if k in ("color", "active", "chip", "strokeColor") else v for k, v in look.items()}


def style_for(preset_id: str, style: dict, h: int, colors: dict | None = None, overrides: dict | None = None) -> dict:
    """Caption style for a preset id (unknown ids fall back to the default preset), with optional customisation."""
    p = BY_ID.get(preset_id) or BY_ID[DEFAULT]
    look = resolve({**p["look"], **(overrides or {})}, colors or {"accent": "#C8E06B", "text": "#FFFFFF", "background": "#141810"})
    a, b = ZONES[look.get("position", "lower")]
    k = h / 1920
    base = {"karaoke": "karaoke", "none": "highlight-word"}.get(look.get("highlight", "fill"), "highlight-word")
    return {**style, "enabled": True, "preset": "boxed" if look.get("box") else base, "look": look,
            "safeTop": round(a * k), "safeBottom": round(b * k)}


def catalog() -> list[dict]:
    return [{"id": p["id"], "name": p["name"], "family": p["family"], "look": p["look"]} for p in PRESETS]
