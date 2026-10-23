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


def build(
    highlight: dict,
    recording: dict,
    words: list[dict],
    render_id: str,
    quality: str = "looks",
    kit: dict | None = None,
    logo_src: str | None = None,
) -> dict:
    """`logo_src` is the logo file name the caller wrote into the render directory (see `logo_file`)."""
    start, end = float(highlight["start_s"]), float(highlight["end_s"])
    duration = round(end - start, 3)
    title = (highlight.get("title") or "")[:120]
    brand, preset = brand_snapshot(kit, title)
    zone = CAPTION_ZONES[(kit or {}).get("caption_position") or "lower"]
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
    if not keyframes:  # centred 9:16 window
        cw = int(round(recording["height"] * 9 / 16 / 2) * 2)
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
    keyframes = [{**k, "t": min(max(float(k["t"]), 0.0), duration)} for k in keyframes]
    doc = {
        "id": render_id,
        "schemaVersion": 1,
        "fps": 30,
        "width": W,
        "height": H,
        "title": title,
        "duration": round(lead + duration + tail, 3),
        "source": {"recordingId": recording["id"], "highlightId": highlight["id"]},
        "assets": assets,
        "tracks": [
            {
                "id": "video",
                "kind": "video",
                "items": [
                    {
                        "id": "clip",
                        "type": "video",
                        "assetId": "source",
                        "start": lead,
                        "duration": duration,
                        "sourceStart": start,
                        "sourceEnd": round(start + duration, 3),
                        "volume": 1,
                        "cropKeyframes": keyframes,
                    }
                ],
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
                        "words": caption_words(words, start, end),
                    }
                ],
            },
        ],
        "brand": brand,
        "captionStyle": {**CAPTION_STYLE, "preset": preset, "safeTop": zone[0], "safeBottom": zone[1]},
        "renderSettings": {"quality": quality},
    }
    validate(doc)
    return doc


def timeline_hash(doc: dict) -> str:
    """Identity of what would be rendered (ignores the render id) — the render cache key."""
    body = {k: v for k, v in doc.items() if k != "id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
