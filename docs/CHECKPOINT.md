# Reel Studio 2.0 — read this first (updated 2026-10-24, session 2)
- **Session 2 (commits 40c090b, e7a7805, 86306f4, ac322a5 + checkpoint docs):** Mode B web app + AI director, motion templates, effects/composites, Blender 3D worker + MCP config, 100 caption presets, collections, campaign agent + tracking, voice profiles (not yet run), Instagram cover/suggestions (nothing published). Status map: master plan Part 1. Next task: handoff §18.
- **Authoritative now:** `docs/REEL_STUDIO_2_MASTER_PLAN.md` (spec + status map) and `docs/REEL_STUDIO_2_HANDOFF.md`.
- Since 2026-10-23: owner phonk reel from 17 clips + phonk audio in Reference 4 style (all QA checks pass), reference style transfer, measured QA module, frame-exact transitions, relative drop detection (HEAD `de9729a` + checkpoint docs).
- Repository: https://github.com/sahilkarande0918-cmd/Reel-Studio (migrated with full history, verified: `docs/MIGRATION.md`).
  Work folder: `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`. The old folder `C:\dev\Reel-Studio` now points at the
  renamed original repo `Open_PS04_` and still runs the production engine and Vercel deployment (not yet re-pointed).
- Plan and phase status: `docs/ROADMAP_2.md`. Research: `docs/REFERENCE_STYLE_ANALYSIS.md`, `docs/OPEN_SOURCE_TOOL_AUDIT.md`.
- Built so far (verified): reference analyzer, beat analysis (±3 BPM on 95–150 BPM tests), 24 effects + 21 transitions
  (each measured to change the picture), beat planner, synthesized score/SFX, separate audio mix (−14 LUFS, ≤ −1.5 dBTP),
  first end-to-end 16 s two-clip phonk edit (exactly 480 frames). Not built yet: Mode B UI/API/ingestion tables,
  Hyperframes motion templates, AI Director, voice profiles, 100 caption styles, collections, campaigns, QA engine.
- Ollama does not auto-start after a reboot; start it (`ollama serve`) before LLM stages.

---

# Reel Studio — checkpoint (2026-10-17, after Feature A)

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
| Context-aware AI editing (Feature A) | ✅ lecture outline (LLM teaching steps + topics), five-component NN/100 score, grounded explanations, Create reel; verified on the owner's real physics class + rendered MP4 |
| Shared logo | ✅ landing Aperture mark used on sign-in pages and inside the app |
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

### Highlight selection today (`services/highlights/outline.py`, `candidates.py`, `llm.py`, `workers/analyze.py`)
Sentences (pause split 0.9 s) → **lecture outline**: local LLM splits timed sentences into teaching steps (kind + title)
grouped into topics, 150-sentence chunks, repaired to a gap-free cover, steps > 60 s split at the strongest boundary,
cached per transcript (`outline.json`); lexical fallback if the LLM is offline → every 30–60 s window (never opening on
filler) scored by **context 35 / educational 25 / opening 15 / ending 15 / engagement 10** → de-dup (overlap, same core
step, ≥ 55 % shared words) → local LLM judge with outline + before/after context (blended into context/educational) →
rows with `features.context` (steps, complete, opens/ends quotes, limitation) and `features.components`; job result holds
the outline and a limitation message when no complete explanation fits. UI shows NN/100, explanation, breakdown, outline.
Known: a 7B model's segmentation varies between runs (cached after the first run); scores on the physics class are
64–67/100 because the LLM judged no clip fully standalone.

### Captions today
Word-timed caption items in the timeline; `compose.paginate` (maxCharsPerLine/maxLines) → per-word GSAP states. Presets
`highlight-word | karaoke | boxed`, font size, chars/line, position (safeTop/safeBottom), body/code fonts, from brand kits or
the editor; style presets add caption CSS (Energy uppercase/stroke, Story spacing, Signature accent bar + lower third).
SRT/VTT via `services/rendering/captions.py`. The five "personalities" of backlog B do not exist yet.

## 5. Approved backlog
**A** context-aware AI editing — ✅ done (2026-10-17, `docs/CURRENT_TASK.md`). **B** five AI caption personalities and **C** AI
clip collections — approved, NOT implemented, postponed until the owner explicitly asks.

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
3. Wait for the owner's next instruction (B/C only when asked); render real MP4s to verify any change; update docs; commit; push.
