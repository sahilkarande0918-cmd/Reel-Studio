"""Durable worker: claims jobs from Supabase with SKIP LOCKED, runs one at a time (one GPU),
heartbeats its lock, retries recoverable failures with backoff and honours cancellation.

    python -m app.workers.run
"""

import logging
import socket
import threading
import time
import traceback
from datetime import UTC, datetime, timedelta

from app.core.db import service_client
from app.workers.analyze import run_analyze
from app.workers.generate import run_generate
from app.workers.jobs import Cancelled, JobContext, Permanent
from app.workers.publish import run_insights, run_publish
from app.workers.render import run_render
from app.workers.transcribe import run_transcribe

log = logging.getLogger("worker")
HANDLERS = {
    "transcribe": run_transcribe,
    "analyze": run_analyze,
    "render": run_render,
    "publish": run_publish,
    "insights": run_insights,
    "generate": run_generate,
}
WORKER_ID = f"{socket.gethostname()}-{int(time.time())}"
POLL_S = 2
HEARTBEAT_S = 30


def _heartbeat(job_id: str, stop: threading.Event) -> None:
    while not stop.wait(HEARTBEAT_S):
        try:
            service_client().table("jobs").update({"locked_at": datetime.now(UTC).isoformat()}).eq(
                "id", job_id
            ).execute()
        except Exception as e:  # noqa: BLE001 — a missed beat only risks a later requeue
            log.warning("heartbeat failed: %s", e)


def finish(job: dict, **fields) -> None:
    service_client().table("jobs").update({"locked_by": None, "locked_at": None, **fields}).eq(
        "id", job["id"]
    ).execute()


def run_one(job: dict) -> None:
    ctx = JobContext(job)
    stop = threading.Event()
    threading.Thread(target=_heartbeat, args=(job["id"], stop), daemon=True).start()
    try:
        handler = HANDLERS.get(job["job_type"])
        if not handler:
            raise Permanent(f"unknown job type {job['job_type']}")
        result = handler(ctx)
        finish(job, status="succeeded", progress=1, current_stage="done", result=result or {}, error=None)
        log.info("job %s succeeded", job["id"])
    except Cancelled:
        finish(job, status="cancelled", current_stage="cancelled")
        log.info("job %s cancelled", job["id"])
    except Exception as e:  # noqa: BLE001 — every failure is recorded on the job row
        msg = f"{type(e).__name__}: {e}"
        log.error("job %s failed: %s\n%s", job["id"], msg, traceback.format_exc())
        if isinstance(e, Permanent) or job["attempts"] >= job["max_attempts"]:
            finish(job, status="failed", error=msg[:2000])
        else:
            delay = 30 * 2 ** (job["attempts"] - 1)
            finish(
                job,
                status="queued",
                error=msg[:2000],
                run_after=(datetime.now(UTC) + timedelta(seconds=delay)).isoformat(),
            )
    finally:
        stop.set()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db = service_client()
    log.info("worker %s started", WORKER_ID)
    last_requeue = 0.0
    while True:
        try:
            if time.monotonic() - last_requeue > 60:
                n = db.rpc("requeue_stale_jobs", {"stale": "3 minutes"}).execute().data
                if n:
                    log.warning("requeued %s stale job(s)", n)
                last_requeue = time.monotonic()
            job = db.rpc("claim_next_job", {"worker": WORKER_ID, "job_types": list(HANDLERS)}).execute().data
            if job and job.get("id"):
                log.info("claimed %s %s (attempt %s)", job["job_type"], job["id"], job["attempts"])
                run_one(job)
            else:
                time.sleep(POLL_S)
        except KeyboardInterrupt:
            return
        except Exception as e:  # noqa: BLE001 — network blips must not kill the worker
            log.warning("poll failed: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
