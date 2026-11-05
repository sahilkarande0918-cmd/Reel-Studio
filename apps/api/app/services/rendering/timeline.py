"""Canonical timeline from a highlight: one source video item following the crop keyframes, plus
word-level captions from the corrected transcript. Validated against the schema generated from
`packages/timeline-schema` (Zod is the source of truth)."""

import base64
import binascii
import hashlib
import json
import re
from functools import cache
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parents[5] / "packages" / "timeline-schema" / "timeline.schema.json"
W, H = 1080, 1920
# output formats: Shorts/Reels/TikTok 9:16, feed 4:5 and 1:1, YouTube/landscape 16:9
ASPECTS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}

DEFAULT_BRAND = {
    "name": "",
    "handle": "",
    "colors": {"background": "#0d0f12", "text": "#ffffff", "accent": "#f5a524"},
    "fonts": {"body": "Archivo", "code": "JetBrains Mono"},
    "watermark": {"enabled": False, "position": "top-right"},
    "intro": {"enabled": False, "duration": 2, "title": ""},
    "outro": {"enabled": False, "duration": 3, "cta": ""},
}
LOGO_TYPES = {"png": "png", "jpeg": "jpg", "webp": "webp", "svg+xml": "svg"}
LOGO_MAX_BYTES = 300 * 1024
CAPTION_STYLE = {
    "preset": "highlight-word",
    "fontSize": 60,
    "maxCharsPerLine": 26,
    "maxLines": 2,
    "safeTop": 1350,
    "safeBottom": 1650,
}
SOCIAL_CAPTIONS = {"fontSize": 74, "maxCharsPerLine": 16, "maxLines": 2}
CAPTION_ZONES = {"lower": (1350, 1650), "upper": (260, 560)}  # clear of the platforms' top and bottom UI
# camelCase / PascalCase with an inner capital, dotted or called identifiers, operators
CODE_RE = re.compile(r"[a-z][A-Z]|^[A-Z][a-z]+[A-Z]|\w[._]\w|\(\)|[<>{}=]")


def is_code(text: str) -> bool:
    return bool(CODE_RE.search(text.strip(".,!?;:\"'")))


@cache
def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(doc: dict) -> None:
    """JSON Schema shape check, then the cross-field rules Zod's superRefine enforces in TS."""
    jsonschema.validate(doc, _schema())
    logo = doc["brand"].get("logoAssetId")
    if logo and logo not in doc["assets"]:
        raise jsonschema.ValidationError(f"unknown asset {logo}")
    for track in doc["tracks"]:
        for item in track["items"]:
            if item["start"] + item["duration"] > doc["duration"] + 1e-3:
                raise jsonschema.ValidationError(f"item {item['id']} ends after the composition")
            if item["type"] in ("video", "audio"):
                if item["start"] < 0:
                    raise jsonschema.ValidationError("video item starts before the composition")
                if item["assetId"] not in doc["assets"]:
                    raise jsonschema.ValidationError(f"unknown asset {item['assetId']}")
                asset = doc["assets"][item["assetId"]]
                if asset["kind"] != item["type"]:
                    raise jsonschema.ValidationError("media asset kind must match item type")
                if item.get("fadeIn", 0) + item.get("fadeOut", 0) > item["duration"] + 1e-3:
                    raise jsonschema.ValidationError("fades are longer than the item")
                if abs(item["sourceEnd"] - item["sourceStart"] - item["duration"]) > 1e-3:
                    raise jsonschema.ValidationError("duration must equal sourceEnd - sourceStart")
                if "duration" in asset and item["sourceEnd"] > asset["duration"] + 1e-3:
                    raise jsonschema.ValidationError("sourceEnd exceeds asset duration")
            if item["type"] == "motion":
                from app.services.rendering import motion

                if item["template"] not in motion.TEMPLATES:
                    raise jsonschema.ValidationError(f"unknown motion template {item['template']}")
                if any(a not in doc["assets"] or doc["assets"][a]["kind"] not in ("image", "video") for a in item.get("media", [])):
                    raise jsonschema.ValidationError("motion media must be image or video assets")
            if item["type"] == "caption" and any(
                w["end"] < w["start"] or w["end"] > item["duration"] + 1e-3 for w in item["words"]
            ):
                raise jsonschema.ValidationError("caption word timing is outside the item")
            if item["type"] == "code":
                changes = item.get("changes", [])
                if item.get("typingDuration", 2) > item["duration"] or any(
                    change["at"] + change["typingDuration"] > item["duration"]
                    or (i > 0 and change["at"] <= changes[i - 1]["at"])
                    for i, change in enumerate(changes)
                ):
                    raise jsonschema.ValidationError("code changes must be ordered and finish within the item")


def logo_file(data_url: str) -> tuple[str, bytes]:
    """Decode a kit logo data URL → (file name, bytes). The name carries a content hash, so a changed logo
    changes the timeline (and the render cache key)."""
    m = re.fullmatch(r"data:image/(png|jpeg|webp|svg\+xml);base64,([A-Za-z0-9+/=]+)", data_url or "")
    if not m:
        raise ValueError("logo must be a base64 PNG, JPEG, WebP or SVG data URL")
    try:
        data = base64.b64decode(m.group(2), validate=True)
    except binascii.Error as e:
        raise ValueError("logo is not valid base64") from e
    if not data or len(data) > LOGO_MAX_BYTES:
        raise ValueError("logo must be 1 byte to 300 KB")
    return f"logo-{hashlib.sha256(data).hexdigest()[:12]}.{LOGO_TYPES[m.group(1)]}", data


def brand_snapshot(kit: dict | None, title: str) -> tuple[dict, str]:
    """Timeline brand + caption preset from a brand_kits row (None → neutral defaults, no intro/outro)."""
    if not kit:
        return DEFAULT_BRAND, "highlight-word"
    intro, outro = kit["intro"], kit["outro"]
    brand = {
        "name": kit["name"],
        "handle": kit.get("handle") or "",
        "colors": kit["colors"],
        "fonts": kit["fonts"],
        "watermark": kit["watermark"],
        "intro": {
            "enabled": bool(intro.get("enabled")),
            "duration": float(intro.get("duration", 2)),
            "title": (intro.get("title") or "{title}").replace("{title}", title)[:80],
        },
        "outro": {
            "enabled": bool(outro.get("enabled")),
            "duration": float(outro.get("duration", 3)),
            "cta": (outro.get("cta") or "")[:80],
        },
    }
    return brand, kit.get("caption_preset") or "highlight-word"


def caption_words(words: list[dict], start: float, end: float) -> list[dict]:
    """Transcript words inside [start, end] on the clip clock; merged/blank corrections are dropped."""
    out = []
    for w in sorted(words, key=lambda w: w["start_s"]):
        text = (w.get("corrected_text") or "").strip()
        mid = (w["start_s"] + w["end_s"]) / 2
        if not text or not start <= mid <= end:
            continue
        s = round(max(w["start_s"] - start, 0.0), 3)
        e = round(min(w["end_s"] - start, end - start), 3)
        out.append({"text": text, "start": s, "end": max(e, s), "isCode": is_code(text)})
    return out


NUM = re.compile(r"^[₹$]?\d[\d,.]*%?$")
UNITS = {"percent", "%", "crore", "lakh", "million", "billion", "thousand", "dollars", "rupees", "x", "times", "minutes",
         "hours", "days", "months", "years", "customers", "users", "people"}


def motion_items(words: list[dict], duration: float, topic: str | None, W: int, H: int,
                 busy: list[tuple[float, float]]) -> list[dict]:
    """Motion graphics grounded in the clip: a callout for spoken numbers ("40 percent", "₹2 crore"), at most two,
    4 s apart, never over the headline; a lower third naming the clip's topic early on."""
    out: list[dict] = []
    last = -99.0
    for i, w in enumerate(words):
        t = w["text"].strip(".,!?;:\"'")
        if not NUM.match(t) or w["start"] - last < 4 or w["start"] + 1.8 > duration:
            continue
        if any(a - 0.3 < w["start"] < b + 0.3 for a, b in busy):
            continue
        nxt = words[i + 1]["text"].strip(".,!?;:\"'").lower() if i + 1 < len(words) else ""
        label = f"{t} {nxt}" if nxt in UNITS else t
        out.append({"id": f"callout-{len(out)}", "type": "text", "start": round(w["start"], 3), "duration": 1.8,
                    "text": label.upper()[:24], "x": W / 2, "y": round(H * 0.3), "fontSize": 120, "align": "center",
                    "style": "callout"})
        last = w["start"]
        if len(out) == 2:
            break
    if topic and duration > 9:
        start = 3.0 if not any(a < 3.0 < b for a, b in busy) else 6.0
        if start + 3.5 < duration:
            out.append({"id": "lower-third", "type": "text", "start": start, "duration": 3.2,
                        "text": topic.strip()[:40].title(), "x": 60, "y": round(H * 0.62), "fontSize": 46,
                        "align": "left", "style": "lower_third"})
    return out


def _even(v: float) -> int:
    return int(v) // 2 * 2


def _fit(box: dict, ar: float, src_w: int, src_h: int) -> dict:
    """The largest box of aspect `ar` centred where `box` is centred, inside the source (faces stay in frame)."""
    cx, cy = box["crop_x"] + box["crop_width"] / 2, box["crop_y"] + box["crop_height"] / 2
    h = min(box["crop_height"], src_h)
    w = h * ar
    if w > src_w:
        w, h = src_w, src_w / ar
    w, h = _even(w), _even(h)
    x = _even(min(max(cx - w / 2, 0), src_w - w))
    y = _even(min(max(cy - h / 2, 0), src_h - h))
    return {"crop_x": x, "crop_y": y, "crop_width": w, "crop_height": h}


def reaspect(keyframes: list[dict], src_w: int, src_h: int, out_w: int, out_h: int) -> list[dict]:
    """Crop keyframes planned for 9:16 → the same subjects framed for another output shape. A split screen stacks
    two halves in portrait/square and sits side by side in landscape; a panel (whole frame) stays a panel."""
    out = []
    for k in keyframes:
        if k["layout"] == "panel":
            out.append(k)
        elif k["layout"] == "split" and k.get("second"):
            half = (out_w / 2) / out_h if out_w > out_h else out_w / (out_h / 2)
            out.append({**k, **_fit(k, half, src_w, src_h), "second": _fit(k["second"], half, src_w, src_h)})
        else:
            out.append({**k, **_fit(k, out_w / out_h, src_w, src_h)})
    return out


ZOOM, ZOOM_S = 1.15, 1.8


def _punch(items: list[dict], at: float) -> None:
    """Cut to a 1.15x tighter crop of the current framing at composition time `at` for 1.8 s (or until the next
    framing change), then cut back. A split screen is never zoomed."""
    for it in items:
        rel = at - it["start"]
        if not 0.3 <= rel <= it["duration"] - 0.6:
            continue
        ks = sorted(it["cropKeyframes"], key=lambda k: k["t"])
        k = [x for x in ks if x["t"] <= rel][-1]
        nxt = next((x["t"] for x in ks if x["t"] > rel), it["duration"])
        if k["layout"] == "split" or k.get("region") == "zoom":
            return
        w, h = int(k["crop_width"] / ZOOM) // 2 * 2, int(k["crop_height"] / ZOOM) // 2 * 2
        x = int(k["crop_x"] + (k["crop_width"] - w) / 2) // 2 * 2
        y = int(k["crop_y"] + (k["crop_height"] - h) * 0.4) // 2 * 2  # keep faces in the upper part of the frame
        z = {**k, "t": round(rel, 3), "crop_x": x, "crop_y": y, "crop_width": w, "crop_height": h, "region": "zoom",
             "transition_mode": "cut"}
        back = rel + ZOOM_S
        new = [z] + ([{**k, "t": round(back, 3), "transition_mode": "cut"}] if back < min(nxt, it["duration"] - 0.2) else [])
        it["cropKeyframes"] = sorted(ks + new, key=lambda q: q["t"])
        return


def build(
    highlight: dict,
    recording: dict,
    words: list[dict],
    render_id: str,
    quality: str = "looks",
    kit: dict | None = None,
    logo_src: str | None = None,
    spans: list[list[float]] | None = None,
    hook_title: str | None = None,
    emphasis: bool = False,
    hook_style: str = "classic",
    auto_zoom: bool = False,
    color_correct: bool = False,
    sfx: bool = False,
    aspect: str = "9:16",
    motion: bool = False,
    emojis: bool = False,
    progress_bar: bool = False,
    transitions: str = "none",
) -> dict:
    """`logo_src` is the logo file name the caller wrote into the render directory (see `logo_file`).
    `spans`: source stretches played back to back (speech-aware cuts, an opening teaser); None = the whole clip.
    `hook_title`: an opening headline text item (first 2.5 s). `emphasis`: content-chosen caption emphasis."""
    start, end = float(highlight["start_s"]), float(highlight["end_s"])
    duration = round(end - start, 3)
    if spans:
        duration = round(sum(round(b - a, 3) for a, b in spans), 3)
    title = (highlight.get("title") or "")[:120]
    brand, preset = brand_snapshot(kit, title)
    OW, OH = ASPECTS.get(aspect, (W, H))
    zone = tuple(round(v * OH / H) for v in CAPTION_ZONES[(kit or {}).get("caption_position") or "lower"])
    lead = brand["intro"]["duration"] if brand["intro"]["enabled"] else 0.0
    tail = brand["outro"]["duration"] if brand["outro"]["enabled"] else 0.0
    assets = {
        "source": {
            "id": "source",
            "kind": "video",
            "src": "source" + Path(recording["filename"]).suffix.lower(),
            "width": recording["width"],
            "height": recording["height"],
            "duration": recording.get("duration_s") or end,
        }
    }
    if logo_src:
        assets["logo"] = {"id": "logo", "kind": "image", "src": logo_src}
        brand = {**brand, "logoAssetId": "logo"}
    keyframes = highlight.get("crop_keyframes") or []
    if not keyframes:  # centred window of the output's shape
        cw = min(recording["width"], int(round(recording["height"] * OW / OH / 2) * 2))
        keyframes = [
            {
                "t": 0.0,
                "crop_x": (recording["width"] - cw) // 2,
                "crop_y": 0,
                "crop_width": cw,
                "crop_height": recording["height"],
                "layout": "crop",
                "region": "hold",
                "transition_mode": "start",
            }
        ]
    if (OW, OH) != (W, H):
        keyframes = reaspect(keyframes, recording["width"], recording["height"], OW, OH)
    if spans:
        video_items, cap_words, off = [], [], lead
        for n, (a, b) in enumerate(spans):
            d = round(b - a, 3)
            rel = a - start
            ks = sorted(keyframes, key=lambda k: float(k["t"]))
            held = [k for k in ks if float(k["t"]) <= rel + 1e-6][-1:] or ks[:1]
            inside = [{**k, "t": round(float(k["t"]) - rel, 3)} for k in ks if rel + 1e-6 < float(k["t"]) < rel + d]
            video_items.append({"id": f"clip-{n}", "type": "video", "assetId": "source", "start": round(off, 3),
                                "duration": d, "sourceStart": round(a, 3), "sourceEnd": round(round(a, 3) + d, 3),
                                "volume": 1, "cropKeyframes": [{**held[0], "t": 0.0}, *inside]})
            off += d
        from app.services.clips import speech_cuts

        for w in speech_cuts.remap(words, spans):
            text = (w.get("corrected_text") or "").strip()
            cap_words.append({"text": text, "start": w["clip_start"], "end": min(w["clip_end"], duration),
                              "isCode": is_code(text)})
    else:
        keyframes = [{**k, "t": min(max(float(k["t"]), 0.0), duration)} for k in keyframes]
        video_items = [{"id": "clip", "type": "video", "assetId": "source", "start": lead, "duration": duration,
                        "sourceStart": start, "sourceEnd": round(start + duration, 3), "volume": 1,
                        "cropKeyframes": keyframes}]
        cap_words = caption_words(words, start, end)
    zooms: list[float] = []
    if emphasis or auto_zoom:
        from app.services.rendering import caption_auto

        marked = caption_auto.emphasise(cap_words)
        if emphasis:
            cap_words = marked
        if auto_zoom:  # punch in on the words that carry the point, never more than one every 5 s
            for w in marked:
                if w["emphasis"] and w["start"] >= 1.5 and (not zooms or w["start"] - zooms[-1] >= 5.0):
                    zooms.append(w["start"])
            for z in zooms:
                _punch(video_items, lead + z)
    doc = {
        "id": render_id,
        "schemaVersion": 1,
        "fps": 30,
        "width": OW,
        "height": OH,
        "title": title,
        "duration": round(lead + duration + tail, 3),
        "source": {"recordingId": recording["id"], "highlightId": highlight["id"]},
        "assets": assets,
        "tracks": [
            {
                "id": "video",
                "kind": "video",
                "items": video_items,
            },
            {
                "id": "captions",
                "kind": "caption",
                "items": [
                    {
                        "id": "captions",
                        "type": "caption",
                        "start": lead,
                        "duration": duration,
                        "words": cap_words,
                    }
                ],
            },
        ],
        "brand": brand,
        "captionStyle": {**CAPTION_STYLE, "preset": preset, "safeTop": zone[0], "safeBottom": zone[1],
                         # talk clips (bulk clipping): short-form grouping, 2-4 words per line, larger type
                         **(SOCIAL_CAPTIONS if (highlight.get("features") or {}).get("profile") not in (None, "education")
                            else {})},
        "renderSettings": {"quality": quality},
    }
    if hook_title:
        y = round((300 if zone[0] >= OH / 2 else 1480) * OH / H)  # clear of the captions, scaled to the format
        doc["tracks"].append({"id": "titles", "kind": "overlay", "items": [
            {"id": "hook-title", "type": "text", "start": lead, "duration": round(min(2.5, duration), 3),
             "text": hook_title[:80], "x": OW / 2, "y": y, "fontSize": 64, "align": "center", "box": True,
             "style": hook_style}]})
    if color_correct:
        doc["renderSettings"]["colorCorrect"] = True
    if transitions != "none":
        doc["renderSettings"]["transitions"] = transitions
    if progress_bar:
        doc["renderSettings"]["progressBar"] = True
    busy = [(0.0, 2.6)] if hook_title else []  # the headline's first seconds stay clear
    if motion:
        graphics = motion_items(cap_words, duration, (highlight.get("features") or {}).get("topic"), OW, OH, busy)
        for g in graphics:
            g["start"] = round(lead + g["start"], 3)
        if graphics:
            doc["tracks"].append({"id": "graphics", "kind": "overlay", "items": graphics})
            busy += [(g["start"] - lead, g["start"] - lead + g["duration"]) for g in graphics if g["style"] == "callout"]
    if emojis:
        from app.services.rendering import emoji

        picks = [e for e in emoji.choose(cap_words, duration)
                 if not any(a - 0.3 < e["at"] < b + 0.3 for a, b in busy)]
        if picks:
            doc["renderSettings"]["emojis"] = [{**e, "at": round(lead + e["at"], 3)} for e in picks[:30]]
    if sfx:  # a whoosh as the headline lands, a soft impact under each punch-in
        cues = ([{"kind": "whoosh", "at": round(lead + 0.15, 3)}] if hook_title else []) + [
            {"kind": "impact", "at": round(lead + z, 3)} for z in zooms]
        if cues:
            doc["renderSettings"]["sfx"] = cues
    validate(doc)
    return doc


def timeline_hash(doc: dict) -> str:
    """Identity of what would be rendered (ignores the render id) — the render cache key."""
    body = {k: v for k, v in doc.items() if k != "id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
