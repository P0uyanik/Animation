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

## Part B: ears, all three

Specs: T-155 candidates (boy 2.3.0, girl 0.14.0, third 0.1.0), girls with the Part A override. Hair is the candidates'
groom/4.

### Findings (before)
- Shape: a squashed sphere with one shallow dent; no rim, the bowl barely reads. References: a rounded C ear with a rim
  and a bowl that opens towards the face.
- Colour: ears render pale grey next to the face. Same material as the face (`M_skin_face`), same albedo; the thin ear
  lets the subsurface light straight through (uniform-light test). Object coordinates are not the cause (first
  guess, tested and dropped).
- Position (outer edge of the ear / eye half-spacing, front view; landmarks.json): boy 2.67 (ref 2.54-2.63), girl 2.86
  (ref 2.74), third 2.68 (ref 2.37). Height below the eye line matches (12 / 12 / 27 mm vs 12 / 12 / 31 mm).
- Coverage: both girls' side hair covers the ears in every view; the references show the ear in front of the hair.
  Hair files: forwarded to hair round 7 (T-167), not changed here.

### Changes (opt-in, `face_generic.build_ears` only)
- `face.ears.shape` {subdiv, bowl_depth, bowl_size, bowl_centre, bowl_edge, rim, back_flat}: C-shaped ear. One shape
  for all three: bowl 0.9 deep, centre [-0.5, -0.05] (front), size [0.75, 0.62], rim 0.3, back_flat 0.6.
- `face.ears.subsurface` 0.3: the ears use a copy of the face skin (`M_skin_face.ear`) with 30 % of its subsurface
  weight; the ear then matches the face skin.
- Position overrides: boy `out_m` 0.006 -> -0.002 (2.63); girl `out_m` 0.004 -> -0.006, `yaw_deg` 32 -> 28 (2.74);
  third `out_m` 0.004 -> -0.007, `yaw_deg` 32 -> 28 (2.55: the ear stays 20 mm outside the head side as in id01; the
  reference ratio 2.37 would need a narrower head, not an ear change). Size and height unchanged.
- Overrides: `overrides/<id>.ears.override.json`. No spec, version or current change.

### Evidence
- `ears/<char>_ears.jpg`: reference | before | after; front, 3/4, side; 100 % pixels (ortho 0.22 m / 512 px), full
  materials and hair.
- `ears/girl_ears_nohair.jpg`, `ears/third_ears_nohair.jpg`: the same crops with the hair hidden (before / after),
  because the girls' hair covers the ear.
- Strict sheets (reference | baseline | candidate | AI target; recipe previews passed first):
  `boy/strict.jpg` (2.2.0 current vs 2.3.0 candidate + ears, arms down; `boy_2.2.0_vs_t159.recipe.json`),
  `girl/strict.jpg` (0.13.0 current vs 0.14.0 candidate + temple + ears, A-pose; `girl_0.13.0_vs_t159.recipe.json`),
  `third/strict.jpg` (0.1.0 candidate vs + temple + ears, A-pose; `tools/third_sheet.py`, no current version).
  At sheet scale the girls differ from their candidates only at the temple; their ears are under the hair.
- Default unchanged: strict mesh hashes of default builds (no override) equal the base code's for all three
  (boy 223 objects: `ears/hash_boy_default_base.json` = `hash_boy_default_t159.json`; girl 224, third 199: same hashes as
  `temple/hash_*`, rebuilt with the final code).
- Tool: `tools/ear_views.py`.

### Tests
- `python3 pipeline/charsys/tests/test_ears_shape.py --blender blender`: 8/8. Blender unit `ears-shape`
  (`tools/check_all.py`, shard 1).

### Open
- Girls: the ear change is not visible until the hair is tucked behind the ear (T-167).
- Third girl: ear / eye-spacing ratio 2.55 vs 2.37 (head width).
- Not run: fidelity score, test_determinism, ctest, full check_all.
