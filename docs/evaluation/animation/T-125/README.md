# T-125: automatic motion checks (flicker, popping, interpenetration)

**`tools/motion_checks/run.py` checks a baked shot, and its rendered frames when given, for flicker / shimmer per
region, popping (jerk outliers on joints, face morphs, props and skinned vertices) and interpenetration over time on
the engine's collision bodies. Every issue reports a frame range, the worst frame and value, and a JPEG evidence
strip.** It is not wired into the gate. Method and usage: [tools/motion_checks/README.md](../../../../tools/motion_checks/README.md).
All limits are in [thresholds.json](../../../../tools/motion_checks/thresholds.json) and come from the measurements
below. Fixture tests: `python3 tools/motion_checks/tests/test_motion_checks.py` (22 tests).

| shot | source | bake | rendered for flicker | flicker | popping | interpenetration |
| --- | --- | --- | --- | --- | --- | --- |
| e907 exchange s010 | input `2464b7a`, cast boy 2.1.0 / girl 0.12.0 | f1–66 | f1–66, all frames | 2 | 17 | 1 |
| e909 two-char acting s010 | T-114 branch `6af5306` (read-only worktree; its own engine build) | f1–286 | f40–84 window | 11 | 67 | 4 |
| e910 showcase s010 | T-117 branch `f8a1961` (read-only; cast "unpublished build from spec") | f1–192 | not rendered | – | 63 | 6 |

Per-shot reports (thresholds omitted; they are thresholds.json at this commit) and strips: [e907/](e907/),
[e909/](e909/), [e910/](e910/). Strips are the 4 worst issues per check (`--strips N` for more).
Renders: the shots' production settings (Cycles, 640 × 360, 16 samples, OIDN, fixed seed), plus the passes from
`render_passes.py` (object index for regions, depth, normal, Vector, the noisy image before the denoiser).

Pixel scale at the e907 / e909 framing: 2.63 mm per pixel at the characters (camera at 1.49 m, 32 mm lens,
36 mm sensor, 640 px wide).

## Popping

Rule (all channels): frame t pops when `|a_t| >= abs_min` and `|a_t| >= 0.45 * max(|v_{t-2}| .. |v_{t+3}|)`.

| measurement (three bakes) | e907 | e909 | e910 |
| --- | --- | --- | --- |
| joint pivots, `|a|` p50 / p99 / max (mm/f²) | 0.23 / 35 / 70 | 0.17 / 32 / 150 | 0.15 / 40 / 169 |
| joint rotations p50 / p99 / max (°/f²) | 0.07 / 26 / 98 | 0.06 / 27 / 136 | 0.06 / 24 / 71 |
| face morphs max (weight/f²) | 0.04 | 0.55 | 0.56 |
| props max (mm/f²) | 1.6 | 3.3 | 3.5 |
| skinned vertices (every 16th) p50 / p99 / max (mm/f²) | 0.04 / 37 / 107 | 0.03 / 40 / 226 | 0.05 / 42 / 239 |
| fast by design (eyes, blinks, lids), max | 66 °/f², 0.53 w/f² | 72 mm/f², 1.0 w/f² | 70 mm/f², 1.0 w/f² |

- **abs_min 8 mm/f² (and 8 °/f²)**: 3 px/f² at this framing, the smallest frame-to-frame change of speed that reads
  as a kink at 24 fps. The body channels' median is about 0.2 mm/f², so 8 is 40× the median and below the p99
  (32–40), which is the hair spring chains.
- **jerk 0.45**: animcheck's `max_jerk`. Measured on synthetic moves (tests): a cubic ease over 8 frames scores
  0.38 and passes; a one-frame spike scores about 2, and starting or stopping within one frame about 1.
  The worst hit above abs_min scores 1.17 (e907) to 1.97 (`jerk_max_above_abs_min`); the flagged frames are
  near-instant starts, stops and reversals, not eases.
- **morph abs_min 0.15 weight/f²**: the body morphs' max is 0.04 on e907. Blinks reach 1.0 and are by design.
- **by design**: eye bones, blink / squint / eye-wide morphs and the lid, lash, eye and brow meshes. They are
  measured (last row) but not flagged.

What the check finds:

- **Hair spring chains (most issues on all three shots).** The boy's `DYN-*` crown, fringe, sides and whorl chains
  and the girl's ringlets and bun whip, with second differences up to 98 °/f² and 239 mm/f² on the mesh. For
  comparison, the head moves about 11 mm/f. Peaks: e907 boy `hair_top` f52–65 (102 mm/f²); e909 boy fringe f63–85
  and f115–123, girl ringlets f53–79 (136 °/f²); e910 boy `hair_sides` f177–188 (239 mm/f²), girl bun f138–142.
  In e909 the rendered window confirms it: the girl's bun and flowers flicker in the hair-tile measure over the
  same frames, f56–83.
- **Neck snaps.** The girl's neck turns about 15° in 2 frames at e907 f29–30, merged into her ringlets issue. The
  boy's neck turns 16°/f at e907 f64 ([popping_01](e907/popping_01_rotation_f65.jpg)); the shadow of his hair then
  flickers on his forehead (flicker, below).
- **Fingers.** Grasp snaps: e907 boy f12–17 (thumb 22 mm/f², fingers 17 °/f²); e909 thumbs f131 and f167;
  e910 girl fingers f9–11 (57 mm/f²) and f107–113.
- **Face morph.** The girl's `WideOpen` steps: e909 f34 (0.55 w/f²), f20 and f56; e910 f75, f111 and f140.

## Interpenetration

| measurement, min gap (mm, negative = inside) | e907 | e909 | e910 | limit |
| --- | --- | --- | --- | --- |
| arm: forearm / hand vs own torso + garment shell (from the rest allowance) | -1.2 | -10.3 (girl L f45) | -12.8 (girl L f105) | -3 |
| head: head / hair shells, character-character | +20.3 | -10.8 (f75) | +103 | 0 |
| limb vs the other character's torso | +111 | +109 | +95 | 0 |
| hand-prop (cup proxy in the hand capsule) | -12.9 | -12.9 | -17.4 (boy R f138) | -15 |
| prop-body (cup vs torsos) | +88 | +71 | +81 | 0 |
| garment sink below rest (mm, positive = deeper) | 16.7 (girl blouse f39) | 19.2 (f47) | 30.8 (f111) | 5 |
| cup vs table top | 0.0 (resting) | 0.0 | 0.0 | -3 |

- **arm -3 mm**: the e907 minimum is -1.2 mm (sleeve cloth touching the torso shell). -3 mm leaves a 2 mm margin
  above that. e909 and e910 go to -10 and -13 mm, and the strip ([e909 arm f45](e909/interpenetration_01_arm_f45.jpg))
  shows the girl's left forearm pressed into her side while she reaches.
- **hand-prop -15 mm**: a firm grip puts the cup handle 12.9 mm inside the hand capsule (both e907 hands, the e909
  pickup). The limit allows 2 mm beyond that. The e910 grip is 17.4 mm deep at f76–139.
- **head 0, limb 0, prop-body 0**: the shells are already padded volumes, so any overlap is contact.
  The e909 f75–76 head overlap (-10.8 mm) is the two heads' hair shells meeting ([strip](e909/interpenetration_02_head_f75.jpg)).
- **garment 5 mm**: a garment vertex deeper under its paired skin vertex than at rest. Deep paired cloth (boy's
  hoodie, all shots) stays at 0 mm. The girl's blouse at the shoulders and cuffs goes 10–31 mm under the skin while
  her arm is raised, on all three shots. On e907 that region is under the vest and hair, so it may not show
  ([strip](e907/interpenetration_01_garment_f39.jpg)); at the e910 cuffs it is at the wrist.
- **prop-room -3 mm**: the cup rests on the table at 0.0 mm on all three shots. -3 mm is under 1 px.

## Flicker / shimmer

Measured per frame and per region on the denoised and the noisy image. Each measure is motion-compensated with the
Vector pass (`motion_compensated: true` on both shots). Values are p50 / p90 / max over the rendered frames:

| region | held noise, denoised (e907 / e909) | held noise, noisy (e907) | flip share, denoised (e907 / e909) | flip share, noisy (e907) | worst tile, p50 (e907 / e909) |
| --- | --- | --- | --- | --- | --- |
| background | 0.0008 / 0.0008 / 0.0008 · same | 0.0 | 0.0007 / 0.0015 / 0.004 · 0.0013 / 0.0023 / 0.0035 | 0.013 | 0.08 / 0.12 |
| hair | 0.038 / 0.043 / 0.050 · 0.037 / 0.053 / 0.063 | 0.097 | 0.26 / 0.29 / 0.31 · 0.30 / 0.34 / 0.37 | 0.51 | 0.58 / 0.72 |
| fibres | 0.034 / 0.037 / 0.038 · 0.032 / 0.035 / 0.038 | 0.19 | 0.20 / 0.32 / 0.38 · 0.20 / 0.25 / 0.35 | 0.54 | 0.59 / 0.55 |
| skin | 0.015 / 0.020 / 0.024 · 0.012 / 0.023 / 0.131 | 0.071 | 0.056 / 0.074 / 0.19 · 0.076 / 0.17 / 0.32 | 0.37 | 0.29 / 0.45 |
| cloth | 0.014 / 0.015 / 0.016 · 0.015 / 0.019 / 0.023 | 0.044 | 0.11 / 0.12 / 0.13 · 0.11 / 0.14 / 0.16 | 0.30 | 0.44 / 0.48 |

The denoiser cuts held noise 2.6× on hair, 5.6× on fibres, 4.6× on skin and 3× on cloth. On hair and fibres,
about a fifth to a quarter of the pixels still turn back by 5% or more every frame after the denoiser (half of them
before it). This is the strand-grain shimmer of 16 samples, and it is the same on both shots.

Limits (`thresholds.json`, `flicker`), from the 107 rendered frames of both shots:

| region | held noise | flip share | tile flip share (3 frames running) |
| --- | --- | --- | --- |
| background | 0.002 | 0.01 | 0.6 |
| hair | 0.056 | 0.405 | 0.88 |
| fibres | 0.045 | 0.384 | 0.82 |
| skin | 0.027 | 0.18 | 0.6 |
| cloth | 0.021 | 0.161 | 0.6 |

- **held noise and flip share = 1.25 × the region's p90** over both shots (background: floors of 0.002 and
  0.01, since its p90 is at float16 resolution). The p90 is the production noise floor at 16 samples. A frame
  25% above it is flagged; the flagged frames sit well above it (e909 skin 0.131 against 0.027).
- **tile flip share**: on hair and fibres, 1.1 × the p90 of the per-frame worst tile (0.80 and 0.74), because
  strand grain fills whole tiles. On the solid regions (background, skin, cloth) the limit is 0.6, above the median
  worst tile of every solid region on both shots (0.08–0.48). In every case a tile must stay over the limit for 3
  frames running, so a blink or a saccade (1–2 frames) does not count.
- To treat the 16-sample strand shimmer as a defect too, lower the hair / fibres limits to the generic defaults
  (0.03 / 0.3 / 0.6). e907 then shows 24 hair and fibre issues, mostly the felt fuzz on the girl's shoulder and the
  boy's hair.

What the check finds:

- **e907 f62–65, skin tile 0.92** ([strip](e907/flicker_01_tile_flip_share_f64.jpg)): the shadow of the boy's
  vibrating hair flickers on his forehead during his neck snap (f64, popping above).
- **e909 f65–70, skin held noise 0.131 (limit 0.027)** ([strip](e909/flicker_01_held_noise_f67.jpg)): the mean
  skin brightness swings 0.34 → 0.39 → 0.40 → 0.35 → 0.37 between f66 and f70 while the background stays at 0.693.
  The faces' shading flickers by up to 15% from frame to frame, during the hair whips and the f75 head-shell
  contact. Skin tiles flag at f56–59 (the girl's forehead under her moving hair,
  [strip](e909/flicker_04_tile_flip_share_f58.jpg)), f66–70 and f75–77.
- **e909 cloth tile f58–60 (0.82)** and hair held noise f79–80 (0.063) are in the same span.
- **Missed:** the e909 bun / flower shimmer (worst hair tile 1.0 at f65) alternates above and below 0.88 from frame
  to frame, so it is not a 3-frame run. The hair-tile check does not flag it; the popping check does (bun f53–79).

## Limits of this evaluation

- e909 flicker covers f40–84 only (45 of 286 frames, about 53 s per frame with passes). The window covers the
  f43–47 arm contact, the f56 morph step, the hair whips from f53 and the f75 head contact. e910 was not rendered.
  It is a bake check on the T-117 branch, whose cast is still an unpublished build.
- The fixed seed makes the background's held noise about 0 in the noisy image. With an animated seed, the noisy
  floor rises, but the denoised floor (what the limits use) is set per frame by OIDN.
- The garment check pairs cloth to skin by the dominant bone. It measures depth below rest, not visibility: an
  occluded sink (e907 shoulder) is reported all the same.
- Region-wide flicker issues have a plot only. Tile issues and every popping and interpenetration issue also get
  rendered crops (the worst frame and its neighbours, plus the flip map for tiles).
