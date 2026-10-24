"""Motion-graphics templates for the Hyperframes compiler (timeline item `type: "motion"`).

Each template is original, reusable and editable: text `fields` (with defaults and length limits), up to N `media`
slots (images/clips shown inside mockups, galleries, split screens), brand colours/fonts, and an `intensity` that
scales travel distances. A template returns (html, js) where js adds tweens to the composition's single paused GSAP
timeline `tl` at absolute times, so every frame is seek-safe and deterministic.

Techniques follow what the reference analysis measured in designed ads (REFERENCE_STYLE_ANALYSIS.md, Reference 3/6):
blur-to-sharp type, staggered words, floating cards in perspective, browser/phone/laptop mockups, counters, charts,
calendars, chat bubbles, masks, light sweeps, glowing arcs, logo reveals, eased camera drift and morph-like exits.
User text is always HTML-escaped; nothing from the timeline is executed.
"""

import html
import json

E = html.escape
SCENE, OVERLAY = "scene", "overlay"


def _f(item: dict, key: str, default: str = "") -> str:
    return E(str((item.get("fields") or {}).get(key, default)))[:400]


def _lines(item: dict, key: str, default: str, n: int) -> list[str]:
    raw = str((item.get("fields") or {}).get(key, default))
    return [E(x.strip()) for x in raw.replace("|", "\n").split("\n") if x.strip()][:n]


def _media(item: dict, ctx: dict, k: int, cls: str = "mg-fill") -> str:
    """<img>/<video> for media slot k, or a branded placeholder panel when the slot is empty."""
    ids = item.get("media") or []
    if k >= len(ids) or ids[k] not in ctx["assets"]:
        return f'<div class="{cls} mg-ph"></div>'
    a = ctx["assets"][ids[k]]
    if a["kind"] == "image":
        return f'<img class="{cls}" src="{E(a["src"])}" alt="" />'
    # framework-owned playback: Hyperframes seeks this video with the composition clock
    return (f'<video id="mv-{item["id"]}-{k}" class="{cls} clip" src="{E(a["src"])}" muted data-start="{item["start"]}" '
            f'data-duration="{item["duration"]}" data-media-start="0" '
            f'data-has-audio="false"></video>')


def _words(text: str, cls: str = "mg-w") -> str:
    return " ".join(f'<span class="{cls}">{w}</span>' for w in text.split())


class Scene:
    """Builds one template instance: element ids are prefixed, tweens use absolute times."""

    def __init__(self, item: dict, idx: int, ctx: dict):
        self.item, self.ctx, self.p = item, ctx, f"m{idx}"
        self.s, self.d = float(item["start"]), float(item["duration"])
        self.k = 0.6 + 0.8 * float(item.get("intensity", 0.6))  # travel multiplier
        self.js: list[str] = []

    def sel(self, part: str = "") -> str:
        return f"#{self.p}{(' ' + part) if part else ''}"

    def tw(self, target: str, frm: dict, to: dict, at: float, stagger: float = 0) -> None:
        to = {**to, "duration": to.get("duration", 0.6), "ease": to.get("ease", "power3.out")}
        if stagger:
            to["stagger"] = stagger
        self.js.append(f"tl.fromTo({json.dumps(target)}, {json.dumps(frm)}, {json.dumps(to)}, {round(self.s + at, 3)});")

    def to(self, target: str, to: dict, at: float) -> None:
        to = {**to, "duration": to.get("duration", 0.6), "ease": to.get("ease", "power2.inOut")}
        self.js.append(f"tl.to({json.dumps(target)}, {json.dumps(to)}, {round(self.s + at, 3)});")

    def wrap(self, kind: str, body: str, extra_cls: str = "") -> str:
        """Scene wrapper with entry, slow camera drift and a morph-like exit (scale + blur + fade)."""
        bg = '<div class="mg-bg"></div><div class="mg-glow"></div>' if kind == SCENE else ""
        self.tw(self.sel(), {"opacity": 0, "scale": 1.06, "filter": "blur(18px)"},
                {"opacity": 1, "scale": 1, "filter": "blur(0px)", "duration": 0.45}, 0)
        self.tw(self.sel(".mg-cam"), {"scale": 1, "rotateX": 0, "y": 0},
                {"scale": 1 + 0.05 * self.k, "rotateX": 2 * self.k, "y": -20 * self.k, "duration": self.d, "ease": "none"}, 0)
        if self.s + self.d < self.ctx.get("dur", 1e9) - 0.05:  # the closing scene holds to the last frame
            out = max(self.d - 0.4, 0.5)
            self.to(self.sel(), {"opacity": 0, "scale": 0.94, "filter": "blur(14px)", "duration": 0.38, "ease": "power2.in"}, out)
        return (f'<div id="{self.p}" class="mg {kind} {extra_cls} clip" data-start="{self.s}" data-duration="{self.d}">'
                f'{bg}<div class="mg-cam">{body}</div></div>')


# ---- templates -------------------------------------------------------------------------------------------------


def kinetic_title(sc: Scene) -> str:
    text, emph = _f(sc.item, "text", "Make it move"), _f(sc.item, "emphasis")
    words = " ".join(f'<span class="mg-w{" mg-accent" if emph and w.lower() == emph.lower() else ""}">{w}</span>' for w in text.split())
    sc.tw(sc.sel(".mg-w"), {"opacity": 0, "y": 90 * sc.k, "rotate": 6, "scale": 0.7},
          {"opacity": 1, "y": 0, "rotate": 0, "scale": 1, "duration": 0.55, "ease": "back.out(1.8)"}, 0.15, 0.09)
    sc.tw(sc.sel(".mg-accent"), {"scale": 1}, {"scale": 1.12, "duration": 0.25, "yoyo": True, "repeat": 1}, 0.9)
    return sc.wrap(SCENE, f'<h1 class="mg-kinetic">{words}</h1>')


def blur_reveal(sc: Scene) -> str:
    title, sub = _f(sc.item, "text", "Designed to be seen"), _f(sc.item, "subtitle")
    # spread → settle as a transform (letter-spacing reflows text and stutters under frame-by-frame capture)
    sc.tw(sc.sel(".mg-serif"), {"opacity": 0, "filter": "blur(30px)", "scaleX": 1.25, "scaleY": 0.96},
          {"opacity": 1, "filter": "blur(0px)", "scaleX": 1, "scaleY": 1, "duration": 1.2, "ease": "expo.out"}, 0.1)
    sc.tw(sc.sel(".mg-rule"), {"scaleX": 0}, {"scaleX": 1, "duration": 0.8}, 0.7)
    sc.tw(sc.sel(".mg-sub"), {"opacity": 0, "y": 30}, {"opacity": 1, "y": 0}, 0.9)
    return sc.wrap(SCENE, f'<div class="mg-center"><h1 class="mg-serif">{title}</h1><i class="mg-rule"></i><p class="mg-sub">{sub}</p></div>')


def stagger_lines(sc: Scene) -> str:
    lines = _lines(sc.item, "lines", "Plan|Shoot|Edit|Publish", 6)
    body = "".join(f'<div class="mg-line"><span>{x}</span></div>' for x in lines)
    sc.tw(sc.sel(".mg-line span"), {"yPercent": 110}, {"yPercent": 0, "duration": 0.6, "ease": "power4.out"}, 0.1, 0.12)
    return sc.wrap(SCENE, f'<div class="mg-stack">{body}</div>')


def typewriter(sc: Scene) -> str:
    text = _f(sc.item, "text", "Type anything here")
    words = html.unescape(text)[:120].split(" ")  # characters inside nowrap words, so lines break between words
    chars = " ".join('<span class="mg-tw">' + "".join(f'<span class="mg-ch">{E(c)}</span>' for c in w) + "</span>" for w in words)
    n = max(len(html.unescape(text)[:120]), 1)
    sc.tw(sc.sel(".mg-ch"), {"opacity": 0}, {"opacity": 1, "duration": 0.01, "ease": "none"}, 0.2, min(0.06, (sc.d * 0.6) / n))
    sc.js.append(f'tl.fromTo("{sc.sel(".mg-caret")}", {{opacity:1}}, {{opacity:0, duration:0.4, repeat:{int(sc.d / 0.4)}, yoyo:true, ease:"steps(1)"}}, {sc.s});')
    return sc.wrap(SCENE, f'<div class="mg-type">{chars}<b class="mg-caret">|</b></div>')


def masked_text(sc: Scene) -> str:
    text = _f(sc.item, "text", "Bold ideas")
    sc.tw(sc.sel(".mg-mask"), {"clipPath": "inset(0 100% 0 0)"}, {"clipPath": "inset(0 0% 0 0)", "duration": 0.9, "ease": "power4.inOut"}, 0.1)
    sc.tw(sc.sel(".mg-mask-fill"), {"backgroundPosition": "0% 50%"}, {"backgroundPosition": "100% 50%", "duration": sc.d, "ease": "none"}, 0)
    return sc.wrap(SCENE, f'<h1 class="mg-mask"><span class="mg-mask-fill">{text}</span></h1>')


def counter(sc: Scene) -> str:
    raw = str((sc.item.get("fields") or {}).get("value", "100"))
    digits = "".join(c for c in raw if c.isdigit() or c == ".") or "0"
    value = float(digits)
    dec = len(digits.split(".")[1]) if "." in digits else 0
    pre, suf, label = _f(sc.item, "prefix"), _f(sc.item, "suffix"), _f(sc.item, "label", "and counting")
    sc.js.append(f'(() => {{ const o = {{v: 0}}, el = document.querySelector("{sc.sel(".mg-num")}"); '
                 f'tl.to(o, {{v: {value}, duration: {min(1.6, sc.d * 0.5):.2f}, ease: "power2.out", '
                 f'onUpdate: () => {{ el.textContent = o.v.toFixed({dec}).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ","); }} }}, {sc.s + 0.2}); }})();')
    sc.tw(sc.sel(".mg-label"), {"opacity": 0, "y": 24}, {"opacity": 1, "y": 0}, 0.6)
    return sc.wrap(SCENE, f'<div class="mg-center"><div class="mg-count">{pre}<span class="mg-num">0</span>{suf}</div><p class="mg-label">{label}</p></div>')


def floating_cards(sc: Scene) -> str:
    cards = _lines(sc.item, "cards", "Fast|Local|Free", 4)
    notes = _lines(sc.item, "notes", "", 4)
    body = "".join(f'<div class="mg-card" style="--i:{i}"><b>{c}</b><span>{notes[i] if i < len(notes) else ""}</span></div>' for i, c in enumerate(cards))
    sc.tw(sc.sel(".mg-card"), {"opacity": 0, "y": 260 * sc.k, "rotateX": 40, "z": -200},
          {"opacity": 1, "y": 0, "rotateX": 0, "z": 0, "duration": 0.8, "ease": "power3.out"}, 0.15, 0.14)
    sc.js.append(f'document.querySelectorAll("{sc.sel(".mg-card")}").forEach((c, i) => tl.to(c, {{y: (i % 2 ? 18 : -18) * {sc.k:.2f}, duration: {sc.d:.2f}, ease: "sine.inOut"}}, {sc.s + 0.9}));')
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{_f(sc.item, "title")}</h2><div class="mg-cards">{body}</div>')


def browser_mockup(sc: Scene) -> str:
    url, head, btn = _f(sc.item, "url", ""), _f(sc.item, "headline", "Your website, alive"), _f(sc.item, "button", "")
    page = (_media(sc.item, sc.ctx, 0, "mg-shot") if sc.item.get("media")
            else f'<div class="mg-site"><h3>{head}</h3><p class="mg-skel"></p><p class="mg-skel s"></p><em>{btn}</em><div class="mg-tiles"><i></i><i></i><i></i></div></div>')
    sc.tw(sc.sel(".mg-browser"), {"opacity": 0, "y": 400 * sc.k, "rotateY": -28, "rotateX": 18},
          {"opacity": 1, "y": 0, "rotateY": -10, "rotateX": 6, "duration": 1.1, "ease": "expo.out"}, 0.1)
    if sc.item.get("media"):  # a screenshot fills the window and drifts closer; a generated page scrolls
        sc.tw(sc.sel(".mg-shot"), {"scale": 1}, {"scale": 1.12, "duration": max(sc.d - 1.0, 0.5), "ease": "sine.inOut"}, 1.0)
    else:
        sc.tw(sc.sel(".mg-site"), {"y": 0}, {"y": -220 * sc.k, "duration": max(sc.d - 1.2, 0.5), "ease": "sine.inOut"}, 1.0)
    sc.tw(sc.sel(".mg-sweep"), {"xPercent": -150}, {"xPercent": 250, "duration": 1.0, "ease": "power2.inOut"}, 0.9)
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{_f(sc.item, "title")}</h2><div class="mg-browser"><div class="mg-bar"><i></i><i></i><i></i><span>{url}</span></div>'
                          f'<div class="mg-view">{page}</div><div class="mg-sweep"></div></div>')


def phone_mockup(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-phone"), {"opacity": 0, "y": 500 * sc.k, "rotate": -8}, {"opacity": 1, "y": 0, "rotate": -3, "duration": 1.0, "ease": "expo.out"}, 0.1)
    sc.tw(sc.sel(".mg-phone"), {"rotate": -3}, {"rotate": 2, "duration": sc.d, "ease": "sine.inOut"}, 1.0)
    sc.tw(sc.sel(".mg-caption"), {"opacity": 0, "x": -60}, {"opacity": 1, "x": 0}, 0.6)
    return sc.wrap(SCENE, f'<div class="mg-phone"><div class="mg-notch"></div><div class="mg-screen">{_media(sc.item, sc.ctx, 0)}</div></div>'
                          f'<p class="mg-caption">{_f(sc.item, "caption")}</p>')


def laptop_mockup(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-lid"), {"rotateX": -88}, {"rotateX": 0, "duration": 1.1, "ease": "power3.out"}, 0.15)
    sc.tw(sc.sel(".mg-laptop"), {"opacity": 0, "scale": 0.8}, {"opacity": 1, "scale": 1, "duration": 0.7}, 0)
    sc.tw(sc.sel(".mg-laptop"), {"rotateY": -14}, {"rotateY": 8, "duration": sc.d, "ease": "sine.inOut"}, 0.2)
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{_f(sc.item, "title")}</h2><div class="mg-laptop"><div class="mg-lid"><div class="mg-screen">{_media(sc.item, sc.ctx, 0)}</div></div><div class="mg-base"></div></div>')


def split_screen(sc: Scene) -> str:
    a, b = _f(sc.item, "left", "Before"), _f(sc.item, "right", "After")
    sc.tw(sc.sel(".mg-half.r"), {"clipPath": "inset(0 0 0 100%)"}, {"clipPath": "inset(0 0 0 0%)", "duration": 1.0, "ease": "power3.inOut"}, 0.5)
    sc.tw(sc.sel(".mg-divider"), {"x": sc.ctx.get("w", 1080) / 2}, {"x": 0, "duration": 1.0, "ease": "power3.inOut"}, 0.5)
    sc.tw(sc.sel(".mg-tag"), {"opacity": 0, "y": -30}, {"opacity": 1, "y": 0}, 0.3, 0.6)
    return sc.wrap(SCENE, f'<div class="mg-split"><div class="mg-half l">{_media(sc.item, sc.ctx, 0)}<span class="mg-tag">{a}</span></div>'
                          f'<div class="mg-half r">{_media(sc.item, sc.ctx, 1)}<span class="mg-tag">{b}</span></div><i class="mg-divider"></i></div>')


def info_list(sc: Scene) -> str:
    items = _lines(sc.item, "items", "Upload your clips|Describe the edit|Download the reel", 5)
    body = "".join(f'<li><b>{i + 1:02d}</b><span>{x}</span><i></i></li>' for i, x in enumerate(items))
    sc.tw(sc.sel("li"), {"opacity": 0, "x": -120 * sc.k}, {"opacity": 1, "x": 0, "duration": 0.6}, 0.3, 0.28)
    sc.tw(sc.sel("li i"), {"scaleX": 0}, {"scaleX": 1, "duration": 0.7}, 0.5, 0.28)
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{_f(sc.item, "title", "How it works")}</h2><ol class="mg-list">{body}</ol>')


def chat_bubbles(sc: Scene) -> str:
    msgs = _lines(sc.item, "messages", "Can you edit this by tonight?|Already done ✅|Wow, that was fast", 5)
    body = "".join(f'<div class="mg-msg {"me" if i % 2 else ""}">{m}</div>' for i, m in enumerate(msgs))
    step = min(1.0, (sc.d - 1) / max(len(msgs), 1))
    for i in range(len(msgs)):
        sc.tw(sc.sel(f".mg-msg:nth-child({i + 1})"), {"opacity": 0, "y": 40, "scale": 0.8},
              {"opacity": 1, "y": 0, "scale": 1, "duration": 0.4, "ease": "back.out(2)"}, 0.3 + i * step)
    return sc.wrap(SCENE, f'<div class="mg-chat">{body}</div>')


def calendar(sc: Scene) -> str:
    month, day = _f(sc.item, "month", "LAUNCH WEEK"), int("".join(c for c in str((sc.item.get("fields") or {}).get("day", "18")) if c.isdigit()) or 18)
    day = min(max(day, 1), 30)
    cells = "".join(f'<i class="{"hit" if d == day else ""}">{d}</i>' for d in range(1, 31))
    sc.tw(sc.sel(".mg-cal i"), {"opacity": 0, "scale": 0.4}, {"opacity": 1, "scale": 1, "duration": 0.3, "ease": "back.out(2)"}, 0.2, 0.02)
    sc.tw(sc.sel(".mg-cal .hit"), {"backgroundColor": "rgba(0,0,0,0)"}, {"backgroundColor": sc.ctx["accent"], "color": sc.ctx["ink"], "scale": 1.25, "duration": 0.4}, 1.1)
    sc.tw(sc.sel(".mg-note"), {"opacity": 0, "y": 30}, {"opacity": 1, "y": 0}, 1.4)
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{month}</h2><div class="mg-cal">{cells}</div><p class="mg-note">{_f(sc.item, "note")}</p>')


def bar_chart(sc: Scene) -> str:
    labels = _lines(sc.item, "labels", "Jan|Feb|Mar|Apr", 6)
    raw = [x for x in str((sc.item.get("fields") or {}).get("values", "30|45|70|100")).replace(",", "|").split("|") if x.strip()]
    vals = [float("".join(c for c in v if c.isdigit() or c == ".") or 0) for v in raw][: len(labels)] or [1]
    top = max(vals) or 1
    bars = "".join(f'<div class="mg-col"><i style="height:{v / top * 100:.0f}%"><b>{E(raw[i].strip())}</b></i><span>{labels[i]}</span></div>' for i, v in enumerate(vals))
    sc.tw(sc.sel(".mg-col i"), {"scaleY": 0}, {"scaleY": 1, "duration": 0.8, "ease": "power3.out"}, 0.3, 0.12)
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{_f(sc.item, "title")}</h2><div class="mg-chart">{bars}</div>')


def stat_ring(sc: Scene) -> str:
    pct = min(max(float("".join(c for c in str((sc.item.get("fields") or {}).get("percent", "87")) if c.isdigit() or c == ".") or 0), 0), 100)
    c = 2 * 3.14159 * 260
    sc.tw(sc.sel(".mg-arc"), {"strokeDashoffset": c}, {"strokeDashoffset": c * (1 - pct / 100), "duration": 1.4, "ease": "power2.out"}, 0.2)
    sc.tw(sc.sel(".mg-ring-label"), {"opacity": 0, "scale": 0.7}, {"opacity": 1, "scale": 1}, 0.6)
    return sc.wrap(SCENE, f'<svg class="mg-ring" viewBox="0 0 600 600"><circle cx="300" cy="300" r="260" class="mg-track"/>'
                          f'<circle cx="300" cy="300" r="260" class="mg-arc" stroke-dasharray="{c:.1f}" stroke-dashoffset="{c:.1f}"/></svg>'
                          f'<div class="mg-ring-label"><b>{pct:g}%</b><span>{_f(sc.item, "label")}</span></div>')


def logo_reveal(sc: Scene) -> str:
    logo = sc.ctx.get("logo")
    mark = f'<img class="mg-logo" src="{E(logo)}" alt="" />' if logo else f'<h1 class="mg-wordmark">{_f(sc.item, "name", sc.ctx.get("name") or "Your brand")}</h1>'
    sc.tw(sc.sel(".mg-logo, .mg-wordmark"), {"opacity": 0, "scale": 1.4, "filter": "blur(24px)"},
          {"opacity": 1, "scale": 1, "filter": "blur(0px)", "duration": 1.0, "ease": "expo.out"}, 0.15)
    sc.tw(sc.sel(".mg-sweep"), {"xPercent": -150}, {"xPercent": 250, "duration": 1.1, "ease": "power2.inOut"}, 0.8)
    sc.tw(sc.sel(".mg-tagline"), {"opacity": 0, "scaleX": 1.4}, {"opacity": 1, "scaleX": 1, "duration": 1.0}, 1.0)
    return sc.wrap(SCENE, f'<div class="mg-center mg-brand">{mark}<div class="mg-sweep"></div><p class="mg-tagline">{_f(sc.item, "tagline")}</p></div>')


def cta_button(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-cta-h"), {"opacity": 0, "y": 50}, {"opacity": 1, "y": 0}, 0.1)
    sc.tw(sc.sel(".mg-btn"), {"opacity": 0, "scale": 0.5}, {"opacity": 1, "scale": 1, "duration": 0.5, "ease": "back.out(2.2)"}, 0.5)
    sc.tw(sc.sel(".mg-cursor"), {"x": 260, "y": 260, "opacity": 0}, {"x": 40, "y": 30, "opacity": 1, "duration": 0.7}, 0.9)
    sc.tw(sc.sel(".mg-btn"), {"scale": 1}, {"scale": 0.92, "duration": 0.12, "yoyo": True, "repeat": 1}, 1.6)
    sc.tw(sc.sel(".mg-pulse"), {"scale": 1, "opacity": 0.7}, {"scale": 1.8, "opacity": 0, "duration": 0.8}, 1.65)
    return sc.wrap(SCENE, f'<div class="mg-center"><h2 class="mg-cta-h">{_f(sc.item, "headline", "Ready when you are")}</h2>'
                          f'<div class="mg-btnwrap"><i class="mg-pulse"></i><em class="mg-btn">{_f(sc.item, "button", "Start now")}</em><b class="mg-cursor">➤</b></div>'
                          f'<p class="mg-sub">{_f(sc.item, "detail")}</p></div>')


def pricing_card(sc: Scene) -> str:
    feats = _lines(sc.item, "features", "Unlimited edits|Beat-synced cuts|Instagram ready", 5)
    body = "".join(f"<li>✓ {x}</li>" for x in feats)
    sc.tw(sc.sel(".mg-price-card"), {"opacity": 0, "y": 200 * sc.k, "rotateX": 30}, {"opacity": 1, "y": 0, "rotateX": 0, "duration": 0.9}, 0.1)
    sc.tw(sc.sel(".mg-price-card li"), {"opacity": 0, "x": -40}, {"opacity": 1, "x": 0, "duration": 0.4}, 0.7, 0.15)
    sc.tw(sc.sel(".mg-price-card"), {"boxShadow": "0 0 0px rgba(0,0,0,0)"}, {"boxShadow": f"0 0 90px {sc.ctx['accent']}", "duration": 1.2, "yoyo": True, "repeat": 1}, 1.0)
    return sc.wrap(SCENE, f'<div class="mg-price-card"><span>{_f(sc.item, "plan", "Pro")}</span><b>{_f(sc.item, "price", "")}</b><ul>{body}</ul></div>')


def lower_third(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-lt"), {"clipPath": "inset(0 100% 0 0)"}, {"clipPath": "inset(0 0% 0 0)", "duration": 0.7, "ease": "power4.out"}, 0.05)
    sc.tw(sc.sel(".mg-lt span"), {"opacity": 0, "y": 20}, {"opacity": 1, "y": 0}, 0.45)
    return sc.wrap(OVERLAY, f'<div class="mg-lt"><b>{_f(sc.item, "name", "Name")}</b><span>{_f(sc.item, "role")}</span></div>')


def light_sweep(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-beam"), {"xPercent": -120, "opacity": 0}, {"xPercent": 120, "opacity": 1, "duration": min(sc.d, 1.4), "ease": "power2.inOut"}, 0)
    return sc.wrap(OVERLAY, '<div class="mg-beam"></div>')


def glow_arc(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-arcs path"), {"strokeDashoffset": 2400}, {"strokeDashoffset": 0, "duration": 1.4, "ease": "power2.inOut"}, 0.1, 0.18)
    sc.tw(sc.sel(".mg-arc-text"), {"opacity": 0, "filter": "blur(16px)"}, {"opacity": 1, "filter": "blur(0px)", "duration": 0.9}, 0.8)
    return sc.wrap(SCENE, '<svg class="mg-arcs" viewBox="0 0 1080 1920"><path d="M-100 1500 Q540 300 1180 1500"/><path d="M-100 1650 Q540 520 1180 1650"/>'
                          f'<path d="M-100 1800 Q540 740 1180 1800"/></svg><h1 class="mg-arc-text mg-serif">{_f(sc.item, "text", "Light up your launch")}</h1>')


def shape_burst(sc: Scene) -> str:
    shapes = "".join(f'<i class="mg-shape" style="--a:{a}deg"></i>' for a in range(0, 360, 30))
    sc.tw(sc.sel(".mg-shape"), {"scale": 0, "opacity": 1}, {"scale": 1, "opacity": 0, "duration": 0.9, "ease": "expo.out"}, 0.05, 0.02)
    sc.tw(sc.sel(".mg-burst-t"), {"scale": 0.3, "opacity": 0}, {"scale": 1, "opacity": 1, "duration": 0.6, "ease": "back.out(2)"}, 0.15)
    return sc.wrap(OVERLAY, f'<div class="mg-burst">{shapes}</div><h1 class="mg-burst-t">{_f(sc.item, "text", "NEW")}</h1>')


def grid_gallery(sc: Scene) -> str:
    n = max(len(sc.item.get("media") or []), 4)
    tiles = "".join(f'<div class="mg-tile">{_media(sc.item, sc.ctx, i)}</div>' for i in range(min(n, 6)))
    sc.tw(sc.sel(".mg-tile"), {"opacity": 0, "scale": 0.6, "rotate": -6}, {"opacity": 1, "scale": 1, "rotate": 0, "duration": 0.6, "ease": "back.out(1.6)"}, 0.1, 0.1)
    return sc.wrap(SCENE, f'<h2 class="mg-h2">{_f(sc.item, "title")}</h2><div class="mg-grid">{tiles}</div>')


def notifications(sc: Scene) -> str:
    notes = _lines(sc.item, "items", "New follower|12 new comments|Your reel is trending", 4)
    body = "".join(f'<div class="mg-toast"><i></i><div><b>{_f(sc.item, "app", "Reels")}</b><span>{x}</span></div></div>' for x in notes)
    sc.tw(sc.sel(".mg-toast"), {"opacity": 0, "y": -140, "scale": 0.9}, {"opacity": 1, "y": 0, "scale": 1, "duration": 0.5, "ease": "back.out(1.6)"}, 0.2, 0.45)
    return sc.wrap(SCENE, f'<div class="mg-toasts">{body}</div>')


def media_card(sc: Scene) -> str:
    sc.tw(sc.sel(".mg-vcard"), {"opacity": 0, "y": 300 * sc.k, "rotateY": 25}, {"opacity": 1, "y": 0, "rotateY": 0, "duration": 0.9, "ease": "expo.out"}, 0.1)
    sc.tw(sc.sel(".mg-vlabel"), {"opacity": 0, "x": 60}, {"opacity": 1, "x": 0}, 0.6)
    return sc.wrap(SCENE, f'<div class="mg-vcard">{_media(sc.item, sc.ctx, 0)}</div><p class="mg-vlabel">{_f(sc.item, "label")}</p>')


TEMPLATES: dict[str, dict] = {
    "kinetic_title": {"fn": kinetic_title, "description": "bold words pop in one by one, one word highlighted", "fields": {"text": 60, "emphasis": 20}, "media": 0, "sfx": [("whoosh", 0.1), ("impact", 0.9)]},
    "blur_reveal": {"fn": blur_reveal, "description": "cinematic serif heading sharpens out of blur, thin rule, subtitle", "fields": {"text": 50, "subtitle": 80}, "media": 0, "sfx": [("riser", 0.0)]},
    "stagger_lines": {"fn": stagger_lines, "description": "stacked words/lines slide up through masks", "fields": {"lines": 120}, "media": 0, "sfx": [("whoosh", 0.1)]},
    "typewriter": {"fn": typewriter, "description": "text typed letter by letter with a cursor", "fields": {"text": 120}, "media": 0, "sfx": [("tick", 0.2)]},
    "masked_text": {"fn": masked_text, "description": "huge gradient text revealed by a wipe mask", "fields": {"text": 30}, "media": 0, "sfx": [("whoosh", 0.1)]},
    "counter": {"fn": counter, "description": "number counts up with a label (only real numbers from the request)", "fields": {"value": 12, "prefix": 4, "suffix": 6, "label": 50}, "media": 0, "sfx": [("riser", 0.0), ("impact", 1.6)]},
    "floating_cards": {"fn": floating_cards, "description": "up to 4 feature cards float in 3D perspective", "fields": {"title": 50, "cards": 80, "notes": 160}, "media": 0, "sfx": [("whoosh", 0.15)]},
    "browser_mockup": {"fn": browser_mockup, "description": "browser window flies in tilted, page scrolls, light sweep (media 1 = website screenshot)", "fields": {"title": 50, "url": 40, "headline": 50, "button": 20}, "media": 1, "sfx": [("whoosh", 0.1)]},
    "phone_mockup": {"fn": phone_mockup, "description": "phone rises with a tilt showing a clip or screenshot", "fields": {"caption": 60}, "media": 1, "sfx": [("whoosh", 0.1)]},
    "laptop_mockup": {"fn": laptop_mockup, "description": "laptop lid opens onto a clip or screenshot", "fields": {"title": 50}, "media": 1, "sfx": [("whoosh", 0.15)]},
    "split_screen": {"fn": split_screen, "description": "before/after split with an animated divider (2 media)", "fields": {"left": 20, "right": 20}, "media": 2, "sfx": [("whoosh", 0.5)]},
    "info_list": {"fn": info_list, "description": "numbered infographic list builds step by step", "fields": {"title": 50, "items": 200}, "media": 0, "sfx": [("tick", 0.3)]},
    "chat_bubbles": {"fn": chat_bubbles, "description": "chat messages pop in alternately", "fields": {"messages": 220}, "media": 0, "sfx": [("tick", 0.3)]},
    "calendar": {"fn": calendar, "description": "month grid builds, one date highlighted", "fields": {"month": 30, "day": 2, "note": 60}, "media": 0, "sfx": [("tick", 0.2), ("impact", 1.1)]},
    "bar_chart": {"fn": bar_chart, "description": "bar chart grows (only real values from the request)", "fields": {"title": 50, "labels": 80, "values": 60}, "media": 0, "sfx": [("riser", 0.2)]},
    "stat_ring": {"fn": stat_ring, "description": "glowing ring fills to a percentage (only real numbers)", "fields": {"percent": 4, "label": 40}, "media": 0, "sfx": [("riser", 0.1)]},
    "logo_reveal": {"fn": logo_reveal, "description": "brand logo/name sharpens with a light sweep and tagline", "fields": {"name": 40, "tagline": 60}, "media": 0, "sfx": [("riser", 0.0), ("impact", 1.0)]},
    "cta_button": {"fn": cta_button, "description": "headline, button pops, cursor clicks it", "fields": {"headline": 50, "button": 24, "detail": 60}, "media": 0, "sfx": [("tick", 1.6)]},
    "pricing_card": {"fn": pricing_card, "description": "pricing card with glowing border and features (only real prices)", "fields": {"plan": 20, "price": 16, "features": 160}, "media": 0, "sfx": [("whoosh", 0.1)]},
    "lower_third": {"fn": lower_third, "description": "name/title bar over footage", "fields": {"name": 40, "role": 50}, "media": 0, "sfx": []},
    "light_sweep": {"fn": light_sweep, "description": "diagonal light beam across the frame over footage", "fields": {}, "media": 0, "sfx": [("whoosh", 0.2)]},
    "glow_arc": {"fn": glow_arc, "description": "glowing arcs draw across the frame behind a serif line", "fields": {"text": 50}, "media": 0, "sfx": [("riser", 0.0)]},
    "shape_burst": {"fn": shape_burst, "description": "radial shape burst behind a short word over footage", "fields": {"text": 12}, "media": 0, "sfx": [("impact", 0.1)]},
    "grid_gallery": {"fn": grid_gallery, "description": "grid of up to 6 clips/images pops in", "fields": {"title": 50}, "media": 6, "sfx": [("whoosh", 0.1)]},
    "notifications": {"fn": notifications, "description": "social notifications stack in from the top", "fields": {"app": 20, "items": 160}, "media": 0, "sfx": [("tick", 0.2)]},
    "media_card": {"fn": media_card, "description": "one clip as a floating rounded video card with a label", "fields": {"label": 50}, "media": 1, "sfx": [("whoosh", 0.1)]},
}


def css(ctx: dict) -> str:
    bg, text, accent, ink, body, serif = ctx["bg"], ctx["text"], ctx["accent"], ctx["ink"], ctx["body_font"], ctx["display_font"]
    return f"""
      .mg {{ position: absolute; inset: 0; perspective: 1600px; overflow: hidden; color: {text}; font-family: "{body}", sans-serif; }}
      .mg-cam {{ position: absolute; inset: 0; transform-style: preserve-3d; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 48px; padding: 0 72px; box-sizing: border-box; }}
      .mg-bg {{ position: absolute; inset: 0; background: radial-gradient(120% 80% at 50% 30%, color-mix(in srgb, {bg} 75%, {accent} 25%), {bg} 70%); }}
      .mg-glow {{ position: absolute; width: 900px; height: 900px; left: 50%; top: 40%; transform: translate(-50%,-50%); border-radius: 50%; background: {accent}; opacity: .16; filter: blur(160px); }}
      .mg-accent {{ color: {accent}; }}
      .mg-kinetic {{ margin: 0; text-align: center; font: 800 132px/1.02 "{body}", sans-serif; letter-spacing: -0.03em; text-transform: uppercase; }}
      .mg-kinetic .mg-w {{ display: inline-block; }}
      .mg-center {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: 28px; }}
      .mg-serif {{ margin: 0; font: 600 118px/1.04 "{serif}", serif; letter-spacing: -0.01em; text-align: center; }}
      .mg-rule {{ display: block; width: 220px; height: 4px; background: {accent}; transform-origin: left; }}
      .mg-sub {{ margin: 0; font: 500 44px/1.3 "{body}", sans-serif; opacity: .8; max-width: 860px; }}
      .mg-h2 {{ margin: 0; font: 700 72px/1.1 "{body}", sans-serif; text-align: center; letter-spacing: -0.02em; }}
      .mg-h2:empty {{ display: none; }}
      .mg-stack {{ display: flex; flex-direction: column; gap: 6px; }}
      .mg-line {{ overflow: hidden; }} .mg-line span {{ display: block; font: 800 150px/1.0 "{body}", sans-serif; text-transform: uppercase; letter-spacing: -0.04em; }}
      .mg-line:nth-child(even) span {{ color: {accent}; }}
      .mg-type {{ font: 600 76px/1.3 "{ctx["code_font"]}", monospace; text-align: left; max-width: 920px; }}
      .mg-caret {{ color: {accent}; }} .mg-tw {{ white-space: nowrap; }}
      .mg-mask {{ margin: 0; font: 900 230px/0.95 "{body}", sans-serif; text-transform: uppercase; text-align: center; letter-spacing: -0.05em; }}
      .mg-mask-fill {{ background: linear-gradient(90deg, {text}, {accent}, {text}, {accent}); background-size: 300% 100%; -webkit-background-clip: text; background-clip: text; color: transparent; }}
      .mg-count {{ font: 800 210px/1 "{body}", sans-serif; letter-spacing: -0.04em; font-variant-numeric: tabular-nums; }}
      .mg-label {{ margin: 0; font: 600 52px/1.2 "{body}", sans-serif; color: {accent}; text-transform: uppercase; letter-spacing: .08em; }}
      .mg-cards {{ display: flex; flex-direction: column; gap: 36px; width: 100%; }}
      .mg-card {{ padding: 40px 48px; border-radius: 36px; background: color-mix(in srgb, {text} 9%, transparent); border: 2px solid color-mix(in srgb, {accent} 45%, transparent);
                  box-shadow: 0 40px 80px rgba(0,0,0,.35); backdrop-filter: blur(12px); margin-left: calc(var(--i) * 60px); }}
      .mg-card b {{ display: block; font: 800 64px/1.1 "{body}", sans-serif; }} .mg-card span {{ font: 500 38px/1.3 "{body}", sans-serif; opacity: .8; }}
      .mg-browser {{ position: relative; width: 920px; height: 1150px; border-radius: 28px; overflow: hidden; background: #fff; box-shadow: 0 60px 120px rgba(0,0,0,.5); transform-style: preserve-3d; }}
      .mg-bar {{ height: 76px; display: flex; align-items: center; gap: 14px; padding: 0 28px; background: #ececec; }}
      .mg-bar i {{ width: 22px; height: 22px; border-radius: 50%; background: #d0d0d0; }} .mg-bar i:first-child {{ background: #ff6159; }} .mg-bar i:nth-child(2) {{ background: #ffbd2e; }} .mg-bar i:nth-child(3) {{ background: #28c941; }}
      .mg-bar span {{ margin-left: 18px; flex: 1; padding: 10px 24px; border-radius: 18px; background: #fff; font: 500 30px/1 "{body}", sans-serif; color: #555; }}
      .mg-view {{ position: absolute; top: 76px; inset-inline: 0; bottom: 0; overflow: hidden; }}
      .mg-shot {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; transform-origin: 50% 0; }}
      .mg-site {{ padding: 80px 64px; color: #151515; display: flex; flex-direction: column; gap: 30px; }}
      .mg-site h3 {{ margin: 0; font: 800 80px/1.05 "{body}", sans-serif; letter-spacing: -0.03em; }}
      .mg-skel {{ margin: 0; height: 28px; border-radius: 14px; background: #e6e6e6; }} .mg-skel.s {{ width: 70%; }}
      .mg-site em {{ align-self: flex-start; font: 700 36px/1 "{body}", sans-serif; font-style: normal; padding: 26px 44px; border-radius: 40px; background: {accent}; color: {ink}; }}
      .mg-tiles {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 40px; }} .mg-tiles i {{ height: 360px; border-radius: 24px; background: linear-gradient(160deg, #f1f1f1, #dadada); }}
      .mg-sweep {{ position: absolute; inset: -20% auto -20% 0; width: 40%; background: linear-gradient(100deg, transparent, rgba(255,255,255,.55), transparent); transform: skewX(-18deg); pointer-events: none; }}
      .mg-brand {{ position: relative; overflow: hidden; padding: 40px; }}
      .mg-phone {{ position: relative; width: 560px; height: 1140px; border-radius: 80px; background: #0d0d0f; padding: 22px; box-shadow: 0 60px 120px rgba(0,0,0,.55), inset 0 0 0 4px #2a2a2e; }}
      .mg-notch {{ position: absolute; top: 34px; left: 50%; width: 160px; height: 40px; margin-left: -80px; border-radius: 20px; background: #0d0d0f; z-index: 2; }}
      .mg-screen {{ width: 100%; height: 100%; border-radius: 60px; overflow: hidden; background: #222; }}
      .mg-fill {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
      .mg-ph {{ background: linear-gradient(160deg, color-mix(in srgb, {accent} 40%, {bg}), {bg}); }}
      .mg-caption {{ margin: 0; font: 700 56px/1.2 "{body}", sans-serif; text-align: center; }}
      .mg-laptop {{ width: 940px; transform-style: preserve-3d; }}
      .mg-lid {{ height: 600px; border-radius: 26px 26px 0 0; background: #111; padding: 22px; transform-origin: bottom; box-shadow: 0 40px 90px rgba(0,0,0,.5); }}
      .mg-lid .mg-screen {{ border-radius: 8px; }}
      .mg-base {{ height: 36px; margin: 0 -50px; border-radius: 0 0 40px 40px; background: linear-gradient(#c9c9cf, #8d8d95); }}
      .mg-split {{ position: absolute; inset: 0; }}
      .mg-half {{ position: absolute; inset: 0; }} .mg-half .mg-fill {{ position: absolute; inset: 0; }}
      .mg-tag {{ position: absolute; top: 220px; padding: 16px 30px; border-radius: 14px; font: 800 44px/1 "{body}", sans-serif; text-transform: uppercase; background: rgba(0,0,0,.6); }}
      .mg-half.l .mg-tag {{ left: 60px; }} .mg-half.r .mg-tag {{ right: 60px; background: {accent}; color: {ink}; }}
      .mg-divider {{ position: absolute; top: 0; bottom: 0; left: 50%; width: 8px; margin-left: -4px; background: #fff; box-shadow: 0 0 40px rgba(255,255,255,.8); }}
      .mg-list {{ list-style: none; margin: 0; padding: 0; width: 100%; display: flex; flex-direction: column; gap: 34px; }}
      .mg-list li {{ position: relative; display: flex; align-items: center; gap: 34px; padding: 30px 36px; border-radius: 28px; background: color-mix(in srgb, {text} 8%, transparent); overflow: hidden; }}
      .mg-list b {{ font: 800 62px/1 "{body}", sans-serif; color: {accent}; }} .mg-list span {{ font: 600 50px/1.2 "{body}", sans-serif; }}
      .mg-list i {{ position: absolute; left: 0; bottom: 0; height: 6px; width: 100%; background: {accent}; transform-origin: left; }}
      .mg-chat {{ width: 100%; display: flex; flex-direction: column; gap: 28px; }}
      .mg-msg {{ max-width: 76%; padding: 30px 40px; border-radius: 44px 44px 44px 12px; background: color-mix(in srgb, {text} 14%, transparent); font: 500 46px/1.3 "{body}", sans-serif; }}
      .mg-msg.me {{ align-self: flex-end; border-radius: 44px 44px 12px 44px; background: {accent}; color: {ink}; }}
      .mg-cal {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 18px; width: 100%; }}
      .mg-cal i {{ display: grid; place-items: center; height: 110px; border-radius: 24px; font: 700 42px/1 "{body}", sans-serif; font-style: normal; background: color-mix(in srgb, {text} 8%, transparent); }}
      .mg-note {{ margin: 0; font: 600 50px/1.2 "{body}", sans-serif; text-align: center; }}
      .mg-chart {{ display: flex; align-items: flex-end; gap: 36px; height: 1000px; width: 100%; }}
      .mg-col {{ flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; gap: 20px; text-align: center; }}
      .mg-col i {{ display: block; border-radius: 22px 22px 6px 6px; background: linear-gradient({accent}, color-mix(in srgb, {accent} 50%, {bg})); transform-origin: bottom; position: relative; }}
      .mg-col i b {{ position: absolute; top: -70px; left: 0; right: 0; font: 800 48px/1 "{body}", sans-serif; }} .mg-col span {{ font: 600 40px/1 "{body}", sans-serif; opacity: .8; }}
      .mg-ring {{ width: 760px; height: 760px; transform: rotate(-90deg); }} .mg-track {{ fill: none; stroke: color-mix(in srgb, {text} 12%, transparent); stroke-width: 44; }}
      .mg-arc {{ fill: none; stroke: {accent}; stroke-width: 44; stroke-linecap: round; filter: drop-shadow(0 0 30px {accent}); }}
      .mg-ring-label {{ position: absolute; display: flex; flex-direction: column; align-items: center; }} .mg-ring-label b {{ font: 800 170px/1 "{body}", sans-serif; }}
      .mg-ring-label span {{ font: 600 44px/1.2 "{body}", sans-serif; opacity: .8; }}
      .mg-logo {{ max-width: 720px; max-height: 420px; object-fit: contain; }}
      .mg-wordmark {{ margin: 0; font: 600 150px/1 "{serif}", serif; letter-spacing: -0.02em; }}
      .mg-tagline {{ margin: 0; font: 600 40px/1.2 "{body}", sans-serif; text-transform: uppercase; color: {accent}; }}
      .mg-cta-h {{ margin: 0; font: 800 96px/1.05 "{body}", sans-serif; letter-spacing: -0.03em; }}
      .mg-btnwrap {{ position: relative; }}
      .mg-btn {{ display: inline-block; font: 800 60px/1 "{body}", sans-serif; font-style: normal; padding: 44px 90px; border-radius: 80px; background: {accent}; color: {ink}; box-shadow: 0 20px 60px color-mix(in srgb, {accent} 60%, transparent); }}
      .mg-pulse {{ position: absolute; inset: 0; border-radius: 80px; border: 6px solid {accent}; }}
      .mg-cursor {{ position: absolute; right: -10px; bottom: -40px; font-size: 90px; color: #fff; transform: rotate(-30deg); text-shadow: 0 4px 12px rgba(0,0,0,.6); }}
      .mg-price-card {{ width: 820px; padding: 64px; border-radius: 48px; background: color-mix(in srgb, {text} 10%, {bg}); border: 3px solid {accent}; }}
      .mg-price-card span {{ font: 700 48px/1 "{body}", sans-serif; color: {accent}; text-transform: uppercase; letter-spacing: .1em; }}
      .mg-price-card b {{ display: block; margin: 24px 0; font: 800 150px/1 "{body}", sans-serif; }} .mg-price-card b:empty {{ display: none; }}
      .mg-price-card ul {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 22px; font: 600 46px/1.2 "{body}", sans-serif; }}
      .mg.overlay .mg-cam {{ justify-content: flex-end; padding-bottom: 360px; }}
      .mg-lt {{ align-self: flex-start; display: flex; flex-direction: column; gap: 8px; padding: 30px 44px; border-left: 12px solid {accent}; background: rgba(0,0,0,.62); border-radius: 0 24px 24px 0; }}
      .mg-lt b {{ font: 800 58px/1.1 "{body}", sans-serif; }} .mg-lt span {{ font: 500 38px/1.2 "{body}", sans-serif; opacity: .85; }}
      .mg-beam {{ position: absolute; inset: -30% 20%; background: linear-gradient(105deg, transparent 35%, rgba(255,255,255,.5) 50%, transparent 65%); mix-blend-mode: screen; }}
      .mg-arcs {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
      .mg-arcs path {{ fill: none; stroke: {accent}; stroke-width: 6; stroke-dasharray: 2400; filter: drop-shadow(0 0 24px {accent}); opacity: .9; }}
      .mg-arc-text {{ position: relative; }}
      .mg-burst {{ position: absolute; left: 50%; top: 50%; }}
      .mg-shape {{ position: absolute; width: 26px; height: 300px; margin: -150px 0 0 -13px; border-radius: 13px; background: {accent}; transform: rotate(var(--a)) translateY(-260px); }}
      .mg-burst-t {{ position: relative; margin: 0; font: 900 200px/1 "{body}", sans-serif; text-shadow: 0 10px 40px rgba(0,0,0,.5); }}
      .mg.overlay .mg-burst-t {{ align-self: center; margin-bottom: auto; margin-top: auto; }}
      .mg-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 28px; width: 100%; }}
      .mg-tile {{ height: 420px; border-radius: 32px; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,.4); }}
      .mg-toasts {{ width: 100%; display: flex; flex-direction: column; gap: 26px; }}
      .mg-toast {{ display: flex; gap: 28px; align-items: center; padding: 32px 36px; border-radius: 36px; background: rgba(255,255,255,.92); color: #151515; box-shadow: 0 24px 60px rgba(0,0,0,.35); }}
      .mg-toast i {{ width: 90px; height: 90px; border-radius: 24px; background: linear-gradient(135deg, {accent}, color-mix(in srgb, {accent} 40%, #000)); flex: none; }}
      .mg-toast b {{ display: block; font: 800 36px/1.1 "{body}", sans-serif; }} .mg-toast span {{ font: 500 40px/1.2 "{body}", sans-serif; }}
      .mg-vcard {{ width: 820px; height: 1240px; border-radius: 48px; overflow: hidden; box-shadow: 0 60px 120px rgba(0,0,0,.55); }}
      .mg-vlabel {{ margin: 0; font: 700 56px/1.2 "{body}", sans-serif; text-align: center; }}
"""


def render(item: dict, idx: int, ctx: dict) -> tuple[str, str]:
    t = TEMPLATES[item["template"]]
    sc = Scene(item, idx, ctx)
    markup = t["fn"](sc)
    return markup, "\n      ".join(sc.js)


# What a scene must be given to say anything real; sample defaults exist for the gallery only, never for an edit.
REQUIRED: dict[str, tuple[tuple[str, ...], int]] = {  # (text fields, all needed; media items needed)
    "kinetic_title": (("text",), 0), "blur_reveal": (("text",), 0), "stagger_lines": (("lines",), 0), "typewriter": (("text",), 0),
    "masked_text": (("text",), 0), "counter": (("value", "label"), 0), "floating_cards": (("cards",), 0), "info_list": (("items",), 0),
    "chat_bubbles": (("messages",), 0), "calendar": (("day", "note"), 0), "bar_chart": (("labels", "values"), 0),
    "stat_ring": (("percent", "label"), 0), "cta_button": (("button",), 0), "pricing_card": (("features",), 0),
    "lower_third": (("name",), 0), "glow_arc": (("text",), 0), "shape_burst": (("text",), 0), "notifications": (("items",), 0),
    "phone_mockup": ((), 1), "laptop_mockup": ((), 1), "media_card": ((), 1), "split_screen": ((), 2), "grid_gallery": ((), 2),
}


def complete(template: str, fields: dict, media: list) -> bool:
    texts, n = REQUIRED.get(template, ((), 0))
    if template == "browser_mockup":  # a real screenshot, or at least a real headline for the generated page
        return bool(media) or bool(str(fields.get("headline", "")).strip())
    return all(str(fields.get(k, "")).strip() for k in texts) and len(media) >= n


def items_from_directive(graphics, dur: float, w: int, h: int, media: dict[int, str] | None = None) -> list[dict]:
    """Director graphics → timeline motion items (clamped inside the edit, never overlapping each other)."""
    out, busy_until = [], 0.0
    for n, g in enumerate(sorted(graphics, key=lambda g: g.at)):
        t = TEMPLATES.get(g.template)
        if not t:
            continue
        start = round(max(g.at * dur, busy_until), 3)
        length = round(min(g.duration_s, dur - start), 3)
        if length < 1.0:
            continue
        fields = {k: str(v)[: t["fields"][k]] for k, v in (g.fields or {}).items() if k in t["fields"]}
        refs = [media[int(x)] for x in str((g.fields or {}).get("media", "")).replace(",", " ").split() if x.isdigit() and media and int(x) in media]
        if not complete(g.template, fields, refs):
            continue  # missing content is skipped, never filled with sample text
        out.append({"id": f"mg-{n}", "type": "motion", "start": start, "duration": length, "template": g.template,
                    "fields": fields, "media": refs[: t["media"]], "intensity": 0.6})
        busy_until = start + length
    return out


def sfx_cues(items: list[dict]) -> list[dict]:
    """Sound design for motion items: each template's whoosh/impact/riser/tick at its animation beats."""
    cues = []
    for it in items:
        for kind, at in TEMPLATES[it["template"]]["sfx"]:
            if at < it["duration"]:
                cues.append({"kind": kind, "at": round(it["start"] + at, 3), "gain_db": -9 if kind == "tick" else -7})
    return cues
