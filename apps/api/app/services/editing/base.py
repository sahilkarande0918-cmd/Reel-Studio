"""Base picture renderer (FFmpeg): source ranges → framed, retimed, effected segments → transitions → one video.

A `Segment` is one shot on the output timeline: which asset, which source range, how it is framed (cover crop with a
focus point and zoom), how fast it plays (constant speed, an eased ramp, reverse, a freeze), which effects run and how
it hands over to the next segment. Every boundary sits on the frame grid. Segments are rendered one by one (bounded
memory, partial re-render possible) and joined with `xfade`; audio is never mixed here (picture and sound are
rendered separately and muxed, which avoids drift).
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.services.editing import effects as fx

CRF = {"draft": 23, "looks": 17, "delivery": 14}


@dataclass
class Segment:
    asset: Path
    src_in: float
    src_out: float
    duration: float  # output seconds (frame-snapped by `snap_plan`)
    focus_x: float = 0.5  # 0..1 framing centre in the source
    focus_y: float = 0.5
    zoom: float = 1.0  # extra static crop-in
    speed_ramp: list[tuple[float, float]] = field(
        default_factory=list
    )  # (output fraction 0..1, speed); empty = constant
    reverse: bool = False
    freeze_tail: float = 0.0  # hold the last frame this long (inside `duration`)
    still: bool = False  # image asset
    effects: list[tuple[str, dict]] = field(default_factory=list)
    transition_out: str = "cut"
    transition_dur: float = 0.0


def frames(t: float, fps: int) -> int:
    return max(1, round(t * fps))


def snap_plan(segs: list[Segment], fps: int) -> None:
    """Durations and transition lengths to whole frames; transitions never longer than either neighbour's half."""
    for i, s in enumerate(segs):
        s.duration = frames(s.duration, fps) / fps
        if s.transition_out != "cut" and i + 1 < len(segs):
            cap_f = frames(min(s.duration, segs[i + 1].duration) / 2, fps)
            want_f = max(2, 2 * round(s.transition_dur * fps / 2))  # even: centred overlaps stay whole frames
            s.transition_dur = min(want_f, cap_f - cap_f % 2) / fps
        else:
            s.transition_out, s.transition_dur = "cut", 0.0


def total_duration(segs: list[Segment]) -> float:
    return sum(s.duration for s in segs) - sum(s.transition_dur for s in segs)


def _frame_filter(s: Segment, w: int, h: int) -> str:
    """Cover-scale to the output aspect around the focus point, then the static zoom."""
    ar = w / h
    z = max(s.zoom, 1.0)
    # crop the largest output-aspect window, shrink it by the zoom, centre it on the focus point, clamp inside
    cw = f"min(iw,ih*{ar:.6f})/{z:.4f}"
    ch = f"min(ih,iw/{ar:.6f})/{z:.4f}"
    cx = f"min(max(iw*{s.focus_x:.4f}-({cw})/2,0),iw-({cw}))"
    cy = f"min(max(ih*{s.focus_y:.4f}-({ch})/2,0),ih-({ch}))"
    return f"crop=w='{cw}':h='{ch}':x='{cx}':y='{cy}',scale={w}:{h}:flags=lanczos,setsar=1"


def _speed_pieces(s: Segment, fps: int) -> list[tuple[float, float, float]]:
    """(source_in, source_out, speed) pieces. A ramp is cut into ~6-frame pieces whose speeds follow the eased curve,
    and the source range consumed is exactly the integral of the speed curve over the output duration."""
    out_frames = frames(s.duration - s.freeze_tail, fps)
    if not s.speed_ramp:
        sp = (s.src_out - s.src_in) / (out_frames / fps) if not s.still else 1.0
        return [(s.src_in, s.src_out, sp)]
    pts = sorted(s.speed_ramp)
    if pts[0][0] > 0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < 1:
        pts.append((1.0, pts[-1][1]))

    def speed_at(u: float) -> float:
        for (u0, v0), (u1, v1) in zip(pts, pts[1:], strict=False):
            if u0 <= u <= u1:
                x = (u - u0) / max(u1 - u0, 1e-6)
                x = x * x * (3 - 2 * x)
                return v0 + (v1 - v0) * x
        return pts[-1][1]

    step = 6
    pieces, src = [], s.src_in
    for f0 in range(0, out_frames, step):
        n = min(step, out_frames - f0)
        sp = speed_at((f0 + n / 2) / out_frames)
        dur_src = n / fps * sp
        pieces.append((src, src + dur_src, sp))
        src += dur_src
    return pieces


def _run(cmd: list[str], what: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"{what} failed: {r.stderr[-1500:]}")


def _effects_chain(s: Segment, w: int, h: int) -> str:
    parts = []
    for n, (eid, params) in enumerate(s.effects):
        e, p = fx.resolve(eid, params)
        parts.append(e.build(p, s.duration, w, h).replace("[g", f"[e{n}g"))
    return ",".join(parts)


def render_segment(s: Segment, out: Path, w: int, h: int, fps: int, quality: str = "looks") -> None:
    """One segment → an intermediate H.264 file of exactly round(duration*fps) frames, no audio."""
    pieces = _speed_pieces(s, fps)
    total = frames(s.duration, fps)
    frame = _frame_filter(s, w, h)
    if s.still:
        graph = f"[0:v]loop=loop=-1:size=1:start=0,fps={fps},{frame},trim=end_frame={total},setpts=PTS-STARTPTS[base]"
        inputs = ["-loop", "1", "-i", str(s.asset)]
    else:
        lo = pieces[0][0]
        inputs = ["-ss", f"{max(lo - 0.5, 0):.3f}", "-i", str(s.asset)]
        off = min(lo, 0.5)  # we seeked 0.5 s early for accuracy; trims below are relative to the seek point
        chains, labels = [], []
        for k, (a, b, sp) in enumerate(pieces):
            chains.append(
                f"[0:v]trim=start={a - lo + off:.4f}:end={b - lo + off:.4f},setpts=(PTS-STARTPTS)/{sp:.5f},fps={fps}[p{k}]"
            )
            labels.append(f"[p{k}]")
        src = labels[0]
        if len(labels) > 1:
            chains.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[cat]")
            src = "[cat]"
        rev = ",reverse" if s.reverse else ""
        hold = f",tpad=stop_mode=clone:stop_duration={s.freeze_tail:.3f}" if s.freeze_tail else ""
        chains.append(f"{src}{frame}{rev}{hold},trim=end_frame={total},setpts=PTS-STARTPTS[base]")
        graph = ";".join(chains)
    chain = _effects_chain(s, w, h)
    graph += f";[base]{chain},setsar=1,format=yuv420p[v]" if chain else ";[base]setsar=1,format=yuv420p[v]"
    _run(
        [
            "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-an",
            "-frames:v", str(total), "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", str(CRF[quality]), "-pix_fmt", "yuv420p", str(out),
        ],
        f"segment {out.name}",
    )  # fmt: skip
    got = _count_frames(out)
    if got != total:  # an empty or short segment would silently break the edit
        raise RuntimeError(
            f"segment {out.name}: {got} frames instead of {total} (source {s.src_in:.2f}-{s.src_out:.2f} s)"
        )


def _count_frames(p: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    return int((r.stdout.strip() or "0").split(",")[0] or 0)


def assemble(parts: list[Path], segs: list[Segment], out: Path, fps: int, quality: str = "looks") -> None:
    """Join rendered segments: hard cuts by concat, others by xfade at frame-exact offsets. The result is padded or
    trimmed to exactly round(total_duration * fps) frames (per-segment frame rounding can lose one)."""
    if len(parts) == 1:
        shutil.copyfile(parts[0], out)
        return
    target = round(total_duration(segs) * fps)
    inputs = sum((["-i", str(p)] for p in parts), [])
    # one timebase/rate/format for every input: concat and xfade refuse mismatched links
    chain = [f"[{i}:v]fps={fps},settb=AVTB,setsar=1,format=yuv420p[n{i}]" for i in range(len(parts))]
    prev, t = "[n0]", segs[0].duration
    for i in range(1, len(parts)):
        s = segs[i - 1]
        label = f"[x{i}]"
        if s.transition_out == "cut" or not fx.TRANSITIONS.get(s.transition_out):
            chain.append(f"{prev}[n{i}]concat=n=2:v=1:a=0{label}")
        else:
            off = t - s.transition_dur
            chain.append(
                f"{prev}[n{i}]xfade=transition={fx.TRANSITIONS[s.transition_out]}:duration={s.transition_dur:.4f}:offset={off:.4f}{label}"
            )
            t -= s.transition_dur
        t += segs[i].duration
        prev = label
    _run(
        [
            "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chain) + f";{prev}tpad=stop_mode=clone:stop_duration=0.5[out]",
            "-map", "[out]", "-an", "-frames:v", str(target), "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF[quality]),
            "-pix_fmt", "yuv420p", str(out),
        ],
        "assemble",
    )  # fmt: skip


def render_base(segs: list[Segment], work: Path, w: int, h: int, fps: int, quality: str = "looks") -> Path:
    work.mkdir(parents=True, exist_ok=True)
    snap_plan(segs, fps)
    parts = []
    for i, s in enumerate(segs):
        p = work / f"seg{i:03d}.mp4"
        render_segment(s, p, w, h, fps, quality)
        parts.append(p)
    out = work / "base.mp4"
    assemble(parts, segs, out, fps, quality)
    return out
