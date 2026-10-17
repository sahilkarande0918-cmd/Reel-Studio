> **Pre-compaction checkpoint (2026-10-17): read [CHECKPOINT.md](CHECKPOINT.md) first.** Next: backlog A → B → C below.

## Backlog — approved by the owner, NOT YET IMPLEMENTED OR VERIFIED (start only on the owner's next prompt)
### Feature A — Context-aware AI editing
Upgrade highlight detection (`services/highlights/candidates.py`, `workers/analyze.py`, `services/highlights/llm.py`) so clips
are complete, self-contained educational explanations: semantic context (what concept is being explained and where that
explanation starts/ends), complete sentence boundaries, educational value, strong opening and closing, and explainable
scoring shown to the user (per-component scores + reasons). Reuse the existing local LLM (Ollama) and scoring architecture.
### Feature B — AI caption personalities
Five selectable caption styles — **Minimal, Creator, Cinematic, Learning, Brand** — selectable in the studios and editor and
applied by the compiler (`compose.py`) so they change the actual rendered MP4, not only the preview.
### Feature C — AI clip collections
Group related highlights from one recording into a coherent educational Reel series (ordering, shared theme), with
AI-generated series/episode titles based strictly on the lecture's actual content (transcript), no invented claims.

## Done since IDE switch: homepage redesign + 61 s Hyperframes tour (see IDE_HANDOFF.md top).

## Current task (IDE switch, 2026-10-17)
1. Production E2E in the owner's account: Topic → Generate → Edit → Render → Download.
2. Verify remaining editor controls; fix bugs. 3. Audio fades + final quality check. 4. UI usability/responsiveness pass.
5. Instagram scheduling verification (owner approval required for any real post). 6. AI feedback once ≥3 reels have reach.
7. Final integration testing + hackathon submission materials. YouTube and billing stay postponed; ₹0.

> **Latest checkpoint (2026-10-17, after the Codex handoff): read [CHECKPOINT.md](CHECKPOINT.md) first.** Mode B now works end to end (JSON vs XML → 46.8 s 1080×1920 MP4, plays and downloads in the UI); repeated-code prompt fix not yet re-verified on a new video. Instagram Business OAuth still pending; nothing published. YouTube postponed (D-035). HEAD at checkpoint start: `fe984a0`.

> **Owner priorities from 2026-10-17 (Claude resume after the Codex handoff), superseding earlier priority notes:**
> 1. Phase 05: Topic → Video produces a real downloadable ~45 s MP4 (JSON vs XML).
> 2. UI: finish the professional redesign (reference screenshots are for structure only, not colours or theme).
> 3. Phase 06: functional multitrack editor (trim, split, captions, audio, overlays, preview, undo/redo, autosave, re-render).
> 4. Phase 07: Instagram Business connection, Reel publishing, scheduling and queue.
> 5. Phase 08: real Instagram analytics and AI performance feedback.
> 6. Phase 09: end-to-end testing, fixes and submission.
>
> **Status:** Phase 05 Mode B works end to end via the UI (JSON vs XML → 46.8 s 1080×1920 MP4, TEST_STATUS). Next: UI redesign, then the Phase 06 editor.
>
> **YouTube is postponed** (no OAuth, API setup, Shorts publishing or analytics) until the owner asks. Billing,
> complex admin features and non-essential optimisation are postponed. ORIGINAL_PS.md and MASTER_PROMPT.md are
> unchanged; this is a delivery-order decision (D-035). Keep moving without approval for routine work; ask only
> for account access, credentials, real publishing or other external actions.

> **Final checkpoint (2026-10-17):** Read [CODEX_TO_CLAUDE_HANDOFF.md](CODEX_TO_CLAUDE_HANDOFF.md) first. It supersedes historical status below. Mode B pipeline/UI implemented but live generation fails on fenced model JSON; full editor and YouTube unfinished. Instagram reaches Reel Studio-IG but awaits the separate Business-account login/consent. Never connect/convert the personal account or publish without explicit approval. Production deployed at 7419b77; two new migrations applied. Final backend: 76 pass, 6 skip, 1 known xfail; DB: 52 pass; final frontend build passes. Owner requested checkpoint only, no more features.
# Current task

## Phase 04 — Captions, Branding and Hyperframes MP4 Rendering (in progress)

### Done (session 2, verified on the local stack)
Selected highlight → canonical timeline (`packages/timeline-schema`) → Hyperframes composition → `render`
job → ffprobe-verified 1080×1920 30 fps H.264/AAC MP4 + thumbnail → Export panel with live progress,
inline player and signed download. Crop camera follows keyframes (the preview uses identical geometry).
Word-by-word captions sit in the safe zone with code terms as monospace chips, and `AbortController` is
shown correctly. A render survived a worker crash (attempt 2), and identical requests reuse the cached
render. Evidence: `docs/TEST_STATUS.md` → "Phase 04 — first task".

### Done (session 2, later): brand kits
`brand_kits` table (RLS, explicit grants, one default per org, DB-validated colours/fonts/logo), `/brand`
editor with a live 9:16 preview (intro / clip / outro), kit chooser in the Export panel, snapshot into the
timeline, intro/outro cards, watermark, three caption presets, bundled OFL fonts. Evidence:
TEST_STATUS → "Phase 04 — brand kits". Migration live on production (7/7).

### Done: captions export, timing check, offline GSAP (D-029)

### Done: Phase 04 acceptance review
Balanced caption pages, caption positioning, subtitle-accurate studio preview and the render benchmark
(D-030, D-031). Results: PHASES.md "Phase 04 acceptance review".

### Next task: Phase 05 — Topic → Video (Mode B)
Read `docs/MASTER_PROMPT.md` §11 and §19 Phase 05. First slice: topic form → Ollama outline/script/storyboard
as validated JSON → code examples validated by a parser → Kokoro TTS per scene (`hyperframes tts`) → word timings
from faster-whisper on the TTS audio → canonical timeline with code-typing blocks and captions → the same renderer
and brand kits. Acceptance: "JSON vs XML" → ~45 s MP4 with accurate script, animated code, voiceover and
synced captions.

### Phase 04 acceptance review (original note)
Go through `docs/MASTER_PROMPT.md` Section 19 Phase 04 acceptance line by line against TEST_STATUS evidence; fix gaps (e.g. orphan one-word caption pages such as "hai." after a full page, thumbnail choice), render one highlight on **production** with a production brand kit, then mark Phase 04 and move to Phase 05 (topic → video).

### Captions export and timing check (original plan, done)
1. SRT and VTT export from the caption track (clip clock, page-sized cues), API `GET /renders/{id}/captions.{srt,vtt}` (signed) + Export panel links.
2. Caption timing consistency check: compare word starts with audio onsets (energy rise) inside the clip; report median/max drift on the render row and warn in the UI over a threshold.
3. Vendor GSAP into the render project (copy `gsap.min.js` from a pinned npm install) so renders work offline.
4. Phase 04 acceptance review against `docs/MASTER_PROMPT.md` Section 19, then mark Phase 04.

### Brand kits (original plan, kept for reference)
1. Migration `brand_kits`:
   - Columns: `id`, `organization_id`, `name`, `is_default`, `colors {background, text, accent}`, `fonts {body, code}`, `logo_path`, `handle`, `watermark` (bool + position), `caption_preset`, `intro {enabled, duration_s, title}`, `outro {enabled, duration_s, cta}`, timestamps.
   - RLS: members read; editors write.
   - **Explicit grants** (D-025): select/insert/update/delete only.
   - At most one default per org (partial unique index).
2. Logo upload:
   - Small file (PNG/SVG/JPG ≤ 2 MB), stored on the backend disk under `DATA_DIR/orgs/<org>/brand/` through an API endpoint with role check and content sniffing. A Supabase Storage private bucket is the alternative (≤ 1 GB free); decide with Ponytail.
   - Served via signed URL.
3. Brand editor page `/brand` (sidebar entry):
   - Colour pickers with a contrast check (reuse `brand_ink` logic in TS).
   - Font choice from bundled OFL fonts only (no remote fonts in renders).
   - Logo, handle, watermark, caption preset (2–3 real presets: highlight-word, karaoke underline, boxed), intro/outro toggles.
   - Live 9:16 preview card.
4. Snapshot into the timeline:
   - `timeline.build` takes the org's default brand kit (or the one chosen in the Export panel) and copies it into `doc.brand` (snapshot, so later kit edits do not change old renders).
   - Extend the Zod `Brand` (logo asset, handle, watermark, captionPreset, intro/outro) and run `pnpm build:schema`.
5. Compiler:
   - Logo watermark and handle overlay.
   - Intro/outro as timed segments (or sub-compositions via `data-composition-src`) that extend the composition duration, with the video item offset by the intro length.
   - Caption preset styles.
   - Update `verify()` duration expectations.
6. Tests:
   - Vitest for the schema changes; pytest for brand snapshot + compiler output.
   - pgTAP for `brand_kits` isolation and the single default.
   - One real render with a logo + intro/outro, checked with ffprobe + frames.

### Then (rest of Phase 04)
- SRT/VTT export from the caption track.
- Caption timing consistency check: word times vs audio energy onsets, report drift.
- Vendor GSAP into the render project (offline renders).
- Thumbnail choice.
- Phase 04 acceptance per `docs/MASTER_PROMPT.md` Section 19.

## Parallel, blocked on the owner (keep visible)
1. `pnpm exec supabase db push --linked` (5 migrations incl. the grants security fix), then Auth URL config and the email-confirmation decision (DEPLOYMENT.md).
2. Owner writes the Reel-Studio `SUPABASE_URL` + secret into `apps/api/.env`, restarts `python -m app.serve --tunnel devtunnel`, and runs the production E2E (signup, workspace, project, refresh, upload, second account cannot see data).
3. Teammate `Atharva486dherange` has not accepted the GitHub invitation.


## CODEx TAKEOVER — 2026-10-17 (current owner priority)

For a time-limited Codex session, [docs/CODEX_HANDOFF.md](CODEX_HANDOFF.md) supersedes the **sequence of upcoming work only**, not verified implementation, the original problem statement or security invariants. Start by inspecting git status and the latest commits; then develop Phase 05 topic-to-video to actual rendered MP4, improve user-facing UI using the **structure** (not theme/colors/fake metrics) of the owner's four screenshots, implement Phase 06 multi-track editor, Phase 07 real social authorization/upload/scheduling, Phase 08 analytics/feedback. Defer subscriptions/checkout and nonessential hardening/polish until working PS flows are integrated. Original older task notes above are historical, not instructions to repeat Phase 04. Update these docs after your current-turn tests.

## Active checkpoint — 2026-10-17: topic studio and Instagram integration

Branch: `feature/topic-studio`. Added local topic generation (Ollama → validated storyboard → Kokoro → measured captions → canonical timeline → Hyperframes), refreshed studio UI, and authenticated Instagram Login/publishing/insights screens and worker handlers. These are implemented slices, not completed phase acceptance.

Instagram env presence verified without values: client ID numeric, secret present, exact callback `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`, backend encryption key present. No manual test token. Actual account authorization, Meta registered redirect acceptance, scopes and token validity remain unverified until OAuth consent. Never publish a real test Reel without the owner's specific approval.

Both migrations `20261017030000_topic_generations.sql` and `20261017040000_social_publishing.sql` applied only to verified project `adjwycjsxtxvjockxtan`. API/tunnel/worker restarted; local health 200 and unauthenticated social route 401. Zero connected accounts and zero publication rows at restart. Port-8001 local test stack was left untouched.

Verified: backend 74 passed / 6 integration tests skipped (one upstream deprecation warning), Ruff clean; workspace lint and typecheck pass; timeline 9 tests pass; direct Next production build passes including publishing callback. Earlier local database suite: 47 pgTAP tests pass and schema lint clean; the later change_publication RPC has not yet been exercised locally. No new live Mode B MP4, Instagram OAuth, real publish, or real analytics retrieval has been verified. Frontend deployment pending this checkpoint.

Next: deploy callback/UI, finish authorized Instagram OAuth, verify public media ingestion without publishing, exercise scheduling failure/retry/idempotency, render and inspect a genuine topic video. Phase 06 full editor, Google OAuth/upload, analytics feedback and final end-to-end acceptance remain outstanding. Keep Google credentials private in backend .env. OAuth tokens are encrypted in backend-only database rows, never frontend storage.
