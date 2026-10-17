# Reel Studio — checkpoint (2026-10-17, before compaction)

**Read first after compaction**, then `docs/IDE_HANDOFF.md` (full detail), `docs/CURRENT_TASK.md` (backlog), `AGENTS.md`,
`CLAUDE.md`. Requirements are unchanged in `docs/ORIGINAL_PS.md` and `docs/MASTER_PROMPT.md` (never edit them).
Earlier checkpoint text is in git history.

## 1. Objective
Hackathon PS4 "Reel Studio": an AI video studio for technical educators and institutes.
- **Mode A, Recording → Reels**: class recording → Hinglish transcript with corrected technical terms → ranked, explained
  30–60 s highlights → code-aware 9:16 crop → synced captions → brand kit → editor → MP4 → Instagram.
- **Mode B, Topic → Video**: topic (or imported JSON script) → editable AI storyboard → animated code cards → Kokoro voiceover →
  synced captions → ~45 s 1080×1920 MP4.
- Shared: multitrack editor, Hyperframes renderer, Instagram publishing/scheduling, analytics + AI feedback.

## 2. Owner rules (non-negotiable)
₹0 cost · no AI authors/co-authors/trailers, commits only as `sahilkarande0918-cmd` · Supabase only `adjwycjsxtxvjockxtan`
(never the owner's SaaS project, never disable RLS, explicit grants) · **YouTube and billing postponed** · **never publish a
real Reel without explicit approval of account, video and caption** · never the personal `@sahil_karande` · no secrets or
private media in git · no ngrok · keep verified features working · use the existing stack (Next.js, FastAPI, Supabase,
Ollama, OpenCV, Hyperframes).

## 3. Status
| Area | Status |
|---|---|
| Phases 00–05 (foundation, auth, ASR, highlights, render, Topic→Video) | ✅ (synthetic + owner's real physics class on production) |
| UI | ✅ forest-green/ivory editorial theme (owner commits `714b8e2`, `d174ff1`; Fraunces + DM Sans); editor dark panels fixed `fd47089` |
| Homepage | ✅ redesigned (`999abb8`, `31adb26`) with embedded **61.4 s Hyperframes tour** (`bb693e0`), `/privacy`, `/terms` |
| Style presets | ✅ Focus / Energy / Story / Signature (timeline `stylePreset`, compiler) |
| 06 Editor | ✅ `/editor/[renderId]`, verified on Mode A and Mode B renders |
| Topic JSON import | ✅ `88a1176` "Import script (JSON)" in Topic Studio → Script & storyboard section; sample `samples/what-is-an-automation-engineer.json` |
| 07 Instagram | ✅ OAuth (@career.with.purpose), **3 real Reels published by/with the owner**, queue, retries, dedupe, delivery copy + real error text (`51f72b7`). Future-scheduled publish not yet verified live |
| 08 Analytics + AI feedback | 🟡 real insights refresh verified; AI feedback needs ≥3 reels with reach (not exercised yet) |
| Performance | ✅ Vercel functions in `sin1` next to Supabase (`5528a7c`), loading skeleton, parallel engine discovery, faster uploads/IG polling, 8 render workers |
| Engine uptime | ✅ watchdog in `app.serve` + `apps/api/start-engine.cmd/.ps1` + Windows task "Reel Studio Engine" at logon (`6cf530a`, `b2b1c38`) |
| 09 Submission | 🟡 README done; production E2E in the owner account + submission materials pending |

Published Reels: physics `18111030863186503` https://www.instagram.com/reel/DekyGWcDEAl/ · maths (owner) ·
automation engineer `17988096129063525` https://www.instagram.com/reel/DelT2zXm_Bt/ (3rd automatic attempt succeeded after a
tunnel blip and a transient Instagram processing ERROR; audio verified present, the owner had the Reel muted).

## 4. Architecture (detail in IDE_HANDOFF §3, §7)
Next.js 16 (Vercel, sin1) ↔ Supabase (Auth, Postgres+RLS, Realtime; ap-southeast-1) ↔ FastAPI + durable worker on the owner's
RTX 5050 laptop via Microsoft Dev Tunnel `https://j96sqlp6-8000.inc1.devtunnels.ms`. One canonical timeline (Zod
`packages/timeline-schema` → JSON Schema → Python validation) → one compiler `apps/api/app/services/rendering/compose.py`
→ Hyperframes 0.8.164 CLI → ffprobe-verified MP4 (silent-render guard `2b5b02c`). Editor preview = same compiler HTML +
seek runtime (`services/rendering/preview.py`). AI: faster-whisper (Hinglish CT2), OpenCV change maps, RapidOCR, Ollama
`qwen2.5vl:7b`, Kokoro via `hyperframes tts`.

### Highlight selection today (`services/highlights/candidates.py`, `workers/analyze.py`)
Sentences from word timings (pause split 0.9 s) → windows of 30–60 s → `score_window` weighted sum: boundary 0.35
(speaker-relative pause percentiles before/after + opener words like "toh", "ab"), length 0.10 (closeness to 45 s or the
learned ideal from `performance_feedback`), voice 0.15 (energy level/variation), pace 0.10, screen 0.15 (typing/screen
change), technical 0.15 (glossary terms + on-screen identifiers that are spoken) → human-readable reasons → "strict" pool
needs both pause ranks ≥ 0.6 (relaxed if < 3 survive) → `select` top-k with ≤ 35 % overlap → local LLM judge (standalone /
educational scores, title, summary) → `highlight_candidates` rows with features, reasons and crop keyframes.
No semantic topic segmentation, no explicit "complete explanation" check and no collections yet (see backlog A/C).

### Captions today
Word-timed caption items in the timeline; `compose.paginate` (maxCharsPerLine/maxLines) → per-word GSAP states. Presets
`highlight-word | karaoke | boxed`, font size, chars/line, position (safeTop/safeBottom), body/code fonts, from brand kits or
the editor; style presets add caption CSS (Energy uppercase/stroke, Story spacing, Signature accent bar + lower third).
SRT/VTT via `services/rendering/captions.py`. The five "personalities" of backlog B do not exist yet.

## 5. Approved backlog — NOT YET IMPLEMENTED OR VERIFIED
`docs/CURRENT_TASK.md` §Backlog: **A** context-aware AI editing, **B** five AI caption personalities (Minimal, Creator,
Cinematic, Learning, Brand) that change the rendered MP4, **C** AI clip collections (a series from one recording with titles
grounded in the lecture). Do not start before the owner's continuation prompt.

## 6. Known issues / unverified
Topic storyboards can still repeat example code (3 of 5 distinct live) · audio fades not checked audibly · future-scheduled
publish not verified · AI feedback not exercised · editor is desktop-first · authenticated page timings on production not
measured · Instagram processing can return a transient ERROR (worker retries) · `next build` while `next dev` runs leaves the
dev server's CSS stale (restart dev with a clean `apps/web/.next`).

## 7. Running state at checkpoint
Production engine via `start-engine.cmd` (:8000 + tunnel + worker, watchdog; logs `%LOCALAPPDATA%\reel-studio\logs`),
logon task registered. Local test stack :8001 (local Supabase in Docker, `upload-owner@test.local`), web dev :3000, Ollama
:11434. Vercel production READY on `b2b1c38` (plus this docs commit).

## 8. Resume after compaction
1. Read this file, `docs/IDE_HANDOFF.md`, `docs/CURRENT_TASK.md`, `AGENTS.md`; run `git status`, `git log --oneline -15`.
2. Engine: `curl http://127.0.0.1:8000/health`; if down, double-click `apps/api/start-engine.cmd`.
3. Implement backlog A → B → C as the owner's prompt specifies; render real MP4s to verify; update docs; commit; push.
