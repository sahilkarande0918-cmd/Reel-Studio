> **IDE switch checkpoint (2026-10-17): read [IDE_HANDOFF.md](IDE_HANDOFF.md) first.** Real Instagram publishing verified (@career.with.purpose, media 18111030863186503, https://www.instagram.com/reel/DekyGWcDEAl/); editor, style presets and dark UI done. Next: production E2E in the owner's account (Topic → Generate → Edit → Render → Download).

## Status at IDE switch (2026-10-17)
00–05 ✅ · UI redesign ✅ · style presets ✅ · 06 editor ✅ · 07 Instagram ✅ publish verified (scheduling not yet verified live) ·
08 🟡 insights verified, AI feedback awaiting data · 09 🟡 production E2E + submission materials pending. Detail: `IDE_HANDOFF.md` §4.

> **Latest checkpoint (2026-10-17, after the Codex handoff): read [CHECKPOINT.md](CHECKPOINT.md) first.** Mode B now works end to end (JSON vs XML → 46.8 s 1080×1920 MP4, plays and downloads in the UI); repeated-code prompt fix not yet re-verified on a new video. Instagram Business OAuth still pending; nothing published. YouTube postponed (D-035). HEAD at checkpoint start: `fe984a0`.

> **Owner priorities from 2026-10-17 (Claude resume after the Codex handoff), superseding earlier priority notes:**
> 1. Phase 05: Topic → Video produces a real downloadable ~45 s MP4 (JSON vs XML).
> 2. UI: finish the professional redesign (reference screenshots are for structure only, not colours or theme).
> 3. Phase 06: functional multitrack editor (trim, split, captions, audio, overlays, preview, undo/redo, autosave, re-render).
> 4. Phase 07: Instagram Business connection, Reel publishing, scheduling and queue.
> 5. Phase 08: real Instagram analytics and AI performance feedback.
> 6. Phase 09: end-to-end testing, fixes and submission.
>
> **YouTube is postponed** (no OAuth, API setup, Shorts publishing or analytics) until the owner asks. Billing,
> complex admin features and non-essential optimisation are postponed. ORIGINAL_PS.md and MASTER_PROMPT.md are
> unchanged; this is a delivery-order decision (D-035). Keep moving without approval for routine work; ask only
> for account access, credentials, real publishing or other external actions.

> **Final checkpoint (2026-10-17):** Read [CODEX_TO_CLAUDE_HANDOFF.md](CODEX_TO_CLAUDE_HANDOFF.md) first. It supersedes historical status below. Mode B pipeline/UI implemented but live generation fails on fenced model JSON; full editor and YouTube unfinished. Instagram reaches Reel Studio-IG but awaits the separate Business-account login/consent. Never connect/convert the personal account or publish without explicit approval. Production deployed at 7419b77; two new migrations applied. Final backend: 76 pass, 6 skip, 1 known xfail; DB: 52 pass; final frontend build passes. Owner requested checkpoint only, no more features.
# Phases

**Current phase:** **Phase 04 — captions, branding, Hyperframes MP4 rendering** (first task verified: selected highlight → captioned 1080×1920 MP4). Phases 02–03 verified on synthetic fixtures only. Phase 01 production: tunnel ✅ (Dev Tunnels); remote migrations still pending an owner `db push`.

Legend: ✅ verified · 🟡 in progress · ⬜ not started · ⛔ blocked (reason)

| Phase | Title | Status |
|-------|-------|--------|
| 00 | Repository, contributors, foundation | ✅ |
| 01 | Frontend, auth, database, deployment | 🟡 local ✅ · production E2E ✅ · second-account RLS ⬜ |
| 02 | Recording ingestion & transcription | 🟡 synthetic-verified |
| 03 | Highlights & screen intelligence (reframing) | 🟡 synthetic-verified |
| 04 | Captions, branding, Hyperframes rendering | ✅ synthetic-verified (acceptance review done; production render pending owner) |
| 05 | Topic-to-video | ⬜ |
| 06 | Advanced timeline editor | ⬜ |
| 07 | Instagram publishing (YouTube postponed, D-035) | 🟡 Codex: OAuth + queue built, Business account not yet connected |
| 08 | Analytics, feedback, SaaS management | ⬜ |
| 09 | Final integration, testing, submission | ⬜ |

Full task lists and acceptance criteria: `docs/MASTER_PROMPT.md` Section 19. Results below.

## Phase 00
Objective: correct repo, team invitations, preserved prompt, docs, monorepo skeleton.

| Item | Status | Evidence |
|------|--------|----------|
| GitHub auth verified (admin on repo) | ✅ | `gh auth status`, repo permissions `admin: true` |
| Remote = `sahilkarande0918-cmd/Reel-Studio` | ✅ | `git remote -v` |
| Invitations: sahillokhande5841-cmyk, Atharva486dherange, SK999CodingWorld | ✅ sent · accepted: sahillokhande5841-cmyk, SK999CodingWorld · pending: Atharva486dherange (2026-10-16) | `GET /collaborators`, `GET /invitations` |
| Master prompt preserved verbatim | ✅ | `docs/MASTER_PROMPT.md`, addendum `docs/MASTER_PROMPT_SUPABASE_ADDENDUM.md` |
| CLAUDE.md, AGENTS.md, persistent docs | ✅ | `docs/` |
| Ponytail installed & active | ✅ | `~/.claude/settings.json` `ponytail@ponytail: true`, SessionStart hook active |
| Design skills | ✅ | Hallmark + Taste Skill (`design-taste-frontend`) installed in `~/.claude/skills` |
| External repo licence review | ✅ | `docs/THIRD_PARTY_LICENSES.md` |
| Monorepo skeleton | ✅ | pnpm workspace, `apps/web`, `apps/api`, `supabase/` |
| Issue labels / phase tracking | ✅ | 9 labels, 10 milestones (Phase 00–09) |
| First commits pushed | ✅ | `main` on origin |

## Phase 01
| Task | Status | Evidence |
|------|--------|----------|
| Next.js 16 + TS + Tailwind v4 | ✅ | `next build` passes |
| Design tokens + landing page | ✅ | taste-skill inspector: 0 FAIL (1 WARN: no footage, defended) |
| Supabase SSR auth: signup/login/logout/reset/confirm | ✅ local · ✅ production signup + email confirm + onboarding (owner, 2026-10-17) | browser test on local stack; production data check |
| Protected routes (proxy.ts) | ✅ | `curl /dashboard` → 307 `/login?next=/dashboard` |
| Workspace model + onboarding | ✅ local | created "Nimbu Academy" via UI, role owner |
| Migrations + RLS | ✅ local | `supabase test db` 16/16, `supabase db lint` clean |
| FastAPI + /health + JWT auth | ✅ | pytest 5/5; `/me` real token 200, tampered 401 |
| Frontend ↔ backend discovery, offline state | ✅ local | heartbeat row fresh; badge online → offline after API stop |
| Remote Supabase project (friend's org) | ⛔ owner | CLI now linked to `adjwycjsxtxvjockxtan`, but **no migrations applied** (5 pending); owner runs `supabase db push --linked` (DEPLOYMENT.md) |
| Vercel deployment | ✅ pages / 🟡 app | https://reel-studio-taupe.vercel.app — owner set env vars; public pages 200, protected 307→login; app data flows fail until the remote DB has migrations |
| Tunnel | ✅ | Microsoft Dev Tunnels, stable URL, verified from outside (`backend-probe` workflow); Tailscale/Cloudflare blocked by the Fortinet network (D-024) |
| Repo moved out of OneDrive | ✅ | `C:\dev\Reel-Studio`, fresh clone, history intact |

## Phase 02 — verified on synthetic fixtures
| Task | Status | Evidence |
|------|--------|----------|
| Recording-upload UI (drag-drop, progress, resume, offline state) | ✅ code | `components/studio/uploader.tsx` |
| Backend ingestion, chunked resumable, validation | ✅ | upload integration tests 6/6 |
| FFprobe metadata / audio extraction | ✅ code | `services/media.py` (run in job) |
| faster-whisper | ✅ | Hinglish-Apex CT2 on CUDA, 25.8× real time on the 192 s lecture |
| WhisperX alignment | ⬜ deferred | D-016: no Roman-Hinglish alignment model; faster-whisper word timing measured ±0.27 s |
| Store transcript (raw + corrected, words, segments) | ✅ schema | migration 20261016140000 |
| Glossary correction + institute glossary | ✅ | glossary tests 5/5, `/glossary` page |
| Transcript editor synced to video | ✅ | browser: search, seek, highlight follows playback, edit persists |
| Progress, retries, cancellation | ✅ | UI cancel/retry; worker kill → stale requeue → attempt 2 succeeded |
| Benchmark | ✅ | 7.45 s for 192.5 s audio, 2.2 GB GPU (TEST_STATUS) |
| **Acceptance** | 🟡 | all criteria pass on the SYNTHETIC lecture; real-world recording unverified (none legally free); AbortController/Kubernetes misses → Phase 03 OCR |

## Phase 03 — verified on synthetic fixtures
| Task | Status | Evidence |
|------|--------|----------|
| Speech energy, pauses | ✅ | `audio_features.py` self-check; speaker-relative pause ranking |
| Screen changes / activity / scene cuts | ✅ | 2 fps change map; cuts at exact window switches on focus fixture (26.0 s, 31.5 s) |
| Screen OCR + evidence-based term correction | ✅ | AbortController 0/4 → 4/4 on lecture; WER 31.1 % → 28.2 %; guards tested |
| Semantic candidates + complete-thought boundaries | ✅ | lecture: 2/2 clips start and end on real topic boundaries |
| Ranking, dedupe, reasons | ✅ | NMS, labelled heuristic(+LLM) score, reasons per clip |
| Local LLM judgment | ✅ | Ollama qwen2.5vl:7b, temperature 0; vetoes on agreement |
| Active-region reframing + smoothing | ✅ | 7 scenario tests; stable keyframes on real frames |
| Clip selection UI, crop preview/override | ✅ | browser: select, boundary edit snaps to word end (61.19 s), manual crop keyframe persisted |
| Judge-style recordings | 🟡 | static/typing/jitter/long lines/scroll/window-switch covered (unit + fixtures); changing *diagram* and slides not yet in a real fixture |
| Real class recording | ⛔ | none legally obtainable at ₹0 (TEST_STATUS) |

## Phase 04 — in progress
| Task | Status | Evidence |
|------|--------|----------|
| Canonical timeline schema (Zod → JSON Schema, Vitest) | ✅ | `packages/timeline-schema`, 6/6 |
| Timeline from highlight + corrected words + crop keyframes | ✅ | `services/rendering/timeline.py`, validated against the schema |
| Hyperframes compiler (camera follows keyframes, word captions in safe zone, code chips, bundled fonts) | ✅ | `services/rendering/compose.py`; preview geometry matches |
| Render job (lint, live progress, ffprobe verify, thumbnail), cache by timeline hash | ✅ | two highlights rendered; crash → attempt 2 succeeded |
| API + UI (render, progress, inline player, signed download) | ✅ | browser on local stack |
| Brand kits (colours, fonts, logo, intro/outro, handle, watermark, caption presets) | ✅ local | `brand_kits` + `/brand` editor with live preview; branded render verified (frames, durations, silent cards) |
| Intro/outro cards | ✅ | cards in the main composition (D-028) |
| SRT/VTT export | ✅ | `GET /renders/{id}/captions?format=srt|vtt`; FFmpeg parses both (16 cues) |
| Quality presets | ✅ draft / looks / delivery | Export panel |
| Timing consistency check (caption words vs audio) | ✅ | audio offset 0.0 ms + 100 % words on speech on real renders; sensitivity measured (D-029) |
| Security fix: explicit table grants | ✅ | D-025, pgTAP 22/22 |

### Phase 04 acceptance review (2026-10-17)
Tasks (MASTER_PROMPT §19):
| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1–2 | Hyperframes integration, rendering adapter | ✅ | `services/rendering`, `workers/render.py` |
| 3 | Synchronised caption compositions | ✅ | word on/off times from the transcript; timing check 0 ms offset |
| 4–5 | Technical vocabulary styling, code formatting | ✅ | code-term chips in the code font (`AbortController`) |
| 6 | Automatic brand-kit integration | ✅ | default kit preselected; snapshot per render |
| 7 | Reusable intro/outro templates | ✅ | kit intro/outro cards (D-028) |
| 8 | Video export pipeline | ✅ | lint → render → ffprobe verify → thumbnail → signed download |
| 9 | MP4 quality settings | ✅ | draft / looks / delivery |
| 10 | Thumbnails and previews | ✅ | thumbnail poster, inline player, subtitle-accurate studio preview |
| 11 | Optimise render performance | ✅ measured | D-030 benchmark; defaults kept |
| 12 | Caching for re-rendering | ✅ | timeline-hash cache |
| 13 | Verify timing consistency | ✅ | D-029 |
| 14 | Complete recording-to-video workflow | ✅ synthetic | upload → transcript → highlights → branded MP4 (local). Production: upload → transcribe → analyze ✅ on the owner's real physics class; a production render is pending the owner |

§9 caption system: word timestamps ✅, Hinglish ✅, technical vocabulary ✅, capitalisation and special characters ✅ (VTT-escaped), subtitle preview ✅, subtitle editing ✅ (transcript editor feeds renders), multiple styles ✅, positioning ✅, font and colour selection ✅, word emphasis ✅, safe zones ✅, line breaking ✅ (D-031), burned-in + SRT/VTT ✅. Syntax highlighting of multi-line code blocks is n/a in Mode A (code comes from the recording); it belongs to Mode B (Phase 05).

§10 brand kit: name, logo, colours (background/text/accent), fonts, caption style, intro/outro, handle, watermark, reusable kits (several per org, one default), preview before rendering, snapshots ✅. A per-kit "default video settings" option is not built (quality is chosen per render).

Acceptance ("upload a programming class → professional 9:16 reel with highlight, framing, accurate captions, branding, audio sync"): ✅ on the **synthetic** programming lecture (frames, ffprobe and timing checks in TEST_STATUS). A real programming class remains unavailable (no free, licensed recording).


## 2026-10-17 Codex hackathon sprint priority overlay

See [CODEX_HANDOFF.md](CODEX_HANDOFF.md). **Original phase numbering and the official PS remain unchanged.** Prioritize Phase 05 Mode B working MP4 → UI redesign across main screens → Phase 06 real editable/exportable timeline → Phase 07 official Instagram/YouTube publishing + scheduler → Phase 08 genuine analytics/feedback → Phase 09 integrated judge demo. Run production smoke checks between slices. Treat subscription billing/deep administration and nonessential polish as stretch after PS workflows. Phase 04 already has successful local synthetic MP4 exports; production render and real programming lecture accuracy remain unverified. Keep essential session auth, tenant isolation/RLS, API authorization, upload checks, OAuth/token safety, and publish idempotency. Verify real results before changing statuses; some older Phase 01 lines above are stale, so check DEPLOYMENT and TEST_STATUS.

## Active checkpoint — 2026-10-17: topic studio and Instagram integration

Branch: `feature/topic-studio`. Added local topic generation (Ollama → validated storyboard → Kokoro → measured captions → canonical timeline → Hyperframes), refreshed studio UI, and authenticated Instagram Login/publishing/insights screens and worker handlers. These are implemented slices, not completed phase acceptance.

Instagram env presence verified without values: client ID numeric, secret present, exact callback `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`, backend encryption key present. No manual test token. Actual account authorization, Meta registered redirect acceptance, scopes and token validity remain unverified until OAuth consent. Never publish a real test Reel without the owner's specific approval.

Both migrations `20261017030000_topic_generations.sql` and `20261017040000_social_publishing.sql` applied only to verified project `adjwycjsxtxvjockxtan`. API/tunnel/worker restarted; local health 200 and unauthenticated social route 401. Zero connected accounts and zero publication rows at restart. Port-8001 local test stack was left untouched.

Verified: backend 74 passed / 6 integration tests skipped (one upstream deprecation warning), Ruff clean; workspace lint and typecheck pass; timeline 9 tests pass; direct Next production build passes including publishing callback. Earlier local database suite: 47 pgTAP tests pass and schema lint clean; the later change_publication RPC has not yet been exercised locally. No new live Mode B MP4, Instagram OAuth, real publish, or real analytics retrieval has been verified. Frontend deployment pending this checkpoint.

Next: deploy callback/UI, finish authorized Instagram OAuth, verify public media ingestion without publishing, exercise scheduling failure/retry/idempotency, render and inspect a genuine topic video. Phase 06 full editor, Google OAuth/upload, analytics feedback and final end-to-end acceptance remain outstanding. Keep Google credentials private in backend .env. OAuth tokens are encrypted in backend-only database rows, never frontend storage.
