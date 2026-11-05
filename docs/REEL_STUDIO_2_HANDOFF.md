# Reel Studio 2.0 — Technical Handoff (updated 2026-11-05, end of the third 2.0 session)

Standalone: a new session can continue from this file plus `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full spec, status map,
owner prompts verbatim) without any chat history. These two files take precedence over every 1.0 document
(`CHECKPOINT.md` below its 2.0 header, `IDE_HANDOFF.md`, `HANDOFF.md`, `PHASES.md` are history). Earlier handoffs are in
git: session 1 `git show 6b29ec7:docs/REEL_STUDIO_2_HANDOFF.md`, session 2 `git show 12108d7:docs/REEL_STUDIO_2_HANDOFF.md`.
**Trust the code over this text if they ever disagree.** Nothing below is called "verified" unless it was run.

> **Session 4 update:** engine task re-enabled and running (owner chose it, 2026-11-05); the HP Victus re-render was
> cancelled at the owner's request ("dont make any video ... keep on engine").
> **Session 4 (2026-11-05): bulk AI clipping for podcasts/interviews** (OpusClip-style, local and free): commits `e0e552e` + `e445899`. Design, options, evidence and gaps: `docs/BULK_CLIPPING.md`. Verified on a SYNTHETIC two-voice interview only (10/10 clean single-exchange clips; honest shortfall when fewer exist; 4–6 s fast renders). Not yet run on real footage or through the production engine/UI. Engine re-enabled and running (owner, 2026-11-05).
> (Session 3 state below.) The production engine was stopped and its task disabled on 2026-11-05 before session 4.
> Owner rules: publish NOTHING on Instagram; never run GPU tests while the owner's edits are rendering.

## 1. What the project is
Reel Studio — an AI video-editing and content-marketing platform (₹0 mandatory cost, local GPU engine on the owner's
RTX 5050 laptop, 8 GB VRAM, 23 GB RAM).
- **Mode A — Recording → Reels**: long class/business recording → Hinglish/English ASR with technical-term correction →
  context-aware highlights (teaching-step outline, five-component score) → code-aware 9:16 crop → captions (100 presets,
  ON/OFF) / brand → editor → Hyperframes MP4 → Instagram (with approval). Clip collections group highlights into series.
- **Mode B — Prompt → Professional edit** (replaced Topic → Video): any practical number of clips/images + optional
  music + optional reference reel + a prompt → AI director → beat planner → FFmpeg base picture + separate audio →
  optional Hyperframes overlays (motion graphics, text, captions, tracked labels) and Blender 3D shots → measured QA →
  MP4 → editor. Photos are matched to the clips' look; optionally animated into real video with local AI (LTX-Video).
- Business layer: campaign agent (EN/HI/Hinglish), tracked links/inquiries, Instagram cover/suggestions/series
  scheduling, consent-based voice profiles (Chatterbox) for narration.

```
Next.js 16 (apps/web, Vercel sin1)  ──JWT──►  FastAPI + durable worker (apps/api, owner's laptop, Dev Tunnel
   │  Supabase Auth/Postgres+RLS/Realtime (adjwycjsxtxvjockxtan)          https://j96sqlp6-8000.inc1.devtunnels.ms)
   │  public: /r/<slug> (click), /i/<slug> (inquiry) → RPCs           jobs: transcribe, analyze, render, publish,
   │                                                                  insights, generate, ingest, edit, voice_preview,
   │                                                                  campaign
Mode B edit job: assets ─ingest→ analysis ─► director.py (LLM directive, validated, placeholders/URLs dropped)
   ─► [photo_match.py: photos matched to clips] ─► [i2v.py → video_worker.py (LTX-Video) if "animate photos"]
   ─► planner.py (beats, slots, whole-beat reference cycle, sources, effects, cues, beat correction)
   ─► render.py/base.py (FFmpeg segments: black-bar crop/blur-fill, composites, frame-exact pad/trim/renumber, xfade)
      + audio.py (music/SFX/voice mix, always exactly the edit length)
   ─► qa.py (measured) ─► tracking.py (tracked labels on the base picture)
   ─► overlay.py (timeline: base + 3D shots + motion items [prompt-structured / before-after / footage-first] + text +
      captions) ─► Hyperframes render (watchdog, low-RAM workers, software fallback) ─► render_jobs ─► editor/download
3D: blender.py → headless Blender (blender_scene.py) → MP4 → timeline video item
Voice: voice_profiles.py → voice-venv/python voice_worker.py (Chatterbox) → WAV → ASR word timing → captions
Photo animation: i2v.py → D:\ReelStudio\video-venv\python video_worker.py (LTX-Video 2B distilled) → 4 s MP4
```

## 2. Implemented and verified (run, with evidence)
| Feature | Evidence |
|---|---|
| Mode B web flow (Phase A) | session 2: UI edit 15.000 s 1080×1920 downloaded from the app |
| AI director (Phase B) | session 2: 8 clips × 3 prompts → three distinct edits |
| Motion templates (Phase C) | session 2: 26/26 animate, lint clean (+ `tracked_tag` session 3, unit-tested only) |
| Effects/transitions (Phase D) | session 2: 35 effects + 33 transitions 69/69; session 3: eight-clip 20 s edit all QA pass (`data/mode-b-tests/phase-d/eight-clips.mp4`) |
| Blender worker (Phase E) | session 2: 3D edit 16.000 s all QA pass |
| **Voice (Phase F)** | session 3: Chatterbox CUDA synthesis EN×2/HI/Hinglish, Perth watermark detected; profile saved via `/voices` (synthetic consented sample, SNR 65.5 dB); Mode B narrated edits EN/HI/Hinglish each 14.000 s, all 8 QA pass, captions within 0–120 ms of speech; speaker similarity 0.95/0.88/0.86 vs 0.72 other speaker (`data/mode-b-tests/phase-f/`) |
| 100 caption presets + ON/OFF (Phase G) | session 2 |
| Clip collections (Phase H) | session 2 (synthetic lecture) |
| Deploy | session 3: 7 migrations on production (remote lint clean); production engine runs this folder; Vercel `dpl_4UBCg8yyma5FXqu1ofa2EsAPZcWa` (commit 0981008) live; GitHub probe: public engine reachable, CORS ok |
| Frame-exact segments | session 3: 8 effect/ramp combos on the owner's HP Victus clip render exactly 88/88 frames (was 70/88); regression test |
| Audio = edit length | session 3: perfume edit re-ran to 20.000 s (was 17.6 s because the song ended); test |
| Export bitrate cap | session 3: 53 Mbps → 20.7 Mbps on grainy footage (`-maxrate 20M`) |
| Photo matching to clips | self-check only (`python -m app.services.editing.photo_match`): colour moves toward the footage, crisp photo softened |
| AI photo animation (LTX-Video) | session 3: one photo → 4.04 s 448×800 97 frames in 121 s on the RTX 5050 (`data/i2v-test/out/`); real motion, but the subject left frame → both-ends conditioning added (not re-tested) |
| Black-bar detection | unit test on a synthetic letterboxed clip (detected, blur-filled, frame-exact); real HP Victus clip detected 590×332 picture |
| Tests B/E/H re-renders | B4 infographic 20 s (fails only `transitions_visible`), E2 before/after 15 s (all pass), H campaign reel 20 s (fails `no_unplanned_black`; caption suggestion source=campaign, tracked link, 0 publish jobs) — **not visually reviewed** |
| Claude storage C:→D: | `docs/CLAUDE_STORAGE_MIGRATION.md` (junction, 3,551 files hash-verified) |
| Engine reliability | Ctrl+C-proof 2-minute ensure task (conhost --headless), no console input, render watchdog, software-render fallback, low-RAM worker count — each observed working (watchdog fired at 03:24 as designed) |

## 3. Partially implemented
- **HP Victus edit fixes (this checkpoint commit)** — owner's production edit `a57b7786-…` rendered 20 s but had four
  problems; fixes are committed and unit-tested, **the re-render was not run** (owner stopped the engine):
  1. text auto-fit (`compose.py` FIT pass) — not yet seen in a render;
  2. footage-first scenes for non-designed styles (`overlay.py` `backdrop:"none"`, ≤ 2.5 s; `motion.py` `.mg-over`) — not yet rendered;
  3. built-in black bars (`base.content_box` per shot range + crop or blur-fill in `_frame_filter`) — unit-tested only;
  4. cuts on beat (`style_transfer.whole_beat_cycle`: a lone 3.5-beat reference shot no longer shifts every cut 333 ms off) — unit-tested.
- **AI photo animation**: works end to end in a smoke test; not yet used in a real Mode B edit through the UI; both-ends
  conditioning (subject stays in frame) not re-tested; ~2 min per photo.
- **Landing page**: card copy now "Prompt → Edit" with `/landing/app-create.jpg` (2.0 UI, public test data only); the
  phone video is hidden until a Mode B reel without private footage exists. Not deployed (Vercel last built 0981008).
- **Campaign agent**: works; copy from the 7B model still repeats hooks (Test H: 3 of 5 similar before the new drop
  rule, which keeps ≥ 3 reels); optional external planner (DIRECTOR_API_*) untried.
- **Photo matching / tracked labels / six shader transitions / layout detection / series scheduling / beat correction
  UI** — built and unit-tested; not yet seen in a real render or used in the UI.
- Owner's own consented voice recording not provided (profile uses a synthetic sample).

## 4. Not started
Marathi (disabled until a model is validated). Everything else in the master plan has code.

## 5. Work completed in session 3 (commits after `12108d7`, oldest first)
`78cb228` storage migration script · `350b8cd` migration verified · `925e192` Hinglish → Devanagari for voice ·
`8cf0d62` series scheduling, reference report, beat correction, hook rejection · `7041005` list-scene merge, hydration ·
`e5ca96c` no placeholders, scene length, bitrate cap · `16d2a25` prompt-structured scenes · `a16e15f` before/after split,
campaign drops · `a61a799` tracked labels, shader transitions · `938176b` layout detection · `0981008` docs/D-049–50 ·
`bb8c04b` deployment id · `1a6b279` no idle sleep, Ollama by launcher · `510393e` docs · `8a760d5` ensure-check engine ·
`5c5ffcc` audio length, safe storyboard · `99c3f4a` engine stopped · `64657b8` photo matching + LTX image-to-video ·
`bf0fc89` windowless check · `2b0d9dd` frame-exact segments · `654b294` render watchdog, low-RAM workers, LTX offline ·
`bea5175` no console input, tree kill · `bc4bd81` software-render fallback · checkpoint commit (HP Victus fixes, landing,
docs).

## 6. Source files changed in session 3 and why (apps/api unless noted)
| File | Purpose |
|---|---|
| `app/services/editing/base.py` | frame-exact pad→trim→renumber after effects; `content_box` (cropdetect per shot range); crop or blur-fill wide pictures; bitrate cap |
| `app/services/editing/render.py` | attach black-bar boxes per shot |
| `app/services/editing/audio.py` | mix padded to exactly the edit length |
| `app/services/editing/style_transfer.py` | `whole_beat_cycle` |
| `app/services/editing/overlay.py` | `merge_lists`, `prompt_structure`, `before_after`, footage-first cap + `backdrop`, branded logo only |
| `app/services/editing/director.py` | placeholder filter (Button/Headline…), URLs not in the prompt dropped, `tracked_tag` overlay-only |
| `app/services/editing/planner.py` | `correct_beats`; photo camera move follows clip motion |
| `app/services/editing/photo_match.py` (new) | photos matched to clips (LAB transfer 60 %, softening, grain) |
| `app/services/editing/tracking.py` (new) | subject path for tracked labels (OpenCV MIL) |
| `app/services/editing/effects.py` | six xfade expression transitions |
| `app/services/i2v.py`, `app/services/video_worker.py` (new) | AI photo animation via LTX-Video in `D:\ReelStudio\video-venv` |
| `app/services/rendering/motion.py` | `tracked_tag`, `.mg-over`, blank mockup defaults |
| `app/services/rendering/compose.py` | FIT pass: motion text never leaves the frame |
| `app/services/reference/analyzer.py` | layout (panels) per shot |
| `app/services/voice_profiles.py` | Hinglish → Devanagari (guarded) |
| `app/services/campaign.py` | near-duplicate hooks, per-field language, drop repeats, strip leaked format text |
| `app/api/collections.py` | `/collections/{id}/schedule` |
| `app/api/edits.py` | `beat_offset_ms`, `bpm`, `animate_photos` |
| `app/api/publishing.py` | AI-generated disclosure in suggestions |
| `app/api/health.py` | `photo_animation` capability |
| `app/workers/edit.py` | photo match, animation, tracking, storyboard never fails |
| `app/workers/render.py` | watchdog (300 s), tree kill, low-RAM workers, software fallback, stdin=DEVNULL |
| `app/serve.py` | public engine keeps Windows from idle-sleeping |
| `start-engine.ps1`, `start-engine.cmd` | 2-minute ensure check (Ollama + engine, `< NUL`) |
| `packages/timeline-schema` | motion `track`, `backdrop` |
| web: `components/studio/{collections,media-bin,edit-studio}.tsx`, `lib/backend.ts`, `app/terms/page.tsx`, `app/page.tsx` | scheduler, reference report + layout, beat grid, animate-photos toggle + AI labels, hydration, LTX terms, landing copy |
| `scripts/claude-storage/migrate-claude-storage.ps1` | storage migration |
| tests: `test_editing.py` (+12), `test_voice_profiles.py`, `test_campaign.py` (+1), `test_health.py` | checks |

## 7. Models, tools, dependencies, skills
Ollama `qwen2.5vl:7b`; Oriserve Hinglish Whisper CT2 + faster-whisper base; Kokoro (Hyperframes); U²-Netp +
Depth-Anything-V2-Small ONNX; Chatterbox Multilingual (`data/models/chatterbox`); **LTX-Video 2B 0.9.8 distilled +
bf16 T5-XXL** (`D:\ReelStudio\models\ltxv`, configs in `configs/`, LTXV Open Weights License: free under US$10M revenue,
outputs disclosed as AI-generated). Venvs: main `C:\Users\Sahil\AppData\Local\reel-studio\venv` (no torch); voice
`…\reel-studio\voice-venv` (torch 2.7.1+cu128, chatterbox 0.1.7); video `D:\ReelStudio\video-venv` (torch 2.7.1+cu128,
diffusers 0.39, transformers 4.57, accelerate 1.15; uv cache `D:\ReelStudio\uv-cache`). Hyperframes CLI 0.8.164
(npx cache). Blender 5.2.3 (Store). OpenCV 5.0 (MIL tracker). Skills: hyperframes*, ponytail. Licences:
`THIRD_PARTY_LICENSES.md`.

## 8. Mode A and Mode B today
- **Mode A**: pipeline + captions ON/OFF, 100 presets, clip collections + series scheduling. Upload→transcribe not re-run in sessions 2–3.
- **Mode B**: `/create` → project → media bin (clips, images, music, reference + style report) → direction form (style,
  duration, aspect, music, voice + language + script, captions, quality, beat grid, animate photos, follow reference) →
  Generate → live stages (analyze, direct, voice, animate, plan, render_base, blender, qa, render) → storyboard + director
  reasons + AI-generated shots + QA → preview/download/editor/publish.

## 9. Renderer status
FFmpeg base ✅ (frame-exact, bitrate-capped, black-bar handling new); Hyperframes overlays ✅ (~1.5–2.5 min per 20 s;
watchdog + software fallback; needs ≥ 10 GB free RAM for 8 workers, else 4); Blender ✅; LTX-Video ✅ smoke test.
Root cause of the 2026-10-27 overlay hangs: a manual LTX GPU test ran during an owner render and was force-killed,
wedging Chrome's GPU path; a Windows restart fixed it.

## 10. Working effects, transitions, templates
Effects (35) and transitions (33) as in session 2, plus transitions `diamond`, `blinds`, `checker`, `luma_burn`,
`ripple_mix`, `iris_soft` (parse/run checked, not visually reviewed). Motion templates 27 (`tracked_tag` new). 3D:
`3d_title`, `3d_product`.

## 11. UI and backend status
Forest-green/ivory theme unchanged. New in session 3: series scheduler in collections, reference style report + layout
row, beat grid controls, animate-photos toggle (enabled only when the engine reports `photo_animation`), AI-generated
shot labels, Terms section for AI video. Backend routers in `app/main.py`, worker handlers in `app/workers/run.py`.

## 12. Supabase, Vercel, Instagram
- Supabase production `adjwycjsxtxvjockxtan`: all 2.0 migrations (20261024100000…160000) applied; db lint clean.
  The Supabase MCP has no permission for this project; use the linked CLI (`supabase/.temp/project-ref`).
- Vercel project `reel-studio` (team_N7gyjjdCHX9K8ifMie5nzuV6, prj_VVWevgFfCwq7LgQauMu1B11RGzua,
  reel-studio-taupe.vercel.app): production `dpl_4UBCg8yyma5FXqu1ofa2EsAPZcWa` = commit 0981008. **Web changes after
  0981008 (animate toggle, Terms, landing, edit-studio types) are not deployed.** The project's Git link points at the
  old repo; deploy with the Vercel API `create_deployment` + `gitSource {type: github, repoId: 1431256555, ref: main, sha}`.
  Vercel env vars cannot be listed with this account (403).
- Engine: task "Reel Studio Engine" (logon + every 2 min, `conhost.exe --headless powershell … start-engine.ps1`),
  currently **Disabled**; Dev Tunnel URL stable.
- Instagram: unchanged OAuth/queue; publish nothing. Series scheduling creates real scheduled posts — not used.

## 13. Local setup and commands
**Engine on/off button (session 4):** desktop shortcut "Reel Studio Engine (on-off)" runs
`apps/api/engine-switch.ps1 -Action toggle` (windowless; a pop-up reports the result). Off = disables the "Reel Studio
Engine" task and stops only `app.serve`/`app.workers.run` processes (stays off after reboot); On = enables and starts
the task and waits for `/health`. Also `-Action start|stop|status` (add `-Quiet` for console output). Recreate the
shortcut: target `conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File
<repo>ppspi\engine-switch.ps1 -Action toggle`, icon `shell32.dll,27`.

```bash
# production engine
powershell -c "Enable-ScheduledTask -TaskName 'Reel Studio Engine'; Start-ScheduledTask -TaskName 'Reel Studio Engine'"
powershell -c "Disable-ScheduledTask -TaskName 'Reel Studio Engine'"   # then end app.serve / ollama processes
# local test stack (Docker Desktop running; if ports 54321+ fail: admin `net stop winnat` / `net start winnat`)
pnpm exec supabase start
sh .claude/local-engine.sh          # API :8001 + worker on local Supabase (git-ignored; local demo secret only)
cd apps/web && pnpm dev             # :3000 (.env.development.local → local stack)
# Mode B through the API (same calls as the web app); tokens expire after 1 h — poll with a fresh token
C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python apps/api/tests/e2e_mode_b.py OUT.mp4 --prompt "..." \
  --settings '{"duration_s":18,"brand_kit_id":"none"}' CLIP1 CLIP2
# photo animation smoke test (GPU must be idle; never during an owner render)
cd apps/api && python -c "from app.services import i2v; print(i2v.available())"
# checks
cd apps/api && python -m pytest -q && python -m ruff check .
cd apps/web && pnpm lint && npx tsc --noEmit && npx next build
cd packages/timeline-schema && pnpm test
pnpm exec supabase test db && pnpm exec supabase db lint --local --level warning
```
Editing on this machine: bash heredocs/`python -` turn `\n` and `\U` escapes into garbage — edit code with the editor
tool. Git Bash rewrites `/paths` in arguments (use `MSYS_NO_PATHCONV=1`). A requeued job: set `status=queued,
attempts=1, locked_by=null` in `jobs`. The worker requeues a stalled job after 3 min.

## 14. Media, references, outputs
Owner inputs: `C:\Users\Sahil\Downloads\` (reel template*.mp4, clip 1–17.mp4, phonk audio.mpeg). Outputs:
`C:\Users\Sahil\AppData\Local\reel-studio\data\mode-b-tests\` → `phase-f\{en,hi,hinglish}.mp4` + `narration\`,
`phase-d\eight-clips.mp4`, `test-b4\infographic.mp4`, `test-e2\before-after.mp4`, `test-h\{campaign-reel.mp4,campaign.json}`,
`test-b*/` (earlier failed attempts); `data\i2v-test\` (LTX smoke test); `data\voice-test\`. Production renders:
`data\orgs\8b94576a-…\renders\<id>\` (owner's HP Victus edit `a57b7786-b5a0-44b6-8093-25143d02c656`, perfume edit
`8faca5ae-…`). 2.0 UI screenshots (public test data): scratchpad `shots\`, landing `apps/web/public/landing/app-create.jpg`.

## 15. Known bugs and limitations
- HP Victus edit still has the four problems until re-rendered with this commit's fixes (§3).
- Text auto-fit runs once at load + after fonts load; it shrinks font sizes only (no re-wrap) — verify in a render.
- `content_box` samples three points per shot; footage whose bars change mid-shot may be cropped imperfectly.
- Blur-fill applies when the picture is ≥ 1.35× wider than the frame; zoom is ignored in that layout.
- LTX animation: ~2 min/photo; first conditioning-only version moved the subject out of frame.
- Campaign copy weak with the 7B model; QA `transitions_visible` failed on the infographic (designed scenes cover cuts).
- Overlay render needs RAM; a concurrent heavy GPU/RAM job can stall Chrome (watchdog + software fallback mitigate).
- Closed lid / manual Sleep takes the engine offline; Vercel web is behind `main` (§12).

## 16. Test results (end of session 3)
API pytest **136 passed / 6 skipped**; ruff clean; timeline schema **12/12**; web `tsc` + `eslint` clean; `next build`
(session 3, 27 routes) ✅; pgTAP 72/72 (session 3 local); production `db lint` clean. Rendered evidence in §2/§14.
Not run: HP Victus re-render, LTX both-ends re-test, transitions gallery for the six new transitions, tracked label in a
real edit, real-browser check of the landing card.

## 17. Remaining work (priority order)
0. **Bulk clipping (session 4):** run once on an authorised REAL two-person podcast through the production engine/UI
   (face framing, speaker switches, split screen, batch ZIP); then caption translation, SRT upload, AI B-roll from
   uploads, other aspect ratios. Details `docs/BULK_CLIPPING.md` § Not verified.
1. Re-render the owner's HP Victus edit with this commit's four fixes and check: text inside the frame, footage visible
   behind titles, no black bars (blur-fill), cuts on beat. (Engine must be re-enabled by the owner.)
2. Visually review Test B4/E2/H outputs; fix `transitions_visible` for designed scenes and the Test H black frames.
3. LTX both-ends re-test, then one real Mode B edit with "Animate my photos" from the UI.
4. Redeploy Vercel from current `main`; finish the landing card video from a render without private footage.
5. Galleries for the six new transitions and `tracked_tag`; owner's consented voice sample; campaign copy quality.

## 18. Precise next task
**Re-render HP Victus edit `a57b7786-b5a0-44b6-8093-25143d02c656` (production project) with the checkpoint fixes.**
Files: `apps/api/app/services/editing/{base,render,overlay,style_transfer}.py`, `app/services/rendering/{compose,motion}.py`.
Steps: owner enables the engine task; confirm `/health`; requeue the edit's job (`status=queued, attempts=1`); wait for
`ready`; contact sheet + QA. Acceptance: 20.000 s 1080×1920; no clipped text; titles over footage (no plain backdrop),
each ≤ 2.5 s; opening shot without black bars; QA `cuts_on_beat` and `no_unplanned_black` pass. Never run GPU tests
during the render.

## 19. Git
Branch `main`, remote `origin` = https://github.com/sahilkarande0918-cmd/Reel-Studio.git. Session-3 code head before
this checkpoint `bc4bd81`; the checkpoint commit follows it (see final report). `source` remote = Open_PS04_ (fetch
only). Identity `sahilkarande0918-cmd <sahilkarande0918@gmail.com>`; never AI authors/co-authors/trailers.

## 20. Environment variable names (values never in git)
- `apps/api/.env`: SUPABASE_URL, SUPABASE_SECRET_KEY, TOKEN_ENCRYPTION_KEY, ALLOWED_ORIGINS, DATA_DIR, OLLAMA_URL,
  OLLAMA_MODEL, PUBLIC_API_URL, SITE_URL, WHISPER_MODEL, WHISPER_LANGUAGE, INSTAGRAM_CLIENT_ID, INSTAGRAM_CLIENT_SECRET,
  INSTAGRAM_REDIRECT_URI, DIRECTOR_API_URL, DIRECTOR_API_KEY, DIRECTOR_MODEL (optional), VOICE_PYTHON, VIDEO_PYTHON,
  I2V_MODEL_DIR, BLENDER_PATH, HYPERFRAMES_CLI (optional overrides).
- `apps/web/.env.local` / Vercel: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_SITE_URL,
  NEXT_PUBLIC_API_URL (optional). `apps/web/.env.development.local` (ignored) → local stack.
