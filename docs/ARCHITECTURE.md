> **Reel Studio 2.0 (2026-10-24) — read first:** `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full approved spec + status map) and `docs/REEL_STUDIO_2_HANDOFF.md` (technical handoff). They supersede the 1.0 status below, which is kept as history. Work folder `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`, repo https://github.com/sahilkarande0918-cmd/Reel-Studio. 2.0 so far: migration ✅, reference analysis ✅, Mode B engine core (beats, 24 effects, 21 transitions, beat planner, reference style transfer, audio, QA) ✅ via scripts; Mode B UI/API, motion templates, AI Director, Blender, voice, 100 captions, collections, campaigns, localisation, results tracking ⬜.

## 2.0 Mode B engine (current)
clips/analysis.py + music/beats.py + reference/analyzer.py → editing/planner.py (pacing.py, style_transfer.py) → editing/render.py (base.py FFmpeg segments + effects.py + xfade; audio.py separate mix) → mux → editing/qa.py. Planned: Hyperframes template layer, AI Director, renderer router (FFmpeg/Hyperframes/shader/headless Blender). Details: `REEL_STUDIO_2_HANDOFF.md` §2–§9.

# Architecture

## Overview

```
 Browser (judge / institute user)
   │  HTTPS
   ▼
 Vercel (Hobby) — apps/web  Next.js App Router
   │  • UI, auth session (Supabase SSR cookies)
   │  • reads/writes app data directly via Supabase (RLS-enforced)
   │  • never touches large media or GPU work
   │
   ├──────────────► Supabase (Free)
   │                 • Auth (email/password, optional OAuth)
   │                 • Postgres (all metadata, RLS by organization)
   │                 • Realtime (job progress)
   │                 • Storage (logos, thumbnails, selected final MP4s, signed URLs)
   │
   └── HTTPS tunnel ─► Local machine   (Microsoft Dev Tunnels, D-024) (owner's laptop, RTX 5050 8 GB)
                        apps/api  FastAPI  (JWT-verified, CORS-restricted)
                          • chunked upload → data/ (local disk)
                          • enqueue jobs (rows in Supabase `jobs`)
                        worker  (same codebase, separate process)
                          • claims jobs with SKIP LOCKED via RPC
                          • FFmpeg / faster-whisper / OpenCV / OCR / Ollama
                          • Hyperframes CLI render (Node 24 + headless Chrome)
                          • scheduler loop for publish jobs
```

The backend registers its current public tunnel URL in Supabase (`backend_endpoints`) on startup and
heartbeats it. The frontend reads it, so a changing quick-tunnel URL does not require a redeploy, and
the UI shows a truthful "processing backend offline" state when the heartbeat is stale.

## Monorepo

| Path | Purpose |
|------|---------|
| `apps/web` | Next.js frontend (all 18 product pages) |
| `apps/api` | FastAPI app + worker (`app/workers`) + services |
| `packages/timeline-schema` | **Canonical timeline** — Zod schema, TS types, generated JSON Schema, migrations |
| `apps/api/app/services/rendering` | Timeline → Hyperframes HTML compiler (D-023: Python, one compiler for render and preview) |
| `supabase/migrations` | Version-controlled SQL + RLS |
| `data/` (git-ignored) | Raw recordings, intermediates, renders, caches |

`packages/shared-types` and `packages/ui` from the master-prompt sketch are folded into
`timeline-schema` and `apps/web/components/ui` until a second consumer exists (see DECISIONS D-007).

## Data flow — Mode A (Recording → Reels)

Steps 1–10 and 12 are **implemented**; 11 (editor) is Phase 06.

1. **Upload** ✅ `POST /recordings` → `PUT /recordings/{id}/chunk?offset=N` (16 MB, offset-checked resume) → `POST /recordings/{id}/complete`; file at `DATA_DIR/orgs/<org>/recordings/<id>/source.<ext>` (`app/api/recordings.py`, `app/core/storage.py`).
2. **Validate** ✅ ffprobe on complete (video+audio, 5 s–4 h, ≤4 GB); invalid files deleted; metadata on `source_recordings`; `transcribe` job inserted (`app/services/media.py`).
3. **Audio** ✅ FFmpeg → `audio16k.wav` (16 kHz mono, highpass + loudnorm), cached.
4. **Transcribe** ✅ faster-whisper with the Hinglish-Apex CT2 model, word timestamps, VAD, glossary hotwords (`services/transcription/whisper.py`). WhisperX deferred (D-016).
5. **Vocabulary correction** ✅ built-in + org glossary spoken forms (`glossary.correct`), repetition-loop cleanup (`cleanup.py`); raw text always kept. Then the `analyze` job applies screen-OCR evidence (`glossary.correct_with_screen`).
6. **Audio features** ✅ RMS dBFS per 0.5 s, pauses, speech rate (`services/highlights/audio_features.py`). Pitch not yet.
7. **Screen analysis** ✅ 2 fps grey change maps → change fraction, active box, text density, hard cuts (`screen_analysis/activity.py`); RapidOCR every 6 s + after cuts, ≤90 frames (`screen_analysis/ocr.py`).
8. **Highlights** ✅ sentences → 30–60 s windows on sentence ends → features + labelled heuristic score → strict speaker-relative pause pool → local LLM judge (veto on agreement) → ranked `highlight_candidates` with reasons (`highlights/candidates.py`, `highlights/llm.py`, `workers/analyze.py`).
9. **Reframe** ✅ per highlight: smoothed crop keyframes (crop / panel layouts, cuts, hysteresis) stored in `highlight_candidates.crop_keyframes` (`screen_analysis/reframe.py`). Studio preview plays the source through these keyframes (`components/studio/highlights.tsx`, `cropAt`).
10. **Timeline** ✅ canonical timeline from a selected highlight: video item + crop keyframes + word caption track (code terms flagged) + brand snapshot, validated against `packages/timeline-schema` (`services/rendering/timeline.py`).
11. **Edit** ⬜ editor on the canonical timeline; preview with `@hyperframes/player`.
12. **Render** ✅ `render` job: compile → `hyperframes lint` → `hyperframes render` (live `@hf-progress`) → ffprobe verify → thumbnail → `render_jobs` row; signed playback/download (`services/rendering/compose.py`, `workers/render.py`, `api/renders.py`).

### Worker jobs (implemented)
`transcribe` (extract_audio → transcribe → correct_terms → save; then inserts `analyze`) and `analyze` (screen_activity → ocr → screen_terms → highlights → llm_judge → reframe). Claimed with `claim_next_job` (SKIP LOCKED), 30 s lock heartbeat, stale-lock requeue after 3 min, retries with backoff, `Permanent` errors fail fast, cancellation via `cancel_job` RPC checked between stages. Caches per recording: `audio16k.wav`, `activity.json`, `ocr.json`.

### Tables (5 migrations)
`profiles`, `organizations`, `organization_members`, `projects`, `jobs`, `job_events`, `backend_endpoints`, `audit_events` · `source_recordings`, `transcripts`, `transcript_segments`, `transcript_words`, `technical_glossaries` · `highlight_candidates` · `render_jobs`. RLS on all; explicit grants only (D-025); membership helpers in `private` schema; column-level update grants for user edits.

## Data flow — Mode B (Topic → Video)

topic + options → Ollama outline/script/storyboard (structured JSON) → code examples validated
(JSON/XML/etc parsed; executable snippets only in sandboxed validators) → Kokoro TTS per scene
(`hyperframes tts`) → word timings (faster-whisper on the TTS audio, aligned to known script text) →
canonical timeline (code-typing blocks, captions, brand) → same render path as Mode A.

## Canonical timeline (one format everywhere)

Defined once in `packages/timeline-schema` (Zod). Used by: AI generation (Python emits JSON validated
against the generated JSON Schema), the editor (Zustand store), preview (compiled composition),
export (same compiler), persistence (`timelines.document` jsonb + `timeline_revisions`).
Every document carries `schemaVersion`; `migrate()` upgrades old documents.

Core shape (abridged): `Composition { id, schemaVersion, fps, width, height, duration, tracks[], assets{}, captions, brand (snapshot), renderSettings }`,
`Track { id, kind: video|audio|text|caption|overlay, items[] }`,
`Item { id, assetId?, start, duration, sourceStart?, sourceEnd?, transform{x,y,scale,crop}, cropKeyframes?, effects[], keyframes[], audio{gain,fadeIn,fadeOut}, ai? }`.

## Jobs

`jobs` table (Section 18 contract: job_id, organization_id, project_id, job_type, status, progress,
current_stage, error, created_at, updated_at, + attempts, locked_at, locked_by, payload, result).
Worker claims via `claim_next_job()` (FOR UPDATE SKIP LOCKED), heartbeats, and on restart re-queues
jobs whose lock expired — it never marks unfinished work as complete. Stages are idempotent and cache
their outputs under `data/cache/<hash>` so a boundary edit re-runs only compile + render.
GPU concurrency = 1 heavy model at a time (transcribe / LLM / render are serialized).

## Rendering pipeline

`timeline.json` → `services/rendering/compose.py` → `DATA_DIR/orgs/<org>/renders/<id>/` with `index.html`,
`timeline.json`, bundled OFL fonts and a hard link to the source → `npx hyperframes@0.8.164 lint --json`
→ `render --quality <draft|looks|delivery> --video-frame-format png` → `ffprobe` (1080×1920, duration ±0.1 s,
H.264 + audio) → thumbnail via FFmpeg → `render_jobs` ready. Camera: `#cam` (source video, GSAP x/y/scale)
inside `#win` (visible window; full frame for `crop`, a band above the captions for `panel`); linear
between keyframes, jump on `cut` or layout change, identical to the studio preview's `cropAt`. Captions:
pages of ≤2 lines × ≤26 chars broken at pauses/sentence ends, active word on an accent pill. Render cache
key = SHA-256 of the timeline minus its id. Hyperframes telemetry is disabled.

## Publishing & analytics

`publish_jobs` (scheduled UTC + tz, state machine scheduled→processing→publishing→published|failed|cancelled,
attempts, idempotency key, platform post id). Worker scheduler claims due jobs with locking.
Instagram: official Graph API (Reels container → poll → publish) using a short-lived signed Storage URL.
YouTube: Data API v3 resumable upload; Analytics API for metrics. Tokens AES-GCM-encrypted server-side.
Metrics → `platform_metrics` snapshots → normalized → feature comparison → `feedback_recommendations`
(ranking weight deltas with explanations, minimum-data thresholds).

## Security boundaries

- Browser ↔ Supabase: publishable key + user JWT; RLS by `organization_members`.
- Browser ↔ local API: user JWT verified against Supabase JWKS; org membership checked server-side.
- Local API ↔ Supabase: secret key, backend only.
- FFmpeg/Hyperframes invoked with argument lists; file paths generated server-side, never from user strings.

## Deployment

See `docs/DEPLOYMENT.md`. Vercel builds `apps/web` only. The local API + worker run on the owner's
machine and are exposed through a free HTTPS tunnel.

## Editor, presets and feedback (final run, 2026-10-17)
```
render_jobs.timeline ──copy──► timeline_drafts (RLS autosave)
        │                              │ edits: packages/timeline-schema/src/edit.ts (pure, tested)
        │                              ▼
        │          POST /renders/{id}/preview → compose.compile_html + preview runtime → iframe srcdoc
        │                                         (<base> = signed /renders/{id}/p/{exp}/{sig}/ folder)
        └──────────► POST /renders/{id}/edit → new render_jobs row (parent_render_id) → render worker
                                               → Hyperframes → apply_fades (ffmpeg) → ffprobe verify
stylePreset (focus|energy|story|signature) → compose.STYLES (transitions, caption CSS, push-in, lower third)
Instagram insights worker → platform_metrics.metrics + .media (per-reel insights)
feedback.collect/learn (≥3 published reels with reach) → performance_feedback.ideal_duration_s
        → analyze worker extras["ideal_s"] → candidates.score_window length term + reason text
```
