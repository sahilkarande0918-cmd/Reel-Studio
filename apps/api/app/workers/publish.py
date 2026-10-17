"""Durable Instagram publishing. Persist the container before the irreversible publish call."""

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core import signing
from app.core.config import get_settings
from app.core.db import service_client
from app.services import media
from app.services.publishing.accounts import instagram_client
from app.workers.jobs import JobContext, Permanent


def _update(pid: str, **fields) -> None:
    service_client().table("publish_jobs").update({**fields, "updated_at": datetime.now(UTC).isoformat()}).eq(
        "id", pid
    ).execute()


def eligible(info: dict) -> None:
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])
    if not video or not audio or video["codec_name"] != "h264" or audio["codec_name"] != "aac":
        raise Permanent("Export must contain H.264 video and AAC audio")
    if not 3 <= duration <= 900 or video["width"] > 1920:
        raise Permanent("Instagram Reel must be 3–900 seconds with width at most 1920 pixels")
    if abs(video["width"] / video["height"] - 9 / 16) > 0.02:
        raise Permanent("Select a portrait 9:16 export")


def instagram_copy(src: Path) -> Path:
    """Delivery copy in the encoding Instagram's Reels pipeline expects (H.264 High 4.1, 2 s GOP, steady
    bitrate, AAC 48 kHz). Mostly static topic videos encode to a few hundred kbit/s, which Instagram
    rejected with a generic processing ERROR. Same frames and audio; cached next to the render."""
    out = src.with_name("instagram.mp4")
    if out.is_file() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    tmp = src.with_name("instagram.tmp.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-profile:v", "high",
                    "-level:v", "4.1", "-pix_fmt", "yuv420p", "-preset", "medium", "-b:v", "3500k", "-minrate", "3500k",
                    "-maxrate", "3500k", "-bufsize", "7M", "-x264-params", "nal-hrd=cbr", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
                    "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                    str(tmp)], check=True, timeout=900)
    tmp.replace(out)
    return out


def run_publish(ctx: JobContext) -> dict:
    db, s = service_client(), get_settings()
    row = db.table("publish_jobs").select("*").eq("id", ctx.payload["publish_id"]).single().execute().data
    pid = row["id"]
    if row["platform_post_id"]:
        return {"publish_id": pid, "platform_post_id": row["platform_post_id"]}
    if row["status"] in ("publishing", "needs_review"):
        _update(
            pid,
            status="needs_review",
            error="Previous publish outcome is unknown; check Instagram before retrying.",
        )
        raise Permanent("Publish outcome needs review; automatic retry stopped to prevent duplicates")
    if row["status"] == "cancelled":
        raise Permanent("Publication was cancelled")
    account = db.table("social_accounts").select("*").eq("id", row["account_id"]).single().execute().data
    render = db.table("render_jobs").select("*").eq("id", row["render_id"]).single().execute().data
    if (
        account["organization_id"] != row["organization_id"]
        or render["organization_id"] != row["organization_id"]
    ):
        raise Permanent("Publication ownership mismatch")
    if account["platform"] != "instagram" or account["status"] != "connected":
        raise Permanent("Reconnect Instagram before publishing")
    ctx.stage("validate_export", 0.05, "Checking the MP4 for Instagram")
    path = s.data_dir / render["output_path"]
    if not path.is_file() or path.stat().st_size > 1024**3:
        raise Permanent("Export file is unavailable or exceeds Instagram's 1 GB limit")
    eligible(media.probe(path))
    ctx.stage("instagram_encode", 0.08, "Preparing an Instagram-ready copy of the video")
    eligible(media.probe(instagram_copy(path)))
    adapter = instagram_client(account)
    _update(pid, status="processing", error=None)
    container = row.get("container_id")
    if not container:
        base = s.public_api_url.rstrip("/")
        if urlparse(base).scheme != "https":
            raise Permanent("Instagram requires the public HTTPS processing-backend URL")
        query, _ = signing.query("render-instagram", render["id"])
        video_url = f"{base}/renders/{render['id']}/file/instagram?{query}"
        # No bypass header here: Meta must be able to ingest the URL itself.
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                with client.stream("GET", video_url, headers={"Range": "bytes=0-1023"}) as response:
                    if response.status_code not in (200, 206) or not response.headers.get(
                        "content-type", ""
                    ).startswith("video/"):
                        raise Permanent("Public media URL is not serving a video to unauthenticated clients")
        except httpx.HTTPError:
            raise RuntimeError(
                "Public media URL is unreachable from this machine; verify HTTPS tunnel access"
            ) from None
        ctx.stage("instagram_container", 0.15, "Uploading the Reel to Instagram processing")
        container = adapter.create_reel(account["platform_user_id"], video_url, row["caption"])
        _update(pid, container_id=container)
    ctx.stage("instagram_processing", 0.35, "Waiting for Instagram to process the video")
    for attempt in range(80):  # ~6 min: quick checks first (most Reels finish in under a minute), then every 6 s
        ctx.check_cancel()
        info = adapter.container(container)
        state = info.get("status_code")
        if state == "FINISHED":
            break
        if state in ("ERROR", "EXPIRED"):
            _update(pid, container_id=None)
            # Instagram's own status text says why (e.g. an unsupported format); keep it, it has no secrets.
            raise RuntimeError(f"Instagram media processing returned {state}: {str(info.get('status', ''))[:300]}")
        if state == "PUBLISHED":
            _update(pid, status="needs_review", error="Container already published; reconcile its media ID")
            raise Permanent("Container already published; automatic duplicate prevented")
        time.sleep(3 if attempt < 20 else 6)
    else:
        raise RuntimeError("Instagram processing is still pending; the existing container will be retried")
    ctx.stage("instagram_publish", 0.85, "Publishing the processed Reel")
    ctx.check_cancel()
    _update(pid, status="publishing")
    try:
        post_id = adapter.publish(account["platform_user_id"], container)
    except Exception:
        _update(
            pid,
            status="needs_review",
            error="Publish response was not confirmed. Check Instagram before retrying.",
        )
        raise Permanent("Publish outcome unknown; review required to prevent duplicates") from None
    # Persist the actual ID before any optional metadata request.
    _update(pid, status="published", platform_post_id=post_id, error=None)
    try:
        detail = adapter.request("GET", post_id, fields="permalink")
        _update(pid, platform_url=detail.get("permalink"))
    except RuntimeError:
        pass
    return {"publish_id": pid, "platform_post_id": post_id}


REEL_METRICS = ("views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
                "ig_reels_avg_watch_time", "ig_reels_video_view_total_time")


def run_insights(ctx: JobContext) -> dict:
    db = service_client()
    account = (
        db.table("social_accounts").select("*").eq("id", ctx.payload["account_id"]).single().execute().data
    )
    adapter = instagram_client(account)
    metrics, unavailable = [], []
    ctx.stage("instagram_insights", 0.1, "Fetching supported Instagram insights")
    # Per-metric calls preserve supported results when permissions or metrics differ by account.
    for metric in ("views", "reach", "accounts_engaged", "total_interactions"):
        ctx.check_cancel()
        try:
            result = adapter.request(
                "GET",
                f"{account['platform_user_id']}/insights",
                metric=metric,
                period="day",
                metric_type="total_value",
            )
            for value in result.get("data", []):
                total = value.get("total_value", {}).get("value")
                if total is not None:
                    metrics.append(
                        {
                            "name": value["name"],
                            "value": total,
                            "period": value.get("period", "day"),
                            "as_of": datetime.now(UTC).isoformat(),
                        }
                    )
                else:
                    for point in value.get("values", []):
                        metrics.append(
                            {
                                "name": value["name"],
                                "value": point["value"],
                                "period": value.get("period", "day"),
                                "as_of": point.get("end_time"),
                            }
                        )
        except RuntimeError as exc:
            unavailable.append(f"{metric}: {exc}")
    ctx.stage("instagram_media", 0.5, "Fetching recent Reels and their insights")
    media = []
    try:
        listed = adapter.request("GET", f"{account['platform_user_id']}/media", limit=25,
                                 fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count")
        for m in listed.get("data", []):
            ctx.check_cancel()
            entry = {k: m.get(k) for k in ("id", "caption", "media_type", "media_product_type", "timestamp", "permalink",
                                           "like_count", "comments_count")}
            entry["insights"], entry["unavailable"] = {}, []
            # Reels support these per-media metrics; each is requested alone so one unsupported metric
            # never hides the others.
            for metric in REEL_METRICS if m.get("media_product_type") == "REELS" else ("reach", "saved", "shares"):
                try:
                    data = adapter.request("GET", f"{m['id']}/insights", metric=metric).get("data", [])
                    if data and data[0].get("values"):
                        entry["insights"][metric] = data[0]["values"][0].get("value")
                except RuntimeError as exc:
                    entry["unavailable"].append(f"{metric}: {exc}")
            media.append(entry)
    except RuntimeError as exc:
        unavailable.append(f"media: {exc}")
    values = {
        "media": media,
        "account_id": account["id"],
        "organization_id": account["organization_id"],
        "metrics": metrics,
        "unavailable": unavailable,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    db.table("platform_metrics").upsert(values).execute()
    return {"account_id": account["id"], "metrics_received": len(metrics), "unavailable": unavailable}
