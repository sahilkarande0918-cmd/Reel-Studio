"""Reference style transfer: turn a measured reference profile (`reference/analyzer.py`) into a pacing profile.

What transfers (all measured, listed in `evidence`): shot lengths in beats after the drop, the opening hook length
(first shot vs the reference's drop), the transition mix, flash colour and rate, and how much the camera punches in.
Not yet transferred: colour grade. Never transferred: the reference's footage, music, text or branding.
"""

from dataclasses import replace

from app.services.editing.pacing import Profile

KIND = {
    "whip/motion-blur": "whip",
    "flash": "flash",
    "zoom-through": "zoom_through",
    "dip-to-black": "dip_black",
    "hard cut": "cut",
}


def whole_beat_cycle(values: list[float]) -> tuple[float, ...]:
    """Half-beat shots only in pairs that land back on a whole beat (0.5+0.5, 1.5+2.5); a lone half beat is rounded
    (half up for the first, so a 3.5 opener does not push every later cut onto the off-beat — seen: HP Victus edit,
    every cut 333 ms off at 90 BPM)."""
    out, i = [], 0
    while i < len(values):
        v = values[i]
        if v % 1 and i + 1 < len(values) and values[i + 1] % 1:
            out += [v, values[i + 1]]
            i += 2
            continue
        out.append(float(max(1, round(v + 0.01))) if v % 1 else v)
        i += 1
    return tuple(out)


def from_reference(ref: dict, base: Profile) -> tuple[Profile, list[str]]:
    ev: list[str] = []
    bpm = (ref.get("beat_sync") or {}).get("tempo_bpm") or (ref.get("music") or {}).get("tempo_bpm")
    shots = ref.get("shots", [])
    drops = (ref.get("music") or {}).get("drops", [])
    dur = ref["meta"]["duration_s"]
    p = base
    if bpm and len(shots) > 2:
        beat = 60 / bpm
        first = shots[0]["duration_s"]
        # hook: the reference holds its first shot through the build and cuts on the drop
        if drops and abs(shots[0]["end_s"] - drops[0]) < 0.4:
            p = replace(p, hook_share=round(first / dur, 3))
            ev.append(
                f"Opening shot held {first:.1f} s ({first / dur:.0%} of the reel) until the drop at {drops[0]:.2f} s"
            )
        cycle = whole_beat_cycle([max(0.5, min(4.0, round(s["duration_s"] / beat * 2) / 2)) for s in shots[1:]])
        if cycle:
            p = replace(p, cut_beats=cycle)
            ev.append(f"Shot lengths after the drop, in beats at {bpm} BPM: {list(cycle)}")
    kinds = [KIND.get(t["kind"], "cut") for t in ref.get("transitions", [])]
    special = [k for k in kinds if k != "cut"]
    if kinds:
        order = sorted(set(special), key=lambda k: -special.count(k))
        if order:
            p = replace(
                p,
                transitions=tuple(order) + ("cut",),
                transition_every=max(1, round(len(kinds) / len(special))),
            )
            ev.append(
                f"Transitions: {', '.join(f'{k} ×{special.count(k)}' for k in order)} of {len(kinds)} cuts"
            )
    flashes = ref.get("flashes", [])
    if flashes:
        black = sum(1 for f in flashes if f["kind"] == "black")
        white = 0 if black > len(flashes) / 2 else 1
        p = replace(p, fx_params={**p.fx_params, "flash": {"white": white, "amount": 0.75}})
        ev.append(
            f"{len(flashes)} flashes, {black} black / {len(flashes) - black} white → {'black' if not white else 'white'} flashes"
        )
    m = ref.get("motion", {})
    if m.get("zoom_in_share", 0) + m.get("zoom_out_share", 0) > 0.2:
        hits = ("punch_zoom", "flash", "zoom_blur", "shake", "punch_zoom", "rgb_split")
        p = replace(p, hit_fx=hits, hit_every=1, intensity=max(p.intensity, 0.85))
        ev.append(
            f"Constant punch-in/out: zoom in {m['zoom_in_share']:.0%} / out {m['zoom_out_share']:.0%} of frames"
        )
    return replace(p, id=f"{base.id}+reference", label=f"{base.label} (reference style)"), ev
