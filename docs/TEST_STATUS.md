> **Reel Studio 2.0 (updated 2026-10-24, session 2) — read first:** `docs/REEL_STUDIO_2_MASTER_PLAN.md` (full approved spec + status map) and `docs/REEL_STUDIO_2_HANDOFF.md` (technical handoff). They supersede the 1.0 status below, which is kept as history. Work folder `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`, repo https://github.com/sahilkarande0918-cmd/Reel-Studio. 2.0 status (second session, HEAD ac322a5+docs): ✅ Mode B web app + AI director, 26 motion templates, 35 effects / 33 transitions + ONNX composites, headless Blender 3D shots, 100 caption presets + ON/OFF, clip collections; 🟡 voice profiles (built, speech not yet synthesised), campaign agent + EN/HI/Hinglish + click/inquiry tracking, Instagram cover/suggestions (nothing published), Phase D/Test B/E/H renders; ⬜ production migrations + Vercel deploy. Next task: handoff §18.

## Reel Studio 2.0 checks (2026-10-23/24)
| Test | Result |
|---|---|
| API pytest / ruff | ✅ 107 passed, 6 skipped / clean (new folder) |
| Web tsc / lint | ✅ clean |
| Schema vitest | ✅ 12 passed |
| Effects gallery | ✅ 24/24 effects change the picture; 21/21 transitions exact frame count |
| Owner phonk reel (17 clips, phonk audio, Ref 4 style) | ✅ 480/480 frames, hard cuts 0 ms off plan and ≤10 ms off beat, transitions ≤15 ms off beat, −14.0 LUFS, −2.2 dBTP |
| Reference analysis (6 reels) | ✅ profiles + contact sheets; Ref 4 89 % cuts within 60 ms of a beat |
| Mode B in the app (UI edit, downloaded MP4) | ✅ 15.000 s 1080×1920 (session 2) |
| Director: same 8 clips, 3 prompts | ✅ distinct phonk / cinematic (all QA pass) / tech-promo edits |
| Motion templates gallery | ✅ 26/26 animated, Hyperframes lint clean |
| Effects + transitions gallery (35 + 33) | ✅ 69/69 |
| Phase C ad (24 s) | ✅ all QA pass (weak look; re-render `ad2` pending) |
| 3D edit (Blender title + turntable, 16 s) | ✅ all QA pass |
| 100 caption presets | ✅ unit test (all valid, distinct); 23-family render gallery; Mode A preset + captions-OFF renders |
| Clip collections | ✅ unit test + synthetic lecture (2 collections) |
| Campaign agent (Hinglish) | 🟡 runs; copy quality weak (repeated hooks) |
| pgTAP RLS (incl. 20 new 2.0 tests) / db lint | ✅ 72/72 / clean |
| API pytest / ruff (session 2) | ✅ 118 passed, 6 skipped / clean |
| Voice synthesis (Chatterbox, synthetic sample, session 3) | ✅ 4 narrations EN×2/HI/Hinglish, CUDA, 82 s incl. load, all Perth-watermarked; speaker similarity to sample 0.909–0.952 (other speaker 0.717), EN1↔EN2 0.935; ASR: EN×2 and HI word-correct |
| Hinglish voice (Roman script) | ❌→✅ Roman text garbled ("samjhenge"→"Samshank", repeated ending); fixed with Devanagari conversion (`voice_profiles.devanagari`, guarded); app path re-run: both sentences ASR-correct, watermarked |
| Voice profile → Mode B narrated edit | ⬜ blocked: Windows reserved TCP 54313–54412 after reboot, local Supabase cannot bind (owner to restart winnat) |
| Phase D acceptance, Tests B/E/H, next build, production | ⬜ not run yet |

> **2026-10-17: Feature A (context-aware AI editing) verified on the owner's real physics class (production) and the synthetic React fixture (local). Read [CHECKPOINT.md](CHECKPOINT.md) first.** B/C not implemented.

## Context-aware AI editing (2026-10-17)
| Test | Data | Result |
|---|---|---|
| Unit tests (outline repair, step split, completeness, cliff ending, filler/back-reference, lexical fallback, de-dup) | synthetic word timings | ✅ 7 new tests; API suite 97 passed, 6 skipped; ruff clean |
| Dry runs (`tests/dryrun_highlights.py`) | **real** physics class, 7.5 min Hinglish (production recording) | ✅ outline 60–70 s on the RTX 5050; best run picked 2:35–3:31 ("plug in 4 and 0 → answer 0 → why? → the bird came back, so s = 0", 84/100) |
| Real analyze job (production worker, new code) | **real** physics class | ✅ 20 teaching steps / LLM outline; 1732 windows; 6 clips, **all 6 start and end on whole steps** (`complete_explanations: 6`), 30–60 s, no clip opens on filler; local LLM judged none fully standalone, so scores are 64–67/100 (honest, the class is one continuous problem) |
| Real render via the existing pipeline (`/highlights/{id}/render`, focus, looks) | top physics clip 5:17–6:04 | ✅ ffprobe 1080×1920 H.264 30 fps + AAC, 46.47 s (= clip length), audio mean −17.8 dB / peak −1.5 dB; frames: whiteboard maths retained, panel + crop reframing, synced captions, ends on "Displacement hai distance nahin." |
| Analyze job, local stack | **SYNTHETIC** React-hooks Hinglish fixture (192.5 s) | ✅ 9 steps / 5 topics; 4 clips (3 complete, 1 marked partial); vs reference topic boundaries (±1 s): new clips start on a boundary 3/4, end on one 3/4 |
| UI (local dev, browser) | synthetic fixture | ✅ NN/100, explanation, 5-bar breakdown, opens/ends quotes, limitation, lecture outline with clip steps highlighted, "Create reel" on unselected clips; legacy rows hide the breakdown (fixed a NaN) |
| Shared logo | browser | ✅ app sidebar shows the landing Aperture mark |
| Web lint · tsc · next build · schema vitest | — | ✅ clean · clean · built · 12 passed |
| Failures found and fixed | production worker | Ollama 500 on a context-size reload → one ctx + retry; Supabase HTTP/2 "Server disconnected" after long LLM stages failed all 3 attempts → HTTP/1.1 + client reset |


## Pre-compaction checks (2026-10-17)
| Test | Data | Result |
|---|---|---|
| Topic JSON import → Record & render (local, new project) | sample file | ✅ 5 scenes imported, generation used file settings, render 1080×1920 53.3 s with voice |
| Automation-engineer Reel on Instagram | **production, real API** | ✅ published once (media 17988096129063525); Instagram-served file has AAC audio (mean −17.3 dB) |
| Silent-render guard | published render vs muted copy | ✅ passes at −1.5 dB peak; muted copy rejected |
| Engine watchdog / single instance / logon task | local machine | ✅ killed worker restarted ~10 s; duplicate start refused; task registered, result 0 |
| Instagram delivery copy | automation render | ✅ H.264 High 4.1, 3.49 Mbit/s, AAC 48 kHz stereo |
| API pytest · ruff · schema vitest · web lint + tsc | — | ✅ 90 passed (6 skipped) · clean · 12 passed · clean |

## Speed pass (2026-10-17)
| Test | Data | Result |
|---|---|---|
| Live function region after `vercel.json` | **production** | ✅ `x-vercel-id: bom1::sin1::…` (was `bom1::iad1::…`) |
| Render workers benchmark (28 s Mode A reel) | local, synthetic | auto 123 s · 8 workers 111 s · GPU encode 119 s · GPU+8+jpg 117 s → adopted 8 workers |
| API pytest / web lint + tsc | — | ✅ 90 passed, 6 skipped / clean |
| Authenticated page timing on production | — | ⏳ not measured (needs owner login) |

## Homepage + Hyperframes tour (2026-10-17)
| Test | Data | Result |
|---|---|---|
| Tour composition lint (`hyperframes lint`) | — | ✅ 0 errors |
| Tour render (`hyperframes render`, 30 fps, high) | real app screens (synthetic data), real renders | ✅ 1920×1080 H.264+AAC, 61.4 s, 17.3 MB, peak −1.9 dB; frames inspected |
| Tour playback on deployed site | **production** (headless Chrome) | ✅ playing, 61.4 s, 1920×1080; live MP4 byte-identical to render |
| Homepage desktop 1440 / mobile 390 full-page screenshots | local | ✅ inspected, no horizontal overflow |
| Live `/`, `/privacy`, `/terms`, landing MP4/VTT/JPG content types | **production** | ✅ |
| Web lint, tsc, `next build`; API pytest | — | ✅ (90 passed, 6 skipped) |

## Final run — UI, editor, presets, Instagram/analytics code (2026-10-17)
| Test | Data | Result |
|---|---|---|
| API pytest + ruff | unit | ✅ 90 passed, 6 skipped (integration), ruff clean |
| timeline-schema vitest (incl. editor ops split/trim/move/duplicate/remove) | unit | ✅ 12 passed |
| Web lint, tsc, `next build` | — | ✅ |
| Editor on Mode B render (split, caption word, text overlay, Signature) → MP4 | local stack, generated topic video | ✅ 1080×1920 H.264+AAC 46.77 s, edits visible in frames |
| Editor on Mode A render (split/delete video + captions, Energy) → MP4 | local stack, **synthetic** recording | ✅ 1080×1920 H.264+AAC 28.17 s, crop + uppercase captions in frames |
| Mode A compose lint (nested timed video) | synthetic | ❌ found → fixed (untimed wrapper) → ✅ lint 0 errors |
| Style presets compile (4) | generated timeline | ✅ |
| Feedback learning (insufficient data / ideal length) | unit | ✅ 2 tests |
| Migration 20261017050000 | local + **production** (db push, ref verified) | ✅ applied |
| Vercel production deploy `41d1917` | production | ✅ READY |
| Instagram OAuth with Business account (owner, private window) | **production** | ✅ @career.with.purpose (BUSINESS, id 17841466046205321), not the personal account; scopes basic, content_publish, manage_insights (+comments, messages); token stored encrypted |
| Live read-only Instagram calls (/me, /media, account insights reach+views) | **production**, real API | ✅ identity matches stored id; 0 media; reach/views 0 (new account). `/{id}/permissions` returns error 100 for Instagram Login tokens (callback already falls back) |
| Production render of owner's real physics class (top highlight, rank 1, score 0.85) | **production, real recording** | ✅ 1080×1920 H.264 30 fps + AAC 48 kHz, 44.5 s, 25.8 MB; timing check ok (170 words on speech, 0 ms offset); Instagram eligibility ok |
| Public media URL fetchable without bypass header | local + GitHub Actions probe (outside network) | ✅ 206 video/mp4; probe run 38984638199 all steps green |
| **Instagram publish (owner-approved, once)** | **production, real API** | ✅ published media 18111030863186503, REELS, @career.with.purpose, https://www.instagram.com/reel/DekyGWcDEAl/ ; caption verified via API; 1 attempt, no duplicates |
| Insights refresh (account + per-reel) | **production, real API** | ✅ 4 account metrics + 9 reel metrics returned, none unavailable (all 0 minutes after posting) |
| AI feedback with real data | — | ⏳ needs ≥3 published reels with reach; shows the honest insufficient-data message now |
| Topic Studio "edit script → re-record" via UI (scene 2 code edited) | local stack | ✅ 1080×1920 H.264+AAC 42.27 s, edited code in timeline/video; invalid code rejected before render |
| Repeated-code gate, live Ollama (JSON vs XML, temperature 0) | local | 🟡 before: 2 distinct examples / 5 scenes; after stricter gate + repair: 3 / 5 (71 s). Still repetitive; script editing covers it |
| Audio fades audible check | — | ⏳ not run |
| Dark UI at 1440 px and 375 px (dashboard, topic, recording, brand, publish, editor) | local | ✅ visually inspected |

> **Latest checkpoint (2026-10-17, after the Codex handoff): read [CHECKPOINT.md](CHECKPOINT.md) first.** Mode B now works end to end (JSON vs XML → 46.8 s 1080×1920 MP4, plays and downloads in the UI); repeated-code prompt fix not yet re-verified on a new video. Instagram Business OAuth still pending; nothing published. YouTube postponed (D-035). HEAD at checkpoint start: `fe984a0`.

> **Final checkpoint (2026-10-17):** Read [CODEX_TO_CLAUDE_HANDOFF.md](CODEX_TO_CLAUDE_HANDOFF.md) first. It supersedes historical status below. Mode B pipeline/UI implemented but live generation fails on fenced model JSON; full editor and YouTube unfinished. Instagram reaches Reel Studio-IG but awaits the separate Business-account login/consent. Never connect/convert the personal account or publish without explicit approval. Production deployed at 7419b77; two new migrations applied. Final backend: 76 pass, 6 skip, 1 known xfail; DB: 52 pass; final frontend build passes. Owner requested checkpoint only, no more features.
# Test status

Only results of commands actually run. Legend: ✅ pass · ❌ fail · ⛔ blocked · ⬜ untested.

## Environment checks (2026-10-16)
| Check | Result | Command |
|-------|--------|---------|
| GitHub CLI auth, admin on repo | ✅ | `gh auth status`; `gh api repos/sahilkarande0918-cmd/Reel-Studio` |
| Collaborator invitations created | ✅ (pending acceptance) | `PUT /collaborators/{user}` → 201 ×3; `GET /invitations` |
| FFmpeg / FFprobe present | ✅ 8.1.2 | `ffmpeg -version` |
| GPU visible | ✅ RTX 5050 8 GB | `nvidia-smi` |
| Ollama API up | ✅ `qwen2.5vl:7b` | `curl localhost:11434/api/tags` |
| `ollama list` CLI | ❌ hung (>5 min); HTTP API works | `ollama list` |

## Phase 01 (2026-10-16)
| Test | Result | Command / method |
|------|--------|------------------|
| API unit tests (health, auth, CORS) | ✅ 5/5 | `pytest` in apps/api |
| RLS isolation (pgTAP) | ✅ 16/16 | `pnpm exec supabase test db` (local stack) |
| Schema lint | ✅ no issues | `pnpm exec supabase db lint --level warning` |
| Web typecheck / lint / build | ✅ | `tsc --noEmit`, `eslint`, `next build` |
| Landing design gate | ✅ 0 FAIL, 1 WARN (no-footage) | taste-skill `inspect.mjs` at 1440/768/390 |
| Signup → onboarding → dashboard | ✅ local | in-app browser against local stack |
| Create project via RLS | ✅ local | in-app browser |
| Signed-out redirect | ✅ | `curl -w %{redirect_url} /dashboard` |
| `/me` real token / tampered token | ✅ 200 / 401 | curl with local-stack session |
| Backend heartbeat + online/offline badge | ✅ local | row fresh in `backend_endpoints`; badge flips after API stop |
| Vercel production pages | ✅ (2026-10-16 checkpoint) | `/`, `/login`, `/signup`, `/forgot-password` 200; `/dashboard`, `/projects`, `/glossary` 307 → login |
| Remote Supabase (migrations, RLS, signup→onboarding on production) | ⛔ blocked | remote project has no tables; CLI cannot access the friend's org |
| Email confirmation + password reset emails | ⬜ | local stack has confirmations off; test on remote |

## Phase 02 (2026-10-16)
| Test | Result | Command / method |
|------|--------|------------------|
| Glossary correction (incl. regression: `component` ≠ `@Component`) | ✅ 6/6 | `pytest tests/test_glossary.py` |
| Repetition-loop cleanup | ✅ 2/2 | `pytest tests/test_cleanup.py` |
| Upload API on local stack (chunks, resume 409, incomplete, fake media, limits, cross-org 404, signed media) | ✅ 6/6 | `RS_INTEGRATION=1 pytest tests/test_upload_integration.py` |
| CTranslate2 on RTX 5050 (Blackwell) | ✅ cuda, float16 | first run 275 s JIT for 28 s audio; warm `base` 1.35 s |
| Worker end to end (claim → audio → ASR → correct → save → ready) | ✅ | `python -m app.workers.run`, job `succeeded`, events extract_audio/transcribe/correct_terms/save |
| Hinglish model (Oriserve Apex, CT2 fp16, lang=hi) on real Hindi speech clips (model-repo Common Voice samples) | ✅ Roman Hinglish output | `tests/bench_asr.py`: "Mehnat to poora karte hain.", "Aap pandrah log hain.", 12.5 s clip in 1.10 s |
| Hinglish model on 28 s synthetic tech-English clip | ✅ ~40× real time warm (0.71 s); cold job 6.4 s incl. model load | worker result `realtime_factor`; terms useEffect/Docker/Kubernetes/JSON/@Autowired correct |
| Known ASR error | ⚠️ "AbortController" → "award controller" | needs screen-OCR evidence (Phase 03) |
| Hallucination loops on 1–3 s clips | ⚠️ observed; mitigated by loop cleanup (raw kept) | bench runs |
| Browser: video playback via signed URL, click-to-seek, search, edit persists after reload | ✅ | in-app browser on local stack |
| Glossary: correct spoken forms only, mishearings not guessed | ✅ 9/9 (glossary + cleanup) | `pytest tests/test_glossary.py tests/test_cleanup.py` |
| **Real Hinglish programming-class recording** | ⛔ none legally obtainable at ₹0 (see below) | |
| WhisperX alignment | ⬜ not implemented (D-016) | |

## Phase 02 acceptance run on the SYNTHETIC lecture (2026-10-16)
Fixture `react-hooks-hinglish`: 192.5 s, 1920×1080 30 fps, Roman-Hinglish narration by Windows OneCore *Ravi (en-IN)*, 14 segments, 62 screen events (typing, edits, pointer, scroll, terminal, browser window). Built by `tests/fixtures/lecture/build.py` with Hyperframes. The reference narration is read only by `tests/eval_transcript.py`, after ASR.

| Step | Result | Evidence |
|------|--------|----------|
| Upload through the app UI (drop on the real uploader) | ✅ | 52 MB lossless copy, 4 × 16 MB chunks |
| Resumable upload | ✅ | page network failed after chunk 2 → UI "keeps failing"; re-drop resumed at offset 33 554 432 (server log), no restart |
| FFprobe metadata | ✅ | 192.5 s, 1920×1080, 30 fps, h264/aac stored |
| FFmpeg audio extraction | ✅ | `extract_audio` stage, 16 kHz mono, loudnorm |
| Local faster-whisper (Hinglish-Apex, CT2 fp16, CUDA) | ✅ | 192.5 s in **7.45 s (25.8× real time)**; GPU memory in use 2.2 GB / 8 GB |
| Hinglish transcription (Roman script) | ✅ with errors | WER raw **35.6%**, corrected **31.1%**; much is romanisation variance (ham/hum, yah/yeh) and TTS mispronunciation ("karte hain" → "kaati hai") |
| Word timestamps | ✅ | 381/381 words start inside the segment being spoken; segment-start error mean **0.27 s**, max 0.44 s |
| Technical terms | ⚠️ partial | correct: useEffect 3/3, React 3/3, API 2/2, Docker, Dockerfile, useState, npm 2/2, replicas · **missed: AbortController 0/4 ("about/Abbot controller"), Kubernetes ("kubernetti"), JSON, setData ("se data"), one sentence-initial "Fetch"** |
| Vocabulary correction | ✅ | 9 corrections applied; mishearings left for OCR evidence (Phase 03) |
| Transcript search | ✅ | "useEffect" → 3 matches |
| Synced playback | ✅ | click "Docker" → video 2:26; active-word highlight follows playback |
| Edit + persistence | ✅ | "kubernetti" → "Kubernetes" saved; raw kept; `{edited, previous}` metadata |
| Cancellation | ✅ | UI Cancel → job `cancelled`, `cancel_requested = true` |
| Retry | ✅ | UI "Retry transcription" → new queued job |
| Worker crash mid-job | ✅ | worker killed during transcribe → job stays `running`, recording `processing`; restarted worker requeued the stale lock after 3 min → attempt 2 `succeeded` (381 words), recording `ready` |

**Real-world validation: unverified.** Spoken Tutorial (IIT Bombay, CC BY-SA 4.0) has Hindi Python screen recordings, but direct file access returns 403 and the official bulk download is now paid (₹99 + GST), which the ₹0 rule forbids. Internet Archive hits were unverifiable YouTube re-uploads; YouTube downloading was not attempted (ToS). A synthetic voice is not equivalent to a real instructor.

## Phase 03 (2026-10-16)
| Test | Result | Evidence |
|------|--------|----------|
| Unit: glossary + cleanup 9, screen correction 4, highlights 3, reframe 7, API 5, misc 1 | ✅ 29 | `pytest` (6 integration tests skipped without RS_INTEGRATION) |
| OCR on lecture (35 frames) | ✅ 220 s CPU | tokens: AbortController, AbortError, setData, useEffect, useState, useFetch … |
| Screen-evidence correction on lecture | ✅ | AbortController 4/4, AbortError fixed, WER 28.2 %; no false merges after guards (setData left uncorrected on purpose) |
| Highlight boundaries vs reference topics (lecture) | ✅ 2/2 starts, 2/2 ends | `tests/eval_highlights.py`; earlier iterations 1/5 → 3/4 → 2/2 recorded in git history |
| LLM judge determinism | ✅ temperature 0, seed 7 | same windows across reruns |
| Reframing on focus fixture | ✅ | cuts at 26.0 s (browser) and 31.5 s (editor) = ground-truth switch times; single panel width |
| Highlights UI | ✅ | select, word-snapped boundary edit, manual crop keyframe persisted (local DB) |
| analyze job timings (lecture) | ✅ | activity 7.3 s, OCR 219.8 s, LLM ~13 s/clip after a ~86 s first load |

## Checkpoint run (2026-10-16, end of session 1)
| Check | Result | Command |
|-------|--------|---------|
| Web lint | ✅ 0 problems | `pnpm lint` (apps/web) |
| Web typecheck | ✅ | `npx tsc --noEmit` |
| Web production build | ✅ 13 routes | `npx next build` |
| API unit tests | ✅ 29 passed, 6 skipped (integration) | `pytest -q` |
| API lint | ✅ | `ruff check .` |
| Upload integration (local stack + API) | ✅ 6/6 | `RS_INTEGRATION=1 pytest tests/test_upload_integration.py` |
| RLS pgTAP | ✅ 16/16 | `pnpm exec supabase test db` |
| DB lint | ✅ no issues | `pnpm exec supabase db lint --level warning` |
| Production probe | ✅ pages / ⛔ data | Vercel `dpl_8kA8nFpH…` READY for `9a4ee55`; remote REST `PGRST205` (no tables) |
| GPU ASR / OCR / LLM benchmarks | not re-run (results above still current) | — |
| Frontend unit tests | ⬜ none exist yet | add Vitest with the timeline schema (Phase 04) |

## Session 2 — infrastructure (2026-10-16)
| Check | Result | Evidence |
|-------|--------|----------|
| Supabase CLI link | ✅ linked to `adjwycjsxtxvjockxtan` (org `yqdlgjynocbxxsmzeesy`) | `supabase/.temp/project-ref`, `linked-project.json` |
| Remote migrations (before owner push) | ⛔ none applied | `supabase migration list --linked`, `inspect db table-stats --linked` (0 rows) |
| Remote migrations (after owner push, 2026-10-17) | 🟡 3/5 applied; `render_jobs` + `explicit_grants` pending | `migration list --linked`; `db push --dry-run` lists the 2 |
| Remote schema | ✅ 14 tables, RLS on 14/14, 26 policies | `supabase db dump --linked --schema public` |
| Remote grants | ❌ `anon` TRUNCATE on 6 tables, `authenticated` TRUNCATE on 14 (fix pending in `…190000`) | same dump |
| Second push by the assistant | ⛔ blocked by the permission classifier | — |
| Remote after second owner push | ✅ 5/5 applied; `anon` 0 table grants, `authenticated` no TRUNCATE, RLS 15/15 | `migration list --linked`; schema dump |
| Backend against production | ❌ `permission denied for table backend_endpoints` and `for function requeue_stale_jobs`: hosted secure-by-default privileges give service_role no DML/EXECUTE | backend log; dump; fix migration `20261017000000` pending owner push |
| RLS pgTAP | ✅ 28/28 | adds service_role RPC + DML assertions (the local stack's defaults hide this class of bug; the assertions guard against grant regressions) |
| Remote after third owner push | ✅ 6/6 migrations | `migration list --linked` |
| Backend on production | ✅ heartbeat row = tunnel URL (age 7 s); table reads OK; `requeue_stale_jobs` 0; `claim_next_job` (probe type) returns empty row; no worker poll failures after the push | service client + worker log |
| External probe against production-configured backend | ✅ run 38950101996: health+CORS, preflight, anon 401, 8 MiB relay, video no-interstitial | GitHub Actions |
| Production auth settings | ✅ signup on · ⚠️ confirm-email on | `/auth/v1/settings` |
| Production signup (owner, after the fix) | ✅ user confirmed via email, onboarding created org + owner membership + audit event | service-client read |
| Production signup (owner, first try) | ❌ "Invalid path specified in request URL": Vercel URL var ends in `/rest/v1/`; base `…/rest/v1` + `/auth/v1/signup` → PGRST125 reproduced, plain origin → GoTrue | probe with backend key, empty body |
| Remote `db push` by the assistant | ⛔ blocked by the session's permission classifier; owner runs it | — |
| Remote auth settings / API keys | ⛔ publishable key from session 1 now returns `Invalid API key`; CLI key listing blocked | `GET /auth/v1/settings` 401 |
| Production signup/login/logout E2E | ⬜ owner must run it (the assistant may not enter passwords or create accounts on a non-local site); needs migrations first | — |
| Tailscale diagnosis | ⛔ network | service Running, CLI 1.104.1 OK, `BackendState: NeedsLogin`; health: "Network equipment from Fortinet may be blocking"; `controlplane.tailscale.com` → `SEC_E_UNTRUSTED_ROOT`; DERP TLS fails |
| Other tunnels from this network | ⛔ | Cloudflare edge reset; pinggy SSH/443 no banner; localhost.run :22 timeout; bore/serveo fail |
| Dev Tunnels host | ✅ | `devtunnel` 1.0.2115 (winget), GitHub login, tunnel `reel-studio.inc1`, `https://j96sqlp6-8000.inc1.devtunnels.ms` |
| Tunnel reachable from the internet | ✅ 200 | check-host.net nodes DE/FR/TR/CA → `/health` 200 |
| Tunnel probe from GitHub Actions (`backend-probe`) | ✅ all steps | run 38944354909: health + CORS for the Vercel origin; preflight OK; anonymous 401; **8 MiB PUT passes the relay** (API 401); `<video>`-style request gets API JSON 403 (no interstitial); navigation gets the interstitial (informational) |
| Same-machine fallback | ✅ | local browser: tunnel `/health` status 0 (TLS intercepted) → `127.0.0.1:8000` 200, badge online |
| Upload integration with 8 MiB chunks | ✅ 6/6 | `RS_INTEGRATION=1 pytest tests/test_upload_integration.py` |
| Default table privileges | ❌→✅ fixed | `authenticated` had TRUNCATE/UPDATE on every table; after `20261016190000_explicit_grants.sql` only the intended grants remain (`information_schema.role_table_grants`) |
| RLS pgTAP | ✅ 24/24 | `pnpm exec supabase test db` (adds render isolation, truncate refused, score edit refused, anon truncate refused, anon holds 0 grants) |
| DB lint | ✅ | `supabase db lint --level warning` |

## Production end to end (2026-10-17, owner's account, owner-supplied recording)
Recording: a 7.5-min Hinglish **physics** class (distance vs displacement), uploaded by the owner. It is real speech, not synthetic, but provenance and licence are unknown to the assistant: it is not committed or redistributed. It is not a programming class, so it does not replace the PS's programming-class validation.
| Step | Result | Evidence |
|------|--------|----------|
| Project create + persists after refresh | ✅ | `projects` row "Existing Lead" (mode recording) |
| Upload through the production site | ✅ | `source_recordings`: 75,273,638 / 75,273,638 bytes, status `ready`, 449.9 s, 1920×1080 29.97 fps h264/aac |
| Transcribe on the local GPU | ✅ | job attempt 1: 449.9 s in **38.8 s (11.6× real time)**, cuda, lang hi, 1,689 words, 15 segments |
| Transcript quality (spot check) | ⚠️ good Roman Hinglish; formula miss | "Hello bachcho aaj badi simple si baat…"; "s = ut + ½at²" heard as "UT plus half **80** square" |
| Analyze | ✅ | 1,970 windows scored, 76 OCR frames in 191 s, 11 screen-term fixes, LLM judged 9 / dropped 3, **6 highlights** of 33–46 s |
| Heartbeat during the run | ✅ | `backend_endpoints` age 5–18 s; earlier `permission denied` lines all predate the service_role grant |

## Phase 04 — acceptance review fixes (2026-10-17)
| Test | Result | Evidence |
|------|--------|----------|
| Balanced caption pages | ✅ | unit test (8 words + lone "hai." → 2 even pages; 5 words → 2+3 lines); real timelines: 0 one-word cues (16 and 22 cues), shortest cue 1.42 s |
| Caption position | ✅ | unit test (upper → y 260–560, panel window [720, 864]; lower → [336, 864]); pgTAP rejects 'middle' (35/35); migration `20261017020000` live on production (8/8) |
| Subtitle preview in studio | ✅ | browser: overlay shows the default kit's karaoke page at the playhead, Poppins, lower zone; note names the kit and preset |
| Render performance benchmark | ✅ measured | default 152.6 s · 4 workers 261.2 s · NVENC 144.4 s (PSNR 56.8 dB, SSIM 0.9994 vs default; +8 % size) |
| Full suite | ✅ | pytest 55 passed / 6 skipped; ruff; web lint + tsc; schema Vitest 8/8; pgTAP 35/35; db lint clean |

## Phase 04 — subtitles, timing check, offline GSAP (2026-10-17, local stack)
| Test | Result | Evidence |
|------|--------|----------|
| Unit: SRT/VTT cues, intro offset, VTT escaping, empty track; audio offset (known 120 ms shift, sign); words-on-speech | ✅ 4/4 (API total 53 passed, 6 skipped) | `pytest tests/test_captions_sync.py` |
| Timing check on 3 existing real renders | ✅ | offset 0.0 ms, correlation 1.0, words on speech 1.0 (98, 98, 87 words), ~2.7 s each |
| Sensitivity | ✅ measured | trim shifted 100 ms → measured 0.100 s; words shifted 0 / 0.5 / 1 / 3 s → 1.000 / 0.908 / 0.724 / 0.765 (clip 63 % voiced) → threshold 0.95 |
| Render with bundled GSAP + kit through the UI | ✅ | 51.533 s vs 2 + 46.53 + 3; `index.html` loads `gsap.min.js` locally (0 CDN references); job result timing ok |
| Export panel | ✅ | "Timing check passed · audio offset 0 ms vs the source · 100% of 87 caption words fall on speech"; SRT and VTT buttons → `GET …/captions?format=…` 200 |
| Captions endpoint auth | ✅ | anonymous → 401 |
| Subtitle files valid | ✅ | ffprobe: `subrip` 16 packets, `webvtt` 16 packets; first cue 00:00:02.000 (after the intro) |

## Phase 04 — brand kits (2026-10-17, local stack, synthetic lecture, test kit "Nimbu Academy (test kit)")
| Test | Result | Evidence |
|------|--------|----------|
| pgTAP (kits isolated, one default per org, colour/logo checks, bob cannot insert) | ✅ 34/34 | `supabase test db` |
| Zod schema (defaults, bundled fonts only, logo asset must exist) | ✅ 8/8 | `pnpm test` |
| Python builder/compiler (intro offset, outro, watermark, fonts, presets, cache key, logo decoding) | ✅ 20/20 rendering, 49 API total | `pytest` |
| Brand editor | ✅ | create kit → colours, Poppins/Fira Code, SVG logo upload, handle, watermark top-left, karaoke → save → reload shows saved values; live preview updates |
| Branded render through the Export panel (default kit preselected) | ✅ | 1080×1920 30 fps H.264+AAC, **55.867 s vs 2 + 50.85 + 3 = 55.85 s**, rendered in 179 s |
| Frames | ✅ | 1.2 s intro (logo, bar, title in Poppins); 9 s karaoke (spoken words accent); 45.5 s `AbortController` code chip in Fira Code; 54.5 s outro (logo, CTA, handle) |
| Audio | ✅ | intro/outro max −91 dB (silent), clip max −6.1 dB |
| Production migration | ✅ 7/7; brand_kits RLS + explicit grants confirmed by schema dump | `migration list --linked`, `db dump --linked` |
| Boxed preset + bottom-right watermark (draft render of the same timeline) | ✅ | panel behind captions, spoken word in accent; watermark backdrop legible over code |

## Phase 04 — first task (2026-10-16, local stack, synthetic lecture)
| Test | Result | Evidence |
|------|--------|----------|
| Timeline schema (Zod) | ✅ 6/6 + tsc | `pnpm test` in `packages/timeline-schema` (defaults, JSON round trip, bad layout, item past end, unknown asset, path traversal, committed JSON Schema in sync) |
| Python timeline + compiler unit tests | ✅ 14/14 (API total 43 passed, 6 skipped) | `pytest tests/test_rendering.py` |
| Hyperframes lint of compiled composition | ✅ 0 errors (16 Studio-editing warnings) | `hyperframes lint --json` |
| Render rank-1 highlight (14.66–61.19 s, manual keyframe) through the UI | ✅ | job `succeeded`, 155 s; ffprobe **1080×1920, 30 fps, H.264 + AAC 48 kHz, 46.533 s vs 46.53 s** |
| Render rank-2 highlight (122.92–173.77 s) | ✅ | ffprobe 1080×1920 30 fps H.264+AAC, **50.867 s vs 50.85 s** |
| Crop follows keyframes | ✅ | frames: 0.2 s panel (manual kf, crop_x 640, window y 363–1173), 4/10/16 s crop layout; 5 s panel, 25 s and 43.6 s crop |
| Captions match corrected words | ✅ | frame 43.6 s: "To **AbortController** vaala pattern abhi zaroori ho" — AbortController in a code chip, highlighted while spoken |
| Crash + retry | ✅ | worker tree killed at 23.6 % render → job stayed `running` → new worker requeued the stale lock after 3 min → attempt 2 succeeded (159 s) |
| Render cache | ✅ | second Render on unchanged highlight → 202, no new row or job |
| Playback / download / signing | ✅ | inline `<video>` 1080×1920 46.53 s plays; download 200 `video/mp4` 5,719,752 B; tampered signature 403 |
| Select-before-render guard | ✅ | unselected highlight shows "Select this highlight to render it", button disabled; API 409 otherwise |
| Known quality limits | ⚠️ | ASR errors pass into captions ("use fish" for useFetch); panel layout code is small (~17 px on 1080 wide); GSAP loaded from jsDelivr during render (needs network) |

## Unverified / untested

### UI audit — 2026-10-17 (Antigravity dashboard follow-up)

| Check | Result | Evidence |
|-------|--------|----------|
| Antigravity commit vs remote | ✅ inspected | `714b8e2` was local only; `origin/main` was `521bbbb` before this UI pass |
| Dashboard data and controls | ✅ code audit | Removed fabricated cards, metrics, chart, paid plan, and dead links; projects/jobs/counts/Instagram insights use org-scoped Supabase rows; no live publishing performed |
| Web ESLint and TypeScript | ✅ | `pnpm lint` and `pnpm exec tsc --noEmit` in `apps/web` |
| Workspace tests | ✅ | `pnpm test`: timeline-schema 12/12 |
| Production web build | ✅ | `RS_BUILD_SINGLE_WORKER=1 node node_modules/next/dist/bin/next build --webpack`: 20/20 static pages, all dynamic routes compiled |
| Default Turbopack build on this Windows host | ⚠️ tool failure | Initial Google Fonts fetch failure fixed by local fonts; later CSS-worker startup panic. Webpack with 15 static workers hit Windows `EPERM` creating segment directories; 1 worker passed. |
| Authenticated visual browser check | ⬜ pending | Review deployed dashboard at desktop and mobile widths after push/deployment. |

Remote Supabase (migrations not applied yet), production auth E2E, email confirmation and password-reset emails, production ↔ backend with a real session. Phase 04 remainder (brand kits, intro/outro, SRT/VTT, timing check) and Phases 05–09.

## Active checkpoint — 2026-10-17: topic studio and Instagram integration

Branch: `feature/topic-studio`. Added local topic generation (Ollama → validated storyboard → Kokoro → measured captions → canonical timeline → Hyperframes), refreshed studio UI, and authenticated Instagram Login/publishing/insights screens and worker handlers. These are implemented slices, not completed phase acceptance.

Instagram env presence verified without values: client ID numeric, secret present, exact callback `https://reel-studio-taupe.vercel.app/publishing/callback/instagram`, backend encryption key present. No manual test token. Actual account authorization, Meta registered redirect acceptance, scopes and token validity remain unverified until OAuth consent. Never publish a real test Reel without the owner's specific approval.

Both migrations `20261017030000_topic_generations.sql` and `20261017040000_social_publishing.sql` applied only to verified project `adjwycjsxtxvjockxtan`. API/tunnel/worker restarted; local health 200 and unauthenticated social route 401. Zero connected accounts and zero publication rows at restart. Port-8001 local test stack was left untouched.

Verified: backend 74 passed / 6 integration tests skipped (one upstream deprecation warning), Ruff clean; workspace lint and typecheck pass; timeline 9 tests pass; direct Next production build passes including publishing callback. Earlier local database suite: 47 pgTAP tests pass and schema lint clean; the later change_publication RPC has not yet been exercised locally. No new live Mode B MP4, Instagram OAuth, real publish, or real analytics retrieval has been verified. Frontend deployment pending this checkpoint.

Next: deploy callback/UI, finish authorized Instagram OAuth, verify public media ingestion without publishing, exercise scheduling failure/retry/idempotency, render and inspect a genuine topic video. Phase 06 full editor, Google OAuth/upload, analytics feedback and final end-to-end acceptance remain outstanding. Keep Google credentials private in backend .env. OAuth tokens are encrypted in backend-only database rows, never frontend storage.

### Final handoff verification (2026-10-17)
Backend: 76 passed, 6 integration skipped, 1 strict xfail for the reproduced live fenced-JSON generation bug; Ruff pass. Frontend ESLint/typecheck pass; 9 timeline tests and 4 API-error tests pass. Latest direct Next production build passes after frontend fixes. Local database 52 pgTAP tests pass. No new MP4 was generated; no ffprobe success claimed. Final secret scan pass; main push and clean tree verified at f144e7b. No Instagram consent/token, real publish or real metrics verified.

## Phase 05 — Mode B live (2026-10-17, local stack, UI job)
| Check | Result | Evidence |
|-------|--------|----------|
| Root cause of "Invalid JSON" | ✅ found | Ollama 0.30.6 ignores `format` when the schema has `$ref` or min/max length keywords (bisected); now sent inlined and without length keywords, Pydantic still enforces them |
| Fenced replies | ✅ | single full-reply fence unwrapped; prose / two blocks / unterminated still rejected (8 cases) |
| Narration alignment | ✅ | stray recognised word ("forward") and "jaison" mishearing no longer fail a scene; <85 % recognised still rejected |
| "JSON vs XML" via Topic Studio | ✅ | storyboard 5 scenes (json/xml), Kokoro narration, render; ffprobe 1080×1920 30 fps H.264+AAC **46.77 s**, 2.5 MB; audio peak −2.5 dB |
| UI | ✅ | inline player plays (1080×1920, 46.77 s); Download MP4 → 200; SRT/VTT buttons present |
| Frames | ✅ / ⚠️ | brand watermark, code cards, karaoke captions, outro. Code card enlarged to 46 px code after review; 4 of 5 scenes reused one JSON object → prompt now asks for progressing examples (not yet re-verified live) |
| Backend suite | ✅ | pytest 88 passed, 6 skipped; ruff clean |

