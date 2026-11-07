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
uploads). Title, channel and licence are kept in `source_recordings.probe.import`. Verified 2026-11-05 through the production
engine: Blender's *Big Buck Bunny* (CC-BY) link → downloaded on the engine (H.264 1080p + AAC, 10.6 min, 289 MB),
probed, transcription queued and run automatically (0 words: the film has no dialogue). Fixed after the test: progress
no longer jumps back when the audio stream starts; the import's title/channel/licence are kept after probing. The
automatic analysis after transcription keeps the original class settings; choose the category in Bulk AI clipping.

## OpusClip-style one-click flow (session 4, commits `768f4b6` … `393c27f`)
**Web:** sidebar "Clip video" → `/clip` (`components/clip/clip-studio.tsx`): paste link or upload, speech language,
genre (auto), adjust range, SRT, ratio 9:16/16:9/1:1/4:5 + layout with a live phone preview, recipe (clipping: AI
picks/length/moments; captions with the 100 preset tiles; auto-hook headline tiles classic/statement/editorial; motion
graphics; AI emojis; auto B-roll; speech cleanup; enhance audio; auto SFX; auto zoom; auto transitions; colour
correction; progress bar; voice dubbing; caption translation; brand kit) → **Get clips** creates the project and hands
the recipe to the engine. Project page: `ClipGallery` grid (preview, score, length, live render state, download, ZIP).
**Engine:** `Recipe` (recordings.py) stored in `source_recordings.probe.recipe` → transcription uses its language (or
the uploaded SRT, `transcription/srt.py`) → analysis uses its clip options → `_auto_render` queues every clip with its
render settings. A manual re-run from the Bulk panel never auto-renders.
**Renderer additions** (`rendering/fast.py`, `timeline.py`): formats via `timeline.ASPECTS` + `reaspect`; transitions
(`_transitions`, xfade without changing the edit's length); motion graphics (`motion_items`: number callouts, topic
lower third); progress bar; AI emojis (`rendering/emoji.py`, Noto 3D PNGs); caption translation
(`rendering/translate.py`, 20 languages, in the render worker, timeline saved back so SRT/VTT match); B-roll
(`services/broll.py`); dubbing (`services/dub.py`, Kokoro en/hi/es/fr/it/pt/ja/zh or a consented voice profile).
**Measured on the synthetic fixture:** all four formats exact length (9:16/1:1/4:5/16:9, 11–22 s per clip with every
option on); Hindi captions render in Devanagari (translation 65 s with the 7B model, somewhat literal); Spanish dub
15 s + render 7 s, exact length, speech confirmed by re-transcription.
**Honest gaps:** stock B-roll needs the owner's free `PEXELS_API_KEY` in `apps/api/.env` (Openverse photos rarely match
strictly; loose matches were rejected after a political photo appeared for "sales demo"); AI B-roll animates found
stills only; dubbing does not clone other speakers' voices (consent) and removes the original background; the studio
(Hyperframes) renderer ignores the new fast-renderer-only options; the whole one-click flow has not yet been run
through the live website with a real podcast.

## Flow
`POST /recordings/{id}/analyze` with `{profile, count, duration, brief, range_start_s, range_end_s}` →
`workers/analyze._analyze_talk` (any profile except `education`, which keeps the original class-reel path and `KEEP = 6`):

1. **Words** of the latest transcript (optionally only the adjusted range). Transcription itself is now batched
   (`whisper.BATCH=8`, faster-whisper `BatchedInferencePipeline`, sequential fallback; `WHISPER_BATCH=0` disables).
2. **Face tracking** (`screen_analysis/speakers.py`, cached `faces.json` v3, session 4 rewrite `ee32513`): one decode —
   YuNet faces on every frame at 6 fps / 480 px (a missed detection holds the box ≤ 1 s, never across a cut) and a
   64x36 thumbnail of EVERY source frame for exact camera cuts. Per clip and shot: faces linked into tracks, the speaker
   = smoothed (1 s) mouth motion while there is speech, weighted to the nearer/larger face, hysteresis + 1.5 s minimum
   turn; a dead-zone camera follows a moving person with eased pans (fast renderer: FFmpeg crop expressions), cuts on
   the film's own cuts (no extra fade) and on a speaker change; people who fit one 9:16 window are framed together;
   rapid 2-s turns between two distant people → split screen. Verified visually on a real edited film scene (3 min,
   36 cuts): every close-up/over-the-shoulder shot framed, face box inside the crop, crop switches on the cut frame.
   v1 (fixed median "seat" per person for the whole video) put half the face out of frame in edited footage.
   Model `D:\ReelStudio\models\yunet\face_detection_yunet_2023mar.onnx` (`FACE_MODEL` env), Haar fallback.
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

## Clip count fixes (session 4, `ee32513`, talk profiles only)
Unpunctuated ASR "sentences" > 12 s are split at real pauses (incl. silence Whisper hides inside a stretched last
word); a pause no longer splits a sentence when the next word continues it ("I … heard", "Your … Grace"); a Q&A
exchange must be whole only when it fits one Short (was 1.5× max — exchanges between 1× and 1.5× could never be
clipped); windows inside parts longer than one Short can be whole; a part's dangling fragment of the next sentence
("… Power | Do") is dropped. Film scene, 5 × 15–30 s requested: 2 → 4 clips (honest shortfall for the 37-s
unpunctuated overlapping opening).

## Enhance to 4K (session 4)
Each finished reel has "Enhance to 4K" (+ optional "HDR look") in the clip gallery and the reel panel →
`POST /renders/{id}/enhance` → child render (`parent_render_id`, `timeline_hash` "4k:…") → `enhance` job
(`workers/enhance.py`): (1) the reel's picture WITHOUT text rebuilt by the fast renderer at the source's own pixel density
(720p source → 404×720; capped at 540×960 = a quarter of 4K), near-lossless; (2) Real-ESRGAN realesr-general-x4v3 with
0.75 denoise blend, fp16 + channels-last on the GPU in the torch env (`services/upscale_worker.py`, frames piped, YUV
conversion on the GPU, repeated frames reused); (3) captions / hook / progress bar / emojis drawn fresh at 2160×3840 by
libass, CAS sharpening, optional vivid look (SDR BT.709 — no fake HDR), H.264 High ~45–55 Mbps (YouTube 4K SDR
recommendation 35–45), AAC. Reels the fast renderer cannot rebuild are upscaled with their text. The ZIP takes the 4K
version when it exists. Measured: 13.6 s reel from 1080p in 67 s (8.2 fps); 43.3 s reel from 720p in 123 s (12.9 fps)
through the production engine. Honest limit: it removes compression blocks/noise and gives crisp text and edges; it cannot
recover detail a 720p crop never had. Platforms always re-compress; a high-bitrate 4K upload gets YouTube's better
VP9/AV1 encodes, Instagram downsizes to 1080 wide. Not built: face restoration (GFPGAN, Apache-2.0) — next candidate.
OpenCut-app/OpenCut was evaluated: a browser editor with no upscaling (its export is being rewritten), so nothing to reuse.
**Quality pass v2 (2026-11-07, after the owner found 4K/HDR "dull")** — measured on the owner's own HDR CC Tyrion reel: the
tutorial recipe pushed saturation +20-50 % (skin orange) and crushed the darkest 5 % to black in dark film scenes, and the
upscale alone added no sharpness at phone size. Fixes: (1) GFPGAN v1.4 face restoration (Apache-2.0, vendored clean
arch, run under autocast — pure fp16 turns faces grey and hazy) on every frame with a face (YuNet landmarks, smoothed
over time, FFHQ alignment, feathered 65 % blend): eyes, lashes, hair strands and skin structure come back; (2) HDR CC v2:
colour burn 22 %, white overlay 50 %, shadow guard, vibrance instead of saturation, clarity — local contrast +44-48 %,
saturation only +12-16 %, shadows lifted not crushed; (3) natural finish for the plain option (clarity + vibrance +
shadow guard); (4) decode of the intermediate as BT.709 (FFmpeg assumed BT.601 → dulled reds/greens); (5) light temporal
grain at 4K so cleaned skin never looks plastic. Tyrion 33.8 s reel: 233 s (5.5 fps), 786 of 1014 frames with a restored
face; face-area frame-to-frame change 4.8 vs 3.7 in the original (no visible flicker). Not used: CodeFormer
(non-commercial licence), RealESRGAN_x4plus (far too slow for video on 8 GB), OpenCut (no colour tools).

**HDR CC option** = the AV Solutions "4K HDR CC Tutorial in CapCut" recipe, read frame by frame from the owner's copy of
the video and rebuilt as one FFmpeg graph (`fast.hdr_cc`, applied to the base before the upscale): (1) adjustment layer
with luma/R/G/B curves all inverted + Blur effect → blurred negative; (2) that layer in Color burn at 29 %; (3) a white
image in Overlay at 83 %; (4) adjustment Hue/tint +12, Saturation +18, Brightness +7, Shadow −9, Sharpen +12, HSL red hue
+16, orange hue +15 / sat +17. CapCut's opacity mixes towards the layer below, FFmpeg's blend opacity towards the top
input, so the colour burn is an explicit expression. The tutorial does no real upscaling — "4K" there is only the export
size; our 4K adds Real-ESRGAN. OpenCut cannot do it: blend modes only on text, its "curves" are keyframe easing, no
adjustment layers or video blur. Measured: 13.6 s 1080p reel, HDR CC 4K in 80 s through the engine.

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
