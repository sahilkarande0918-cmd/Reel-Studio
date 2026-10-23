"""Local media layout. Paths are built only from server-generated UUIDs, never from user input."""

import uuid
from pathlib import Path

from app.core.config import get_settings


def recording_dir(org_id: str, recording_id: str) -> Path:
    # uuid.UUID() rejects anything that is not a UUID, so no traversal is possible.
    d = (
        get_settings().data_dir
        / "orgs"
        / str(uuid.UUID(org_id))
        / "recordings"
        / str(uuid.UUID(recording_id))
    )
    d.mkdir(parents=True, exist_ok=True)
    return d


def source_path(rec: dict) -> Path:
    return recording_dir(rec["organization_id"], rec["id"]) / f"source{Path(rec['filename']).suffix.lower()}"


def render_dir(org_id: str, render_id: str) -> Path:
    d = get_settings().data_dir / "orgs" / str(uuid.UUID(org_id)) / "renders" / str(uuid.UUID(render_id))
    d.mkdir(parents=True, exist_ok=True)
    return d


def asset_dir(org_id: str, asset_id: str) -> Path:
    d = get_settings().data_dir / "orgs" / str(uuid.UUID(org_id)) / "assets" / str(uuid.UUID(asset_id))
    d.mkdir(parents=True, exist_ok=True)
    return d


def asset_path(asset: dict) -> Path:
    """Mode B upload on disk; the name is fixed, only the (validated) extension comes from the upload."""
    return asset_dir(asset["organization_id"], asset["id"]) / f"source{Path(asset['filename']).suffix.lower()}"
