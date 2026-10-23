"""Mode B end to end through the real API + worker (local stack): sign in, create a Prompt → Edit project, upload clips
(resumable chunks), optional music/reference, request an edit, wait for the job, download the MP4.

    python tests/e2e_mode_b.py OUT.mp4 --prompt "..." [--project ID] [--music F] [--reference F] [--style auto] CLIP ...

Same HTTP calls the web app makes (components/studio/media-bin.tsx, edit-studio.tsx). Manual tool, not a unit test.
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

API = "http://127.0.0.1:8001"
SB = "http://127.0.0.1:54321"
PASSWORD = "local-test-Pass-2026"
EMAIL = "upload-owner@test.local"


def pk() -> str:
    env = Path(__file__).parents[2] / "web" / ".env.development.local"
    return next(x.split("=", 1)[1].strip() for x in env.read_text().splitlines() if x.startswith("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"))


def token() -> str:
    body = {"email": EMAIL, "password": PASSWORD}
    r = httpx.post(f"{SB}/auth/v1/token?grant_type=password", headers={"apikey": pk()}, json=body)
    if r.status_code != 200:
        httpx.post(f"{SB}/auth/v1/signup", headers={"apikey": pk()}, json=body)
        r = httpx.post(f"{SB}/auth/v1/token?grant_type=password", headers={"apikey": pk()}, json=body)
    return r.json()["access_token"]


def rest(t: str, method: str, path: str, **kw):
    r = httpx.request(method, f"{SB}/rest/v1/{path}", headers={"apikey": pk(), "Authorization": f"Bearer {t}", "Prefer": "return=representation"}, **kw)
    r.raise_for_status()
    return r.json()


def upload(h: dict, project: str, kind: str, path: Path) -> dict:
    r = httpx.post(f"{API}/assets", headers=h, json={"project_id": project, "kind": kind, "filename": path.name, "size_bytes": path.stat().st_size})
    r.raise_for_status()
    aid, chunk = r.json()["id"], r.json()["chunk_size"]
    data, sent = path.read_bytes(), 0
    while sent < len(data):
        r = httpx.put(f"{API}/assets/{aid}/chunk?offset={sent}", headers={**h, "Content-Type": "application/octet-stream"}, content=data[sent:sent + chunk], timeout=120)
        r.raise_for_status()
        sent = r.json()["received_bytes"]
    r = httpx.post(f"{API}/assets/{aid}/complete", headers=h, timeout=300)
    r.raise_for_status()
    return r.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--prompt", default="Edit it professionally")
    ap.add_argument("--project")
    ap.add_argument("--music")
    ap.add_argument("--reference")
    ap.add_argument("--settings", default="{}", help="extra JSON settings (style, duration_s, captions, voice...)")
    a = ap.parse_intermixed_args()
    t = token()
    h = {"Authorization": f"Bearer {t}"}
    project = a.project
    if not project:
        orgs = rest(t, "GET", "organization_members?select=organization_id")
        org = orgs[0]["organization_id"] if orgs else rest(t, "POST", "rpc/create_organization", json={"org_name": "Mode B test", "org_slug": f"mb-{uuid.uuid4().hex[:8]}"})["id"]
        project = rest(t, "POST", "projects", json={"organization_id": org, "name": f"Mode B e2e {time.strftime('%H:%M')}", "mode": "edit", "created_by": jwt_sub(t)})[0]["id"]
        t0 = time.time()
        for c in a.clips:
            print("upload", c, upload(h, project, "image" if Path(c).suffix.lower() in (".jpg", ".png", ".jpeg", ".webp") else "clip", Path(c))["duplicate"], flush=True)
        if a.music:
            upload(h, project, "audio", Path(a.music))
        if a.reference:
            upload(h, project, "reference", Path(a.reference))
        print(f"uploaded in {time.time() - t0:.1f}s; project {project}", flush=True)
    body = {"prompt": a.prompt, **json.loads(a.settings)}
    r = httpx.post(f"{API}/projects/{project}/edit", headers=h, json=body, timeout=60)
    print(r.status_code, r.text, flush=True)
    r.raise_for_status()
    gid = r.json()["generation_id"]
    t0, last = time.time(), None
    while True:
        g = rest(t, "GET", f"edit_generations?id=eq.{gid}&select=status,error,render_id,director,qa,job:jobs(progress,current_stage,status,error)")[0]
        stage = (g["job"] or {}).get("current_stage")
        if stage != last:
            print(f"{time.time() - t0:6.1f}s {g['status']} {stage} {(g['job'] or {}).get('progress')}", flush=True)
            last = stage
        if g["status"] in ("ready", "failed", "cancelled"):
            break
        time.sleep(3)
    if g["status"] != "ready":
        print("FAILED", g["error"] or g["job"]["error"])
        sys.exit(1)
    urls = httpx.get(f"{API}/renders/{g['render_id']}/urls", headers=h).json()
    Path(a.out).write_bytes(httpx.get(API + urls["video"], timeout=300).content)
    d = g["director"]
    print(json.dumps({"engine": d["provenance"], "style": d["style"], "profile": d["profile"], "pacing": d["pacing"], "look": d["look"],
                      "treatment": d["treatment"], "text": d["on_screen_text"], "graphics": d.get("graphics"), "reasons": d["reasons"],
                      "qa_pass": g["qa"]["pass"], "loudness": g["qa"]["loudness"], "project": project, "render_id": g["render_id"],
                      "seconds": round(time.time() - t0, 1)}, indent=1))


def jwt_sub(t: str) -> str:
    import base64

    part = t.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))["sub"]


if __name__ == "__main__":
    main()
