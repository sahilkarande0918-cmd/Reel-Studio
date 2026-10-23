> **Reel Studio 2.0 (2026-10-24) — read first:** `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full approved spec + status map) and `docs/REEL_STUDIO_2_HANDOFF.md` (technical handoff). They supersede the 1.0 status below, which is kept as history. Work folder `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`, repo https://github.com/sahilkarande0918-cmd/Reel-Studio. 2.0 so far: migration ✅, reference analysis ✅, Mode B engine core (beats, 24 effects, 21 transitions, beat planner, reference style transfer, audio, QA) ✅ via scripts; Mode B UI/API, motion templates, AI Director, Blender, voice, 100 captions, collections, campaigns, localisation, results tracking ⬜.

## 2.0 notes
The 2.0 folder has its own copies of `apps/api/.env` and `apps/web/.env.local` (ignored). Variable names are unchanged (list in `REEL_STUDIO_2_HANDOFF.md` §12). New Python dependency: librosa 0.11 (`requirements/vision.txt`). Fresh clones need `npx next typegen` before `tsc`.

# Environment

Never commit real values. `.env`, `.env.*` (except `.env.example`) are git-ignored.

## Frontend (`apps/web/.env.local` locally; Vercel → Settings → Environment Variables in production)
| Variable | Public? | Value / where |
|----------|---------|---------------|
| `NEXT_PUBLIC_SUPABASE_URL` | public | local: `http://127.0.0.1:54321` · production: `https://adjwycjsxtxvjockxtan.supabase.co` (set in Vercel) |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | public | local: printed by `supabase status` · production: Reel-Studio → Project Settings → API Keys → publishable (set in Vercel) |
| `NEXT_PUBLIC_SITE_URL` | public | `http://localhost:3000` · production `https://reel-studio-taupe.vercel.app` (set in Vercel) |
| `NEXT_PUBLIC_API_URL` | public | optional override; normally the backend URL is discovered from `backend_endpoints` |

Current local `apps/web/.env.local` points at the **local** Supabase stack.

## Backend (`apps/api/.env`, processing machine only)
| Variable | Secret? | Notes |
|----------|---------|-------|
| `SUPABASE_URL` | no | local `http://127.0.0.1:54321` (current); production `https://adjwycjsxtxvjockxtan.supabase.co` after migrations |
| `SUPABASE_SECRET_KEY` | **SECRET** | local stack's default key now; production secret only ever typed into this file |
| `TOKEN_ENCRYPTION_KEY` | **SECRET** | needed from Phase 07 (OAuth tokens) |
| `ALLOWED_ORIGINS` | no | `http://localhost:3000,https://reel-studio-taupe.vercel.app` (set 2026-10-16) |
| `DATA_DIR` | no | `C:/Users/Sahil/AppData/Local/reel-studio/data` |
| `PUBLIC_API_URL` | no | `http://127.0.0.1:8000` locally; overwritten by the tunnel launcher |
| `WHISPER_MODEL` | no | `C:/Users/Sahil/AppData/Local/reel-studio/data/models/hinglish-apex-ct2` |
| `WHISPER_LANGUAGE` | no | `hi` (Hinglish model) |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | no | defaults `cuda` / `float16` |
| `OLLAMA_URL` / `OLLAMA_MODEL` | no | defaults `http://localhost:11434` / `qwen2.5vl:7b` |

## Supabase projects
- **Only** `adjwycjsxtxvjockxtan` (Reel-Studio, friend's organization). Never touch the owner's personal org/projects that the current CLI login shows.
- Local development uses the Docker stack: `pnpm exec supabase start -x vector,logflare,imgproxy,edge-runtime` (API 54321, DB 54322, Studio 54323, Mailpit 54324).

## Machine (verified 2026-10-16)
- Windows 11, NVIDIA RTX 5050 Laptop 8 GB (Blackwell sm_120, driver 616.64), CUDA 12.8 toolkit.
- Node 24.13.1, pnpm 12.5.1, Python 3.11.9 (backend venv), FFmpeg/FFprobe 8.1.2, Docker 29.6.2.
- Ollama with `qwen2.5vl:7b`. `cloudflared` 2026.10.1 (winget). Tailscale 1.104.1 installed, service running, logged out (cannot log in on this network, D-024). **Microsoft Dev Tunnels CLI 1.0.2115** (winget; `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Microsoft.devtunnel_*\devtunnel.exe`), logged in with GitHub `sahilkarande0918-cmd`, tunnel `reel-studio.inc1`.
- Python venv `C:\Users\Sahil\AppData\Local\reel-studio\venv`: fastapi, uvicorn, supabase, faster-whisper 1.2.1, ctranslate2 4.8.3, nvidia-cublas/cudnn cu12 wheels, opencv-python-headless 4.14, scenedetect 0.6.7, rapidocr-onnxruntime 1.4.4, kokoro-onnx 0.6.1, soundfile, pytest, ruff.
- Converter venv `C:\Users\Sahil\AppData\Local\reel-studio\convert-venv` (torch CPU, transformers, ctranslate2) — only for re-converting the ASR model.
- Models: `data/models/hinglish-apex-ct2` (1.6 GB fp16), `data/models/models--Systran--faster-whisper-base`; HF cache holds the original Oriserve weights; Kokoro voices downloaded by Hyperframes.
- Hyperframes CLI used via `npx --yes hyperframes@0.8.164` (set `HYPERFRAMES_PYTHON` to the venv python for `tts`; set `HYPERFRAMES_TELEMETRY=0 DO_NOT_TRACK=1`).
- Windows OneCore voices present: Microsoft Ravi / Heera (en-IN), David, Mark, Zira.
- Network: Fortinet firewall with SSL inspection. Outbound TCP/UDP 7844 blocked (Cloudflare tunnel fails); port 22 blocked; 443 open, but `controlplane.tailscale.com`, Tailscale DERP and `*.devtunnels.ms` are TLS-intercepted with an untrusted CA. The Dev Tunnels relay (`*.rel.tunnels.api.visualstudio.com`) works.
- Python venv also has `jsonschema` 4.26 (Phase 04). Node workspace package `packages/timeline-schema` (zod 4, vitest 5).
