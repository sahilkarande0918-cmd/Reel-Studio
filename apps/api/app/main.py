import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, campaigns, collections, editor, edits, health, publishing, recordings, renders, social, topics, voices
from app.core import heartbeat
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    task = (
        asyncio.create_task(heartbeat.run_forever()) if s.public_api_url and s.supabase_configured else None
    )
    yield
    if task:
        task.cancel()


app = FastAPI(title="Reel Studio API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Content-Range",
        "Upload-Offset",
        "X-Tunnel-Skip-AntiPhishing-Page",
    ],
)

app.include_router(health.router)
app.include_router(recordings.router)
app.include_router(renders.router)
app.include_router(topics.router)
app.include_router(social.router)
app.include_router(publishing.router)
app.include_router(editor.router)
app.include_router(assets.router)
app.include_router(edits.router)
app.include_router(voices.router)
app.include_router(collections.router)
app.include_router(campaigns.router)
