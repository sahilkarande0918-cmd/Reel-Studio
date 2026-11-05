from app.services import link_import as li


def test_youtube_links_are_normalised_and_everything_else_refused():
    vid = "aqz-KE-bpKQ"
    for url in (f"https://www.youtube.com/watch?v={vid}", f"youtube.com/watch?v={vid}&t=42s&list=PL123",
                f"https://youtu.be/{vid}?si=abc", f"https://m.youtube.com/watch?v={vid}",
                f"https://www.youtube.com/shorts/{vid}", f"https://www.youtube.com/live/{vid}?feature=share",
                f"https://www.youtube.com/embed/{vid}"):
        assert li.normalize(url) == f"https://www.youtube.com/watch?v={vid}", url
    for bad in ("https://www.youtube.com/playlist?list=PL123", "https://www.youtube.com/@channel",
                "https://vimeo.com/123456", "https://evil.example/watch?v=aqz-KE-bpKQ",
                "https://youtube.com.evil.example/watch?v=aqz-KE-bpKQ", "https://youtu.be/short", "not a link",
                "file:///C:/Windows/win.ini"):
        assert li.normalize(bad) is None, bad


def test_srt_upload_becomes_timed_words():
    from app.services.transcription import srt

    text = "1\n00:00:01,000 --> 00:00:03,000\n<i>Price on value,</i>\n\n2\n00:00:03.500 --> 00:00:05,000\n- not on cost.\n"
    segs, words = srt.to_words(srt.parse(text))
    assert [s["raw_text"] for s in segs] == ["Price on value,", "not on cost."]
    assert [w["raw_text"] for w in words] == ["Price", "on", "value,", "not", "on", "cost."]
    assert words[0]["start_s"] == 1.0 and words[2]["end_s"] <= 3.0 and words[3]["start_s"] == 3.5
    assert all(a["end_s"] <= b["start_s"] for a, b in zip(words, words[1:]))
