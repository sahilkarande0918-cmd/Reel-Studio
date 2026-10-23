"""Deterministic beat planner: analysed clips + beat grid + pacing profile → an executable edit plan.

The plan is plain JSON (segments, transitions, effects, SFX cues, music offset, reuse notes) so the AI Director can
read and adjust it, the editor can show it as a storyboard, and `render.py` turns it into an MP4. Every cut lands on a
beat (frame-snapped); a transition is centred on its beat (each neighbour overlaps by half of it), so total length is
exact and whoosh/flash peaks sit on the beat.

Footage reuse: moments are used best-first and spread across clips; when they run out a moment is reused with a
different treatment (offset range, punch-in, reframe, reverse, ramp) and the reuse is recorded, never hidden.
"""

from app.services.editing.pacing import Profile

RAMP_FSF = [(0.0, 1.8), (0.4, 0.35), (0.75, 0.35), (1.0, 2.2)]  # fast → slow → fast


def ramp_factor(ramp: list[tuple[float, float]], samples: int = 64) -> float:
    """Average speed of an eased ramp = source seconds consumed per output second."""
    pts = sorted(ramp)
    tot = 0.0
    for k in range(samples):
        u = (k + 0.5) / samples
        for (u0, v0), (u1, v1) in zip(pts, pts[1:], strict=False):
            if u0 <= u <= u1:
                x = (u - u0) / max(u1 - u0, 1e-6)
                tot += v0 + (v1 - v0) * x * x * (3 - 2 * x)
                break
    return tot / samples


def beat_grid(
    music: dict | None, bpm: float, duration: float
) -> tuple[list[float], list[float], list[float]]:
    """(beats, downbeats, accents) — from analysis, or a synthetic grid at `bpm` when there is no music."""
    if music and music.get("beats"):
        return music["beats"], music.get("downbeats") or music["beats"][::4], music.get("accents", [])
    step = 60 / bpm
    beats = [round(i * step, 4) for i in range(int((duration + 4) / step) + 1)]
    return beats, beats[::4], beats[::2]


def music_offset(
    music: dict | None,
    downbeats: list[float],
    duration: float,
    hook_share: float = 0.0,
    beats: list[float] | None = None,
) -> float:
    """Start the music so its first drop lands ~30 % into the edit (a hook that pays off), else on a downbeat.
    With a hook (reference style), the drop lands exactly where the held opening shot ends."""
    if not music or not downbeats:
        return 0.0
    for d in music.get("drops", []):
        if hook_share and beats:
            want = d - duration * hook_share
            start = min(beats, key=lambda b: abs(b - want))
            if start >= 0 and d - start > 1.0 and start + duration <= music["duration_s"]:
                return start
        want = d - duration * 0.3
        if want >= 0 and d + duration * 0.7 <= music["duration_s"]:
            return min(downbeats, key=lambda b: abs(b - want))
    return downbeats[0] if downbeats[0] < 2 else 0.0


def slots(
    beats: list[float],
    start: float,
    duration: float,
    profile: Profile,
    fps: int,
    hook_until: float | None = None,
) -> list[float]:
    """Cut times on the output clock (0 … duration), following the profile's cycle of shot lengths in beats.
    `hook_until`: one held opening shot, first cut exactly there (the drop)."""
    rel = [b - start for b in beats if start - 1e-6 <= b <= start + duration + 1e-6]
    if len(rel) < 2:
        return [0.0, duration]
    cuts, i, k = [0.0], 0, 0
    if hook_until and 1.0 < hook_until < duration - 1.0:
        i = min(range(len(rel)), key=lambda j: abs(rel[j] - hook_until))
        cuts.append(round(round(rel[i] * fps) / fps, 4))
    while True:
        n = profile.cut_beats[k % len(profile.cut_beats)]
        k += 1
        nxt = i + n
        if nxt >= len(rel) - 1:
            break
        t = rel[int(nxt)] if float(nxt).is_integer() else (rel[int(nxt)] + rel[int(nxt) + 1]) / 2
        if duration - t < 0.6:  # never leave a sliver at the end
            break
        cuts.append(round(round(t * fps) / fps, 4))
        i = nxt
    cuts.append(duration)
    return cuts


def pick_sources(
    clips: list[dict],
    durs: list[float],
    ramps: list[bool],
    weights: list[float] | None = None,
    first: int | None = None,
    last: int | None = None,
) -> list[dict]:
    """For each slot: clip index, source in/out, framing and any reuse treatment.
    `weights` scale each clip's moment scores (0 = never use); `first`/`last` pin the opening/closing clip."""
    w = weights or [1.0] * len(clips)
    pool = [
        {"clip": ci, **m, "score": m["score"] * w[ci], "uses": 0}
        for ci, c in enumerate(clips)
        for m in (
            c["moments"]
            or [
                {
                    "start_s": 0,
                    "end_s": c.get("duration_s") or 0,
                    "score": 0.1,
                    "focus": c.get("focus", [0.5, 0.5]),
                }
            ]
        )
        if w[ci] > 0
    ]
    pool.sort(key=lambda m: -m["score"])
    out, last_clip = [], None
    for i, d in enumerate(durs):
        need = d * (ramp_factor(RAMP_FSF) if ramps[i] else 1.0)
        fresh = [m for m in pool if m["uses"] == 0]
        cands = fresh or sorted(pool, key=lambda m: (m["uses"], -m["score"]))
        # prefer a different clip from the previous shot (variety), then the best score
        # never two shots of the same clip back to back (an invisible jump cut): a fresh moment of another clip,
        # else a reused moment of another clip, and only with a single usable clip the same one again
        m = (next((x for x in cands if x["clip"] != last_clip), None)
             or next((x for x in sorted(pool, key=lambda q: (q["uses"], -q["score"])) if x["clip"] != last_clip), None)
             or cands[0])
        pin = first if i == 0 else last if i == len(durs) - 1 and i else None
        if pin is not None:
            m = next((x for x in cands if x["clip"] == pin), None) or next((x for x in pool if x["clip"] == pin), m)
        c = clips[m["clip"]]
        still = c["kind"] == "image"
        cdur = c.get("duration_s") or 0
        treatment = {}
        if still:
            src_in, src_out = 0.0, need
            treatment = {"ken_burns": True}
        else:
            centre = (m["start_s"] + m["end_s"]) / 2
            if m["uses"]:  # reuse: shift the range and change the framing so it never reads as a loop
                shift = (-1) ** m["uses"] * min(need * 0.6, 1.2) * m["uses"]
                centre += shift
                treatment = {
                    "reuse": m["uses"],
                    "zoom": round(1.18 + 0.12 * (m["uses"] % 3), 2),
                    "range_shift_s": round(shift, 2),
                }
                if m["uses"] % 3 == 2 and c.get("motion_mean", 0) > 0.3:
                    treatment["reverse"] = True
            src_in = max(0.0, min(centre - need / 2, cdur - need))
            src_out = min(cdur, src_in + need)
            if src_out - src_in < need - 1e-3:  # clip shorter than the shot: play slower to fill it exactly
                treatment["stretch"] = round(need / max(src_out - src_in, 1e-3), 2)
        m["uses"] += 1
        last_clip = m["clip"]
        out.append(
            {
                "clip": m["clip"],
                "src_in": round(src_in, 3),
                "src_out": round(src_out, 3),
                "focus": m.get("focus", [0.5, 0.5]),
                "still": still,
                **treatment,
            }
        )
    return out


COMPOSITE_BUDGET = 2  # ponytail: subject cutouts run per frame on the CPU (~15 s per output second at 1080p)


def limit_composites(segments: list[dict], cutout_ok: bool) -> None:
    """Subject cutouts only on video shots, at most COMPOSITE_BUDGET per edit (the longest shots get them);
    depth parallax only on stills. Anything else becomes a push-in, so the plan never asks for the impossible."""
    pops = [i for i, s in enumerate(segments) if any(e[0] == "subject_pop" for e in s["effects"])]
    keep = set(sorted(pops, key=lambda i: segments[i]["slot"][0] - segments[i]["slot"][1])[:COMPOSITE_BUDGET]) if cutout_ok else set()
    for i, s in enumerate(segments):
        s["effects"] = [
            ["push_in", {"amount": 0.12}]
            if (e[0] == "subject_pop" and (i not in keep or s["still"])) or (e[0] == "depth_parallax" and not s["still"])
            else e
            for e in s["effects"]
        ]


def plan(
    clips: list[dict],
    profile: Profile,
    duration: float,
    music: dict | None = None,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
    weights: list[float] | None = None,
    first: int | None = None,
    last: int | None = None,
) -> dict:
    bpm = (music or {}).get("tempo_bpm") or profile.default_bpm
    beats, downbeats, accents = beat_grid(music, bpm, duration)
    start = music_offset(music, downbeats, duration, profile.hook_share, beats)
    drops_rel = [d - start for d in (music or {}).get("drops", []) if start < d < start + duration]
    hook = drops_rel[0] if profile.hook_share and drops_rel else None
    cuts = slots(beats, start, duration, profile, fps, hook)
    durs = [b - a for a, b in zip(cuts, cuts[1:], strict=False)]
    beat_len = 60 / bpm
    ramps = [profile.ramps and d >= 1.6 * beat_len and i % 3 == 1 for i, d in enumerate(durs)]
    srcs = pick_sources(clips, durs, ramps, weights, first, last)
    rel_acc = [a - start for a in accents if start <= a < start + duration]
    drop_rel = drops_rel
    k = profile.intensity
    from app.services.editing import composite

    depth_ok = composite.available("depth")
    segments, cues, last_flash = [], [], -9.0
    for i, (a, b) in enumerate(zip(cuts, cuts[1:], strict=False)):
        s = srcs[i]
        fxs: list[list] = []
        if hook and i == 0:  # the held hook builds with a slow push; hits start on the drop
            fxs.append(["push_in", {"amount": 0.18, "at": 0.0}])
        elif profile.hit_fx and i % profile.hit_every == 0:
            eid = profile.hit_fx[i % len(profile.hit_fx)]
            hits = [x - a for x in rel_acc if a + 0.05 <= x < b - 0.1]
            at = hits[0] if hits and eid != "push_in" else 0.0
            if eid == "flash" and (a + at) - last_flash < 1.0:
                eid = "punch_zoom"  # photosensitivity: at most one flash per second
            if eid == "flash":
                last_flash = a + at
            params = {"at": round(at, 3)}
            if eid in ("punch_zoom", "zoom_blur", "zoom_bounce"):
                params["amount"] = round(0.12 + 0.25 * k, 3)
            if eid == "push_in":
                params["amount"] = round(0.05 + 0.12 * k, 3)
            if eid == "shake":
                params.update({"amount": round(0.3 + 0.5 * k, 2), "dur": 0.35})
            params.update(profile.fx_params.get(eid, {}))
            fxs.append([eid, params])
        if any(abs(x - a) < 0.05 for x in drop_rel):
            if a - last_flash >= 1.0:
                fxs.append(["flash", {"at": 0.0, "amount": 0.6, **profile.fx_params.get("flash", {})}])
                last_flash = a
            else:
                fxs.append(["contrast_snap", {"at": 0.0, "amount": 0.6}])
            cues.append({"kind": "impact", "at": round(a, 3), "gain_db": -4})
        if s.get("ken_burns"):  # stills: real 2.5D parallax when the depth model is installed, else a push-in
            fxs.append(["depth_parallax", {"amount": 0.045, "direction": (-1) ** i}] if depth_ok else ["push_in", {"amount": 0.15}])
        fxs += [[e, dict(p)] for e, p in profile.base_fx]
        tr = "cut"
        if i + 1 < len(durs) and (i + 1) % profile.transition_every == 0:
            tr = profile.transitions[(i // profile.transition_every) % len(profile.transitions)]
        segments.append(
            {
                "clip": s["clip"],
                "slot": [round(a, 4), round(b, 4)],
                "src_in": s["src_in"],
                "src_out": s["src_out"],
                "focus": s["focus"],
                "zoom": s.get("zoom", 1.0),
                "reverse": bool(s.get("reverse")),
                "still": s["still"],
                "speed_ramp": RAMP_FSF if ramps[i] else [],
                "effects": fxs,
                "transition_out": tr,
                "transition_s": round(min(profile.transition_beats * beat_len, 0.5), 3)
                if tr != "cut"
                else 0.0,
                "reuse": {k2: s[k2] for k2 in ("reuse", "range_shift_s", "stretch") if k2 in s},
            }
        )
        if tr != "cut" and profile.sfx:
            cues.append(
                {
                    "kind": "whoosh"
                    if tr in ("whip", "swipe_left", "swipe_up", "zoom_through", "blur")
                    else "tick",
                    "at": round(b, 3),
                    "gain_db": -8,
                }
            )
    limit_composites(segments, composite.available("u2netp"))
    for d in drop_rel:
        if d > 1.6 and profile.sfx:
            cues.append({"kind": "riser", "at": round(d, 3), "gain_db": -12})
    return {
        "version": 1,
        "profile": profile.id,
        "duration": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "bpm": round(bpm, 1),
        "music_start": round(start, 3),
        "beats": [round(b - start, 3) for b in beats if start <= b <= start + duration],
        "segments": segments,
        "cues": cues,
        "reused_shots": sum(1 for s in segments if s["reuse"].get("reuse")),
    }
