"""Engine switch for the dashboard: GET /engine (state) and POST /engine {"processing": bool} (owners/admins).

The engine serves every organisation on this machine, so only an owner or admin of an organisation (or, when
ENGINE_ADMIN_EMAILS is set, only those e-mail addresses) may pause or resume it. Pausing stops the worker; the API stays
up so the switch keeps working. A fully stopped engine is started from the desktop button (engine-switch.ps1).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import engine_state
from app.core.auth import User, current_user
from app.core.config import get_settings
from app.core.db import service_client

router = APIRouter()


def can_switch(user: User) -> bool:
    allow = {e.strip().lower() for e in (get_settings().engine_admin_emails or "").split(",") if e.strip()}
    if allow:
        return (user.email or "").lower() in allow
    rows = service_client().table("organization_members").select("role").eq("user_id", user.id) \
        .in_("role", ["owner", "admin"]).limit(1).execute().data
    return bool(rows)


class Switch(BaseModel):
    processing: bool


@router.get("/engine")
def state(user: User = Depends(current_user)) -> dict:
    return {**engine_state.info(), "can_switch": can_switch(user)}


@router.post("/engine")
def switch(body: Switch, user: User = Depends(current_user)) -> dict:
    if not can_switch(user):
        raise HTTPException(403, "Only an organisation owner or admin can turn the engine on or off")
    return {**engine_state.set_processing(body.processing, by=user.email or user.id), "can_switch": True}
