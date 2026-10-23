# Reference style analysis (2026-10-23)

Inputs: the owner's reference reels in `Downloads` — `reel template.mp4` (Ref 1), `reel template 2.mp4` (Ref 2),
`reel template 3.mp4` (Ref 3), `reel template 4.mp4` (Ref 4), `reel template 6.mp4` (Ref 6) and an extra
`reel template 5.mp4` (Ref 5, not named in the prompt but supplied) — plus `VenomsTechAI_Claude_Video_Editor_Guide.pdf`.
All were available.

**Method.** Every number below was measured by `app/services/reference/analyzer.py` (PySceneDetect shots, OpenCV
optical flow, luma-spike flashes, k-means palettes, RapidOCR text, librosa beats; tool:
`tests/analyze_references.py`). Time-coded scene notes come from 2 fps contact sheets read frame by frame. Local
VLM (`qwen2.5vl:7b`) key-frame descriptions were also collected; they are good at layout ("split-screen BEFORE/AFTER",
"speech bubbles", "laptop on a dark background") but invent details (it described Ref 4's shelves as "sneakers on
skateboards"), so they are treated as model text, never as measurements. Raw profiles + contact sheets:
`%LOCALAPPDATA%\reel-studio\data\reference-analysis\` (not in git: third-party media).

**Use.** We learn transferable technique. No reference footage, audio, logos, handles, product names or text is ever
reused in an output.

## Measured summary
| Ref | Format | Length | Shots (detected) | Median shot | Flashes | Music BPM | Cuts within 60 ms of a beat | Character |
|---|---|---|---|---|---|---|---|---|
| 1 Before/After | 720×1280 | 37.8 s | 7 (card-internal cuts not separable from the static frame) | 5.6 s | 0 | 99.4 | 33 % | Fixed split layout, cuts inside the AFTER card |
| 2 Infographic | 720×1280 | 61.1 s | 1 (static frame, content changes inside a card) | — | 0 | 123 (drops 4, 26, 36 s) | — | Template layout + numbered list + video card |
| 3 Motion graphics | 720×720 | 33.7 s | 13 | 2.1 s | 9 | 123–136 | 17 % | Voice-led kinetic UI scenes |
| 4 Phonk montage | 478×850 | 14.0 s | 10 | **0.87 s** | 7 (6 black, 1 white) | **143.6** (drop 3.5 s) | **89 %, median offset 28 ms** | Beat-locked product montage |
| 5 (extra) Product UI ad | 1276×718 | 27.1 s | 9 | 2.5 s | 5 | 123 (drops 8.5, 16.5 s) | 38 % | Landscape designed scenes |
| 6 Premium ad | 720×1280 | 57.8 s | 5 (screen content changes inside a filmed laptop) | 11.1 s (outer shots) | 0 | 103.4 (drop 25 s) | 25 % | Designed ad played on a filmed laptop |

Analyzer limitation found here: when the frame is a fixed layout (Ref 1, 2) or a filmed screen (Ref 6), cuts happen
inside a sub-region and full-frame shot detection under-counts them. Next step: region-of-interest shot detection
(detect the dominant card/screen rectangle, then run the detector inside it).

## Ref 1 — Before/After showcase
- **Layout (whole video):** light-grey radial gradient ground; left card "BEFORE" (smaller, ~40 % width, sits lower),
  right card "AFTER" (larger, ~55 % width); condensed bold italic labels above each card (BEFORE black, AFTER magenta).
  Cards have no frame, slight drop shadow.
- **Content:** BEFORE plays flat, static phone footage of the same place; AFTER plays the professionally shot version.
- **Time-coded:** 0–6.9 s storefront: drone push-in with a cyan light sweep · 7.0–8.0 s light-painting swirl reveals a
  logo · 9–12 s interior pans · 19.5 s circular mask reveal (spotlight vignette) · 21–24 s logo with an orbiting light
  ring · 27–30 s product shots with glow · 30.5–31 s fast push down an aisle with motion blur · 33–37.8 s storefront at
  night, warm lights.
- **Pacing:** AFTER-card cuts every ~1–2.5 s while the BEFORE card changes only per section; hard cuts; no flashes.
- **Transferable:** persistent comparison layout as a Hyperframes template; same-subject pairing (before range ↔
  after range); light sweeps and orbit rings as overlays; mask reveals; push-ins on the AFTER side only.

## Ref 2 — Animated infographic
- **Layout:** white ground with a soft green→blue gradient blob (top-right, breathing); headline locked at the top
  ("Sounds trending / *in October*" — black bold sans + italic accent on a highlight), small "(with examples)"
  subtitle; numbered list 1–10 on the left; a rounded vertical video card on the right with a dark label pill under it.
- **Time-coded:** 0–4 s intro, list empty, blob only · 4.0 s (first music drop) the card appears and item 1 writes in ·
  then one item every ~5–6 s: the item text writes in, the card swaps to that example clip and the pill updates ·
  26 s and 36 s drops align with new items.
- **Transferable:** "list + embedded clip" template; items revealed on phrase boundaries; card swap with a short
  mask/scale; constant ambient motion (blob) so the static layout never feels frozen.

## Ref 3 — Motion graphics (voice-led)
- **Time-coded:** 0–2 s word-by-word "Hey I'm a motion designer" with emoji stickers popping in around the line ·
  2–3.5 s blue gradient, sparkles, name blurs in · 4–5 s app icons burst into a grid · 5.5–7 s price slider card
  ("−1000 $ +") with glow · 7.3 s white flash · 7.5–9 s dark gold ground, typewriter line with caret · 9–9.5 s pixel
  dissolve · 9.5–13.5 s AI-chat input bar types a sentence, dropdown opens · 13.5–14.5 s segmented pill toggles ·
  15–18 s blue chat bubbles stack · 18.5–21.5 s "I'll be posting on" + social-icon carousel with cursor clicks ·
  21.5–22.5 s kinetic "I'll keep making" · 23–26 s single words slam full-frame ("land", "my", "client") then a dot
  morph · 26.5–29 s calendar grid, selection highlight slides across dates · 29.5–32 s word reveal on black ·
  32–33.7 s glowing signature.
- **Measured:** 9 flashes clustered at 24–31 s (accent run), median scene 2.1 s, low camera motion (it is all
  designed graphics).
- **Transferable:** chat bubbles, input-bar typing, slider/counter, icon carousel, calendar selection, single-word
  slams, typewriter, blur-in titles, glow sign-off: each becomes an editable Hyperframes template with word-timed
  entrances.

## Ref 4 — Phonk product montage (the beat-sync benchmark)
- **Measured:** 143.6 BPM, music drop at 3.5 s; 89 % of cuts within 60 ms of a beat (median 28 ms); median shot
  0.87 s; zoom-in in 14.8 % and zoom-out in 13.8 % of frames (constant punch-in/out); 4 whip/motion-blur transitions;
  flashes at 4.47, 5.30, 11.17, 12.00, 12.83, 13.27 s (black) and 13.73 s (white).
- **Time-coded:** 0–3.7 s model holds a shoe to camera (the hook, before the drop) · 3.7 s cut on the drop to shelf
  close-ups · 4.5–9.5 s shoe close-ups, punch-ins, whips between angles · 10.4 s staged "proposal" gag with a shoe ·
  11–14 s fast beat cuts with black flashes, white flash on the last hit.
- **Transferable:** hook shot held through the build, drop = first hard cut; one cut per beat (sometimes two);
  punch-zoom on hits; black flashes as accents on off-beats near the end; whip transitions between angles of the same
  product; same footage repeated with different framing. Implemented as the `phonk` pacing profile.

## Ref 5 (extra) — Product/UI advertisement, landscape
- **Time-coded:** 0–8.9 s chat thread (green bubbles: "Hello", "your video is ready…", "what do you think?", reply
  "It's good but… BRO YOU COOKED") · 8.9–12.6 s dashboard UI with headline "All In One" / "Manage your Business",
  donut chart animating · 12.7–13.3 s profile card "Upload Reels — zero followers" · 13.3–14.6 s phone mockup with a
  revenue counter rolling up ($52 → $1,417 → $3,…) · 14.6–15.5 s giant word "Clothes" with a product **behind/inside
  the letters** · 15.5–17.4 s "Essentials" + sneaker · 17.4–21.8 s tilted phone with yellow caution tape ("PAIN")
  sweeping across · 21.8–24.6 s pink app UI with flying folders · "Minutes" + alarm clock · 24.6–27 s end card.
- **Transferable:** counters, text-behind-object, caution-tape wipe, tilted device mockups, flying UI elements.

## Ref 6 — Premium motion-designed advertisement (filmed on a laptop)
- **Framing:** the whole ad is a designed animation playing on a laptop screen filmed in a dark room; a persistent
  top caption ("…COOKED" until ~25 s, then "Comment SKILL and it's yours").
- **Time-coded (screen content):** 0–2.5 s sunrise-sky reveal · 2.5–5.5 s single words blur-to-sharp ("one file",
  "videos") · 6–10 s UI dialog types "A skill file" · 10.5–14 s floating window card over clouds · 14.5–19 s portfolio
  grid cards slide in · 19–23 s collage + red poster "never stop exploring" · 24–26 s "Premium websites" cards ·
  27–31 s logo page · 32–35 s laptop over clouds · 35.5–38.5 s glowing blue horizon arc with headline · 39–42 s website
  mockup · 44.5 s "But be quick" · 45.5–49 s counter "200" then FREE/PAID swap with a mascot · 50–57 s CTA card with
  a profile and button.
- **Measured:** long outer shots (median 11.1 s) because the cuts are on the filmed screen; one dip to black;
  25 % of outer cuts on the beat (voice-led, not beat-led).
- **Transferable:** blur-to-sharp words, floating windows over a sky, portfolio grids, light arcs/horizon glow,
  counters, price swap, CTA card; "screen in world" framing (composite a designed scene onto a device mockup).

## Guide (VenomsTechAI) — rules adopted
Storyboard before render; one plan file for every time; captions 1–3 words with the current word highlighted;
picture and sound rendered separately then muxed (fixed 0.77 s drift in their test); −14 LUFS / −1.5 dBTP;
Instagram safe zone x 90–930, y 200–1560, nothing on the right rail; cuts in pauses on the frame grid; whoosh peak ≥
0.15 s before the next word; SFX ducked ~6 dB under speech; QA with numbers (contact sheets, frames either side of
cuts, re-transcribe joints).

## How this is used
| Technique | Where it lives |
|---|---|
| Beat-locked cuts, punch/shake/flash/whip, ramps | `editing/pacing.py` (`phonk`, `energetic`, `product_showcase`…), `editing/planner.py`, `editing/effects.py` |
| Grade, glow, vignette, grain, RGB split, blur reveal | `editing/effects.py` (FFmpeg, verified 24/24 effects change the picture) |
| 21 transitions (whip, zoom-through, dip, flash, swipe, radial…) | `editing/effects.py:TRANSITIONS` → FFmpeg xfade |
| Layout templates (before/after, list + card, chat, counters, mockups, text behind object, CTA) | Phase 6 Hyperframes template library |
| Reference transfer ("make it like my reference") | `reference/analyzer.py` profile → AI Director (Phase 7) |
