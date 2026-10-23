"""voice_preview job: synthesise a short preview with a saved voice profile."""

import soundfile as sf

from app.core.db import service_client
from app.services import voice, voice_profiles as vp
from app.workers.jobs import JobContext, Permanent


def run_voice_preview(ctx: JobContext) -> dict:
    pl = ctx.payload
    vid = pl["voice"].split(":", 1)[1]
    rows = service_client().table("voice_profiles").select("organization_id").eq("id", vid).limit(1).execute().data
    if not rows:
        raise Permanent("voice profile was deleted")
    out_dir = vp.voice_dir(rows[0]["organization_id"], vid) / "previews"
    out_dir.mkdir(exist_ok=True)
    ctx.stage("voice", 0.1, "Generating the preview with your voice")
    wav = voice.synthesize(pl["text"], pl["voice"], out_dir, pl.get("language", "en"))
    return {"path": str(wav), "seconds": round(sf.info(str(wav)).duration, 2)}
