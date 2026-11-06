"""4K enhancement planning: target size, the text-free base at the source's own pixel density, the 4K overlay args."""

import copy

from app.workers import enhance


def _doc(crop_h: int, fps: float = 30) -> dict:
    kf = {"t": 0, "crop_x": 0, "crop_y": 0, "crop_width": int(crop_h * 9 / 16), "crop_height": crop_h,
          "layout": "crop", "region": "speaker-0", "transition_mode": "start"}
    return {"width": 1080, "height": 1920, "fps": fps, "duration": 10.0, "renderSettings": {"emojis": [{"code": "1f525"}],
            "progressBar": True}, "captionStyle": {"safeTop": 200},
            "tracks": [{"items": [{"type": "video", "cropKeyframes": [kf]}, {"type": "text"}]},
                       {"items": [{"type": "caption", "words": []}]}]}


def test_target_is_twice_the_reel():
    assert enhance.target_size(1080, 1920) == (2160, 3840)
    assert enhance.target_size(1920, 1080) == (3840, 2160)


def test_base_uses_native_density_capped_at_a_quarter_of_4k():
    b = enhance.base_doc(_doc(720), 720)  # 720p source: its own 404x720 pixels, never a stretched image
    assert (b["width"], b["height"]) == (404, 720)
    b = enhance.base_doc(_doc(1080), 1080)  # 1080p source: capped at 540x960 (x4 = exactly 2160x3840)
    assert (b["width"], b["height"]) == (540, 960)
    assert all(i["type"] == "video" for t in b["tracks"] for i in t["items"])  # no text: drawn later at 4K
    assert b["renderSettings"]["emojis"] == [] and b["renderSettings"]["progressBar"] is False
    assert enhance.base_doc(_doc(720, 30), 720, 23.976)["fps"] == 23.976  # only the film's real frames
    assert enhance.base_doc(_doc(720, 30), 720, 30)["fps"] == 30


def test_overlay_args_redraw_text_at_4k_and_encode_for_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(enhance.fast, "ass", lambda doc: "[Script Info]\n")
    monkeypatch.setattr(enhance.fast, "fonts_dir", lambda: tmp_path / "nofonts")
    (tmp_path / "nofonts").mkdir()
    doc = copy.deepcopy(_doc(720))
    doc["renderSettings"]["emojis"] = []
    args = enhance.overlay_args(doc, tmp_path, 2160, 3840, vivid=True)
    g = args[args.index("-filter_complex") + 1]
    assert "subtitles=captions.ass" in g and "eq=contrast" in g and g.startswith("[0:v]fps=30")
    assert args[args.index("-b:v") + 1] == "45M" and "bt709" in args
    assert (tmp_path / "captions.ass").is_file()
