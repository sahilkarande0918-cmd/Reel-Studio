"""Fast renderer: canonical timeline → one FFmpeg pass (NVENC when available) instead of a headless-browser capture.

Used for talk clips and bulk exports (≈5–15 s per 45 s Short instead of ≈2 min). Same inputs as the Hyperframes
path: the source spans (speech cuts), crop keyframes (crop / panel / split layouts, cut at keyframes), caption words
paginated by `compose.paginate` (identical pages to the preview), the caption preset's look (font, colours, stroke,
shadow, box, case, highlight of the spoken word, entrance, content emphasis) as ASS rendered by libass, and text items
(hook titles). Docs with intro/outro cards, logos, watermarks, code or motion items use the Hyperframes renderer.

ponytail: crop keyframes are held until the next keyframe (cuts); eased pans between keyframes are not interpolated
here. Talk framing only cuts; screen-recording reels with eased pans stay on the Hyperframes path.
"""

import shutil
import subprocess
from functools import cache
from pathlib import Path

from app.core.config import get_settings
from app.services.rendering import compose

FONTS = Path(__file__).parent / "fonts"
PANEL_CENTER = 0.42
ASS_SCALE = 1.3


def supported(doc: dict) -> str | None:
    """None when this renderer can produce the doc exactly; otherwise the reason it cannot."""
    b = doc["brand"]
    if b["intro"]["enabled"] or b["outro"]["enabled"]:
        return "intro/outro cards"
    if b.get("logoAssetId") or b["watermark"].get("enabled"):
        return "logo/watermark"
    vids = [a for a in doc["assets"].values() if a["kind"] == "video"]
    if len(vids) != 1 or any(a["kind"] == "audio" for a in doc["assets"].values()):
        return "multiple media sources"
    for t in doc["tracks"]:
        for i in t["items"]:
            if i["type"] not in ("video", "caption", "text"):
                return f"{i['type']} items"
            if i["type"] == "video" and any(k["transition_mode"] == "ease" for k in i["cropKeyframes"][1:]):
                return "eased camera pans"
    return None


# ------------------------------------------------------------------ fonts


@cache
def fonts_dir() -> Path:
    """Bundled fonts as TTF (libass cannot read WOFF2), converted once into the data cache."""
    """Bundled fonts as TTF (libass cannot read WOFF2), converted once into the data cache. Each file's family is
    renamed to "RS <family>" with a Regular style: the bundled subsets carry inconsistent names ("Archivo SemiBold
    ExtraBold"), which made libass fall back to Arial, and a unique name can never be shadowed by a system font."""
    from fontTools.ttLib import TTFont

    out = get_settings().data_dir / "cache" / "fonts-ttf-v2"
    out.mkdir(parents=True, exist_ok=True)
    by_file = {Path(file).stem: fam for fam, (file, _w) in compose.FONT_FILES.items()}
    for f in FONTS.iterdir():
        dst = out / (f.stem + ".ttf")
        if dst.exists() or f.suffix not in (".woff2", ".ttf") or f.stem not in by_file:
            continue
        t = TTFont(str(f))
        t.flavor = None
        name = family(by_file[f.stem])
        for rec in list(t["name"].names):
            if rec.nameID in (1, 4, 16, 21):
                rec.string = name
            elif rec.nameID in (2, 17, 22):
                rec.string = "Regular"
            elif rec.nameID == 6:
                rec.string = name.replace(" ", "")
        t["OS/2"].fsSelection = (t["OS/2"].fsSelection & ~0b1100001) | 0b1000000  # REGULAR, not bold/italic
        t["head"].macStyle = 0
        t.save(str(dst))
    return out


def family(font: str) -> str:
    """The family name libass asks for (set on the converted file by `fonts_dir`)."""
    return f"RS {font if font in compose.FONT_FILES else 'Archivo'}"


# ------------------------------------------------------------------ captions → ASS


def _ass_color(hex_color: str, alpha: int = 0) -> str:
    h = (hex_color or "#FFFFFF").lstrip("#")[:6].ljust(6, "F")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _t(s: float) -> str:
    s = max(0.0, s)
    cs = int(round(s * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def _word(w: dict, look: dict, active: bool, upper: bool) -> str:
    text = _esc(w["text"].upper() if upper else w["text"])
    hi = look.get("highlight", "fill")
    tags = ""
    if w.get("emphasis") and not active:  # content emphasis: accent colour, a touch larger, never flashing
        tags = f"\\c{_ass_color(look['active'])}\\fscx106\\fscy106"
    if active and hi != "none":
        if hi == "chip":
            chip = look.get("chip") or look["active"]
            tags = f"\\c{_ass_color(compose.brand_ink(chip))}\\3c{_ass_color(chip)}\\bord14\\shad0"
        elif hi == "underline":
            tags = f"\\u1\\c{_ass_color(look['active'])}"
        elif hi == "scale":
            tags = f"\\c{_ass_color(look['active'])}\\fscx115\\fscy115"
        else:  # fill, karaoke
            tags = f"\\c{_ass_color(look['active'])}"
    return "{" + tags + "}" + text + "{\\r}" if tags else text


def _entrance(look: dict) -> str:
    e = look.get("entrance", "none")
    return {
        "fade": "\\fad(150,0)", "blur": "\\fad(180,0)\\blur6\\t(0,200,\\blur0)",
        "pop": "\\fscx70\\fscy70\\t(0,160,\\fscx100\\fscy100)", "zoom": "\\fscx150\\fscy150\\t(0,180,\\fscx100\\fscy100)",
        "bounce": "\\fad(120,0)", "drop": "\\fad(120,0)", "slide": "\\fad(120,0)", "swing": "\\fad(120,0)",
    }.get(e, "")


def ass(doc: dict) -> str:
    """ASS subtitles for every caption and text item of the doc (any frame size; 1080×1920 by default)."""
    W, H = doc["width"], doc["height"]
    style = doc["captionStyle"]
    look = style.get("look") or {"font": doc["brand"]["fonts"].get("body", "Archivo"), "color": "#FFFFFF",
                                 "active": doc["brand"]["colors"]["accent"], "highlight": "fill", "stroke": 4}
    # ASS sizes the full font height, CSS the em box: x1.3 renders the same visual size as the HTML preview
    fs = round(style["fontSize"] * look.get("sizeScale", 1) * ASS_SCALE)
    stroke = look.get("stroke", 4 if not look.get("box") else 0)
    shadow = {"none": 0, "soft": 2, "hard": 4, "long": 6}.get(look.get("shadow", "soft"), 2)
    border_style = 3 if look.get("box") else 1
    back = _ass_color(doc["brand"]["colors"].get("background", "#000000"), 0x40) if look.get("box") else _ass_color("#000000", 0x60)
    spacing = round(look.get("tracking", 0) * fs, 1)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Cap,{family(look['font'])},{fs},{_ass_color(look['color'])},&H000000FF,"
        f"{_ass_color(look.get('strokeColor', '#000000'))},{back},0,{-1 if look.get('italic') else 0},0,0,100,100,"
        f"{spacing},0,{border_style},{stroke if border_style == 1 else 18},{shadow},5,40,40,0,1",
        f"Style: Title,{family('Archivo')},72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,6,3,"
        "8,60,60,0,1",
        # hook headline looks (OpusClip-style families, own designs): classic = white card with dark text,
        # statement = large bold left-aligned lines, editorial = serif headline in the accent colour
        f"Style: HookClassic,{family('Archivo')},70,&H00141414,&H000000FF,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,"
        "22,0,8,90,90,0,1",
        f"Style: HookStatement,{family('Archivo')},132,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,"
        "0,5,1,80,120,0,1",
        # motion graphics: key-number callout (accent card, pop) and lower third (slides in from the left)
        f"Style: Callout,{family('Archivo')},{round(130 * min(W, H) / 1080)},"
        f"{_ass_color(compose.brand_ink(doc['brand']['colors']['accent']))},&H000000FF,"
        f"{_ass_color(doc['brand']['colors']['accent'])},&H00000000,0,0,0,0,100,100,0,0,3,26,0,5,60,60,0,1",
        f"Style: LowerThird,{family('Archivo')},{round(46 * min(W, H) / 1080)},&H00FFFFFF,&H000000FF,&H00141414,"
        "&H00141414,0,0,0,0,100,100,0,0,3,16,0,1,60,60,0,1",
        f"Style: HookEditorial,{family('Fraunces')},96,{_ass_color(doc['brand']['colors']['accent'])},&H000000FF,"
        "&H00000000,&H80000000,0,-1,0,0,100,100,0,0,1,0,4,8,80,80,0,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    cy = (style["safeTop"] + style["safeBottom"]) / 2
    upper = bool(look.get("uppercase"))
    enabled = style.get("enabled", True)
    for t in doc["tracks"]:
        for item in t["items"]:
            if item["type"] == "caption" and enabled:
                off = item["start"]
                pages = compose.paginate(item["words"], style["maxCharsPerLine"], style["maxLines"], item["duration"])
                for p in pages:
                    flat = [w for ln in p["lines"] for w in ln]
                    marks = [p["start"]] + [w["start"] for w in flat[1:]] + [p["end"]]
                    for j, w in enumerate(flat):  # one event per spoken word: that word is the active one
                        a, b = max(marks[j], p["start"]), max(marks[j + 1], marks[j] + 0.01)
                        if b <= a:
                            continue
                        body = "\\N".join(" ".join(_word(x, look, x is w, upper) for x in ln) for ln in p["lines"])
                        tag = f"{{\\an5\\pos({W // 2},{round(cy)}){_entrance(look) if j == 0 else ''}}}"
                        lines.append(f"Dialogue: 0,{_t(off + a)},{_t(off + b)},Cap,,0,0,0,,{tag}{body}")
            elif item["type"] == "text" and item.get("style") in ("callout", "lower_third"):
                lines.append(_motion(item, W, H))
            elif item["type"] == "text" and item.get("style") in ("classic", "statement", "editorial"):
                lines.append(_hook(item, W, H))
            elif item["type"] == "text":
                an = {"left": 7, "center": 8, "right": 9}[item.get("align", "left")]
                x = W // 2 if an == 8 else round(item.get("x", 80))
                col = _ass_color(item.get("color") or "#FFFFFF")
                box = "\\3c" + _ass_color(doc["brand"]["colors"]["accent"]) + "\\bord18\\shad0" if item.get("box") else ""
                tag = (f"{{\\an{an}\\pos({x},{round(item.get('y', 180))})\\fs{item.get('fontSize', 64)}\\c{col}{box}"
                       f"\\fad(200,200)}}")
                lines.append(f"Dialogue: 1,{_t(item['start'])},{_t(item['start'] + item['duration'])},Title,,0,0,0,,"
                             f"{tag}{_esc(item['text'])}")
    if doc.get("renderSettings", {}).get("progressBar"):  # thin accent bar filling across the top
        bar = max(6, round(H / 240))
        col = _ass_color(doc["brand"]["colors"]["accent"])
        tag = r"{\an7\pos(0,0)\bord0\shad0\1c%s\fscx0\t(0,%d,\fscx100)\p1}" % (col, round(doc["duration"] * 1000))
        lines.append(f"Dialogue: 3,{_t(0)},{_t(doc['duration'])},Cap,,0,0,0,,{tag}m 0 0 l {W} 0 {W} {bar} 0 {bar}" + r"{\p0}")
    return "\n".join(lines) + "\n"


def _wrap(text: str, width: int) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return [*out, cur] if cur else out


def _hook(item: dict, W: int = 1080, H: int = 1920) -> str:
    """One headline event in the item's style, wrapped to balanced lines and faded in and out."""
    style, text = item["style"], _esc(item["text"].strip())
    t0, t1 = _t(item["start"]), _t(item["start"] + item["duration"])
    y = round(item.get("y", 300))
    nl = r"\N"
    head = f"Dialogue: 2,{t0},{t1},"
    if style == "classic":
        tag = r"{\an8\pos(%d,%d)\fad(150,200)}" % (W // 2, y)
        return head + "HookClassic,,0,0,0,," + tag + nl.join(_wrap(text, 22))
    if style == "statement":  # a small lead-in line, then the last words large, bottom-left above the captions
        words = text.split()
        cut = max(len(words) - 3, 0)
        lead = (r"{\fs62}" + " ".join(words[:cut]) + nl + r"{\fs132}") if cut else ""
        tag = r"{\an1\pos(80,%d)\fad(150,200)}" % max(y, round(H * 0.65))
        return head + "HookStatement,,0,0,0,," + tag + lead + nl.join(_wrap(" ".join(words[cut:]), 12))
    tag = r"{\an8\pos(%d,%d)\fad(200,200)}" % (W // 2, y)
    return head + "HookEditorial,,0,0,0,," + tag + nl.join(_wrap(text, 18))


def _motion(item: dict, W: int, H: int) -> str:
    """Motion-graphics events: a key-number callout pops in (scale overshoot), a lower third slides in from the left."""
    t0, t1 = _t(item["start"]), _t(item["start"] + item["duration"])
    text = _esc(item["text"].strip())
    if item["style"] == "callout":
        y = round(item.get("y", H * 0.3))
        tag = r"{\an5\pos(%d,%d)\fscx30\fscy30\t(0,160,\fscx112\fscy112)\t(160,260,\fscx100\fscy100)\fad(0,200)}" % (W // 2, y)
        return f"Dialogue: 2,{t0},{t1},Callout,,0,0,0,,{tag}{text}"
    y = round(item.get("y", H * 0.62))
    tag = r"{\an1\move(%d,%d,60,%d,0,320)\fad(0,250)}" % (-W // 2, y, y)
    return f"Dialogue: 2,{t0},{t1},LowerThird,,0,0,0,,{tag}{text}"


# ------------------------------------------------------------------ video graph


def _pieces(item: dict) -> list[tuple[float, float, dict]]:  # (source start, source end, keyframe)
    """(source start, source end, keyframe) for each stretch of one video item held on one crop keyframe."""
    ks = sorted(item["cropKeyframes"], key=lambda k: k["t"])
    out = []
    for i, k in enumerate(ks):
        a = item["sourceStart"] + max(0.0, k["t"])
        b = item["sourceStart"] + (ks[i + 1]["t"] if i + 1 < len(ks) else item["duration"])
        b = min(b, item["sourceEnd"])
        if b - a > 1 / 60:
            out.append((a, b, k))
    return out or [(item["sourceStart"], item["sourceEnd"], ks[0])]


def _crop(k: dict) -> str:
    return f"crop={k['crop_width']}:{k['crop_height']}:{k['crop_x']}:{k['crop_y']}"


XFADE = {"auto": "fade", "fade": "fade", "slide": "slideleft", "flash": "fadewhite"}
XFADE_S = 0.18


def _transitions(doc: dict, pieces: list) -> list[str | None]:
    """xfade kind for the boundary before each piece (None = straight cut). auto: only where the framing changes to
    another speaker or layout; fade/slide/flash: also where a speech cut joins two stretches. Punch-ins never."""
    mode = doc.get("renderSettings", {}).get("transitions") or "none"
    out: list[str | None] = [None]
    for (pa, pb, pk, pit), (qa, qb, qk, qit) in zip(pieces, pieces[1:], strict=False):
        zoom = "zoom" in (pk.get("region"), qk.get("region"))
        framing = (pk.get("region"), pk["layout"]) != (qk.get("region"), qk["layout"])
        join = pit is not qit
        hit = mode != "none" and not zoom and (framing or (join and mode != "auto"))
        short = min(pb - pa, qb - qa) < 3 * XFADE_S
        out.append(XFADE[mode] if hit and not short else None)
    return out


def graph(doc: dict, t0: float) -> tuple[str, int]:
    """filter_complex for the doc; input 0 is the source seeked to t0. Returns (graph, number of pieces).
    Transitions keep the edit's length: the shot before one runs XFADE_S longer and the two overlap by that much."""
    W, H = doc["width"], doc["height"]
    fps = doc["fps"]
    items = sorted((i for t in doc["tracks"] for i in t["items"] if i["type"] == "video"), key=lambda i: i["start"])
    pieces = [(*p, it) for it in items for p in _pieces(it)]
    n = len(pieces)
    trans = _transitions(doc, pieces)
    parts = [f"[0:v]split={n}" + "".join(f"[s{i}]" for i in range(n)) if n > 1 else "[0:v]null[s0]",
             f"[0:a]asplit={len(items)}" + "".join(f"[r{i}]" for i in range(len(items))) if len(items) > 1 else "[0:a]anull[r0]"]
    lengths = []
    for i, (a, b, k, _it) in enumerate(pieces):
        ext = XFADE_S if i + 1 < n and trans[i + 1] else 0.0
        lengths.append(b - a + ext)
        trim = f"[s{i}]trim=start={a - t0:.4f}:end={b + ext - t0:.4f},setpts=PTS-STARTPTS"
        norm = f"fps={fps},settb=AVTB,format=yuv420p,setsar=1"
        if k["layout"] == "split" and k.get("second"):
            side = W > H  # landscape: side by side; portrait/square: stacked
            hw, hh = (W // 2, H) if side else (W, H // 2)
            parts.append(f"{trim},split[t{i}][u{i}]")
            parts.append(f"[t{i}]{_crop(k)},scale={hw}:{hh}:force_original_aspect_ratio=increase,crop={hw}:{hh}[ta{i}]")
            parts.append(f"[u{i}]{_crop(k['second'])},scale={hw}:{hh}:force_original_aspect_ratio=increase,crop={hw}:{hh}[ub{i}]")
            parts.append(f"[ta{i}][ub{i}]{'hstack' if side else 'vstack'},{norm}[v{i}]")
        elif k["layout"] == "panel":
            ph = min(H, round(k["crop_height"] * W / k["crop_width"] / 2) * 2)
            pw = W if ph < H else round(k["crop_width"] * H / k["crop_height"] / 2) * 2
            y = min(max(round(PANEL_CENTER * H - ph / 2), 0), H - ph) if ph < H else 0
            parts.append(f"{trim},{_crop(k)},split[pa{i}][pb{i}]")
            parts.append(f"[pa{i}]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
                         f"boxblur=8:2,scale={W}:{H},eq=brightness=-0.12[bg{i}]")  # blur a quarter-size copy: same look, ~10x cheaper
            parts.append(f"[pb{i}]scale={pw}:{ph}[fg{i}]")
            parts.append(f"[bg{i}][fg{i}]overlay=(W-w)/2:{y},{norm}[v{i}]")
        else:
            parts.append(f"{trim},{_crop(k)},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{norm}[v{i}]")
    for i, it in enumerate(items):  # audio per span, 8 ms fades so joins inside silence never click
        d = it["sourceEnd"] - it["sourceStart"]
        parts.append(f"[r{i}]atrim=start={it['sourceStart'] - t0:.4f}:end={it['sourceEnd'] - t0:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={max(d - 0.008, 0):.4f}:d=0.008,volume={it.get('volume', 1)}[a{i}]")
    if not any(trans):
        parts.append("".join(f"[v{i}]" for i in range(n)) + "concat=n=%d:v=1:a=0[vc]" % n)
    else:  # fold left: straight cuts concatenate, transitions overlap by XFADE_S (lengths already include it)
        cur, total = "v0", lengths[0]
        for i in range(1, n):
            out = "vc" if i == n - 1 else f"x{i}"
            if trans[i]:
                parts.append(f"[{cur}][v{i}]xfade=transition={trans[i]}:duration={XFADE_S}:offset={total - XFADE_S:.4f}[{out}]")
                total += lengths[i] - XFADE_S
            else:
                parts.append(f"[{cur}][v{i}]concat=n=2:v=1:a=0[{out}]")
                total += lengths[i]
            cur = out
    parts.append("".join(f"[a{i}]" for i in range(len(items))) + f"concat=n={len(items)}:v=0:a=1[ac]")
    return ";".join(parts), n


# auto colour correction: temporally smoothed auto levels (no flicker), then a gentle contrast/saturation lift
COLOR_CHAIN = "normalize=blackpt=black:whitept=white:smoothing=48:independence=0.4:strength=0.5,eq=contrast=1.04:saturation=1.08"
SPEECH_CHAIN = ("highpass=f=70,afftdn=nf=-28,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=150,"
                "loudnorm=I=-14:TP=-1.5:LRA=11")


@cache
def nvenc() -> bool:
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1", "-c:v", "h264_nvenc",
                        "-f", "null", "-"], capture_output=True, timeout=60)
    return r.returncode == 0


def render(doc: dict, source: Path, project: Path, enhance_audio: bool = True, timeout: int = 1800) -> Path:
    """Write project/out.mp4 for the doc. Raises CalledProcessError with FFmpeg's message on failure."""
    project.mkdir(parents=True, exist_ok=True)
    (project / "captions.ass").write_text(ass(doc), encoding="utf-8")
    fdir = project / "fonts"
    fdir.mkdir(exist_ok=True)
    for f in fonts_dir().iterdir():  # ~1 MB in all; always refreshed so a re-render never uses stale font files
        shutil.copyfile(f, fdir / f.name)
    vids = [i for t in doc["tracks"] for i in t["items"] if i["type"] == "video"]
    t0 = max(0.0, min(i["sourceStart"] for i in vids) - 1.0)
    t1 = max(i["sourceEnd"] for i in vids) + 0.5
    g, _ = graph(doc, t0)
    rs = doc.get("renderSettings", {})
    grade = COLOR_CHAIN + "," if rs.get("colorCorrect") else ""
    W, H = doc["width"], doc["height"]
    extra: list[str] = []

    def add_input(*args: str) -> int:  # input 0 is the source
        extra.extend(args)
        return sum(1 for x in extra if x == "-i")

    # B-roll cutaways (under the captions): stock clips cover the frame, stills get a slow push-in
    cur = "vc"
    for n, c in enumerate(rs.get("brollClips") or []):
        if not (project / c["src"]).is_file():
            continue
        a, d = c["at"], c["duration"]
        frames = max(2, round(d * doc["fps"]))
        if c["kind"] == "video":
            idx = add_input("-i", c["src"])
            prep = (f"[{idx}:v]trim=duration={d:.3f},setpts=PTS-STARTPTS+{a:.3f}/TB,"
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={doc['fps']},format=yuv420p")
        else:
            idx = add_input("-loop", "1", "-t", f"{d:.3f}", "-i", c["src"])
            prep = (f"[{idx}:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                    f"zoompan=z='min(1+0.0009*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={doc['fps']},"
                    f"setpts=PTS-STARTPTS+{a:.3f}/TB,format=yuv420p")
        g += f";{prep},fade=t=in:st={a:.3f}:d=0.12,fade=t=out:st={a + d - 0.12:.3f}:d=0.12[br{n}]"
        g += f";[{cur}][br{n}]overlay=0:0:enable='between(t,{a:.3f},{a + d:.3f})':eof_action=pass[vb{n}]"
        cur = f"vb{n}"
    stickers = []
    for e in rs.get("emojis") or []:  # AI emojis: Noto 3D PNGs above the caption block, fading in and out
        from app.services.rendering import emoji

        if (png := emoji.png(e["code"])) is not None:
            stickers.append((png, e))
    g += f";[{cur}]{grade}subtitles=captions.ass:fontsdir=fonts,format=yuv420p" + ("[vs]" if stickers else "[vout]")
    if stickers:
        size = round(min(W, H) * 0.15)
        cy = max(0, round(doc["captionStyle"]["safeTop"] - size * 0.9))
        cur = "vs"
        for n, (png, e) in enumerate(stickers):
            shutil.copyfile(png, project / f"emoji{n}.png")
            idx = add_input("-loop", "1", "-t", f"{doc['duration']:.3f}", "-i", f"emoji{n}.png")
            a, b = e["at"], e["at"] + e["duration"]
            g += (f";[{idx}:v]format=rgba,scale={size}:{size},fade=t=in:st={a:.3f}:d=0.15:alpha=1,"
                  f"fade=t=out:st={max(b - 0.2, a):.3f}:d=0.2:alpha=1[em{n}]")
            out = "vout" if n == len(stickers) - 1 else f"vo{n}"
            g += f";[{cur}][em{n}]overlay=(W-w)/2:{cy}:enable='between(t,{a:.3f},{b:.3f})',format=yuv420p[{out}]"
            cur = out
    voice = rs.get("dubAudio")  # voice dubbing: the dubbed speech replaces the original voice track
    speech = "[ac]"
    if voice and (project / voice).is_file():
        idx = add_input("-i", voice)
        g += f";[{idx}:a]aresample=48000,apad=whole_dur={doc['duration']:.3f}[dub]"
        speech = "[dub]"
    if rs.get("sfx"):  # synthesized, royalty-free effects (editing/audio.py), mixed under the speech
        from app.services.editing import audio

        audio.sfx_track([audio.Cue(c["kind"], c["at"], -12.0) for c in rs["sfx"]], doc["duration"], project / "sfx.wav")
        idx = add_input("-i", "sfx.wav")
        g += (f";{speech}{SPEECH_CHAIN if enhance_audio else 'anull'},aresample=48000[sp];[{idx}:a]aresample=48000,"
              "aformat=channel_layouts=mono[sx];[sp][sx]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        g += f";{speech}{SPEECH_CHAIN if enhance_audio else 'anull'},aresample=48000[aout]"
    if speech == "[dub]":
        g += ";[ac]anullsink"  # the original voice is not used
    (project / "graph.txt").write_text(g, encoding="utf-8")
    enc = (["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "21", "-b:v", "0",
            "-maxrate", "14M", "-bufsize", "28M"] if nvenc() else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(source), *extra,
           "-filter_complex_script", "graph.txt", "-map", "[vout]", "-map", "[aout]", *enc, "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-t", f"{doc['duration']:.3f}", "-movflags", "+faststart", "out.mp4"]
    subprocess.run(cmd, cwd=project, check=True, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return project / "out.mp4"
