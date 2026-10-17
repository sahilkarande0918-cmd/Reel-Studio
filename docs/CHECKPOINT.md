> **IDE switch checkpoint (2026-10-17): read [IDE_HANDOFF.md](IDE_HANDOFF.md) first.** Real Instagram publishing verified (@career.with.purpose, media 18111030863186503, https://www.instagram.com/reel/DekyGWcDEAl/); editor, style presets and dark UI done. Next: production E2E in the owner's account (Topic → Generate → Edit → Render → Download).

# Reel Studio — latest checkpoint (2026-10-17, Claude, final development run)

**Read this first after compaction.** It supersedes older status lines in other docs (not the requirements).
`ORIGINAL_PS.md` and `MASTER_PROMPT.md` are unchanged. Owner rules: ₹0, no AI attribution or co-author trailers,
commits only as `sahilkarande0918-cmd`, only Supabase `adjwycjsxtxvjockxtan`, never disable RLS, no secrets in git,
**YouTube postponed**, never connect/publish to personal `@sahil_karande`, no real post without explicit approval.

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

## 1. Phase status
| Phase | Status |
|---|---|
| 00–04 | ✅ (synthetic + owner's real physics class on production) |
| 05 Topic → Video | ✅ end to end; editable script (re-record and render), plain-language errors, progress stepper, code without ligatures |
| UI redesign | ✅ cinematic dark theme (owner direction 2026-10-17: Inter, #0D0F14 / #12151C / #191D27, **amber #F2B544 primary — no purple at owner's request**, cyan only for live states). Screens: Dashboard, Projects, Recordings, Topic Studio, Editor, Brand Kits, Glossary, Publish, Analytics, Settings. Desktop + mobile checked |
| Style presets | ✅ Focus / Energy / Story / Signature in timeline `stylePreset`, applied by `compose.py` (verified in rendered MP4s) |
| 06 Editor | ✅ `/editor/[renderId]`; verified on Mode B and Mode A renders (see §3) |
| 07 Instagram | ✅ publish verified; scheduling not yet verified live. **Business account connected and verified live** (@career.with.purpose, IG user 17841466046205321, BUSINESS, token encrypted, expires 2026-12-15; media list + account insights calls succeed). **First owner-approved Reel published 2026-10-17**: media 18111030863186503, https://www.instagram.com/reel/DekyGWcDEAl/ (physics class top highlight, 44.5 s). Code complete (connect, encrypted tokens, renewal, disconnect, publish now/schedule, queue, calendar, retries, dedupe, permalink). publishing verified end to end on production |
| 08 Analytics + AI feedback | 🟡 insights refresh verified with the real API (account + per-reel metrics stored; values 0 right after posting). AI feedback needs ≥3 published reels with reach — not yet exercised on real data |
| 09 Submission | 🟡 README rewritten; production E2E in the owner account + submission materials pending |

## 2. Architecture additions this run
- `packages/timeline-schema/src/edit.ts` (+ `edit.test.ts`): pure split/trim/move/duplicate/remove/update keeping invariants.
- Schema: `transition` (none/fade/slide/zoom) on visual items, `fadeIn/fadeOut` on media, `box` on text, `stylePreset`.
- `apps/api/app/api/editor.py`: `POST /renders/{id}/preview` (validate → `preview.write_preview` = compiler HTML + seek runtime),
  `GET /renders/{id}/p/{exp}/{sig}/{file}` (signed folder so relative media/fonts load), `POST /renders/{id}/edit`
  (new render, `parent_render_id`, assets hard-linked), `POST /renders/{id}/brand` (kit → snapshot + logo file).
- Editor UI `apps/web/components/editor/*`: preview is an iframe `srcdoc` with `<base>` = signed folder; postMessage clock.
- Drafts: `timeline_drafts` (RLS, editors write directly → autosave works with the backend offline).
- Render worker: `apply_fades` (ffmpeg volume expression after render). Compose fix: video wrapper `win-*` is untimed
  (Hyperframes lint `video_nested_in_timed_element` had made **Mode A renders fail** with Codex's compositor).
- Instagram: scope `instagram_business_manage_insights` added; `POST /social/accounts/{id}/disconnect`; insights worker
  stores recent media + per-reel metrics in `platform_metrics.media`.
- Feedback: `apps/api/app/services/feedback.py`, `GET/POST /feedback`, table `performance_feedback`; analyze worker passes
  `extras["ideal_s"]` to `candidates.score_window`.
- Migration `20261017050000_timeline_drafts.sql` (drafts, `render_jobs.parent_render_id`, `platform_metrics.media`,
  `performance_feedback`) — **applied to production** (`supabase db push --linked`, ref verified) and local.

## 3. Verified this run (actually run)
- Backend pytest 90 passed / 6 skipped; ruff clean. Timeline-schema vitest 12 passed. Web lint + tsc clean; `next build` ok.
- Mode B editor (local stack): JSON vs XML render → split caption, edited word "EDITED", text overlay, Signature style →
  rendered **1080×1920 H.264+AAC 46.77 s**; frames show overlay, lower third, edited caption, `</name>` without ligature.
- Mode A editor (local stack, synthetic React-hooks lecture): split + delete video and captions → 28.17 s, Energy style →
  rendered **1080×1920 H.264+AAC 28.17 s**; frames show uppercase captions and code-following crop.
- Style presets compile for all four (`compile_html`), Signature/Energy verified in real renders.
- Vercel production deploy READY for `41d1917`. Production backend restarted on new code; tunnel up.
- Topic Studio edit-script → re-record → render verified via UI (42.27 s MP4). Repeated-code: new generation still repeated
  (4/5); stricter gate + repair gives 3/5 distinct live — partial; editing covers the rest.
- Instagram connect attempt by owner returned "Invalid redirect_uri": `.env` value is correct; the Meta app's Business
  login settings must list it exactly, and `INSTAGRAM_CLIENT_ID` must be the Instagram app ID. Owner to fix in Meta.
- **Not verified:** audio fades audible check; analytics/feedback with real data; any Instagram API call with the Business account.

## 4. Pending owner actions
1. ~~Instagram OAuth~~ done. ~~First test post~~ done (approved and published).
2. Approve any further real post (each one) — needed for scheduling verification and AI feedback (≥3 reels with reach).

## 5. Runtime
Production backend `python -m app.serve --tunnel devtunnel` (:8000 → https://j96sqlp6-8000.inc1.devtunnels.ms). Local
test stack :8001 against local Supabase; web dev :3000. **Running `next build` while `next dev` runs leaves the dev server
serving stale CSS — restart dev with a clean `.next`.** Restart API+worker together after backend changes.

## 6. Next steps
See `IDE_HANDOFF.md` §12. First: production E2E in the owner's account (Topic → Generate → Edit → Render → Download).
