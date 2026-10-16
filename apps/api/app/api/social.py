"""Organization-bound OAuth. Callback code exchange still requires a Supabase session."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.access import get_owned, require_role
from app.core.auth import User, current_user
from app.core.config import get_settings
from app.core.db import service_client
from app.services import feedback
from app.services.publishing import instagram, tokens

router = APIRouter()
ACCOUNT_COLUMNS = "id,organization_id,platform,platform_user_id,username,status,scopes,expires_at"


class ConnectBody(BaseModel):
    organization_id: UUID


class CallbackBody(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=32, max_length=256)


def configuration() -> dict:
    s = get_settings()
    required = {
        "INSTAGRAM_CLIENT_ID": s.instagram_client_id,
        "INSTAGRAM_CLIENT_SECRET": s.instagram_client_secret.get_secret_value(),
        "INSTAGRAM_REDIRECT_URI": s.instagram_redirect_uri,
        "TOKEN_ENCRYPTION_KEY": s.token_encryption_key,
    }
    missing = [key for key, value in required.items() if not value]
    return {
        "instagram": {
            "configured": not missing,
            "missing": missing,
            "redirect_uri": s.instagram_redirect_uri,
        },
        "youtube": {
            "configured": False,
            "missing": ["YouTube integration setup pending"],
            "redirect_uri": s.google_redirect_uri,
        },
    }


@router.get("/social/config")
def config(user: User = Depends(current_user)) -> dict:
    return configuration()


@router.get("/social/accounts")
def accounts(organization_id: UUID, user: User = Depends(current_user)) -> list:
    require_role(str(organization_id), user)
    return (
        service_client()
        .table("social_accounts")
        .select(ACCOUNT_COLUMNS)
        .eq("organization_id", str(organization_id))
        .execute()
        .data
    )


@router.post("/social/instagram/connect")
def connect(body: ConnectBody, user: User = Depends(current_user)) -> dict:
    require_role(str(body.organization_id), user, write=True)
    s = get_settings()
    if not configuration()["instagram"]["configured"]:
        raise HTTPException(503, "Instagram connection is not configured on the processing backend")
    if not s.instagram_redirect_uri.startswith("https://"):
        raise HTTPException(503, "Instagram callback must be HTTPS")
    # Check encryption before asking the user to authorize.
    tokens.encrypt({}, s.token_encryption_key, "configuration-check")
    state = secrets.token_urlsafe(48)
    db = service_client()
    db.table("oauth_states").delete().lt("expires_at", datetime.now(UTC).isoformat()).execute()
    db.table("oauth_states").insert(
        {
            "state_hash": hashlib.sha256(state.encode()).hexdigest(),
            "organization_id": str(body.organization_id),
            "user_id": user.id,
            "platform": "instagram",
            "redirect_uri": s.instagram_redirect_uri,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
        }
    ).execute()
    return {
        "authorization_url": instagram.authorization_url(
            s.instagram_client_id, s.instagram_redirect_uri, state
        )
    }


@router.post("/social/instagram/callback")
def callback(body: CallbackBody, user: User = Depends(current_user)) -> dict:
    s, db = get_settings(), service_client()
    states = (
        db.rpc(
            "consume_oauth_state",
            {
                "p_hash": hashlib.sha256(body.state.encode()).hexdigest(),
                "p_user": user.id,
                "p_platform": "instagram",
            },
        )
        .execute()
        .data
    )
    if not states or states[0]["redirect_uri"] != s.instagram_redirect_uri:
        raise HTTPException(400, "Authorization expired or already used. Connect Instagram again.")
    org = states[0]["organization_id"]
    require_role(org, user, write=True)
    try:
        credentials = instagram.exchange(body.code, s)
        adapter = instagram.Instagram(credentials["access_token"], s.instagram_api_version)
        profile = adapter.profile()
        uid = str(profile.get("user_id") or profile.get("id") or credentials["user_id"])
        if not uid or not profile.get("username"):
            raise RuntimeError("Instagram did not return the authorized account identity")
        try:
            scopes = adapter.permissions(uid)
        except RuntimeError:
            scopes = credentials.get("permissions", [])
        old = (
            db.table("social_accounts")
            .select("id")
            .eq("organization_id", org)
            .eq("platform", "instagram")
            .eq("platform_user_id", uid)
            .execute()
            .data
        )
        aid = old[0]["id"] if old else str(uuid4())
        expires = datetime.now(UTC) + timedelta(seconds=int(credentials.get("expires_in", 3600)))
        account = {
            "id": aid,
            "organization_id": org,
            "platform": "instagram",
            "platform_user_id": uid,
            "username": profile["username"],
            "status": "disconnected",
            "scopes": scopes,
            "expires_at": expires.isoformat(),
            "created_by": user.id,
        }
        db.table("social_accounts").upsert(account).execute()
        db.table("social_credentials").upsert(
            {"account_id": aid, "ciphertext": tokens.encrypt(credentials, s.token_encryption_key, aid)}
        ).execute()
        db.table("social_accounts").update({"status": "connected"}).eq("id", aid).execute()
        account["status"] = "connected"
        return {"account": {key: value for key, value in account.items() if key != "created_by"}}
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from None


@router.post("/social/accounts/{account_id}/disconnect")
def disconnect(account_id: UUID, user: User = Depends(current_user)) -> dict:
    """Forget the stored token. Scheduled posts for this account fail safely until it is reconnected."""
    account = get_owned("social_accounts", str(account_id), user, write=True)
    db = service_client()
    db.table("social_credentials").delete().eq("account_id", account["id"]).execute()
    db.table("social_accounts").update({"status": "disconnected"}).eq("id", account["id"]).execute()
    return {"id": account["id"], "status": "disconnected"}


@router.get("/social/accounts/{account_id}/insights")
def insights(account_id: UUID, user: User = Depends(current_user)) -> dict:
    get_owned("social_accounts", str(account_id), user)
    rows = (
        service_client()
        .table("platform_metrics")
        .select("metrics,unavailable,media,updated_at")
        .eq("account_id", str(account_id))
        .execute()
        .data
    )
    return (
        rows[0] if rows else {"metrics": [], "media": [], "unavailable": ["No insights fetched yet"], "updated_at": None}
    )


@router.post("/social/accounts/{account_id}/insights", status_code=202)
def refresh_insights(account_id: UUID, user: User = Depends(current_user)) -> dict:
    account = get_owned("social_accounts", str(account_id), user, write=True)
    row = (
        service_client()
        .table("jobs")
        .insert(
            {
                "organization_id": account["organization_id"],
                "created_by": user.id,
                "job_type": "insights",
                "payload": {"account_id": str(account_id)},
                "current_stage": "queued",
            }
        )
        .execute()
        .data[0]
    )
    return {"job_id": row["id"]}


@router.get("/feedback")
def get_feedback(organization_id: UUID, user: User = Depends(current_user)) -> dict:
    """Per-reel performance rows (live) and the last stored learning for this workspace."""
    require_role(str(organization_id), user)
    rows = feedback.collect(str(organization_id))
    stored = (service_client().table("performance_feedback").select("ideal_duration_s,summary,updated_at")
              .eq("organization_id", str(organization_id)).execute().data)
    return {"rows": rows, "stored": stored[0] if stored else None, "min_posts": feedback.MIN_POSTS}


@router.post("/feedback")
def run_feedback(body: ConnectBody, user: User = Depends(current_user)) -> dict:
    """Learn from published reels; with too little data nothing is stored and the reason is returned."""
    org = str(body.organization_id)
    require_role(org, user, write=True)
    summary = feedback.learn(feedback.collect(org))
    if not summary["enough"]:
        return {"summary": summary, "stored": False}
    summary["recommendations"] = feedback.explain(summary)
    service_client().table("performance_feedback").upsert({
        "organization_id": org, "ideal_duration_s": summary["ideal_duration_s"], "summary": summary,
        "updated_at": datetime.now(UTC).isoformat(),
    }).execute()
    return {"summary": summary, "stored": True}
