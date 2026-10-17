> **Pre-compaction checkpoint (2026-10-17): read [CHECKPOINT.md](CHECKPOINT.md) first.** Latest: homepage + 61 s Hyperframes tour, sin1 speed pass, Topic JSON import, Instagram delivery copy, silent-render guard, self-restarting engine (HEAD `b2b1c38` + docs). Backlog A/B/C (context-aware editing, caption personalities, clip collections) is NOT implemented.

# Reel Studio — IDE-independent handoff (2026-10-17)

For any agent (Cursor, Antigravity, Claude, Codex) or human continuing this project without the chat history.
Read this file first, then `docs/CHECKPOINT.md`, `AGENTS.md`, `CLAUDE.md`. The requirements live unchanged in
`docs/ORIGINAL_PS.md` and `docs/MASTER_PROMPT.md` (+ `MASTER_PROMPT_SUPABASE_ADDENDUM.md`): **never edit those two**.

**UI audit, 2026-10-17:** Antigravity's local `714b8e2` introduced the forest/ivory shell and reference-style dashboard
but was not on `origin/main` when audited. The follow-up UI pass keeps its palette and layout while removing invented
project thumbnails, jobs, analytics, upgrade offer, and dead navigation. Dashboard counts and Instagram insights now
come from the authorized workspace's stored data; missing metrics show as unavailable. The header search opens filtered
Projects. The three UI fonts are self-hosted with OFL notices, so builds require no Google Fonts request. No publishing
action was triggered during this UI work. See the latest entry in `docs/TEST_STATUS.md` for verification.

---

## Latest changes (after the homepage), 2026-10-17
- Shared logo: the landing `Logo`/`LogoMark` (Aperture mark) is now used on the sign-in pages and in the app sidebar,
  editor rail and mobile header (`components/landing/site-nav.tsx`).
- Speed: Vercel `regions: ["sin1"]` (`apps/web/vercel.json`) + `preferredRegion`; `app/(app)/loading.tsx`; parallel engine
  discovery remembered per session (`lib/backend.ts`); uploads check ownership once and persist progress every 64 MB;
  Instagram container polled every 3 s; renders with `--workers 8`.
- Topic Studio "Import script (JSON)" (`components/studio/topic-studio.tsx`): accepts a full generate request or a bare
  `{title, scenes}` storyboard; sample `samples/what-is-an-automation-engineer.json`.
- Publishing: cached Instagram delivery copy `instagram.mp4` (H.264 High 4.1, 3.5 Mbit/s CBR, 2 s GOP, AAC 48 kHz) served at
  `/renders/{id}/file/instagram`; Instagram's own status text kept on ERROR.
- Render: fails verification if a timeline with narration/unmuted media renders silent (peak < −45 dBFS).
- Engine: `app.serve` watchdog restarts tunnel/worker within 10 s; `apps/api/start-engine.cmd` (detached, single instance,
  outer restart loop, logs in `%LOCALAPPDATA%\reel-studio\logs`); Windows task "Reel Studio Engine" runs it 30 s after logon.

## Context-aware AI editing (Feature A), 2026-10-17
Highlight selection now reads the class as a **lecture outline** before choosing clips:
- `services/highlights/outline.py` (new): the local LLM (`qwen2.5vl:7b`, temperature 0) splits the numbered, timed
  transcript sentences into **teaching steps** (introduction / concept / example / demonstration / question / recap /
  conclusion / digression) grouped into **topics**; long classes are read in 150-sentence overlapping chunks; output is
  repaired into a gap-free cover; any step > 60 s is split at its strongest internal boundary (speaker-relative pause +
  closing cue before + fresh start after, never just before an answer). LLM offline → deterministic TextTiling-style
  lexical segmentation (vocabulary shift + long pauses), labelled `lexical`. Cached per transcript text (`outline.json`).
- `services/highlights/candidates.py`: every 30–60 s sentence-bounded window is scored from five named, deterministic
  components (0–100, never a probability): **context completeness 35 %** (starts/ends on whole steps, whole-step share,
  covers the whole topic), **educational value 25 %** (step kinds, technical terms, spoken on-screen identifiers, code
  activity), **opening 15 %** (cue/question/pause, penalised if it leans on earlier talk or starts on a recap),
  **ending 15 %** (closing cue/step end/pause, penalised if it stops before an answer or right after posing a point),
  **engagement 10 %** (voice, pace, learned length). Windows never open on filler ("Thik hai?"); clip edges breathe
  ≤ 0.2 s / 0.3 s into the surrounding pauses. De-duplication: time overlap, same core teaching step, or ≥ 55 %
  content-word overlap. The local LLM judge now sees the outline and the sentences before/after the clip; its
  standalone/complete/educational judgment is blended into context (35 %) and educational (35 %) and shown separately.
- Grounded explanation per clip ("Selected because it starts where the instructor begins “…”, covers the example “…”
  and conclusion “…”, and ends as that point is concluded."), exact opening/closing sentences, and a **limitation** line
  when a clip is partial or its topic is longer than 60 s; the job result says when no complete explanation fits.
- UI (`components/studio/highlights.tsx`): title, NN/100, start–end, duration, complete/partial tag, explanation,
  5-bar breakdown, opens/ends quotes, limitation, collapsible lecture outline (clip's steps highlighted), preview, boundary
  edits, Select/Reject, and **Create reel** (selects + renders through the existing pipeline).
- Reliability fixes found while verifying: PostgREST client uses HTTP/1.1 (`core/db.py`; HTTP/2 raised "Server
  disconnected" after the long LLM stages and failed every retry); worker drops its cached client after a transport error
  (`workers/run.py`); one Ollama context size (12288) + one retry on a 5xx (`llm.py`).
- Dry-run tool: `python tests/dryrun_highlights.py RECORDING_ID [--fresh]` (prints outline + picks, writes nothing).

## Backlog — approved, NOT YET IMPLEMENTED (postponed until the owner explicitly asks)
### Feature B — AI caption personalities
Five selectable caption styles — **Minimal, Creator, Cinematic, Learning, Brand** — selectable in the studios and editor and
applied by the compiler (`compose.py`) so they change the actual rendered MP4, not only the preview.
### Feature C — AI clip collections
Group related highlights from one recording into a coherent educational Reel series (ordering, shared theme), with
AI-generated series/episode titles based strictly on the lecture's actual content (transcript), no invented claims.

## Speed pass (2026-10-17)
- Cause of slow clicks: Vercel functions ran in iad1 (US East) while Supabase is in ap-southeast-1 (Singapore), ~200 ms per
  database round trip, several per page, plus no loading UI. Fix: `apps/web/vercel.json` `regions: ["sin1"]` (+ `preferredRegion`
  in the root layout), verified live `x-vercel-id: bom1::sin1::…`; `app/(app)/loading.tsx` skeleton; engine discovery probes
  tunnel and same-machine in parallel and remembers the winner (`lib/backend.ts`).
- Uploads: ownership checked once per upload (not per 8 MB chunk), progress written every 64 MB. Instagram: container status
  polled every 3 s at first (was 10 s). Renders: `--workers 8` (measured 111 s vs 123 s for a 28 s Mode A reel; capture-bound,
  GPU encoding gave no meaningful gain).
- Not measured: authenticated page timings on production (needs the owner's login); expected saving ≈ 0.2 s × database
  round trips per page.

## Homepage redesign + 60-second Hyperframes tour (2026-10-17)
- **Homepage** (`apps/web/app/page.tsx`, `components/landing/{site-nav,hero-visual,tour-player,hinglish-compare,legal-page}.tsx`):
  forest/ivory editorial design (Fraunces + DM Sans, the owner's theme commits `714b8e2`/`d174ff1`); sticky nav; hero with a
  real class frame, the real crop keyframes of render 023ff36c and the rendered reel; embedded tour; how it works; real
  Hinglish corrections (AbortController/AbortError via on-screen OCR, useEffect via glossary, from the synthetic lecture's
  transcript) next to the source frames; reframing demo; both modes; editor + brand kits; the verified Instagram publish
  (link to the real permalink, no invented stats); CTA; footer; new `/privacy` and `/terms`. Old landing components and
  Wikimedia archive images removed. `proxy.ts` now lets `/landing/*`, media files, `/privacy`, `/terms` through.
- **Tour** (`marketing/tutorial/`): `capture.mjs` (real app screens + target boxes via the Chrome bundled with
  Hyperframes, local stack, synthetic data), `narrate.py` (Kokoro via `hyperframes tts` + faster-whisper word timings),
  `build.py` (Hyperframes composition: camera moves, cursor, rings, karaoke captions, synthesized UI sounds, real reels),
  then `hyperframes lint` (0 errors) and `hyperframes render --fps 30 --quality high`. All composition and rendering is
  Hyperframes; FFmpeg/ffprobe were used only for probing and for extracting stills/short loops for the web page.
  Output 1920×1080, 30 fps, H.264 + AAC 48 kHz stereo, **61.4 s**, 17.3 MB, peak −1.9 dB; WebVTT captions generated from
  the same word timings. Served from `apps/web/public/landing/` (Vercel static, faststart). `build/` is git-ignored;
  `.gitignore` exempts only `apps/web/public/landing/*.mp4`.
- Rebuild: local stack + web running → `node marketing/tutorial/capture.mjs` (env HF_NODE_MODULES, CHROME, EMPTY_PROJECT)
  → `python marketing/tutorial/narrate.py` → `python marketing/tutorial/build.py` → `hyperframes render marketing/tutorial/build/project
  --fps 30 --quality high --video-frame-format png -o marketing/tutorial/build/reel-studio-tour.mp4` → copy MP4 + VTT to `apps/web/public/landing/`.
- Fixes found on the way: editor text invisible on the forest theme (style preset names, media cards) → fixed; narration
  aligner rejected scenes with hallucinated zero-length words → now drops them; landing MP4s were excluded by `*.mp4`.
- Verified: lint, tsc, `next build`, API pytest 90 passed; full-page screenshots at 1440 and 390 px (no horizontal
  overflow); tour plays locally and **on the deployed site** (headless Chrome: playing, 1920×1080, 61.4 s; live file
  byte-identical to the render). The in-app browser pane blocks that media request itself (ERR_BLOCKED_BY_CLIENT), not the site.

## 1. Objective
Hackathon PS4, "Reel Studio": an AI video studio for technical educators and institutes.
- **Mode A, Recording → Reels**: upload a class recording; Hinglish transcription (Roman script) with corrected technical
  terms; ranked, explained 30–60 s highlights on complete thoughts; smart 9:16 crop that follows code/board; synced
  captions; brand kit; edit; MP4 export; publish.
- **Mode B, Topic → Video**: a topic (e.g. "JSON vs XML") becomes an AI script and storyboard (editable), animated code
  cards, local Kokoro voiceover, synced captions, branding and a ~45 s 1080×1920 MP4.
- Shared: multitrack editor, Hyperframes rendering, project management, Instagram publishing/scheduling, analytics and
  AI feedback that tunes future highlight scoring.

## 2. Non-negotiable owner rules
- **₹0 cost.** No paid APIs, cloud GPUs, paid DB tiers, billing, or Hyperframes cloud rendering.
- **No AI attribution anywhere**: no AI as author, contributor or co-author, and **no `Co-Authored-By` trailers** (this
  overrides tool defaults). Commit only as `sahilkarande0918-cmd` (sahilkarande0918@gmail.com). Never force-push.
- Supabase: only project **`adjwycjsxtxvjockxtan`** (Reel-Studio). Never touch the owner's other SaaS project or the
  owner's **Sahvora** Meta app/accounts. Never disable RLS. New tables need explicit grants (D-025).
- **YouTube is postponed** until the owner explicitly asks. Billing and complex admin are postponed too.
- **Never publish a real Reel without explicit owner approval of account, video and exact caption.** Never connect,
  convert or publish to the personal Instagram `@sahil_karande`.
- No secrets in git, docs, logs or chat. Never ask for secret values in chat. No fake features or fabricated metrics;
  label synthetic data. Never mark unrun tests as passed.
- Don't use ngrok (owner's choice). Never use the obsolete OneDrive copy of the repo.

## 3. Architecture and stack
```
Browser ── Next.js 16 on Vercel (apps/web) ───► Supabase adjwycjsxtxvjockxtan (Auth, Postgres+RLS, Realtime)
   │                                                   ▲ service role
   └── HTTPS (Microsoft Dev Tunnel, signed URLs) ──► FastAPI + durable worker on the owner's GPU laptop (apps/api)
         faster-whisper (Hinglish CT2 model) · OpenCV · RapidOCR · Ollama qwen2.5vl:7b · Kokoro TTS (hyperframes tts)
         Hyperframes 0.8.164 CLI (local render) · GSAP 3.14.2 · bundled OFL fonts · FFmpeg/ffprobe
```
- Frontend: Next.js 16 App Router (`proxy.ts` = middleware), React 19, TypeScript, Tailwind v4, TanStack Query, Lucide.
- Backend: Python 3.11, FastAPI, Pydantic, Supabase-backed job queue (`claim_next_job`), worker handlers per job type.
- **One canonical timeline**: Zod in `packages/timeline-schema/src/index.ts` → `timeline.schema.json`
  (`pnpm build:schema`) → validated in Python (`app/services/rendering/timeline.py`) → compiled by **one** compiler
  `app/services/rendering/compose.py` → Hyperframes `index.html` → render worker → ffprobe-verified MP4.
- The editor preview uses the same compiler: `POST /renders/{id}/preview` returns compiler HTML plus a small seek
  runtime (`app/services/rendering/preview.py`), loaded as iframe `srcdoc` with `<base>` set to a signed folder URL.

## 4. Phase status (truthful)
| Phase | Status |
|---|---|
| 00 Foundation, 01 Auth/DB/deploy | ✅ |
| 02 Ingestion + Hinglish ASR, 03 Highlights + reframing | ✅ synthetic recordings + owner's **real physics class on production** |
| 04 Captions/branding/render | ✅ incl. brand kits, SRT/VTT, timing check; **production render of the real physics class verified** |
| 05 Topic → Video | ✅ end to end locally; editable script → re-record → render verified; plain-language errors |
| UI redesign | ✅ dark cinematic theme, all screens, desktop + mobile inspected |
| Style presets | ✅ Focus/Energy/Story/Signature in timeline `stylePreset`, applied by compiler (verified in MP4s) |
| 06 Editor | ✅ verified on Mode A (synthetic) and Mode B renders, local stack |
| 07 Instagram | ✅ OAuth with Business account and **real publish verified**. Scheduling is built but **not verified with a real future-dated post** |
| 08 Analytics + AI feedback | 🟡 real insights refresh verified (values 0 right after posting); AI feedback needs ≥3 published reels with reach, **not yet exercised on real data** |
| 09 Submission | 🟡 README rewritten; production E2E in the owner's account and final materials pending |

## 5. Verified milestones (actually run)
- **Real Instagram publishing, 2026-10-17**: a 44.5 s physics reel (top highlight "Understanding Displacement and
  Distance in Motion" from the owner's real class, rendered on production) was published once, with the owner's
  explicit approval, to Business account **@career.with.purpose** (IG user `17841466046205321`, account_type BUSINESS).
  - Media ID `18111030863186503`, REELS. Permalink as returned by the API: **https://www.instagram.com/reel/DekyGWcDEAl/**
    (the code ends in a lowercase `l`, not `I`).
  - Caption verified through the API. One attempt, no duplicate.
  - Insights refresh returned 4 account metrics and 9 per-reel metrics (views, reach, likes, comments, shares, saved,
    total_interactions, ig_reels_avg_watch_time, ig_reels_video_view_total_time), all 0 minutes after posting.
- Public media URL reachable without a bypass header (local check + GitHub Actions `backend-probe` run 38984638199).
- **Editor, Mode B**: split, caption word edit, text overlay, Signature style → 1080×1920 H.264+AAC 46.77 s; edits visible in frames.
- **Editor, Mode A** (synthetic lecture): split/delete video and captions, Energy style → 28.17 s MP4 with code-following crop.
- **Topic Studio edit script**: scene-2 code edited in the UI → re-recorded → 42.27 s MP4 with the edit; invalid code rejected first.
- Tests: API pytest 90 passed / 6 skipped (integration); ruff clean; timeline-schema vitest 12 passed; web lint + tsc
  clean; `next build` ok. Vercel production READY on the pushed commits.
- Bug fixed: Mode A renders failed Hyperframes lint (`video_nested_in_timed_element`); the video wrapper is now untimed.
- Bug fixed: the app theme never loaded (Turbopack Tailwind loader dropped local `@import`); tokens are inlined in `globals.css`.

## 6. Known issues / unverified
- Mode B storyboards still repeat example code (live: 3 distinct of 5 scenes after the stricter gate; the script is
  editable, so a creator can fix it). `apps/api/app/services/generation/storyboard.py` `quality_issues`.
- Audio fades: implemented (ffmpeg volume expression after render, `app/workers/render.py` `apply_fades`); **not checked audibly**.
- Scheduled publishing (future `scheduled_at`) is not verified with a real post. Requires owner approval to test.
- AI feedback not exercised on real data (needs ≥3 published reels with reach).
- Editor is desktop-first (side panels hidden below `lg`); the timeline works on tablets but is not tuned for phones.
- `GET /{ig-user-id}/permissions` returns error 100 for Instagram Login tokens; the callback falls back to the scopes from the token exchange (fine).
- Running `next build` while `next dev` runs makes the dev server serve stale CSS: stop dev, delete `apps/web/.next`, restart.
- Production E2E (Topic → Generate → Edit → Render → Download) in the owner's own account on the live site: **not yet run**.

## 7. Key files and entry points
**Web (`apps/web`)**
- Shell: `app/(app)/layout.tsx`, `components/app/sidebar.tsx` (icon rail on `/editor/*`), `components/app/backend-badge.tsx`, theme tokens in `app/globals.css`.
- Pages: `app/(app)/{dashboard,projects,recordings,topics,editor,brand,glossary,publishing,analytics,settings}/page.tsx`, project workspace `app/(app)/projects/[id]/page.tsx`, editor `app/(app)/editor/[id]/page.tsx`.
- Studios: `components/studio/topic-studio.tsx` (generation, stepper, script editor), `recording-studio.tsx` (6-step flow), `highlights.tsx`, `transcript-view.tsx`, `renders.tsx`, `uploader.tsx`, `style-picker.tsx`.
- Editor: `components/editor/editor.tsx` (state, history, autosave, export), `timeline-panel.tsx`, `properties.tsx`, `use-preview.ts`, `render-thumb.tsx`.
- Publishing/analytics: `components/publishing/{publishing-studio,account-connections,analytics-studio,social-callback}.tsx`, `lib/social.ts`.
- Backend discovery and auth calls: `lib/backend.ts` (heartbeat URL, same-machine fallback `127.0.0.1:8000`), errors `lib/api-error.ts`, `lib/friendly-error.ts`.

**API (`apps/api/app`)**
- `main.py` (routers), `serve.py` (API + worker + tunnel launcher; sets `PUBLIC_API_URL` for children).
- Routers: `api/recordings.py`, `api/renders.py` (highlight render, signed files, captions), `api/topics.py` (generate; accepts edited `storyboard`, `style`), `api/editor.py` (preview, signed folder, edit-render, brand), `api/social.py` (Instagram connect/callback/accounts/disconnect/insights, `/feedback`), `api/publishing.py` (queue, cancel, retry).
- Workers: `workers/run.py` (dispatcher), `transcribe.py`, `analyze.py` (uses learned ideal length), `generate.py`, `render.py` (lint, render, fades, verify, timing check), `publish.py` (publish + insights).
- Services: `services/rendering/{compose,timeline,preview,captions,sync}.py`, `services/generation/{storyboard,narration,...}`, `services/highlights/candidates.py`, `services/publishing/{instagram,accounts,tokens}.py`, `services/feedback.py`.

**Shared/DB**: `packages/timeline-schema/src/{index,edit}.ts` (+ tests), `supabase/migrations/*` (latest `20261017050000_timeline_drafts.sql`: drafts, `render_jobs.parent_render_id`, `platform_metrics.media`, `performance_feedback`; applied to production and local).

## 8. Environment variable NAMES (values live only in ignored `.env*` files and the Vercel dashboard)
- `apps/web/.env.local` / Vercel: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SITE_URL`, optional `NEXT_PUBLIC_API_URL`.
- `apps/api/.env`: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY` (never regenerate: it encrypts the stored
  Instagram token and derives media signing), `INSTAGRAM_CLIENT_ID` (= Reel Studio-IG **Instagram app ID**),
  `INSTAGRAM_CLIENT_SECRET`, `INSTAGRAM_REDIRECT_URI` (= `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`,
  also registered in Meta → Instagram → Business login settings), `INSTAGRAM_API_VERSION`, `ALLOWED_ORIGINS`, `DATA_DIR`,
  `OLLAMA_URL`, `OLLAMA_MODEL`, `PUBLIC_API_URL`, `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`,
  `WHISPER_LANGUAGE`. `GOOGLE_*` names exist for postponed YouTube work: leave them unused.

## 9. Local paths, services, commands (Windows laptop of the owner)
- Repo `C:\dev\Reel-Studio`. Python venv `C:\Users\Sahil\AppData\Local\reel-studio\venv` (no `apps/api/.venv`). Data,
  models and renders in `C:\Users\Sahil\AppData\Local\reel-studio\data` (`orgs/<org>/renders/<render>/out.mp4`).
- Production backend + worker + tunnel: `cd apps/api && <venv>\Scripts\python -m app.serve --tunnel devtunnel` → `:8000`,
  tunnel `https://j96sqlp6-8000.inc1.devtunnels.ms` (heartbeat to Supabase lets Vercel find it). Ollama must run (`ollama serve`; check with `curl localhost:11434/api/tags`, since `ollama list` hangs here).
- Local test stack: Docker Desktop + `pnpm exec supabase start -x vector,logflare,imgproxy,edge-runtime`, then
  `SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_SECRET_KEY=<from supabase status -o env> PUBLIC_API_URL=http://127.0.0.1:8001 <venv>\Scripts\python -m app.serve --tunnel none --port 8001`; web `pnpm --filter web dev` (:3000, `.env.local` points to local Supabase). Local login `upload-owner@test.local` (password in `apps/api/tests/test_upload_integration.py`).
- **Restart API and worker together after any backend change** (the launcher runs both). Find processes with
  `Get-CimInstance Win32_Process | ? CommandLine -like '*app.serve*'`.
- Checks: API `cd apps/api && <venv>\Scripts\python -m pytest -q && <venv>\Scripts\python -m ruff check .`; schema
  `cd packages/timeline-schema && pnpm test`; web `cd apps/web && pnpm lint && npx tsc --noEmit && npx next build`;
  DB `pnpm exec supabase test db`. Production migrations: verify `supabase/.temp/project-ref` = `adjwycjsxtxvjockxtan`, then `pnpm exec supabase db push --linked`.
- This network TLS-intercepts some tunnel traffic; verify the public tunnel with `gh workflow run backend-probe.yml -f url=<tunnel>`.

## 10. Deployment state
- Vercel project `prj_VVWevgFfCwq7LgQauMu1B11RGzua`, https://reel-studio-taupe.vercel.app, auto-deploys `main` (READY).
- Supabase `adjwycjsxtxvjockxtan`: all migrations through `20261017050000` applied.
- Production backend running on the owner's laptop at checkpoint time; it must be running for processing, preview,
  render, publish and insights (the site shows "Engine offline" otherwise; saved work is safe).

## 11. Git
- Branch `main`; remote `origin` = github.com/sahilkarande0918-cmd/Reel-Studio. Teammates also push small docs
  (`docs/sahil`, `docs/sk`): always `git pull --rebase` before pushing; never force-push.
- Recent history (newest first; this handoff commit sits on top):
  `32e018e` docs: verified Instagram publish + insights · `84ed5ac` docs: Instagram connection ·
  `565636e` scene-aware validation errors · `af7b676` six-step recording flow + stricter script gate ·
  `81d8da4` docs checkpoint/README/decisions · `41d1917` Instagram disconnect, insights, analytics, AI feedback ·
  `a34d491` multitrack editor · `4385a20` style presets + Mode A lint fix · `e5cf3b3` dark theme ·
  `f0c13fc` workspace shell + editable topic script · `79b0a70` previous checkpoint.

## 12. Next tasks, in order
1. **Production E2E in the owner's account** on https://reel-studio-taupe.vercel.app: Topic Studio → Generate →
   Edit (editor: split, caption, overlay) → Render → Download. Record results in `docs/TEST_STATUS.md` as production.
2. Verify the remaining editor controls (trim by dragging edges, move, duplicate, undo/redo, fades, transitions, crop
   lock, brand apply, caption position/fonts, autosave reopen) and fix bugs found.
3. Check audio fades audibly and final video quality on a short draft render.
4. UI usability/responsiveness pass (Recording Studio layout, editor below `lg`).
5. Instagram: verify a scheduled (future) post **only after explicit owner approval**; check retry and cancel flows.
6. AI feedback once ≥3 published reels have reach (owner approves each post).
7. Final integration testing and hackathon submission materials (README demo flow exists; slides/video script pending).

**First task for the next agent:** run the production E2E (task 1). Ensure the production backend
(`python -m app.serve --tunnel devtunnel`) and Ollama are running, log in on the live site, generate "JSON vs XML" in
Topic Studio, open it in the Editor, make one split, one caption edit and one text overlay, render, download, verify
the MP4 with ffprobe, and record the outcome.
