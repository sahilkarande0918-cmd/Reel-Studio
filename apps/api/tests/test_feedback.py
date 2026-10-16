from app.services import feedback


def row(d, eng, style="focus", mode="recording"):
    return {"duration_s": d, "engagement": eng, "style": style, "mode": mode, "post_id": str(d), "reach": 100}


def test_needs_enough_real_posts():
    out = feedback.learn([row(40, 0.1), row(50, 0.2)])
    assert out["enough"] is False and out["posts"] == 2


def test_learns_ideal_length_from_top_half():
    out = feedback.learn([row(32, 0.20), row(34, 0.18, "energy"), row(58, 0.03), row(55, 0.04, "energy")])
    assert out["enough"] and out["ideal_duration_s"] == 33.0
    assert out["by_duration"][0]["group"] == "under 35 s"
    assert out["findings"]
