# Open-source tool audit — Reel Studio 2.0 (2026-10-23)

Every entry was checked against its GitHub repository (licence file or SPDX id, last push, contents). "Use" means it
becomes part of the product; "study" means we learn the technique and write our own code; "skip" says why.
Agent skills are prompts and scripts for a coding agent, **not** a video-editing runtime: what we take from them is
re-implemented as typed, tested application code and declarative templates.

## Already installed and used (no new dependency)
| Tool | Licence | Role in 2.0 |
|---|---|---|
| FFmpeg 8.1.2 full build (gyan.dev) | GPL-3 build, invoked as a binary | Cut/scale/crop, `setpts`/`rubberband` speed, `minterpolate` slow motion, `xfade` (61 transitions incl. zoomin, radial, hblur, pixelize, slides, wipes), `gblur`/`dblur`, `rgbashift`/`chromashift`, `vignette`, `noise` grain, `curves`/`lut3d` grading, `perspective`, `zoompan`, `loudnorm`/`ebur128` loudness, `sidechaincompress` ducking, final encode |
| Hyperframes 0.8.164 (+ GSAP) | Apache-2.0 (GSAP standard licence) | Typography, UI cards, mockups, masks, captions, designed scenes, composition of the base picture with graphics |
| OpenCV 5.0, PySceneDetect 0.6.7 | Apache-2.0 / BSD-3 | Shot detection, optical flow (motion, zoom, pan), flashes, palette, crops |
| RapidOCR (ONNX) | Apache-2.0 | On-screen text positions in references and footage |
| faster-whisper (Hinglish CT2 model) | MIT | Word timings for captions, cuts on speech |
| Ollama `qwen2.5vl:7b` | Qwen licence (commercial use allowed under 100M MAU) | Edit planning (structured JSON), key-frame descriptions |
| Kokoro (via `hyperframes tts`) | Apache-2.0 | Default narration voice |

## Added in this phase
| Tool | Licence | Decision |
|---|---|---|
| librosa 0.11.0 (`librosa/librosa`, ★8.7k, active) | ISC | **Use.** Tempo, beat grid, onsets, accents, energy, drops (`app/services/music/beats.py`) |

## Editing skills and kits (study → re-implement)
| Repository | Licence | What we take | Decision |
|---|---|---|---|
| nateherkai/herk-edit-kit (★2.0k) | MIT for kit material; `THIRD_PARTY_NOTICES.md` keeps third-party rights (example media, brand-named styles, fonts) | Motion laws (one idea per beat ≈ 1.5 s, camera never static, motion blur rides transitions, timelines must fill their slot or Hyperframes shows a black frame), word-anchored beat validation (−0.2…+1.8 s lead window), card/blueprint registry idea | **Study + re-implement** as our own template registry and validators. Do not copy brand-named styles (Vox/Kallaway/Infinite) or example media |
| DotanVG/video-director-skill | MIT | Director interview → hook, arc, beat-by-beat timing table; scenes locked to bar lines; A/B/C music versions; held "money shot"; hard cut to black before the payoff | **Study.** Feeds the AI Director's plan schema and pacing rules |
| rockwithsystems/AIvideokit | MIT (53 KB, no tests) | Downbeat-on-hard-cut trim, multi-stage eased speed ramp plan (`speed@duration` plateaus), punch-ins/shake/flash/zoom-through/whip/swipe cutaways driven by one `edit.json` | **Study + re-implement** in our effects engine. Its optional paid services (Gemini, ElevenLabs) are not used |
| riecodes/free247editor | MIT | Natural-language revision loop, persistent per-user style memory file | **Study** for revisions and saved style |
| adriiita/vertical-video-editing-skill | MIT | Anti-jitter camera contract (animate a wrapper, `force3D`, GPU layers), editorial layouts (serif/sans, seam captions, stacked splits), `init → preview → lint → render → verify` loop, edit report per render | **Study + re-implement** |
| wergle3232/claude-motion-graphics | **No licence** (all rights reserved) | Ideas only | **Study only; no code copied** |
| VenomsTechAI Claude Video Editor Guide (PDF, owner-supplied) | Free guide | Storyboard gate; one plan file for all times; picture and sound rendered separately then muxed (avoids drift); −14 LUFS / −1.5 dBTP; safe zone x 90–930, y 200–1560; cuts on the frame grid in pauses; whoosh peak ≥ 0.15 s before the next word; SFX ≤ +3 dB over voice, ducked ~6 dB under speech; contact sheets and frames either side of every cut for QA | **Adopt as QA rules** (Phase 14) |

## Effects, interpolation, segmentation, depth
| Repository | Licence | Decision |
|---|---|---|
| gl-transitions/gl-transitions (125 shaders) | MIT collection; **each shader declares its own licence** (spot-checked CrossZoom, Directional, directionalwarp, GlitchMemories, ZoomInCircles: MIT) | **Use selectively** inside Hyperframes (WebGL canvas) for shader transitions; vendor only shaders whose header says MIT, record each in `THIRD_PARTY_LICENSES.md` |
| dyne/frei0r | GPL-2.0, native plugins (Windows needs separate binaries) | **Skip.** FFmpeg built-ins cover glow/blur/grain/colour; avoids shipping GPL plugins |
| NatronGitHub/natron-plugins | Mixed per plugin, last push 2022-11 | **Skip.** Unmaintained, licence varies per node, needs Natron |
| hzwer/Practical-RIFE | MIT | **Later, optional** GPU frame interpolation for smooth slow motion; FFmpeg `minterpolate` is the dependency-free default |
| facebookresearch/sam2 | Apache-2.0 (code and weights) | **Later, optional** precise masks (tiny/small model fits 8 GB) for cutouts and tracking |
| DepthAnything/Depth-Anything-V2 | Code Apache-2.0; **only the Small model is Apache-2.0**, Base/Large/Giant are CC-BY-NC-4.0 | **Small only**, if depth parallax is built |
| google-ai-edge/mediapipe | Apache-2.0 | **Use first** for subject masks (selfie/multiclass segmentation) and face boxes on CPU: text behind subject, subject-aware crops |

## 3D and voice
| Repository | Licence | Decision |
|---|---|---|
| ahujasid/mcp-for-blender (★32k) | MIT (Blender itself GPL, free) | **Developer tool only** (scene authoring/inspection through MCP). The app uses a separate headless Blender worker that accepts validated templates; users never run Blender Python. Blender is not installed yet (Phase 8) |
| resemble-ai/chatterbox | MIT; output carries an imperceptible PerTh watermark | **Preferred** for user-owned voice profiles (multilingual model includes Hindi); evaluate quality in Phase 9 |
| myshell-ai/OpenVoice (V2) | MIT | **Fallback.** Tone-colour cloning on top of a base TTS; no native Hindi base speaker |

## Hardware note
RTX 5050 Laptop, 8 GB VRAM. One heavy model at a time (Whisper, Ollama VLM, Chatterbox, SAM2 never co-resident); unload
between stages as the analyze worker already does.
