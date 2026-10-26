from fastapi.testclient import TestClient

from app.core import auth
from app.main import app

client = TestClient(app)


def test_health_is_public_and_reports_capabilities():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["capabilities"]) == {"ffmpeg", "ffprobe", "supabase", "photo_animation"}


def test_me_requires_bearer_token():
    assert client.get("/me").status_code == 401


def test_me_rejects_token_supabase_rejects(monkeypatch):
    def reject(token, settings):
        raise auth.HTTPException(401, "Invalid or expired session")

    monkeypatch.setattr(auth, "_verify_with_supabase", reject)
    r = client.get("/me", headers={"Authorization": "Bearer bad"})
    assert r.status_code == 401


def test_me_returns_verified_user_and_caches(monkeypatch):
    calls = []

    def accept(token, settings):
        calls.append(token)
        return auth.User(id="u1", email="a@b.c", token=token)

    monkeypatch.setattr(auth, "_verify_with_supabase", accept)
    auth._cache.clear()
    for _ in range(2):
        r = client.get("/me", headers={"Authorization": "Bearer good"})
        assert r.json() == {"id": "u1", "email": "a@b.c"}
    assert calls == ["good"]


def test_cors_allows_configured_origin_only():
    ok = client.options(
        "/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options(
        "/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in bad.headers
