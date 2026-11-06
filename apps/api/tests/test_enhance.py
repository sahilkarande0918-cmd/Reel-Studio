"""4K enhancement planning: target size, the text-free base at the source's own pixel density, the 4K overlay args."""

import copy
import subprocess

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
    assert enhance.base_doc(_doc(720), 720, hdr=True)["renderSettings"]["hdrGrade"] is True


def test_overlay_args_redraw_text_at_4k_and_encode_for_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(enhance.fast, "ass", lambda doc: "[Script Info]\n")
    monkeypatch.setattr(enhance.fast, "fonts_dir", lambda: tmp_path / "nofonts")
    (tmp_path / "nofonts").mkdir()
    doc = copy.deepcopy(_doc(720))
    doc["renderSettings"]["emojis"] = []
    args = enhance.overlay_args(doc, tmp_path, 2160, 3840)
    g = args[args.index("-filter_complex") + 1]
    assert "subtitles=captions.ass" in g and g.startswith("[0:v]fps=30")
    assert args[args.index("-b:v") + 1] == "45M" and "bt709" in args
    assert (tmp_path / "captions.ass").is_file()


def test_hdr_cc_grade_runs_and_changes_the_picture(tmp_path):
    """The CapCut "4K HDR CC" layer stack as one FFmpeg graph: parses, renders, brightens a dim frame's shadows."""
    from app.services.rendering import fast

    out = tmp_path / "g.png"
    g = "[0:v]null[s];" + fast.hdr_cc("s", "v", 96)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=96x96:rate=1:duration=1,eq=brightness=-0.2",
                        "-filter_complex", g, "-map", "[v]", "-frames:v", "1", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    def mean(args):
        return float(subprocess.run(["ffmpeg", "-v", "error", *args, "-vf", "format=gray,scale=1:1", "-f", "rawvideo", "-"],
                                    capture_output=True).stdout[0])
    before = mean(["-f", "lavfi", "-i", "testsrc2=size=96x96:rate=1:duration=1,eq=brightness=-0.2", "-frames:v", "1"])
    assert mean(["-i", str(out)]) > before + 5
