# Third-party inventory

Reviewed 2026-10-16 via GitHub API (licence SPDX, archived flag, last push). Re-check before release.

## Integrated / planned runtime dependencies

| Project | Licence | Status | Use in Reel Studio |
|---------|---------|--------|--------------------|
| heygen-com/hyperframes (CLI v0.8.164, `@hyperframes/player`) | Apache-2.0 | active | Principal renderer; editor preview player; local Kokoro TTS (`hyperframes tts`) |
| SYSTRAN/faster-whisper | MIT | active | Speech recognition with word timestamps |
| m-bain/whisperX | BSD-2-Clause | active | Word-level forced alignment (where reliable) |
| Breakthrough/PySceneDetect | BSD-3-Clause | active | Scene-change detection |
| OpenCV (opencv-python) | Apache-2.0 | active | Frame analysis, motion, region tracking |
| ollama/ollama | MIT | active | Local LLM runtime |
| hexgrad/kokoro (Kokoro-82M weights) | Apache-2.0 | active | Local TTS voice model (via Hyperframes) |
| remsky/Kokoro-FastAPI | Apache-2.0 | active | Optional TTS server — not adopted yet (D-010) |
| FFmpeg 8.1 (gyan.dev full build) | GPL-3.0 build (LGPL core) | system binary | Media extraction/transcode; invoked as a separate process, not linked |
| Next.js / React | MIT | — | Frontend |
| Tailwind CSS | MIT | — | Styling |
| Radix UI primitives | MIT | — | Accessible primitives |
| Zustand | MIT | — | Editor state |
| TanStack Query | MIT | — | Request state |
| Lucide | ISC | — | Icons |
| Zod | MIT | — | Canonical timeline schema |
| FastAPI / Pydantic / Uvicorn | MIT / MIT / BSD-3 | — | Backend |
| pyca/cryptography (50.0.2) | Apache-2.0 OR BSD-3-Clause | active | Backend AES-GCM encryption of OAuth credentials |
| supabase-js / @supabase/ssr / supabase-py | MIT | — | Supabase clients |

LLM weights (Qwen family candidates) — licence verified per exact model in Phase 03 before use.

## Engineering / design tooling (not shipped)

| Project | Licence | Notes |
|---------|---------|-------|
| DietrichGebert/ponytail | MIT | Installed Claude Code plugin; mandatory review/audit discipline |
| Leonxlnx/taste-skill | MIT | Design direction skill |
| Nutlope/hallmark | MIT | Design audit skill (installed) |
| 21st-dev/magic-mcp | ISC | Optional; not enabled — hosted generation may not be free (Section 5.5) |
| unovue/inspira-ui | MIT | Reference only (Vue) — no Vue runtime added |

## Editor references

| Project | Licence | Decision |
|---------|---------|----------|
| OpenCut-app/opencut-classic | MIT, **archived** | Reference for timeline interaction patterns; any copied code keeps its MIT notice |
| opencutvideo/Opencut | **No licence file** | Do not copy code (all rights reserved by default) |
| openvideodev/react-video-editor | **NOASSERTION (custom)** | Do not adopt; custom licence terms not verified for our use |

Decision: custom React timeline (D-011/Phase 06), built on permissive primitives only.

## Social integration references

| Project | Licence | Notes |
|---------|---------|-------|
| adelaidasofia/instagram-mcp | MIT | Reference for official Graph API flow; review token handling before reuse |
| Burak-cell-max/instagram-mcp-panel | MIT | Scheduling-panel reference; 0 stars, very new — read-only reference |

## Notices
Hyperframes (Apache-2.0) requires preserving its LICENSE/NOTICE if we redistribute its code. We consume it as an npm dependency; attribution is listed in README.

## Added in Phase 02
| Project | Licence | Use |
|---------|---------|-----|
| Oriserve/Whisper-Hindi2Hinglish-Apex (weights) | Apache-2.0 | ASR model, converted locally to CTranslate2 |
| CTranslate2 / faster-whisper | MIT | ASR runtime |
| nvidia-cublas-cu12, nvidia-cudnn-cu12 (pip wheels) | NVIDIA proprietary redistributable (free) | CUDA runtime libraries for local GPU inference; not redistributed by us |
| opencv-python-headless | Apache-2.0 (OpenCV), MIT wrapper | Screen activity analysis |
| scenedetect (PySceneDetect) | BSD-3-Clause | Scene cuts (Phase 03) |
| kokoro-onnx | MIT | Local Kokoro TTS runtime used by `hyperframes tts` |
| Windows OneCore voices (Microsoft Ravi/Heera, en-IN) | bundled with Windows | Test-fixture narration only; not shipped |

Test audio: Oriserve model-repo sample clips (Common Voice, CC0) used for local spot checks; not committed.

## Added in Phase 04
| Project | Licence | Use |
|---------|---------|-----|
| zod 4 | MIT | Canonical timeline schema (`packages/timeline-schema`) |
| vitest 5 | MIT | Schema tests |
| jsonschema (Python) | MIT | Validates timelines against the generated JSON Schema |
| Archivo (Omnibus-Type), JetBrains Mono (JetBrains) via @fontsource 5.3.0 | SIL OFL 1.1 | Caption fonts bundled into renders; licence texts in `apps/api/app/services/rendering/fonts/` |
| DM Sans, Fraunces, JetBrains Mono (Google Fonts distributions) | SIL OFL 1.1 | Local Latin WOFF2 files for the web UI in `apps/web/app/fonts/`; copyright and license texts alongside each font. Self-hosted so the production build needs no Google Fonts network request. |
| GSAP 3.14.2 (bundled: `apps/api/app/services/rendering/vendor/gsap.min.js`, copied into each render) | GSAP Standard "No Charge" licence (free incl. commercial; the Webflow-published terms restrict only no-code visual animation builders competing with Webflow — not our use) | Composition timeline |
| Microsoft Dev Tunnels CLI 1.0.2115 | Microsoft licence terms (free service) | Public HTTPS tunnel to the local backend; installed with winget, not redistributed |
| Poppins (Indian Type Foundry), Noto Sans (Google), Fira Code (Nikita Prokopov) via @fontsource 5.3.0 | SIL OFL 1.1 | Brand kit fonts, bundled into renders and `apps/web/public/brand-fonts`; licence texts beside the font files |

## Added for Reel Studio 2.0 (2026-10-23)
| Project | Licence | Use |
|---------|---------|-----|
| librosa 0.11 | ISC | Music analysis: tempo, beats, downbeats, onsets, energy, drops (`app/services/music/beats.py`) |
| FFmpeg filters (xfade, gblur, dblur, tblend, rgbashift, eq, colorbalance, vignette, noise, rotate, loudnorm, ebur128, sidechaincompress) | FFmpeg build is GPL-3 (gyan.dev full build), invoked as an external binary | Base-picture effects, transitions, audio mix and loudness |

Studied, not copied (see `OPEN_SOURCE_TOOL_AUDIT.md`): herk-edit-kit (MIT), video-director-skill (MIT), AIvideokit (MIT),
free247editor (MIT), vertical-video-editing-skill (MIT), claude-motion-graphics (no licence: ideas only).
Synthesized score and SFX (`music/score.py`, `editing/audio.py`) are original, generated in code.
