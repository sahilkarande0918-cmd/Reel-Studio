# Reel Studio

**The AI video studio for technical educators.**
Turn recorded programming classes and one-line topics into branded, ready-to-publish 9:16 reels, with Hinglish-aware transcription, correctly spelled technical terms and framing that follows the code instead of cropping the centre.

Live app: https://reel-studio-taupe.vercel.app (with a 60-second product tour rendered in Hyperframes) · Hackathon PS4 · Runs at **₹0** (open-source models on our own GPU machine, free tiers only).

## What it does
| Mode | Input | Output |
|------|-------|--------|
| **Recording → Reels** | A long screen-share class recording | Ranked 30–60 s highlights that start and end on complete thoughts, smart 9:16 crop that follows the active code, word-synced Hinglish captions, brand kit |
| **Topic → Video** | A topic such as `JSON vs XML` | ~45 s explainer: AI script and storyboard (editable), animated code cards, local voiceover, synced captions, branding |

Both modes share:
- **Creative editor**: multitrack timeline (video, audio, captions, text, code), split, trim, move, duplicate, caption word editing, overlays, fades, transitions, crop framing, brand kits, undo/redo, autosaved drafts. The preview is produced by the same compiler as the export.
- **Style presets**: Focus, Energy, Story and Signature change the rendered MP4 (transitions, caption typography, push-ins, branded lower third).
- **Instagram publishing**: official Instagram API with Instagram Login, encrypted tokens, publish now or schedule, a queue with calendar, safe retries and duplicate prevention.
- **Analytics and AI feedback**: real per-reel Instagram insights, comparison and trend charts. Once at least 3 published reels have metrics, local-LLM recommendations and a learned ideal length feed back into highlight scoring.

## Architecture
```
Browser (Next.js 16 on Vercel)  ──►  Supabase (Auth, Postgres + RLS, Realtime)
        │                                  ▲
        └── signed HTTPS (Microsoft Dev Tunnel) ──► FastAPI + durable worker on a local GPU machine
                                                   faster-whisper · OpenCV · RapidOCR · Ollama (Qwen2.5-VL)
                                                   Kokoro TTS · Hyperframes renderer · FFmpeg
```
One canonical timeline (Zod schema → JSON Schema) is produced by both AI pipelines, edited in the editor, previewed and rendered by a single Python compiler into a Hyperframes composition, then verified with ffprobe. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), decisions in [docs/DECISIONS.md](docs/DECISIONS.md).

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, TanStack Query, Lucide |
| Backend | Python 3.11, FastAPI, Pydantic, Supabase-backed durable job queue |
| AI / media | faster-whisper (Hinglish model), OpenCV, RapidOCR, Ollama `qwen2.5vl:7b`, Kokoro TTS, FFmpeg |
| Rendering | Hyperframes 0.8.164 (local), GSAP, bundled OFL fonts |
| Data | Supabase Postgres + RLS, Auth, Realtime |

## Repository layout
```
apps/web                  Next.js app (studios, editor, publishing, analytics)
apps/api                  FastAPI API + worker (transcribe, analyze, generate, render, publish, insights)
packages/timeline-schema  canonical timeline (Zod → JSON Schema) and pure editor operations
supabase/migrations       schema, RLS policies, explicit grants
docs/                     checkpoint, phases, decisions, test status, deployment
```

## Demo flow (5 minutes)
1. **Dashboard**: real projects, renders, jobs and upcoming posts.
2. **Topic Studio**: type "JSON vs XML", choose a style, generate. Watch Script → Voiceover → Render progress, edit the script and re-render, then download the MP4 and SRT/VTT.
3. **Recordings**: open a class recording. Search the transcript (corrected terms are underlined), review ranked highlights with reasons, adjust the crop, render.
4. **Editor**: open the reel, split and trim, change a caption word, add a text overlay, switch to the Signature style, render, and download the new MP4.
5. **Publish** (after the Instagram Business account is connected): pick the reel, add a caption and hashtags, schedule it, and watch the queue.
6. **Analytics**: refresh from Instagram, compare reels, run AI feedback.

## Running locally
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md). In short: `pnpm install`, `pnpm --filter web dev`, and on the GPU machine `cd apps/api && python -m app.serve --tunnel devtunnel` (API, worker and tunnel together; Ollama must be running).

## What was tested, and how
Every claim is recorded in [docs/TEST_STATUS.md](docs/TEST_STATUS.md), which marks whether a test used **synthetic recordings**, the owner's **real physics class**, or **production**. Instagram publishing and insights are not claimed as verified until real authorised API responses confirm them.

## Team
| GitHub |
|--------|
| [@sahilkarande0918-cmd](https://github.com/sahilkarande0918-cmd) |
| [@sahillokhande5841-cmyk](https://github.com/sahillokhande5841-cmyk) |
| [@Atharva486dherange](https://github.com/Atharva486dherange) |
| [@SK999CodingWorld](https://github.com/SK999CodingWorld) |

## Acknowledgements
Built on [Hyperframes](https://github.com/heygen-com/hyperframes) (Apache-2.0), [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT), [Ollama](https://github.com/ollama/ollama) (MIT), [Kokoro](https://github.com/hexgrad/kokoro) (Apache-2.0), RapidOCR, FFmpeg, OpenCV, GSAP and Supabase. Full inventory: [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md).

## Licence
MIT — see [LICENSE](LICENSE).
