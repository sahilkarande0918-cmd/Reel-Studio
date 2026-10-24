# Reel Studio 2.0 — Technical Handoff (updated 2026-10-24, end of the second 2.0 session)

Standalone: a new session can continue from this file plus `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full spec, status map,
owner prompts verbatim) without any chat history. These two files take precedence over every 1.0 document
(`CHECKPOINT.md` below its 2.0 header, `IDE_HANDOFF.md`, `HANDOFF.md`, `PHASES.md` are history). The first 2.0
session's handoff (engine internals, reference analysis, phonk reel) is in git: `git show 6b29ec7:docs/REEL_STUDIO_2_HANDOFF.md`.
**Trust the code over this text if they ever disagree.** Nothing below is called "verified" unless it was run.

## 1. What the project is
Reel Studio — an AI video-editing and content-marketing platform (₹0 mandatory cost, local GPU engine).
- **Mode A — Recording → Reels**: long class/business recording → Hinglish/English ASR with technical-term correction →
  context-aware highlights (teaching-step outline, five-component score) → code-aware 9:16 crop → captions/brand →
  editor → Hyperframes MP4 → Instagram (with approval).
- **Mode B — Prompt → Professional edit** (replaces Topic → Video): any practical number of clips/images + optional
  music + optional reference reel + a prompt → AI director → beat planner → FFmpeg base picture + separate audio →
  optional Hyperframes overlays (motion graphics, text, captions) and Blender 3D shots → measured QA → MP4 → editor.
- Business layer: AI clip collections (Mode A series), campaign agent (EN/HI/Hinglish), tracked links/inquiries,
  Instagram publishing extras (cover frame, suggestions). Voice profiles for narration.

Architecture:
```
Next.js 16 (apps/web, Vercel sin1)  ──JWT──►  FastAPI + durable worker (apps/api, owner's RTX 5050 laptop, Dev Tunnel)
   │  Supabase Auth/Postgres+RLS/Realtime (project adjwycjsxtxvjockxtan)        │
   │  public: /r/<slug> (click redirect), /i/<slug> (inquiry form) → RPCs     ├─ jobs: transcribe, analyze, render,
   │                                                                          │   publish, insights, generate (old topic),
   │                                                                          │   ingest, edit, voice_preview, campaign
Mode B edit job:  assets ─ingest→ analysis ─► director.py (LLM directive, validated) ─► planner.py (beats, slots,
   sources, effects, cues) ─► render.py/base.py (FFmpeg segments, composites, xfade) + audio.py (music/SFX/voice mix)
   ─► qa.py (measured) ─► overlay.py (canonical timeline: base video + 3D shots + motion items + text + captions)
   ─► Hyperframes render only if overlays exist (else base is the export) ─► render_jobs row ─► editor/download
3D: blender.py launches headless Blender with our blender_scene.py (validated params only) → MP4 → timeline video item
Voice: voice_profiles.py → subprocess voice-venv/python voice_worker.py (torch + Chatterbox) → WAV → ASR word timing
```

## 2. Implemented and verified (run, with evidence)
| Feature | Evidence |
|---|---|
| Repo migration, owner-only history | `docs/MIGRATION.md` |
| Mode B web flow (Phase A) | UI edit in the browser (2 clips + phonk): 15.000 s, 1080×1920 H.264+AAC downloaded from the app; editor opens the Mode B timeline |
| AI director (Phase B) | Same 8 clips, 3 prompts → phonk/fast/vintage (16 cuts), cinematic/slow/cool (all QA pass), tech promo with floating cards + browser mockup; logs `data/mode-b-tests/phase-b/*.log` |
| Motion templates (Phase C) | 26/26 templates animated + Hyperframes lint clean (`tests/motion_gallery.py`, `data/motion-gallery/sheet.jpg`); 24 s ad rendered, all QA pass (`phase-c/ad.mp4`) |
| Effects (Phase D) | 35 effects + 33 transitions: 69/69 gallery renders pass (`data/effects-gallery-3`, `effects-gallery-2`); subject cutout, depth parallax, minterpolate slow-mo checked visually (`data/composite-test/sheet.jpg`) |
| Blender worker (Phase E) | Headless Blender 5.2.3 renders text_3d + product_turntable (`data/blender-test`); 3D edit 16.000 s, all QA pass, timeline has b3d-0 (title) + b3d-1 (turntable) (`phase-e/3d.mp4`) |
| 100 caption presets + ON/OFF (Phase G) | `tests/test_caption_presets.py` validates + compiles all 100 (no colour-only duplicates); 23-family render gallery (`data/caption-gallery/sheet.jpg`); Mode A render with `phonk-red` and with captions OFF (`data/mode-a-test/{preset,off}.mp4`, 46.53 s) |
| Clip collections (Phase H) | `tests/test_collections.py`; generated on the synthetic React lecture: "UseEffect" (6) + "Full class series" (6) |
| DB security | pgTAP 72/72 incl. 20 new 2.0 tests (`supabase/tests/database/v2.test.sql`); `supabase db lint` clean |
| Phonk reel from owner footage (first session) | `data/mode-b-tests/grind-phonk-ref4/edit.mp4`, 480/480 frames, −14.0 LUFS |

## 3. Partially implemented
- **Phase D acceptance**: two-clip 18 s and eight-clip 20 s edits were queued at checkpoint (scratchpad
  `acceptance2.py` → `data/mode-b-tests/phase-d/`); results NOT recorded. Rerun with `tests/e2e_mode_b.py` (§13).
- **Phase C ad quality**: first ad used the local test workspace's brand kit (Nimbu watermark) and landscape
  screenshots left white space; fixed (`brand_kit_id: "none"`, cover-fit mockups, keep director scenes, no closing
  fade, required-content check). Re-render `phase-c/ad2.mp4` was running at checkpoint (not verified).
- **Voice (Phase F), session 3 update**: speech synthesised and checked (TEST_STATUS); Hinglish now converted to
  Devanagari before synthesis. Still open: profile via `/voices` + Mode B narrated edit (local Supabase blocked by
  Windows port reservation 54313–54412; fix: admin `net stop winnat` / `net start winnat`).
- **Voice (Phase F)**: everything built (table, API, consent, quality checks, owner-only use, pronunciations, preview job,
  deletion, Settings UI, Mode B narration path); isolated venv installed; model files downloaded to
  `data/models/chatterbox` (ve.pt, t3_mtl23ls_v2.safetensors, s3gen.pt, grapheme json, conds.pt, Cangjie5_TC.json).
  **No speech has been synthesised yet.** Test job at `data/voice-test/job.json` (synthetic Kokoro reference voice;
  add `"model_dir"`). The owner's consented voice sample has not been provided.
- **Campaign agent (Phase I)**: works end to end (Ollama → plan → tracked links → UI → project with prefilled prompt);
  staged planner (strategy + one call per reel format). Latest direct run (`data/campaign-test-3.json`, 239 s): full
  concept sentence, Hinglish hooks, but hooks still repeat across reels and scripts drift to English. Needs better
  prompts or the optional stronger model.
- **Localisation/tracking (Phase J)**: EN/HI/Hinglish prompts + checks; Marathi disabled ("not yet: model output not
  validated"); `/r` and `/i` public routes + RPCs tested in pgTAP; no real visitor click yet (not deployed).
- **Instagram (Phase K)**: cover frame (`cover_ms` → `thumb_offset`), campaign id on posts, caption/hashtag suggestions
  (campaign → director → highlight), UI. **Nothing was published or scheduled (owner rule: publish nothing).**
- **Phase L**: suites green (§16); `next build` not run this session; Tests B, E, H not rendered.

## 4. Not started
Marathi (disabled until a model is validated). Everything else listed here at the end of session 2 was built in session
3: deploy (✅ live), collection scheduling, manual beat correction, reference style report + layout detection, tracked
labels (`tracked_tag`, OpenCV MIL), six shader-style transitions (`diamond`, `blinds`, `checker`, `luma_burn`,
`ripple_mix`, `iris_soft`), prompt-structured scenes, before/after split screen, export bitrate cap (D-049, D-050).
**Built in session 3 but not yet verified in a render:** tracked labels, the six new transitions, layout detection on a
real reference, series scheduling, beat correction, the final Test B/E/H re-renders (were running at the end).

## 5. Work completed in this session (commits after `6b29ec7`)
- `40c090b` Mode B web app + AI director + migrations (media_assets, edit_generations, project mode `edit`), ingest/edit jobs, assets/edits APIs, Create page, media bin, edit studio, motion library start.
- `e7a7805` 26 motion templates, 11 new effects + 11 transitions, minterpolate, ONNX composites, Blender worker + MCP config.
- `86306f4` voice profiles, 100 caption presets + ON/OFF, clip collections, campaign agent + tracking, Instagram cover/suggestions.
- `ac322a5` grounded scenes, staged campaign planner, 3D shot length, hydration fix, QA/RLS tests, licences, D-045…D-048.
- checkpoint docs commit (this file, master plan, synced docs).

## 6. Source files changed and why (apps/api unless noted)
| File | Purpose |
|---|---|
| `app/api/assets.py`, `app/core/upload.py`, `app/core/storage.py` | Mode B uploads: resumable chunks, kinds clip/image/audio/reference, SHA-256 dedupe, limits, signed media/thumb URLs |
| `app/api/edits.py`, `app/workers/edit.py` | Edit request (prompt, duration, aspect, style, music, reference, captions+preset+overrides, voice, language, quality, brand kit) and the edit job |
| `app/workers/ingest.py` | Per-asset analysis (clip moments, beats, reference profile, thumbnail, VLM subject tags) |
| `app/services/llm.py` | Ollama JSON calls (seeded) + optional OpenAI-compatible endpoint; vision `look()` |
| `app/services/editing/director.py` | AI director directive, schema, rules fallback, sanitising, profile/weights |
| `app/services/editing/planner.py` | clip weights, pinned first/last clip, no same-clip back-to-back, composite budget, depth parallax for stills |
| `app/services/editing/effects.py` | 35 effects, 33 transitions (registry) |
| `app/services/editing/base.py` | composites hook, minterpolate slow-mo, 1 s clone pad before exact trim, source height ≤ 1920 |
| `app/services/editing/composite.py` | OpenCV + ONNX subject cutout and depth parallax |
| `app/services/editing/overlay.py` | plan → canonical timeline (base, 3D shots, motion, text, captions), designed-scene structure, 3D split/fallback |
| `app/services/editing/qa.py` | black-frame test (p98), planned dip-to-black allowance, cut spike detection |
| `app/services/clips/analysis.py` | optical flow sampled ~15/s at any fps |
| `app/services/rendering/motion.py` | 26 templates, CSS, SFX cues, required-content rule |
| `app/services/rendering/caption_presets.py` | 100 presets, overrides model, style_for, catalog |
| `app/services/rendering/compose.py` | motion items, caption looks/entrances/ON-OFF, new fonts, silent-video flag |
| `app/services/rendering/timeline.py` | motion item validation |
| `app/services/rendering/blender.py`, `blender_scene.py` | validated 3D scenes, headless render, completion via done/error files |
| `app/services/voice.py`, `voice_profiles.py`, `voice_worker.py`, `app/api/voices.py`, `app/workers/voice.py` | narration (Kokoro or profile), consent + quality, isolated synthesis, preview job |
| `app/api/collections.py` | grounded series from outline topics, edit, batch render |
| `app/services/campaign.py`, `app/api/campaigns.py`, `app/workers/campaign.py` | campaign planning, grounding, tracked links |
| `app/api/publishing.py`, `services/publishing/instagram.py`, `workers/publish.py` | cover_ms/thumb_offset, campaign id, suggestions |
| `app/api/renders.py` | captions ON/OFF + preset for Mode A, `/captions/presets`, shared `enqueue_highlight_render` |
| `packages/timeline-schema/src/index.ts` (+ json) | `motion` item, `source.editId`, `captionStyle.enabled`, `captionStyle.look`, `CAPTION_FONTS` |
| `supabase/migrations/20261024*` (7) | mode `edit`; media_assets/edit_generations; voice_profiles; clip_collections; campaigns/tracked_links/link_clicks/inquiries + public RPCs; projects.campaign_*; publish_jobs.cover_ms/campaign_id |
| web: `app/(app)/create`, `components/studio/{media-bin,edit-studio,caption-picker,collections}.tsx`, `components/campaigns/*`, `app/(app)/campaigns/*`, `app/r/[slug]`, `app/i/[slug]`, `components/settings/voice-profiles.tsx`, publishing/editor/renders/sidebar/projects/dashboard edits, `lib/backend.ts` (hydration), `proxy.ts` (public /r /i), `public/caption-fonts` | UI for all of the above in the existing forest-green/ivory theme |
| tests: `test_caption_presets.py`, `test_collections.py`, `test_campaign.py`, `test_editing.py` (+3), `e2e_mode_b.py`, `motion_gallery.py`, `caption_gallery.py`; `supabase/tests/database/v2.test.sql` | checks |
| `.mcp.json` | Blender MCP for Claude Code (`uvx mcp-for-blender`, safe mode, telemetry off) |

## 7. Models, tools, dependencies, skills
See master plan Part 4. Local models: Ollama `qwen2.5vl:7b`; Oriserve Hinglish Whisper CT2; Kokoro (Hyperframes);
U²-Netp + Depth-Anything-V2-Small ONNX (`data/models/onnx`); Chatterbox Multilingual (`data/models/chatterbox`).
Python venv `C:\Users\Sahil\AppData\Local\reel-studio\venv` (no torch); voice venv
`C:\Users\Sahil\AppData\Local\reel-studio\voice-venv` (Python 3.11, torch 2.7.1+cu128, torchaudio 2.7.1,
chatterbox-tts 0.1.7 installed `--no-deps` + its dependencies, numpy<2). Blender 5.2.3 LTS (Microsoft Store; run via
`%LOCALAPPDATA%\Microsoft\WindowsApps\blender-launcher.exe`, which returns before Blender finishes). uv/uvx in
`%LOCALAPPDATA%\hermes\bin`. Blender add-on lives in the Store's virtualised AppData
(`%LOCALAPPDATA%\Packages\BlenderFoundation.Blender_ppwjx1n5r4v9t\LocalCache\Roaming\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py`).
Claude Code skills used: hyperframes*, ponytail. Licences: `THIRD_PARTY_LICENSES.md`.

## 8. Mode A and Mode B today
- **Mode A**: unchanged pipeline + new: captions ON/OFF and 100 presets in "Create reel" and the editor, clip
  collections panel. Mode A upload→transcribe→analyze was not re-run this session (only render paths).
- **Mode B**: `/create` → project → media bin → direction form → Generate → live stages (analyze, direct, voice,
  plan, render_base, blender, qa, compose/render, verify) → storyboard stills + director reasons + QA flags → preview,
  download, Open in editor, Publish link. Campaign ideas create Mode B projects with the prompt prefilled.

## 9. Renderer status
FFmpeg base picture ✅ (all effects/transitions); Hyperframes overlays ✅ (motion, text, captions, watermark;
~150 s for a 16 s overlay pass); Blender ✅ headless worker (EEVEE, ~35–55 s per second of 3D at 1080×1920);
GPU shader layer ⬜.

## 10. Working effects, transitions, templates
Effects (35): push_in, pull_out, punch_zoom, zoom_bounce, shake, pan, rotate, whip_pan, gaussian_blur, motion_blur,
directional_blur, blur_reveal, zoom_blur, flash, rgb_split, glitch, contrast_snap, bright_pulse, vignette, grain, grade,
glow, vhs, black_white, wobble, crash_zoom, tilt, drift, light_leak, bloom, color_pulse, exposure, focus_blur, edge_glow,
strobe (≤ 3 Hz); composites subject_pop, depth_parallax. Transitions (33): cut, crossfade, dip_black, dip_white, flash,
swipe_left/right/up, wipe, zoom_through, whip, blur, radial, circle_reveal, pixelize, smooth_left, squeeze, diagonal,
cover_up, reveal_down, slice, wind, dissolve, circle_close, open_vertical, open_horizontal, smooth_up, rect_crop,
distance, fade_grays, squeeze_vertical, wipe_up, slide_down. Motion templates (26): kinetic_title, blur_reveal,
stagger_lines, typewriter, masked_text, counter, floating_cards, browser_mockup, phone_mockup, laptop_mockup,
split_screen, info_list, chat_bubbles, calendar, bar_chart, stat_ring, logo_reveal, cta_button, pricing_card,
lower_third, light_sweep, glow_arc, shape_burst, grid_gallery, notifications, media_card. 3D: 3d_title, 3d_product.

## 11. UI and backend status
UI: unchanged forest-green/ivory theme; new pages Create, Campaigns, campaign detail, public /r and /i; Settings voice
section; caption picker; collections panel; publishing cover/suggest. Phone width checked (no horizontal overflow).
Backend: all routers in `app/main.py`; worker handlers in `app/workers/run.py`.

## 12. Supabase, Vercel, Instagram
**Session 3: deployed.** Production migrated, the production engine runs 2.0 from this folder, Vercel serves 2.0
(details and rollback at the top of `DEPLOYMENT.md`). The notes below describe the pre-deploy state.
- Supabase: 7 new migrations applied **locally only**. Production project `adjwycjsxtxvjockxtan` has NOT been migrated
  (`supabase/.temp/project-ref` = adjwycjsxtxvjockxtan; review then `pnpm exec supabase db push`).
- Vercel: project `reel-studio` (team_N7gyjjdCHX9K8ifMie5nzuV6, prj_VVWevgFfCwq7LgQauMu1B11RGzua, domain
  reel-studio-taupe.vercel.app, latest prod deployment dpl_EG8TUnJnEjRxVTsWqqfRkPBfUttU built from the OLD repo
  `Open_PS04_`). No Vercel CLI on this machine; the Vercel MCP tools work (get_project verified). The owner asked to
  deploy "at last", with the same dashboard UI.
- Production engine still runs from `C:\dev\Reel-Studio` (old code; Windows task "Reel Studio Engine"); the deployed
  2.0 web needs the 2.0 engine (`apps/api/start-engine.cmd` in this folder; production `.env` already copied) or Mode B
  calls will 404.
- Instagram: unchanged OAuth/queue; **owner rule: publish nothing**. No publish/schedule jobs exist locally.

## 13. Local setup and commands
```bash
# local test stack
pnpm exec supabase start && pnpm exec supabase migration up --local
sh .claude/local-engine.sh          # API :8001 + worker against local Supabase (git-ignored file; local demo secret only)
cd apps/web && pnpm dev             # :3000; apps/web/.env.development.local points at the local stack + engine :8001
# local login (local stack only): upload-owner@test.local, password in apps/api/tests/test_upload_integration.py
"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve     # Ollama does not auto-start
# end-to-end Mode B through the API (same calls as the web app)
C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python apps/api/tests/e2e_mode_b.py OUT.mp4 --prompt "..." \
  --settings '{"duration_s":18,"use_reference":false,"brand_kit_id":"none"}' --music "C:/Users/Sahil/Downloads/phonk audio.mpeg" CLIP1 CLIP2
# galleries
python apps/api/tests/motion_gallery.py OUT IMG...
python apps/api/tests/effects_gallery.py SRC.mp4 OUT 5
python apps/api/tests/caption_gallery.py OUT BG.mp4 [--all]
# voice test (isolated env)
C:/Users/Sahil/AppData/Local/reel-studio/voice-venv/Scripts/python apps/api/app/services/voice_worker.py JOB.json
# checks
cd apps/api && python -m pytest -q && python -m ruff check .
cd apps/web && pnpm lint && npx tsc --noEmit && npx next build
cd packages/timeline-schema && pnpm test
pnpm exec supabase test db && pnpm exec supabase db lint --local --level warning
```
Restarting the engine: kill the `python … app.serve` / `app.workers` processes, then start again (a killed job is
requeued after 3 min). Never restart during an upload. Shell-scripted Python edits on this machine turn `\b`/`\n`
escapes into control characters — edit files with the editor tool and scan for `[\x00-\x08]` after bulk edits.

## 14. Media, references, outputs
Owner inputs: `C:\Users\Sahil\Downloads\` (reel template*.mp4, clip 1–17.mp4, phonk audio.mpeg, guide PDF).
Outputs under `C:\Users\Sahil\AppData\Local\reel-studio\data\`: `mode-b-tests\phase-b\{phonk,cinematic,ad}.mp4`,
`phase-b\compare.jpg`, `phase-c\ad.mp4` (+ `ad2` pending), `phase-d\` (pending), `phase-e\3d.mp4`,
`app-e2e\phonk.mp4`, `grind-phonk-ref4\`, `motion-gallery\`, `effects-gallery-2\`, `effects-gallery-3\`,
`caption-gallery\`, `composite-test\`, `blender-test\`, `mode-a-test\{preset,off}.mp4`, `campaign-test*.json`,
`voice-test\`, `models\onnx\`, `models\chatterbox\`. Local renders also in `data\orgs\<org>\renders\<id>\`.

## 15. Known bugs and limitations
- Campaign copy from qwen2.5vl:7b repeats hooks and mixes English into Hinglish; grounding removes invented numbers.
- Director sometimes picks `cinematic` for promos; model scene durations are short (now stretched to the next scene).
- Ingest ~50 s per clip (VLM tag ~8 s warm / 25 s cold + analysis); one GPU worker runs jobs one at a time.
- Hyperframes overlay pass is slow (~150 s for 16 s); a brand watermark alone triggers it.
- Blender Store build only reachable through the launcher alias (no stdout); completion detected via files.
- Local test workspace has a default "Nimbu Academy (test kit)" brand kit → watermark unless `brand_kit_id:"none"`.
- `subject_pop` is CPU-heavy (~15 s per output second at 1080p), budgeted to 2 shots per edit.
- Old test clips are 478×850 (upscaled, soft); night clips are genuinely dark.
- `next build` not run this session; landing page card still says Topic → Video.
- Production not migrated/deployed (§12).

## 16. Test results (this session)
API pytest 118 passed / 6 skipped; ruff clean; web `tsc` clean, `eslint` clean; schema vitest 12/12; pgTAP 72/72;
`supabase db lint` no errors; motion gallery 26/26; effects+transitions 69/69; caption gallery 23/23 families animate;
Phase B three prompts → three distinct edits (cinematic all QA pass; phonk had one cut-detection miss caused by two
shots of the same clip — planner fixed); Phase C ad 24.000 s all QA pass; 3D edit 16.000 s all QA pass; Mode A preset
and captions-OFF renders ready. Not run: voice synthesis, `next build`, Tests B/E/H, production checks.

## 17. Remaining work (priority order, after session 3)
1. One-go verification of everything built in session 3 (owner asked to build first, test at the end): tracked labels,
   the six new transitions (gallery: `tests/effects_gallery.py`), layout detection on Reference 2/3, series scheduling
   (UI only, publish nothing), beat correction, and the Test B/E/H re-render outputs in `data/mode-b-tests/test-b4`,
   `test-e2`, `test-h` (fetch with the scratch `fetch_gen.py` pattern: a fresh token per poll; tokens expire after 1 h).
2. Landing card: `apps/web/app/page.tsx` already says Prompt → Edit and uses `/landing/app-create.jpg` (2.0 UI, no private
   media); it still needs `/landing/reel-edit.mp4` + `reel-edit.jpg` from a render without private footage (Test B4 is
   the intended source). page.tsx and app-create.jpg are not committed until the video exists.
3. Owner's own consented voice recording for a real profile (Phase F used a synthetic consented sample).
4. Campaign copy: judge Test H output; consider the optional external planner (DIRECTOR_API_*) for better Hinglish.
5. Redeploy Vercel after each web change (project Git link points at the old repo: use the API `gitSource` deploy).

## 18. Precise next task
Run the one-go verification in §17.1, record results in TEST_STATUS, then finish the landing card (§17.2) and redeploy.
Claude storage lives on D: (`docs/CLAUDE_STORAGE_MIGRATION.md`); never delete the C: original without approval.

## 19. Git
Branch `main`, remote `origin` = https://github.com/sahilkarande0918-cmd/Reel-Studio.git (in sync at checkpoint).
Latest code commit `ac322a5`; the checkpoint docs commit follows it. `source` remote = Open_PS04_ (fetch only).
Identity `sahilkarande0918-cmd <sahilkarande0918@gmail.com>`; never AI authors/co-authors/trailers.

## 20. Environment variable names (values never in git)
- `apps/api/.env`: SUPABASE_URL, SUPABASE_SECRET_KEY, TOKEN_ENCRYPTION_KEY, ALLOWED_ORIGINS, DATA_DIR, OLLAMA_URL,
  OLLAMA_MODEL, PUBLIC_API_URL, SITE_URL (new: public web URL for inquiry links), WHISPER_MODEL, WHISPER_LANGUAGE,
  INSTAGRAM_CLIENT_ID, INSTAGRAM_CLIENT_SECRET, INSTAGRAM_REDIRECT_URI, DIRECTOR_API_URL / DIRECTOR_API_KEY /
  DIRECTOR_MODEL (new, optional external planner), VOICE_PYTHON (optional), BLENDER_PATH (optional),
  HYPERFRAMES_CLI (optional).
- `apps/web/.env.local` / Vercel: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_SITE_URL,
  NEXT_PUBLIC_API_URL (optional). `apps/web/.env.development.local` (ignored) points dev at the local stack.
