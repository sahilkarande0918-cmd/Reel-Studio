import shutil

from fastapi import APIRouter, Depends

from app.core.auth import User, current_user
from app.core.config import Settings, get_settings
from app.services import i2v

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    """Public liveness + capability report. Contains no user data or secrets."""
    return {
        "status": "ok",
        "service": "reel-studio-api",
        "capabilities": {
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "ffprobe": shutil.which("ffprobe") is not None,
            "supabase": settings.supabase_configured,
            "photo_animation": i2v.available(),  # local AI image-to-video installed (Mode B "animate photos")
        },
    }


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email}
