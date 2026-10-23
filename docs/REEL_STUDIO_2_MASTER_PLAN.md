# Reel Studio 2.0 — Master Plan (permanent, authoritative)

This file is the complete approved specification for Reel Studio 2.0 plus its current implementation status. A new
agent must be able to continue from this file and `docs/REEL_STUDIO_2_HANDOFF.md` alone, without chat history.
Where this file conflicts with 1.0 documents (`MASTER_PROMPT.md`, `PHASES.md`, `ORIGINAL_PS.md`), **this file wins**;
those stay as history and must not be deleted.

- Part 1: status map (what is VERIFIED / PARTIAL / UNTESTED / NOT IMPLEMENTED), as of 2026-10-24, HEAD `de9729a`.
- Part 2: standing owner rules (non-negotiable).
- Part 3: the owner's Reel Studio 2.0 master prompt, preserved verbatim (Appendix A) with the working-directory /
  authorship addendum (Appendix B) and later owner instructions (Appendix C).

---

## Part 1 — Status map (2026-10-24)

Legend: ✅ VERIFIED (code + run + evidence) · 🟡 PARTIAL (some parts built/verified) · ⚪ UNTESTED (code exists, not
run end to end) · ⬜ NOT IMPLEMENTED.

| Requirement (prompt section) | Status | Evidence / what exists | What is missing |
|---|---|---|---|
| Stage A — repository migration | ✅ | `docs/MIGRATION.md`: same main SHA `a28eaca` + tree `02ae2cf`, 295 files, 87 commits verified before rewrite; owner then asked to drop two other people's placeholder commits (`docs/sk`, `docs/sahil`) → new history, all commits by the owner, new main `6e94ddf`, force-pushed once to the new repo only | — |
| Stage B — project restoration (read docs, keep stack, keep UI) | ✅ | New folder runs: API pytest 107 passed / 6 skipped, web tsc + lint clean, schema vitest 12 passed | Production engine + Vercel still run from the OLD folder/repo (see handoff) |
| Phase 1 — reference analysis + tool audit | ✅ | `docs/REFERENCE_STYLE_ANALYSIS.md` (all 6 references + guide PDF, measured + time-coded), `docs/OPEN_SOURCE_TOOL_AUDIT.md` (licences checked on GitHub) | Region-of-interest shot detection for layout/screen references |
| Phase 2 — unrestricted clip ingestion | 🟡 | `app/services/clips/analysis.py` (per-clip motion, sharpness, brightness, moments, motion+interest framing, proxy function) used on 17 real clips | No `media_assets` table, no multi-file/resumable upload API or UI, no dedupe, no queue/cancel, no 1/2/10/30+ acceptance run |
| Phase 3 — Reference Style Analyzer | 🟡 | `app/services/reference/analyzer.py` (+ `tests/analyze_references.py`), 6 profiles + contact sheets; optional local-VLM key-frame descriptions | Not exposed in the app (no API/UI, no stored profile table, no visual report page) |
| Phase 4 — music, phonk, beat sync | 🟡 | `app/services/music/beats.py` (tempo from kick band, beats, downbeats, accents, energy, relative drop detection), `editing/pacing.py` (9 profiles), `editing/planner.py`, `editing/style_transfer.py`; **real 16 s reel from 17 owner clips + owner phonk track in Reference 4 style, QA all pass** | Manual beat correction UI, phrase detection, per-profile acceptance renders, app integration |
| Phase 5 — effects engine | 🟡 | `app/services/editing/effects.py`: 24 FFmpeg effects (camera/blur/impact/light) + 21 xfade transitions; `tests/effects_gallery.py` measured 45/45 change the picture / exact frame counts | Category E velocity beyond eased ramps/reverse/freeze (no frame interpolation yet), Category G composites (cutout, text-behind-subject, PiP, split screen, depth), shader (gl-transitions) layer, preview/export parity UI, substitution explanations |
| Phase 6 — motion design engine (Hyperframes) | ⬜ | Existing 1.0 Hyperframes compiler (`services/rendering/compose.py`) for Mode A captions/code cards only | Template library (kinetic type, cards, mockups, chat, counters, calendars, lists, CTA, light sweeps…), 15–30 s ad render |
| Phase 7 — AI Editing Director | ⬜ | Keyword fallback `pacing.guess()` only | LLM planning with schema validation, storyboard, distinct outputs per prompt |
| Phase 8 — renderer router (+ Blender) | 🟡 | FFmpeg base picture + separate audio + mux is the footage path (`editing/render.py`) | Router across FFmpeg/Hyperframes/shader/Blender; **Blender not installed, Blender MCP not configured**, no headless Blender worker |
| Phase 9 — voice cloning | ⬜ | — | Chatterbox evaluation, consent flow, profile storage, Hindi/Hinglish tests |
| Phase 10 — 100 caption styles + ON/OFF | ⬜ | 1.0 caption presets (`highlight-word`, `karaoke`, `boxed`) + style presets | 100 presets, gallery, ON/OFF, render parity |
| Phase 11 — AI clip collections | ⬜ | 1.0 context-aware highlights (teaching steps, scores) in Mode A | Topic clustering into series, grounded titles, batch render, scheduling |
| Phase 12 — business campaign agent, localization, results tracking | ⬜ | 1.0 Instagram insights refresh | Campaign generator, EN/HI/Hinglish localisation, UTM/click/WhatsApp tracking, grounded suggestions |
| Phase 13 — Instagram automation extensions | 🟡 | 1.0 OAuth, publish queue, retries, dedupe, delivery copy, insights (3 real Reels published in 1.0) | Campaign-aware scheduling, cover selection, caption suggestions in 2.0 flow |
| Phase 14 — quality engine | 🟡 | `app/services/editing/qa.py`: exact length, hard cuts on planned frame, cuts/transitions vs beat, transition visibility, black/frozen frames, LUFS/true peak; mux auto-repairs true peak | Text clipping/safe zones, A/V sync per range, masked words, motion jitter, contact sheets in app, VERIFY report, automatic repair loop |
| Phase 15 — E2E tests A–H | 🟡 | Test F-like (2 clips) and Test A-like (17 clips + phonk + Ref 4) rendered with the engine script | Tests B, C, D, E, G, H; all through the app UI |
| Mode B UI (replace Topic → Video) | ⬜ | Topic Studio (1.0) still in the app | New Mode B project flow, removal of old topic entry points while keeping old projects readable |

### Generated outputs (local, not in git)
| Output | Path |
|---|---|
| Phonk reel (17 clips + owner phonk track, Reference 4 style), 16 s, QA all pass | `C:\Users\Sahil\AppData\Local\reel-studio\data\mode-b-tests\grind-phonk-ref4\edit.mp4` (copy: `C:\Users\Sahil\OneDrive\Desktop\grind-phonk-reel.mp4`); plan `…\grind-phonk-ref4\plan.json`; QA `…\grind-phonk-ref4\report.json` |
| First engine test (2 class recordings + synthesized phonk score) — internal only, contains third-party branding | `…\data\mode-b-tests\f-two-clips-phonk\edit.mp4` |
| Effects/transitions gallery (45 renders + sheet + gallery.json) | `…\data\effects-gallery\` |
| Reference profiles (style.json + contact sheets) | `…\data\reference-analysis\` |
| Owner music analysis | `…\data\mode-b-tests\phonk-audio.json` |

### Owner-supplied inputs (local, never committed)
- Reference reels: `C:\Users\Sahil\Downloads\reel template.mp4`, `reel template 2.mp4`, `reel template 3.mp4`,
  `reel template 4.mp4`, `reel template 5.mp4` (extra), `reel template 6.mp4`.
- Guide: `C:\Users\Sahil\Downloads\VenomsTechAI_Claude_Video_Editor_Guide.pdf`.
- Test footage: `C:\Users\Sahil\Downloads\clip 1.mp4` … `clip 17.mp4` (copies with underscores in
  `…\data\mode-b-tests\src\clip_N.mp4`); music `C:\Users\Sahil\Downloads\phonk audio.mpeg` (129.2 BPM, drop 15.19 s).
- Owner instruction: use **Reference 4 (`reel template 4.mp4`) as the template** for the phonk edit.

---

## Part 2 — Standing owner rules (apply to every phase)
1. ₹0 mandatory cost; no paid APIs/hosting/render cloud required; an external LLM key may be OPTIONAL for planning only.
2. Git: commit only as `sahilkarande0918-cmd <sahilkarande0918@gmail.com>`. Never add Claude, Anthropic, Codex, Cursor,
   AI agents or bots as authors, co-authors or contributors. **No `Co-Authored-By` trailers.** Never backdate,
   impersonate or squash history into misleading commits. Never force-push unrelated work.
3. Work only in `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0` against
   https://github.com/sahilkarande0918-cmd/Reel-Studio.git. The old `Open_PS04_` repo and `C:\dev\Reel-Studio` are
   read-only history (the old folder still runs the production engine until deliberately re-pointed).
4. Supabase: only project `adjwycjsxtxvjockxtan`; never the owner's separate SaaS project; never disable RLS; every new
   table needs explicit grants.
5. Never publish an Instagram post without explicit approval of the exact account, video and caption. Never use the
   personal account `@sahil_karande`. YouTube postponed.
6. No secrets, tokens, private media, voice samples, model weights or generated files in git.
7. The forest-green / warm-ivory UI is FINAL: no redesign; new features use existing tokens and components.
8. No fake features: every control does something real or shows a truthful unavailable state; synthetic data labelled.
9. Never claim something works without running it; record every test in `docs/TEST_STATUS.md`.
10. Reference reels are for technique only; never copy their footage, audio, branding, logos or text.

---

## Part 3 — Appendix A: owner's Reel Studio 2.0 master prompt (verbatim)

REEL STUDIO 2.0 — COMPLETE REPOSITORY MIGRATION + ADVANCED AI VIDEO EDITOR MASTER PROMPT
YOUR ROLE AND MISSION
You are the principal architect, AI engineer, professional video-editing engineer, motion designer, audio-processing specialist and full-stack developer for Reel Studio 2.0.
We already have a substantial, working Reel Studio application.
Your task has TWO major objectives:
OBJECTIVE 1 — FIRST PRIORITY: Transfer the complete original GitHub repository into our new GitHub repository, preserving every tracked project file, directory, configuration, asset, dependency declaration, document and original Git history.
OBJECTIVE 2 — ONLY AFTER OBJECTIVE 1 IS VERIFIED: Upgrade the application into an AI-powered professional video-editing and business content automation platform.
Do not create a new application from scratch.
Do not replace working architecture unnecessarily.
Do not start implementing new features until repository migration has been completed and verified.
The final platform should allow ordinary users to upload raw clips, optionally provide music and a reference video, describe their desired edits, and automatically receive a professional edited Reel.
The application must perform genuine video editing, including advanced effects, motion graphics, music synchronization, typography, compositions, creative transitions, professional narration and Instagram publishing.

STAGE A — TRANSFER THE ENTIRE EXISTING REPOSITORY FIRST
A1. Exact repository details
Original repository — SOURCE: https://github.com/sahilkarande0918-cmd/Open_PS04_.git
New repository — DESTINATION: https://github.com/sahilkarande0918-cmd/Reel-Studio.git
Final application name: Reel Studio. Do not rename the product to something else.
The destination repository was verified to be empty when this instruction was written. Recheck immediately before migration.
The existing local development directory was: `C:\dev\Reel-Studio`. Do not overwrite or delete it.
Create a separate local working directory for the new destination, for example: `C:\dev\Reel-Studio-2` (superseded by Appendix B: `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`).
A2. Inspect source and destination. Before modifying anything:
1. Check authenticated GitHub access. 2. Verify both repository URLs and unique repository identities. 3. Confirm source `main` exists. 4. Fetch the current source HEAD commit. 5. Check available branches and tags. 6. Check Git LFS and submodules. 7. Verify that the destination is still empty. 8. Inspect the existing local worktree for uncommitted changes. 9. Verify Git identity and permissions.
The source's last independently observed main commit was: `a28eacac1a8c60b4c8ddcfdf6be8c2b4dfaec8da`. Do not assume that is still the latest commit.
If the current local project has legitimate uncommitted changes not present in GitHub, preserve them separately and report them. Do not silently discard or overwrite them.
A3. Transfer everything in ONE migration operation. Use a full Git clone/migration, not manual file-by-file copying. Prefer a temporary mirror clone or equivalent full-history transfer.
Transfer: complete tracked source tree; full original Git commit history; all relevant branches; tags; commit attribution and timestamps; Git-tracked assets; existing documentation; original README; frontend; backend; shared packages; Supabase migrations; Python scripts; tests; Hyperframes compositions; existing static public assets; CI/workflow files; configuration templates; Git attributes and ignore rules; any Git LFS objects used by the repository.
Preserve original history and do not squash the existing application into one misleading development commit.
Since the destination is initially empty, transfer all normal branches and tags directly. Avoid pushing internal or protected GitHub refs. Do not force-push over any unexpected destination content.
Do not copy: `.env` secrets into Git; access tokens; passwords; private media not already intended for version control; local virtual environments; `node_modules`; temporary caches; GPU model caches; machine-specific credentials. These belong outside Git and can be reconfigured locally when needed.
If the source history contains exposed secrets or private material, STOP the migration and report the issue rather than replicating the exposure.
A4. Verify exact migration. After transferring, verify: 1. Source and destination main commit SHAs match. 2. Source and destination Git tree SHAs match. 3. Tracked file counts match. 4. Tracked file paths match. 5. Relevant branch refs match. 6. Tags match. 7. LFS objects are accessible where used. 8. No tracked file is missing. 9. No file was accidentally changed by the migration. 10. Original Git history remains intact.
A strong verification is that the source and destination point to the same original commit SHA and tree SHA. Use Git commands and appropriate file/tree comparisons. Do not claim success based only on the GitHub website showing files.
A5. Establish the new local working copy. Clone the NEW repository into `C:\dev\Reel-Studio-2` (superseded: see Appendix B). Verify: `origin = https://github.com/sahilkarande0918-cmd/Reel-Studio.git`. Keep the original source as a read-only reference remote if useful. Do not accidentally push future changes back to `Open_PS04_`. Preserve the existing original local directory. Review runtime configuration needed for development, including Python, Node, Ollama, Blender, Supabase and environment variables. Secrets may be used through secure local configuration but must not be committed.
A6. Transfer completion report. Before writing any new feature code, produce: original repository HEAD; destination repository HEAD; tree SHA comparison; number of transferred tracked files; branch/tag transfer status; LFS/submodule status; any missing items; local working directory; final Git remote configuration; Git working-tree status. Create a migration record only AFTER exact verification. Do not modify product functionality during migration. Once this stage passes, begin development in the new repository only.

STAGE B — FULL PROJECT RESTORATION
Read all relevant existing project instructions. Mandatory order: 1. `AGENTS.md` 2. `docs/IDE_HANDOFF.md` 3. `docs/CHECKPOINT.md` 4. `CLAUDE.md` 5. `docs/ORIGINAL_PS.md` 6. `docs/MASTER_PROMPT.md` 7. `docs/MASTER_PROMPT_SUPABASE_ADDENDUM.md` 8. `docs/ARCHITECTURE.md` 9. `docs/DECISIONS.md` 10. `docs/PHASES.md` 11. `docs/CURRENT_TASK.md` 12. `docs/TEST_STATUS.md` 13. `docs/DEPLOYMENT.md` 14. `docs/ENVIRONMENT.md` 15. `docs/THIRD_PARTY_LICENSES.md` 16. Historical handoff files referenced by the latest checkpoint.
The new requirements in THIS prompt supersede the old product roadmap where they conflict. Keep the original specification and previous documentation as historical reference. Create a separate Reel Studio 2.0 roadmap rather than deleting the original problem statement.
Existing implementation. Preserve the working technology stack: Next.js 16; React; TypeScript; Tailwind CSS; FastAPI; Python; Supabase PostgreSQL/Auth/RLS; durable background workers; Ollama/Qwen vision-language model; faster-whisper; RapidOCR; OpenCV; Kokoro TTS; Hyperframes; FFmpeg/FFprobe; shared canonical timeline schema; existing video editor; brand kits; Instagram OAuth/publishing; Instagram analytics.
The existing Context-Aware AI Editing pipeline is already implemented. Its teaching-step segmentation, educational scoring and self-contained highlight selection must be preserved.
Existing UI. The forest-green and warm-ivory design is FINAL. Preserve: sidebar; navigation; dashboard; project library; typography; cards; design tokens; authentication appearance; existing visual identity. Do not redesign the dashboard. Use the same visual system for new features.

STAGE C — FINAL PRODUCT REQUIREMENTS
We will offer EXACTLY TWO video-creation modes.
MODE A — RECORDING TO REELS. This is the upgraded version of our original recording workflow. Input: Long educational or business recording. Pipeline: Upload → Transcribe → Understand context → Select complete highlights → Smart reframing → Captions → Motion effects → Edit → Render → Instagram.
Preserve: Hinglish transcription; technical-term correction; code OCR; educational completeness scoring; coherent 30–60 second highlights; smart 9:16 cropping; advanced timeline editing; brand kits; Instagram integration.
Add: optional uploaded music; automatic beat synchronization; professional motion effects; caption ON/OFF; 100 caption styles; saved voice profiles; AI clip collections; campaign generation; improved exports; advanced quality inspection.
MODE B — PROMPT-TO-PROFESSIONAL-EDIT. This completely replaces the old Topic-to-Video user workflow. Old JSON/XML topic-video generation must no longer appear as Mode B. Remove its unnecessary entry points carefully while preserving historical projects and shared internal utilities where still needed.
New Mode B: Upload raw footage → Add optional audio/reference Reel → Describe desired edit → AI creative planning → Effects/motion design → Render → Edit/Export → Instagram.
Inputs: multiple video clips; images; screenshots; optional audio; optional reference Reel; natural-language prompt; desired duration; target aspect ratio; brand kit; caption style; optional voice profile/narration.
The application must work even with very short instructions. Example: "Make a professional phonk edit." The system should infer sensible rhythm, pacing, subject framing, effects and overall editing structure. Another example: "Make this into a professional tech advertisement with floating website mockups, kinetic typography, cinematic transitions, smooth animations and music synchronization." The platform must generate actual motion-designed scenes, not static images connected by simple fades.

PHASE 1 — REFERENCE VIDEO AND OPEN-SOURCE SKILL RESEARCH
Analyze all supplied video examples: 1. `reel template.mp4` 2. `reel template 2.mp4` 3. `reel template 3.mp4` 4. `reel template 4.mp4` 5. `reel template 6.mp4` 6. `VenomsTechAI_Claude_Video_Editor_Guide.pdf`. If any asset is unavailable, report it accurately. Create detailed scene breakdowns and technical observations.
Reference 1 — Before/After Showcase. Study: split-screen comparisons; Before/After labels; source/reveal layouts; camera movement; transformations; product presentation; perspective changes; smooth transitions.
Reference 2 — Animated Infographic. Study: grid backgrounds; vertical embedded video cards; numbered lists; moving layouts; animated typography; mask transitions; card composition; visual storytelling.
Reference 3 — Motion Graphics. Study: kinetic typography; animated UI elements; floating cards; chat bubbles; counters; calendar graphics; gradient transitions; easing; morph-like layout changes.
Reference 4 — Phonk Product Montage. Study: rapid cuts; product emphasis; velocity ramps; whip transitions; motion blur; impact zooms; camera reframing; beat-sensitive editing; repeated footage treatment.
Reference 6 — Premium Motion-Designed Advertisement. Study: blur-to-sharp text reveals; animated documents; floating websites; browser/laptop compositions; portfolio grids; masked typography; layered motion; perspective movement; glowing arcs; light sweeps; brand reveals; animated social interfaces; pricing graphics; CTA animation.
The system must learn transferable editing principles rather than copy the creators' identities, branding or protected media.
Free editing skills — mandatory investigation. Investigate and evaluate:
- Herk Edit Kit https://github.com/nateherkai/herk-edit-kit — agent-oriented short-form editing techniques, transcript editing, motion cards, Hyperframes references and validation tools.
- Video Director Skill https://github.com/DotanVG/video-director-skill — creative direction, storyboarding, musical pacing and camera choreography.
- AIvideokit https://github.com/rockwithsystems/AIvideokit — practical implementations of beat alignment, speed ramps, cutaway effects, flash cuts, motion effects, music ducking, audio processing, Hyperframes-based editing.
- free247editor https://github.com/riecodes/free247editor — natural-language revisions, editing workflows and style memory.
- Vertical Video Editing Skill https://github.com/adriiita/vertical-video-editing-skill — vertical layouts, B-roll, captions and motion.
- Claude Motion Graphics https://github.com/wergle3232/claude-motion-graphics — branded motion graphics and Hyperframes compositions.
Do not blindly install everything. Inspect dependencies, licenses, existing tests and practical compatibility. Most importantly, agent skills are NOT automatically a video-editing runtime. Convert relevant techniques into safe reusable application components and declarative editing templates. No copying of paid proprietary skill packages.
Phase deliverables: `docs/REFERENCE_STYLE_ANALYSIS.md`; `docs/OPEN_SOURCE_TOOL_AUDIT.md`; initial editing architecture; real test fixtures; verified library selection. Commit and push.

PHASE 2 — UNRESTRICTED-COUNT CLIP INGESTION
Users should be able to upload as many clips as practical without an arbitrary low clip-count limit. Implement: multi-file upload; chunked/resumable uploads; background processing; durable queues; per-asset metadata; media previews; proxy files; caching; duplicate identification; automatic cleanup; project persistence; retry and cancellation. Use transparent storage, compute and upload-size limits rather than claiming infinite resources.
Analyze each clip with: FFprobe; OpenCV; PySceneDetect; optical flow; existing vision-language model; MediaPipe where useful. Extract: duration; FPS; resolution; orientation; scene changes; visual subjects; product/object regions; approximate camera movement; lighting; composition; color; motion intensity; strong reusable moments; audio characteristics. Use a bounded-memory architecture suitable for our local GPU.
Intelligent clip reuse. If only two clips are supplied for a longer video, the AI should creatively reuse those clips. Possible techniques: different in/out ranges; punch zoom; reframing; motion effects; speed ramps; reversal when appropriate; freeze frames; detail crops; split screen; alternate layouts; Before/After composition; motion-matched reuse. Avoid obvious looping. Never pretend unavailable footage or viewpoints exist.
Acceptance: test media ingestion with 1, 2, 10 and 30+ clips. Verify persistence and background processing. Commit and push.

PHASE 3 — ADVANCED REFERENCE REEL ANALYZER
Build a reusable Reference Style Analyzer. Input: any user-uploaded reference video. Output: a structured style profile. Extract: shot boundaries; pacing; cut density; transition categories; camera movement cues; zoom characteristics; speed changes; typography; text positions; color palette; visual layout; motion intensity; graphic effects; music energy; approximate music-to-cut relationships. Use: PySceneDetect; OpenCV; optical flow; local VLM; FFprobe; audio analysis. Store: shot timeline; transition timeline; motion profile; typography profile; color profile; pacing curve; beat profile; layout profile; confidence/evidence; recommended transferable techniques. Create a visual analysis report.
Acceptance: analyze all five supplied reference videos and generate accurate, time-coded reports. Commit and push.

PHASE 4 — MUSIC, PHONK AND BEAT SYNCHRONIZATION
Use: https://github.com/librosa/librosa. Analyze uploaded soundtracks. Support: BPM estimation; onset detection; beat grids; strong rhythmic accents; musical phrase detection where feasible; drops/buildups where detectable; energy curves; manual beat correction; downbeat alignment; transition timing; frame-grid snapping.
The AI must synchronize: cuts; flashes; motion peaks; zooms; camera shakes; speed ramps; graphic entrances; typography reveals; scene changes. Do not apply every effect on every beat.
Create pacing profiles: Cinematic; Phonk/Velocity; Energetic; Clean Commercial; Minimal; Educational; Product Showcase; Motion Graphics; Tech Advertisement.
Phonk-specific editing. Support: velocity transitions; bass impact; controlled camera shake; zoom punches; blur; RGB split; flash; beat cuts; speed changes; freeze/release; glitch accents; dramatic product reveals. Measure cut-to-beat timing and report offsets. Preserve sound quality.
Acceptance: produce a real beat-synchronized 15–20 second Reel. Commit and push.

PHASE 5 — COMPLETE PROFESSIONAL EFFECTS ENGINE
Build an extensive CapCut-style effects system using lawful, original or appropriately licensed equivalents. We are not importing CapCut's proprietary library. Create a typed effects registry. Each effect must declare: unique ID; category; description; parameters; intensity; duration; keyframes; renderer; hardware needs; supported formats; preview implementation; validation rules.
Category A — Camera motion: push in; pull out; punch zoom; crash zoom; zoom bounce; pan; tilt; rotation; whip pan; wobble; handheld shake; impact shake; perspective tilt; orbit-like motion; drift; subject tracking; simulated camera push; eased crop movement.
Category B — Blur: Gaussian blur; motion blur; directional blur; zoom blur; radial blur; focus blur; background blur; selective blur; masked blur; blur reveal; blur transition.
Category C — Impact: white flash; black flash; flash shake; brightness pulse; bass impact; short freeze; wobble impact; glitch; RGB split; chromatic aberration; controlled strobe; high-contrast snap. Include photosensitivity-aware limits for flashing effects.
Category D — Transitions: hard cut; crossfade; dip to black; dip to white; swipe; whip; zoom-through; cross-zoom; spin; rotate; luma wipe; directional wipe; mask reveal; match cut; motion-matched cut; blur transition; flash transition; glitch transition; perspective transition; foreground wipe; split-screen transition.
Category E — Velocity: slow-fast-slow; fast-slow-fast; smooth slow motion; frame-interpolated slow motion; fast-forward; reverse; freeze/release; beat-controlled speed ramps; smooth motion easing.
Category F — Light and color: glow; bloom; light leaks; light sweeps; lens-flare approximation; warm/cool grading; contrast; exposure; vignette; film grain; VHS; RGB aberration; color pulse; color matching.
Category G — Advanced composites: subject cutout; text behind the subject; product highlight glow; tracking overlays; split screens; Before/After comparisons; video cards; picture-in-picture; luma masking; depth parallax; foreground/background separation; animated cutaways.
Additional tool research. Evaluate: https://github.com/gl-transitions/gl-transitions ; https://github.com/dyne/frei0r ; https://github.com/NatronGitHub/natron-plugins ; https://github.com/hzwer/Practical-RIFE ; https://github.com/facebookresearch/sam2 ; https://github.com/DepthAnything/Depth-Anything-V2 ; https://github.com/google-ai-edge/mediapipe . Verify code and model licenses independently. Implement only compatible, genuinely useful tools. Every registered effect must produce real output. If the user requests an unsupported effect, the AI should select a compatible substitute and explain the change.
Acceptance: render representative tests from every effect category. Verify effect visibility and preview/export parity. Commit and push.

PHASE 6 — PROFESSIONAL MOTION DESIGN ENGINE
Reuse Hyperframes and GSAP. This phase must support effects seen in the premium Claude-edited advertisement.
Animated typography: word-by-word reveals; character staggers; blur-to-sharp; masked typography; kinetic typography; typographic tracking motion; scale changes; position changes; glow typography; outline effects; cinematic serif headings; animated underlines; word emphasis; number counters; typewriter effects.
Graphic compositions: floating cards; animated lists; website mockups; phone mockups; laptop screens; browser interfaces; grid galleries; animated UI elements; chat bubbles; pricing cards; calendars; charts; timelines; animated buttons; comparison layouts; picture-in-picture; split screens; infographic scenes.
Motion: spring easing; elastic movement; staggered entrances; smooth camera pushes; perspective movement; morph-like scene transitions; mask reveals; shape animation; layer movement; light sweeps; motion blur; coordinated exits.
Reusable skill library. Study Herk Edit Kit's motion-card architecture. Build a native library of original, validated, reusable scene templates. Templates must have editable: text; colors; fonts; timing; assets; layout parameters; motion intensity; transition rules. The AI Director should select templates according to the video context. Do not choose random motion templates simply to make a video look busy.
Acceptance: render an original 15–30 second motion-designed advertisement inspired by Reference 6's technical editing approach. It must include real animated typography, UI cards, scene transformations and sound design. Commit and push.

PHASE 7 — AI EDITING DIRECTOR
This is the main intelligence layer. The AI Director receives: 1. user editing prompt 2. media analysis 3. reference-video analysis 4. music beat analysis 5. brand identity 6. existing effects 7. motion templates 8. render capabilities 9. output settings. It should generate a coherent creative treatment and a validated executable editing plan.
Required planning intelligence. Understand: main visual subject; creative intent; video storyline; pacing; shot priority; product focus; best opening; best closing; available source angles; transition compatibility; beat importance; motion intensity; color consistency; typography requirements; visual repetition; brand requirements.
The director must decide: which clip to use; how long to show it; which source range to select; where cuts should land; where a transition is beneficial; which effect actually suits a particular moment; which camera motion is visually valid; when to introduce text; when to use motion graphics; when to use footage reuse; when to choose Blender; when not to use Blender.
Prompt examples: "Make a cinematic Reel." Choose restrained movement, smooth transitions, considered pacing and consistent grading. "Make an aggressive phonk edit." Choose velocity ramps, impact zooms, flashes, motion blur and energetic shot selection synchronized to the soundtrack. "Create a premium SaaS advertisement." Choose animated website mockups, editorial typography, floating cards, visual storytelling and professional sound design. "Make it like my uploaded reference." Transfer the general editing structure, rhythm and stylistic treatment to the user's own media. "Edit it professionally." Make reasonable creative decisions based on the footage and soundtrack.
LLM usage. Use the existing local Ollama/Qwen model as the default planning engine. Allow an optional external LLM API key for stronger creative planning. External API use must not be required for normal rendering. Do not call an LLM on every frame. Use structured output and schema validation.
Canonical timeline. Extend the existing shared timeline schema instead of creating competing timeline formats. The edit plan must include: asset IDs; clip source ranges; timeline positions; beat anchors; effects; effect keyframes; motion curves; renderer selection; transition timing; captions; graphics; sound effects; music automation; voice track; brand settings; output format; reuse metadata. The same plan must drive preview and export. Provide a storyboard with exact timings, still previews and animation explanations.
Acceptance: use the same uploaded clips with different creative prompts. Verify distinct, appropriate rendered outcomes. Commit and push.

PHASE 8 — INTELLIGENT RENDERER ROUTER
Select the simplest renderer capable of producing each effect.
FFmpeg/OpenCV: use for cutting; scaling; cropping; audio processing; basic transforms; speed adjustments; standard color operations; conventional effects; final encoding.
Hyperframes: use for advanced typography; UI animations; graphic compositions; animated cards; 2D motion; captions; masks; transitions; designed scenes.
GPU shader renderer: use compatible shader effects for distortion; blur; zoom; RGB aberration; GPU transitions; light effects; perspective movement.
Blender: use when genuine 3D work is required. Repository: https://github.com/ahujasid/mcp-for-blender . Configure Blender MCP for Claude Code development and scene inspection. Use Blender for: 3D models; real 3D camera paths; 3D typography; advanced lighting; authored product scenes; complex 3D composition; depth-dependent effects requiring genuine 3D geometry. Do not launch Blender for ordinary flashes, blur, wobble, zoom or basic transitions. For application jobs, create a safe headless Blender worker accepting validated scene templates. Never expose arbitrary Blender Python execution to users.
Quality requirements. All renderers must use the same timeline/frame clock. Outputs must not contain: one-frame flashes; missing overlays; timing drift; black gaps; misaligned captions; incorrect transitions; unintended stretching.
Acceptance: verify a mixed-renderer video using footage, Hyperframes animations and optional Blender content. Commit and push.

PHASE 9 — REUSABLE VOICE CLONING
Implement user-owned voice profiles. Evaluate: https://github.com/resemble-ai/chatterbox ; https://github.com/myshell-ai/OpenVoice . Preferred starting point: Chatterbox Multilingual, subject to actual voice-quality evaluation.
User workflow: 1. Record or upload their voice sample once. 2. Confirm ownership/authorization. 3. Create a saved voice profile. 4. Preview the voice. 5. Select it for future projects. 6. Generate narration using that profile.
Requirements: clear sample-quality validation; secure profile storage; persistent voice selection; consistent speaker characteristics; English/Hindi support; tested Hinglish code-switching; pronunciation correction; natural timing; audio preview; profile deletion; workspace isolation; synthetic speech identification where supported. Aim for high, stable similarity; do not promise acoustically perfect identity. Test multiple scripts against the same voice profile. Do not clone third-party voices without verified permission.
Acceptance: generate at least two distinct narrations using the same authorized voice. Commit and push.

PHASE 10 — 100 PROFESSIONAL CAPTION STYLES
Provide: Captions: ON / OFF. When OFF: no burned-in captions; preserve transcript data. When ON: show a gallery of 100 selectable caption presets; provide animation previews; support font/color changes; apply the chosen style to the real MP4.
Implement style families including: Minimal; Creator; Cinematic; Learning; Brand; Karaoke; Kinetic; Glow; Neon; Outline; Bold; Retro; Editorial; Typewriter; Gaming; Phonk; Pop; Bounce; Documentary; Product Showcase; Modern; Handwritten; Animated Headline. Develop 100 meaningfully distinct preset definitions, not 100 simple color swaps.
Preserve: word-level timestamps; readability; safe zones; technical terminology; preview/export consistency; font licensing. Use existing Hyperframes/caption infrastructure.
Acceptance: validate all 100 definitions and visually inspect representative renders for each distinct animation family. Commit and push.

PHASE 11 — AI CLIP COLLECTIONS
Upgrade Mode A to generate related educational video series. Example: one Python lecture may produce: Functions Explained; Understanding Recursion; Practical Example; Common Mistakes; Summary. These titles must be supported by the actual recording.
Capabilities: topic clustering; ordered clips; collection descriptions; accurate AI-generated titles; timestamp evidence; manual reordering; individual video editing; batch rendering; brand consistency; collection persistence; optional Instagram scheduling. Never invent topics absent from the lecture.
Acceptance: generate and edit a real multi-clip educational collection. Commit and push.

PHASE 12 — AI BUSINESS CAMPAIGN AGENT
Implement the three business-focused features.
A. AI Campaign Generation. Inputs: business identity; industry; audience; goals; offer; brand assets; raw footage. Output: campaign concept; Reel ideas; scripts; recommended clip selection; hooks; captions; calls to action; posting plan; related clip collections. Connect the campaign directly to Mode A or Mode B editing.
B. Localized Content Intelligence. Support: English; Hindi; Hinglish. Investigate Marathi, enabling it only after adequate model testing. Respect brand names, technical terms and code identifiers.
C. Business Results Tracking. Support measurable: Instagram analytics; campaign IDs; UTM links; click tracking; WhatsApp inquiry CTAs; recorded inquiries; engagement changes; grounded AI improvement suggestions. Do not invent leads, revenue or conversion values.
Acceptance: demonstrate a local-business content campaign based on real sample inputs. Commit and push.

PHASE 13 — INSTAGRAM AUTOMATION
Preserve all existing working Instagram integration. Workflow: Create → Edit → Render → Review → Approve → Schedule/Publish → Analytics. Preserve: OAuth; account identity; access-token protection; upload/publishing queue; duplicate prevention; retry handling; Instagram media verification; analytics refresh. Extend: campaign-aware scheduling; caption suggestions; cover selection; post tracking; status visibility. No real Instagram post without explicit user approval of the exact account, video and caption. YouTube remains postponed. Commit and push.

PHASE 14 — PROFESSIONAL VIDEO QUALITY ENGINE
This is mandatory. Implement automatic checks using the actual rendered file. Verify: duration; resolution; FPS; codec; playback validity; missing frames; black frames; unexpected freezes; caption placement; text clipping; audio loudness; A/V synchronization; beat alignment; transition-boundary continuity; motion jitter; source-clip duplication; missing effects; unexpected silence; distortion; final output integrity.
Use techniques from the uploaded VenomsTechAI guide where appropriate: word alignment; shared edit decision list; storyboard snapshots; beat-aware timing; separate audio/picture processing where helpful; render contact sheets; loudness measurement; platform-safe zones; rechecking speech around cuts; effect timing checks. Measure objective quality instead of inventing subjective scores. Automatically repair safe, deterministic defects when possible. Record unfixable issues honestly.
Hardware optimization. Our local machine includes an NVIDIA RTX 5050 with 8 GB VRAM. Use: staged processing; GPU-memory monitoring; proxy rendering; model unloading; asset caching; partial re-renders; resource-aware queues; CPU fallbacks. Do not load all heavy models simultaneously.

PHASE 15 — REAL END-TO-END VALIDATION
Every major workflow must produce actual playable video files.
TEST A — Phonk Shoe-Store Reel. Inputs: several raw product clips; licensed phonk-style music; Reference 4; user prompt. Expected: beat-synchronized cuts; impact zooms; velocity transitions; motion blur; flash/shake effects; strong product framing; coherent ending.
TEST B — Animated Infographic. Use Reference 2's editing language. Expected: animated text; lists; embedded video cards; clean layout; appropriate transitions.
TEST C — Motion Graphics. Use Reference 3's editing language. Expected: chat bubbles; animated cards; kinetic typography; UI counters; smooth scene transformations.
TEST D — Premium Advertisement. Use Reference 6 as editing inspiration. Expected: editorial text animation; floating website cards; browser/laptop mockups; branded motion; light sweeps; cinematic reveal; sound design; professional CTA. Do not copy the reference creator's exact assets or branding.
TEST E — Before/After. Use Reference 1 as style inspiration. Expected: comparison layout; visually coherent source/reveal sequence; camera transforms; real transition effects.
TEST F — Minimal Footage. Upload only two clips. Generate a 15-second edit with music and a short prompt. Verify meaningful clip reuse without obvious looping.
TEST G — Mode A Regression. Ensure: long recording upload works; transcription works; context-aware highlights work; smart cropping works; caption styles work; editing works; MP4 export works.
TEST H — Business Workflow. Generate a campaign from actual business information. Demonstrate one real exported Reel, accompanying caption, posting plan and trackable CTA. Do not publish without approval.

GLOBAL PRODUCT RULES
Design: preserve the existing approved dashboard and brand identity. No UI redesign. New components must use current design tokens.
Cost: no mandatory paid services. An external LLM API key may be optional for planning. Local editing and rendering must remain functional without paid API access.
Licensing: verify every third-party dependency and model license. Maintain `docs/THIRD_PARTY_LICENSES.md`. Do not copy proprietary CapCut effects or commercial paid skill files.
Security: preserve Supabase RLS; auth boundaries; workspace permissions; backend JWT validation; encrypted tokens; secure voice profiles; media privacy; worker isolation. Use only the authorized Reel Studio Supabase project. Do not accidentally connect to separate projects owned by the developer.
Deployment: preserve existing functioning Vercel and local-backend deployments. Changing the Git remote must not silently deploy experimental changes to production. Check repository linkage, environment configuration and production targets before deployment.
Git discipline: after successful full repository migration, implement new features in genuine phases. For each: 1. write actual code 2. test it 3. render genuine results 4. fix defects 5. update documentation 6. commit meaningful changes 7. push safely 8. record the SHA. Preserve genuine authorship. Never create artificial history, backdate commits, impersonate teammates or falsely represent migrated code as new development. Do not force-push unrelated work.
Documentation: keep these current: `docs/CHECKPOINT.md`; `docs/IDE_HANDOFF.md`; `docs/CURRENT_TASK.md`; `docs/PHASES.md`; `docs/ARCHITECTURE.md`; `docs/TEST_STATUS.md`; `docs/DEPLOYMENT.md`; `docs/THIRD_PARTY_LICENSES.md`; `docs/REFERENCE_STYLE_ANALYSIS.md`; `docs/OPEN_SOURCE_TOOL_AUDIT.md`. If context becomes limited, write a complete checkpoint before compaction.

EXECUTION PRIORITIES. Follow the sequence strictly.
FIRST — complete repository migration (clone and transfer the complete original repository to https://github.com/sahilkarande0918-cmd/Reel-Studio.git; verify the migrated Git tree and commit history match exactly).
SECOND — prepare the Reel Studio 2.0 architecture (read all project files and inspect the supplied references and public tools).
THIRD — build the core Mode B pipeline. Prioritize: 1. media ingestion 2. reference-video understanding 3. music/beat analysis 4. CapCut-style effects 5. Hyperframes motion graphics 6. AI Director 7. intelligent rendering router 8. real MP4 output 9. quality verification.
FOURTH — build shared advanced features: voice cloning; 100 caption styles; clip collections; business campaign generation; localized content; campaign tracking; Instagram enhancements.
FIFTH — final testing: verify full production workflows and prepare a genuinely working demonstration.
FINAL DIRECTIVE: DO THE ENTIRE REPOSITORY TRANSFER FIRST, IN ONE VERIFIED MIGRATION. DO NOT ALTER THE ORIGINAL APPLICATION WHILE COPYING IT. Then build Reel Studio 2.0 from the migrated project. The final product must support professional prompt-driven video editing with intelligent effects, motion graphics, music synchronization, optional voice cloning, creative scene planning and automatic publishing workflows. A static slideshow, decorative UI or unverified feature implementation is not acceptable. Do not stop at designing the architecture. Build, test, render, verify, commit and push real functionality. Prioritize the best possible working editing engine over superficial feature counts. START NOW WITH STAGE A: REPOSITORY MIGRATION.

## Appendix B — Working directory and Git authorship addendum (verbatim)
**IMPORTANT — Working Directory & Git Authorship**
Work ONLY in this new folder: `C:\Users\Sahil\OneDrive\Desktop\Reel Studio 2.0`
Clone the new GitHub repository into this exact folder. Do not create another nested project folder or modify the original repository.
**Git commits must use my existing Git identity only (`sahilkarande0918-cmd`).** Never add Claude, Anthropic, Codex, AI agents or bots as authors, co-authors or contributors. Do not include `Co-Authored-By` trailers or AI attribution in commits.
After migration, continue all development, testing, commits and pushes from this new folder. Preserve the original Git history and commit genuine new changes phase by phase.
("ask credential if required")

## Appendix C — Later owner instructions in this session
- "remove the previous contributors, only keep me" → done by deleting the two other people's one-line placeholder
  commits from the NEW repo's history (not re-attributing their work); one force-push to the new repo only.
- Supplied 17 test clips + `phonk audio.mpeg`: "take reference reel as template 4" → phonk reel built in Reference 4 style.
- Owner asked whether Blender, campaign agent, localization, results tracking etc. are done → answered: not implemented
  yet; proposed order: Mode B screen + AI Director → motion graphics + captions → campaigns/localisation/tracking →
  voice → Blender. Owner has not yet chosen the order.
- Pre-compaction checkpoint requested (this file, the handoff, doc sync); no new development during the checkpoint.
