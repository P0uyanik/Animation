# T-156: lashes and eye shape to the T-150 targets (both girls)

> **Sheet review (final renders, 2026-11-20).** `eyes_closed_100.jpg`: top = baseline, bottom = candidate, Blink 1.0. Front: thin liner + 5 outer lashes read as intended on both girls; openings rounder than T-137. Closed: lash curve is a clean thin arc on both (third girl's baseline band kinked at the inner end; gone). Open defects, not fixed here: (1) three-quarter view, near eye, both girls: a pale flap of sclera/socket shows past the outer corner (the widened socket window, corner_deg 37/36, is not covered by the lid at that angle); (2) auburn front: faint creases remain under the lower lid; (3) the lid-patch tone edge on the closed lids pre-exists in the T-137 baselines.

Input `t-137-claude-faces @ 321466a`; targets `docs/evaluation/characters/T-150/targets.json` (main `e2c8904`).
Blender: bpy 5.3 behind `tools/bpy_blender.py`. Overrides only; no current version, spec or published file changed.
Scope follows the Supervisor's notes of 06:41 / 06:50 / 07:04Z (lash first, lower-lid crease, boy; fringe untouched).

**Result.** Lash: thin dark liner with five short separate lashes at the outer corner (both girls); the closed eye
keeps a thin lash curve (auburn now too). Shape: every T-150 front metric is inside its band on both eyes
(auburn 11/28 -> 28/28, third girl 9/28 -> 28/28); opening width 67 -> 62 mm and 71 -> 61 mm. The pale lower-lid
crease is gone except a 4 mm stub under the iris. **Boy: not changed, see the question below.**

## What changed
`auburn/girl_auburn_bun_glasses.eyes.override.json`, `third/girl_white_hair_blue_dress.eyes.override.json`
(`face.eyes` only; they replace the T-137 F1a / F1b eye overrides; the F1b fringe override is used as it is).

| key (`face.eyes.`) | auburn T-137 -> T-156 | third T-137 -> T-156 | effect |
|---|---|---|---|
| `lash.thick_m`, `flare`, `srgb` | 3.4 -> 1.3 mm, 0.6 -> 0.8, [96,58,42] -> [52,32,26] | 3.4 -> 1.3 mm, 0.6 -> 0.8, [70,44,36] -> [40,26,24] | thin dark liner instead of the brown band |
| `lash.span_deg`, `lash.strands` | 52 -> 36; 5 lashes at 20-35 deg, 2.5-4.2 mm | 56 -> 36; same | liner ends at the corners; short outer lashes |
| `lash.lower_strands.count` | 0 (as F1a) | 3 -> 0 | they showed as two dark specks |
| `lids.trim.lo_outer_deg` / `lo_inner_deg` | 62 / none -> 2 / 2 | same | lower lid shell (the pale crease) cut to a stub the blink seam needs |
| `lids.closed_fit.lash_curve` | none -> as F1b, span [-0.45, 0.62] | span -> [-0.45, 0.62] | closed-eye lash curve |
| `socket.corner_deg` | 42 -> 37 | 46 -> 36 | narrower opening (width, H/W, D/W, no inner white) |
| `lids.upper_edge_deg` / `lower_edge_deg` | 38 / -36 -> 34.5 / -41.5 | 38 / -36 -> 33.5 / -39 | arch, lower lid, white above |
| `iris.radius` (`pupil` = half) | 0.47 -> 0.46 | 0.462 -> 0.458 | D/spacing |
| `lids.upper_roll_deg` | -18 -> 6 | -18 -> 1 | corners level, outer corner angle |
| `lids.upper_yaw_deg` (new, opt-in) | 8 | 8 | lid peak over the middle of the opening |
| `lids.lower_curve`, `lids.trim.up_outer_deg` | 0.15 -> 0.6, 72 -> 46 | same | lower corners; upper shell tip past the outer corner |

The lash keys are separable: drop the `lash` block to keep the T-137 lash on the new shape.

Shared code, opt-in: `pipeline/charsys/face_v3/lids.py` `lid_yaw` (`lids.upper_yaw_deg` / `lower_yaw_deg`). A lid
edge is close to a circle about the eye's forward axis, so its peak sat over the iris, at 0.63 W from the outer
corner (band <= 0.586) whatever the roll (tried -6 .. +14 deg): the nose-side skin makes the opening narrower on the
inner side. The yaw turns the lid and its lash about the eye's vertical axis; the eyeball does not move. Key
absent = the previous return value, bit for bit (unit test).

## Measurement (reproducible)
`eye_measure.py` (headless, no render, about 6 s): one ray per pixel of the 0.24 x 0.12 m eye window (1280 x 640)
against the evaluated skin, lid, lash and eyeball meshes, from the strict sheet's face camera; metrics as defined in
the T-150 README. `--camera probe --overlay` draws the trace on a 100 % eye strip (checked on the T-137 build).
`report.py` prints the tables from `*/measure_*.json`.

```
blender -b --factory-startup -P docs/evaluation/characters/T-156/eye_measure.py -- <master.blend> <out.json> [--yaw -35]
python3 docs/evaluation/characters/T-156/report.py <T-150 targets.json> auburn|white_haired front <before.json> <after.json>
```

Before = the T-137 F1a / F1b build, after = this task. Unlike T-150's hand traces, glasses, hair and lens refraction
are not occluders here. The T-137 READMEs' hand estimates of H/W (~0.73) were lower than this measure of the same
builds (0.83 / 0.79). Blink: 0 open pixels on both girls.

### Auburn girl, front
| metric | target front | before left | before right | after left | after right |
|---|---|---|---|---|---|
| opening_h_w | 0.948 ±0.073 | **0.831** | **0.833** | 0.913 | 0.913 |
| iris_d_w | 0.742 ±0.045 | 0.707 | 0.709 | 0.746 | 0.746 |
| iris_d_spacing | 0.369 ±0.018 | **0.389** | **0.389** | 0.381 | 0.381 |
| iris_x_from_outer_w | 0.623 ±0.038 | **0.585** | 0.586 | 0.621 | 0.621 |
| iris_y_from_top_h | 0.500 ±0.049 | **0.551** | **0.551** | 0.508 | 0.508 |
| white_above_w | 0.056 ±0.041 | **0.106** | **0.106** | 0.078 | 0.078 |
| white_below_w | 0.028 ±0.044 | 0.017 | 0.017 | 0.036 | 0.036 |
| white_inner_w | 0.000 ±0.042 | **0.058** | **0.056** | 0.000 | 0.000 |
| white_outer_w | 0.248 ±0.044 | **0.181** | **0.181** | 0.236 | 0.236 |
| arch_w | 0.504 ±0.050 | 0.507 | 0.511 | 0.550 | 0.549 |
| inner_angle_deg | 142.504 ±9.485 | 138.933 | 138.229 | 148.263 | 148.247 |
| outer_angle_deg | 142.178 ±9.962 | **126.543** | **126.969** | 136.036 | 136.204 |
| inner_drop_w | 0.006 ±0.087 | **-0.092** | **-0.090** | 0.015 | 0.019 |
| apex_from_outer_w | 0.516 ±0.070 | 0.568 | 0.570 | 0.524 | 0.524 |

In tolerance: before 11/28, after 28/28. left / right = image left / right (the viewer's); bold = out of band.

### Third girl, front
| metric | target front | before left | before right | after left | after right |
|---|---|---|---|---|---|
| opening_h_w | 0.952 ±0.075 | **0.787** | **0.796** | 0.905 | 0.905 |
| iris_d_w | 0.751 ±0.049 | **0.656** | **0.663** | 0.761 | 0.761 |
| iris_d_spacing | 0.356 ±0.022 | 0.377 | 0.377 | 0.374 | 0.374 |
| iris_x_from_outer_w | 0.619 ±0.048 | **0.565** | **0.571** | 0.623 | 0.623 |
| iris_y_from_top_h | 0.498 ±0.047 | **0.553** | **0.553** | 0.512 | 0.512 |
| white_above_w | 0.038 ±0.048 | **0.108** | **0.109** | 0.071 | 0.071 |
| white_below_w | 0.022 ±0.048 | 0.021 | 0.021 | 0.058 | 0.058 |
| white_inner_w | 0.009 ±0.044 | **0.095** | **0.085** | 0.000 | 0.000 |
| white_outer_w | 0.237 ±0.061 | **0.176** | 0.178 | 0.242 | 0.242 |
| arch_w | 0.509 ±0.059 | 0.540 | 0.547 | 0.464 | 0.465 |
| inner_angle_deg | 142.863 ±10.364 | **130.926** | **132.161** | 147.236 | 147.197 |
| outer_angle_deg | 140.768 ±11.999 | **121.145** | **121.888** | 138.916 | 138.917 |
| inner_drop_w | -0.020 ±0.055 | **-0.077** | **-0.076** | -0.037 | -0.037 |
| apex_from_outer_w | 0.528 ±0.077 | 0.550 | 0.554 | 0.529 | 0.524 |

In tolerance: before 9/28, after 28/28. left / right = image left / right (the viewer's); bold = out of band.

### Auburn girl, oblique (yaw -35, informative)
| metric | target oblique_near | target oblique_far | before left | before right | after left | after right |
|---|---|---|---|---|---|---|
| opening_h_w | 0.987 ±0.035 | 1.775 ±0.035 | **0.879** | **1.256** | **0.921** | **1.408** |
| iris_d_w | 0.680 ±0.035 | 0.950 ±0.035 | **0.623** | **0.797** | 0.647 | **0.859** |
| iris_d_spacing | 0.416 ±0.015 | 0.310 ±0.015 | **0.434** | **0.348** | 0.425 | **0.340** |
| iris_x_from_outer_w | 0.653 ±0.035 | 0.537 ±0.035 | 0.653 | 0.505 | 0.674 | 0.548 |
| iris_y_from_top_h | 0.500 ±0.035 | 0.507 ±0.035 | **0.542** | **0.544** | 0.512 | 0.504 |
| white_above_w | 0.040 ±0.035 | 0.100 ±0.035 | **0.165** | **0.282** | **0.135** | **0.272** |
| white_below_w | 0.033 ±0.035 | 0.050 ±0.035 | **0.072** | **0.150** | **0.097** | **0.184** |
| white_inner_w | 0.007 ±0.035 | 0.000 ±0.035 | 0.030 | **0.084** | 0.000 | 0.000 |
| white_outer_w | 0.313 ±0.035 | 0.062 ±0.035 | **0.165** | **0.101** | 0.304 | **0.117** |
| arch_w | 0.516 ±0.035 | 0.961 ±0.035 | 0.529 | **0.705** | 0.511 | **0.898** |
| inner_angle_deg | 143.475 ±8.000 | 158.878 ±8.000 | 141.714 | **150.707** | 147.357 | **150.120** |
| outer_angle_deg | 142.646 ±8.000 | 160.233 ±8.000 | **88.904** | **150.367** | **132.082** | 154.350 |
| inner_drop_w | -0.007 ±0.035 | -0.050 ±0.035 | **-0.200** | **0.142** | **-0.162** | **0.470** |
| apex_from_outer_w | 0.547 ±0.035 | 0.525 ±0.035 | **0.638** | **0.480** | 0.579 | **0.468** |

In tolerance: before 5/28, after 13/28. left / right = image left / right (the viewer's); bold = out of band.

## Evidence
- `*/eyes_100.jpg`: 100 % eye crops, open, front and 3/4 (T-137 build | T-156 | references), Cycles 8 spp.
- `*/eyes_closed_100.jpg`: 100 % crops, Blink, front (T-137 build | T-156), 8 spp.
- `*/strict.jpg`: strict sheets, Cycles 16 spp.
- `preview.jpg`: the cheap preview run first (4 spp, hair and clothes hidden; open and Blink, one trial before final).

## Not reached by an override, and what it would need
- **H/W is 0.91 / 0.905, not 0.95, and the iris D/W 0.75 / 0.76.** The reference irises are taller than wide (T-150
  traces: D/W 0.74 with only 0.06 + 0.03 W of white at H/W 0.95, about 1.2 : 1); ours are round
  (`felt.round_iris`). A taller opening adds white above / below, a larger iris leaves the D/spacing band (now 0.381
  of max 0.387, and 0.374 of max 0.378). Needs an iris aspect in `face_v3/felt_eye.py`, or wider-set eyes.
- **The outline is in band but not a circle.** The opening is the socket's azimuth / elevation window in the skin
  (`face_v3/socket.py`): a near-vertical inner wall, a flat bottom, a straight lower-outer edge. `lower_curve` and
  `lower_roll_deg` barely move it. Needs a rounded window in `lid_socket_v3` (separate inner / outer corner).
- **Lash.** It turns with the lid and is symmetric about the lid peak, so the liner is as long on the nose side as
  on the outer side. Needs a per-side span / thickness in `face_generic.build_eyes`.
- **Lower-lid stub.** `face.add_blink_lid_seam` reads the lower lid's front edge within 0.25 r of the middle, so
  the shell cannot be removed completely (an empty or off-centre shell fails the build).
- **Oblique (G02) targets: not reached** (13/28). Yaw is not matched to G02 (-35 deg, the eye-crop view), the lens is
  not modelled, and the far eye is too wide (H/W 1.39 vs 1.78).
- Inherited from T-137: folds on the third girl's closed lid; a small upper-shell tip at the outer liner end.

## Question for the Supervisor: boy
Not changed. His references (hero24, val27) show a thick, flat, dark upper-lid band and no separate lashes, and
2.2.0 has exactly that (`lash.thick_m` 2.6 mm, [30,20,18], no strands). A thin liner with outer lashes would move
him away from his references. His closed eye shows no lash line; the closed-eye lash curve lives in
`face_v3/lids.py` and he is `face_generic/2`, so that needs a generator decision, not an override.

## Tests
`python3 pipeline/charsys/tests/test_face_r5.py --blender blender`: 20/20 (14 existing + 6 for the lid yaw: guard,
no spec under `assets/` uses it, overrides touch `face.eyes` only, unchanged without the key, peak shift with it).
No test, threshold or golden changed. Not run: ctest, verify_charsys, face_system_test, expression sheets, pupil
pixels (pupil radius 0.235 -> 0.23 and 0.231 -> 0.229 of the eye radius).

Rebuild: `build_character.py -- --spec <spec> --out <dir> --no-glb --no-compare --override <...>` (auburn: 0.13.0
spec + this override; third: T-126a spec + T-126 hands, hair, dress, materials + T-137 fringe + this override);
sheets: `python3 docs/evaluation/characters/T-137/tools/face_sheets.py <part.json> strict|eyes --out <dir>`.
