# Bulk AI clipping (Mode A extension) — podcasts, interviews, talks → many distinct Shorts

Added 2026-11-05 (session 4). Commits `e0e552e` (engine) and `e445899` (OpusClip-parity options). Owner prompt:
"Professional AI podcast clipping & bulk Shorts engine" (phases 1–11) plus "take reference how OpusClip makes ... all
features ... free tools only". Everything is local and ₹0: no API key or paid service is used.

## Paste a YouTube link (session 4)
Recording projects accept a YouTube link instead of a file: `POST /recordings/import {project_id, url,
rights_confirmed}` (YouTube watch/youtu.be/shorts/live/embed links only; playlists, channels and other sites refused;
the user must confirm they own the video or may clip it) → `import_url` job (`workers/import_url.py`,
`services/link_import.py`): yt-dlp downloads ≤ 1080p (H.264 preferred) straight onto the engine with real byte
progress, refuses running live streams, > 4 h or > 4 GB, then `recordings.finalize` (the same probe → transcribe path as
uploads). Title, channel and licence are kept in `source_recordings.probe.import`. Verified: link parsing (unit test),
format resolution for a CC-BY video (metadata only). A full import has not yet been run through the engine.

## Flow
`POST /recordings/{id}/analyze` with `{profile, count, duration, brief, range_start_s, range_end_s}` →
`workers/analyze._analyze_talk` (any profile except `education`, which keeps the original class-reel path and `KEEP = 6`):

1. **Words** of the latest transcript (optionally only the adjusted range). Transcription itself is now batched
   (`whisper.BATCH=8`, faster-whisper `BatchedInferencePipeline`, sequential fallback; `WHISPER_BATCH=0` disables).
2. **Speakers / faces** (`screen_analysis/speakers.py`, cached `faces.json`): YuNet face boxes every 0.5 s at 480 px,
   seats by 1-D k-means, active speaker = slot with most mouth motion while there is speech, 1 s majority + 2 s
   minimum shot (hysteresis). Model `D:\ReelStudio\models\yunet\face_detection_yunet_2023mar.onnx` (`FACE_MODEL`
   env), Haar fallback.
3. **Voice labels** per sentence (`transcription/diarize.py`, cached `speakers-audio.json`): MFCC statistics + Ward
   clustering, k by silhouette. CPU, no download. Upgrade path: pyannote (gated model).
4. **Conversation map** (`highlights/outline.py` + `llm.units(profile=…)`, cached `outline-<profile>.json`; LLM asked
   only for each part's first sentence, kind, topic) → `bulk.split_questions`: real host questions (voice changes
   around them; short host prompts without "?" count), deterministic sponsor-read and tangent detection, LLM
   low-value labels inside an exchange kept only when the text agrees → `conversation-<profile>.json`
   (parts, topics, question→answer links).
5. **Spans** (`bulk.spans`): runs of whole parts inside the duration preset, never starting/ending on sponsor/tangent/
   filler; long parts fall back to sentence windows. `bulk.refine` trims greetings/segues/"Yeah." at the edges.
6. **Editorial score /100** (`bulk.features` + `profiles.PROFILES[*].weights`): hook 20, standalone context 25,
   payoff 20, value 15, delivery 10, visual 5, relevance 5 (business/podcast; motivational/general differ). The
   exchange (question + all of its answer) is the unit: starting inside an answer, stopping before it ends, answering
   a question that is not shown, or covering two exchanges are penalised and listed as limitations. A ranking aid,
   never a virality probability.
7. **Selection** (`bulk.select`): best-first, topic- and timeline-diverse, duplicates rejected by time overlap (>30 %),
   embedding cosine ≥ 0.88 (`nomic-embed-text` in Ollama, cached `embeddings.json`, TF-IDF fallback) or ≥ 50 % shared
   words. Each pick is checked by the local LLM (`llm.judge_talk`: reasoning-first schema, 1–5 ratings, grammar-
   bounded lengths, cached `judgments-<profile>.json`); a vetoed clip frees its slot; an unreadable answer is rejected.
   The count is a target: the report says how many good clips exist and why the rest were not produced.
8. Rows in `highlight_candidates` (score 0–1 = editorial/100; full breakdown, quotes, topic, duplicates, hook teaser,
   editing recommendations in `features`), crop keyframes from `speakers.plan`.

Changing count/duration/brief reuses every cache: 5.5 s end to end on the test interview.

## Render options (`RenderRequest`, single clip and `POST /recordings/{id}/render-batch`)
`engine` auto/fast/studio · `pace` original/natural/engaging/fast (`clips/speech_cuts.py`: shortened pauses, um/uh and
stutters removed, content words never; timeline spans, non-destructive) · `caption_preset` id or `auto`
(`caption_auto.auto_preset`) · `emphasis` · `hook_title` + `hook_style` classic/statement/editorial · `hook_teaser`
(authentic later quote, labelled, off by default) · `auto_zoom` (1.15× punch-ins on emphasised words, ≤ 1 per 5 s) ·
`color_correct` · `sfx` (synthesized whoosh/impacts) · `enhance_audio` (high-pass, denoise, compressor, −14 LUFS) ·
`layout` auto (speaker framing, split screen in fast exchanges) / fill / fit (whole frame over blurred copy).
Talk clips get short-form caption grouping (16 chars × 2 lines, 74 px) in preview and export.

**Fast renderer** (`rendering/fast.py`): one FFmpeg pass, NVENC (libx264 fallback), captions as ASS from the same
`compose.paginate` pages as the preview, bundled fonts converted to TTF and renamed "RS <family>" (cache
`DATA_DIR/cache/fonts-ttf-v2`). Not supported (Hyperframes path used): intro/outro cards, logo/watermark, code/motion
items, eased pans. Measured: 4–6 s per 25 s 1080×1920 Short (Hyperframes ≈ 111 s); polish (auto levels) ≈ 15 s; fit
layout ≈ 11 s.

**Batch** (`api/batch.py`): disk check, per-clip `enqueue_highlight_render` (identical timeline → reused, never exported
twice), per-clip real job status `GET /recordings/{id}/batch`, signed ZIP (`batch-zip-url` → `batch.zip`: MP4 + SRT +
`metadata.json`), campaign brief (`clips/campaign_brief.py`: rights confirmation, min/max length, hashtags, mentions,
required text, topic warning, low-transformation warning, duplicate-submission warning; no guarantees, no publishing).

**UI**: `apps/web/components/studio/bulk-clipping.tsx` inside the Highlights section (existing styles): category (auto),
count (auto/5/10/15/20/30/custom), duration, adjust range, layout, pace, caption style, brand kit, hook style, toggles
(hook title, emphasis, auto zoom, enhance audio, colour, SFX, campaign brief), prompt, Generate clips, Render selected /
all eligible, ZIP, per-clip status with retry; highlight detail shows the 7-component breakdown, hook/insight/ending
quotes, duplicates, recommendations, proposed teaser.

## Evidence (SYNTHETIC fixture, not real-world validation)
`tests/podcast_fixture.py` builds an original two-voice business interview with Kokoro TTS (5.7 min: 12 Q&A insights,
sponsor read, cricket tangent, repeated advice; `--short`: 5 insights) on labelled colour panels (no faces).
`tests/dryrun_bulk.py VIDEO WORKDIR …` runs everything without the database.
- 10 requested → 10 single complete exchanges (question → answer → natural ending); sponsor, tangent and the repeated
  advice excluded; LLM check 96 s (≈ 9.6 s/clip).
- 15 requested on the full interview → 11 + honest shortfall; on the 5-insight version → exactly 5 + shortfall.
- Count change 10 → 5: 5.5 s (all cached). ASR batched 5.4 s vs sequential 8.4 s (same 1 039 words).
- Speaker labels: host/guest correct on every sentence spot-checked.
- Renders: natural/engaging/fast versions of 2 clips, exact durations (25.93/25.63/25.16 s), H.264 1080×1920 + AAC;
  contact sheets checked (captions bold Archivo, 2–3 word groups, spoken-word highlight, emphasis, three hook styles,
  fit layout).
- Unit tests: `tests/test_bulk_clipping.py` (15). Full API suite 150 passed / 6 skipped; ruff clean; web tsc/eslint clean;
  schema 12/12.

## Not verified / not built (honest)
- **Real footage**: no authorised real podcast was available; face framing, active-speaker switching and split screen are
  unit-tested only. Needs one authorised two-person interview (owner to provide or approve a CC-licensed download).
- Hindi/Hinglish podcasts, 60-minute recordings (time scales with LLM speed: ≈ 50–100 s per 150 sentences of outline).
- Database/UI end to end (engine path `_analyze_talk`, batch API, ZIP) not yet run against production; only the
  offline dry run and unit tests.
- OpusClip features not built yet: AI B-roll, AI emojis, motion graphics in the fast path, voice dubbing, caption
  translation, SRT upload, other aspect ratios (1:1, 16:9). No claim of identical output quality to OpusClip.
- LLM speed: `qwen2.5vl:7b` runs ≈ 1/3 on CPU on this 8 GB GPU (≈ 15 tok/s). A text-only `qwen2.5:7b` (free) should
  fit fully on the GPU; needs the owner's OK to download ≈ 4.7 GB (C: has ≈ 10 GB free).
