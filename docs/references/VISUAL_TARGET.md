# Reusable visual target

This document converts the owner benchmark frames and the two canonical front
views into render checks. It defines a style envelope, not the blocking or
content of a particular scene.

## Evidence and measurement conventions

### Sources

- Motion/look samples: `visual_target/frames/paperboat_01.jpg` through
  `paperboat_12.jpg` and `watertable_01.jpg` through `watertable_05.jpg`.
  These are 1 s samples from 24 fps benchmarks. The landscape samples are
  640 x 360; the portrait samples are 640 x 856.
- Character look anchors:
  `../../assets/characters/boy_yellow_hoodie/references/views/canon29_front.png`
  and
  `../../assets/characters/girl_auburn_bun_glasses/references/views/sheet30_front.png`.
- Identity, silhouette and local character colours come from the character
  front views. Scene lighting, focus, grade and motion come from the benchmark
  frames. A grade must not move a character so far that the canonical local
  colours cease to read.

`MEASURED` means a value was taken directly from the supplied files.
`ESTIMATE` means it was inferred visually because the images contain no camera,
light, material or sub-frame motion metadata. Estimate ranges are acceptance
targets until a better calibrated benchmark exists.

### Common measurement setup

1. Evaluate the final display transform in sRGB/Rec.709, with auto exposure,
   sharpening, denoising and dynamic resolution locked. Compare like-for-like
   crops, not raw shader values.
2. Define **H** as the projected outer skull width in pixels, excluding ears,
   loose hair, bun and accessories. For material checks, crop the clearest head
   and rescale both render and reference so `H = 256 px`. Use nearest output
   resolution first, then the same high-quality resampler for both images.
3. Unless noted otherwise, measure three unobstructed patches and report the
   median. A pass requires at least two of the three patches to be in range and
   none to miss the nearest limit by more than 20%.
4. Display luma is `Y' = 0.2126 R + 0.7152 G + 0.0722 B` on 8-bit sRGB values.
   Pixel saturation is `(max(R,G,B) - min(R,G,B)) / max(R,G,B)`. Colour error
   is CIEDE2000 under D65 after converting the displayed pixels to Lab.
5. For focus comparisons, use `E = variance(Laplacian(Y'))` on matched
   64 x 64 px texture crops after the common H normalization. Report
   `E_test / E_in-focus`; do not compare unrelated surfaces.
6. Fibre and weave checks are valid only when the source crop has `H >= 180 px`.
   Below that scale, judge the integrated soft texture and silhouette rather
   than trying to resolve individual fibres.

No extra reference crops are required: the full saved frames above contain the
measurement regions and avoid introducing another resampling generation.

## Materials

| Property | Target | How to measure in a render | Reference anchors |
| --- | --- | --- | --- |
| Felt fibre scale | **ESTIMATE:** exposed fibre width `0.003-0.008 H` and free length `0.010-0.025 H`. At `H = 256 px`, that is about `1-2 px` wide and `3-6 px` long. | On a light/dark silhouette boundary, measure 20 isolated fibres at 200-400% view. Use the median shaft width and root-to-tip length. Reject fibres below 1 px after H normalization as noise and clumps over `0.03 H` as yarn locks. | Sleeves and hair edges in `paperboat_02`-`05`; hoodie and hair edges in both front views. |
| Surface fuzz amount | **ESTIMATE:** `18-45` distinct silhouette crossings per H on felt/fleece; flat-patch high-frequency RMS `3-8/255 Y'` after subtracting a 9 px Gaussian blur at `H = 256 px`. Skin and paper remain below `3/255`. | Count strand crossings along a clean boundary of length H. On a 64 x 64 flat-lit patch, subtract the blurred patch and calculate luma RMS. Fuzz must be stochastic, with no repeated comb pattern. | Blue sleeves in `paperboat_03`-`05`; yellow hoodie in `paperboat_01`; both front views. |
| Sheen/roughness read | **ESTIMATE:** cloth/felt residual highlight ratio `P90/P50 = 1.08-1.22`; plush hair `1.10-1.28`; skin `1.12-1.32`. No cloth highlight may exceed `1.45 x` its local median except a direct rim. | Divide a patch by a 31 px Gaussian-blurred copy to remove form shading, then take the positive residual's P90/P50. Specular features should be broad and broken by fibre, never plastic pinpoints. | Soft sleeves in `paperboat_02`-`05`; hoodie and vest in the front views. |
| Material colour saturation | **MEASURED:** ordinary classroom frames have median pixel saturation `36-48%` and P90 `69-75%`; water/magic close-ups fall to median `16-30%`. **ESTIMATE:** any flat garment patch should retain `75-110%` of its canonical front-view saturation and be within `Delta E00 <= 8` after compensating exposure. | Compute frame S50/S90 excluding emissive pixels, then sample the same garment location in a neutral-lit render and canonical front view. Compare Lab after matching patch median luma. | All 17 frames for the frame statistics; canonical front views for local colours. |
| Hair yarn and lock thickness | **ESTIMATE:** boy primary locks `0.055-0.12 H`; auburn primary curls/ropes `0.035-0.080 H`; fine surface ridges `0.006-0.015 H`. At least three lock-width families must be visible, with the largest no more than `2.5 x` the median. | Take 12 perpendicular cross-sections away from roots and tips. Divide each visible lock width by H; bin into fine/medium/large families. Do not count shading bands as geometry. | Boy and auburn-girl front views; group frames `paperboat_01`, `paperboat_06`, and `watertable_01`-`05`. |
| Fabric weave visibility | **ESTIMATE:** close-up weave/fleece pitch `0.006-0.016 H` (`1.5-4 px` at normalized size) with luma modulation `2-6%` of local median. At `H <= 100 px`, a weave grid must not remain individually resolvable or alias. | In a tangent garment patch, measure peak-to-peak spacing across 10 repeats and `(P90-P10)/P50` after removing a 15 px shading gradient. Downsample once to delivery size and inspect for moire. | Sleeve/vest close-ups in `paperboat_02`-`05`; front-view hoodie, vest, shorts and boots. |

Useful **MEASURED** display-colour anchors from the front references (not raw
shader base colours) are: boy hoodie `#C7954F`, boy dark hair `#2C2930`, auburn
hair `#56362C`, auburn vest `#6E4C4A`, auburn shorts `#636B64`, and auburn shirt
`#CBC1BE`. Measure a median patch under comparable neutral illumination; allow
the `Delta E00 <= 8` tolerance above for texture and lighting.

## Lighting

| Property | Target | How to measure in a render | Reference anchors |
| --- | --- | --- | --- |
| Key direction and size | **ESTIMATE:** soft front/side key, usually from screen-left: camera-relative azimuth `25-45 deg` and elevation `35-55 deg`. Penumbra width on a face or hand is `0.03-0.10 H`. | Fit the direction from the nose, finger and paper shadows. Their centroids should move down and away from the key. Divide the 10-90% shadow-edge width by H. A shot may mirror screen direction, but all objects must agree. | `paperboat_02`-`05` and `paperboat_07`-`08`; face modelling in `paperboat_01`/`06`. |
| Key colour temperature | **ESTIMATE:** daylight key `5000-5800 K`; warm room/bounce contribution `3500-4500 K`. A nominally neutral diffuse patch should land at displayed `R/B = 1.03-1.15` outside deliberate blue water reflection. | Sample white paper or a neutral shirt on the lit side, excluding specular pixels, and compare median R/B. Confirm with the shadow side: warm bounce may raise R, but should not turn skin orange. | White paper in `paperboat_02`-`10`; neutral sleeves/shirt in the auburn-girl front view. |
| Fill ratio | **ESTIMATE:** key-side to shadow-side linear-luminance ratio `1.6:1-2.5:1` (`0.7-1.3 stops`) on skin; deepest non-contact facial shadow remains at least `35%` of the lit cheek. | Choose equal-size mirrored cheek or hand patches with similar normals, convert sRGB to linear light, and calculate the median ratio. Exclude eyes, blush, hair occlusion and rim. | Faces in `paperboat_01`, `paperboat_06`, and `watertable_01`-`05`. |
| Rim/backlight | **ESTIMATE:** selective, broad rim `0.15-0.60 stop` over adjacent hair/fabric and `0.01-0.04 H` wide; coverage below `35%` of the character silhouette. It is absent where the window/key geometry does not justify it. | Trace the silhouette, compare rim median to the immediately inward band in linear light, and measure rim width/coverage. Reject a continuous CG outline. | Window-facing hair edges in `paperboat_01`/`06` and `watertable_01`-`05`. |
| Contact shadows | **ESTIMATE:** contact core is `20-45%` darker than adjacent lit surface, core width `0.005-0.025 H`, and soft falloff completes within `0.01-0.05 H`. No visible gap may exceed `0.005 H` at an intended finger/paper/table contact. | Draw a normal profile through at least five contacts. Record minimum/local median, core and 90% recovery distance. Also inspect the alpha/depth edge for floating. | Fingers, paper and tabletop in `paperboat_02`-`05`; boat/water contact in `paperboat_08`-`10`. |

## Camera and focus

| Property | Target | How to measure in a render | Reference anchors |
| --- | --- | --- | --- |
| Focal length | **ESTIMATE:** `40-55 mm` full-frame equivalent for ensemble/table views and `65-85 mm` for hand, object and reaction close-ups; overall allowed range `40-85 mm`. | Record render metadata. As a visual cross-check, on a face near frame centre the nearer/farther eye diameter ratio should stay below `1.08`, and the nearest/farthest same-sized hand ratio below `1.15`. | Ensemble frames `paperboat_01`/`06`, portrait sequence; close-ups `paperboat_02`-`05` and `07`-`11`. The canonical front views are indexed as **ESTIMATE** `70 mm`. |
| Focus plane | **ESTIMATE:** intended eyes/hands/object have normalized sharpness `0.85-1.00`; a subject about one head-depth away is `0.40-0.75`; far classroom detail is `0.08-0.30`. | Set the in-focus matched texture crop to `E = 1.0`, then use the Laplacian-energy ratio defined above at near, one-head-depth and far planes. Keep every element required to understand a manipulation at `>= 0.75`. | Background falloff in `paperboat_01`/`06`; hand/object plane in `paperboat_02`-`05`; boat close-ups `paperboat_09`/`10`. |
| Focus falloff shape | **ESTIMATE:** transition from `E = 0.8` to `E = 0.3` occurs across `0.5-1.5 H` of scene depth, without a hard composited edge. Foreground blur may reach `E = 0.15-0.45` but may not cover the active contact. | Place identical calibration cards at known depth offsets for a test render and plot E against depth/H. In production, inspect hair, fingers and prop edges for matte-like discontinuities. | Layering in `paperboat_03`, `paperboat_07`, and `paperboat_11`. |
| Close-up framing | **ESTIMATE:** active hands plus object occupy `55-82%` of frame width and `35-68%` of frame height; object alone occupies `32-58%` of width. Preserve `4-8%` frame margin ahead of the motion and at least `3%` around the manipulated object. Cropping the upper face/head is acceptable; cropping fingertips or the contact point is not. | Measure the union bounding box of active hands/object and divide by frame dimensions. Check motion extrema, not only the held pose. | `paperboat_02`-`05` for manipulation and `paperboat_07`-`10` for object close-ups. |
| Close-up viewpoint | **ESTIMATE:** optical axis `5-20 deg` downward for tabletop work; roll below `1 deg`; active surface foreshortening leaves its near/far projected width ratio between `1.0` and `1.25`. | Read camera metadata and verify with a planar grid placed on the active surface. | `paperboat_02`-`05` and `paperboat_07`-`10`. |

## Colour grade and contrast

The grade is warm, soft and moderately saturated. It should feel bright without
lifting all blacks or clipping the window/paper. Character accents carry more
chroma than the set; water and white paper provide cooler/neutral relief.

| Property | Target | How to measure in a render |
| --- | --- | --- |
| Frame luma distribution | **MEASURED:** across the supplied frames, observed `Y'05 = 26-76`, `Y'50 = 105-140`, and `Y'95 = 171-232`. **ESTIMATE production envelope:** for a non-emissive classroom frame use `Y'05 = 28-52`, `Y'50 = 110-138`, `Y'95 = 185-235`; pixels below 8 or above 247 each remain under `1%`. | Compute whole-frame percentiles after the final display transform, masking only authored emissive/spark particles. For an emissive close-up, report masked and unmasked values. |
| Contrast shape | **ESTIMATE:** soft shoulder beginning near `Y' = 220`, no broad clipped paper/window plateau, and local face contrast `(P90-P10)/P50 = 0.55-0.95`. Black hair may reach `Y' = 18-35` but must retain at least `12/255` P90-P10 separation inside the hair mass. | Plot a 256-bin luma histogram and inspect waveform clipping. Measure one face crop and one dark-hair crop at matched H. |
| Global saturation | **MEASURED:** ordinary classroom samples have `S50 = 36-48%`, `S90 = 69-75%`; water/object close-ups have `S50 = 16-30%`, `S90 = 44-58%`. **ESTIMATE:** keep non-emissive shots inside the corresponding family within `+/-5 percentage points`. | Calculate S50/S90 on final sRGB pixels. Mask only emissive particles; do not mask skin, set dressing or water. |
| Palette anchors | **ESTIMATE display midtones:** warm cream `#D8CBBB`, honey wood `#8B6248`, powder blue `#86A8B5`, mustard `#C7954F`, dusty rose `#8A625F`, sage `#68766A`, water blue `#6F9AA8`, and charcoal `#2C2930`. Use `Delta E00 <= 10` for set colours and `<= 8` for the canonical character patches listed above. | Sample 15 x 15 px or larger flat midtone patches, reject the brightest/darkest 10%, and compare the median in Lab. Match patch luma before checking character chroma. |
| Warm/cool separation | **ESTIMATE:** neutral lit surfaces have `R/B = 1.03-1.15`; water/cool-shadow patches `R/B = 0.78-1.00`; warm wood/bounce `R/B = 1.25-1.65`. At least two of these three families should be visible in an interior frame. | Use median RGB from unclipped diffuse patches. Report R/B and the patch coordinates with the review render. |

Golden particles are an accent, not a new base grade. In frames with that effect,
keep particle cores below `0.5%` of the image and the affected halo below `12%`;
**ESTIMATE:** halo hue `35-55 deg`, saturation `25-65%`, and unmasked
`Y'95 <= 235`. Compare `paperboat_09` and `paperboat_10`.

## Motion and editorial rhythm

All frame counts below assume 24 fps. Because the evidence is sampled only once
per second, every sub-second motion value is an **ESTIMATE**.

**MEASURED at 1 s sampling resolution:** the manipulation close-up remains the
same composition from `paperboat_02` through `paperboat_05` (about 3 s between
first and last samples); the water-table composition persists across all five
portrait samples; the object-on-water close view persists through
`paperboat_08`-`10` (about 2 s between first and last samples). These are the
cadence anchors, not proof of exact cut frames.

| Motion item | Target | How to measure in a render |
| --- | --- | --- |
| Overall tempo | **ESTIMATE:** one readable primary beat every `0.75-1.50 s` (`18-36 f`); shot duration normally `2-5 s`; no more than two competing primary actions in one second. | Mark each change of intention or dominant silhouette on a dope sheet. Measure beat-to-beat and cut-to-cut intervals; flag simultaneous actions whose screen-space speed each exceeds `0.03 H/f`. |
| Pose holds | **ESTIMATE:** readable key-pose dwell `8-18 f`. During a living hold, head/torso centroid motion is `0.001-0.006 H/f`; avoid a perfectly identical pose for more than `6 f` unless the stillness is intentional and eyes/breath remain active. | Track head and torso centroids and joint angles frame by frame. Count consecutive frames inside `0.01 H` position and `2 deg` rotation of the key pose, and inspect for sub-pixel render noise being mistaken for motion. |
| Anticipation | **ESTIMATE:** `5-10 f` before a hand, head or torso action; opposite-direction displacement `0.02-0.06 H` or a visible `20-45%` compression of the acting limb's speed curve. Gaze leads a hand target by `2-5 f`. | Plot screen-space root/hand velocity and gaze-target error. Identify the first purposeful reversal or compression before peak action speed. |
| Primary action | **ESTIMATE:** ordinary reach/fold/place travels `0.15-0.45 H` over `10-24 f`; peak hand speed `0.018-0.045 H/f`. Contact speed must drop below `0.008 H/f` for the final `2-4 f` before touch to avoid snapping or penetration. | Track the active wrist and contact point in screen space, normalized by H. Plot displacement and speed; check interpenetration on every contact frame. |
| Settle and overshoot | **ESTIMATE:** overshoot `3-8%` of the primary travel, followed by `8-18 f` to reach less than `10%` of peak speed. Final prop drift after placement stays below `0.005 H` over `12 f`, except buoyant objects. | Measure action travel, maximum past the final pose, and frames until velocity threshold. Use prop-relative coordinates when the camera moves. |
| Secondary motion | **ESTIMATE:** hair/curl/hood/string tips lag the driving head or torso by `2-5 f`; tip amplitude `0.02-0.06 H` for hair and `0.01-0.04 H` for clothing details. Motion decays below 10% of first swing within `12-24 f`, with at most two visible reversals. | Cross-correlate driver and tip displacement to obtain lag. Measure peak-to-rest amplitude and successive extrema. Hair groups need small phase variation (`1-3 f`), not synchronized pendulums. |
| Facial micro-timing | **ESTIMATE:** blink `4-7 f` total with closure faster than opening; reaction eyes/brows lead mouth/head by `2-4 f`; expression settle `8-16 f`. Hold eye direction within `3 deg` of the intended target during fine hand work. | Log eyelid aperture, brow/mouth controls and gaze vector. Verify lead/lag on the curves and inspect at full speed and frame-by-frame. |

Camera motion, when used, must stay subordinate to the acting: **ESTIMATE** drift
below `0.006 frame-width/f`, ease-in/out for `8-16 f`, and no handheld-frequency
jitter above `0.5 px RMS` at delivery resolution. The supplied samples mostly
read as locked or gently settled compositions.

## Minimum review package and pass rule

For each new lighting/material setup, submit these final-display images or
measurements:

1. one ensemble crop with at least two faces, reporting H, luma percentiles,
   S50/S90, fill ratio and far-background sharpness ratio;
2. one `H >= 180 px` material close-up, reporting fibre width/length, fuzz RMS,
   sheen ratio, weave pitch and the relevant canonical colour error;
3. one contact/object close-up, reporting framing occupancy, focus ratios and
   contact-shadow profile;
4. one representative motion beat with the tracked anticipation, primary,
   hold, settle and one secondary-motion curve at 24 fps.

A setup passes when every non-estimated measured limit is met, at least 90% of
the applicable **ESTIMATE** rows are in range, and no miss is visually systemic
(for example plastic cloth, hard focus mattes, floating contacts, clipped
whites, or uniformly synchronized hair). Record any deliberate exception with
the shot and artistic reason; do not silently retune this reusable target per
shot.
