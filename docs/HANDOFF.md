> **IDE switch checkpoint (2026-10-17): read [IDE_HANDOFF.md](IDE_HANDOFF.md) first.** Real Instagram publishing verified (@career.with.purpose, media 18111030863186503, https://www.instagram.com/reel/DekyGWcDEAl/); editor, style presets and dark UI done. Next: production E2E in the owner's account (Topic → Generate → Edit → Render → Download).

> **Latest checkpoint (2026-10-17, after the Codex handoff): read [CHECKPOINT.md](CHECKPOINT.md) first.** Mode B now works end to end (JSON vs XML → 46.8 s 1080×1920 MP4, plays and downloads in the UI); repeated-code prompt fix not yet re-verified on a new video. Instagram Business OAuth still pending; nothing published. YouTube postponed (D-035). HEAD at checkpoint start: `fe984a0`.

> **Final checkpoint (2026-10-17):** Read [CODEX_TO_CLAUDE_HANDOFF.md](CODEX_TO_CLAUDE_HANDOFF.md) first. It supersedes historical status below. Mode B pipeline/UI implemented but live generation fails on fenced model JSON; full editor and YouTube unfinished. Instagram reaches Reel Studio-IG but awaits the separate Business-account login/consent. Never connect/convert the personal account or publish without explicit approval. Production deployed at 7419b77; two new migrations applied. Final backend: 76 pass, 6 skip, 1 known xfail; DB: 52 pass; final frontend build passes. Owner requested checkpoint only, no more features.
# Handoff — Reel Studio

_Session 1 checkpoint (2026-10-16), updated in session 2 (Phase 04 first task, Dev Tunnels, grants fix).
Read with `CLAUDE.md` (mandatory reading order). Everything here was verified unless marked otherwise._

## 1. Project identity and objective
Reel Studio — "the AI video studio built for technical educators". Hackathon PS4, 24-hour national
hackathon. Turns (A) long Hinglish programming-class screen recordings into ranked, branded 30–60 s
9:16 reels and (B) a topic prompt (e.g. "JSON vs XML") into a ~45 s explainer with animated code,
local voiceover and captions. Both modes share one editor, renderer (Hyperframes), publishing,
analytics and feedback loop. Hard rules: ₹0 cost, no fake features, no AI attribution in git, genuine
human commits only (operator identity `sahilkarande0918-cmd <sahilkarande0918@gmail.com>`).

## 2. Problem statement
`docs/ORIGINAL_PS.md` (verbatim + PS-1…PS-11 checklist). Full instructions: `docs/MASTER_PROMPT.md`
(verbatim, do not edit) + `docs/MASTER_PROMPT_SUPABASE_ADDENDUM.md`.

## 3. Requirements
- **Mandatory PS:** Hinglish ASR with word timing; 30–60 s highlights from transcript + voice energy + screen
  change; complete-thought boundaries; active-region 9:16 reframing; word-synced captions with correct tech
  terms and code as formatted text; automatic brand kit (colours, fonts, logo, intro, outro); timeline
  editor with fast re-render; topic → 45 s explainer (script, animated code, voiceover, captions).
- **Optional PS (in scope):** schedule/publish to Instagram + YouTube (official APIs), performance tracking,
  feedback into highlight ranking.
- **Extra scope:** advanced multi-track editor, accounts, workspaces, teams, subscriptions (test mode), usage.

## 4. Architecture and stack
Next.js 16 on Vercel ↔ Supabase (Auth, Postgres+RLS, Realtime) ↔ local FastAPI + worker on the owner's
RTX 5050 laptop, reached through Microsoft Dev Tunnels (stable URL, heartbeated into `backend_endpoints`).
Details: `docs/ARCHITECTURE.md`. Decisions D-001…D-026: `docs/DECISIONS.md`.

## 5. Phase status and verification level
| Phase | Status | Verification |
|-------|--------|--------------|
| 00 Foundation | ✅ | repo, docs, Ponytail + Hallmark + Taste Skill, labels, 10 milestones; invitations: sahillokhande5841-cmyk ✅ accepted, SK999CodingWorld ✅ accepted, Atharva486dherange ⏳ pending |
| 01 Frontend/auth/DB/deploy | 🟡 | local stack: fully verified (RLS now 22/22). Production: pages 200 / protected 307; remote 6/6 migrations (15 tables, RLS on all, explicit grants); backend on production with a live heartbeat; production signup → workspace → project → 75 MB upload → transcribe → analyze ✅ (owner, 2026-10-17); second-account RLS check pending; public tunnel ✅ (Dev Tunnels, verified from outside) |
| 02 Ingestion + transcription | 🟡 synthetic-verified | all acceptance steps pass on the generated lecture; real classroom validation not done |
| 03 Highlights + reframing | 🟡 synthetic-verified | OCR correction, highlights, reframing, UI pass on fixtures; diagram/slide footage not covered |
| 04 Captions/branding/render | 🟡 | render ✅ (crop camera, word captions, crash-retry, cache, signed download) · brand kits ✅ (editor, snapshot, intro/outro, watermark, 3 caption presets) · SRT/VTT ✅ · timing check ✅ · offline GSAP ✅ · balanced captions, positioning, subtitle preview ✅ · acceptance review done (synthetic-verified) · next: Phase 05 |
| 05–09 | ⬜ | topic-to-video, advanced editor, IG/YT publishing+scheduler, analytics+feedback+SaaS, final QA/submission |

## 6. Current exact task
`docs/CURRENT_TASK.md` → Phase 04 second task: brand kits (table, editor, snapshot into the timeline) +
intro/outro sub-compositions + caption style presets, then SRT/VTT and the timing check.

## 7. Source directories and entry points
| Path | What |
|------|------|
| `apps/web/app/page.tsx` + `components/landing/*` | landing (live 9:16 crop demo) |
| `apps/web/app/(auth)/*`, `app/auth/confirm/route.ts`, `proxy.ts` | auth flows, session refresh, protected-route redirect |
| `apps/web/app/onboarding/*` | workspace creation (`create_organization` RPC), workspace switch cookie `rs_org` |
| `apps/web/app/(app)/layout.tsx`, `components/app/*` | app shell, sidebar (Dashboard, Projects, Glossary), backend badge |
| `apps/web/app/(app)/projects/[id]/page.tsx` → `components/studio/recording-studio.tsx` | studio: uploader, job progress, highlights, transcript |
| `apps/web/components/studio/{uploader,job-progress,transcript-view,highlights,renders}.tsx` | chunked upload (8 MiB) w/ resume; Realtime progress, cancel/retry; synced transcript editor; highlights + 9:16 preview (same geometry as the renderer) + crop override; Export panel (render, progress, player, download) |
| `apps/web/lib/{backend,realtime,media}.ts` (backend: tunnel header + `127.0.0.1:8000` fallback), `lib/supabase/{client,server}.ts` | backend discovery + `apiFetch`, Realtime jobs hook, signed media URL hook, Supabase clients (`requireUser`, `requireOrg`) |
| `apps/api/app/main.py` | FastAPI app (`/health`, `/me`, `/recordings/*`, `/highlights/{id}/render`, `/renders/*`) + heartbeat lifespan |
| `apps/api/app/serve.py` | **launcher**: tunnel (`devtunnel` ← use this; cloudflare/tailscale/none) + API + worker |
| `apps/api/app/api/renders.py`, `app/core/signing.py` | render request (cache by timeline hash), signed playback/download URLs; shared HMAC signing |
| `apps/api/app/services/rendering/{timeline,compose}.py` + `fonts/` | canonical timeline builder/validator; Hyperframes compiler; bundled OFL fonts |
| `apps/api/app/workers/render.py` | render job: lint → render (live progress) → ffprobe verify → thumbnail |
| `packages/timeline-schema` | Zod canonical timeline, generated `timeline.schema.json`, Vitest |
| `.github/workflows/backend-probe.yml` | manual external probe of the tunnel (CORS, auth, 8 MiB body, interstitial) |
| `apps/api/app/api/recordings.py` | create/chunk/complete/status, `/transcribe`, `/analyze`, `/media-url`, `/media` |
| `apps/api/app/core/{auth,access,config,db,storage,heartbeat}.py` | Supabase-verified bearer auth, org-role checks (404 on foreign), settings, service client, UUID-only paths, URL heartbeat |
| `apps/api/app/workers/{run,jobs,transcribe,analyze,render}.py` | durable worker loop + job handlers |
| `apps/api/app/services/media.py` | ffprobe validation, audio extraction |
| `apps/api/app/services/transcription/{whisper,glossary,cleanup}.py` | ASR, term correction (dictionary/org/screen evidence), loop cleanup |
| `apps/api/app/services/screen_analysis/{activity,ocr,reframe}.py` | change maps, RapidOCR + identifiers, crop keyframes |
| `apps/api/app/services/highlights/{candidates,audio_features,llm}.py` | windows + scoring, energy/pauses, Ollama judge |
| `apps/api/tests/*` | unit tests + `bench_asr.py`, `eval_transcript.py`, `eval_highlights.py`, `test_upload_integration.py` |
| `tests/fixtures/lecture/{script,build,screen.html}` + `tests/fixtures/tts-onecore.ps1` | synthetic lecture generator |
| `scripts/convert-hinglish-model.sh` | CT2 conversion of the ASR model |
| `supabase/migrations/*.sql`, `supabase/tests/database/rls.test.sql`, `supabase/config.toml` | schema, RLS tests, local stack config |

## 8. How modules interact
Upload (web) → API writes chunks to disk → `complete` probes and inserts a `transcribe` job → worker
extracts audio, runs ASR, corrects terms, stores transcript/segments/words, marks recording `ready`,
inserts `analyze` job → worker samples screen activity, OCRs frames, applies screen-evidence fixes,
scores windows, asks the local LLM, plans crop keyframes, writes `highlight_candidates` → web reads
everything via Supabase (RLS) with Realtime invalidation; media plays from the API via HMAC-signed URLs;
user edits (words, highlight status/bounds/crop) go straight to Supabase via column-level grants.
Render: Export panel → `POST /highlights/{id}/render` builds + validates the timeline (or returns a cached
identical render) → `render_jobs` row + `render` job → worker compiles `index.html`, runs Hyperframes,
verifies with ffprobe → row `ready` → panel fetches signed URLs for the inline player and download.

## 9. Database
Migrations (applied to the **local** stack only):
`20261016120000_identity_orgs_jobs.sql`, `20261016140000_recordings_transcripts.sql`,
`20261016160000_highlights.sql`, `20261016180000_render_jobs.sql`, `20261016190000_explicit_grants.sql`
(security fix D-025: revokes default ALL/TRUNCATE). Remote `adjwycjsxtxvjockxtan`: linked, **none applied**.
Key RPCs: `create_organization`, `claim_next_job` (service role only), `requeue_stale_jobs` (service),
`cancel_job` (editors). Realtime publication: `jobs`, `source_recordings`, `highlight_candidates`, `render_jobs`.
Not yet created: brand kits, timelines/revisions, export_assets (folded into render_jobs, D-026), social accounts, publish
jobs, metrics, feedback, plans/subscriptions/usage.

## 10. Local environment and paths
Repo `C:\dev\Reel-Studio` (old OneDrive copy obsolete). Venv `C:\Users\Sahil\AppData\Local\reel-studio\venv`.
Data `C:\Users\Sahil\AppData\Local\reel-studio\data` (orgs/…, models/, test-recordings/, test-audio/, tts-eval/).
Full tool list: `docs/ENVIRONMENT.md`.

## 11. Models and commands
- ASR: `data/models/hinglish-apex-ct2` (Oriserve Whisper-Hindi2Hinglish-Apex, Apache-2.0, fp16, use `language=hi`).
  Re-create: `CONVERT_PY=…/convert-venv/Scripts/python OUT=…/hinglish-apex-ct2 scripts/convert-hinglish-model.sh`.
- LLM: Ollama `qwen2.5vl:7b` (check `curl localhost:11434/api/tags`; `ollama list` hangs).
- OCR: RapidOCR (pip). TTS: `HYPERFRAMES_PYTHON=<venv python> npx --yes hyperframes@0.8.164 tts "<text>" --voice hm_omega --lang hi -o out.wav`.
- Start everything locally: Docker Desktop → `pnpm exec supabase start -x vector,logflare,imgproxy,edge-runtime`
  → `cd apps/api && <venv>/python -m app.serve --tunnel devtunnel` (or `--tunnel none`) → `pnpm dev` (root) → http://localhost:3000.
- Render by hand: `timeline.build` + `compose.write_project`, then `HYPERFRAMES_TELEMETRY=0 npx --yes hyperframes@0.8.164 render --quality looks --video-frame-format png -o out.mp4 .`
- Tunnel: `devtunnel` (winget, GitHub login done); external check `gh workflow run backend-probe.yml -f url=https://j96sqlp6-8000.inc1.devtunnels.ms`.

## 12. Local test fixtures (synthetic, git-ignored)
`data/test-recordings/react-hooks-hinglish.mp4` (192.5 s, 5.9 MB), `react-hooks-hinglish-hq.mp4` (52 MB
lossless, for multi-chunk upload), `react-hooks-hinglish.reference.json`, `react-hooks-hinglish.ocr.json`,
`express-scroll-focus.mp4` (37.6 s) + `.reference.json`; `tests/fixtures/synthetic-lesson.mp4` (28 s,
SAPI voice). Rebuild: `<venv>/python tests/fixtures/lecture/build.py [--only lecture|focus]`.
Real Hindi speech clips (Common Voice samples from the Oriserve repo): `data/test-audio/`.
Local test users (local stack only, password in fixtures/tests): `asha@nimbu.test`, `upload-owner@test.local`.

## 13. Latest verified tests and measurements (synthetic fixture results — not guarantees for real lectures)
- Checkpoint: web lint ✅, typecheck ✅, build ✅; pytest 29 passed / 6 integration skipped; integration 6/6;
  pgTAP 16/16; db lint clean.
- 192.5 s audio transcribed in ~7.45 s on GPU (25.8× real time), ~2.2 GB GPU memory.
- WER 35.6 % raw → 31.1 % after glossary → 28.2 % with OCR screen evidence.
- `AbortController` 0/4 → 4/4 with OCR evidence; Kubernetes, JSON, setData still missed.
- Word timing: segment-start error mean 0.27 s, max 0.44 s.
- OCR: 35 frames ≈ 220 s on CPU.
- Highlights: 2/2 clips start and end on the fixture's real topic boundaries.
- Reframing: hard cuts at 26.0 s and 31.5 s = true window-switch times on the focus fixture.
- Upload resume through UI, cancel, retry and worker-crash recovery all verified.
- Session 2: pytest 43 passed / 6 skipped; schema Vitest 6/6; pgTAP 22/22; integration 6/6 (8 MiB chunks); web build ✅.
- Render: 46.53 s clip → 46.533 s MP4 in 155 s (first manual render 210 s); 50.85 s clip → 50.867 s in 159 s; `--quality looks`, png frame extraction, GPU drawelement capture.
- Captions show `AbortController` correctly as a code chip at the moment it is spoken.

## 14. Known bugs and limitations
- Real-world Hinglish classroom validation not done (no free licensed recording).
- ASR misses some terms not shown on screen (Kubernetes → "kubernetti", JSON, setData); romanisation variance inflates WER.
- Hallucination loops on very short clips (mitigated by `cleanup.remove_loops`).
- OCR is CPU-bound (≈3–6 s/frame); 1 h class capped at 90 frames ≈ 5–9 min.
- First GPU run after reboot spends minutes JIT-compiling kernels (Blackwell).
- Highlight thresholds tuned on synthetic speech; LLM judge (7B VL model) is noisy.
- No pitch/prosody features yet; PySceneDetect installed but unused (cuts from change map).
- Reframing not validated on diagrams/slides footage; no picture-in-picture/split layouts yet.
- Glossary `fetch` term lowercases sentence-initial "Fetch" only when matched exactly; one miss remains in eval.
- No frontend unit tests in apps/web yet (the schema package has Vitest).
- Captions inherit ASR errors ("use fish" for useFetch); panel-layout code is small (~17 px at 1080 wide).
- Renders fetch GSAP from jsDelivr (needs internet); 16 Studio-editing lint warnings (nested caption lines).
- On the owner's network the tunnel URL itself is TLS-intercepted; the app uses the 127.0.0.1 fallback there.

## 15. Unfinished work
Phase 01 production (remote migrations, auth URLs, email confirmation, backend switched to remote, production
RLS/E2E test); Phase 04 remainder (brand kits, intro/outro, SRT/VTT, timing check); Phases 05–09; WhisperX (deferred, D-016); onnxruntime-gpu OCR speed-up; Storage for small assets.

## 16. Remote deployment status
`docs/DEPLOYMENT.md` (single source of truth). Summary: Vercel https://reel-studio-taupe.vercel.app,
latest production deployment `dpl_8kA8nFpHbdXaxCMX8un2vNi2iu2e` (commit `9a4ee55`) READY; public pages
200, protected 307; env vars set by owner (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`,
`NEXT_PUBLIC_SITE_URL`); remote DB still empty (CLI linked, push pending); tunnel ✅ Dev Tunnels
`https://j96sqlp6-8000.inc1.devtunnels.ms` (backend still on the local Supabase stack). Every push to `main` auto-deploys.

## 17. Owner actions needed (no secrets in chat)
1. Supabase: done, 6/6 migrations live. Future migrations: `pnpm exec supabase db push --linked` from
   `C:\dev\Reel-Studio` (NOT the stale OneDrive `Reel Studio` copy); the assistant's pushes are blocked by its classifier.
2. Supabase Auth: Site URL + redirect URLs; decide on email confirmation (options and trade-offs in DEPLOYMENT.md).
3. Put the Reel-Studio `SUPABASE_URL` + secret key into `apps/api/.env` yourself, restart `app.serve --tunnel devtunnel`,
   then test signup → workspace → project → upload on production (the assistant may not enter passwords on non-local
   sites). Tailscale is not needed (blocked by the network, D-024).
4. Ask `Atharva486dherange` to accept the GitHub invitation; teammates commit their own work.
5. Later: Meta developer app + IG professional account (Phase 07); Google Cloud project with YouTube Data
   + Analytics APIs and OAuth client (Phase 07). Secrets go only into `apps/api/.env`.

## 18. Key decisions
D-001 Hyperframes renderer · D-002 Zod canonical timeline · D-003 Supabase job queue · D-004/D-022
heartbeat URL discovery · D-005 tunnels · D-006 chunked uploads · D-008 Python 3.11 · D-014 no
cacheComponents · D-015 Hinglish-Apex ASR · D-016 WhisperX deferred (Hindi aligners need Devanagari) ·
D-017 Blackwell JIT · D-018 RapidOCR + screen evidence · D-019 heuristic+LLM scoring with agreement veto ·
D-020 reframing hysteresis/panel · D-021 synthetic fixtures · D-023 one Python compiler · D-024 Dev Tunnels
(Tailscale/Cloudflare blocked by Fortinet; ngrok excluded by owner) · D-025 explicit grants · D-026 render_jobs as export asset.

## 19. Files changed this session
Everything in the repo was created this session (see `git log`). Main areas: docs/*, CLAUDE.md, AGENTS.md,
apps/web (landing, auth, app shell, studio, glossary), apps/api (API, worker, services, tests),
supabase (3 migrations, RLS tests, config), tests/fixtures (synthetic lecture generator), scripts/.

## 20. Commits
Session 2: `cc6636e` timeline schema · `9a8a1ee` Dev Tunnels + fallback · `3f19aec` render pipeline ·
`d2555a9` explicit grants · `a6ac345` backend-probe workflow · then the docs commit containing this file
(`git log --oneline -8`). Session 1 ended at `d696a94`.
Full history (oldest → newest): d0f6f18, 521b046, ab3e82d, 927dc5a, 37ed03e, abe3d24, 9f49e62, 2db179a,
0d5d58b, ad9d8f3, 8ea16fe, 7339471, 4b636a2, 629abc5, c444ae4, 6459e71, 1e1a9d2, 5e76599, 9a4ee55.
All authored by `sahilkarande0918-cmd`; no co-author trailers.

## 21–22. Working tree
Clean and in sync with `origin/main` at checkpoint time (verify with `git status -sb`). No pending changes.

## 23. Next implementation tasks (in order)
1. Phase 04 brand kits (CURRENT_TASK.md): `brand_kits` table + editor + snapshot into the timeline; intro/outro; caption presets.
2. SRT/VTT export, caption timing consistency check, vendor GSAP locally for offline renders.
3. When the owner has pushed migrations: switch the backend to the remote project; production RLS + upload + render test via the tunnel.
4. Phase 05 topic-to-video (Ollama script/storyboard, validated code, Kokoro TTS, code-typing compositions).
5. Phase 06 editor (Zustand multi-track on the canonical timeline, `@hyperframes/player` preview, autosave, undo/redo).
6. Phase 07 publishing (official IG Graph + YouTube APIs, encrypted tokens, durable scheduler), 08 analytics/feedback/SaaS, 09 QA + judge demo.

## 24. How to resume and test
1. Read docs in `CLAUDE.md` order; `git log --oneline -20`; `git status`.
2. Start Docker Desktop; `pnpm exec supabase start -x vector,logflare,imgproxy,edge-runtime`.
3. `cd apps/api && C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python -m app.serve --tunnel devtunnel`.
4. `pnpm dev`; sign in locally as `upload-owner@test.local`; open project "React hooks Hinglish lecture (synthetic)".
5. Checks: web lint/tsc/build; `pytest -q`; `RS_INTEGRATION=1 pytest tests/test_upload_integration.py`; `pnpm exec supabase test db`; `cd packages/timeline-schema && pnpm test`.

## 25. Critical warnings — do not repeat
- Never touch the owner's personal Supabase projects visible to the current CLI login; only `adjwycjsxtxvjockxtan`.
- Never commit as teammates or add `Co-Authored-By` (the harness suggests it — owner rule overrides).
- Never present synthetic results as real-world validation.
- Don't fuzzy-match plain words into symbol terms (`component` → `@Component` bug) or merge spans starting with Hindi function words (`se data` → setData bug); keep the regression tests.
- Don't let the LLM veto alone; it is noisy (dropped 9/10 windows when used alone).
- The Vercel connector cannot read/write env vars (403); ask the owner or use the CLI after login.
- Cloudflare quick tunnels and Tailscale fail on this network (Fortinet); use `--tunnel devtunnel`. Never use ngrok (owner).
- Every new table needs explicit grants; Supabase defaults grant ALL incl. TRUNCATE (D-025).
- After editing `packages/timeline-schema/src`, run `pnpm build:schema` (Vitest fails if the JSON Schema drifts).
- curl/WebFetch from this machine cannot reach `*.devtunnels.ms` (TLS interception); verify externally (check-host.net or `backend-probe`).
- Python one-off doc edits via heredoc broke once on quotes; prefer the Edit tool for docs.
- Kill old worker processes before restarting (PowerShell `Get-CimInstance Win32_Process … app.workers.run`), or an old process claims jobs with stale code.

## Active checkpoint — 2026-10-17: topic studio and Instagram integration

Branch: `feature/topic-studio`. Added local topic generation (Ollama → validated storyboard → Kokoro → measured captions → canonical timeline → Hyperframes), refreshed studio UI, and authenticated Instagram Login/publishing/insights screens and worker handlers. These are implemented slices, not completed phase acceptance.

Instagram env presence verified without values: client ID numeric, secret present, exact callback `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`, backend encryption key present. No manual test token. Actual account authorization, Meta registered redirect acceptance, scopes and token validity remain unverified until OAuth consent. Never publish a real test Reel without the owner's specific approval.

Both migrations `20261017030000_topic_generations.sql` and `20261017040000_social_publishing.sql` applied only to verified project `adjwycjsxtxvjockxtan`. API/tunnel/worker restarted; local health 200 and unauthenticated social route 401. Zero connected accounts and zero publication rows at restart. Port-8001 local test stack was left untouched.

Verified: backend 74 passed / 6 integration tests skipped (one upstream deprecation warning), Ruff clean; workspace lint and typecheck pass; timeline 9 tests pass; direct Next production build passes including publishing callback. Earlier local database suite: 47 pgTAP tests pass and schema lint clean; the later change_publication RPC has not yet been exercised locally. No new live Mode B MP4, Instagram OAuth, real publish, or real analytics retrieval has been verified. Frontend deployment pending this checkpoint.

Next: deploy callback/UI, finish authorized Instagram OAuth, verify public media ingestion without publishing, exercise scheduling failure/retry/idempotency, render and inspect a genuine topic video. Phase 06 full editor, Google OAuth/upload, analytics feedback and final end-to-end acceptance remain outstanding. Keep Google credentials private in backend .env. OAuth tokens are encrypted in backend-only database rows, never frontend storage.
