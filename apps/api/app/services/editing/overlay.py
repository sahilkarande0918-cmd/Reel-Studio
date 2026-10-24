"""Mode B plan → canonical timeline (packages/timeline-schema): the FFmpeg base picture as one video item (it already
carries the mixed music/SFX/voice), plus the overlay layers Hyperframes renders on top — motion-graphic scenes,
on-screen text and captions. The same document opens in the editor, so preview and export share one source of truth."""

import os
import re
import shutil
from pathlib import Path

from app.services.rendering import blender, caption_presets, motion
from app.services.rendering import timeline as tl

TEXT_ROLE = {  # (y as share of height, font size, seconds on screen)
    "hook": (0.16, 84, 2.2),
    "point": (0.2, 64, 1.8),
    "cta": (0.68, 72, 2.4),
}
DESIGNED = ("motion_graphics", "tech_ad")


# genuine 3D scenes (headless Blender); a Hyperframes template stands in when Blender is not installed
BLENDER = {"3d_title": ("text_3d", "blur_reveal"), "3d_product": ("product_turntable", "media_card")}


def templates() -> dict[str, dict]:
    out = {k: {"description": t["description"], "fields": list(t["fields"])} for k, t in motion.TEMPLATES.items()}
    out["3d_title"] = {"description": "GENUINE 3D extruded title on a reflective floor, orbiting camera (only for 3D requests)",
                       "fields": ["text", "subtitle"]}
    out["3d_product"] = {"description": "GENUINE 3D turntable: one image on a rotating card on a glowing plinth (only for 3D requests)",
                         "fields": ["media"]}
    return out


def split_3d(d) -> tuple[list, list[dict], list[str]]:
    """(2D graphics, 3D scene requests, substitution notes). Without Blender, each 3D scene becomes its stand-in."""
    flat, scenes, notes = [], [], []
    for g in d.graphics:
        if g.template not in BLENDER:
            flat.append(g)
        elif blender.available():
            scenes.append(g)
        else:
            sub = BLENDER[g.template][1]
            notes.append(f"{g.template} needs Blender, which is not installed: used the 2D '{sub}' template instead")
            flat.append(_G(sub, g.at, g.duration_s, dict(g.fields or {})))
    return flat, scenes, notes


def has_overlays(doc: dict) -> bool:
    return any(i["type"] in ("text", "caption", "motion", "code") or i["id"] != "edit"
               for t in doc["tracks"] for i in t["items"]) or bool(
        doc["brand"].get("watermark", {}).get("enabled")
    )


class _G:  # the director's Graphic shape, for scenes the structure fallback adds
    def __init__(self, template: str, at: float, duration_s: float, fields: dict):
        self.template, self.at, self.duration_s, self.fields = template, at, duration_s, fields


LISTS = {"info_list": "items", "notifications": "items", "floating_cards": "cards"}
STEP_NO = re.compile(r"^\s*(?:step\s*)?(\d+)\s*[.):-]\s*", re.IGNORECASE)


def merge_lists(chosen: list, title: str = "") -> list:
    """The local model often splits one list into one scene per item ("01 4. publish" four times, in any order). All
    scenes of a list template become one scene at the first one's position, items de-numbered (the template numbers
    them) and put in their stated step order."""
    out, merged = [], {}
    for g in chosen:
        key = LISTS.get(g.template)
        if not key:
            out.append(g)
            continue
        items = [x.strip() for x in str((g.fields or {}).get(key, "")).split("|") if x.strip()]
        if g.template not in merged:
            merged[g.template] = _G(g.template, g.at, g.duration_s, dict(g.fields or {}))
            merged[g.template].parts = []
            out.append(merged[g.template])
        else:
            merged[g.template].duration_s += g.duration_s
        merged[g.template].parts += items
    for t, g in merged.items():
        numbered = [STEP_NO.match(x) for x in g.parts]
        order = sorted(range(len(g.parts)), key=lambda i: int(numbered[i].group(1))) if all(numbered) else range(len(g.parts))
        items = list(dict.fromkeys(STEP_NO.sub("", g.parts[i]).strip() for i in order))
        g.fields[LISTS[t]] = "|".join(items)
        if len(items) > 1 and "title" in g.fields:
            g.fields["title"] = title or "How it works"
    return out


def graphics(d, dur: float, clips: list[dict], chosen: list | None = None) -> list[dict]:
    """Motion items for the edit. Designed styles (motion graphics / tech ad) need scenes across most of the edit; when
    the model chose too few, a structure is added from what is known — the request's own on-screen lines and the
    uploaded media in mockups — never invented claims. `clips` are the media assets in director numbering (1-based)."""
    media = {n + 1: f"media-{n + 1}" for n in range(len(clips))}
    chosen = sorted(d.graphics if chosen is None else chosen, key=lambda g: g.at)
    chosen = merge_lists(chosen, next((t.text for t in d.on_screen_text if t.role == "hook"), ""))
    if d.style in DESIGNED and chosen:  # the director's scenes, each held until the next one starts (a designed ad
        starts = [g.at * dur for g in chosen] + [dur]  # flows scene to scene instead of dropping back to footage)
        chosen = [_G(g.template, g.at, min(8.0, max(1.5, starts[i + 1] - starts[i])), dict(g.fields or {}))
                  for i, g in enumerate(chosen)]
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
             motion_items: list[dict], clips: list[tuple[dict, Path]], shots_3d: list[dict] | None = None) -> dict:
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
    scenes = [(m["start"], m["start"] + m["duration"]) for m in motion_items if m["template"] not in ("lower_third", "light_sweep", "shape_burst")]
    scenes += [(s["start"], s["start"] + s["duration"]) for s in shots_3d or []]
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
    if shots_3d:  # Blender renders sit above the footage for their window, on the same frame clock
        for s in shots_3d:
            assets[s["id"]] = {"id": s["id"], "kind": "video", "src": s["src"], "width": w, "height": h, "duration": s["duration"]}
        tracks.append({"id": "3d", "kind": "video", "items": [
            {"id": s["id"], "type": "video", "assetId": s["id"], "start": s["start"], "duration": s["duration"], "sourceStart": 0,
             "sourceEnd": s["duration"], "volume": 0, "cropKeyframes": video["cropKeyframes"]} for s in shots_3d]})
    if motion_items:
        tracks.append({"id": "graphics", "kind": "overlay", "items": motion_items})
    if texts:
        tracks.append({"id": "text", "kind": "text", "items": texts})
    if settings.get("captions") and narration:
        words = [x for x in narration["words"] if x["end"] <= dur]
        tracks.append({"id": "captions", "kind": "caption", "items": [
            {"id": "captions", "type": "caption", "start": 0, "duration": dur, "words": words}]})
    style = {**tl.CAPTION_STYLE, "preset": preset, "enabled": bool(settings.get("captions"))}
    if settings.get("captions"):
        over = {k: v for k, v in (settings.get("caption_overrides") or {}).items() if v is not None}
        style = caption_presets.style_for(settings.get("caption_preset", ""), style, h, brand["colors"], over)
    return {
        "id": rid, "schemaVersion": 1, "title": d.treatment[:120], "fps": plan["fps"], "width": w, "height": h,
        "duration": dur, "assets": assets, "tracks": tracks, "brand": brand, "captionStyle": style,
        "stylePreset": "focus", "renderSettings": {"quality": settings.get("quality", "looks")},
    }

