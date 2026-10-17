"""Builds the 60-second Reel Studio product tutorial as a Hyperframes composition (1920x1080, 30 fps).

All motion, typography, transitions, compositing and the final render happen in Hyperframes/GSAP. This script only
lays out the composition from real assets: captured app screens (capture.mjs), narration + word timings
(narrate.py), real rendered reels and the real class recording. Then:
    hyperframes lint build/project && hyperframes render build/project -o build/reel-studio-tour.mp4

Usage (from repo root, API venv python):  python marketing/tutorial/build.py
"""

import json
import os
import shutil
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
PROJ = BUILD / "project"
SCREENS = HERE / "assets" / "screens"
DATA = Path(os.environ.get("DATA_DIR", r"C:\Users\Sahil\AppData\Local\reel-studio\data"))
GSAP = ROOT / "apps/api/app/services/rendering/vendor/gsap.min.js"
FONTS = ROOT / "apps/web/app/fonts"

W, H = 1920, 1080
FX, FY, FW, FH = 240, 104, 1440, 810  # browser frame on stage
SX, SY = 1600, 900  # screenshot CSS size (captured at 2x)
S0 = FW / SX

INK, FOREST, OLIVE, SAGE, IVORY, CREAM, LINE = "#20271C", "#1D2618", "#3C462F", "#647457", "#FCF9F4", "#F6F3EC", "#E7E5DE"

# Real media (synthetic test lecture + its renders; the physics reel is the owner's published post).
MEDIA = {
    "source.mp4": "orgs/7d612534-293d-492e-95d1-e87856829346/recordings/0ba5238f-0c10-49e7-86a3-83b5255f91d2/source.mp4",
    "reel-hooks.mp4": "orgs/7d612534-293d-492e-95d1-e87856829346/renders/023ff36c-9b5f-4a0a-8510-c4a5bc460d67/out.mp4",
    "reel-topic.mp4": "orgs/7d612534-293d-492e-95d1-e87856829346/renders/1e29683c-e155-47f5-a257-28796c4d8775/out.mp4",
    "reel-edited.mp4": "orgs/7d612534-293d-492e-95d1-e87856829346/renders/a325cf54-b681-452b-b18b-61fee66b1d73/out.mp4",
    "reel-physics.mp4": "orgs/8b94576a-04b8-4c80-ac93-38876f16f766/renders/540767ff-808d-43b6-8c2f-f3b5c770b509/out.mp4",
}
# Real 9:16 crop keyframes of the hooks reel (render 023ff36c): (t, crop_x) on the 1920x1080 source, width 608.
CROP_KEYS = [(0, 450), (0.5, 304), (1.0, 209), (1.5, 148)]


def link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def sfx(path: Path, kind: str) -> None:
    """Tiny synthesized UI sounds (no third-party audio): a soft click and a short airy whoosh."""
    rate = 48000
    rng = np.random.default_rng(7)
    if kind == "click":
        n = int(rate * 0.05)
        t = np.arange(n) / rate
        sig = (np.sin(2 * np.pi * 2200 * t) * 0.5 + rng.normal(0, 0.3, n)) * np.exp(-t * 90)
    else:
        n = int(rate * 0.45)
        t = np.arange(n) / rate
        noise = np.cumsum(rng.normal(0, 1, n))
        noise -= np.convolve(noise, np.ones(400) / 400, mode="same")  # crude band-pass
        sig = noise / np.abs(noise).max() * np.sin(np.pi * t / t[-1]) ** 2
    sig = (sig / np.abs(sig).max() * 0.35 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1), f.setsampwidth(2), f.setframerate(rate)
        f.writeframes(np.repeat(sig, 1).tobytes())


class Cam:
    """Camera over one captured screen inside the browser frame; tracks state to place cursor and rings."""

    def __init__(self, sel: str):
        self.sel, self.x, self.y, self.s = sel, 0.0, 0.0, S0

    def to(self, r: dict | None, zoom: float) -> dict:
        s = S0 * zoom
        if r is None:
            x, y = 0.0, 0.0
        else:
            cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
            x = min(0.0, max(FW - SX * s, FW / 2 - cx * s))
            y = min(0.0, max(FH - SY * s, FH / 2 - cy * s))
        self.x, self.y, self.s = x, y, s
        return {"x": round(x, 1), "y": round(y, 1), "scale": round(s, 4)}

    def screen(self, r: dict, fx: float = 0.5, fy: float = 0.5) -> tuple[float, float]:
        return FX + self.x + (r["x"] + r["w"] * fx) * self.s, FY + self.y + (r["y"] + r["h"] * fy) * self.s

    def box(self, r: dict, pad: float = 8) -> dict:
        return {"left": round(FX + self.x + r["x"] * self.s - pad), "top": round(FY + self.y + r["y"] * self.s - pad),
                "width": round(r["w"] * self.s + 2 * pad), "height": round(r["h"] * self.s + 2 * pad)}


def main() -> None:
    narration = json.loads((BUILD / "narration.json").read_text(encoding="utf-8"))
    rects = json.loads((SCREENS / "rects.json").read_text(encoding="utf-8"))
    for old in PROJ.glob("*") if PROJ.exists() else []:  # clear contents (the folder may be open elsewhere)
        shutil.rmtree(old) if old.is_dir() else old.unlink()
    (PROJ / "media").mkdir(parents=True, exist_ok=True)
    for name in os.listdir(SCREENS):
        if name.endswith(".jpg"):
            link(SCREENS / name, PROJ / "media" / name)
    for name, rel in MEDIA.items():
        link(DATA / rel, PROJ / "media" / name)
    for f in ("fraunces-latin.woff2", "dm-sans-latin.woff2", "jetbrains-mono-latin.woff2"):
        link(FONTS / f, PROJ / "fonts" / f)
    shutil.copyfile(GSAP, PROJ / "gsap.min.js")
    sfx(PROJ / "media" / "click.wav", "click")
    sfx(PROJ / "media" / "whoosh.wav", "whoosh")

    # Scene timing from measured narration: 0.45 s lead-in, 0.6 s tail, never shorter than the storyboard minimum.
    t, scenes = 0.0, []
    for sc in narration:
        dur = round(max(sc["min"], sc["audio_s"] + 0.95), 2)
        scenes.append({**sc, "start": round(t, 2), "dur": dur, "voice_at": round(t + 0.45, 2)})
        t += dur
    total = round(t, 2)

    html, js, audio = [], [], []
    clicks, whooshes = [], []

    def at(sc, rel):  # absolute time inside a scene
        return round(sc["start"] + rel, 3)

    def scene_box(sc, inner, cls=""):
        html.append(f'<section id="s-{sc["id"]}" class="scene {cls}">{inner}</section>')
        js.append(f'tl.set("#s-{sc["id"]}", {{autoAlpha: 1}}, {sc["start"]});')
        js.append(f'tl.fromTo("#s-{sc["id"]}", {{opacity: 0, scale: 1.015}}, {{opacity: 1, scale: 1, duration: 0.45, ease: "power2.out"}}, {sc["start"]});')
        if sc["start"] > 0:
            whooshes.append(sc["start"] - 0.05)
        js.append(f'tl.set("#s-{sc["id"]}", {{autoAlpha: 0}}, {round(sc["start"] + sc["dur"], 3)});')

    def browser(shots: list[str], sc) -> str:
        layers = "".join(f'<div id="cam-{sc["id"]}-{i}" class="cam"><img src="media/{s}.jpg" alt="" /></div>'
                         for i, s in enumerate(shots))
        return (f'<div class="browser"><div class="chrome"><i></i><i></i><i></i>'
                f'<span>reel-studio-taupe.vercel.app</span></div><div class="viewport">{layers}</div></div>')

    def cam_move(sc, i, cam: Cam, r, zoom, rel, dur=1.0):
        st = cam.to(r, zoom)
        js.append(f'tl.to("#cam-{sc["id"]}-{i}", {{x: {st["x"]}, y: {st["y"] - 0}, scale: {st["scale"]}, '
                  f'duration: {dur}, ease: "power3.inOut"}}, {at(sc, rel)});')

    def cam_set(sc, i, cam: Cam, r, zoom, rel):
        st = cam.to(r, zoom)
        js.append(f'tl.set("#cam-{sc["id"]}-{i}", {{x: {st["x"]}, y: {st["y"]}, scale: {st["scale"]}}}, {at(sc, rel)});')

    def show_layer(sc, i, rel, dur=0.5):
        js.append(f'tl.fromTo("#cam-{sc["id"]}-{i}", {{opacity: 0}}, {{opacity: 1, duration: {dur}, ease: "power1.out"}}, {at(sc, rel)});')

    def cursor(sc, cam: Cam, r, rel, click=True, dur=0.7):
        x, y = cam.screen(r)
        js.append(f'tl.to("#cursor", {{x: {round(x)}, y: {round(y)}, duration: {dur}, ease: "power2.inOut"}}, {at(sc, rel)});')
        if click:
            c = at(sc, rel + dur + 0.05)
            js.append(f'tl.fromTo("#cursor", {{scale: 1}}, {{scale: 0.82, duration: 0.09, yoyo: true, repeat: 1}}, {c});')
            js.append(f'tl.set("#ripple", {{x: {round(x)}, y: {round(y)}}}, {c});')
            js.append(f'tl.fromTo("#ripple", {{scale: 0.2, opacity: 0.55}}, {{scale: 1.6, opacity: 0, duration: 0.5, ease: "power2.out"}}, {c});')
            clicks.append(c)

    def ring(sc, cam: Cam, r, rel, hold, rid):
        b = cam.box(r)
        html.append(f'<div id="ring-{rid}" class="ring" style="left:{b["left"]}px;top:{b["top"]}px;width:{b["width"]}px;height:{b["height"]}px"></div>')
        js.append(f'tl.fromTo("#ring-{rid}", {{autoAlpha: 0, scale: 1.08}}, {{autoAlpha: 1, scale: 1, duration: 0.35, ease: "back.out(2)"}}, {at(sc, rel)});')
        js.append(f'tl.to("#ring-{rid}", {{autoAlpha: 0, duration: 0.3}}, {at(sc, rel + hold)});')

    def chip(sc, text, x, y, rel, hold, cid, mono=False):
        html.append(f'<div id="chip-{cid}" class="chip{" mono" if mono else ""}" style="left:{round(x)}px;top:{round(y)}px">{text}</div>')
        js.append(f'tl.fromTo("#chip-{cid}", {{autoAlpha: 0, y: 12}}, {{autoAlpha: 1, y: 0, duration: 0.4, ease: "power2.out"}}, {at(sc, rel)});')
        js.append(f'tl.to("#chip-{cid}", {{autoAlpha: 0, duration: 0.3}}, {at(sc, rel + hold)});')

    def phone(pid, src, left, top, h, media_start, sc, rel, dur, label=""):
        w = round(h * 9 / 16)
        html.append(f'<div id="phone-{pid}" class="phone" style="left:{left}px;top:{top}px;width:{w}px;height:{h}px">'
                    f'<video id="v-{pid}" class="clip" src="media/{src}" data-start="{at(sc, rel)}" data-duration="{round(dur, 3)}" '
                    f'data-media-start="{media_start}" muted playsinline></video>'
                    + (f'<span class="tag">{label}</span>' if label else "") + "</div>")
        js.append(f'tl.fromTo("#phone-{pid}", {{autoAlpha: 0, x: 60}}, {{autoAlpha: 1, x: 0, duration: 0.6, ease: "power3.out"}}, {at(sc, rel)});')
        js.append(f'tl.to("#phone-{pid}", {{autoAlpha: 0, duration: 0.3}}, {at(sc, rel + dur - 0.3)});')

    sc = {s["id"]: s for s in scenes}

    # 1 — Hook: widescreen class → real crop keyframes → the rendered vertical reel.
    s = sc["hook"]
    gw, gh, gx, gy = 1104, 621, 150, 300
    k = gw / 1920
    scene_box(s, f'''<h1 class="hook-title"><span>One recording.</span><span>Multiple moments worth sharing.</span></h1>
      <div class="wide" style="left:{gx}px;top:{gy}px;width:{gw}px;height:{gh}px">
        <video id="v-source" class="clip" src="media/source.mp4" data-start="{s['start']}" data-duration="{s['dur']}" data-media-start="20" muted playsinline></video>
        <div id="guide" class="guide" style="width:{round(608 * k)}px;height:{gh}px;left:0"><b>9:16</b></div>
      </div>
      <svg class="link" viewBox="0 0 1920 1080"><path id="link-path" d="M{gx + gw} {gy + gh / 2} C {gx + gw + 120} {gy + gh / 2}, 1380 {gy + gh / 2}, 1430 {gy + gh / 2}" /></svg>''')
    for i, (kt, cx) in enumerate(CROP_KEYS[1:], 1):
        js.append(f'tl.to("#guide", {{x: {round(cx * k)}, duration: 0.5, ease: "power2.inOut"}}, {at(s, 0.6 + kt * 1.6)});')
    js.append(f'tl.fromTo(".hook-title span", {{autoAlpha: 0, y: 30}}, {{autoAlpha: 1, y: 0, duration: 0.7, stagger: 0.25, ease: "power3.out"}}, {at(s, 0.2)});')
    js.append(f'tl.fromTo("#link-path", {{strokeDashoffset: 600}}, {{strokeDashoffset: 0, duration: 0.8, ease: "power2.inOut"}}, {at(s, 2.6)});')
    js.append(f'tl.set("#guide", {{x: {round(CROP_KEYS[0][1] * k)}}}, 0);')
    phone("hook", "reel-hooks.mp4", 1440, 196, 760, 6.0, s, 3.0, s["dur"] - 3.0, "Rendered reel")

    # 2 — Dashboard: the two creation modes.
    s = sc["dashboard"]
    cam = Cam("")
    scene_box(s, browser(["dashboard"], s), "framed")
    r = rects["dashboard"]
    cam_set(s, 0, cam, None, 1.0, 0)
    cam_move(s, 0, cam, {"x": 300, "y": 300, "w": 600, "h": 120}, 1.55, 1.0, 1.2)
    cursor(s, cam, r["Use a recording"], 2.4)
    ring(s, cam, r["Use a recording"], 3.1, 1.6, "rec")
    cursor(s, cam, r["Create from a topic"], 4.7)
    ring(s, cam, r["Create from a topic"], 5.4, 1.8, "topic")
    cam_move(s, 0, cam, None, 1.0, 7.0, 0.9)

    # 3 — Upload and analyze: uploader, then transcript with a corrected term.
    s = sc["upload"]
    cam = Cam("")
    scene_box(s, browser(["uploader", "recording-top"], s), "framed")
    cam_set(s, 0, cam, rects["uploader"]["Drop a class recording here"], 1.35, 0)
    cursor(s, cam, rects["uploader"]["Drop a class recording here"], 0.6)
    ring(s, cam, rects["uploader"]["Drop a class recording here"], 1.3, 1.6, "drop")
    js.append(f'tl.set("#cam-{s["id"]}-1", {{opacity: 0}}, {s["start"]});')
    cam2 = Cam("")
    cam_set(s, 1, cam2, None, 1.0, 0)
    show_layer(s, 1, 3.0)
    rt = rects["recording-top"]
    cam_move(s, 1, cam2, rt["useEffect"], 2.1, 4.1, 1.2)
    ring(s, cam2, rt["useEffect"], 5.4, 2.8, "term")
    ux, uy = cam2.screen(rt["useEffect"], 0.5, 1.0)
    chip(s, "Corrected from the code on screen", ux - 190, uy + 30, 5.6, 2.6, "term")
    js.append(f'tl.to("#cursor", {{autoAlpha: 0, duration: 0.2}}, {at(s, 3.0)});')
    js.append(f'tl.to("#cursor", {{autoAlpha: 1, duration: 0.2}}, {at(s, s["dur"] - 0.2)});')

    # 4 — Highlights: ranked candidates, crop preview, then the real reframed reel.
    s = sc["highlights"]
    cam = Cam("")
    scene_box(s, browser(["recording-highlights"], s), "framed")
    rh = rects["recording-highlights"]
    cam_set(s, 0, cam, None, 1.0, 0)
    cam_move(s, 0, cam, {"x": 290, "y": 190, "w": 560, "h": 120}, 1.7, 0.5, 1.1)
    cursor(s, cam, rh["Custom Hook with useEffect in React"], 1.7)
    ring(s, cam, {"x": 290, "y": 196, "w": 640, "h": 70}, 2.4, 2.2, "hl")
    cam_move(s, 0, cam, {"x": 990, "y": 210, "w": 560, "h": 360}, 1.45, 4.4, 1.1)
    phone("hl", "reel-hooks.mp4", 1430, 150, 780, 6.0, s, 5.6, s["dur"] - 5.6, "Smart 9:16 reframe")

    # 5 — Topic Studio: prompt, generate, script, rendered video.
    s = sc["topic"]
    cam = Cam("")
    scene_box(s, browser(["topic-studio", "topic-script"], s), "framed")
    rt = rects["topic-studio"]
    cam_set(s, 0, cam, {"x": 290, "y": 200, "w": 840, "h": 200}, 1.45, 0)
    cursor(s, cam, {"x": 300, "y": 250, "w": 200, "h": 60}, 0.4, click=False)
    ring(s, cam, {"x": 293, "y": 245, "w": 830, "h": 130}, 0.8, 1.6, "prompt")
    cam_move(s, 0, cam, rt["Generate new version"], 1.6, 2.2, 0.9)
    cursor(s, cam, rt["Generate new version"], 3.0)
    js.append(f'tl.set("#cam-{s["id"]}-1", {{opacity: 0}}, {s["start"]});')
    cam2 = Cam("")
    cam_set(s, 1, cam2, {"x": 293, "y": 200, "w": 700, "h": 420}, 1.25, 0)
    show_layer(s, 1, 4.2)
    cam_move(s, 1, cam2, {"x": 293, "y": 260, "w": 1250, "h": 520}, 1.1, 4.8, 1.6)
    js.append(f'tl.to("#cursor", {{autoAlpha: 0, duration: 0.2}}, {at(s, 4.2)});')
    phone("topic", "reel-topic.mp4", 1430, 150, 780, 7.0, s, 5.0, s["dur"] - 5.0, "Generated: JSON vs XML")
    js.append(f'tl.to("#cursor", {{autoAlpha: 1, duration: 0.2}}, {at(s, s["dur"] - 0.2)});')

    # 6 — Editor: timeline + caption words, then style presets and render.
    s = sc["editor"]
    cam = Cam("")
    scene_box(s, browser(["editor", "editor-recording"], s), "framed")
    re_ = rects["editor"]
    cam_set(s, 0, cam, None, 1.0, 0)
    cam_move(s, 0, cam, {"x": 60, "y": 700, "w": 900, "h": 160}, 1.6, 0.6, 1.1)
    cursor(s, cam, {"x": 540, "y": 790, "w": 60, "h": 24}, 1.8)
    cam_move(s, 0, cam, re_["Caption words"], 1.9, 3.0, 1.0)
    ring(s, cam, {"x": 1290, "y": 290, "w": 295, "h": 170}, 4.1, 1.5, "words")
    js.append(f'tl.set("#cam-{s["id"]}-1", {{opacity: 0}}, {s["start"]});')
    cam2 = Cam("")
    cam_set(s, 1, cam2, {"x": 1293, "y": 150, "w": 287, "h": 190}, 1.7, 0)
    show_layer(s, 1, 5.5)
    js.append(f'tl.to("#cursor", {{autoAlpha: 0, duration: 0.15}}, {at(s, 5.4)});')
    js.append(f'tl.to("#cursor", {{autoAlpha: 1, duration: 0.15}}, {at(s, 6.0)});')
    energy = {"x": 1441, "y": 158, "w": 139, "h": 76}
    cursor(s, cam2, energy, 6.0, dur=0.55)
    ring(s, cam2, energy, 6.6, 1.0, "energy")
    js.append(f'tl.to("#cursor", {{autoAlpha: 0, duration: 0.15}}, {at(s, 7.4)});')
    phone("edit", "reel-edited.mp4", 1430, 150, 780, 4.0, s, 7.4, s["dur"] - 7.4, "Re-rendered MP4")
    js.append(f'tl.to("#cursor", {{autoAlpha: 1, duration: 0.15}}, {at(s, s["dur"] - 0.15)});')

    # 7 — Publish: the real Instagram connection, then the real published reel.
    s = sc["publish"]
    cam = Cam("")
    scene_box(s, browser(["publishing"], s), "framed")
    cam_set(s, 0, cam, None, 1.0, 0)
    cam_move(s, 0, cam, {"x": 293, "y": 225, "w": 800, "h": 380}, 1.2, 0.3, 1.0)
    ring(s, cam, {"x": 293, "y": 225, "w": 1000, "h": 230}, 1.4, 1.5, "ig")
    js.append(f'tl.to("#cursor", {{autoAlpha: 0, duration: 0.2}}, {at(s, 0.2)});')
    phone("ig", "reel-physics.mp4", 1430, 150, 780, 10.0, s, 2.6, s["dur"] - 2.6, "Published · @career.with.purpose")
    chip(s, "Posted through the official Instagram API", 820, 860, 3.0, s["dur"] - 3.4, "ig")

    # 8 — CTA
    s = sc["cta"]
    scene_box(s, '''<div class="cta-bg"></div><div class="cta-copy"><div class="logo"><span class="mark">◎</span>Reel Studio</div>
      <h2>Your content.<br/>Beautifully repurposed.</h2><p>Start creating with Reel Studio.</p></div>''', "cta")
    phone("cta", "reel-hooks.mp4", 1290, 150, 780, 30.0, s, 0.0, s["dur"], "")
    js.append(f'tl.fromTo(".cta-copy > *", {{autoAlpha: 0, y: 24}}, {{autoAlpha: 1, y: 0, duration: 0.6, stagger: 0.15, ease: "power3.out"}}, {at(s, 0.15)});')
    js.append(f'tl.to("#cursor", {{autoAlpha: 0, duration: 0.2}}, {s["start"]});')

    # Chapter labels.
    for s in scenes:
        if s["chapter"]:
            n = scenes.index(s)
            html.append(f'<div id="chap-{s["id"]}" class="chapter"><b>{n:02d}</b>{s["chapter"]}</div>')
            js.append(f'tl.fromTo("#chap-{s["id"]}", {{autoAlpha: 0, x: -16}}, {{autoAlpha: 1, x: 0, duration: 0.45, ease: "power2.out"}}, {at(s, 0.1)});')
            js.append(f'tl.to("#chap-{s["id"]}", {{autoAlpha: 0, duration: 0.25}}, {at(s, s["dur"] - 0.3)});')

    # Narration audio + karaoke captions (pages of up to ~44 characters).
    cap_html, n, vtt = [], 0, []
    for s in scenes:
        audio.append(f'<audio id="a-{s["id"]}" class="clip" src="{s["audio"]}" data-start="{s["voice_at"]}" data-duration="{s["audio_s"]}" data-has-audio="true" data-volume="1"></audio>')
        link(BUILD / s["audio"], PROJ / s["audio"])
        if s["id"] == "cta":
            continue
        pages, cur = [], []
        ws = s["words"]
        for i, w in enumerate(ws):
            cur.append(w)
            rest = next((j for j in range(i + 1, len(ws)) if ws[j]["text"][-1] in ".?!,"), len(ws) - 1) - i
            long = sum(len(x["text"]) + 1 for x in cur) > 40 and rest > 2  # no 1–2 word orphan pages
            if w["text"][-1] in ".?!" or (w["text"][-1] == "," and len(cur) > 3) or long:
                pages.append(cur)
                cur = []
        if cur:
            pages.append(cur)
        for pi, page in enumerate(pages):
            on = round(s["voice_at"] + page[0]["start"], 3)
            nxt = pages[pi + 1][0]["start"] if pi + 1 < len(pages) else page[-1]["end"] + 0.35
            off = round(s["voice_at"] + nxt, 3)
            spans = []
            for w in page:
                spans.append(f'<span id="w{n}">{w["text"]}</span>')
                js.append(f'tl.set("#w{n}", {{color: "{IVORY}"}}, {round(s["voice_at"] + w["start"], 3)});')
                n += 1
            cid = f"cap-{s['id']}-{pi}"
            cap_html.append(f'<div id="{cid}" class="cap">{" ".join(spans)}</div>')
            vtt.append((on, off, " ".join(w["text"] for w in page)))
            js.append(f'tl.set("#{cid}", {{autoAlpha: 1}}, {on});')
            js.append(f'tl.set("#{cid}", {{autoAlpha: 0}}, {off});')

    for i, c in enumerate(clicks):
        audio.append(f'<audio id="click-{i}" class="clip" src="media/click.wav" data-start="{c}" data-duration="0.05" data-has-audio="true" data-volume="0.35"></audio>')
    for i, c in enumerate(whooshes):
        audio.append(f'<audio id="whoosh-{i}" class="clip" src="media/whoosh.wav" data-start="{max(0, round(c, 3))}" data-duration="0.45" data-has-audio="true" data-volume="0.18"></audio>')

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<title>Reel Studio — 60-second tour</title><script src="gsap.min.js"></script>
<style>
@font-face {{ font-family: "Fraunces"; src: url("fonts/fraunces-latin.woff2") format("woff2"); font-weight: 100 900; }}
@font-face {{ font-family: "DM Sans"; src: url("fonts/dm-sans-latin.woff2") format("woff2"); font-weight: 100 1000; }}
@font-face {{ font-family: "JetBrains Mono"; src: url("fonts/jetbrains-mono-latin.woff2") format("woff2"); }}
html, body {{ margin: 0; background: {CREAM}; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; background: {CREAM}; font-family: "DM Sans", sans-serif; color: {INK}; }}
.scene {{ position: absolute; inset: 0; visibility: hidden; opacity: 0; }}
.browser {{ position: absolute; left: {FX}px; top: {FY - 34}px; width: {FW}px; height: {FH + 34}px; border-radius: 18px; overflow: hidden;
  background: #fff; box-shadow: 0 30px 80px -30px rgba(29,38,24,.45), 0 0 0 1px {LINE}; }}
.chrome {{ height: 34px; display: flex; align-items: center; gap: 8px; padding: 0 16px; background: {IVORY}; border-bottom: 1px solid {LINE}; }}
.chrome i {{ width: 11px; height: 11px; border-radius: 50%; background: {LINE}; }}
.chrome span {{ margin-left: 18px; font-size: 14px; color: #7a7d70; }}
.viewport {{ position: relative; width: {FW}px; height: {FH}px; overflow: hidden; }}
.cam {{ position: absolute; left: 0; top: 0; width: {SX}px; height: {SY}px; transform-origin: 0 0; }}
.cam img {{ width: {SX}px; height: {SY}px; display: block; }}
.ring {{ position: absolute; border: 3px solid {SAGE}; border-radius: 14px; box-shadow: 0 0 0 6px rgba(100,116,87,.18); visibility: hidden; z-index: 5; }}
.chip {{ position: absolute; z-index: 6; padding: 10px 16px; border-radius: 12px; background: {FOREST}; color: {IVORY}; font-size: 22px; font-weight: 500; visibility: hidden; white-space: nowrap; }}
.chip.mono {{ font-family: "JetBrains Mono", monospace; }}
#cursor {{ position: absolute; left: -6px; top: -4px; z-index: 20; width: 34px; height: 34px; transform-origin: 6px 4px; }}
#ripple {{ position: absolute; left: -30px; top: -30px; width: 60px; height: 60px; border-radius: 50%; border: 3px solid {SAGE}; z-index: 19; opacity: 0; }}
.chapter {{ position: absolute; left: {FX}px; top: 22px; z-index: 8; font-size: 22px; font-weight: 500; color: {OLIVE}; visibility: hidden; display: flex; gap: 14px; align-items: baseline; }}
.chapter b {{ font-family: "Fraunces", serif; font-weight: 500; font-size: 26px; color: {SAGE}; }}
.phone {{ position: absolute; z-index: 7; border-radius: 34px; overflow: hidden; background: #000; visibility: hidden;
  box-shadow: 0 40px 90px -30px rgba(29,38,24,.6), 0 0 0 10px {FOREST}; }}
.phone video, .wide video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.phone .tag {{ position: absolute; left: 16px; top: 16px; padding: 8px 12px; border-radius: 10px; background: rgba(252,249,244,.92); color: {FOREST}; font-size: 18px; font-weight: 600; }}
.hook-title {{ position: absolute; left: 150px; top: 92px; margin: 0; font-family: "Fraunces", serif; font-weight: 400; font-size: 72px; line-height: 1.05; letter-spacing: -0.02em; color: {FOREST}; }}
.hook-title span {{ display: block; visibility: hidden; }}
.hook-title span + span {{ color: {SAGE}; font-style: italic; }}
.wide {{ position: absolute; border-radius: 18px; overflow: hidden; box-shadow: 0 30px 80px -30px rgba(29,38,24,.5), 0 0 0 1px {LINE}; }}
.guide {{ position: absolute; top: 0; border: 4px solid #F2E7C9; box-shadow: 0 0 0 9999px rgba(20,26,16,.45); border-radius: 6px; box-sizing: border-box; }}
.guide b {{ position: absolute; left: 8px; top: 8px; padding: 4px 8px; border-radius: 6px; background: #F2E7C9; color: {FOREST}; font-size: 18px; }}
.link {{ position: absolute; inset: 0; width: {W}px; height: {H}px; z-index: 6; }}
.link path {{ fill: none; stroke: {SAGE}; stroke-width: 4; stroke-dasharray: 600; stroke-linecap: round; }}
.cta-bg {{ position: absolute; inset: 0; background: {FOREST}; }}
.cta-copy {{ position: absolute; left: 180px; top: 300px; color: {IVORY}; }}
.cta-copy .logo {{ display: flex; align-items: center; gap: 14px; font-size: 30px; font-weight: 600; color: #DCE3D1; }}
.cta-copy .mark {{ display: grid; place-items: center; width: 48px; height: 48px; border-radius: 12px; background: {IVORY}; color: {FOREST}; font-size: 28px; }}
.cta-copy h2 {{ margin: 36px 0 0; font-family: "Fraunces", serif; font-weight: 400; font-size: 86px; line-height: 1.04; letter-spacing: -0.02em; }}
.cta-copy p {{ margin: 28px 0 0; font-size: 30px; color: #C9D2BD; }}
#caps {{ position: absolute; left: 0; right: 0; bottom: 18px; height: 70px; z-index: 30; }}
.cap {{ position: absolute; left: 50%; transform: translateX(-50%); bottom: 0; visibility: hidden; white-space: nowrap;
  padding: 12px 24px; border-radius: 16px; background: rgba(29,38,24,.92); font-size: 32px; font-weight: 500; color: #9AA58C; }}
.cap span {{ margin: 0 2px; }}
</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
{"".join(html)}
<div id="caps">{"".join(cap_html)}</div>
<div id="ripple"></div>
<svg id="cursor" viewBox="0 0 24 24"><path d="M3 2l7.5 19 2.6-7.9L21 10.5z" fill="{FOREST}" stroke="{IVORY}" stroke-width="1.6" stroke-linejoin="round"/></svg>
{"".join(audio)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
tl.set("#cursor", {{ x: 1000, y: 700 }}, 0);
{chr(10).join(js)}
tl.set({{}}, {{}}, {total});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script></body></html>
"""
    (PROJ / "index.html").write_text(page, encoding="utf-8")
    stamp = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:06.3f}"  # noqa: E731
    cues = [f"{stamp(a)} --> {stamp(b)}\n{text}\n" for a, b, text in vtt]
    (BUILD / "reel-studio-tour.vtt").write_text("WEBVTT\n\n" + "\n".join(cues), encoding="utf-8")
    print(f"composition: {len(scenes)} scenes, {total} s, {n} caption words, {len(clicks)} clicks")
    for s in scenes:
        print(f"  {s['id']:<11} {s['start']:6.2f} +{s['dur']:5.2f}")


if __name__ == "__main__":
    main()
