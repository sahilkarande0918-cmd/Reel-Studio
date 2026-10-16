# Reel Studio — latest checkpoint (2026-10-17, Claude, final development run)

**Read this first after compaction.** It supersedes older status lines in other docs (not the requirements).
`ORIGINAL_PS.md` and `MASTER_PROMPT.md` are unchanged. Owner rules: ₹0, no AI attribution or co-author trailers,
commits only as `sahilkarande0918-cmd`, only Supabase `adjwycjsxtxvjockxtan`, never disable RLS, no secrets in git,
**YouTube postponed**, never connect/publish to personal `@sahil_karande`, no real post without explicit approval.

## 1. Phase status
| Phase | Status |
|---|---|
| 00–04 | ✅ (synthetic + owner's real physics class on production) |
| 05 Topic → Video | ✅ end to end; editable script (re-record and render), plain-language errors, progress stepper, code without ligatures |
| UI redesign | ✅ cinematic dark theme (owner direction 2026-10-17: Inter, #0D0F14 / #12151C / #191D27, **amber #F2B544 primary — no purple at owner's request**, cyan only for live states). Screens: Dashboard, Projects, Recordings, Topic Studio, Editor, Brand Kits, Glossary, Publish, Analytics, Settings. Desktop + mobile checked |
| Style presets | ✅ Focus / Energy / Story / Signature in timeline `stylePreset`, applied by `compose.py` (verified in rendered MP4s) |
| 06 Editor | ✅ `/editor/[renderId]`; verified on Mode B and Mode A renders (see §3) |
| 07 Instagram | 🟡 code complete (connect, encrypted tokens, renewal, disconnect, publish now/schedule, queue, calendar, retries, dedupe, permalink). **Business account not connected yet → nothing published** |
| 08 Analytics + AI feedback | 🟡 code complete (per-reel insights, comparison, trend chart, feedback ≥3 reels, LLM explanation, learned ideal length → highlight scoring). **No real Instagram data yet** |
| 09 Submission | 🟡 README rewritten; final E2E on production pending Instagram |

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
- **Not verified:** repeated-code fix on a new Mode B generation; Topic Studio edit-script re-render through the UI;
  audio fades audible check; analytics/feedback with real data; any Instagram API call with the Business account.

## 4. Pending owner actions
1. Instagram Business OAuth in a private window (Publish → Connect Instagram → log in with the Business account).
   If Meta rejects the insights scope, enable `instagram_business_manage_insights` on app "Reel Studio-IG".
2. Approve one controlled test post (account, video, caption) before anything is published.

## 5. Runtime
Production backend `python -m app.serve --tunnel devtunnel` (:8000 → https://j96sqlp6-8000.inc1.devtunnels.ms). Local
test stack :8001 against local Supabase; web dev :3000. **Running `next build` while `next dev` runs leaves the dev server
serving stale CSS — restart dev with a clean `.next`.** Restart API+worker together after backend changes.

## 6. Next steps
1. Instagram OAuth (owner) → verify username/ID → approved test post → verify media ID/permalink → insights refresh.
2. Production E2E pass (topic generation + editor render on the owner's account), docs/TEST_STATUS update.
3. Optional polish: editor mobile (desktop-first now), Recording Studio layout refresh.
