> **Reel Studio 2.0 (updated 2026-10-24, session 2) — read first:** `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full approved spec + status map) and `docs/REEL_STUDIO_2_HANDOFF.md` (technical handoff). They supersede the 1.0 status below, which is kept as history. Work folder `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`, repo https://github.com/sahilkarande0918-cmd/Reel-Studio. 2.0 status (second session, HEAD ac322a5+docs): ✅ Mode B web app + AI director, 26 motion templates, 35 effects / 33 transitions + ONNX composites, headless Blender 3D shots, 100 caption presets + ON/OFF, clip collections; 🟡 voice profiles (built, speech not yet synthesised), campaign agent + EN/HI/Hinglish + click/inquiry tracking, Instagram cover/suggestions (nothing published), Phase D/Test B/E/H renders; ⬜ production migrations + Vercel deploy. Next task: handoff §18.

## 2.0 deployment linkage (2026-10-24)
**Always-on engine (session 3):** task "Reel Studio Engine" has a logon trigger plus a trigger repeating every 5 min
(IgnoreNew + the launcher mutex = only restarts a dead launcher), restart-on-failure 999×1 min, no battery stop, no time
limit. The launcher starts Ollama when it is not running, and the public engine asks Windows not to idle-sleep while it
runs (`SetThreadExecutionState`). A closed lid or manual Sleep still takes it offline: keep the laptop plugged in with the
lid open (or set "When I close the lid: Do nothing" for plugged in). Public check: `gh workflow run backend-probe.yml -f url=https://j96sqlp6-8000.inc1.devtunnels.ms` (passed 2026-10-24, CORS allows reel-studio-taupe.vercel.app).
**Latest production deployment:** `dpl_4UBCg8yyma5FXqu1ofa2EsAPZcWa` (commit 0981008); production engine restarted on the same code.
**DEPLOYED (session 3, 2026-10-24):** 7 migrations pushed to `adjwycjsxtxvjockxtan` with `supabase db push --linked` (dry run first; all additive; remote `db lint` clean). Windows task "Reel Studio Engine" now runs `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0\apps\api\start-engine.ps1` (same Dev Tunnel URL; `SITE_URL` added to `.env`). Vercel production deployment `dpl_4vYYDteBdvU3tbBvxQ4HXxwuVTpf` built from Reel-Studio commit 8cf0d62 via the Vercel API (`gitSource` repoId 1431256555), aliased to reel-studio-taupe.vercel.app. The project's Git link still points at the old repo, so redeploy new commits the same way (or relink the repo in the Vercel dashboard). Rollback: redeploy `dpl_EG8TUnJnEjRxVTsWqqfRkPBfUttU` and point the task back at `C:\dev\Reel-Studio`. Live checks: login page renders the same UI; `/r/<unknown>` and `/i/<unknown>` → 404; `/create`, `/campaigns` redirect to login when signed out.
**Session 2 update:** the owner asked to deploy to Vercel last, keeping the same dashboard UI. Not done yet. Order: `next build` → review and `supabase db push` the 7 migrations `20261024100000…20261024160000` to `adjwycjsxtxvjockxtan` → run the 2.0 engine for production from this folder → deploy `apps/web` to project `reel-studio` (prj_VVWevgFfCwq7LgQauMu1B11RGzua, domain reel-studio-taupe.vercel.app) → verify /create, /campaigns, /r, /i. Never publish anything on Instagram while verifying.
Vercel project `reel-studio` is still linked to the old repo `Open_PS04_`; pushes to Reel-Studio do not deploy. The production engine runs from `C:\dev\Reel-Studio` (logon task). Re-pointing either is a deliberate owner decision. Engine on :8000 was not responding at the 2026-10-24 checkpoint; start it with `C:\dev\Reel-Studio\apps\api\start-engine.cmd`. Start Ollama manually after a reboot.

> **Pre-compaction checkpoint (2026-10-17): read [CHECKPOINT.md](CHECKPOINT.md) first.** Latest: homepage + 61 s Hyperframes tour, sin1 speed pass, Topic JSON import, Instagram delivery copy, silent-render guard, self-restarting engine (HEAD `b2b1c38` + docs). Backlog A/B/C (context-aware editing, caption personalities, clip collections) is NOT implemented.

> **Latest checkpoint (2026-10-17, after the Codex handoff): read [CHECKPOINT.md](CHECKPOINT.md) first.** Mode B now works end to end (JSON vs XML → 46.8 s 1080×1920 MP4, plays and downloads in the UI); repeated-code prompt fix not yet re-verified on a new video. Instagram Business OAuth still pending; nothing published. YouTube postponed (D-035). HEAD at checkpoint start: `fe984a0`.

> **Final checkpoint (2026-10-17):** Read [CODEX_TO_CLAUDE_HANDOFF.md](CODEX_TO_CLAUDE_HANDOFF.md) first. It supersedes historical status below. Mode B pipeline/UI implemented but live generation fails on fenced model JSON; full editor and YouTube unfinished. Instagram reaches Reel Studio-IG but awaits the separate Business-account login/consent. Never connect/convert the personal account or publish without explicit approval. Production deployed at 7419b77; two new migrations applied. Final backend: 76 pass, 6 skip, 1 known xfail; DB: 52 pass; final frontend build passes. Owner requested checkpoint only, no more features.
# Deployment

_Verified 2026-10-17 (session 2, after the owner's first push). This file is the single source of truth for deployment state._

## Current state
| Piece | State | Evidence |
|-------|-------|----------|
| Vercel project `reel-studio` (`prj_VVWevgFfCwq7LgQauMu1B11RGzua`) | ✅ Git-connected to `main`, auto-deploys on push | session 1: `dpl_8kA8nFpH…` READY |
| Production URL | https://reel-studio-taupe.vercel.app | |
| Public routes | ✅ `/`, `/login`, `/signup` → 200 | curl, session 2 |
| Protected routes | ✅ `/dashboard`, `/projects` → 307 `/login?next=…` | curl, session 2 |
| Vercel env vars | ✅ set by owner (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SITE_URL`) | values not readable by the assistant |
| Supabase CLI link | ✅ `adjwycjsxtxvjockxtan` (project "reel.studio'org", org `yqdlgjynocbxxsmzeesy`) | `supabase/.temp/project-ref` |
| Remote migrations | ✅ 7/7 applied (`20261017010000_brand_kits` pushed by the assistant on the owner's instruction, 2026-10-17) | `supabase migration list --linked` |
| `brand_kits` on production | ✅ RLS on; `authenticated` select/insert/update/delete only; backend (service_role) reads it; `anon` has no table grants (schema USAGE only) | schema dump |
| Remote schema | ✅ 15 tables, RLS enabled on all 15 | `supabase db dump --linked --schema public,private` (read-only) |
| Remote grants (anon/authenticated) | ✅ fixed: `anon` 0 table grants; `authenticated` 24 explicit grants, none with TRUNCATE (the earlier anon-TRUNCATE hole on 6 tables is closed) | dump after the push |
| Remote grants (service_role) | ✅ DML on all tables + EXECUTE on `claim_next_job` / `requeue_stale_jobs` (`20261017000000`); the project uses Supabase's secure-by-default privileges | backend reads/writes; RPC calls succeed; no worker poll failures after 00:16:42 |
| Remote Auth URL config / email confirmation | ⬜ not verified (needs dashboard) | |
| Public backend tunnel | ✅ Microsoft Dev Tunnels, stable URL `https://j96sqlp6-8000.inc1.devtunnels.ms` | external probes 200; `backend-probe` workflow passed |
| Backend data source | ✅ production: `apps/api/.env` → `https://adjwycjsxtxvjockxtan.supabase.co`; `app.serve --tunnel devtunnel` running | `/health` 200 |
| Production heartbeat | ✅ `backend_endpoints.primary` = `https://j96sqlp6-8000.inc1.devtunnels.ms`, refreshed every few seconds | service-client read (age 7 s) |
| Tunnel against the production backend | ✅ external `/health` 200 (DE, KZ, RU); `backend-probe` run 38950101996 all steps green | check-host.net; GitHub Actions |
| Production Auth | ✅ signup enabled · ⚠️ email confirmation ON (`mailer_autoconfirm: false`): the built-in mailer reaches only members of the Supabase org | `GET /auth/v1/settings` |
| Production signup → confirm → onboarding | ✅ (owner, 2026-10-17): 1 confirmed user, profile from trigger, workspace "Sahil Karande" with owner membership and `organization.created` audit event | service-client read (emails masked) |
| Production project + upload + processing | ✅ (owner, 2026-10-17): project created and persisted after refresh; 75.3 MB / 449.9 s 1080p recording uploaded in 8 MiB chunks, ffprobed, `transcribe` and `analyze` jobs succeeded on attempt 1 on the local GPU; 1,689 words, 6 highlights | production rows + worker log |
| Second-account RLS on production | ⬜ needs a second account (built-in mailer only reaches Supabase-org members) | |
| Vercel `NEXT_PUBLIC_SUPABASE_URL` value | ✅ corrected by owner to `https://adjwycjsxtxvjockxtan.supabase.co` (was the REST endpoint (`…supabase.co/rest/v1/`), so signup failed with "Invalid path specified in request URL" (PostgREST PGRST125, reproduced) | owner screenshot 2026-10-17; fixed in code by `lib/supabase/env.ts` (origin only); owner should still set it to `https://adjwycjsxtxvjockxtan.supabase.co` |
| Production ↔ backend with a real session | ⬜ owner E2E (step 5): needs a signed-in user, which the assistant may not create on a non-local site | |

## Owner actions, in order
1. **Apply migrations** (terminal, from `C:\dev\Reel-Studio`; the DB password is asked for in the terminal, never in chat):
   ```
   pnpm exec supabase db push --linked
   ```
   Always run it from `C:\dev\Reel-Studio`; the OneDrive folder `Reel Studio` is a stale copy. Next pending: `20261017000000_service_role_rpcs` (backend DML + worker RPC grants). Confirm with `pnpm exec supabase migration list --linked`, where every row needs a remote timestamp.
2. **Auth → URL Configuration** (Reel-Studio dashboard; may need the Owner account): Site URL `https://reel-studio-taupe.vercel.app`; Redirect URLs `https://reel-studio-taupe.vercel.app/**` and `http://localhost:3000/**`.
3. **Email confirmation** (decision for the owner): with confirmation on, Supabase's built-in mailer only delivers to the project team's addresses at a low hourly rate, so judges cannot sign up. The options:
   - (a) Keep it on and demo with team accounts.
   - (b) Add free SMTP (e.g. Brevo or Resend free tier) so confirmations reach anyone.
   - (c) Turn "Confirm email" off for the demo. Anyone can then register any address without proving they own it (spam accounts, typo'd emails, no recovery guarantee), but RLS still isolates every account's data.

   Recommended: (b) if time allows, else (c) for the judging window only.
4. **Switch the backend to production**: in `C:\dev\Reel-Studio\apps\api\.env` (git-ignored, this machine only; save the file) set `SUPABASE_URL=https://adjwycjsxtxvjockxtan.supabase.co` and `SUPABASE_SECRET_KEY=` the Reel-Studio **secret** key (Project Settings → API Keys). Type it into the file yourself; never paste it into chat. `ALLOWED_ORIGINS` already includes the Vercel domain. Restart the backend (below).
5. **Test on production** (the assistant cannot enter passwords or create accounts on a non-local site):
   - sign up, then log in and log out;
   - create a workspace and a project, then refresh and check the project persists;
   - check the backend badge reads "online";
   - upload a short clip.

   For the RLS check, use a second account in another browser: it must not see the first account's project.
6. Ask teammate `Atharva486dherange` to accept the GitHub invitation.

## Frontend — Vercel Hobby
- Root Directory `apps/web`, framework Next.js, Node 24.x, install `pnpm install`.
- Env vars are inlined at build time → redeploy after changing them.
- Hobby may refuse Git-triggered deploys for commits authored by someone other than the project owner; the owner then redeploys from the dashboard. Never spoof authors.

## Local processing backend
```
cd C:\dev\Reel-Studio\apps\api
C:\Users\Sahil\AppData\Local\reel-studio\venv\Scripts\python -m app.serve --tunnel devtunnel   # API + worker + public tunnel (use this)
C:\Users\Sahil\AppData\Local\reel-studio\venv\Scripts\python -m app.serve --tunnel none        # local only
```
`--tunnel cloudflare` and `--tunnel tailscale` remain in the launcher for other networks; both fail on the current one (D-024).

## Tunnel: Microsoft Dev Tunnels (D-024)
- One-time setup (done 2026-10-16): `winget install Microsoft.devtunnel`, then `devtunnel user login -g -d` (GitHub device code, account `sahilkarande0918-cmd`). The launcher creates the persistent tunnel `reel-studio` with anonymous relay access and port 8000 on first run. The URL is stable, and the tunnel expires after 30 days of inactivity.
- Free limits: 5 GB/month bandwidth per user, **16 MB max request body** (uploads use 8 MiB chunks), 20 MB/s, 1,500 requests/min per port. A 1 GB lecture upload uses 1 GB of the monthly 5 GB.
- Security: anonymous relay access is required for browsers. Every processing route needs a Supabase JWT plus an org-role check. Media and downloads use 6-hour HMAC-signed URLs. CORS is restricted to `ALLOWED_ORIGINS`. Uploads are capped at 4 GB and ffprobe-validated.
- Browsers get an HTML warning page only on direct navigation. API calls send `X-Tunnel-Skip-AntiPhishing-Page`, `<video>` requests are not intercepted (verified), and downloads use fetch + blob.
- **This network intercepts `*.devtunnels.ms` too.** A browser on the owner's network falls back to `http://127.0.0.1:8000`, which works only on the machine running the backend; Chrome may ask once for local-network access. Judges on other networks use the tunnel. To check from outside: `gh workflow run backend-probe.yml -f url=<tunnel url>`.

## Tailscale (diagnosed 2026-10-16)
Installed (1.104.1), service running, CLI at `C:\Program Files\Tailscale\tailscale.exe`, but **logged out** (`NeedsLogin`). Login cannot complete on this network: Fortinet presents an untrusted certificate for `controlplane.tailscale.com` and blocks the DERP relays (Tailscale's own health message says so). Nothing is wrong with the install. On an unfiltered network (e.g. a phone hotspot), `tailscale up` → approve in the browser → enable Funnel for the node → `python -m app.serve --tunnel tailscale` would also work.

## Known limitations
- Heavy processing (ASR, OCR, LLM, rendering) only runs while the owner's machine, API, worker and tunnel are up; the UI shows a truthful offline state otherwise.
- Renders are self-contained (bundled GSAP and fonts); the processing machine needs internet only for the tunnel and Supabase.

## Active checkpoint — 2026-10-17: topic studio and Instagram integration

Branch: `feature/topic-studio`. Added local topic generation (Ollama → validated storyboard → Kokoro → measured captions → canonical timeline → Hyperframes), refreshed studio UI, and authenticated Instagram Login/publishing/insights screens and worker handlers. These are implemented slices, not completed phase acceptance.

Instagram env presence verified without values: client ID numeric, secret present, exact callback `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`, backend encryption key present. No manual test token. Actual account authorization, Meta registered redirect acceptance, scopes and token validity remain unverified until OAuth consent. Never publish a real test Reel without the owner's specific approval.

Both migrations `20261017030000_topic_generations.sql` and `20261017040000_social_publishing.sql` applied only to verified project `adjwycjsxtxvjockxtan`. API/tunnel/worker restarted; local health 200 and unauthenticated social route 401. Zero connected accounts and zero publication rows at restart. Port-8001 local test stack was left untouched.

Verified: backend 74 passed / 6 integration tests skipped (one upstream deprecation warning), Ruff clean; workspace lint and typecheck pass; timeline 9 tests pass; direct Next production build passes including publishing callback. Earlier local database suite: 47 pgTAP tests pass and schema lint clean; the later change_publication RPC has not yet been exercised locally. No new live Mode B MP4, Instagram OAuth, real publish, or real analytics retrieval has been verified. Frontend deployment pending this checkpoint.

Next: deploy callback/UI, finish authorized Instagram OAuth, verify public media ingestion without publishing, exercise scheduling failure/retry/idempotency, render and inspect a genuine topic video. Phase 06 full editor, Google OAuth/upload, analytics feedback and final end-to-end acceptance remain outstanding. Keep Google credentials private in backend .env. OAuth tokens are encrypted in backend-only database rows, never frontend storage.

### Final main handback
Main f144e7b337ee0d712d079529efdaf0c2001c51c7 pushed and remotely verified. Production build dpl_J6YEgyj4ro1emy4DGyLYEgDB4Ntw triggered (BUILDING at first check); previous 7419b77 production READY. API remains running with pre-shared-signing-fix imports; restart API and worker together before actual media ingest. See CODEX_TO_CLAUDE_HANDOFF.md for exact process/environment evidence.

## Runtime at checkpoint (2026-10-17)
Vercel deployment for `fe984a0`: success; `/` 200, `/login` 200, `/dashboard` 307. Production backend :8000 (`app.serve --tunnel devtunnel`) restarted with `fe984a0`, heartbeat fresh at `https://j96sqlp6-8000.inc1.devtunnels.ms`. Local test backend :8001 (local Supabase), web dev :3000 and Ollama serve running. Supabase migrations through `20261017040000_social_publishing` applied (Codex).

## Runtime at IDE switch (2026-10-17)
Vercel production READY on `main` (auto-deploy). Supabase `adjwycjsxtxvjockxtan` migrations through `20261017050000` applied.
Production backend `python -m app.serve --tunnel devtunnel` (:8000 → https://j96sqlp6-8000.inc1.devtunnels.ms) restarted on
`af7b676`-era backend code (no backend changes since). Instagram app "Reel Studio-IG": client ID = Instagram app ID, redirect
`https://reel-studio-taupe.vercel.app/publishing/callback/instagram` registered in Business login settings. Connected account
@career.with.purpose (token encrypted, expires 2026-12-15; renewed automatically within 7 days of expiry when used).

## Homepage media (2026-10-17)
`apps/web/public/landing/` holds the tour (`reel-studio-tour.mp4` 17.3 MB + `.vtt` + poster), two short reel loops and
stills; served statically by Vercel (verified video/mp4 with byte ranges). `proxy.ts` excludes these from the auth redirect.

## Keeping the engine on (2026-10-17)
Start the processing engine with `apps/api/start-engine.cmd` (double-click), not from an editor/agent terminal: it runs
hidden, independent of any session, restarts the whole engine 5 s after it stops, and refuses to start a second copy.
Inside, `app.serve` now restarts a crashed tunnel or worker within 10 s (watchdog). Log:
`%LOCALAPPDATA%
eel-studio\logs\engine.log`. The engine still needs the laptop awake and online; set Windows to never
sleep while plugged in during demos. Auto-start at login is optional (Task Scheduler → run `start-engine.cmd` at log on).
