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
W, H = 1080, 1920
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
    """ASS subtitles for every caption and text item of the doc (frame size 1080×1920)."""
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
            elif item["type"] == "text" and item.get("style") in ("classic", "statement", "editorial"):
                lines.append(_hook(item))
            elif item["type"] == "text":
                an = {"left": 7, "center": 8, "right": 9}[item.get("align", "left")]
                x = W // 2 if an == 8 else round(item.get("x", 80))
                col = _ass_color(item.get("color") or "#FFFFFF")
                box = "\\3c" + _ass_color(doc["brand"]["colors"]["accent"]) + "\\bord18\\shad0" if item.get("box") else ""
                tag = (f"{{\\an{an}\\pos({x},{round(item.get('y', 180))})\\fs{item.get('fontSize', 64)}\\c{col}{box}"
                       f"\\fad(200,200)}}")
                lines.append(f"Dialogue: 1,{_t(item['start'])},{_t(item['start'] + item['duration'])},Title,,0,0,0,,"
                             f"{tag}{_esc(item['text'])}")
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


def _hook(item: dict) -> str:
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
        tag = r"{\an1\pos(80,%d)\fad(150,200)}" % max(y, 1250)
        return head + "HookStatement,,0,0,0,," + tag + lead + nl.join(_wrap(" ".join(words[cut:]), 12))
    tag = r"{\an8\pos(%d,%d)\fad(200,200)}" % (W // 2, y)
    return head + "HookEditorial,,0,0,0,," + tag + nl.join(_wrap(text, 18))


# ------------------------------------------------------------------ video graph


def _pieces(item: dict) -> list[tuple[float, float, dict]]:
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


def graph(doc: dict, t0: float) -> tuple[str, int]:
    """filter_complex for the doc; input 0 is the source seeked to t0. Returns (graph, number of pieces)."""
    items = sorted((i for t in doc["tracks"] for i in t["items"] if i["type"] == "video"), key=lambda i: i["start"])
    pieces = [p for it in items for p in _pieces(it)]
    n = len(pieces)
    parts = [f"[0:v]split={n}" + "".join(f"[s{i}]" for i in range(n)) if n > 1 else "[0:v]null[s0]",
             f"[0:a]asplit={len(items)}" + "".join(f"[r{i}]" for i in range(len(items))) if len(items) > 1 else "[0:a]anull[r0]"]
    for i, (a, b, k) in enumerate(pieces):
        trim = f"[s{i}]trim=start={a - t0:.4f}:end={b - t0:.4f},setpts=PTS-STARTPTS"
        if k["layout"] == "split" and k.get("second"):
            hh = H // 2
            parts.append(f"{trim},split[t{i}][u{i}]")
            parts.append(f"[t{i}]{_crop(k)},scale={W}:{hh}:force_original_aspect_ratio=increase,crop={W}:{hh}[ta{i}]")
            parts.append(f"[u{i}]{_crop(k['second'])},scale={W}:{hh}:force_original_aspect_ratio=increase,crop={W}:{hh}[ub{i}]")
            parts.append(f"[ta{i}][ub{i}]vstack,setsar=1[v{i}]")
        elif k["layout"] == "panel":
            ph = round(k["crop_height"] * W / k["crop_width"] / 2) * 2
            y = min(max(round(PANEL_CENTER * H - ph / 2), 0), H - ph)
            parts.append(f"{trim},{_crop(k)},split[pa{i}][pb{i}]")
            parts.append(f"[pa{i}]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
                         f"boxblur=8:2,scale={W}:{H},eq=brightness=-0.12[bg{i}]")  # blur a quarter-size copy: same look, ~10x cheaper
            parts.append(f"[pb{i}]scale={W}:{ph}[fg{i}]")
            parts.append(f"[bg{i}][fg{i}]overlay=0:{y},setsar=1[v{i}]")
        else:
            parts.append(f"{trim},{_crop(k)},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v{i}]")
    for i, it in enumerate(items):  # audio per span, 8 ms fades so joins inside silence never click
        d = it["sourceEnd"] - it["sourceStart"]
        parts.append(f"[r{i}]atrim=start={it['sourceStart'] - t0:.4f}:end={it['sourceEnd'] - t0:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={max(d - 0.008, 0):.4f}:d=0.008,volume={it.get('volume', 1)}[a{i}]")
    parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fps={doc['fps']}[vc]")
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
    g += f";[vc]{grade}subtitles=captions.ass:fontsdir=fonts,format=yuv420p[vout]"
    extra = []
    if rs.get("sfx"):  # synthesized, royalty-free effects (editing/audio.py), mixed under the speech
        from app.services.editing import audio

        audio.sfx_track([audio.Cue(c["kind"], c["at"], -12.0) for c in rs["sfx"]], doc["duration"], project / "sfx.wav")
        extra = ["-i", "sfx.wav"]
        g += (f";[ac]{SPEECH_CHAIN if enhance_audio else 'anull'},aresample=48000[sp];[1:a]aresample=48000,"
              "aformat=channel_layouts=mono[sx];[sp][sx]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        g += f";[ac]{SPEECH_CHAIN if enhance_audio else 'anull'},aresample=48000[aout]"
    (project / "graph.txt").write_text(g, encoding="utf-8")
    enc = (["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "21", "-b:v", "0",
            "-maxrate", "14M", "-bufsize", "28M"] if nvenc() else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(source), *extra,
           "-filter_complex_script", "graph.txt", "-map", "[vout]", "-map", "[aout]", *enc, "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-t", f"{doc['duration']:.3f}", "-movflags", "+faststart", "out.mp4"]
    subprocess.run(cmd, cwd=project, check=True, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return project / "out.mp4"
