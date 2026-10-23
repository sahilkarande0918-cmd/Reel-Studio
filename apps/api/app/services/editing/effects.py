"""Typed effects registry for the base picture (FFmpeg renderer).

Every registered effect declares its category, parameters (min/max/default), the renderer that draws it and a builder
that returns a real FFmpeg filter fragment. Times inside a builder are segment-local seconds (`t` restarts at 0 for
each segment), `d` is the segment's output duration. Effects drawn by other renderers (typography, cards, masks in
Hyperframes; 3D in Blender) live in their own registries and are routed by `router.py`.

Flashing effects carry `photosensitive=True`; `validate` caps their rate (≤ 3 flashes per second, WCAG 2.3.1).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

Builder = Callable[
    [dict, float, int, int], str
]  # (params, segment duration, width, height) -> filter fragment


@dataclass(frozen=True)
class Param:
    lo: float
    hi: float
    default: float


@dataclass(frozen=True)
class Effect:
    id: str
    category: str  # camera | blur | impact | velocity | light | composite
    description: str
    params: dict[str, Param]
    build: Builder
    renderer: str = "ffmpeg"
    gpu: bool = False
    photosensitive: bool = False
    keyframed: bool = False  # parameters follow a curve over the effect window
    formats: tuple[str, ...] = ("9:16", "1:1", "4:5", "16:9")
    tags: tuple[str, ...] = field(default_factory=tuple)


def _win(p: dict, d: float) -> tuple[float, float]:
    """Effect window inside the segment: [at, at+dur], clamped."""
    at = max(0.0, min(p.get("at", 0.0), d))
    dur = max(1 / 30, min(p.get("dur", d - at), d - at))
    return at, at + dur


def _enable(p: dict, d: float) -> str:
    a, b = _win(p, d)
    return f"enable='between(t,{a:.3f},{b:.3f})'"


def _zoom(expr: str, w: int, h: int) -> str:
    """Scale by a time-varying factor around the centre and crop back to the frame (no black borders)."""
    return (
        f"scale=w='ceil(iw*({expr})/2)*2':h='ceil(ih*({expr})/2)*2':eval=frame:flags=bicubic,"
        f"crop={w}:{h}:'(iw-{w})/2':'(ih-{h})/2'"
    )


def _ease(a: float, b: float) -> str:
    """Smoothstep 0→1 across [a, b] as an FFmpeg expression in t."""
    x = f"clip((t-{a:.3f})/{max(b - a, 1e-3):.3f},0,1)"
    return f"({x}*{x}*(3-2*{x}))"


# --- camera ------------------------------------------------------------------------------------------------------
def push_in(p, d, w, h):
    a, b = _win(p, d)
    return _zoom(f"1+{p['amount']:.3f}*{_ease(a, b)}", w, h)


def pull_out(p, d, w, h):
    a, b = _win(p, d)
    return _zoom(f"1+{p['amount']:.3f}*(1-{_ease(a, b)})", w, h)


def punch_zoom(p, d, w, h):
    """Instant jump in scale at `at`, eased back over `dur` (the classic beat punch)."""
    a, b = _win(p, d)
    decay = f"exp(-4*clip((t-{a:.3f})/{max(b - a, 1e-3):.3f},0,1))"
    return _zoom(f"1+{p['amount']:.3f}*if(gte(t,{a:.3f}),{decay},0)", w, h)


def zoom_bounce(p, d, w, h):
    a, b = _win(p, d)
    return _zoom(
        f"1+{p['amount']:.3f}*if(between(t,{a:.3f},{b:.3f}),sin(PI*(t-{a:.3f})/{max(b - a, 1e-3):.3f}),0)",
        w,
        h,
    )


def shake(p, d, w, h):
    """Handheld/impact shake: overscan 8 % and move the crop window with decaying sines."""
    a, b = _win(p, d)
    amp = p["amount"] * w * 0.04
    env = f"if(between(t,{a:.3f},{b:.3f}),exp(-{p['decay']:.2f}*(t-{a:.3f})),0)"
    fx, fy = p["freq"], p["freq"] * 1.37
    return (
        f"scale=ceil(iw*1.08/2)*2:ceil(ih*1.08/2)*2,"
        f"crop={w}:{h}:'(iw-{w})/2+{amp:.1f}*{env}*sin(2*PI*{fx:.2f}*t)':'(ih-{h})/2+{amp:.1f}*{env}*sin(2*PI*{fy:.2f}*t+1.1)'"
    )


def pan(p, d, w, h):
    """Ken-Burns pan across an overscanned frame (direction: -1 left, +1 right)."""
    a, b = _win(p, d)
    over = 1 + p["amount"]
    return (
        f"scale=ceil(iw*{over:.3f}/2)*2:ceil(ih*{over:.3f}/2)*2,"
        f"crop={w}:{h}:'(iw-{w})*(0.5+0.5*{p['direction']:.0f}*(2*{_ease(a, b)}-1))':'(ih-{h})/2'"
    )


def rotate(p, d, w, h):
    a, b = _win(p, d)
    ang = f"{p['degrees']:.2f}*PI/180*{_ease(a, b)}"
    return f"scale=ceil(iw*1.25/2)*2:ceil(ih*1.25/2)*2,rotate='{ang}':ow={w}:oh={h}:c=black"


def whip_pan(p, d, w, h):
    """Fast lateral move with directional blur over a short window (use at the end/start of a segment)."""
    a, b = _win(p, d)
    return (
        f"scale=ceil(iw*1.3/2)*2:ceil(ih*1.3/2)*2,"
        f"crop={w}:{h}:'(iw-{w})/2+(iw-{w})/2*{p['direction']:.0f}*{_ease(a, b)}':'(ih-{h})/2',"
        f"dblur=angle=0:radius={p['blur']:.0f}:{_enable(p, d)}"
    )


# --- blur --------------------------------------------------------------------------------------------------------
def gaussian_blur(p, d, w, h):
    return f"gblur=sigma={p['sigma']:.1f}:{_enable(p, d)}"


def motion_blur(p, d, w, h):
    """Average each frame with its predecessors (chained tblend; tmix with a time window corrupted colour)."""
    en = _enable(p, d)
    return (
        "format=gbrp,"
        + ",".join([f"tblend=all_mode=average:{en}"] * (int(p["frames"]) - 1))
        + ",format=yuv420p"
    )


def directional_blur(p, d, w, h):
    return f"dblur=angle={p['angle']:.0f}:radius={p['radius']:.0f}:{_enable(p, d)}"


def blur_reveal(p, d, w, h):
    """Starts blurred and sharpens over the window (blur-to-sharp)."""
    a, b = _win(p, d)
    # gblur sigma cannot vary per frame; step it in 4 windows for a visible ramp
    steps = []
    for i in range(4):
        s0 = a + (b - a) * i / 4
        steps.append(
            f"gblur=sigma={p['sigma'] * (1 - i / 4):.1f}:enable='between(t,{s0:.3f},{s0 + (b - a) / 4:.3f})'"
        )
    return ",".join(steps)


def zoom_blur(p, d, w, h):
    a, b = _win(p, d)
    smear = motion_blur({"frames": 3, "at": a, "dur": b - a}, d, w, h)
    return f"{punch_zoom({'amount': p['amount'], 'at': a, 'dur': b - a}, d, w, h)},{smear}"


# --- impact / light ----------------------------------------------------------------------------------------------
def flash(p, d, w, h):
    """White (+) or black (−) flash: brightness spike with a fast exponential decay."""
    a, b = _win(p, d)
    sign = 1 if p["white"] >= 0.5 else -1
    return f"eq=brightness='{sign * p['amount']:.2f}*if(gte(t,{a:.3f}),exp(-(t-{a:.3f})/{max((b - a) / 3, 0.01):.3f}),0)':eval=frame"


def rgb_split(p, d, w, h):
    n = int(p["pixels"])
    return f"rgbashift=rh=-{n}:bh={n}:rv={n // 3}:bv=-{n // 3}:{_enable(p, d)}"


def glitch(p, d, w, h):
    n = int(p["pixels"])
    return f"rgbashift=rh=-{n}:bv={n // 2}:gh={n // 3}:{_enable(p, d)},noise=alls=40:allf=t:{_enable(p, d)}"


def contrast_snap(p, d, w, h):
    return f"eq=contrast={1 + p['amount']:.2f}:saturation={1 + p['amount'] / 2:.2f}:{_enable(p, d)}"


def bright_pulse(p, d, w, h):
    a, b = _win(p, d)
    return f"eq=brightness='{p['amount']:.2f}*if(between(t,{a:.3f},{b:.3f}),sin(PI*(t-{a:.3f})/{max(b - a, 1e-3):.3f}),0)':eval=frame"


def vignette(p, d, w, h):
    return f"vignette=angle={p['angle']:.2f}"


def grain(p, d, w, h):
    return f"noise=alls={p['amount']:.0f}:allf=t"


def grade(p, d, w, h):
    """Warm (+) / cool (−) grade with contrast and saturation."""
    k = p["warmth"]
    return (
        f"eq=contrast={p['contrast']:.2f}:saturation={p['saturation']:.2f},"
        f"colorbalance=rs={0.08 * k:.3f}:bs={-0.08 * k:.3f}:rm={0.05 * k:.3f}:bm={-0.05 * k:.3f}"
    )


def glow(p, d, w, h):
    # blend in RGB: a screen blend on YUV planes tints the picture magenta
    return (
        f"format=gbrp,split[g0][g1];[g1]gblur=sigma={p['radius']:.0f}[g2];"
        f"[g0][g2]blend=all_mode=screen:all_opacity={p['amount']:.2f},format=yuv420p"
    )


def vhs(p, d, w, h):
    return "rgbashift=rh=-3:bh=3,noise=alls=18:allf=t,eq=saturation=1.25:contrast=1.1,gblur=sigma=0.6"


def black_white(p, d, w, h):
    return f"hue=s=0:{_enable(p, d)}"


# --- 2.0 additions -----------------------------------------------------------------------------------------------
def wobble(p, d, w, h):
    """Decaying rotational wobble (impact/handheld feel) inside an overscanned frame."""
    a, b = _win(p, d)
    env = f"if(between(t,{a:.3f},{b:.3f}),exp(-{p['decay']:.2f}*(t-{a:.3f})),0)"
    return (f"scale=ceil(iw*1.14/2)*2:ceil(ih*1.14/2)*2,"
            f"rotate='{p['degrees']:.2f}*PI/180*{env}*sin(2*PI*{p['freq']:.2f}*t)':ow={w}:oh={h}:c=black")


def crash_zoom(p, d, w, h):
    """Very fast zoom in that holds (crash zoom), eased over a short window."""
    a, b = _win(p, d)
    x = f"clip((t-{a:.3f})/{max(b - a, 1e-3):.3f},0,1)"
    return _zoom(f"1+{p['amount']:.3f}*(1-pow(1-{x},3))", w, h)


def tilt(p, d, w, h):
    """Vertical camera tilt across an overscanned frame (direction: -1 up, +1 down)."""
    a, b = _win(p, d)
    over = 1 + p["amount"]
    return (f"scale=ceil(iw*{over:.3f}/2)*2:ceil(ih*{over:.3f}/2)*2,"
            f"crop={w}:{h}:'(iw-{w})/2':'(ih-{h})*(0.5+0.5*{p['direction']:.0f}*(2*{_ease(a, b)}-1))'")


def drift(p, d, w, h):
    """Slow floating camera (gentle elliptical drift) for calm shots."""
    amp = p["amount"] * min(w, h) * 0.05
    return (f"scale=ceil(iw*1.1/2)*2:ceil(ih*1.1/2)*2,"
            f"crop={w}:{h}:'(iw-{w})/2+{amp:.1f}*sin(2*PI*t/{max(d, 1):.2f})':'(ih-{h})/2+{amp:.1f}*cos(2*PI*t/{max(d, 1):.2f})'")


def light_leak(p, d, w, h):
    """Warm light leak sweeping across the frame, screen-blended (drawn at low resolution, then scaled)."""
    a, b = _win(p, d)
    pos = f"(T-{a:.3f})/{max(b - a, 1e-3):.3f}"
    blob = f"exp(-(pow(X-W*(-0.2+1.4*{pos}),2)+pow(Y-H*0.35,2))/(W*W*0.09))"
    return (f"format=gbrp,split[g0][g1];[g1]scale=90:160,geq=r='255*{blob}':g='150*{blob}':b='60*{blob}',"
            f"scale={w}:{h},eq=brightness=0[g2];[g0][g2]blend=all_mode=screen:all_opacity={p['amount']:.2f}:{_enable(p, d)},format=yuv420p")


def bloom(p, d, w, h):
    """Bloom: only the highlights are blurred and screened back (glow blurs everything)."""
    return (f"format=gbrp,split[g0][g1];[g1]curves=all='0/0 {p['threshold']:.2f}/0 1/1',gblur=sigma={p['radius']:.0f}[g2];"
            f"[g0][g2]blend=all_mode=screen:all_opacity={p['amount']:.2f},format=yuv420p")


def color_pulse(p, d, w, h):
    a, b = _win(p, d)
    return f"hue=h='{p['degrees']:.0f}*if(between(t,{a:.3f},{b:.3f}),sin(PI*(t-{a:.3f})/{max(b - a, 1e-3):.3f}),0)':s='1+{p['saturation']:.2f}*if(between(t,{a:.3f},{b:.3f}),1,0)'"


def exposure(p, d, w, h):
    return f"exposure=exposure={p['ev']:.2f}:{_enable(p, d)}"


def focus_blur(p, d, w, h):
    """Background/edge blur with a sharp centre (shallow depth-of-field look), radial mask at low resolution."""
    mask = f"255*clip((hypot(X-W/2,Y-H*{p['centre_y']:.2f})/(H*{p['radius']:.2f})-0.5)*2,0,1)"
    return (f"format=gbrp,split=3[g0][g1][g3];[g1]gblur=sigma={p['sigma']:.0f}[g2];"
            f"[g3]scale=90:160,geq=r='{mask}':g='{mask}':b='{mask}',scale={w}:{h}[g4];"
            f"[g0][g2][g4]maskedmerge,format=yuv420p")


def edge_glow(p, d, w, h):
    """Glowing outline around the subject's edges (product highlight)."""
    return (f"format=gbrp,split[g0][g1];[g1]edgedetect=low=0.08:high=0.25:mode=colormix,gblur=sigma={p['radius']:.1f},"
            f"eq=brightness=0.1:saturation=2[g2];[g0][g2]blend=all_mode=screen:all_opacity={p['amount']:.2f}:{_enable(p, d)},format=yuv420p")


def strobe(p, d, w, h):
    """Controlled strobe: brightness steps at ≤ 3 Hz (photosensitivity limit) inside the window."""
    a, b = _win(p, d)
    return f"eq=brightness='{p['amount']:.2f}*if(between(t,{a:.3f},{b:.3f}),lt(mod(t-{a:.3f},1/{p['freq']:.2f}),0.5/{p['freq']:.2f}),0)':eval=frame"


EFFECTS: dict[str, Effect] = {
    e.id: e
    for e in [
        Effect(
            "push_in",
            "camera",
            "Slow eased push towards the centre",
            {"amount": Param(0.02, 0.5, 0.12)},
            push_in,
            keyframed=True,
        ),
        Effect(
            "pull_out",
            "camera",
            "Eased pull back from a punched-in frame",
            {"amount": Param(0.02, 0.5, 0.12)},
            pull_out,
            keyframed=True,
        ),
        Effect(
            "punch_zoom",
            "camera",
            "Instant zoom on a hit, eased back",
            {"amount": Param(0.05, 0.6, 0.25), "dur": Param(0.1, 1.5, 0.35)},
            punch_zoom,
            keyframed=True,
            tags=("beat",),
        ),
        Effect(
            "zoom_bounce",
            "camera",
            "Zoom in and back within the window",
            {"amount": Param(0.05, 0.4, 0.15), "dur": Param(0.15, 1.0, 0.4)},
            zoom_bounce,
            keyframed=True,
            tags=("beat",),
        ),
        Effect(
            "shake",
            "camera",
            "Decaying camera shake (impact/handheld)",
            {
                "amount": Param(0.1, 1.0, 0.5),
                "freq": Param(2, 30, 14),
                "decay": Param(0, 20, 6),
                "dur": Param(0.1, 2.0, 0.4),
            },
            shake,
            tags=("beat",),
        ),
        Effect(
            "pan",
            "camera",
            "Ken-Burns pan across the frame",
            {"amount": Param(0.05, 0.5, 0.2), "direction": Param(-1, 1, 1)},
            pan,
            keyframed=True,
        ),
        Effect("rotate", "camera", "Eased roll", {"degrees": Param(-15, 15, 4)}, rotate, keyframed=True),
        Effect(
            "whip_pan",
            "camera",
            "Fast lateral whip with directional blur",
            {"direction": Param(-1, 1, 1), "blur": Param(5, 60, 30), "dur": Param(0.08, 0.5, 0.2)},
            whip_pan,
            tags=("transition",),
        ),
        Effect(
            "gaussian_blur",
            "blur",
            "Gaussian blur over the window",
            {"sigma": Param(1, 40, 8)},
            gaussian_blur,
        ),
        Effect("motion_blur", "blur", "Frame-blend motion blur", {"frames": Param(2, 8, 3)}, motion_blur),
        Effect(
            "directional_blur",
            "blur",
            "Directional blur",
            {"angle": Param(0, 360, 0), "radius": Param(2, 60, 15)},
            directional_blur,
        ),
        Effect(
            "blur_reveal",
            "blur",
            "Blurred to sharp",
            {"sigma": Param(4, 40, 20), "dur": Param(0.2, 2.0, 0.6)},
            blur_reveal,
        ),
        Effect(
            "zoom_blur",
            "blur",
            "Punch zoom with frame-blend smear",
            {"amount": Param(0.05, 0.5, 0.2), "dur": Param(0.1, 0.8, 0.3)},
            zoom_blur,
            tags=("beat",),
        ),
        Effect(
            "flash",
            "impact",
            "White or black flash with fast decay",
            {"amount": Param(0.2, 1.0, 0.7), "white": Param(0, 1, 1), "dur": Param(0.05, 0.6, 0.18)},
            flash,
            photosensitive=True,
            tags=("beat",),
        ),
        Effect(
            "rgb_split",
            "impact",
            "RGB channel split",
            {"pixels": Param(4, 60, 22), "dur": Param(0.05, 1.0, 0.2)},
            rgb_split,
            tags=("beat",),
        ),
        Effect(
            "glitch",
            "impact",
            "Channel offsets with noise burst",
            {"pixels": Param(4, 40, 14), "dur": Param(0.05, 0.6, 0.15)},
            glitch,
            photosensitive=True,
            tags=("beat",),
        ),
        Effect(
            "contrast_snap",
            "impact",
            "High-contrast snap",
            {"amount": Param(0.1, 1.0, 0.4), "dur": Param(0.05, 1.0, 0.2)},
            contrast_snap,
            tags=("beat",),
        ),
        Effect(
            "bright_pulse",
            "impact",
            "Brightness pulse",
            {"amount": Param(0.05, 0.5, 0.2), "dur": Param(0.1, 1.0, 0.3)},
            bright_pulse,
            tags=("beat",),
        ),
        Effect("vignette", "light", "Lens vignette", {"angle": Param(0.1, 1.2, 0.5)}, vignette),
        Effect("grain", "light", "Film grain", {"amount": Param(2, 40, 10)}, grain),
        Effect(
            "grade",
            "light",
            "Warm/cool grade with contrast and saturation",
            {"warmth": Param(-1, 1, 0.3), "contrast": Param(0.7, 1.6, 1.08), "saturation": Param(0, 2, 1.1)},
            grade,
        ),
        Effect(
            "glow",
            "light",
            "Bloom: blurred copy screened on top",
            {"radius": Param(4, 60, 18), "amount": Param(0.1, 0.9, 0.35)},
            glow,
        ),
        Effect("vhs", "light", "VHS look (chroma shift, grain, soft)", {}, vhs),
        Effect("black_white", "light", "Desaturate over the window", {}, black_white),
        Effect("wobble", "camera", "Decaying rotational wobble",
               {"degrees": Param(0.5, 8, 3), "freq": Param(2, 14, 7), "decay": Param(0, 12, 4), "dur": Param(0.1, 2, 0.5)},
               wobble, tags=("beat",)),
        Effect("crash_zoom", "camera", "Very fast zoom in that holds", {"amount": Param(0.1, 0.8, 0.35), "dur": Param(0.08, 0.6, 0.18)},
               crash_zoom, keyframed=True, tags=("beat",)),
        Effect("tilt", "camera", "Vertical camera tilt", {"amount": Param(0.05, 0.5, 0.2), "direction": Param(-1, 1, 1)}, tilt, keyframed=True),
        Effect("drift", "camera", "Slow floating camera drift", {"amount": Param(0.1, 1, 0.4)}, drift, keyframed=True),
        Effect("light_leak", "light", "Warm light leak sweeping across", {"amount": Param(0.1, 0.9, 0.5), "dur": Param(0.3, 3, 1.2)},
               light_leak, keyframed=True),
        Effect("bloom", "light", "Highlight bloom", {"threshold": Param(0.4, 0.95, 0.7), "radius": Param(6, 60, 24), "amount": Param(0.1, 0.9, 0.5)}, bloom),
        Effect("color_pulse", "light", "Hue/saturation pulse", {"degrees": Param(-90, 90, 30), "saturation": Param(0, 1, 0.4), "dur": Param(0.1, 1.5, 0.4)},
               color_pulse, tags=("beat",)),
        Effect("exposure", "light", "Exposure change over the window", {"ev": Param(-2, 2, 0.4)}, exposure),
        Effect("focus_blur", "blur", "Sharp centre, blurred surroundings (shallow focus)",
               {"sigma": Param(2, 30, 10), "radius": Param(0.2, 0.8, 0.45), "centre_y": Param(0.2, 0.8, 0.45)}, focus_blur),
        Effect("edge_glow", "composite", "Glowing outline around edges (product highlight)", {"radius": Param(0.5, 6, 2), "amount": Param(0.2, 1, 0.6)},
               edge_glow),
        Effect("strobe", "impact", "Controlled strobe (≤ 3 Hz)", {"amount": Param(0.1, 0.6, 0.35), "freq": Param(1, 3, 3), "dur": Param(0.2, 1.5, 0.6)},
               strobe, photosensitive=True),
        # drawn frame by frame with OpenCV + local ONNX models (composite.py), before the FFmpeg effects
        Effect("subject_pop", "composite", "Subject cutout: sharp subject, blurred/darkened background, glowing outline",
               {"blur": Param(2, 30, 9), "darken": Param(0, 0.8, 0.45), "outline": Param(0, 1, 1)}, lambda p, d, w, h: "",
               renderer="opencv"),
        Effect("depth_parallax", "composite", "2.5D camera move from a depth map (stills)",
               {"amount": Param(0.01, 0.1, 0.04), "direction": Param(-1, 1, 1)}, lambda p, d, w, h: "", renderer="opencv"),
    ]
}

# Transitions between base-picture segments map onto FFmpeg xfade (61 built-in types).
TRANSITIONS: dict[str, str] = {
    "cut": "",
    "crossfade": "fade",
    "dip_black": "fadeblack",
    "dip_white": "fadewhite",
    "flash": "fadewhite",
    "swipe_left": "slideleft",
    "swipe_right": "slideright",
    "swipe_up": "slideup",
    "wipe": "wipeleft",
    "zoom_through": "zoomin",
    "whip": "hblur",
    "blur": "hblur",
    "radial": "radial",
    "circle_reveal": "circleopen",
    "pixelize": "pixelize",
    "smooth_left": "smoothleft",
    "squeeze": "squeezeh",
    "diagonal": "diagtl",
    "cover_up": "coverup",
    "reveal_down": "revealdown",
    "slice": "hlslice",
    "wind": "hrwind",
    "dissolve": "dissolve",
    "circle_close": "circleclose",
    "open_vertical": "vertopen",
    "open_horizontal": "horzopen",
    "smooth_up": "smoothup",
    "rect_crop": "rectcrop",
    "distance": "distance",
    "fade_grays": "fadegrays",
    "squeeze_vertical": "squeezev",
    "wipe_up": "wipeup",
    "slide_down": "slidedown",
}


def resolve(effect_id: str, params: dict | None = None) -> tuple[Effect, dict]:
    """Effect + parameters clamped to their declared range (unknown params dropped, `at`/`dur` kept)."""
    if effect_id not in EFFECTS:
        raise KeyError(f"unknown effect {effect_id}")
    e = EFFECTS[effect_id]
    given = params or {}
    out = {k: min(max(float(given.get(k, p.default)), p.lo), p.hi) for k, p in e.params.items()}
    for k in ("at", "dur"):
        if k in given:
            out[k] = max(0.0, float(given[k]))
    return e, out


def validate(applied: list[tuple[str, dict]], duration: float) -> list[str]:
    """Problems with a segment's effect list (photosensitivity rate, unknown ids)."""
    issues = []
    flashes = [p.get("at", 0) for i, p in applied if i in EFFECTS and EFFECTS[i].photosensitive]
    if flashes and len(flashes) / max(duration, 1e-3) > 3:
        issues.append(f"{len(flashes)} flashing effects in {duration:.2f} s exceeds 3 per second")
    issues += [f"unknown effect {i}" for i, _ in applied if i not in EFFECTS]
    return issues
