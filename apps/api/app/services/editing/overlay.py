"""Mode B plan → canonical timeline (packages/timeline-schema): the FFmpeg base picture as one video item (it already
carries the mixed music/SFX/voice), plus the overlay layers Hyperframes renders on top — motion-graphic scenes,
on-screen text and captions. The same document opens in the editor, so preview and export share one source of truth."""

import os
import shutil
from pathlib import Path

from app.services.rendering import motion
from app.services.rendering import timeline as tl

TEXT_ROLE = {  # (y as share of height, font size, seconds on screen)
    "hook": (0.16, 84, 2.2),
    "point": (0.2, 64, 1.8),
    "cta": (0.68, 72, 2.4),
}
DESIGNED = ("motion_graphics", "tech_ad")


def templates() -> dict[str, dict]:
    return {k: {"description": t["description"], "fields": list(t["fields"])} for k, t in motion.TEMPLATES.items()}


def has_overlays(doc: dict) -> bool:
    return any(i["type"] in ("text", "caption", "motion", "code") for t in doc["tracks"] for i in t["items"]) or bool(
        doc["brand"].get("watermark", {}).get("enabled")
    )


class _G:  # the director's Graphic shape, for scenes the structure fallback adds
    def __init__(self, template: str, at: float, duration_s: float, fields: dict):
        self.template, self.at, self.duration_s, self.fields = template, at, duration_s, fields


def graphics(d, dur: float, clips: list[dict]) -> list[dict]:
    """Motion items for the edit. Designed styles (motion graphics / tech ad) need scenes across most of the edit; when
    the model chose too few, a structure is added from what is known — the request's own on-screen lines and the
    uploaded media in mockups — never invented claims. `clips` are the media assets in director numbering (1-based)."""
    media = {n + 1: f"media-{n + 1}" for n in range(len(clips))}
    chosen = list(d.graphics)
    if d.style in DESIGNED and sum(g.duration_s for g in chosen) < 0.5 * dur:
        hook = next((t.text for t in d.on_screen_text if t.role == "hook"), "")
        points = [t.text for t in d.on_screen_text if t.role == "point"]
        cta = next((t.text for t in d.on_screen_text if t.role == "cta"), "")
        seq: list[tuple[str, dict]] = []
        if hook:
            seq.append(("blur_reveal", {"text": hook}))
        for n, c in enumerate(clips[:3], start=1):
            portrait = (c.get("height") or 0) > (c.get("width") or 0)
            seq.append(("phone_mockup" if portrait else "browser_mockup", {"media": str(n), "caption": points[n - 1] if n <= len(points) else ""}))
        if len(points) >= 2:
            seq.append(("floating_cards", {"cards": "|".join(points[:4])}))
        if cta:
            seq.append(("cta_button", {"headline": hook or cta, "button": cta[:24]}))
        seq.append(("logo_reveal", {}))
        span = dur / len(seq)
        chosen = [_G(t, i * span / dur, span, f) for i, (t, f) in enumerate(seq)]
    return motion.items_from_directive(chosen, dur, 0, 0, media)


def timeline(rid: str, plan: dict, d, settings: dict, kit: dict | None, narration: dict | None, project: Path,
             motion_items: list[dict], clips: list[tuple[dict, Path]]) -> dict:
    w, h, dur = plan["width"], plan["height"], plan["duration"]
    brand, preset = tl.brand_snapshot(kit, d.treatment[:80])
    # Mode B branding is opt-in per edit: intro/outro cards would change the planned length and beat grid.
    brand = {**brand, "intro": {**brand["intro"], "enabled": False}, "outro": {**brand["outro"], "enabled": False}}
    assets = {"base": {"id": "base", "kind": "video", "src": "base.mp4", "width": w, "height": h, "duration": dur}}
    if kit and kit.get("logo"):
        name, data = tl.logo_file(kit["logo"])
        (project / name).write_bytes(data)
        assets["logo"] = {"id": "logo", "kind": "image", "src": name}
        brand["logoAssetId"] = "logo"
    used = {m for it in motion_items for m in it["media"]}
    for n, (a, path) in enumerate(clips, start=1):  # uploads shown inside mockups/galleries are linked next to the render
        aid = f"media-{n}"
        if aid not in used:
            continue
        name = f"{aid}{path.suffix.lower()}"
        if not (project / name).exists():
            try:
                os.link(path, project / name)
            except OSError:
                shutil.copyfile(path, project / name)
        assets[aid] = {"id": aid, "kind": "image" if a["kind"] == "image" else "video", "src": name,
                       **({"duration": a["duration_s"]} if a.get("duration_s") else {})}
    video = {
        "id": "edit", "type": "video", "assetId": "base", "start": 0, "duration": dur, "sourceStart": 0,
        "sourceEnd": dur, "volume": 1,
        "cropKeyframes": [{"t": 0, "crop_x": 0, "crop_y": 0, "crop_width": w, "crop_height": h, "layout": "crop",
                           "region": "full", "transition_mode": "start"}],
    }
    scenes = [(m["start"], m["start"] + m["duration"]) for m in motion_items if motion.TEMPLATES[m["template"]]["fn"].__name__ not in ("lower_third", "light_sweep", "shape_burst")]
    texts = []
    for n, t in enumerate(d.on_screen_text):
        y, size, show = TEXT_ROLE[t.role]
        start = round(min(max(t.at * dur, 0), dur - 0.8), 3)
        length = round(min(show, dur - start), 3)
        if any(abs(start - x["start"]) < 0.5 for x in texts) or any(a - 0.2 < start < b for a, b in scenes):
            continue  # unreadable on top of another line, or already said by a designed scene
        texts.append({"id": f"text-{n}", "type": "text", "start": start, "duration": length, "text": t.text,
                      "x": 80, "y": round(y * h), "fontSize": round(size * min(w, h) / 1080), "align": "left",
                      "box": True, "transition": "zoom" if t.role == "hook" else "fade"})
    tracks = [{"id": "video", "kind": "video", "items": [video]}]
    if motion_items:
        tracks.append({"id": "graphics", "kind": "overlay", "items": motion_items})
    if texts:
        tracks.append({"id": "text", "kind": "text", "items": texts})
    if settings.get("captions") and narration:
        words = [x for x in narration["words"] if x["end"] <= dur]
        tracks.append({"id": "captions", "kind": "caption", "items": [
            {"id": "captions", "type": "caption", "start": 0, "duration": dur, "words": words}]})
    style = {**tl.CAPTION_STYLE, "preset": preset}
    if settings.get("captions"):
        style = _caption_style(settings.get("caption_preset", ""), style, h)
    return {
        "id": rid, "schemaVersion": 1, "title": d.treatment[:120], "fps": plan["fps"], "width": w, "height": h,
        "duration": dur, "assets": assets, "tracks": tracks, "brand": brand, "captionStyle": style,
        "stylePreset": "focus", "renderSettings": {"quality": settings.get("quality", "looks")},
    }


def _caption_style(preset: str, style: dict, h: int) -> dict:
    """Caption preset id → caption style (100-preset library in rendering/caption_presets.py when present)."""
    try:
        from app.services.rendering import caption_presets
    except ImportError:
        return {**style, "preset": preset if preset in ("highlight-word", "karaoke", "boxed") else "highlight-word"}
    return caption_presets.style_for(preset, style, h)
