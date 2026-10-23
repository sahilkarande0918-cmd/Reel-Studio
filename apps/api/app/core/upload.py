"""Shared chunked-upload step: append one chunk at the exact offset the disk says we are at."""

from pathlib import Path

from fastapi import HTTPException, Request

CHUNK_MAX = 8 * 1024 * 1024  # half of Dev Tunnels' 16 MB request-body cap


async def append_chunk(p: Path, offset: int, request: Request, declared: int) -> tuple[int, int]:
    """Returns (bytes before, bytes after). 409 tells a client that lost sync where to resume."""
    have = p.stat().st_size if p.exists() else 0
    if offset != have:
        raise HTTPException(409, detail={"message": "offset mismatch", "received_bytes": have})
    data = await request.body()
    if not data or len(data) > CHUNK_MAX:
        raise HTTPException(413, f"Chunk must be 1..{CHUNK_MAX} bytes")
    if have + len(data) > declared:
        raise HTTPException(413, "Chunk exceeds declared file size")
    with p.open("ab") as f:
        f.write(data)
    return have, have + len(data)
