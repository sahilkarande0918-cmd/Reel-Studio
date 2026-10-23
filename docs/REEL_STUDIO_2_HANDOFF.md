# Reel Studio 2.0 — Technical Handoff (2026-10-24)

Read with `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full spec + status map). These two files take precedence over every
1.0 document. History of 1.0 lives in `CHECKPOINT.md` (below its 2.0 header), `IDE_HANDOFF.md`, `HANDOFF.md`, `PHASES.md`.

## 1. Repository and directory
| | Value |
|---|---|
| Work folder (only place to develop) | `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0` |
| Repository | https://github.com/sahilkarande0918-cmd/Reel-Studio.git, branch `main` |
| Remotes | `origin` = Reel-Studio (fetch+push); `source` = `Open_PS04_` (fetch only, push URL disabled) |
| Latest commit before this checkpoint | `de9729a` (see §18; the checkpoint commit follows it) |
| Git identity | `sahilkarande0918-cmd <sahilkarande0918@gmail.com>`; never AI authors/co-authors/trailers |
| Old folder / old repo | `C:\dev\Reel-Studio` → `origin` = https://github.com/sahilkarande0918-cmd/Open_PS04_ (the renamed original). Read-only history, BUT it still hosts the running production engine (Windows task "Reel Studio Engine" → `C:\dev\Reel-Studio\apps\api\start-engine.cmd`) and the Vercel project is still linked to `Open_PS04_` |

## 2. Architecture (2.0)
```
Next.js 16 web (Vercel, sin1)  ──JWT──►  FastAPI + durable worker (owner's RTX 5050 laptop, Dev Tunnel)
        │                                   │
   Supabase (Auth, Postgres+RLS, Realtime)  ├─ Mode A (1.0, working): ASR → context-aware highlights → reframe →
   project adjwycjsxtxvjockxtan (ap-se-1)   │   captions → Hyperframes compose → MP4 → Instagram
                                            └─ Mode B engine (2.0, script-driven so far):
     clips ─► clips/analysis.py ─┐
     music ─► music/beats.py ────┼─► editing/planner.py (+ pacing.py profiles, style_transfer.py from
     reference ─► reference/analyzer.py ─┘     a reference profile) ─► plan JSON
                                            plan ─► editing/render.py: base.py (FFmpeg segments + effects.py + xfade)
                                                    + audio.py (music, SFX, ducking, loudnorm) ─► mux ─► MP4
                                                    ─► editing/qa.py (measured checks on the file)
```
Planned (not built): Hyperframes motion-template layer over the base picture, AI Director (local Qwen JSON plan →
schema validation), renderer router incl. shader + headless Blender, Mode B API/UI/tables.

## 3. Implemented 2.0 code (all under `apps/api/`)
| File | What it does | Status |
|---|---|---|
| `app/services/reference/analyzer.py` | Reference Style Analyzer: probe, PySceneDetect shots (Content → Adaptive fallback), Farneback flow (motion, zoom divergence, pan), flashes, k-means palette, RapidOCR text, librosa beats + cut-to-beat offsets, optional Qwen-VL key-frame descriptions, techniques, contact sheet | ✅ run on 6 references |
| `app/services/music/beats.py` | `analyze()`: tempo from kick-band onsets folded to 80–160 BPM, beat grid, 4/4 downbeat phase, onsets, accents, energy (0.5 s), relative beat-snapped drops; `snap()`, `cut_offsets()` | ✅ ±3 BPM on 95–150 BPM tests; drops found on owner track (15.19 s), Ref 4 (3.67 s) |
| `app/services/music/score.py` | Original synthesized score (phonk / cinematic / commercial), royalty-free by construction | ✅ self-check |
| `app/services/clips/analysis.py` | Per-clip: motion, sharpness, brightness, framing centre (motion + visual interest), best moments; images; `proxy()` | ✅ on 17 owner clips |
| `app/services/editing/effects.py` | Typed registry: 24 effects (push_in, pull_out, punch_zoom, zoom_bounce, shake, pan, rotate, whip_pan, gaussian_blur, motion_blur, directional_blur, blur_reveal, zoom_blur, flash, rgb_split, glitch, contrast_snap, bright_pulse, vignette, grain, grade, glow, vhs, black_white) + 21 transitions mapped to FFmpeg xfade; param clamping; photosensitivity validation | ✅ 45/45 gallery |
| `app/services/editing/base.py` | `Segment`; cover-crop around focus + zoom; constant speed / eased ramps / reverse / freeze; effects chain; frame-count guard; `assemble()` concat/xfade with normalised timebase, padded to exact frames; even-frame transitions | ✅ |
| `app/services/editing/pacing.py` | 9 profiles (phonk, energetic, cinematic, clean_commercial, minimal, educational, product_showcase, motion_graphics, tech_ad), `hook_share`, `fx_params`, keyword `guess()` | ✅ unit-tested |
| `app/services/editing/planner.py` | Beat planner: music offset (drop at 30 % or hook end), slots on beats, best-moment source picking across clips, honest reuse (shift/zoom/reverse, recorded), ramps, hit effects on accents, flash rate limit (≤1/s), centred transitions, SFX cues | ✅ unit-tested |
| `app/services/editing/style_transfer.py` | Reference profile → pacing profile (hook, shot lengths in beats, transition mix, flash colour, punch-ins) + evidence list | ✅ unit-tested + used for owner reel |
| `app/services/editing/audio.py` | Synth SFX (whoosh peak-aligned, impact, riser, tick), `mix()` (music trim/fade, sidechain ducking under voice, two-pass loudnorm −14 LUFS / −2.5 dBTP), `measure()`, `mux()` with true-peak auto-repair (≤ −1 dBTP) | ✅ |
| `app/services/editing/render.py` | Plan → segments (frame-exact) → base picture → SFX → mix → mux | ✅ |
| `app/services/editing/qa.py` | Measured QA on the MP4 (length, hard cuts on frame, beat offsets, transition visibility, black/frozen, loudness) | ✅ |
| `tests/test_editing.py` | 10 unit tests | ✅ |
| `tests/effects_gallery.py`, `tests/auto_edit.py`, `tests/analyze_references.py` | Manual measured tools (render galleries, end-to-end edit + QA report, reference profiles) | ✅ run |

## 4. Incomplete 2.0 features
Everything marked 🟡/⬜ in the master plan status map: Mode B API/UI/tables and the replacement of Topic → Video;
multi-file resumable ingestion + `media_assets`; Hyperframes motion templates; AI Director; renderer router, GPU shader
layer, Blender + Blender MCP + headless worker; voice profiles (Chatterbox); 100 caption presets + ON/OFF; clip
collections; campaign agent; EN/HI/Hinglish localisation; UTM/click/WhatsApp results tracking; Instagram 2.0
extensions; quality engine items beyond §3 (`qa.py`); E2E tests B, C, D, E, G, H; Category G composites, frame
interpolation, region-of-interest shot detection, manual beat correction.

## 5. Mode A / Mode B status
- **Mode A (1.0, preserved):** working in production from the old folder (upload → Hinglish ASR → context-aware
  highlights with teaching-step outline → reframing → captions/brand kits → editor → Hyperframes MP4 → Instagram).
  2.0 additions (music, effects, 100 captions, collections…) not started.
- **Mode B:** the old Topic → Video (JSON/XML storyboard) is still what the app shows. The new prompt-to-edit engine
  exists as Python services + scripts only; no API endpoints, worker job type, tables or UI yet.

## 6. Commands
```bash
# Python venv (shared, outside the repo)
C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python
# install API deps (librosa added to requirements/vision.txt)
C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python -m pip install -r apps/api/requirements/dev.txt
# web
pnpm install --frozen-lockfile
cd apps/web && npx next typegen && pnpm dev            # :3000 (uses apps/web/.env.local)
# local Supabase stack (Docker) — only for local tests
pnpm exec supabase start
# API + worker locally against the local stack (port 8001), from apps/api:
SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_SECRET_KEY=<local secret> PUBLIC_API_URL=http://127.0.0.1:8001 \
  C:/Users/Sahil/AppData/Local/reel-studio/venv/Scripts/python -m app.serve --tunnel none --port 8001
# production engine (API :8000 + worker + Dev Tunnel) — currently runs from C:\dev\Reel-Studio:
C:\dev\Reel-Studio\apps\api\start-engine.cmd   (also Windows task "Reel Studio Engine" at logon)
# Ollama (does NOT auto-start after reboot)
"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve      # check: curl localhost:11434/api/tags
# Mode B engine, end to end (from apps/api, PYTHONPATH=.):
python tests/auto_edit.py OUT_DIR --profile phonk --duration 16 --music "C:/Users/Sahil/Downloads/phonk audio.mpeg" \
  --reference C:/Users/Sahil/AppData/Local/reel-studio/data/reference-analysis/reel-template-4/style.json CLIP...
python tests/effects_gallery.py SOURCE.mp4 OUT_DIR 60
python tests/analyze_references.py OUT_DIR VIDEO... --describe 4
# checks
cd apps/api && python -m pytest -q && python -m ruff check .
cd apps/web && pnpm lint && npx tsc --noEmit && npx next build
cd packages/timeline-schema && pnpm test
```

## 7. Rendering pipelines
- 1.0 (Mode A, Topic): timeline JSON → `services/rendering/compose.py` → Hyperframes 0.8.164 CLI → MP4
  (`workers/render.py`, silent-render guard, Instagram delivery copy).
- 2.0 engine: plan JSON → `editing/render.py` (FFmpeg segments, xfade, separate audio, mux) → `editing/qa.py`. Picture
  and sound are rendered separately and muxed (no drift). Not yet merged with the Hyperframes layer.

## 8. Beat detection, effects, transitions — source files
`app/services/music/beats.py`, `app/services/editing/effects.py` (`EFFECTS`, `TRANSITIONS`), `app/services/editing/base.py`
(`assemble`), `app/services/editing/planner.py`, `app/services/editing/pacing.py`, `app/services/editing/style_transfer.py`.

## 9. Canonical timeline schema
`packages/timeline-schema/src/index.ts` (Zod, source of truth) → `timeline.schema.json` (`pnpm build:schema`) → Python
`jsonschema` validation (`services/rendering/timeline.py`). Items: video (crop keyframes), caption, audio, code, text;
`Brand`, `CaptionStyle`, `StylePreset`. **Not yet extended for 2.0**: the Mode B plan JSON is separate today
(`planner.plan()` output). The master plan requires extending the canonical schema (speed/ramps, effects with keyframes,
transitions, graphics templates, beat anchors, music automation, renderer selection, reuse metadata) instead of a
competing format — do this before building the Mode B UI/editor integration.

## 10. UI status
Forest-green/ivory UI is final (no redesign). Shared logo (Aperture mark) on landing, sign-in and app. No 2.0 screens
exist yet. Topic Studio (old Mode B) still present.

## 11. Supabase and Vercel
- Supabase project `adjwycjsxtxvjockxtan` only; `supabase/.temp/project-ref` copied locally (ignored). No 2.0
  migrations yet; every new table needs RLS + explicit grants (D-025).
- Vercel project `reel-studio` (team `team_N7gyjjdCHX9K8ifMie5nzuV6`, prj_VVWevgFfCwq7LgQauMu1B11RGzua) is linked to the
  **old** repo `Open_PS04_` (Vercel status checks appear there, none on Reel-Studio commits). Pushing to Reel-Studio does
  not deploy. Re-linking production to the new repo is a deliberate owner decision (check env vars, regions sin1).

## 12. Environment variable NAMES (values only in ignored files / dashboards)
- `apps/web/.env.local` / Vercel: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SITE_URL`,
  `NEXT_PUBLIC_API_URL` (optional).
- `apps/api/.env`: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `ALLOWED_ORIGINS`, `DATA_DIR`, `OLLAMA_URL`,
  `PUBLIC_API_URL`, `WHISPER_MODEL`, `WHISPER_LANGUAGE`, `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET`, `INSTAGRAM_REDIRECT_URI`.
- Both env files were copied into the 2.0 folder (ignored by git).

## 13. Models and dependencies
Local: faster-whisper with converted Oriserve Hinglish model (`%LOCALAPPDATA%\reel-studio\data\models`), Ollama
`qwen2.5vl:7b`, Kokoro (via `hyperframes tts`), RapidOCR ONNX, FFmpeg 8.1.2 full (gyan.dev), Hyperframes 0.8.164 (npx),
Node + pnpm, Python 3.11 venv with OpenCV 5.0, PySceneDetect 0.6.7, librosa 0.11.0 (new, ISC). Hardware: RTX 5050
Laptop 8 GB — load one heavy model at a time.

## 14. Blender
**Not installed** (`C:\Program Files\Blender Foundation` absent; no `blender` on PATH). **Blender MCP
(`ahujasid/mcp-for-blender`, MIT) is NOT configured.** Phase 8 must install Blender (free, GPL) and the MCP add-on for
development only, and build a separate headless worker that accepts validated scene templates (no user Python).

## 15. Model downloads still required for future phases
Chatterbox (MIT; multilingual weights, PerTh watermark) for voice profiles; optionally MediaPipe segmentation models
(Apache-2.0), SAM 2 tiny/small (Apache-2.0), Depth-Anything-V2 **Small only** (Apache-2.0; larger sizes CC-BY-NC),
Practical-RIFE (MIT) for interpolation. None downloaded yet. Downloads need internet once; the owner approved these tools
in the master prompt, but state filename/size when downloading.

## 16. Known bugs and limitations
- Production engine on :8000 was **not responding** at checkpoint time (it runs from the old folder; restart with
  `start-engine.cmd`). Ollama does not auto-start after a reboot.
- Owner test clips are ~478×850 → upscaled 2.3× to 1080×1920 (soft).
- Shot detection under-counts on fixed layouts / filmed screens (Ref 1, 2, 6): needs region-of-interest detection.
- Local VLM descriptions invent details; treat as model text only.
- Clip 17 (owner) is nearly black and is never picked (dark penalty).
- `opencv-python-headless==4.*` in requirements while the venv has OpenCV 5.0 (works; pin later).
- Two class recordings in production data carry third-party branding (e.g. "Pradeep Giri"); internal tests only.
- The 2.0 plan JSON is not yet the canonical timeline (see §9).
- The working folder is inside OneDrive: avoid syncing `node_modules`/`.next` (consider excluding them from OneDrive).

## 17. Testing evidence (2026-10-23/24)
| Test | Result |
|---|---|
| API pytest / ruff | 107 passed, 6 skipped / clean |
| Web tsc / lint | clean / clean (route types via `npx next typegen` in a fresh clone) |
| Timeline schema vitest | 12 passed |
| Effects gallery (`effects_gallery.py`) | 24/24 effects visibly change the picture, 21/21 transitions exact frame counts |
| Two-clip engine test | 16 s, 480 frames, −14.5 LUFS, −1.6 dBTP (internal, third-party footage) |
| Owner phonk reel (17 clips + phonk audio + Ref 4 style) | 480/480 frames; 3 hard cuts on planned frame (0 ms), ≤10 ms from beat; 7 whips/flashes centred ≤15 ms from beat and visible; no unplanned black/frozen; −14.0 LUFS, −2.2 dBTP; render 65 s |
| Reference analysis | Ref 4: 143.6 BPM, 89 % cuts ≤60 ms of a beat (median 28 ms), median shot 0.87 s |

## 18. Commit history (2.0, newest first)
`de9729a` style transfer + QA + frame-exact transitions · `5022673` checkpoint pointer · `6580218` engine core ·
`8f3fef0` reference analyzer + research · `2653a14` migration record · `6e94ddf` (rewritten history tip of 1.0:
context-aware AI editing). Full log: `git log --oneline`.

## 19. Local outputs and reference assets
See master plan Part 1 ("Generated outputs", "Owner-supplied inputs"). Data root:
`C:\Users\Sahil\AppData\Local\reel-studio\data\` (`mode-b-tests\`, `effects-gallery\`, `reference-analysis\`, `orgs\…`
recordings/renders, `models\`). Owner inputs in `C:\Users\Sahil\Downloads\`. Nothing of this is in git.

## 20. Offline vs online
Offline OK: Mode B engine (clip analysis, beats, planning, FFmpeg render, audio, QA), reference analysis, local Ollama,
Whisper, Kokoro, Hyperframes render (fonts/GSAP bundled), tests. Needs internet: Supabase (auth, DB, Realtime), Vercel
frontend, Dev Tunnel, Instagram API, GitHub push, first-time model/package downloads, `npx hyperframes` first fetch.

## Next step (owner has not chosen yet)
Proposed order: (1) extend the canonical timeline for 2.0 + Mode B API/worker job + Mode B UI replacing Topic → Video +
AI Director (local Qwen JSON plan, validated); (2) Hyperframes motion templates + 100 caption presets/ON-OFF;
(3) campaign agent + EN/HI/Hinglish + results tracking; (4) voice profiles; (5) Blender + router.
