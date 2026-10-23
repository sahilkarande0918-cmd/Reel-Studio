"""Pacing profiles: how an edit of a given style breathes against the music.

`cut_beats` is the cycle of shot lengths in beats; `transitions` the palette used every `transition_every` cuts;
`hit_fx` the effects placed on strong beats inside a shot (at most one per shot, flashes rate-limited);
`base_fx` runs on every shot (grade, vignette); `ramps` turns on speed ramps on longer shots; `sfx` places a whoosh
under transitions and an impact on drops. Intensity 0..1 scales effect amounts.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    cut_beats: tuple[float, ...]
    transitions: tuple[str, ...]
    transition_every: int
    transition_beats: float
    hit_fx: tuple[str, ...]
    hit_every: int
    base_fx: tuple[tuple[str, dict], ...] = field(default_factory=tuple)
    ramps: bool = False
    sfx: bool = True
    intensity: float = 0.6
    default_bpm: int = 120
    score: str = "commercial"


PROFILES: dict[str, Profile] = {
    p.id: p
    for p in [
        Profile(
            "phonk",
            "Phonk / velocity",
            (1, 1, 2, 1, 1, 2),
            ("whip", "flash", "zoom_through", "cut"),
            2,
            0.5,
            ("punch_zoom", "shake", "zoom_blur", "rgb_split", "flash"),
            1,
            (("grade", {"warmth": -0.35, "contrast": 1.3, "saturation": 0.8}), ("vignette", {"angle": 0.6})),
            ramps=True,
            intensity=0.9,
            default_bpm=140,
            score="phonk",
        ),
        Profile(
            "energetic",
            "Energetic",
            (2, 2, 1, 1, 2),
            ("swipe_left", "zoom_through", "cut", "swipe_up"),
            2,
            0.5,
            ("punch_zoom", "bright_pulse"),
            2,
            (("grade", {"warmth": 0.2, "contrast": 1.12, "saturation": 1.2}),),
            intensity=0.7,
            default_bpm=128,
        ),
        Profile(
            "cinematic",
            "Cinematic",
            (4, 4, 8),
            ("crossfade", "dip_black", "blur"),
            1,
            1.0,
            ("push_in",),
            1,
            (
                ("grade", {"warmth": 0.35, "contrast": 1.1, "saturation": 0.9}),
                ("vignette", {"angle": 0.5}),
                ("grain", {"amount": 6}),
            ),
            intensity=0.4,
            default_bpm=90,
            score="cinematic",
        ),
        Profile(
            "clean_commercial",
            "Clean commercial",
            (2, 4, 2),
            ("crossfade", "swipe_left", "cut"),
            2,
            0.5,
            ("push_in",),
            1,
            (("grade", {"warmth": 0.1, "contrast": 1.06, "saturation": 1.08}),),
            intensity=0.4,
            default_bpm=118,
        ),
        Profile(
            "minimal",
            "Minimal",
            (4, 4),
            ("cut", "crossfade"),
            3,
            0.5,
            ("push_in",),
            2,
            (),
            sfx=False,
            intensity=0.25,
            default_bpm=100,
        ),
        Profile(
            "educational",
            "Educational",
            (8, 8, 4),
            ("crossfade", "cut"),
            2,
            0.5,
            ("push_in",),
            1,
            (),
            sfx=False,
            intensity=0.25,
            default_bpm=100,
        ),
        Profile(
            "product_showcase",
            "Product showcase",
            (2, 2, 4),
            ("zoom_through", "whip", "cut"),
            2,
            0.5,
            ("punch_zoom", "glow"),
            2,
            (("grade", {"warmth": 0.0, "contrast": 1.15, "saturation": 1.1}), ("vignette", {"angle": 0.45})),
            ramps=True,
            intensity=0.6,
            default_bpm=124,
        ),
        Profile(
            "motion_graphics",
            "Motion graphics",
            (2, 2, 4),
            ("swipe_left", "circle_reveal", "cut"),
            2,
            0.5,
            ("zoom_bounce",),
            2,
            (),
            intensity=0.5,
            default_bpm=120,
        ),
        Profile(
            "tech_ad",
            "Tech advertisement",
            (2, 4, 2, 4),
            ("blur", "zoom_through", "crossfade"),
            1,
            0.5,
            ("push_in", "glow"),
            1,
            (("grade", {"warmth": -0.25, "contrast": 1.1, "saturation": 1.0}),),
            intensity=0.5,
            default_bpm=110,
        ),
    ]
}

KEYWORDS = {
    "phonk": ("phonk", "aggressive", "velocity", "drift", "hype", "sigma"),
    "cinematic": ("cinematic", "film", "movie", "emotional", "dramatic", "slow"),
    "energetic": ("energetic", "energy", "fast", "upbeat", "fun", "viral"),
    "clean_commercial": ("commercial", "clean", "professional", "brand", "business"),
    "minimal": ("minimal", "simple", "calm", "subtle"),
    "educational": ("educational", "lesson", "explain", "tutorial", "class"),
    "product_showcase": ("product", "showcase", "store", "shop", "shoe", "launch"),
    "motion_graphics": ("motion graphic", "infographic", "animated", "kinetic"),
    "tech_ad": ("saas", "tech", "app", "software", "website", "startup"),
}


def guess(prompt: str) -> str:
    """Keyword fallback when the LLM director is offline: the profile whose words appear most in the prompt."""
    p = prompt.lower()
    best = max(KEYWORDS, key=lambda k: sum(w in p for w in KEYWORDS[k]))
    return best if any(w in p for w in KEYWORDS[best]) else "clean_commercial"
