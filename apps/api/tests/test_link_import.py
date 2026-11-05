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
