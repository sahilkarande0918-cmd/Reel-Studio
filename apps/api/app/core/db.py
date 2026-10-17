from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def service_client() -> Client:
    """Supabase client with the secret key. Backend only; bypasses RLS, so callers must check ownership."""
    s = get_settings()
    if not s.supabase_configured:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SECRET_KEY not configured")
    client = create_client(s.supabase_url, s.supabase_secret_key)
    # PostgREST's default HTTP/2 session raised "Server disconnected" on the first request after a long idle
    # stretch (e.g. the worker's local-LLM stages) and kept failing on retries. HTTP/1.1 keep-alive
    # connections are checked before reuse, so a connection the server closed is simply replaced.
    pg, old = client.postgrest, client.postgrest.session
    pg.session = httpx.Client(
        base_url=old.base_url, headers=old.headers, timeout=old.timeout, follow_redirects=True, http2=False
    )
    old.close()
    return client


def transcript_words(transcript_id: str) -> list[dict]:
    """All words of a transcript in order (PostgREST pages at 1000 rows)."""
    out: list[dict] = []
    for start in range(0, 200_000, 1000):
        page = (
            service_client()
            .table("transcript_words")
            .select("*")
            .eq("transcript_id", transcript_id)
            .order("idx")
            .range(start, start + 999)
            .execute()
            .data
        )
        out += page
        if len(page) < 1000:
            break
    return out
