# Professional AI Clipping — Master Plan (Reel Studio 2.0, session 4, 2026-11-05)

Read with `docs/REEL_STUDIO_2_MASTER_PLAN.md` and `docs/REEL_STUDIO_2_HANDOFF.md` before any clipping work. Design detail and
measurements: `docs/BULK_CLIPPING.md`. Status below is evidence-based (code, tests, rendered MP4s), never "done because
it was asked for". Appendix A is the owner's approved prompt **verbatim**; Appendix B the later owner instructions.

**Main objective:** turn one long-form recording (podcast, interview, livestream, class) into 5, 10, 15, 20, 30 or more
professionally edited, meaningful, distinct Shorts — as many as the source genuinely supports (the count is a target).

## Part 1 — Implementation status (code head `635b111`)

Legend: ✅ verified by test + real output · 🟡 built, verified only on the SYNTHETIC fixture or unit tests · ❌ not built

| Area | Status | Evidence / where |
|---|---|---|
| Fixed 6-clip limit | ✅ replaced for talk profiles | `workers/analyze.py` `KEEP = 6` now education-only; talk → `pick_talk` + `bulk.select` |
| Conversation map (questions, answers, stories, lessons, claims, sponsor, tangent…), Q→A links, topics | 🟡 | `highlights/bulk.py` (`split_questions`, `conversation_map`, `merge_topics`), `llm.units(profile=…)`, 80-sentence chunks + per-chunk lexical fallback (`outline.outline`) |
| Speaker labels (CPU MFCC + clustering) | 🟡 | `transcription/diarize.py`; host/guest correct on the fixture; real 85-min podcast found 3 voices |
| 5 profiles + explainable 100-pt editorial score | 🟡 | `highlights/profiles.py`, `bulk.features/score`; education keeps the original scoring |
| Hook / context / payoff, exchange-level completeness, grounded titles | 🟡 | `bulk.features`, `grounded_title`; rule limited to exchanges that fit one Short (`635b111`) |
| Quality-first diverse selection, embeddings dedup, honest shortfall report | 🟡 | `bulk.select`; nomic-embed-text (Ollama) + TF-IDF fallback; fixture 10/10, 15→11, 5-insight→5 |
| LLM standalone check | 🟡 | `llm.judge_talk` (reasoning-first schema, grammar-bounded, invalid answers rejected), cached |
| Caching / count change reuse | ✅ | 5.5 s re-run on the fixture; per-profile outline, embeddings, judgments, faces, speakers caches |
| Face tracking: per-frame faces, exact shot cuts, active speaker, dead-zone camera with eased pans, split screen | ✅ real film scene (visual check of crops + rendered MP4s); 🟡 two-person podcast split screen | `screen_analysis/speakers.py` v3 (`ee32513`), fast-renderer pans |
| Speech cleanup natural/engaging/fast | 🟡 | `clips/speech_cuts.py`; three fixture renders at exact length |
| Fast renderer (FFmpeg/NVENC, ASS captions = preview pages) | ✅ on fixture; 🟡 real | `rendering/fast.py`; 4–22 s per Short; 6 real podcast clips rendered (not yet visually reviewed) |
| Captions: 100 presets, auto style, emphasis, short-form grouping, SRT/VTT | 🟡 | `caption_presets.py`, `caption_auto.py`, `timeline.SOCIAL_CAPTIONS`; fonts renamed "RS <family>" for libass |
| Hook headline styles classic/statement/editorial | 🟡 | `fast._hook` |
| Auto zoom, colour correction, SFX, progress bar, motion graphics (callouts, lower third), AI emojis (Noto 3D) | 🟡 | `timeline._punch/motion_items`, `fast.COLOR_CHAIN`, `rendering/emoji.py` |
| Auto transitions (auto/fade/slide/flash, length kept) | 🟡 | `fast._transitions` + xfade fold |
| Formats 9:16, 4:5, 1:1, 16:9 + layouts auto/fill/fit | 🟡 | `timeline.ASPECTS/reaspect`; all four rendered at exact length |
| Caption translation (20 languages) | 🟡 | `rendering/translate.py`; Hindi Devanagari render checked; ~65 s/clip, somewhat literal |
| Voice dubbing (Kokoro 8 langs or consented profile) | 🟡 | `services/dub.py`; Spanish dub exact length, speech confirmed |
| Auto B-roll | 🟡 needs key | `services/broll.py`; Pexels needs free `PEXELS_API_KEY`; Openverse strict matching usually returns nothing |
| SRT upload instead of ASR | 🟡 | `transcription/srt.py`, unit test |
| YouTube link import | ✅ | `services/link_import.py`, `workers/import_url.py`; CC-BY test + owner's 85-min podcast imported |
| English / non-Hinglish ASR | ✅ | Whisper large-v3-turbo routing (`whisper.choose_model`); podcast 1 213 → 11 895 words |
| One-click recipe (link/upload → transcribe → clips → renders) | 🟡 | `Recipe` (recordings.py), `_auto_render`; first live run exposed and fixed 4 bugs (see handoff §15) |
| Batch render, per-clip status, retry, ZIP, campaign brief | 🟡 | `api/batch.py`, `clips/campaign_brief.py`; ZIP not yet downloaded in a live test |
| Web: Clip video page, gallery, bulk panel, engine switch, resumable uploads | 🟡 | `/clip`, `ClipGallery`, `BulkClipping`, `EngineSwitch` (owner-verified), `lib/uploads.ts` |
| Benchmark vs professional clippers (Phase 11), Hindi/Hinglish podcasts, 60-min benchmark | ❌ | not run |
| Multi-speaker diarization with pyannote/WhisperX, AI B-roll from text, lip-sync dubbing, voice clone of speakers | ❌ | deliberately not built (consent / heavy models); see Part 2 |

## Part 2 — Tools (existing vs proposed)

| Tool | Status | Use / decision |
|---|---|---|
| faster-whisper + Hinglish-Apex CT2 | existing | Hinglish/Hindi (Roman script); **cannot transcribe English** (prints "nan") |
| Whisper large-v3-turbo (CT2, MIT) | **added session 4** | English + other languages; `D:\ReelStudio\models\whisper-large-v3-turbo` |
| Batched faster-whisper | added, off by default | 5× faster but repeated lines on real audio (`WHISPER_BATCH=8` to enable) |
| Silero VAD | existing (inside faster-whisper) | speech regions |
| Ollama qwen2.5vl:7b | existing | outline, judge, translation, B-roll queries; ~1/3 on CPU (15 tok/s). Proposal: text-only qwen2.5:7b (owner OK + move Ollama models to D:) |
| nomic-embed-text (Ollama, Apache-2.0) | added | dedup, topic merge |
| scikit-learn | existing dep, now used | speaker clustering, TF-IDF |
| pyannote.audio / WhisperX | proposed, not installed | gated models / heavy; MFCC clustering used instead |
| Sentence Transformers | not used | nomic embeddings via Ollama instead (no torch in the API venv) |
| MediaPipe | not used | OpenCV YuNet (MIT, 0.2 MB) instead |
| OpenCV, PySceneDetect, FFmpeg (NVENC, libass), Hyperframes, effects registry, Blender | existing | fast renderer = FFmpeg; Hyperframes = studio path; Blender = Mode B 3D only |
| yt-dlp (Unlicense) + Node.js | added | link import |
| fonttools + brotli (MIT) | added | WOFF2 → TTF for libass |
| Noto Emoji 3D PNGs (Apache-2.0) | added (cached on use) | AI emojis |
| Kokoro (via hyperframes tts), Chatterbox profiles | existing | dubbing voices |
| LTX-Video 2B (local) | existing | "AI video B-roll" animates found stills |
| Pexels API (free key) | optional | stock B-roll; owner adds `PEXELS_API_KEY` |
| Openverse (no key) | added | CC photos, strict tag matching |
| MoneyPrinterTurbo (MIT) | studied | idea for stock B-roll search only |
| VoiceStudio (AGPL-3.0) | studied | could run as a separate local dubbing engine; code not copied |

## Part 3 — Next tasks (priority)

1. **Finish and visually review the owner's 85-min podcast run** (project `5dfc9504-6494-4843-ac31-0819e66f15a6`, recording
   `d4b42b3b-…`, re-analysis job `180e2344-…` was running at checkpoint): target 10 clips; check every MP4 (framing of the
   two speakers, captions, hook, endings), ZIP download, gallery. Acceptance: ≥ 8 distinct complete clips or an honest
   shortfall; 1080×1920 H.264/AAC; no clipped sentences; speakers framed.
2. Split-screen check on a real two-camera podcast (face tracking itself verified on a film scene, `ee32513`).
3. Phase 11 benchmark set (60-min podcast, 20-min/5-insight interview, Hinglish podcast) with the metrics in Appendix A.
4. Speed: text-only LLM (owner approval), outline time (~1–2 min per 10 min of audio).
5. B-roll with the owner's Pexels key; Hindi/Hinglish podcast test; dubbing/translation quality review.

---

## Appendix A — Owner's approved prompt (verbatim, 2026-11-05)

REEL STUDIO 2.0 — PROFESSIONAL AI PODCAST CLIPPING & BULK SHORTS ENGINE
You are upgrading our existing Reel Studio 2.0 application.
MISSION: Build a professional AI clipping engine that can analyze a long podcast, interview, livestream or educational recording and automatically generate 10, 20, 30 or more meaningful, distinct, professionally edited Shorts when the source contains enough suitable content.
The experience should be competitive with the useful clipping and editing capabilities of OpusClip, Vizard, Riverside, Klap, Descript and Submagic.
This is an extension of Mode A. Do not rebuild the application or change our dashboard theme.

STEP 1 — RESTORE AND AUDIT THE PROJECT
Working directory: `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`. Repository: https://github.com/sahilkarande0918-cmd/Reel-Studio.git
Read: 1. `AGENTS.md` 2. `CLAUDE.md` 3. `docs/REEL_STUDIO_2_MASTER_PLAN.md` 4. `docs/REEL_STUDIO_2_HANDOFF.md` 5. `docs/CHECKPOINT.md` 6. `docs/CURRENT_TASK.md` 7. `docs/ARCHITECTURE.md` 8. `docs/TEST_STATUS.md` 9. `docs/THIRD_PARTY_LICENSES.md`
Check current Git state and actual code. Inspect specifically: `apps/api/app/services/highlights/outline.py`, `apps/api/app/services/highlights/candidates.py`, `apps/api/app/services/highlights/llm.py`, `apps/api/app/workers/analyze.py`, `apps/api/app/api/collections.py`, `apps/web/components/studio/highlights.tsx`, existing ASR, speaker framing, caption and rendering services, canonical timeline schema and worker queues.
The existing highlight engine uses sentence boundaries, teaching-step outlines, five-component scoring and LLM evaluation. It currently contains `KEEP = 6`, which limits the number of generated highlights. We need to replace the fixed-limit selection design with a configurable, content-aware bulk clipping system. Preserve all verified functionality.
IMPORTANT: Check the latest Supabase environment and migration status. Our newer team Supabase project reference is `pwcbacurvlxzhbaxjjjb`. Never assume an old documented project reference is the active target. Do not modify another project's database.
Also respect the latest engine status. If the production engine has been disabled by the owner, do not re-enable it without permission. Avoid interfering with another active GPU render.

PHASE 1 — ADVANCED CONVERSATION UNDERSTANDING
Upgrade the current context-aware analysis from mainly educational lectures to professional podcasts, business interviews and long-form conversations. The AI must understand the entire recording before choosing individual clips.
Recognize conversational structures. Detect: topic introductions; questions; answers; follow-up questions; personal stories; business lessons; important claims; surprising observations; problems; solutions; examples; debates; disagreements; reveals; conclusions; actionable advice; filler conversations; sponsor segments; repetitive or low-value tangents.
For a business podcast, useful segments might include: a founder explaining why a startup failed; an investor explaining how to evaluate a business; an entrepreneur sharing a sales lesson; a discussion of a common financial mistake; a compelling story that leads to an actual takeaway. The system must distinguish genuinely interesting insights from generic conversation.
Context-first understanding. Use hierarchical analysis: 1. Transcribe the recording. 2. Divide speech into sentences and speaker turns. 3. Identify coherent discussion units. 4. Identify topics and subtopics. 5. Link questions to their answers. 6. Identify examples and conclusions. 7. Build a complete recording outline. 8. Generate clip candidates from meaningful discussion units.
Use the existing Ollama/Qwen and transcription pipeline. For long recordings, use cached chunks with overlapping context and a final global topic map. Do not ask the LLM to analyze an entire multi-hour transcript in one oversized context. Preserve the actual speaker words and timestamps. Never invent quotes or change the meaning of the discussion.
Acceptance: Analyze a realistic long-form business interview containing several topics and produce a time-coded conversation map with questions, answers, stories and conclusions. Test and commit.

PHASE 2 — USER-CONTROLLED BULK CLIPPING
This is the MAIN new feature. Currently Reel Studio is limited to a small number of selected highlights. Replace the fixed selection limit with a configurable bulk clipping workflow.
UI requirements. In Mode A, after selecting/uploading a long recording, add: How many clips do you want? Options: Auto — select all sufficiently strong, distinct clips; 5 clips; 10 clips; 15 clips; 20 clips; 30 clips; Custom number. For custom mode, allow the user to request a practical number based on storage and compute resources. Do not impose an arbitrary small fixed limit in the editor.
Add duration preferences: 15–30 seconds; 30–45 seconds; 45–60 seconds; 60–90 seconds; up to 180 seconds for YouTube Shorts where allowed; Auto — choose the shortest duration that preserves the complete explanation. Respect platform and paid-campaign rules; a 3-minute YouTube Short may not be acceptable for a particular clipping campaign.
IMPORTANT QUALITY RULE: The requested count is a TARGET, not a mandate to manufacture clips. If the video supports only 8 genuinely meaningful standalone moments, generate 8 and explain why the remaining 2 were not produced. Never create repetitive, incomplete or misleading clips merely to reach the requested count.
Candidate discovery. Instead of selecting only the global top-scoring windows: 1. Generate candidates across the whole recording. 2. Group them by topic and semantic similarity. 3. Assess each candidate's story completeness. 4. Rank candidates within topic groups. 5. Ensure broad coverage across the recording. 6. Avoid overlapping or duplicate insights. 7. Select a diverse set of high-quality clips. 8. Report how many suitable clips were found. Do not select all clips from the first 15 minutes simply because their scores are highest. Use semantic embeddings and transcript-overlap checks to identify near-duplicates. Allow multiple clips from the same topic only when they communicate distinct ideas.
Efficiency. Analyze/transcribe the long video only once. Cache: transcript; speaker turns; topic map; candidate spans; visual analysis; reframe information; caption timing; clip scores. Changing the requested clip count should reuse cached analysis instead of restarting transcription.
Acceptance. Test: 10 requested clips from a recording with at least 10 genuine standalone insights; 20 requested clips from a sufficiently varied long recording; a request for 15 clips from a recording that only supports 7 meaningful clips; deduplication of overlapping candidates; changing the clip count without unnecessary full reanalysis. Commit and push after verification.

PHASE 3 — PROFESSIONAL HOOK, STORY AND PAYOFF DETECTION
This is the most important part of selecting good podcast clips. Every selected clip should ideally have: HOOK → CONTEXT → VALUE → PAYOFF / ENDING.
Hook. The clip should begin with something that makes sense and creates interest. Potential patterns: surprising statement; strong question; interesting business mistake; unexpected insight; clear problem; compelling personal experience; strong opinion supported by the discussion. Do not automatically start a clip with: "Yeah, exactly." "As I was saying..." "And that's why..." "Coming back to the previous point..." unless the necessary context is included.
Context. The viewer must understand what the speaker is discussing without watching the full podcast. If the guest answers a question, include the question when necessary. If the speaker says "this company," "he," or "that strategy," ensure the referent is clear.
Value. The segment must contain a useful insight, example, meaningful story or other genuine entertainment/informational value.
Payoff. The clip must reach its meaningful conclusion. Do not stop: before an answer; halfway through a story; immediately before the actual lesson; in the middle of a sentence; just before the speaker reveals the important point.
Boundary refinement. Use sentence boundaries, word timing, speech pauses, VAD, speaker turns and content structure. Allow slight lead-in/out breathing room. Prefer clean pauses and natural cuts. Never remove context so aggressively that the clip changes the speaker's intended meaning.
Smart hook editing. Where justified, support creating a stronger opening using an authentic quote from later within the same source recording. If doing so: preserve the original words; do not invent speech; do not create a misleading sequence; avoid repeating the same sentence unnecessarily; keep the original timeline edit reversible; clearly label rearranged openings in editing metadata. Do not use artificial clickbait unrelated to the actual video.
Acceptance. Test with real question-answer exchanges and multi-part stories. Verify complete sentences, natural openings, intact explanations and meaningful conclusions. Commit and push.

PHASE 4 — ADVANCED CLIP RANKING
Extend the current educational scoring system with a separate Business/Podcast profile. Use an explainable 100-point editorial ranking, for example: Hook strength: 20. Standalone context completeness: 25. Payoff/story completion: 20. Information/entertainment value: 15. Speech delivery and audio engagement: 10. Visual suitability: 5. Campaign/topic relevance: 5. These are initial scoring weights, not a verified virality prediction model. Make scores inspectable and tunable. Allow future tuning based on real outcome data.
For every recommended clip, produce: title grounded in spoken content; source timestamps; duration; editorial score; hook quote; main insight; ending quote; why the clip was selected; relevant topic; potential context limitations; duplicate group, if applicable; editing recommendations. Do not label an editorial score as a guaranteed probability of going viral.
Add configurable selection profiles: 1. Business/Entrepreneurship. 2. Podcast/Interview. 3. Educational/Technical. 4. Motivational/Storytelling. 5. General creator clips. Preserve our existing Education scoring profile and previously generated clip data.
Acceptance. Generate visibly different clip rankings for business insights versus educational explanations. Commit and push.

PHASE 5 — MULTI-SPEAKER PODCAST EDITING
Improve the automatic vertical crop engine. Research and evaluate: https://github.com/pyannote/pyannote-audio, https://github.com/m-bain/whisperX, https://github.com/snakers4/silero-vad. Reuse existing OpenCV, MediaPipe and FFmpeg.
Add: speaker diarization where suitable; speaker-turn detection; active speaker tracking; face-position tracking; smooth 9:16 reframing; multi-speaker split-screen layouts; interviewer/guest switching; picture-in-picture when useful; smart crop smoothing; avoid cutting off faces; avoid unnecessary camera movement. The editor should know when to display the person asking the question and when to show the person answering. Do not blindly switch on every sound or syllable. Use hysteresis and stable layouts to avoid jitter. If only one camera angle is available, use defensible crops, not fabricated camera views. On the 8 GB GPU, use CPU or lightweight models where appropriate. Keep diarization optional if it causes excessive latency or installation complications.
Acceptance. Test a two-person interview containing multiple speaker turns. Verify framing and speaker switches in the actual rendered MP4. Commit and push.

PHASE 6 — PROFESSIONAL AUTOMATIC CUTS
Implement a non-destructive speech-aware editing pass. Automatic cleanup. Detect: long silences; unnecessary pauses; filler words; repeated words; false starts; retakes; awkward gaps.
Provide pace presets: Natural — preserve conversational rhythm and meaningful pauses. Engaging — remove unnecessary dead air while maintaining natural speech. Fast — tighter editing suited to energetic Shorts. Never remove all pauses. Do not automatically remove a hesitation that changes the meaning or character of a statement. Retain all original audio/video and save cuts as editable timeline operations.
Smart jump cuts. Apply: frame-accurate speech cuts; minimal visual discontinuities; appropriate reframing around jump cuts; subtle zoom variation where useful; controlled transitions; smooth audio joins. Avoid random effects on every cut.
Optional audio enhancement. Reuse FFmpeg and existing local tools for: noise reduction; volume normalization; mild EQ; speech clarity; music ducking; peak control.
Acceptance. Render three versions of the same podcast highlight: 1. Natural. 2. Engaging. 3. Fast. Confirm that meaning is preserved and differences in pacing are observable. Commit and push.

PHASE 7 — PREMIUM AUTOMATIC SUBTITLES
Reel Studio already has 100 caption styles. DO NOT recreate the library. Upgrade automatic selection, timing and rendering.
Professional subtitle requirements: accurate word-level timestamps; correct punctuation; capitalization; proper nouns; business terms; speaker names when known; Hindi/English/Hinglish handling; editable transcript; readable caption groupings; vertical safe-zone positioning; 1080×1920 rendering; no text clipping; no missing words.
Smart caption grouping. Use phrase boundaries and speech rhythm. For fast social captions, show small readable groups, often 2–5 words, with exceptions for natural phrasing. Avoid: too much text on screen; random mid-sentence breaks; tiny fonts; constant flashing; excessive emojis; captions covering faces or products.
AI-selected caption emphasis. Automatically emphasize: important numbers; strong statements; business terms; surprising words; contrasts; questions; key takeaways. Use visual emphasis based on content rather than randomly highlighting every word.
Caption styles. Preserve all 100 existing presets. Add an Auto style selector that chooses a suitable preset based on: video type; pace; brand kit; spoken language; creative brief; subject/background contrast. Examples: Business podcast: clean bold captions with restrained highlights. Motivational clip: impactful emphasis and kinetic text. Educational clip: minimal, precise captions with technical terms highlighted. Preserve captions ON/OFF. Ensure the actual final MP4 matches the preview. Export SRT/VTT as well.
Acceptance. Render several caption styles on one podcast clip. Verify timing, safe zones, readability and actual preset application. Commit and push.

PHASE 8 — INTELLIGENT PROFESSIONAL VIDEO POLISH
Use our existing FFmpeg, Hyperframes, GSAP, effects registry and motion templates. Automatically determine which visual polish is justified. Available treatments: punch zooms; smooth pushes; dynamic reframing; emphasized words; animated hook titles; lower thirds; simple kinetic typography; subtle motion blur; match cuts; tasteful transitions; visual callouts; key-number highlights; branded graphics; contextual B-roll; music and sound effects.
Smart effect selection. For a serious business podcast, avoid excessive wobble, flashing, RGB effects or phonk transitions unless explicitly requested. Prioritize clarity and retention over flashy visuals. Use effects when: a key statement lands; a new topic begins; a surprising number is mentioned; a visual example improves understanding; a scene needs a clean transition; a hook needs emphasis.
B-roll. Allow: user-uploaded B-roll; original generated motion graphics; properly licensed stock assets; relevant source footage. Choose B-roll grounded in the actual discussion. Never insert misleading images representing an event as real footage. Do not automatically download copyrighted content without authorization.
Hook title. Optionally add an opening headline, such as: "The Biggest Mistake New Founders Make". Only when the actual speaker discusses that subject. No fabricated quotes or unsupported factual claims.
Acceptance. Compare an unpolished source clip against its professionally edited result. Verify: real visual changes; correct captions; deliberate effect placement; readable layouts; natural audio; clean ending. Commit and push.

PHASE 9 — ONE UPLOAD → 10+ PROFESSIONAL SHORTS
Create a new user-facing Mode A workflow: Bulk AI Clipping. User experience: 1. Upload a long video. 2. Select the content category. 3. Select the number of requested clips. 4. Select preferred duration. 5. Select editing intensity. 6. Choose caption style or Auto. 7. Choose brand kit. 8. Optional editing prompt. 9. Click Generate Clips.
Example prompt: "Find 15 of the strongest business insights from this podcast. Each clip must explain a complete idea, start with an engaging hook and end naturally. Use professional captions, clean cuts, occasional punch zooms and smooth speaker framing. Avoid repeated topics and preserve the speaker's meaning."
Result gallery. Show: all discovered clips; preview thumbnails; titles; durations; source timestamps; scores and explanations; topic labels; strong opening/ending quotes; selection controls; individual editing; boundary adjustments; caption style selection; regenerate selection; render selected; render all eligible; download individual clips; download all as ZIP.
Bulk processing. Use our existing durable background-job architecture. Support: incremental processing; separate status per clip; retry failed renders; cancellation; partial completion; safe concurrency; disk-space checks; no duplicate exports; consistent branding; reuse of cached analysis; recoverable work after a worker restart. Rendering 20 Shorts must not require processing the entire source 20 times. Save the complete batch under a project with individual clip metadata. Avoid re-rendering unchanged clips. Provide clear progress based on actual job states, not fabricated percentages.
Export format. Default for YouTube Shorts: portrait 9:16; 1080×1920; H.264 MP4; AAC audio; 30 fps, configurable where source and effects support it; accurate captions; suitable audio levels; optional separate SRT; thumbnail; editable title and description suggestions. Support platform-specific duration settings. Do not implement automatic YouTube OAuth/upload without separate authorization; the immediate goal is excellent Shorts-ready files.
Acceptance. Upload one suitable long-form recording and request at least 10 clips. Verify actual output files. Every clip must be: distinct; meaningful; properly framed; correctly captioned; audible; free of clipped sentences; complete enough to stand alone; valid MP4. If the recording lacks sufficient meaningful segments, return fewer clips and an honest explanation. Commit and push.

PHASE 10 — CAMPAIGN-READY CLIP EDITING
This feature is useful for approved Clipadi/Clipster campaigns. Add an optional Clipping Campaign Brief input. Allow the user to specify: campaign name; authorized source video; required topic; minimum/maximum video length; required hashtags; required account mentions; required caption text; brand guidelines; target audience; allowed platforms; content restrictions. The AI should use these constraints to guide selection and export.
Implement: length validation; caption/metadata validation; required tag checks; content originality review flags; source-rights confirmation; duplicate-submission warnings; export-ready caption suggestions. Do not imply that satisfying these checks guarantees payment, views or YouTube monetization. Do not automatically publish campaign clips. Do not download or reuse copyrighted podcast or TV-show content without appropriate rights. Do not implement view manipulation, fake engagement or monetization evasion.
Acceptance. Create a test campaign brief and verify that generated Shorts respect its duration and metadata requirements. Commit and push.

PHASE 11 — VALIDATION AGAINST PROFESSIONAL CLIPPERS
Benchmark our output quality using real, authorized long-form content. Study the published capabilities of: OpusClip; Vizard; Riverside; Descript; Submagic; Klap. Do not use their paid APIs as mandatory dependencies. Compare relevant functionality, not unsupported marketing claims.
Evaluation dataset. Prepare recordings with: multiple speakers; long interviews; several separate topics; questions and answers; filler words and awkward pauses; clear stories; incomplete discussions; repeated advice; different speech rates; Hindi, English and Hinglish. Include source clips with known good start/end references.
Measure: clip count achieved versus meaningful clips available; standalone context completeness; opening quality; ending quality; sentence truncation rate; duplicate insight rate; topic coverage; speaker framing correctness; caption timing drift; caption word accuracy; audio continuity; render success rate; resource usage; processing time. Use human review for subjective metrics such as hook quality and storytelling. Do not invent a single objective "professional quality" score without defined evaluation.
Mandatory test cases. Test 1: 60-minute podcast with at least 12 independent insights → request 10 clips. Test 2: 20-minute interview with only 5 complete insights → request 15 clips and verify that the system does not invent the other 10. Test 3: Two-speaker podcast → verify accurate speaker-aware layout. Test 4: Business podcast with filler words → compare Natural, Engaging and Fast edits. Test 5: Same clip with multiple caption styles → verify text legibility and timing. Test 6: Source with repetitive discussion → verify near-duplicate rejection. Test 7: Bulk rendering → verify ZIP, individual MP4s, partial retries and project persistence. Test 8: Existing educational Mode A regression. Test 9: Existing prompt-driven Mode B regression. No claims of success without actual test results.

DEVELOPMENT RULES. Preserve: existing Next.js frontend; FastAPI backend; Supabase Auth/RLS; canonical timeline schema; Ollama/Qwen; Whisper transcription; OpenCV; Hyperframes; FFmpeg; Blender functionality; 100 existing caption presets; Mode B professional editing; voice cloning; Instagram integration; approved forest-green/ivory dashboard design. No redesign. No mandatory paid API. Use the existing local GPU efficiently. Evaluate each new repository's code and model-weight licenses before installing. Do not run heavy models simultaneously when the 8 GB VRAM budget cannot support them. Never change unrelated Supabase projects or AnswerRank/Tamrivo. Never publish real Shorts or Reels without my explicit approval. Never commit secrets, personal recordings or copyrighted test media. Never add Claude, Codex, Anthropic, Cursor or AI agents as Git authors/co-authors. Preserve genuine Git history.
COMMIT AND PUSH AFTER EVERY VERIFIED PHASE: implement; run tests; verify actual media output where applicable; fix defects; update documentation; commit using the established Git identity; push to `sahilkarande0918-cmd/Reel-Studio`; continue. Update: `docs/REEL_STUDIO_2_MASTER_PLAN.md`, `docs/REEL_STUDIO_2_HANDOFF.md`, `docs/CHECKPOINT.md`, `docs/CURRENT_TASK.md`, `docs/PHASES.md`, `docs/ARCHITECTURE.md`, `docs/TEST_STATUS.md`, `docs/THIRD_PARTY_LICENSES.md`. Do not repeatedly ask whether to proceed with routine coding tasks. If GPU testing requires re-enabling a production engine deliberately stopped by the owner, ask first and use isolated test workers where possible. If essential test media is missing, use appropriate authorized fixtures and clearly mark what remains unverified with real footage.
FINAL GOAL. The user uploads a 60-minute business podcast, selects "Generate 15 professional Shorts," and Reel Studio: 1. Understands the complete podcast. 2. Finds its strongest standalone moments. 3. Rejects filler and repeated insights. 4. Selects natural beginnings and endings. 5. Generates as many meaningful clips as possible. 6. Reframes each speaker intelligently. 7. Removes unnecessary dead air. 8. Applies professional subtitles and appropriate effects. 9. Produces actual 1080×1920 MP4s. 10. Allows preview, individual editing and bulk download.
START BY AUDITING THE EXISTING HIGHLIGHT SELECTION SYSTEM. REPLACE THE HARDCODED SIX-CLIP LIMIT WITH A QUALITY-AWARE BULK CLIPPING ENGINE. THEN COMPLETE THE REMAINING PHASES. Build actual functionality, not only UI or planning documents.

## Appendix B — Later owner instructions in session 4 (quoted where short)

- "it should be fast generation without reducing quality, precision etc. search any tools, repos available for it"
- "take reference how opusclips make, i want the exact output and all features which opus clips has" (screenshots:
  recipe, AI picks/clip length/moments prompt, caption style tiles, Auto hook Editorial/Statement/Classic, motion
  graphics, AI emojis, Auto B-roll, speech cleanup, enhance audio, auto SFX, auto zoom, auto transitions, auto colour
  correction, voice dubbing, caption translation, adjust range, 9:16 layouts, upload SRT; brand kit with caption/headline
  style, layouts per ratio, intro/outro, ratio preview) — implemented as the same workflow/features in our own design;
  identical output is not claimed.
- "any api key needed, or any credentials ask me, and dont use any paid tools or api keys, use free ones only"
- Add features: Auto B-roll, AI emojis, motion graphics in the fast renderer, voice dubbing, caption translation,
  upload SRT, auto transitions, square and landscape formats — all built (Part 1).
- "add a button to start and turn off engine" → desktop button; "button should be on dashboard of website" → dashboard
  Engine card (owner verified in Chrome).
- "if i leave platform in background tabs, or switch sections, or refresh the website it should not stop the work" →
  server-side jobs + app-wide resumable upload manager.
- "add a feature of pasting link from youtube directly" → link import (rights confirmation required).
- "dont make any video pause video generation if doing, just keep on engine" (HP Victus re-render cancelled).
- Repos checked on request: MoneyPrinterTurbo (MIT, idea only), VoiceStudio (AGPL, not copied).
