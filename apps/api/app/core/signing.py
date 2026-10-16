"""Short-lived HMAC-signed URLs for media the browser loads without an Authorization header
(<video src>, download links). The signature binds the resource kind, id and expiry."""

import hashlib
import hmac
import secrets
import time

from app.core.config import get_settings


def _shared_key() -> bytes:
    settings = get_settings()
    secret = settings.token_encryption_key or settings.supabase_secret_key
    # API and worker must verify each other's URLs. Domain separation keeps this key
    # distinct from OAuth encryption and database authentication keys.
    return (
        hmac.new(secret.encode(), b"reel-studio:media-signing:v1", hashlib.sha256).digest()
        if secret else secrets.token_bytes(32)
    )


_KEY = _shared_key()
TTL_S = 6 * 3600


def sign(kind: str, resource_id: str, exp: int) -> str:
    return hmac.new(_KEY, f"{kind}:{resource_id}:{exp}".encode(), hashlib.sha256).hexdigest()


def query(kind: str, resource_id: str) -> tuple[str, int]:
    exp = int(time.time()) + TTL_S
    return f"exp={exp}&sig={sign(kind, resource_id, exp)}", exp


def valid(kind: str, resource_id: str, exp: int, sig: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(sig, sign(kind, resource_id, exp))
