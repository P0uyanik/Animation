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
candidate specs): `overrides/<id>.temple.override.json`, `front_fade_m` 0.08. No spec, version or current change.

Effect of 0.08: skin moves only for y in [-0.09, -0.01] within the face-width band (max about -1.9 mm in front of the
cut, +2.6 mm behind it); head width at the ear (y 0) and the face front are unchanged.

### Evidence
- `temple/girl_clay.jpg`, `temple/third_clay.jpg`: skin only, grey material, grazing light, 3/4 and side, 100 % pixels
  (ortho 0.20 m / 640 px), before | after. The ledge is the ragged vertical line in front of the ear.
- `temple/girl_full.jpg`, `temple/third_full.jpg`: same views with the masters' materials and hair, before | after.
  Girl: the ledge shows below the glasses arm before, gone after. Third girl: the groom/4 side hair covers the temple
  in both views, so the change is only visible in the clay sheet.
- Default unchanged: strict mesh hashes (T-158 `mesh_hash_strict.py`, all objects, basis + shape keys) of a default
  build with and without the code change are identical: girl 224 objects, third 199 objects
  (`temple/hash_*_default_base.json` = `hash_*_default_t159.json`). The `.blend` files themselves differ byte-wise
  between two output directories, with or without the change.
- Tool: `tools/temple_views.py`.

### Tests
- `python3 pipeline/charsys/tests/test_face_front_fade.py --blender blender`: 9/9 (hard cut = old formula to 4e-9 m,
  12.7 mm step on the test sphere; fade: 0.55 mm per 2 mm bin, front and back untouched). Not registered in
  `tools/check_all.py` (outside the write-set).

### Open
- A faint horizontal seam remains at cheek height between the eye and the ear (visible in the clay views before and
  after; not the ledge). Not diagnosed; likely another shaping stage's edge. Needs a decision before it is touched.
- Not run: full strict sheets, fidelity score, test_determinism, ctest (Part A changes no default build).

## Part B: ears
Not started.
