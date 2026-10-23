# AGENTS.md — Reel Studio engineering rules

> **Reel Studio 2.0 — start here instead:** `docs/REEL_STUDIO_2_MASTER_PLAN.md`, then `docs/REEL_STUDIO_2_HANDOFF.md` (standalone; next task in §18). Never publish anything on Instagram (owner, 2026-10-24). Work only in `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0` (repo Reel-Studio). Commits only as `sahilkarande0918-cmd`; never AI authors, co-authors or `Co-Authored-By` trailers.
>
> (1.0) **Start here:** read `docs/IDE_HANDOFF.md` (complete current state, rules, commands, next task), then `docs/CHECKPOINT.md`.
> Never publish a real Reel without the owner's explicit approval of account, video and caption. YouTube is postponed.
> Feature A (context-aware AI editing) is done and verified. Features B (caption personalities) and C (clip collections) are approved but postponed until the owner asks.

Applies to any coding agent or human working in this repository. `CLAUDE.md` holds the full
session workflow; this file holds the shared engineering rules (no conflicting duplicates).

## Attribution
- Team: `sahilkarande0918-cmd`, `sahillokhande5841-cmyk`, `Atharva486dherange`, `SK999CodingWorld`.
- Never add an AI/agent/bot as author, co-author, contributor or team member. No `Co-Authored-By` trailers.
- Commit only under your own real git identity.

## Cost
Everything must run at ₹0. No paid APIs, cloud rendering, paid hosting or billing upgrades.

## Code
- Prefer existing code, stdlib and installed dependencies before adding anything new.
- New dependency → add it to `docs/THIRD_PARTY_LICENSES.md` with license.
- One canonical timeline format (`packages/timeline-schema`). Do not invent parallel formats.
- Long work (transcription, analysis, rendering, publishing) runs in the worker and returns a job id. Never in a request handler.
- Never build shell strings for FFmpeg; pass argument lists (`subprocess.run([...])`).
- Never execute uploaded or generated code outside a sandboxed validator.
- Validate every input at trust boundaries (uploads, OAuth redirects, API payloads).

## Security
- Supabase RLS on every exposed table; org membership enforced. Never disable RLS.
- Secret/service keys only on the backend. OAuth tokens encrypted at rest.
- Local backend endpoints require a valid Supabase JWT.

## Truthfulness
- No decorative controls. Unavailable features say so.
- Heuristic scores are labelled heuristic. Synthetic analytics are labelled synthetic.
- Never claim tests passed without running them; record results in `docs/TEST_STATUS.md`.

## Workflow
- Branches `feature/<name>` / `fix/<name>`, PRs into `main`, conventional commits.
- Run lint, typecheck and tests before pushing. Don't force-push shared branches.

## Codex sprint handoff (2026-10-17)
When Codex takes over, first read `docs/CODEX_HANDOFF.md`, plus the original PS and full master prompt as described there. That document is a **priority overlay**, not permission to remove auth/RLS, fake successful posts or replace real tests with UI mockups. Keep actual human authorship; no AI attribution in team/commit metadata. Read actual repository status before acting, as Claude and Codex may work on the same branch at different times.
