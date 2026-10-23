"""Execute an edit plan: base picture (FFmpeg) + sound (separate) → mux → MP4. Overlays (Hyperframes) are layered by
`overlay.py` when the plan has graphics or captions; this module stays the footage path of the renderer router."""

from pathlib import Path

from app.services.editing import audio, base
from app.services.music import score


def to_segments(plan: dict, clip_paths: list[Path]) -> list[base.Segment]:
    segs = []
    sp = plan["segments"]
    for i, s in enumerate(sp):
        td_in = sp[i - 1]["transition_s"] if i else 0.0
        td_out = s["transition_s"]
        slot = s["slot"][1] - s["slot"][0]
        dur = slot + td_in / 2 + td_out / 2  # transitions are centred on the cut
        need = (
            (s["src_out"] - s["src_in"]) * dur / slot
        )  # the planner's range, grown by the transition overlap
        centre = (s["src_in"] + s["src_out"]) / 2
        src_in = max(0.0, centre - need / 2)
        segs.append(
            base.Segment(
                asset=clip_paths[s["clip"]],
                src_in=src_in,
                src_out=src_in + need,
                duration=dur,
                focus_x=s["focus"][0],
                focus_y=s["focus"][1],
                zoom=s.get("zoom", 1.0),
                speed_ramp=[tuple(p) for p in s["speed_ramp"]],
                reverse=s.get("reverse", False),
                still=s.get("still", False),
                effects=[(e, p) for e, p in s["effects"]],
                transition_out=s["transition_out"],
                transition_dur=td_out,
            )
        )
    return segs


def clamp_sources(segs: list[base.Segment], durations: list[float | None]) -> None:
    """Keep every source range inside its clip (a shift near the end slides the window back)."""
    for s, cd in zip(segs, durations, strict=True):
        if s.still or not cd:
            continue
        span = s.src_out - s.src_in
        if span > cd:
            s.src_in, s.src_out = 0.0, cd
        elif s.src_out > cd:
            s.src_in, s.src_out = cd - span, cd


def render_plan(
    plan: dict,
    clip_paths: list[Path],
    clip_durations: list[float | None],
    work: Path,
    out: Path,
    music_path: Path | None = None,
    voice_path: Path | None = None,
    quality: str = "looks",
) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    segs = to_segments(plan, clip_paths)
    clamp_sources(segs, [clip_durations[s["clip"]] for s in plan["segments"]])
    picture = base.render_base(segs, work / "picture", plan["width"], plan["height"], plan["fps"], quality)
    dur = plan["duration"]
    synthesized = False
    if music_path is None and plan.get("generate_score"):
        music_path = score.write_wav(
            work / "score.wav",
            score.generate(plan["generate_score"], plan["bpm"], dur + plan["music_start"] + 1),
        )
        synthesized = True
    cues = [audio.Cue(c["kind"], c["at"], c.get("gain_db", -6)) for c in plan["cues"]]
    sfx = audio.sfx_track(cues, dur, work / "sfx.wav") if cues else None
    mixed = audio.mix(
        dur, work / "mix.wav", music=music_path, music_start=plan["music_start"], voice=voice_path, sfx=sfx
    )
    audio.mux(picture, mixed, out)
    return {"output": str(out), "segments": len(segs), "synthesized_score": synthesized}
