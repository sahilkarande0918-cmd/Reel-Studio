"""Compile a canonical timeline into a Hyperframes composition (index.html).

Camera: the source video sits in #cam (scaled/translated by GSAP) inside #win (the visible window).
  crop  layout → #win is the whole 9:16 frame, the crop box is scaled to full height.
  panel layout → the (wider) crop box is scaled to full width; #win shrinks to the panel's height and
                 sits above the caption zone, so long code lines stay whole and legible.
Interpolation matches the studio preview (`cropAt` in apps/web/components/studio/highlights.tsx):
linear between keyframes, a jump at `cut` keyframes or layout changes.
Captions: pages of ≤ maxLines lines (≤ maxCharsPerLine chars); presets highlight-word / karaoke / boxed.
Brand: bundled fonts only, optional intro/outro cards and a corner watermark (logo + handle). Clip-relative
times (keyframes, caption words) are offset by their item's start, i.e. the intro length.
"""

import html
import json
import re
import shutil
from pathlib import Path

from app.services.rendering import motion

FONTS_DIR = Path(__file__).with_name("fonts")
GSAP_FILE = Path(__file__).with_name("vendor") / "gsap.min.js"  # GSAP 3.14.2, bundled so renders work offline
PANEL_CENTER = 0.4  # panel centre as a fraction of frame height, captions in the lower zone
PANEL_CENTER_UPPER_CAPTIONS = 0.6  # captions at the top: code panels sit lower


def panel_center(caption_style: dict, h: int) -> float:
    return PANEL_CENTER if caption_style["safeTop"] >= h / 2 else PANEL_CENTER_UPPER_CAPTIONS


PAGE_GAP_S = 0.7  # a pause this long starts a new caption page
LINGER_S = 0.5  # a page stays this long after its last word when speech pauses


def camera(k: dict, w: int, h: int, center: float = PANEL_CENTER) -> dict:
    """Frame-space placement for one crop keyframe."""
    if k["layout"] == "panel":
        s = w / k["crop_width"]
        ph = round(k["crop_height"] * s)
        win_y = min(max(round(center * h - ph / 2), 0), h - ph)
        win = [win_y, ph]
    else:
        s = h / k["crop_height"]
        win = [0, h]
    return {
        "t": k["t"],
        "win": win,
        "cam": [round(-k["crop_x"] * s, 2), round(-k["crop_y"] * s, 2), round(s, 5)],
    }


def camera_track(keyframes: list[dict], w: int, h: int, center: float = PANEL_CENTER) -> list[dict]:
    out, prev = [], None
    for k in sorted(keyframes, key=lambda k: k["t"]):
        c = camera(k, w, h, center)
        c["jump"] = prev is None or k["transition_mode"] == "cut" or k["layout"] != prev["layout"]
        out.append(c)
        prev = k
    return out


def _chars(ws: list[dict]) -> int:
    return len(" ".join(w["text"] for w in ws))


def _lines(ws: list[dict], max_chars: int, max_lines: int) -> list[list[dict]] | None:
    """Balanced line breaks for one page (shortest longest line), or None if it cannot fit."""
    if _chars(ws) <= max_chars or len(ws) == 1:
        return [ws]
    if max_lines < 2:
        return None
    best = None
    for i in range(1, len(ws)):
        head, rest = ws[:i], _lines(ws[i:], max_chars, max_lines - 1)
        if rest and _chars(head) <= max_chars:
            worst = max(_chars(head), *(_chars(line) for line in rest))
            if best is None or worst < best[0]:
                best = (worst, [head, *rest])
    return best[1] if best else None


def _pages(phrase: list[dict], max_chars: int, max_lines: int) -> list[list[list[dict]]]:
    """Fewest pages that fit, with the phrase split into pages of even length (no orphan words)."""
    total = _chars(phrase)
    for n in range(1, len(phrase) + 1):
        chunks, cur, pos = [], [], 0
        for w in phrase:
            mid = pos + len(w["text"]) / 2
            if cur and len(chunks) < n - 1 and mid > total * (len(chunks) + 1) / n:
                chunks.append(cur)
                cur = []
            cur.append(w)
            pos += len(w["text"]) + 1
        chunks.append(cur)
        laid = [_lines(c, max_chars, max_lines) for c in chunks]
        if all(laid):
            return laid
    return [[[w]] for w in phrase]


def paginate(words: list[dict], max_chars: int, max_lines: int, duration: float) -> list[dict]:
    """[{start, end, lines: [[word, ...], ...]}]. Phrases end at sentence ends and long pauses; each phrase
    is laid out on the fewest pages of ≤ max_lines balanced lines of ≤ max_chars characters."""
    phrases, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > PAGE_GAP_S or cur[-1]["text"][-1] in ".?!"):
            phrases.append(cur)
            cur = []
        cur.append(w)
    if cur:
        phrases.append(cur)
    pages = [{"lines": lines} for ph in phrases for lines in _pages(ph, max_chars, max_lines)]
    for i, p in enumerate(pages):
        first, last = p["lines"][0][0], p["lines"][-1][-1]
        nxt = pages[i + 1]["lines"][0][0]["start"] if i + 1 < len(pages) else duration
        p["start"] = first["start"]
        p["end"] = min(nxt, last["end"] + LINGER_S, duration) if nxt - last["end"] > 1.0 else nxt
        p["end"] = max(p["end"], p["start"] + 0.2)
    return pages


FONT_FILES = {  # family → (file in fonts/, weight); all SIL OFL, bundled
    "Archivo": ("archivo-800.woff2", 800),
    "Poppins": ("poppins-700.woff2", 700),
    "Noto Sans": ("noto-sans-700.woff2", 700),
    "JetBrains Mono": ("jetbrains-mono-700.woff2", 700),
    "Fira Code": ("fira-code-600.woff2", 600),
    "Fraunces": ("fraunces-600.woff2", 600),  # display serif for motion-graphics headings
}


def font_families(doc: dict) -> list[str]:
    fams = list(dict.fromkeys(doc["brand"]["fonts"].values()))
    if any(i["type"] == "motion" for t in doc["tracks"] for i in t["items"]):
        fams.append("Fraunces")
    return fams
SAFE_Y = 150  # keep corner marks clear of the platforms' top/bottom UI


def rgba(hex_color: str, alpha: float) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


def word_states(preset: str, text: str, accent: str, ink: str, chip: str, shadow: str) -> dict:
    """GSAP property sets per caption preset: on (being spoken) and off (after) for plain/code words.
    `None` as off means the word keeps its spoken colour (karaoke fill)."""
    code_on = {"backgroundColor": accent, "color": ink}
    code_off = {"backgroundColor": chip, "color": accent}
    if preset == "karaoke":
        return {"on": {"color": accent}, "off": None, "code_on": code_on, "code_off": code_off}
    if preset == "boxed":
        return {"on": {"color": accent}, "off": {"color": text}, "code_on": code_on, "code_off": code_off}
    return {  # highlight-word: the spoken word sits on an accent pill
        "on": {"backgroundColor": accent, "color": ink, "textShadow": "none"},
        "off": {"backgroundColor": "rgba(0, 0, 0, 0)", "color": text, "textShadow": shadow},
        "code_on": code_on,
        "code_off": code_off,
    }


TOKEN = re.compile(
    r'(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'
    r'|(?P<comment>//[^\n]*|\#[^\n]*|<!--[\s\S]*?-->)'
    r'|(?P<number>\b\d+(?:\.\d+)?\b)'
    r'|(?P<keyword>\b(?:true|false|null|const|let|var|function|return|if|else|for|while|'
    r'def|class|import|from|print|True|False|None|SELECT|FROM|WHERE)\b)'
    r'|(?P<tag></?[A-Za-z][\w:-]*|/?>)'
)


def code_markup(source: str) -> str:
    """Small offline lexical highlighter. Every source character is escaped, never executed."""
    parts, end = [], 0

    def chars(value: str) -> str:
        return "".join(f'<span class="char">{html.escape(c)}</span>' for c in value)

    for match in TOKEN.finditer(source):
        parts.append(chars(source[end:match.start()]))
        parts.append(f'<span class="tok-{match.lastgroup}">{chars(match.group())}</span>')
        end = match.end()
    parts.append(chars(source[end:]))
    return "".join(parts)


def compile_html(doc: dict) -> str:
    w, h, dur = doc["width"], doc["height"], doc["duration"]
    items = [i for t in doc["tracks"] for i in t["items"]]
    brand, style = doc["brand"], doc["captionStyle"]
    bg, text, accent = (brand["colors"][k] for k in ("background", "text", "accent"))
    ink = brand_ink(accent)
    body_font, code_font = brand["fonts"]["body"], brand["fonts"]["code"]
    fs = style["fontSize"]
    preset = style.get("preset", "highlight-word")
    lead = min((i["start"] for i in items), default=0)
    tail_at = max((i["start"] + i["duration"] for i in items), default=dur)
    clip_d = tail_at - lead
    intro = brand.get("intro") or {"enabled": False}
    outro = brand.get("outro") or {"enabled": False}
    watermark = brand.get("watermark") or {"enabled": False}
    logo_id = brand.get("logoAssetId")
    logo_src = html.escape(doc["assets"][logo_id]["src"]) if logo_id else None
    handle = html.escape(brand.get("handle") or "")
    shadow = "0 3px 0 rgba(0, 0, 0, 0.7), 0 0 20px rgba(0, 0, 0, 0.8)"
    chip = rgba(bg, 0.85)
    states = word_states(preset, text, accent, ink, chip, shadow)

    media_html, cameras, overlays, code_sequences, fx, pushes, motion_js = [], [], [], [], [], [], []
    mctx = {"w": w, "h": h, "bg": bg, "text": text, "accent": accent, "ink": ink, "body_font": body_font, "code_font": code_font,
            "display_font": "Fraunces", "assets": doc["assets"], "logo": logo_src, "name": brand.get("name", "")}

    look = STYLES[doc.get("stylePreset", "focus")]

    def transition(item: dict, selector: str, start: float, end: float) -> None:
        kind = item.get("transition", "none")
        kind = look["transition"] if kind == "none" else kind  # an explicit editor choice wins
        if kind != "none":
            fx.append({"sel": selector, "s": round(start, 3), "e": round(end, 3), "kind": kind})

    for idx, item in enumerate(items):
        start, duration = item["start"], item["duration"]
        if item["type"] in ("video", "audio"):
            asset = doc["assets"][item["assetId"]]
            tag = item["type"]
            media = (f'<{tag} id="media-{idx}" class="clip" src="{html.escape(asset["src"])}" '
                     f'data-start="{start}" data-duration="{duration}" data-media-start="{item["sourceStart"]}" '
                     f'data-has-audio="true" data-volume="{item.get("volume", 1)}"></{tag}>')
            if tag == "video":
                cams = camera_track(item["cropKeyframes"], w, h, panel_center(style, h))
                for c in cams:
                    c["t"] = round(c["t"] + start, 3)
                cameras.append({"win": f"#win-{idx}", "cam": f"#cam-{idx}", "keys": cams})
                transition(item, f"#win-{idx}", start, start + duration)
                if look["push"]:
                    pushes.append({"sel": f"#cam-{idx} video", "s": start, "d": duration})
                media = (f'<div id="win-{idx}" class="win">'  # untimed: the <video> inside carries the timing
                         f'<div id="cam-{idx}" class="cam" style="width:{asset.get("width", w)}px;'
                         f'height:{asset.get("height", h)}px">{media}</div></div>')
            media_html.append(media)
        elif item["type"] == "text":
            transition(item, f"#text-{idx}", start, start + duration)
            box = f"background:{rgba(bg, 0.82)};padding:18px 28px;border-radius:24px;" if item.get("box") else ""
            overlays.append(f'<div id="text-{idx}" class="text-overlay clip" data-start="{start}" data-duration="{duration}" '
                            f'style="{box}left:{item.get("x", 80)}px;top:{item.get("y", 180)}px;'
                            f'font-size:{item.get("fontSize", 64)}px;color:{item.get("color", text)};'
                            f'text-align:{item.get("align", "left")}">{html.escape(item["text"])}</div>')
        elif item["type"] == "motion":
            markup, js = motion.render(item, idx, mctx)
            overlays.append(markup)
            motion_js.append(js)
        elif item["type"] == "code":
            revisions = [{"at": 0, "code": item["code"], "typingDuration": item.get("typingDuration", 2)},
                         *item.get("changes", [])]
            transition(item, f"#code-{idx}-0", start, start + (revisions[1]["at"] if len(revisions) > 1 else duration))
            for ri, revision in enumerate(revisions):
                at = revision["at"]
                end = revisions[ri + 1]["at"] if ri + 1 < len(revisions) else duration
                selector = f"code-{idx}-{ri}"
                overlays.append(f'<section id="{selector}" class="code-panel clip" data-start="{start + at}" '
                                f'data-duration="{end - at}"><header>{html.escape(item.get("title", ""))}'
                                f'<small>{html.escape(item["language"])}</small></header>'
                                f'<pre>{code_markup(revision["code"])}</pre></section>')
                code_sequences.append({"selector": f"#{selector} .char", "at": start + at,
                                       "duration": min(revision["typingDuration"], end - at)})
    pages = []
    for caption in (i for i in items if i["type"] == "caption"):
        for page in paginate(caption["words"], style["maxCharsPerLine"], style["maxLines"], caption["duration"]):
            pages.append({**page, "offset": caption["start"]})
    page_html, word_times, n = [], [], 0
    for p in pages:
        cap_at = p["offset"]
        flat = [x for line in p["lines"] for x in line]
        lines_html = []
        for line in p["lines"]:
            spans = []
            for x in line:
                cls = "w code" if x["isCode"] else "w"
                spans.append(f'<span id="w{n}" class="{cls}">{html.escape(x["text"])}</span>')
                idx = flat.index(x)
                off = flat[idx + 1]["start"] if idx + 1 < len(flat) else p["end"]
                on_t = round(cap_at + x["start"], 3)
                word_times.append([n, on_t, round(cap_at + max(off, x["start"] + 0.05), 3), x["isCode"]])
                n += 1
            lines_html.append(f'<div class="line">{"".join(spans)}</div>')
        page_html.append(
            f'<div id="cap-{len(page_html)}" class="page clip" data-start="{cap_at + p["start"]:.3f}" '
            f'data-duration="{p["end"] - p["start"]:.3f}">{"".join(lines_html)}</div>'
        )

    fonts_css = "\n".join(
        f'      @font-face {{ font-family: "{f}"; src: url("fonts/{FONT_FILES[f][0]}") format("woff2"); '
        f"font-weight: {FONT_FILES[f][1]}; }}"
        for f in dict.fromkeys([body_font, code_font, *font_families(doc)])
    )
    bw, cw = FONT_FILES[body_font][1], FONT_FILES[code_font][1]
    logo_img = f'<img class="logo" src="{logo_src}" alt="" />' if logo_src else ""

    lower_third = ""
    if look["lower_third"] and (handle or brand.get("name")):
        lower_third = (f'<div id="lower" class="clip" data-start="{lead}" data-duration="{clip_d}">'
                       f'<i></i><b>{html.escape(brand.get("name") or "")}</b><span>{handle}</span></div>')
    cards = []
    if intro.get("enabled") and lead > 0:
        cards.append(
            f'<div id="intro" class="card clip" data-start="0" data-duration="{lead}">{logo_img}'
            f'<div class="bar"></div><h1 id="intro-title">{html.escape(intro.get("title", ""))}</h1></div>'
        )
    if outro.get("enabled") and dur - tail_at > 0:
        cards.append(
            f'<div id="outro" class="card clip" data-start="{tail_at}" data-duration="{round(dur - tail_at, 3)}">'
            f'{logo_img}<h1 id="outro-cta">{html.escape(outro.get("cta", ""))}</h1>'
            + (f'<p class="handle">{handle}</p>' if handle else "")
            + "</div>"
        )
    motion_script = "\n      ".join(motion_js)
    mark = ""
    if watermark.get("enabled") and (logo_src or handle):
        vert, horiz = watermark.get("position", "top-right").split("-")
        pos = f"{vert}: {SAFE_Y}px; {horiz}: 44px;"
        mark = (
            f'<div id="mark" class="clip" data-start="{lead}" data-duration="{clip_d}" style="{pos}">'
            + (f'<img src="{logo_src}" alt="" />' if logo_src else "")
            + (f"<span>{handle}</span>" if handle else "")
            + "</div>"
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w}, height={h}" />
    <title>{html.escape(doc["id"])}</title>
    <script src="gsap.min.js"></script>
    <style>
{fonts_css}
      html, body {{ margin: 0; background: {bg}; }}
      #root {{ position: relative; width: {w}px; height: {h}px; overflow: hidden; background: {bg}; }}
      .win {{ position: absolute; left: 0; top: 0; width: {w}px; height: {h}px; overflow: hidden; }}
      .cam {{ position: absolute; left: 0; top: 0; transform-origin: 0 0; }}
      .cam video {{ display: block; width: 100%; height: 100%; }}
      .text-overlay {{ position: absolute; max-width: calc(100% - 160px); white-space: pre-wrap;
                         font: {bw} 64px/1.2 "{body_font}", sans-serif; }}
      .code-panel {{ position: absolute; left: 56px; right: 56px; top: 300px; height: 900px; box-sizing: border-box;
                      display: flex; flex-direction: column; justify-content: center;
                      border: 3px solid {rgba(accent, 0.35)}; border-radius: 36px; padding: 56px 52px;
                      background: {rgba(text, 0.05)}; overflow: hidden; color: {text}; }}
      .code-panel header {{ display: flex; justify-content: space-between; align-items: center; gap: 24px;
                           font: {bw} 54px/1.2 "{body_font}", sans-serif; margin-bottom: 48px; }}
      .code-panel small {{ font-size: 32px; color: {accent}; text-transform: uppercase; letter-spacing: 0.08em; }}
      .code-panel pre {{ font: {cw} 46px/1.5 "{code_font}", monospace; white-space: pre-wrap; font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0;
                         overflow-wrap: anywhere; margin: 0; tab-size: 2; }}
      .tok-string {{ color: #a7e3bc; }} .tok-number {{ color: #f0c488; }}
      .tok-keyword, .tok-tag {{ color: #e9b5a5; }} .tok-comment {{ color: #9aa6a1; }}
      #caps {{ position: absolute; left: 48px; right: 48px; top: {style["safeTop"]}px; height: {style["safeBottom"] - style["safeTop"]}px; }}
      .page {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }}
      .line {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 0 10px; }}
      .w {{ font: {bw} {fs}px/1.2 "{body_font}", sans-serif; color: {text}; padding: 2px 12px; border-radius: 12px;
            background-color: rgba(0, 0, 0, 0); text-shadow: {shadow}; }}
      .w.code {{ font: {cw} {round(fs * 0.86)}px/1.2 "{code_font}", monospace; color: {accent};
                 background-color: {chip}; text-shadow: none; }}
      .boxed .page {{ inset: auto 0; top: 50%; transform: translateY(-50%); padding: 22px 18px; border-radius: 24px;
                      background: {rgba(bg, 0.82)}; }}
      .boxed .w {{ text-shadow: none; }}
{look["css"].format(accent=accent, bg=bg, text=text, fs=round(fs * 1.12), body=body_font)}
      .card {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
               gap: 36px; padding: 0 90px; background: {bg}; text-align: center; }}
      .card .logo {{ max-width: 520px; max-height: 300px; object-fit: contain; }}
      .card h1 {{ margin: 0; font: {bw} 84px/1.12 "{body_font}", sans-serif; color: {text}; letter-spacing: -0.01em; }}
      .card .bar {{ width: 140px; height: 10px; border-radius: 5px; background: {accent}; }}
      .card .handle {{ margin: 0; font: {bw} 52px/1.2 "{body_font}", sans-serif; color: {accent}; }}
      #mark {{ position: absolute; display: flex; align-items: center; gap: 14px; padding: 10px 18px; border-radius: 18px;
                background: {rgba(bg, 0.72)}; }}
      #mark img {{ height: 84px; max-width: 260px; object-fit: contain; }}
{motion.css(mctx) if motion_js else ""}
      #mark span {{ font: {bw} 34px/1 "{body_font}", sans-serif; color: {text}; text-shadow: {shadow}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="{w}" data-height="{h}" data-duration="{dur}">
      {"".join(media_html)}
      {"".join(overlays)}
      <div id="caps" class="{"boxed " if preset == "boxed" else ""}look-{doc.get("stylePreset", "focus")}">{"".join(page_html)}</div>
      {lower_third}
      {mark}
      {"".join(cards)}
    </div>
    <script>
      const CAMERAS = {json.dumps(cameras)};
      const CODE = {json.dumps(code_sequences)};
      const WORDS = {json.dumps(word_times)};
      const S = {json.dumps(states)};
      const FX = {json.dumps(fx)};
      const PUSH = {json.dumps(pushes)};
      const TD = {look["duration"]};
      const tl = gsap.timeline({{ paused: true }});
      CAMERAS.forEach(track => track.keys.forEach((k, i) => {{
        const win = {{ y: k.win[0], height: k.win[1] }}, cam = {{ x: k.cam[0], y: k.cam[1], scale: k.cam[2] }};
        if (k.jump) {{ tl.set(track.win, win, k.t); tl.set(track.cam, cam, k.t); return; }}
        const d = Math.max(k.t - track.keys[i - 1].t, 0.001), at = track.keys[i - 1].t;
        tl.to(track.win, {{ ...win, duration: d, ease: "none" }}, at);
        tl.to(track.cam, {{ ...cam, duration: d, ease: "none" }}, at);
      }}));
      CODE.forEach(sequence => {{
        const chars = document.querySelectorAll(sequence.selector);
        if (chars.length) tl.fromTo(chars, {{ opacity: 0 }}, {{ opacity: 1, duration: 0,
          stagger: sequence.duration / chars.length, ease: "none" }}, sequence.at);
      }});
      WORDS.forEach(([id, on, off, code]) => {{
        const el = "#w" + id;
        tl.set(el, code ? S.code_on : S.on, on);
        const after = code ? S.code_off : S.off;
        if (after) tl.set(el, after, off);
      }});
      const FROM = {{ fade: {{ opacity: 0 }}, slide: {{ opacity: 0, x: 160 }}, zoom: {{ opacity: 0, scale: 0.86 }} }};
      FX.forEach(({{ sel, s, e, kind }}) => {{
        const d = Math.min(TD, (e - s) / 2);
        tl.fromTo(sel, FROM[kind], {{ opacity: 1, x: 0, scale: 1, duration: d, ease: "power2.out" }}, s);
        tl.to(sel, {{ ...FROM[kind], duration: d, ease: "power2.in" }}, e - d);
      }});
      PUSH.forEach(({{ sel, s, d }}) => tl.fromTo(sel, {{ scale: 1 }}, {{ scale: 1.06, duration: d, ease: "none" }}, s));
      if (document.querySelector("#intro")) {{
        tl.fromTo("#intro .logo", {{ opacity: 0, scale: 0.9 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "power2.out" }}, 0.05);
        tl.fromTo("#intro .bar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.45, ease: "power2.out" }}, 0.2);
        tl.fromTo("#intro-title", {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.55, ease: "power2.out" }}, 0.3);
      }}
      if (document.querySelector("#outro")) {{
        tl.fromTo("#outro-cta", {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }}, {tail_at + 0.1});
        tl.fromTo("#outro .handle", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {tail_at + 0.4});
      }}
      {motion_script}
      tl.set({{}}, {{}}, {dur});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


# Creative style presets (schema `stylePreset`). CSS is formatted with the brand colours.
STYLES = {
    "focus": {"transition": "none", "duration": 0.4, "push": False, "lower_third": False, "css": ""},
    "energy": {"transition": "zoom", "duration": 0.25, "push": False, "lower_third": False, "css": (
        "      .look-energy .w {{ text-transform: uppercase; letter-spacing: 0.01em; font-size: {fs}px;"
        " -webkit-text-stroke: 2px rgba(0,0,0,.55); paint-order: stroke fill; }}\n"
        "      .look-energy .line {{ gap: 0 14px; }}")},
    "story": {"transition": "fade", "duration": 0.7, "push": True, "lower_third": False, "css": (
        "      .look-story .w {{ letter-spacing: 0.02em; text-shadow: 0 2px 18px rgba(0,0,0,.9); }}\n"
        "      .look-story .page {{ gap: 14px; }}")},
    "signature": {"transition": "slide", "duration": 0.45, "push": False, "lower_third": True, "css": (
        "      .look-signature .page {{ border-left: 10px solid {accent}; }}\n"
        "      #lower {{ position: absolute; left: 48px; right: 48px; bottom: 120px; display: flex; align-items: center; gap: 18px;"
        " padding: 20px 28px; border-radius: 20px; background: rgba(0,0,0,.55); }}\n"
        "      #lower i {{ width: 10px; align-self: stretch; border-radius: 5px; background: {accent}; }}\n"
        "      #lower b {{ font: 600 36px/1.1 \"{body}\", sans-serif; color: {text}; }}\n"
        "      #lower span {{ margin-left: auto; font: 500 32px/1 \"{body}\", sans-serif; color: {accent}; }}")},
}


def brand_ink(hex_color: str) -> str:
    """Dark or light text for legibility on the accent colour (WCAG relative luminance)."""
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    lum = sum(
        c * (v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        for c, v in zip((0.2126, 0.7152, 0.0722), (r, g, b))
    )
    return "#141005" if lum > 0.35 else "#ffffff"


def write_project(doc: dict, project_dir: Path) -> Path:
    """index.html + the fonts it uses. The caller places the source media (and logo) at their asset `src`."""
    (project_dir / "fonts").mkdir(parents=True, exist_ok=True)
    for family in font_families(doc):
        name = FONT_FILES[family][0]
        shutil.copyfile(FONTS_DIR / name, project_dir / "fonts" / name)
    shutil.copyfile(GSAP_FILE, project_dir / GSAP_FILE.name)
    (project_dir / "timeline.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    index = project_dir / "index.html"
    index.write_text(compile_html(doc), encoding="utf-8")
    return index
