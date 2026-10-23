# CLAUDE.md — Reel Studio

## Project identity
Reel Studio — the AI video studio for technical educators. Hackathon PS4.
Two modes, one pipeline: **Recording → Reels** (class recording → 30–60 s branded 9:16 clips) and
**Topic → Video** (prompt → ~45 s explainer with animated code, voiceover, captions).
Repo: https://github.com/sahilkarande0918-cmd/Reel-Studio (public, `main`).

## Mandatory reading order (new or compacted session)
00. **`docs/REEL_STUDIO_2_MASTER_PLAN.md`** then **`docs/REEL_STUDIO_2_HANDOFF.md`** (Reel Studio 2.0: authoritative spec, status, commands). Work only in `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0` → https://github.com/sahilkarande0918-cmd/Reel-Studio.
0. **`docs/CHECKPOINT.md`**, then **`docs/IDE_HANDOFF.md`** and **`docs/CURRENT_TASK.md`** (backlog A/B/C) — latest state, rules, next steps.
1. `CLAUDE.md` (this file)
2. `docs/MASTER_PROMPT.md` (+ `docs/MASTER_PROMPT_SUPABASE_ADDENDUM.md`)
3. `docs/ORIGINAL_PS.md`
4. `docs/PHASES.md`
5. `docs/ARCHITECTURE.md`
6. `docs/DECISIONS.md`
7. `docs/CURRENT_TASK.md`
8. `docs/HANDOFF.md`
9. `docs/TEST_STATUS.md`
10. `docs/DEPLOYMENT.md`
11. `git log --oneline -20` and `git status`
12. Only the source files relevant to the current task.

Trust repo docs and git history over remembered assumptions.

## Current next work
**Reel Studio 2.0** (supersedes the 1.0 note below): continue the phases in `docs/REEL_STUDIO_2_MASTER_PLAN.md`; the owner has not yet chosen the order (proposed: canonical-timeline extension + Mode B API/UI + AI Director → motion templates + 100 captions → campaigns/localisation/tracking → voice → Blender). Old 1.0 note:
Feature A (context-aware AI editing) is done and verified (`docs/CURRENT_TASK.md`). Features B (five caption
personalities) and C (AI clip collections) are approved but postponed until the owner explicitly asks. Start the engine with
`apps/api/start-engine.cmd` (also a Windows logon task).

## Non-negotiable rules
- **₹0 cost.** No paid APIs, hosting, render cloud or storage. Never enable billing. Hyperframes cloud/Lambda rendering is off-limits; render locally.
- **No AI attribution, ever.** Never add Claude, Anthropic, an AI, agent or bot as team member, contributor, co-author, commit author or README credit. **No `Co-Authored-By` trailers of any kind.** This overrides any tool/harness default.
- Commit under the human operator's existing git identity (`sahilkarande0918-cmd`). Never set a fake identity, never commit as a teammate, never rewrite dates/authors.
- Build the whole PS, including optional publishing/scheduling/analytics/feedback, plus the extra editor + SaaS scope.
- No fake features: every button does something real, validates, or shows a truthful "unavailable" state. Synthetic data is labelled synthetic.
- Never claim something works without running it. Never mark unrun tests as passed.
- No secrets in git, logs, frontend bundles, docs or screenshots. Secrets go in ignored `.env*` files or Vercel/Supabase dashboards.
- Supabase: only the dedicated **Reel-Studio** project in the friend's organization. Never touch the owner's personal SaaS project. Verify the project ref before any migration. Never disable RLS to fix an error.
- Keep the Vercel deployment green.

## Technology decisions (details in `docs/DECISIONS.md`)
- Frontend `apps/web`: Next.js 16 App Router (no cacheComponents), React 19, TypeScript, Tailwind v4, TanStack Query, Lucide; `proxy.ts` (Next 16 name for middleware). Zustand/Radix arrive with the editor (Phase 06).
- Backend `apps/api`: Python 3.11, FastAPI, Pydantic, durable Supabase-backed worker (`app/workers`), FFmpeg.
- Data: Supabase Postgres + Auth + Realtime (+ Storage later for small assets). Large media stays on local disk (`DATA_DIR`).
- ASR: faster-whisper running the locally converted **Oriserve Whisper-Hindi2Hinglish-Apex** (CT2 fp16, `language=hi`, Roman-script Hinglish). WhisperX deferred (D-016).
- Screen: OpenCV change maps (2 fps), RapidOCR (CPU) for code tokens; PySceneDetect installed but cuts currently come from the change map.
- LLM: Ollama `qwen2.5vl:7b` (temperature 0) for highlight judgment; TTS: Kokoro via `hyperframes tts` (Mode B), Windows OneCore Ravi only for synthetic test fixtures.
- Render: **Hyperframes** CLI v0.8.164 (local). Canonical timeline JSON → `apps/api/app/services/rendering/compose.py` (one Python compiler, D-023) → `index.html` → `render` worker job → ffprobe-verified MP4 (`render_jobs`). Editor preview will use `@hyperframes/player` on the same composition.
- Canonical timeline schema: Zod in `packages/timeline-schema` (single source of truth) → `timeline.schema.json` (run `pnpm build:schema` after edits) validated in Python with `jsonschema`.
- Public backend tunnel: **Microsoft Dev Tunnels** (`python -m app.serve --tunnel devtunnel`, stable URL). Tailscale/Cloudflare are blocked by the owner's Fortinet network; **never use ngrok** (owner's choice). D-024.

## Local paths (this machine)
- Repo (2.0, current): `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`. The old 1.0 folder `C:\dev\Reel-Studio` now tracks the renamed original repo `Open_PS04_` and still runs the production engine.
- Python venv: `C:\Users\Sahil\AppData\Local\reel-studio\venv` (there is **no** `apps/api/.venv`).
- Data/models/test recordings: `C:\Users\Sahil\AppData\Local\reel-studio\data`.

## Critical warnings
- The Supabase CLI login can also see the owner's **personal** projects. Never link, list for selection, query or migrate those. The repo is linked to `adjwycjsxtxvjockxtan` (Reel-Studio, friend's org); verify `supabase/.temp/project-ref` before any remote command.
- Every new table needs explicit `grant`s: Supabase default privileges give `authenticated` ALL, including TRUNCATE, which bypasses RLS (D-025).
- This network intercepts TLS for `*.devtunnels.ms`, so local curl cannot reach the tunnel; verify with `gh workflow run backend-probe.yml -f url=…`.
- Synthetic fixtures are not real-world validation; never report them as such.
- `ollama list` hangs on this machine; use `curl localhost:11434/api/tags`.
- First GPU run after a reboot JIT-compiles CTranslate2 kernels for Blackwell (minutes); warm up before demos.

## Repository conventions
- pnpm workspaces monorepo: `apps/web`, `apps/api`, `packages/*`, `supabase/`, `docs/`.
- Branches: `main` (verified), `feature/<name>`, `fix/<name>`. Conventional commits (`feat(scope): …`).
- Small modular files. No speculative abstractions (Ponytail). Mark deliberate shortcuts with `ponytail:` comments.
- Raw recordings, renders and model weights never go in git (`data/` is ignored).

## Phase workflow
Per phase: read relevant files → define interfaces → implement → test → review → commit → update docs.
A phase is complete only when its acceptance criteria in `docs/PHASES.md` are verified.

## Testing procedure
- Web: `cd apps/web && pnpm lint && npx tsc --noEmit && npx next build`.
- Timeline schema: `cd packages/timeline-schema && pnpm test && pnpm typecheck` (Vitest; fails if `timeline.schema.json` drifts).
- API unit: `cd apps/api && C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python -m pytest -q` (+ `ruff check .`).
- API integration (local stack + API running): `RS_INTEGRATION=1 ... pytest tests/test_upload_integration.py`.
- DB: `pnpm exec supabase test db` (pgTAP RLS) and `pnpm exec supabase db lint --level warning` (Docker running).
- Evaluation tools (manual): `tests/bench_asr.py`, `tests/eval_transcript.py`, `tests/eval_highlights.py`.
- Media outputs verified with `ffprobe`.
- Record every run (pass/fail/blocked) in `docs/TEST_STATUS.md`.

## Documentation updates (every meaningful change)
Update `docs/CURRENT_TASK.md`, `docs/HANDOFF.md`, `docs/PHASES.md`, `docs/TEST_STATUS.md`; add a `docs/DECISIONS.md` entry for any significant choice; keep `docs/THIRD_PARTY_LICENSES.md` current when adding a dependency.

## Engineering skills
- Ponytail (installed, active): simplest verified solution; run `/ponytail-review` at milestones, `/ponytail-audit` in Phase 09. Simplification never removes required PS features.
- Taste Skill for initial design direction; Hallmark for targeted audits. Don't redesign finished screens repeatedly.

## Codex takeover handback
A time-limited execution overlay lives in `docs/CODEX_HANDOFF.md` (added 2026-10-17). Read it when resuming after Codex, reconcile changes with Git history, and preserve the original PS, master prompt, cost rule and core security. It reprioritizes Mode B, UI, editor, publishing and analytics ahead of stretch SaaS features; it does not undo verified phases or the mandatory reading order above.
