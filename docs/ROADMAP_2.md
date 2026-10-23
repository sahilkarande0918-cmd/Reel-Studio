# Reel Studio 2.0 — roadmap and architecture (from 2026-10-23)

> Full spec and the authoritative status map: `REEL_STUDIO_2_MASTER_PLAN.md`; handoff: `REEL_STUDIO_2_HANDOFF.md`.

The owner's Reel Studio 2.0 master prompt supersedes the old roadmap where they conflict. `ORIGINAL_PS.md`,
`MASTER_PROMPT.md` and `PHASES.md` stay as history. Repository: https://github.com/sahilkarande0918-cmd/Reel-Studio
(migrated with full history, see `MIGRATION.md`); local folder `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`.

## Product: exactly two modes
- **Mode A — Recording → Reels** (kept and extended): upload → transcribe → context-aware highlights (teaching steps,
  five-component score) → smart 9:16 crop → captions → motion effects → editor → render → Instagram. Adds music + beat
  sync, effects, caption ON/OFF + 100 styles, voice profiles, clip collections, campaigns, QA.
- **Mode B — Prompt → Professional edit** (replaces Topic → Video in the UI; old topic projects stay readable):
  many clips/images/screenshots + optional music + optional reference reel + a prompt (even "make a professional
  phonk edit") + duration/aspect/brand/caption style/voice → AI Director plan → effects + motion design → render →
  edit/export → Instagram.

## Architecture (one timeline, many renderers)
```
media assets ─► per-asset analysis (ffprobe, PySceneDetect, optical flow, palette, moments, VLM tags)
music ───────► beats.py (tempo, beats, downbeats, accents, energy, drops)             ┐
reference ───► reference/analyzer.py (shots, transitions, flashes, motion, text, beat sync) ├─► AI Director
prompt/brand/output settings ─────────────────────────────────────────────────────┘   (local Qwen → JSON plan,
                                                                                         schema-validated; deterministic
                                                                                         beat/frame snapping)
                         canonical timeline (packages/timeline-schema, extended)
                                   │
            renderer router: simplest renderer that can do each layer
     ┌──────────────┬─────────────────────┬──────────────────────┬────────────────┐
  FFmpeg/OpenCV   Hyperframes + GSAP     WebGL shaders (in HF)   Blender (headless,
  base picture:   typography, cards,     gl-transitions MIT       validated templates
  cut/crop/speed/ mockups, captions,     shaders                  only, real 3D)
  blur/RGB/flash/ masks, designed scenes
  grade/xfade
     └──────────────┴──── same frame clock (fps grid) ┴──────────────────────┘
  audio rendered separately (music + SFX + voice, ducking, −14 LUFS) → mux → QA engine (measured) → MP4
```
Rules carried from the guide and our own verified practice: one plan file holds every time; cuts on the frame grid;
picture and sound rendered separately and muxed; QA measures the actual file.

## Phase list (status kept current in `CHECKPOINT.md`)
| # | Phase | Status |
|---|---|---|
| A | Repository migration (full history, verified) | ✅ `2653a14` |
| 1 | Reference analysis + open-source tool audit | ✅ (`REFERENCE_STYLE_ANALYSIS.md`, `OPEN_SOURCE_TOOL_AUDIT.md`) |
| 2 | Unrestricted-count clip ingestion (chunked/resumable, proxies, dedupe, analysis queue) | 🟡 per-clip analysis only (`clips/analysis.py`) |
| 3 | Reference Style Analyzer (reusable, report) | 🟡 analyzer built (`services/reference/analyzer.py`), UI/report pending |
| 4 | Music + beat sync, pacing profiles, phonk | 🟡 engine verified on the owner's phonk reel; app integration pending |
| 5 | Effects engine (typed registry, every effect renders) | 🟡 24 effects + 21 transitions verified; velocity/composites/shaders pending |
| 6 | Motion design engine (Hyperframes templates) | 🟡 26 templates verified; ad re-render pending |
| 7 | AI Editing Director | ✅ distinct outputs per prompt (session 2) |
| 8 | Renderer router (+ Blender worker) | ✅ FFmpeg / Hyperframes / Blender routing; shader layer ⬜ |
| 9 | Voice profiles (Chatterbox) | 🟡 built, not yet run |
| 10 | 100 caption styles + ON/OFF | ✅ |
| 11 | AI clip collections (Mode A) | ✅ (synthetic lecture) |
| 12 | Business campaign agent | 🟡 works; copy quality open; tracking built |
| 13 | Instagram automation extensions | 🟡 cover/suggestions/campaign link; nothing published |
| 14 | Video quality engine | 🟡 `editing/qa.py` (length, cuts, beats, black/frozen, loudness) |
| 15 | End-to-end validation tests A–H | 🟡 A ✅, C/D/F/G/H partial, B/E ⬜ |

## Inputs still needed from the owner
Real test media the product may legally use: raw product clips (e.g. a shoe store), a licensed or self-made phonk
track, a voice sample the owner records and authorises, and real business details for the campaign test. The
reference reels are analysed for technique only; their footage, branding and audio are never reused in outputs.
