# Decisions

Format: ID — decision. *Alternatives* · *Why* · *Trade-off*.

## D-001 — Hyperframes CLI as the only renderer
*Alt:* Remotion (company license needed above a size threshold), raw FFmpeg filter graphs, MoviePy.
*Why:* Mandated; Apache-2.0; HTML/CSS compositions give us code animation, captions, brand intros with one engine; deterministic local render; `@hyperframes/player` previews the same composition in the browser → preview/export parity.
*Trade-off:* Needs Node 22+ and headless Chrome on the render machine; render is slower than a pure FFmpeg trim. Cloud/Lambda render paths are never used (₹0).

## D-002 — Canonical timeline in Zod (`packages/timeline-schema`), JSON Schema for Python
*Alt:* Pydantic as source + generated TS; hand-maintained twin schemas.
*Why:* The editor and the compiler (both TS) are the heaviest consumers. One definition, exported JSON Schema validates Python-generated timelines in tests and at the API boundary.
*Trade-off:* Python sees the timeline as validated JSON rather than rich typed objects.

## D-003 — Jobs live in Supabase Postgres, claimed with SKIP LOCKED via RPC
*Alt:* Redis/RQ, Celery, local SQLite queue.
*Why:* Durable across restarts, already provisioned, Realtime gives free progress streaming to the UI, no extra service to run.
*Trade-off:* Worker depends on internet to Supabase; poll latency ~1–2 s.

## D-004 — Backend URL discovery through Supabase heartbeat
*Alt:* Hard-code tunnel URL in Vercel env (redeploy on every change); paid static tunnel.
*Why:* Free quick tunnels change URL on restart. Backend writes its URL + heartbeat to `backend_endpoints`; frontend reads it and shows a truthful offline state when stale.
*Trade-off:* Extra table; a stale URL window of one heartbeat interval.

## D-005 — Tunnel: Cloudflare quick tunnel (primary), ngrok free static domain (fallback)
*Why:* No account, no bandwidth cap stated for quick tunnels; ngrok free has a monthly data cap that video uploads would exhaust. Cloudflare limits request bodies (~100 MB), so uploads are chunked (D-006).
*Trade-off:* Quick-tunnel URLs are ephemeral and best-effort; documented in DEPLOYMENT.md.
*Update 2026-10-16:* verified that the owner's current network blocks outbound port 7844 (TCP and UDP), which Cloudflare tunnels require (`cloudflared` pre-checks: QUIC FAIL, HTTP/2 FAIL). Added **Tailscale Funnel** (free personal plan, outbound 443 only, stable `*.ts.net` URL) as the second option in `python -m app.serve --tunnel tailscale`. ngrok rejected as default: free plan data-transfer cap is too small for video uploads.

## D-006 — Chunked resumable uploads straight to the local API
*Alt:* tus server, Supabase Storage (1 GB free total, 50 MB per-file limit on Free).
*Why:* Recordings are hundreds of MB; they must land on the GPU machine anyway. Fixed-size chunks with offset resume stay under tunnel body limits.
*Trade-off:* Upload only works while the backend is online (UI says so).

## D-007 — Fold `shared-types` and `ui` packages until a second consumer exists
*Why:* Ponytail/YAGNI — UI components have one consumer (`apps/web`); shared types are the timeline schema. Recreate the packages if a second app appears.

## D-008 — Python 3.11 venv for the backend
*Alt:* System Python 3.13/3.14.
*Why:* CTranslate2 / faster-whisper / WhisperX / PyTorch wheels are most reliable on 3.11; the machine has 3.11 installed.

## D-009 — Local LLM via Ollama, ~7–8B instruct model (Q4)
*Why:* 8 GB VRAM. A Q4 7–8B model (~5 GB) fits when Whisper is unloaded. Models used strictly sequentially. Exact model chosen and licence-checked in Phase 03 (candidates: Qwen2.5-7B-Instruct / Qwen3-8B, Apache-2.0). `qwen2.5vl:7b` already pulled — usable for screen understanding.

## D-010 — TTS via `hyperframes tts` (local Kokoro-82M)
*Alt:* `kokoro` Python package, Kokoro-FastAPI server.
*Why:* Already bundled with the mandated renderer, local, Apache-2.0 weights, no extra service. Kokoro-FastAPI stays an option if we need streaming or more control.

## D-011 — Frontend UI primitives: Radix (via shadcn-style copied components) + Tailwind
*Why:* Accessible primitives, no second UI system, components live in our repo.

## D-012 — Repository licence: MIT
*Why:* Permissive, compatible with all integrated dependencies (Apache-2.0, MIT, BSD). Owner may change before submission.

## D-013 — No AI attribution trailers
The coding harness suggests `Co-Authored-By` trailers; the project owner's explicit rule forbids AI attribution, and owner instructions take precedence. Commits carry only the operator's own identity.

## D-014 — Next.js 16 without `cacheComponents`
*Alt:* keep the template's `cacheComponents` + partial prefetching.
*Why:* Nearly every app route reads the Supabase session; with Cache Components each session read must sit behind Suspense or the build fails. Plain dynamic rendering is simpler and sufficient for an authenticated SaaS. Landing page stays static by default.
*Trade-off:* No static shell for authenticated pages.

## D-015 — ASR model: Oriserve Whisper-Hindi2Hinglish-Apex via faster-whisper
*Alt:* stock Whisper large-v3 / large-v3-turbo; Hub84's pre-converted CT2 copy.
*Why:* Stock Whisper writes Hindi in Devanagari (or translates it to English when forced to `en`), neither of which is how Indian educators caption reels. Apex (Apache-2.0, fine-tuned from large-v3-turbo on ~700 h of Indian-accented Hindi) transcribes to Roman-script Hinglish and reports much lower WER than large-v3 on Hinglish-transliterated references (model card: FLEURS 29.8 vs 50.8). Turbo base keeps it fast and inside 8 GB. We convert the official safetensors ourselves (`scripts/convert-hinglish-model.sh`) rather than trust an unverified third-party conversion.
*Trade-off:* Model-card numbers are the authors'; our own spot checks are recorded in TEST_STATUS. `task="transcribe"` always, never translate.

## D-016 — Word timing: faster-whisper cross-attention timestamps; WhisperX alignment deferred
*Why:* WhisperX aligns with a per-language wav2vec2 phoneme model. Its Hindi models expect Devanagari, so they cannot align Roman-script Hinglish text, which is our main case. faster-whisper's word timestamps (DTW over cross-attention) are available for every language. WhisperX would also add a ~3 GB CUDA PyTorch install for Blackwell (cu128).
*Plan:* Optional WhisperX stage for English-language recordings only, if time permits. `transcripts.word_timing` records which method produced the timings. Not implemented yet; the PS's word-level timing requirement is met by faster-whisper.

## D-017 — Blackwell (RTX 5050, sm_120) runs CTranslate2 through JIT
Measured: the first GPU transcription took 275 s for a 28 s clip (kernel JIT compilation); later runs took 1.35 s with `base`. `CUDA_CACHE_MAXSIZE` is raised to 4 GB so compiled kernels persist across worker restarts. Warm up the worker before a demo.

## D-018 — OCR: RapidOCR (ONNX, CPU) and screen-evidence term correction
*Alt:* Tesseract (system install, weaker on code fonts), PaddleOCR (heavier), GPU OCR.
*Why:* pip-only, Apache-2.0, accurate on editor text (reads `new AbortController()` at 0.98). Identifiers seen on screen within ±30 s correct ASR mishearings ("about controller" → `AbortController`); a merge may not start with a Hinglish function word and must not swallow a leading word; user edits always win.
*Trade-off:* ~3–6 s per frame on CPU (35 frames = 220 s for the 3-min lecture); capped at 90 frames per recording. Upgrade path: onnxruntime-gpu.

## D-019 — Highlight scoring: transparent heuristic + local LLM, vetoes only on agreement
Boundaries are sentence ends followed by pauses ranked against the speaker's own pause distribution (strict pool: both ends in the top 40 %). Features: boundary, length, voice energy/variation, pace, typing/screen activity, technical terms and spoken on-screen identifiers. The local LLM (Ollama `qwen2.5vl:7b`, temperature 0) adds standalone/educational/complete-start/end; a window is dropped only when the LLM says both ends are incomplete *and* pauses are not strong; one-sided doubts become a visible "check the start/end" reason. Scores are labelled `heuristic` / `heuristic+llm`, never presented as probabilities. Thresholds were tuned on the synthetic lecture — real-class tuning pending.

## D-020 — Reframing: deterministic keyframes, hysteresis, fixed panel zoom
Activity boxes (2 fps change map) and OCR text regions drive a virtual camera with dead zone, speed cap and easing; window switches are hard cuts. Lines wider than a 9:16 slice switch to a fixed 1200-px "panel" (one zoom level, ~0.9× at 1080-wide portrait) instead of zooming until code is cut. Layout changes need 3 consecutive samples (1.5 s). Keyframes are stored per highlight; manual drags add `manual` keyframes; the source is never modified.

## D-021 — Synthetic test fixtures generated locally
No free, licensed, downloadable Hinglish programming-class recording exists (Spoken Tutorial: direct files 403, official bulk download paid; YouTube not used). Fixtures are generated by `tests/fixtures/lecture/build.py`: Roman-Hinglish narration via Windows OneCore *Ravi (en-IN)* with SSML pauses/emphasis (Kokoro's Hindi voice was evaluated and mangled English terms: "enduce effect"), and a VS Code-like screen rendered by Hyperframes with typed code, edits, pointer, scrolling, terminal and browser windows. Reference narration/timings are saved separately and only used after ASR. Results on these fixtures are **not** real-world validation.

## D-022 — Production backend URL discovery stays heartbeat-based
Unchanged from D-004; the launcher (`app/serve.py`) supports Cloudflare (blocked on this network) and Tailscale Funnel (stable URL, needs owner setup).

## D-023 — One timeline compiler, in Python
*Alt:* a Node `packages/video-templates` compiler used by both the worker and the editor.
*Why:* the worker that renders is Python, and the editor preview (Phase 06) can load the same compiled `index.html` from the backend, so there is one compiler and no Node-in-Python bridge. Zod (`packages/timeline-schema`) stays the single source of truth for the document shape; Python validates against the generated `timeline.schema.json` and re-checks the cross-field rules. Revisit if the editor needs to compile offline in the browser.

## D-024 — Public backend tunnel: Microsoft Dev Tunnels (Tailscale and Cloudflare blocked here)
*Measured 2026-10-16 on the owner's network:* Tailscale 1.104.1 is installed and its service runs, but the node is logged out, and its own health check reports Fortinet blocking. `controlplane.tailscale.com` is served with an untrusted (Fortinet) certificate and the DERP relays fail TLS, so login cannot complete; the "app not opening" is a symptom of that, not a broken install. Cloudflare's tunnel edge (`*.argotunnel.com:7844`) is reset. Pinggy (SSH over 443), localhost.run (22), bore and serveo are also blocked. ngrok is excluded at the owner's request.
*Why Dev Tunnels:* free (Microsoft or GitHub login, no card), the host connects to `*.rel.tunnels.api.visualstudio.com` over 443 (works here), and a persistent named tunnel keeps one URL. Limits (Microsoft Learn): 5 GB/month bandwidth per user, 16 MB maximum request body, 20 MB/s, 1,500 requests/min per port. Upload chunks were cut to 8 MiB.
*Security:* the relay allows anonymous connect (the browser cannot send a tunnel token), so the API's Supabase-JWT check and org-role checks remain the gate. Media uses signed URLs, and CORS is restricted to `ALLOWED_ORIGINS`.
*Caveat:* this network also intercepts `*.devtunnels.ms`, so a browser *on the owner's network* cannot reach the tunnel. The frontend falls back to `http://127.0.0.1:8000` when the advertised URL fails, which works only on the machine running the backend. Verified from outside by the `backend-probe` workflow.

## D-025 — Explicit table grants (security fix)
Supabase's default privileges gave `authenticated` ALL on public tables, including TRUNCATE (not subject to RLS) and table-wide UPDATE, which made the column-level edit grants ineffective. Migration `20261016190000_explicit_grants.sql` revokes all of it and grants only what each table's policies intend; pgTAP asserts that truncate and score edits are refused. Every future table must state its grants explicitly. The hosted project turned out to use Supabase's secure-by-default privileges (service_role gets no DML on new tables and no EXECUTE on new functions), unlike the local stack. `20261017000000_service_role_rpcs.sql` grants the backend's needs explicitly, and default privileges now give service_role DML on future tables.

## D-026 — `render_jobs` doubles as the export asset
One row per render: the timeline snapshot, its hash (render cache key), status and the verified output (path, size, duration, fps, thumbnail). A separate `export_assets` table waits until one render has several outputs (SRT/VTT, alternate qualities). Progress lives on the linked `jobs` row.

## D-027 — Brand kit logo stored in the row as a data URL
*Alt:* a private Supabase Storage bucket with storage policies; files on the processing machine.
*Why:* logos are small; a ≤300 KB `data:image/(png|jpeg|webp|svg+xml);base64,…` value (checked by the DB) needs no bucket, policies or backend, and the brand editor works with the processing machine offline. When a render is requested the API decodes it into the render folder as `logo-<sha256>.<ext>`, so the snapshot keeps the exact logo and a changed logo changes the render cache key. SVG is shown only through `<img>`, which never runs scripts.
*Upgrade:* move to Storage if kits need larger assets (intro videos, music).

## D-028 — Brand snapshot, intro/outro as cards in the main composition
Each render copies the chosen kit (default kit, a specific kit, or none) into `timeline.brand`; editing a kit never changes finished reels. Intro and outro are full-frame cards in the same composition (not `data-composition-src` sub-compositions): the clip and captions are offset by the intro length, and GSAP animates the cards. Only bundled OFL fonts (Archivo, Poppins, Noto Sans; JetBrains Mono, Fira Code) are allowed, enforced by Zod, the DB check and the editor. Caption presets: highlight-word, karaoke (words keep the accent once spoken), boxed (solid panel).

## D-029 — Subtitles from the timeline; timing check by audio correlation and voice overlap
SRT/VTT are generated on request from the render's stored timeline (no files, no migration): the same caption pages the renderer burns in, on the composition clock (intro included); VTT escapes `<`, `>` and `&` so code survives. The render job then runs a timing check, stored in the job result:
- **Audio offset**: FFT cross-correlation of the exported clip's audio against the same span of the source. A deliberate 100 ms trim error measures exactly 0.100 s; real renders measure 0.0 ms.
- **Words on speech**: the share of caption words overlapping voiced 20 ms frames of the source. Correct timing scores 1.0; words shifted 0.5 s score 0.91 and 1 s scores 0.72, so the 0.95 threshold flags drifts of about 0.5 s or more. It cannot see smaller per-word errors (the measured mean is 0.27 s, D-016).

A failed check is shown in the Export panel ("review before publishing") but never discards the render. GSAP 3.14.2 is now bundled into each render project, so renders need no internet.

## D-030 — Render settings: one worker, CPU x264 (measured)
Benchmark on the same 51.5 s branded composition (RTX 5050 laptop, 16 threads, 23 GB):
- **Default** (Hyperframes auto-calibrates to 1 worker, drawelement capture on the GPU, x264 during capture): 152.6 s.
- **`--workers 4`**: 261.2 s, slower, because the workers compete for one Chrome/GPU pipeline.
- **`--gpu` (NVENC)**: 144.4 s, 5 % faster, visually identical to x264 (PSNR 56.8 dB, SSIM 0.9994) but an 8 % larger file.

Frame capture dominates, so the defaults stay (portable to machines without NVENC). The speed levers are the `draft` preset, the timeline-hash render cache and re-rendering only what changed.

## D-031 — Caption layout: balanced pages, two positions, server-computed preview
Phrases end at sentence ends and pauses over 0.7 s. Each phrase goes on the fewest pages of at most 2 lines × 26 characters, with pages and lines split evenly, so no page holds a lone word. Brand kits choose the lower third (y 1350–1650) or top (y 260–560); code panels move to the opposite half. The studio preview asks the API for the exact pages, zone and panel position (`GET /highlights/{id}/preview`, same builder and paginator as the renderer), so preview and export cannot drift.

## D-032 — Local Mode B and additive canonical tracks
Topic generation is a durable worker job with immutable cached storyboard/narration, syntax-only example validation and measured word timestamps. Audio/code/text extend the existing schema/compiler; no alternate timeline. Live model JSON fences remain a documented blocker, not a canned-success fallback.

## D-033 — Instagram Login and durable publication identity
Use official Instagram Login for professional accounts, backend-only encrypted tokens (AES-GCM with account-bound AAD), single-use org/user-bound OAuth state, and durable render/account publication identity. Persist container and publish transition before the irreversible call. Unknown outcomes require review and cannot auto-retry. No linked Facebook Page is required for this selected flow. Real test posts require owner approval. Current browser personal account is never the target.

## D-034 — Shared signed media URLs across processes
Publishing worker and API cannot use unrelated random signing keys. Derive a domain-separated HMAC key from backend secret configuration; six-hour expiry and kind/resource binding remain. Rotation invalidates links. Unit checks pass; restart API and worker together before live ingestion. This narrowly necessary fix supersedes the original per-process-signing choice.

## D-035 — Delivery order for the hackathon: Instagram only, YouTube postponed
The owner reprioritised on 2026-10-17: Mode B MP4 → UI redesign → multitrack editor → Instagram publishing and
scheduling → Instagram analytics and AI feedback → end-to-end testing and submission. YouTube (OAuth, Data/Analytics
API, Shorts) is postponed until explicitly requested; existing YouTube configuration names stay but no YouTube code is
added. Billing, complex admin and non-essential optimisation are postponed. The PS and master prompt are unchanged.

## D-036 — Dark cinematic UI, amber accent (no purple)
Owner direction 2026-10-17: premium dark editing-software look with Inter. The suggested purple primary was rejected by the
owner ("should not look AI"); a single warm amber (#F2B544) is the primary action colour, cyan (#67E8F9) only marks live/
processing states. Tokens live in `apps/web/app/globals.css` (inlined: the Turbopack Tailwind loader dropped local `@import`s,
which is why Codex's light theme never actually loaded).

## D-037 — Editor preview = export compiler + small runtime
The editor never re-implements rendering in React. `POST /renders/{id}/preview` compiles the draft with `compose.compile_html`
and injects a ~40-line runtime (clip visibility, GSAP seek, media sync) — the part Hyperframes does at render time. The page
loads as iframe `srcdoc` with `<base>` = a signed render-folder URL, so Dev Tunnels' HTML interstitial is avoided and media/
fonts authorise themselves. Edits render as a new `render_jobs` row (`parent_render_id`); finished renders are immutable.

## D-038 — Drafts through RLS, renders through the API
`timeline_drafts` is written directly by editors under RLS so autosave works while the GPU machine is offline; rendering and
preview go through the API, which validates the timeline (JSON Schema + cross-field rules) before touching disk.

## D-039 — Style presets in the compiler
`stylePreset` (focus/energy/story/signature) is part of the canonical timeline and changes the compiled composition
(default transitions and timing, caption CSS, push-in, lower third). An explicit per-item transition always wins.

## D-040 — Feedback only from real, sufficient data
Feedback uses only reels published from Reel Studio whose Instagram insights include reach, requires ≥3, and stores just
the learned ideal length (fed to highlight scoring) plus findings. The local LLM may phrase recommendations from the
computed numbers only; with it offline the measured findings are shown alone. Audio fades are applied to the mix with an
ffmpeg volume expression after rendering (ponytail: per-source fades would need Hyperframes element-volume animation).

