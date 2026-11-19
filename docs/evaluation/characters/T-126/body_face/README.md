# T-126a: girl_white_hair_blue_dress body, face and eyes, base spec 0.1.0

Input `integration/docs-r4 @ 6596eaf`, branch `t-126a-claude-body-face`. Blender: bpy 5.3.0 module behind
`tools/bpy_blender.py`. **Environment setup: none needed** (bpy 5.3.0 was already installed in the "Animation" env).
Nothing published or current. Boy and girl are untouched, and no shared generator, test or threshold was changed.

## Base spec
`assets/characters/girl_white_hair_blue_dress/spec/candidates/T-126a/girl_white_hair_blue_dress.0.1.0.spec.json`
plus the opt-in `hands_r2.override.json` (this folder). The composer is [make_spec.py](make_spec.py), and it states
every number's source.

**Path deviation from the task file.** A `*.json` directly in `spec/` makes the character "buildable" for the
regression gate (`tools/regression/tiers.py`), which then requires a current version and a fidelity-baseline entry, so
`tools/regression/tests/test_gate_tools.py` fails. `spec/candidates/` is not globbed. `body.hands` may not be set by
any spec under `assets/` (`pipeline/charsys/tests/test_hands_r2.py`), so hands_r2 comes from an override. Both tests
pass. The Supervisor was told.

- **Body:** the auburn girl's 0.13.0 `body_generic/2`, scaled by 0.972 (03 lineup: 1.069 m sole to bun top). Then:
  lower face 3 mm longer (chin 0.101 m below the eyes), eyes wider set (x 0.0623 m, eye spacing / ear width 0.421),
  arms 8 % longer (fingertips at 0.683 H), slimmer tights legs, and hands_r2/1 (T-121) through the override.
  The skeleton is the shared `rigify_human/1` (06 compatible).
- **Face:** `face_generic/3` with round 4 (T-109) and the T-113 closed fit and expression library (all 14 presets plus
  SmileOpen; none missing). Layout from her landmarks: mouth 0.052, nose 0.025, chin 0.101 m below the eyes;
  mouth half-width 0.018 m. Blue irises (iris radius 0.52), sclera, bolder dark lash with outer flicks, pale thin
  brows, small button nose, peach blush, closed soft-smile rest (14 e1 / 02 Neutral).
- **Fit pass from the probes:** the girl's T-115 flat upper lid read as a frown on her open eyes. Lids are now 58/−58°
  with upper_curve 0.2, the cheek pads are softer (0.011 m) so the crease across the face is gone, and eye yaw is −6°
  so the skin clears the inner-upper eye and the lash shows. The +6° yaw was worse.
- **Gaze:** `face.eyes.gaze_range_deg` [16, 8]. T-120 `gazeLegibility` is a scene or character key (opt-in), noted
  under `animation.gaze`.
- **Placeholders that b–d replace:** hair (T-070 `groom/2` cream draft with a felt bow), dress (garment/2 `dress`
  type demo, length 0.30, boots height 0.30), and materials (skin from color_targets plus the T-070 hair/bow).

## Evidence
- [preview_0.1.0.jpg](preview_0.1.0.jpg): cheap preview, Cycles 2 spp (first fit iteration).
- [strict_0.1.0.jpg](strict_0.1.0.jpg): strict sheet, reference | candidate | Higgsfield target (W05, W04, W02),
  Cycles 16 spp, T-087 cameras and character_neutral/1. Made with [sheet.py](sheet.py), which uses the shared
  blender_render.py and strict_sheet.py unchanged. recipe.py could not be used because it requires a published
  baseline column, and she has none.
- [expressions_0.1.0.jpg](expressions_0.1.0.jpg): 15 presets, each next to its 04 or 14 reference tile, made with
  [expr.py](expr.py) on the T-113 renderer, Cycles 12 spp.

## Visual read (fidelity first)
- **Closer:** the scale and silhouette match 02/03; the eyes are round, blue and open with catchlights; Neutral,
  Smile, SmileOpen, Surprise and MouthOpen mouths read like 04/14; the legs now show between hem and boots.
- **Open points for the combine/Codex step:**
  1. A soft skin wedge still covers the inner-upper eye, so the eyes read slightly stern; the reference shows the full
     upper lash arch.
  2. Closed lids (Blink, Laugh, Squint, one-eye closes) read as large skin domes without the curved lash line of 04.
     This is the T-113 closed fit on her larger, wider-set eyes.
  3. The brows are too pale to carry Sadness, Anger and Confusion (the 04 brows are light brown but visible).
  4. The head reads smaller than in 02 because her volume comes from the hair; that is part b's job.
- Not done: glb and compare builds, fidelity scoring, publish (Supervisor + T-126a step).

## Face pass 2 (Supervisor review of expressions_0.1.0)
Picked from cheap probes (spec copies A–F, Cycles 4 spp, Neutral/Smile/Blink/Laugh/Sadness/Anger); then 12 spp.
- **Stern wedge removed:** the upper lid edge sloped down towards the nose, and the skin rose over its shell.
  `lids.upper_roll_deg` −18 raises the inner end, giving a level, open arch as in m04_neutral; `upper_gap` 0.012
  keeps the shell close to the eyeball; socket `ramp_deg` 12 / `reach_deg` 36 blends it out softly. Rejected
  variants: −10° roll (still slanted), eyes 4 mm deeper (more wedge), eyes 4 mm forward with a 62° edge (the
  build fails in the lid fit).
- **Closed lids:** T-113 `closed_fit.gap` 0.002 plus `blink.flatten` 0.35 make the lids follow the eyeball, so the
  domes are flatter and smaller. **Open point, generator gap:** no `face_generic/3` lid or lash option draws the dark
  downward lash curve of a closed eye (04). The lash strip stays at the open edge and is covered, with
  `flatten_lash` on or off. This needs a closed-lash option in the shared lid code (`face_v3/lids.py`); shared code
  was not changed.
- **Brows:** light brown (146, 108, 86), 1.8 mm, at 1.42 r, just under the fringe edge. Sadness, Frown, Confusion
  and Anger now read through them and stay soft.
- Evidence: [expressions_0.1.0_pass2.jpg](expressions_0.1.0_pass2.jpg) (12 spp) and
  [face_front_pass2.jpg](face_front_pass2.jpg) (pass 1 | pass 2 | ref 01 | ref 04 neutral). The strict body sheet
  was not re-rendered (only face values changed).
