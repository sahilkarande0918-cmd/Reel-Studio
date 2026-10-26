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
        if e.renderer == "ffmpeg":  # OpenCV composites are drawn by composite.py, not a filter string
            assert e.build(p, 1.5, 540, 960).strip(), eid


def test_composites_are_budgeted_and_routed_by_shot_kind():
    segs = [{"slot": [i, i + 1 + (i == 2)], "still": i == 4, "effects": [["subject_pop", {}], ["depth_parallax", {}]]}
            for i in range(5)]
    planner.limit_composites(segs, cutout_ok=True)
    pops = [i for i, s in enumerate(segs) if any(e[0] == "subject_pop" for e in s["effects"])]
    assert len(pops) == planner.COMPOSITE_BUDGET and 2 in pops and 4 not in pops
    assert [i for i, s in enumerate(segs) if any(e[0] == "depth_parallax" for e in s["effects"])] == [4]


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


def test_reference_style_transfers_hook_flashes_and_shot_lengths():
    from app.services.editing import style_transfer

    ref = {
        "meta": {"duration_s": 14.0},
        "music": {"tempo_bpm": 120.0, "drops": [3.5]},
        "beat_sync": {"tempo_bpm": 120.0},
        "shots": [{"duration_s": 3.5, "end_s": 3.5}]
        + [{"duration_s": 1.0, "end_s": 4.5 + i} for i in range(5)],
        "transitions": [
            {"kind": "whip/motion-blur"},
            {"kind": "hard cut"},
            {"kind": "flash"},
            {"kind": "whip/motion-blur"},
        ],
        "flashes": [{"t": 5.0, "kind": "black"}, {"t": 7.0, "kind": "black"}, {"t": 9.0, "kind": "white"}],
        "motion": {"zoom_in_share": 0.15, "zoom_out_share": 0.12},
    }
    prof, evidence = style_transfer.from_reference(ref, pacing.PROFILES["phonk"])
    assert prof.hook_share == 0.25 and prof.cut_beats == (2.0,) * 5
    assert prof.transitions[0] == "whip" and prof.fx_params["flash"]["white"] == 0
    assert len(evidence) >= 4
    p = planner.plan(clips(), prof, 12.0, music())
    assert p["segments"][1]["slot"][0] == 8.0 - p["music_start"]  # the first cut lands on the drop


def test_no_back_to_back_shots_from_one_clip_when_others_exist():
    clips = [{"kind": "video", "duration_s": 20, "moments": [{"start_s": i * 2, "end_s": i * 2 + 1.5, "score": 0.9 - i * 0.01,
              "focus": [0.5, 0.5]} for i in range(8)]}, {"kind": "video", "duration_s": 3, "moments": [
              {"start_s": 0, "end_s": 1.5, "score": 0.2, "focus": [0.5, 0.5]}]}]
    picks = planner.pick_sources(clips, [0.5] * 10, [False] * 10)
    assert all(a["clip"] != b["clip"] for a, b in zip(picks, picks[1:]))


def test_correct_beats_shift_and_tempo():
    from app.services.editing.planner import correct_beats

    m = {"beats": [0.5, 1.0, 1.5, 2.0], "downbeats": [0.5], "accents": [1.0], "drops": [1.5], "duration_s": 3.0}
    assert correct_beats(m) is m
    s = correct_beats(m, offset_ms=-100)
    assert s["beats"] == [0.4, 0.9, 1.4, 1.9] and s["drops"] == [1.4] and m["beats"][0] == 0.5
    t = correct_beats(m, bpm=60)
    assert t["beats"] == [0.5, 1.5, 2.5] and t["tempo_bpm"] == 60 and t["downbeats"] == [0.5]


def test_merge_lists_joins_split_steps_in_order():
    from app.services.editing.overlay import _G, merge_lists

    scenes = [_G("kinetic_title", 0.0, 2, {"text": "Reel Studio"}),
              _G("info_list", 0.12, 3, {"title": "Publish", "items": "4. publish"}),
              _G("info_list", 0.3, 3, {"title": "Upload", "items": "1. upload your clips"}),
              _G("info_list", 0.5, 3, {"title": "Director", "items": "2. AI director plans the edit|3) fine-tune"})]
    out = merge_lists(scenes, "Four steps")
    assert [g.template for g in out] == ["kinetic_title", "info_list"]
    assert out[1].fields == {"title": "Four steps", "items": "upload your clips|AI director plans the edit|fine-tune|publish"}
    assert out[1].at == 0.12 and out[1].duration_s == 9


def test_merge_lists_reads_step_numbers_from_titles():
    from app.services.editing.overlay import _G, merge_lists

    scenes = [_G("info_list", 0.125, 3, {"title": "Step 4: Publish", "items": "Publish to Instagram"}),
              _G("info_list", 0.45, 3, {"title": "Step 2: Plan", "items": "AI director plans the edit"}),
              _G("info_list", 1.0, 3, {"title": "Step 1: Upload", "items": "Upload your clips"})]
    out = merge_lists(scenes, "Reel Studio in 4 steps")
    assert out[0].fields["items"] == "Upload your clips|AI director plans the edit|Publish to Instagram"
    assert out[0].at == 0.125


def test_placeholder_fields_are_dropped():
    from app.services.editing.director import PLACEHOLDER

    assert all(PLACEHOLDER.match(v) for v in ["Button", "Call to action button", "Your brand name", "Headline"])
    assert not PLACEHOLDER.match("Try Reel Studio")


def test_prompt_structure_uses_only_the_requests_words():
    from app.services.editing.overlay import prompt_structure

    p = ("Animated infographic that explains Reel Studio in four steps: 1. Upload your clips, 2. The AI director plans the edit, "
         "3. Fine-tune in the editor, 4. Publish to Instagram. Kinetic title 'Reel Studio in 4 steps', a numbered info list, "
         "end with a call to action button 'Try Reel Studio'.")
    shots = [{"width": 1600, "height": 900}] * 4
    s = prompt_structure(p, shots, 20)
    assert [g.template for g in s] == ["kinetic_title", "info_list"] + ["browser_mockup"] * 4 + ["cta_button"]
    assert s[0].fields["text"] == "Reel Studio in 4 steps"
    assert s[1].fields["items"] == "Upload your clips|The AI director plans the edit|Fine-tune in the editor|Publish to Instagram"
    assert s[2].fields == {"media": "1", "title": "1. Upload your clips"} and s[-1].fields["button"] == "Try Reel Studio"
    assert prompt_structure("Make a phonk edit with 2 drops", shots, 20) is None


def test_before_after_request_gets_a_split_screen():
    from app.services.editing.overlay import before_after

    two = [{"width": 1080, "height": 1920}] * 2
    s = before_after("Before / after comparison reel of my room makeover", two, 15)
    assert s[0].template == "split_screen" and s[0].fields["media"] == "1 2" and s[0].duration_s == 9.0
    assert before_after("before/after", two[:1], 15) is None and before_after("phonk edit", two, 15) is None


def test_tracked_tag_follows_the_track():
    from app.services.rendering import motion

    item = {"id": "mg-0", "type": "motion", "start": 2.0, "duration": 1.0, "template": "tracked_tag", "fields": {"text": "₹499"},
            "media": [], "intensity": 0.6, "track": [[0, 0.5, 0.5], [0.5, 0.6, 0.5], [1.0, 0.7, 0.4]]}
    markup, js = motion.render(item, 0, {"w": 1080, "h": 1920})
    assert "₹499" in markup and "mg-pin" in markup
    assert 'x: 648.0, y: 960.0, duration: 0.500, ease: "none"}, 2.000' in js and "x: 756.0, y: 768.0" in js


def test_mix_is_exactly_the_edit_length_when_the_song_ends_early(tmp_path):
    import subprocess

    from app.services.editing import audio

    song = tmp_path / "song.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=2", "-ar", "48000", str(song)], check=True)
    out = audio.mix(3.0, tmp_path / "mix.wav", music=song)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                             capture_output=True, text=True).stdout)
    assert abs(d - 3.0) < 0.02, d


def test_photo_animation_prompt_and_analysis_come_from_the_photo():
    from app.services import i2v

    a = {"vlm": {"subject": "A woman holding a perfume bottle", "setting": "A sunlit balcony"}, "focus": [0.4, 0.5]}
    p = i2v.motion_prompt(a, "warm")
    assert p.startswith("A woman holding a perfume bottle. A sunlit balcony.") and "warm look" in p
    c = i2v.clip_analysis(a, portrait=True)
    assert c["kind"] == "video" and c["ai_generated"] and c["moments"][0]["focus"] == [0.4, 0.5] and c["height"] > c["width"]
