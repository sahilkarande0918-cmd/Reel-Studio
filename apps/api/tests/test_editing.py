"""Mode B editing engine: planner, effects registry, pacing, beat helpers (no rendering; see effects_gallery.py and
auto_edit.py for the measured render checks)."""

from app.services.editing import effects as fx
from app.services.editing import pacing, planner
from app.services.editing.base import Segment, snap_plan, total_duration
from app.services.music.beats import cut_offsets, snap


def clips(n_moments: int = 3, n: int = 2, dur: float = 60.0) -> list[dict]:
    return [
        {
            "kind": "video",
            "duration_s": dur,
            "motion_mean": 1.0,
            "focus": [0.5, 0.5],
            "moments": [
                {"start_s": 5 + 10 * k, "end_s": 6.5 + 10 * k, "score": 1 - 0.1 * k, "focus": [0.4, 0.6]}
                for k in range(n_moments)
            ],
        }
        for _ in range(n)
    ]


def music(bpm: float = 120.0, length: float = 40.0) -> dict:
    step = 60 / bpm
    beats = [round(i * step, 4) for i in range(int(length / step))]
    return {
        "duration_s": length,
        "tempo_bpm": bpm,
        "beats": beats,
        "downbeats": beats[::4],
        "accents": beats[1::2],
        "drops": [8.0],
    }


def test_cuts_land_on_the_beat_grid_and_fill_the_duration():
    p = planner.plan(clips(), pacing.PROFILES["phonk"], 12.0, music())
    cuts = [s["slot"][0] for s in p["segments"]][1:]
    assert all(abs(o["offset_ms"]) <= 17 for o in cut_offsets(cuts, p["beats"]))  # within half a frame
    assert p["segments"][-1]["slot"][1] == 12.0 and p["segments"][0]["slot"][0] == 0.0
    assert p["music_start"] == 4.0  # drop at 8 s lands 30 % into a 12 s edit (snapped to a downbeat)


def test_short_footage_is_reused_with_a_different_treatment():
    p = planner.plan(clips(n_moments=1, n=2), pacing.PROFILES["phonk"], 12.0, music())
    reused = [s for s in p["segments"] if s["reuse"].get("reuse")]
    assert reused and p["reused_shots"] == len(reused)
    assert all(s["zoom"] > 1.0 for s in reused)  # reuse is reframed, never an identical repeat


def test_flashes_are_rate_limited():
    p = planner.plan(clips(), pacing.PROFILES["phonk"], 12.0, music())
    flashes = sorted(
        s["slot"][0] + e[1].get("at", 0) for s in p["segments"] for e in s["effects"] if e[0] == "flash"
    )
    assert all(b - a >= 1.0 - 1e-6 for a, b in zip(flashes, flashes[1:], strict=False))


def test_transitions_are_centred_so_total_length_is_exact():
    segs = [Segment(None, 0, 1, 1.0, transition_out="whip", transition_dur=0.2), Segment(None, 0, 1, 1.0)]  # type: ignore[arg-type]
    snap_plan(segs, 30)
    assert abs(total_duration(segs) - 1.8) < 1e-9


def test_effect_params_are_clamped_and_unknown_effects_rejected():
    _, p = fx.resolve("punch_zoom", {"amount": 9, "at": 0.4})
    assert p["amount"] == fx.EFFECTS["punch_zoom"].params["amount"].hi and p["at"] == 0.4
    assert fx.validate([("flash", {"at": i * 0.1}) for i in range(5)], 1.0)  # 5 flashes in 1 s
    try:
        fx.resolve("capcut_magic")
        raise AssertionError("unknown effect accepted")
    except KeyError:
        pass


def test_every_effect_builds_a_filter():
    for eid in fx.EFFECTS:
        e, p = fx.resolve(eid, {"at": 0.2})
        assert e.build(p, 1.5, 540, 960).strip(), eid


def test_ramp_consumes_the_integral_of_its_speed():
    assert abs(planner.ramp_factor([(0, 2.0), (1, 2.0)]) - 2.0) < 1e-9
    assert 0.5 < planner.ramp_factor(planner.RAMP_FSF) < 1.5


def test_prompt_keywords_pick_a_profile():
    assert pacing.guess("Make a professional phonk edit") == "phonk"
    assert pacing.guess("premium SaaS advertisement for our app") == "tech_ad"
    assert pacing.guess("just edit it") == "clean_commercial"


def test_snap_moves_to_beat_then_frame():
    assert snap(1.03, [1.0, 1.5]) == 1.0
    assert snap(1.3, [1.0, 1.5]) == round(round(1.3 * 30) / 30, 4)  # too far from a beat: frame grid only
