# T-159: temple hollow (Part A) and ears (Part B)

Base `origin/integration/t-141` (2a02532). Blender: bpy 5.3.0 module (`tools/bpy_blender.py`). Builds with the T-158
determinism environment. Specs: the T-155 candidates (girl 0.14.0, third girl 0.1.0, branch
`t-155-claude-candidates-r2`), hair = their groom/4 (not T-160 r6; the temple skin does not depend on the hair).

## Part A: temple hollow, both girls

### Cause
`face_features.shape_face_v2` applies `face.shape.face_width_m` (and `jaw_depth_roundness`) through a hard boolean
front/back mask: `y < face_y + 0.6·|face_y|` (about y = -0.05 m, just behind the outer eye corner). The lower-face
widening therefore stops dead on one vertex row and leaves a ragged vertical ledge between the eye corner and the ear;
behind it the head is narrower, which reads as a pinched temple. Both girls share the same `face.shape` values.

Measured (auburn girl, lateral skin x at fixed depth y, mm; ledge between y -0.06 and -0.05):

| height | y -0.07 | -0.06 | -0.05 | -0.04 | -0.03 |
|---|---|---|---|---|---|
| eye line -2 cm, before | 117.2 | 125.4 | 125.7 | 129.9 | 133.0 |
| same, `face_width_m` 0 (A/B) | 112.5 | 120.1 | 125.7 | 129.9 | 133.0 |
| same, after (`front_fade_m` 0.08) | 116.5 | 123.5 | 128.3 | 131.6 | 133.8 |
| eye line, before | 120.0 | 126.8 | 129.0 | 132.7 | 135.5 |
| eye line, after | 119.7 | 125.8 | 130.3 | 133.5 | 135.9 |

Step at the cut: 5.3 mm (eye line -2 cm), 2.7 mm (eye line). Third girl: same kink one bin further back
(122.5 / 123.2 / 126.6 before, 121.3 / 125.0 / 127.6 after).

Ruled out: ears (seat starts at y -0.026, skin unchanged there), hair cap (4 mm outside the skin, does not reach the
ledge), glasses temple arm (no skin contact; the third girl has no glasses and the same ledge), eye socket (the A/B
removes the ledge with the socket unchanged).

### Fix (opt-in)
`face.shape.front_fade_m` (new, default 0 = the hard cut): the mask falls smoothly from 1 to 0 over this depth, centred
on the cut. Code: `pipeline/charsys/face_features.py` (`front_weight`, `shape_face_v2`). Overrides (on the T-155
candidate specs): `overrides/<id>.temple.override.json`, `front_fade_m` 0.08, `outline_smooth_m` 0.006. No spec, version or current change.

Effect of 0.08: skin moves only for y in [-0.09, -0.01] within the face-width band (max about -1.9 mm in front of the
cut, +2.6 mm behind it); head width at the ear (y 0) and the face front are unchanged.

### Evidence
- `temple/girl_clay.jpg`, `temple/third_clay.jpg`: skin only, grey material, grazing light, 3/4 and side, 100 % pixels
  (ortho 0.20 m / 640 px), before | + front_fade_m | + front_fade_m + outline_smooth_m. The ledge is the ragged vertical line in front of the
  ear; the seam is the horizontal ripple band below the eye line.
- `temple/girl_full.jpg`, `temple/third_full.jpg`: same views with the masters' materials and hair, before | after.
  Girl: the ledge shows below the glasses arm before, gone after. Third girl: the groom/4 side hair covers the temple
  in both views, so the change is only visible in the clay sheet.
- Default unchanged: strict mesh hashes (T-158 `mesh_hash_strict.py`, all objects, basis + shape keys) of a default
  build with and without the code change are identical: girl 224 objects, third 199 objects
  (`temple/hash_*_default_base.json` = `hash_*_default_t159.json`). The `.blend` files themselves differ byte-wise
  between two output directories, with or without the change.
- Tool: `tools/temple_views.py`.

### Tests
- `python3 pipeline/charsys/tests/test_face_front_fade.py --blender blender`: 14/14 (hard cut = old formula to 4e-9 m,
  12.7 mm step on the test sphere; fade: 0.55 mm per 2 mm bin, front and back untouched; outline scale ripple
  0.0119 -> 0.0036). Registered as Blender unit `face-front-fade` (`tools/check_all.py`, shard 1 in
  `tools/ci/blender_shards.json`); `tools/ci/blender_inventory.py` and `tools/ci/tests/test_t127_shards.py` pass.

### Cheek-height seam (horizontal ripples, eye corner to ear)
Cause: the `outline_roundness` step of the same function scales every horizontal slice in x by target / measured
width; the measured width comes from raw 3 mm bins (max |x| within ±2 mm), which jitter with the vertex rows, so the
scale ripples with height. A/B (auburn girl, second differences of the lateral skin x at 4 mm steps, eye line -2.4 to
-5.6 cm, y -0.045): candidate +0.2 / -1.2 / +0.8 / -0.2 / -0.3 / -0.7 / -0.9 / +0.4 / -0.7 mm; `outline_roundness` 0:
all within -0.7..+0.3 without sign flips; `cheek_pad_m` 0 and cheek raise 0: unchanged. Fix (opt-in):
`face.shape.outline_smooth_m` (default 0 = raw bins), Gaussian sigma over height for the measured widths
(`smooth_profile`). With 0.006: -0.1 / -0.2 / -0.1 / -0.3 / -0.3 / -0.7 / -0.2 / -0.1 / -0.2 mm (no sign flips; the
larger values further down are the jaw turn). Third girl with both keys: -0.1 / -0.4 / -0.5 / -0.3 / -0.3 / -0.2 /
+0.2 / -0.2 (y -0.030). Third column of the clay sheets. Default builds hash-identical with this change too (same
hashes as above, rebuilt).

### Open
- Not run: full strict sheets, fidelity score, test_determinism, ctest (Part A changes no default build).
- The full-material sheets show `front_fade_m` only (rendered before the seam fix).

## Part B: ears, all three (pass 2, owner brief 2026-11-20 ~17:50 / ~18:15 CET)

Specs: T-155 candidates (boy 2.3.0, girl 0.14.0, third 0.1.0), girls with the Part A override. Hair is the candidates'
groom/4. Brief: larger, rounder C-shaped cup ears that stand out sideways in the front view, full lobe, defined rim and
bowl, warm pink skin, size and protrusion per T-161; auburn girl: the glasses arm rests on the ear.

### Findings (before)
- Shape: a squashed sphere with one shallow dent, lying flat against the head; no rim, the bowl barely reads.
- Colour: ears render pale grey next to the face. Same material and albedo as the face; the thin ear lets the
  subsurface light straight through (uniform-light test). Object coordinates are not the cause (first guess, tested
  and dropped).
- Size / protrusion (T-161 definitions, `ears/measures_before.json`): front projection 0.042 / 0.051 / 0.057 of the
  face width (boy / auburn / third) against targets 0.18 / 0.13 / 0.12.
- Glasses (auburn): the arm climbs to 22 mm above the ear landmark and is then lifted again over every ear vertex in
  its corridor (build report `temple_lift_m` 15-18 mm), so it floats above the ear with a bend.
- Coverage: both girls' side hair covers the ears in every view; the references show the ear in front of the hair.
  Hair files: hair round 7 (T-167), not changed here.

### Changes (all opt-in; default builds unchanged)
`face_generic.py` `build_ears` (+ helpers `ear_shape`, `ear_skin`, `ear_landmark`):
- `face.ears.shape` {subdiv, bowl_depth, bowl_size, bowl_centre, bowl_edge, rim, back_flat}: cup ear with rim, bowl
  and full lobe.
- `face.ears.subsurface` (0.3) and `face.ears.tint` {srgb, strength}: the ears use a copy of the face skin
  (`M_skin_face.ear`) with 30 % of its subsurface weight and a warm pink multiply tint.
- `face.ears.seat_offset_m` [out, back, up]: moves the ear from its seat; the ear landmark stays at the seat, so the jaw
  pivot (DEF-jaw head) and LM_ear are identical to the candidates (checked on all three). `face_generic_v3.py`: the
  one landmark line reads `ear_landmark(e)`.
- Negative `yaw_deg` turns the ear out the anatomical way (rear edge out, bowl facing front).

`accessories.py` glasses, temples block (+ helper `_temple_rest`):
- `temples.rest_on_ear`: a straight arm from the hinge, tangent on the top of the ear's section next to the head
  (`rest_clearance_m`), then the hook behind the ear. Build report: `temple_rest_m`, `temple_lift_m` 0.

Overrides (per character, stackable): `overrides/boy_ears.json`, `girl_ears.json`, `third_ears.json` (face.ears
only), `girl_glasses.json` (accessories.items = the candidate's list + `rest_on_ear`; lists are replaced, not merged).

### Measures vs T-161 (after; `tools/ear_measures.py`, `ears/measures_after.json`)
Computed from the geometry in orthographic projections; T-161 traces them by hand in perspective images (on the
unchanged boy this tool reads front projection 0.042 where T-161 traced 0.073 for 2.2.0; height and turn agree), so
read the comparison as approximate.

| measure | boy | target | auburn | target | third | target |
|---|---|---|---|---|---|---|
| ear_front_projection | 0.157 | 0.1845 ±0.04 | 0.140 | 0.1325 ±0.04 | 0.138 | 0.1168 ±0.04 |
| ear_width | 0.173 | 0.1964 ±0.055 | 0.152 | 0.1589 ±0.055 | 0.146 | 0.1533 ±0.055 |
| ear_height | 0.175 | 0.1728 ±0.045 | 0.211 | 0.2199 ±0.045 | 0.212 | 0.2077 ±0.045 |
| ear_turn_projection (30 deg) | 0.225 | 0.2229 ±0.06 | 0.200 | 0.2557 ±0.06 | 0.192 | 0.1916 ±0.06 |
| ear_top_eye | -0.053 | -0.0257 ±0.045 | -0.062 | -0.0262 ±0.045 | -0.025 | -0.0328 ±0.045 |
| ear_base_mouth | -0.017 | -0.0441 ±0.045 | -0.001 | 0.0209 ±0.045 | 0.033 | 0.0219 ±0.045 |

All inside the bands; the auburn turn projection is at the lower edge.

Correction: the pass-1 figures "outer edge / eye half-spacing" (2.67 / 2.86 / 2.68) were taken from bounding-box
corners and overstated by about 5 %. From the vertices the candidates are 2.53 / 2.68 / 2.50 (landmark references
2.54-2.63 / 2.74 / 2.37) and pass 2 is 3.06 / 3.11 / 2.87: the cup ears of the brief stand further out than the
landmark ratio, because the models' heads are wider relative to the eyes than the references.

### Evidence
- `ears/<char>_ears.jpg`: reference | before | after; front, 3/4, side; 100 % pixels (ortho 0.22 m / 512 px), full
  materials and hair.
- `ears/<char>_ears_nohair.jpg`: before / after with the hair hidden (all three; shows the ear and, for the auburn
  girl, the glasses arm on the ear).
- Strict sheets (reference | baseline | candidate | AI target; recipe previews passed first):
  `boy/strict.jpg` (2.2.0 current vs 2.3.0 candidate + ears, arms down; `boy_2.2.0_vs_t159.recipe.json`),
  `girl/strict.jpg` (0.13.0 current vs 0.14.0 candidate + temple + ears + glasses, A-pose;
  `girl_0.13.0_vs_t159.recipe.json`), `third/strict.jpg` (0.1.0 candidate vs + temple + ears, A-pose;
  `tools/third_sheet.py`, no current version).
- Default unchanged: strict mesh hashes of default builds (no override) with the final code equal the base code's:
  boy 223, girl 224, third 199 objects (`ears/hash_<char>_default_base.json` = `hash_<char>_default_t159.json`).
- Tools: `tools/ear_views.py`, `tools/ear_measures.py`.

### Tests (Blender units in `tools/check_all.py`, shard 1 in `tools/ci/blender_shards.json`)
- `test_ears_shape.py --blender blender`: 11/11 (`ears-shape`).
- `test_glasses_rest.py --blender blender`: 7/7 (`glasses-rest`).
- `test_face_front_fade.py --blender blender`: 14/14 (`face-front-fade`).
- `tools/ci/blender_inventory.py` and `tools/ci/tests/test_t127_shards.py` pass.

### Open
- Girls: with their hair the ears are still mostly covered; the hair tuck is T-167.
- The ears stand out further than the landmark ratio of the references (see correction above); a narrower lower
  face (T-168, boy) changes that ratio.
- Not run: fidelity score, test_determinism, ctest, full check_all, CI.
