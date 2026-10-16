> **Final-run checkpoint (2026-10-17): read [CHECKPOINT.md](CHECKPOINT.md) first.** Dark UI redesign, style presets, multitrack editor (verified on Mode A and Mode B renders), Instagram disconnect/insights/analytics/AI feedback code are done; Instagram Business OAuth and any real post are pending the owner.

> **Latest checkpoint (2026-10-17, after the Codex handoff): read [CHECKPOINT.md](CHECKPOINT.md) first.** Mode B now works end to end (JSON vs XML → 46.8 s 1080×1920 MP4, plays and downloads in the UI); repeated-code prompt fix not yet re-verified on a new video. Instagram Business OAuth still pending; nothing published. YouTube postponed (D-035). HEAD at checkpoint start: `fe984a0`.

# Reel Studio: final engineering handoff — 2026-10-17

This is the current checkpoint. It supersedes stale status statements in older documents, not the original requirements. The owner stopped new feature work to switch development sessions. Preserve all unfinished work; do not reset the checkout.

## Mission, scope and priorities

Hackathon PS4: technical educators turn recordings into branded portrait reels, or a topic into an approximately 45-second narrated code explainer. Read `ORIGINAL_PS.md`, `MASTER_PROMPT.md` and `MASTER_PROMPT_SUPABASE_ADDENDUM.md` unchanged. Their complete scope still applies.

Owner's revised priority: (1) finish Mode B end to end; (2) substantial professional UI redesign; (3) functional multitrack editor; (4) official Instagram and YouTube publishing/scheduling; (5) real analytics and performance feedback; (6) integrated demo and submission. Billing, complex tiers, admin extras and excessive optimization are postponed. Auth, org RLS, endpoint authorization, upload validation, encrypted tokens and duplicate-post prevention remain mandatory. No paid APIs, hosting upgrades or mandatory billing: ₹0.

## Repository and history

- Only checkout: `C:\dev\Reel-Studio`; old OneDrive copy is obsolete.
- Origin: https://github.com/sahilkarande0918-cmd/Reel-Studio
- Takeover base: `5acd53aa96c6fe6be77f972c11cd14298bf6b5fe`.
- First implementation commit: `7419b774b6c0b2dfbee51a4cc57b60a86469963b`, pushed on `feature/topic-studio`.
- Draft PR: https://github.com/sahilkarande0918-cmd/Reel-Studio/pull/1 (into main).
- At final-checkpoint start, remote main was still `5acd53a`; fetch showed no concurrent changes. Owner explicitly requests final reviewed checkpoint on main. Final verification is appended below after commit/push.
- Use existing human identity `sahilkarande0918-cmd <sahilkarande0918@gmail.com>`. No AI authors, contributors or coauthor trailers. Never rewrite timestamps or force push.

## Architecture retained

Next.js 16 / React / TypeScript / Tailwind frontend on Vercel, Python 3.11 FastAPI and durable local GPU worker, Supabase Auth/Postgres/Realtime Free, large media on local disk. Only Supabase project `adjwycjsxtxvjockxtan` is authorized; never inspect or modify the owner's personal SaaS projects. Microsoft Dev Tunnels provides HTTPS; do not switch to Tailscale or ngrok. Hyperframes 0.8.164 + FFmpeg render locally. Existing Hinglish faster-whisper, RapidOCR, OpenCV and Ollama/Qwen code remains. `packages/timeline-schema` is the sole canonical timeline.

## Phase status (acceptance is separate from code presence)

| Phase | Actual checkpoint state |
| --- | --- |
| 00 Foundation | Existing repository, requirements, team and conventions retained. |
| 01 Auth/deployment | Existing production auth retained. New frontend deployed; API health/JWT gate verified. |
| 02 Ingestion/transcription | Existing synthetic integration evidence retained; prior real 7.5-minute physics recording production upload/transcription evidence exists. Not rerun here. |
| 03 Highlight intelligence | Existing synthetic and prior production physics analysis evidence retained. Real programming-class acceptance remains unverified. |
| 04 Rendering/branding | Existing synthetic MP4, captions and brands retained. New additive compiler supports audio/code/text; new Mode B MP4 not produced. Prior full real production render remains unconfirmed. |
| 05 Mode B | Implemented first pipeline and UI; live LLM test FAILED before narration. Incomplete. |
| 06 Advanced editor | Schema/compiler groundwork only. Full editor not started. |
| 07 Publishing | Instagram implementation and queue UI deployed; OAuth reaches correct app but Business-account authorization incomplete. YouTube not implemented. |
| 08 Analytics/feedback | Instagram metric-fetch worker and UI implemented, no real metrics fetched. AI feedback not started. |
| 09 Submission | Regression/build checks run; integrated demo and submission not complete. |

## Mode B implementation and exact failure

Topic projects can now be created and opened. Topic studio submits authenticated generation jobs, shows real status/storyboard, and can display/download ready render MP4/SRT/VTT. Topic <=500 characters, English only, 30–60-second target, selected audience/tone/difficulty and Kokoro voices. Storyboard is currently read-only, not an editable script approval step.

Backend queues atomically with active-project deduplication. Local Ollama returns structured storyboard; Pydantic validates shape, JSON/XML/Python examples are parsed without execution (XML entities/DTDs rejected). Immutable storyboard/audio caches support retries. Kokoro CLI synthesizes scenes; faster-whisper measures words and alignment rejects missing/unreliable mappings instead of inventing uniform timestamps. Canonical audio/code/caption tracks reuse brand snapshot and Hyperframes renderer. Audio/code/text and multi-caption compiler support are additive to schema version 1.

**Live failure:** after starting the installed Ollama service, a real request for JSON versus XML failed after repair attempts with `ValueError: Local model could not produce a valid storyboard` and Pydantic `Invalid JSON: expected value at line 1 column 1`. Model content was wrapped in ```json fences despite structured-output instructions. No valid storyboard cache, narration, new MP4 or ffprobe success was produced by this run. New strict-xfail regression documents this exact unsupported wrapper; fix the parser or generation response and then remove xfail only after verification. No canned script fallback was added.

Local probe destination was `C:\dev\Reel-Studio\data\modeb-smoke` (ignored). Reproduce via `cached_storyboard(TopicRequest(topic='Explain JSON versus XML using the same small data example', duration_s=45), Path(...))`, then `synthesize_narration`, `build_timeline`, `compose.write_project`; finally exercise the actual generate job/UI and render. Do not start another expensive benchmark just to reproduce this parse failure.

## UI redesign and editor

Shared evergreen/ivory app tokens, typography, sidebar and responsive shell; real dashboard counts/activity/projects; signed project thumbnails; recording player/transcript moved above highlights; working topic-generation form; Publishing and Analytics pages with truthful loading/error/empty states. Four reference screenshots are structural inspiration only, not their branding/colors/people or fabricated numbers.

Publishing page was observed in production, signed in, backend online, zero upcoming posts and Connect Instagram enabled. YouTube says unavailable. Final frontend refinements correct null project activity links, normalize media URLs, enforce configured platforms and show Pydantic validation messages without echoing inputs. Build/lint/types pass. Full responsive visual review remains open.

**Editor:** no full multitrack editing page, track management, split/trim, caption editing, autosave or undo/redo was completed. Existing recording highlight boundary/crop controls remain. Schema supports audio, code, text overlays and measured captions; compiler/export groundwork is not an editor acceptance claim.

## Exact Instagram situation — do not lose this

- Official **Instagram API with Instagram Login**, app **Reel Studio-IG**. No Facebook Login or linked Facebook Page required for this selected connection flow.
- Owner says a separate Professional Business account was created, added as Instagram Tester and invitation accepted. Its username/ID has NOT yet been retrieved or verified by this app.
- Chrome personal session is `@sahil_karande` (observed profile link used `_sahil_karande`). It is NOT authorized for this project. Do not convert, connect or publish to it; do not retrieve its cookies/passwords.
- OAuth from production reached the correct app-labelled Instagram page, but Meta offered personal-to-professional conversion. No conversion or consent was performed. This is an account-session blocker, not evidence that the configured app credentials are absent.
- Owner must press Ctrl+Shift+N or use a separate Chrome profile, manually sign into the Business account at https://www.instagram.com/accounts/login/, then sign into Reel Studio in the SAME isolated session at https://reel-studio-taupe.vercel.app/publishing and click Connect Instagram. Verify displayed Business username before consent. Fresh state lasts 10 minutes; restart Connect if expired. Incognito cannot use the original window's Reel Studio session.
- No actual Reel has been published. A real test post requires explicit owner approval for the chosen video/caption/account, even after successful OAuth.

### Environment (names/presence only; do not print values)

Ignored `C:\dev\Reel-Studio\apps\api\.env`: `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET`, `INSTAGRAM_REDIRECT_URI` present and correctly named. Client ID matched the app-labelled authorization request. Secret value was not validated by successful exchange yet. Redirect exactly `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`. The Meta dashboard session showed a different app, Sahvora Chat, and was left untouched; registered redirect was not independently inspected there.

No Instagram access-token environment variable was found. No manual-token import flow exists; OAuth is the supported path. `TOKEN_ENCRYPTION_KEY` was missing and was generated privately into ignored backend .env; do not regenerate it after storing account credentials. Supabase URL matched the authorized project. Existing credentials were preserved. `INSTAGRAM_API_VERSION` defaults to v24.0.

### Implemented vs tested

Authenticated connect endpoint stores hashed, user/org-bound, single-use state in service-only rows. Authorization requests `instagram_business_basic` and `instagram_business_content_publish`. Callback route removes code/state from URL, exchanges code, obtains long-lived token, fetches profile and granted permissions, encrypts credentials with AES-256-GCM bound to account ID, then sets connected status. Account metadata only is exposed to org members. Renewal occurs on use within seven days of expiry; no daily proactive refresh task exists.

Unit tests verify encryption/account binding, authorization URL and sanitized provider/network errors; HTTPX/httpcore info logs are suppressed to prevent credential-query logging. Database tests verify RLS, state one-use/user binding and denial of client access to secrets. **Actual callback completion, App Secret validity, returned Business username/ID, token expiry and granted scopes remain unverified.** Never mark them verified based solely on implementation.

Publisher validates MP4 (H264/AAC, portrait, duration and size bounds), makes a signed HTTPS URL, probes it without tunnel bypass headers, creates/reuses a Reel container, polls processing, calls publish, saves actual media ID before optional permalink. It runs in durable worker with retries. SQL queues atomically and deduplicates render/account; queued cancel is lock-safe. An ambiguous publish result becomes `needs_review`, preventing unsafe automatic retry. No live container creation, ingestion, publishing or manual reconcile UI has been verified. FPS/audio constraints and platform-specific eligibility need complete review.

**Checkpoint fix:** signed URL keys were previously random per process, so worker-generated URLs would fail API verification. New signing derives a domain-separated key from backend secret configuration, shared by API/worker; unit tests pass. This change is on disk but the already-running API/worker have NOT been restarted since it was made. Restart BOTH together before testing ingestion. Public tunnel can be blocked by this laptop's Fortinet network; verify external fetch independently, without bypassing browser/TLS warnings. Do not claim local preflight proves Meta can fetch it.

## YouTube and analytics

YouTube remains unavailable in config/UI: Google settings fields exist, but no real OAuth exchange, upload, scheduling adapter or Analytics API implementation. Owner has a channel but had not configured Google Cloud.

Setup previously provided: https://console.cloud.google.com/ → free project, do not enable billing → enable YouTube Data API v3 and YouTube Analytics API → Google Auth Platform Branding/Audience External Testing with owner as test user → Web application OAuth client. Redirect `https://reel-studio-taupe.vercel.app/publishing/callback/youtube`; backend-only `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`. Scopes `youtube.upload`, `youtube.readonly`, `yt-analytics.readonly`. Verify current Google verification/test-mode quota restrictions in official docs at implementation time; do not repeat obsolete upload/audit claims unverified. Testing-mode refresh tokens may expire after seven days.

Instagram insights job requests views, reach, accounts_engaged and total_interactions individually, stores actual results and explicit unavailable errors; dashboard displays saved metrics. No metrics were fetched from a real account. Insights permission support needs current official verification: `instagram_business_manage_insights` appeared in research but has NOT been validated/added. Current OAuth only requests basic/publish. Per-media metrics, watch-time analysis and AI performance feedback are outstanding. No fabricated analytics exist.

## Database, deployment and running environment

Two additive migrations applied successfully to verified hosted project: `20261017030000_topic_generations.sql`, `20261017040000_social_publishing.sql`. All new tables have RLS and explicit grants; credentials/state are backend-only. Local migrations were applied directly with Docker psql for testing, so local schema-migration history may not reflect them; do not blindly reapply CREATE TABLE statements. The later change_publication function was also applied locally and tested.

Production https://reel-studio-taupe.vercel.app served commit `7419b77`, Vercel deployment `dpl_DoBakQZ39GcC1tsCJMqChke4Q8Fx` READY, production alias verified. Project `prj_VVWevgFfCwq7LgQauMu1B11RGzua`, team `team_N7gyjjdCHX9K8ifMie5nzuV6`, scope `sahilkarande0918-9163s-projects`, Hobby plan. Connector mutation/read credentials returned 403 for this team; owner authorized local Vercel CLI via device flow and exact Git commit deployment succeeded. Use CLI credentials without exposing them. Final main push may trigger a newer deployment; verify separately before claiming READY.

Python: `C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python.exe`; cwd `C:/dev/Reel-Studio/apps/api`. Start main stack `python.exe -m app.serve --tunnel devtunnel`. Hidden launcher PID105560, API Python child108200, tunnel105552, worker launcher109340/child109368 at checkpoint. Existing separate port8001 stack (36804/36976; workers34684/34676) left alone; inspect current PIDs/config before stopping anything. Ollama `serve` PID115084 started for live test. PIDs are snapshots, not safe future kill targets.

Main API health 200; unauthenticated /social/config 401. At restart no connected accounts and no publication rows. Last backend process restart preceded shared-signing fix. Logs `apps/api/serve-local*.log`, `ollama-local*.log` are ignored. Original large media/models are under `C:/Users/Sahil/AppData/Local/reel-studio/data`, cache/models under user home, not Git. Local GPU must remain on for scheduled tasks.

## Verification ledger

| Check | Actual result |
| --- | --- |
| Final backend pytest | 76 passed, 6 integration skipped, 1 strict expected failure (fenced JSON), 1 upstream AnyIO deprecation warning |
| Ruff | Pass |
| Frontend lint/types | Passed before final handoff; final rerun recorded below |
| Direct Next build | Passed after final frontend fixes, 16 pages including publishing/callback and analytics |
| Timeline Vitest | 9 passed; final rerun recorded below |
| Frontend API error tests | 4 passed in frontend review; final rerun below |
| Local pgTAP | 52 passed, includes state replay, secret isolation, duplicate queue, outsider cancel, uncertain publish blocks retry |
| Local DB lint | Earlier clean; no later schema change after tested cancel/retry function |
| Secret scan | Staged initial commit compared against configured secret values: PASS; final staging scan below |
| Live Mode B | FAILED on Markdown-wrapped JSON before TTS; no new MP4/ffprobe output |
| Live Instagram | Correct app reached; personal session unsuitable; no token/account connected |
| Real publish / insights / YouTube | Not run; not verified |

Some earlier escalated commands were blocked by approval-review usage quota (not an unsafe-action determination); subsequent authorized handoff commands worked. One incomplete Vercel request was rejected by automatic review because target/source were unspecified; corrected exact project/commit deployment later succeeded. No rejected action was bypassed.

## Exact next work, in order

1. Read this checkpoint, inspect Git and running processes, verify final main deployment. No assumptions based on stale Phase04 headers.
2. Fix live Mode B fenced-JSON parsing/repair while retaining strict schema and syntax validation. Run actual local narration/alignment and a genuine JSON-versus-XML render, ffprobe it, inspect frames/captions and play/download in UI. No success claim until complete.
3. Continue coherent UI; build real canonical multitrack editor (trim/split, audio/text/captions, synchronized preview, undo/redo/autosave, re-render).
4. In parallel only when owner ready, complete Business-account OAuth in isolated session. Verify identity/scopes/expiry via official API, not personal account. Restart main API and worker for shared signing before media-ingest testing. Ask before any real post.
5. Verify publishing errors/retries against actual authorized account, finish proactive renewal/permission handling and supported insights; implement YouTube after owner setup.
6. Real analytics/feedback, integrated end-to-end tests and submission evidence. Preserve ₹0 and security invariants.

## File inventory

The following generated inventory lists every changed/new tracked project file since takeover base and its purpose. Ignored secrets, media, dependencies and logs are deliberately excluded.

| File | Purpose |
| --- | --- |
| `apps/api/app/api/publishing.py` | Authenticated project, OAuth or publishing HTTP boundary |
| `apps/api/app/api/social.py` | Authenticated project, OAuth or publishing HTTP boundary |
| `apps/api/app/api/topics.py` | Authenticated project, OAuth or publishing HTTP boundary |
| `apps/api/app/core/config.py` | Backend-only Instagram/Google configuration names |
| `apps/api/app/core/signing.py` | Shared API/worker media-signing key |
| `apps/api/app/main.py` | Register topic/social/publishing routers |
| `apps/api/app/services/generation/__init__.py` | Validated local storyboard, narration, measured captions or timeline construction |
| `apps/api/app/services/generation/models.py` | Validated local storyboard, narration, measured captions or timeline construction |
| `apps/api/app/services/generation/narration.py` | Validated local storyboard, narration, measured captions or timeline construction |
| `apps/api/app/services/generation/storyboard.py` | Validated local storyboard, narration, measured captions or timeline construction |
| `apps/api/app/services/generation/timeline.py` | Validated local storyboard, narration, measured captions or timeline construction |
| `apps/api/app/services/publishing/__init__.py` | Official Instagram adapter, encrypted credentials or token renewal |
| `apps/api/app/services/publishing/accounts.py` | Official Instagram adapter, encrypted credentials or token renewal |
| `apps/api/app/services/publishing/instagram.py` | Official Instagram adapter, encrypted credentials or token renewal |
| `apps/api/app/services/publishing/tokens.py` | Official Instagram adapter, encrypted credentials or token renewal |
| `apps/api/app/services/rendering/captions.py` | Canonical multi-track compiler, validation or caption export |
| `apps/api/app/services/rendering/compose.py` | Canonical multi-track compiler, validation or caption export |
| `apps/api/app/services/rendering/timeline.py` | Canonical multi-track compiler, validation or caption export |
| `apps/api/app/workers/generate.py` | Durable generation/publishing/insights/render job execution |
| `apps/api/app/workers/publish.py` | Durable generation/publishing/insights/render job execution |
| `apps/api/app/workers/render.py` | Durable generation/publishing/insights/render job execution |
| `apps/api/app/workers/run.py` | Durable generation/publishing/insights/render job execution |
| `apps/api/requirements/base.txt` | Declare cryptography runtime dependency |
| `apps/api/tests/test_generation.py` | Backend regression tests, including explicit known Mode B failure |
| `apps/api/tests/test_rendering.py` | Backend regression tests, including explicit known Mode B failure |
| `apps/api/tests/test_signing.py` | Backend regression tests, including explicit known Mode B failure |
| `apps/api/tests/test_social.py` | Backend regression tests, including explicit known Mode B failure |
| `apps/api/tests/test_topic_api.py` | Backend regression tests, including explicit known Mode B failure |
| `apps/web/app/(app)/analytics/page.tsx` | Real stored metrics UI with unavailable states |
| `apps/web/app/(app)/dashboard/page.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/(app)/layout.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/(app)/projects/[id]/page.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/(app)/projects/actions.ts` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/(app)/projects/new-project-form.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/(app)/projects/page.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/(app)/publishing/callback/[provider]/page.tsx` | Account connection, callback, publishing queue UI or API contract |
| `apps/web/app/(app)/publishing/page.tsx` | Account connection, callback, publishing queue UI or API contract |
| `apps/web/app/app-tokens.css` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/app/globals.css` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/components/app/project-preview.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/components/app/sidebar.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/components/publishing/account-connections.tsx` | Account connection, callback, publishing queue UI or API contract |
| `apps/web/components/publishing/analytics-studio.tsx` | Account connection, callback, publishing queue UI or API contract |
| `apps/web/components/publishing/publishing-studio.tsx` | Account connection, callback, publishing queue UI or API contract |
| `apps/web/components/publishing/social-callback.tsx` | Account connection, callback, publishing queue UI or API contract |
| `apps/web/components/studio/recording-studio.tsx` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/components/studio/topic-studio.tsx` | Topic form, job progress, storyboard and export UI |
| `apps/web/lib/api-error.ts` | Safe field-error formatting and focused tests |
| `apps/web/lib/backend.ts` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/lib/social.ts` | Workspace redesign, project routing, real data or backend UI integration |
| `apps/web/tests/api-error.test.mjs` | Safe field-error formatting and focused tests |
| `docs/CODEX_HANDOFF.md` | Current evidence, constraints, decisions and handoff |
| `docs/CODEX_TO_CLAUDE_HANDOFF.md` | Current evidence, constraints, decisions and handoff |
| `docs/CURRENT_TASK.md` | Current evidence, constraints, decisions and handoff |
| `docs/DEPLOYMENT.md` | Current evidence, constraints, decisions and handoff |
| `docs/HANDOFF.md` | Current evidence, constraints, decisions and handoff |
| `docs/PHASES.md` | Current evidence, constraints, decisions and handoff |
| `docs/TEST_STATUS.md` | Current evidence, constraints, decisions and handoff |
| `docs/THIRD_PARTY_LICENSES.md` | Current evidence, constraints, decisions and handoff |
| `packages/timeline-schema/src/index.test.ts` | Canonical audio/code/text schema and generated validation/tests |
| `packages/timeline-schema/src/index.ts` | Canonical audio/code/text schema and generated validation/tests |
| `packages/timeline-schema/timeline.schema.json` | Canonical audio/code/text schema and generated validation/tests |
| `supabase/migrations/20261017030000_topic_generations.sql` | Tenant-isolated generation or secure publishing tables/RPCs |
| `supabase/migrations/20261017040000_social_publishing.sql` | Tenant-isolated generation or secure publishing tables/RPCs |
| `supabase/tests/database/social.test.sql` | RLS, OAuth replay and publishing idempotency database tests |
| `docs/DECISIONS.md` | D-032 local generation, D-033 official Instagram/idempotency, D-034 shared signing |

## Final check results
Final rerun: frontend ESLint and TypeScript passed; timeline 9/9 passed; frontend API-error tests 4/4 passed (Node emits a harmless module-type warning). Backend 76 passed / 6 skipped / 1 strict known xfail; Ruff passed. Next production build already passed with final frontend files. No new feature or GPU benchmark started during handoff. Working changes are checkpoint fixes, regression tests and documentation only.

Local-only state deliberately retained: ignored backend .env and encryption key, frontend .env.local, user CLI authentication, node_modules/.next, Python/model caches, local media/data, ignored service logs and empty failed-probe directory data/modeb-smoke. None should be added to Git. Existing service PIDs remain running as documented; no test video published.

## Verified repository handback

Implementation checkpoint `f144e7b337ee0d712d079529efdaf0c2001c51c7` was committed, main was fast-forwarded from `5acd53aa96c6fe6be77f972c11cd14298bf6b5fe`, and `git push origin main` succeeded. `git ls-remote origin refs/heads/main` returned the identical f144e7b SHA. `git status --porcelain=v1` was empty. PR #1 is MERGED. No conflict, reset, stash, history rewrite or force push occurred. The feature remote still points to the earlier 7419b77; all final work is preserved on main.

66 tracked files changed from takeover base; complete file inventory above. Final staged secret-value scan passed, with zero environment/media/log/key files staged. Original PS/master prompts untouched. Subsequent documentation-only commit records these observations; obtain its exact current local/remote SHA with `git rev-parse HEAD` and `git ls-remote origin refs/heads/main` instead of assuming this embedded checkpoint SHA is HEAD.

Main push triggered production deployment `dpl_J6YEgyj4ro1emy4DGyLYEgDB4Ntw` for f144e7b; first check BUILDING. Prior manually deployed 7419b77 remained READY. A separate earlier branch-preview deployment was ERROR; the successful production deployment/build is not that preview. Check current production state on resume. No remaining source edits or untracked project files were left at that clean-tree check; ignored runtime state remains as listed above.
