from app.services.rendering import caption_presets as cp
from app.services.rendering import compose, timeline


def _doc(style: dict) -> dict:
    brand = timeline.brand_snapshot(None, "")[0]
    words = [{"text": w, "start": i * 0.4, "end": i * 0.4 + 0.35, "isCode": False} for i, w in enumerate("one two three four".split())]
    return {"id": "x", "schemaVersion": 1, "fps": 30, "width": 1080, "height": 1920, "duration": 2,
            "assets": {}, "tracks": [{"id": "c", "kind": "caption", "items": [
                {"id": "c", "type": "caption", "start": 0, "duration": 2, "words": words}]}],
            "brand": brand, "captionStyle": style, "renderSettings": {"quality": "draft"}}


def test_100_distinct_presets_validate_and_compile():
    assert len(cp.PRESETS) == 100 and len(cp.BY_ID) == 100 and len({p["family"] for p in cp.PRESETS}) == 23
    behaviour = {tuple(sorted((k, v) for k, v in p["look"].items() if k not in ("id", "color", "active", "chip", "strokeColor")))
                 for p in cp.PRESETS}
    assert len(behaviour) == 100  # no preset is only a colour swap of another
    for p in cp.PRESETS:
        doc = _doc(cp.style_for(p["id"], dict(timeline.CAPTION_STYLE), 1920))
        timeline.validate(doc)
        page = compose.compile_html(doc)
        assert p["look"]["font"] in page and 'class="w"' in page


def test_captions_off_burns_nothing_but_keeps_words():
    doc = _doc({**timeline.CAPTION_STYLE, "enabled": False})
    timeline.validate(doc)
    assert 'class="w"' not in compose.compile_html(doc)
    assert doc["tracks"][0]["items"][0]["words"]
