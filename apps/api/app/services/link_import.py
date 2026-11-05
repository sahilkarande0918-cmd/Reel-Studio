"""Import a video from a YouTube link on the engine (yt-dlp, Unlicense/public domain, free; Node.js as its JS runtime).

Only YouTube video links are accepted (no playlists, channels or other sites) and only after the user confirms they own
the video or may clip it. The file is downloaded straight onto the processing computer (≤ 1080p, H.264 preferred) and
then handled exactly like an upload, so no download/upload round trip through the user's browser.
"""

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# best ≤1080p: H.264 + AAC first (fast to decode, plays everywhere), then any MP4, then anything (FFmpeg merges)
FORMAT = ("bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/"
          "b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b[height<=1080]/b")


def video_id(url: str) -> str | None:
    """The 11-character video id of a YouTube watch/short/live/embed/youtu.be link, else None."""
    try:
        u = urlparse(url.strip() if "://" in url else "https://" + url.strip())
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.").removeprefix("music.")
    vid = None
    if host == "youtu.be":
        vid = u.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "youtube-nocookie.com"):
        if u.path == "/watch":
            vid = (parse_qs(u.query).get("v") or [None])[0]
        else:
            parts = u.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed", "v"):
                vid = parts[1]
    return vid if vid and ID.match(vid) else None


def normalize(url: str) -> str | None:
    vid = video_id(url)
    return f"https://www.youtube.com/watch?v={vid}" if vid else None


def download(url: str, dest: Path, max_bytes: int, max_s: int, on_progress=None, check_cancel=None) -> dict:
    """Download the video to `dest` (an .mp4 path). Returns {title, duration, uploader, license, webpage_url}.
    Raises ValueError with a readable reason (too long, private, unavailable...)."""
    import yt_dlp

    files: dict[str, tuple[int, int]] = {}  # video and audio streams download one after the other
    shown = [0.0]

    def hook(d: dict) -> None:
        if check_cancel:
            check_cancel()
        if on_progress and d.get("status") in ("downloading", "finished"):
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0) if d["status"] == "downloading" else total
            files[d.get("filename", "")] = (done, total)
            got, want = sum(f[0] for f in files.values()), sum(f[1] for f in files.values())
            # the second stream's size is unknown until it starts, so never let the bar move backwards
            if want:
                shown[0] = max(shown[0], min(got / want, 1.0) * (0.85 if len(files) == 1 else 1.0))
                on_progress(shown[0])

    def too_long(info, *, incomplete):
        dur = info.get("duration")
        if info.get("is_live"):
            return "This is a live stream that is still running; import it after it ends"
        if dur and dur > max_s:
            return f"The video is {dur / 3600:.1f} h long; up to {max_s / 3600:.0f} h is supported"
        return None

    opts = {
        "format": FORMAT, "merge_output_format": "mp4", "outtmpl": str(dest.with_suffix(".%(ext)s")),
        "noplaylist": True, "quiet": True, "no_warnings": True, "noprogress": True, "overwrites": True,
        "max_filesize": max_bytes, "match_filter": too_long, "progress_hooks": [hook], "js_runtimes": {"node": {}},
        "retries": 5, "fragment_retries": 5, "concurrent_fragment_downloads": 4,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        msg = re.sub(r"^ERROR:\s*(\[[^\]]+\]\s*[\w-]+:\s*)?", "", str(e)).strip()
        raise ValueError(msg[:300] or "The video could not be downloaded") from e
    if not dest.exists():
        found = sorted(dest.parent.glob(dest.stem + ".*"), key=lambda p: p.stat().st_size, reverse=True)
        if not found:
            raise ValueError("The video was skipped (too long, a live stream, or larger than 4 GB)")
        found[0].replace(dest)
    return {k: info.get(k) for k in ("title", "duration", "uploader", "license", "webpage_url", "channel")}
