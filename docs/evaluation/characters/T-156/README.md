# T-156: lashes and eye shape to the T-150 targets (both girls)

> **Owner review of 2026-11-20 (14:43Z relay), status of the five points.** Sheets below are the final renders.
> 1. *Pale flap past the outer corner of the near eye in 3/4 (both girls):* **fixed** (`lids.trim.up_outer_deg` 44, liner span 41).
> 2. *Creases under the auburn lower lid:* **reduced.** The lower-lid shell is cut to a speck (trims 0.4 deg) and the
>    skin shelf under the eye is lower and without its pleat (`socket.cover_softness` 0.3 -> 0.12); a soft ledge remains.
> 3. *Lash colour / fullness:* **changed** to warm dark brown, a fuller liner and six outer lashes on both girls
>    (auburn [70,40,28], 1.9 mm; third girl [60,37,30], 1.7 mm). Boy unchanged.
> 4. *Pale pink teardrop above the closed lids,* and 5. *the third girl's shape above the closed eyes:* **fixed, both
>    girls** (second pass, 18:29Z relay: `face_v3/socket.py` added to the write-set). New opt-in `socket.closed_fill`:
>    on a full blink the skin itself closes the socket opening, so the closed eye is smooth skin with the lash arc on
>    it, as in `f14_e10_eyes_closed_calm`. No teardrop, no bowl or fold, and no lid dome or dome edge on the auburn girl.

Input `t-137-claude-faces @ 321466a`; targets `docs/evaluation/characters/T-150/targets.json` (main `e2c8904`).
Blender: bpy 5.3 behind `tools/bpy_blender.py`. Overrides only; no current version, spec or published file changed.
Scope follows the Supervisor's notes of 06:41 / 06:50 / 07:04Z (lash first, lower-lid crease, boy; fringe untouched).

**Result.** Lash: warm dark brown liner with six short separate lashes at the outer corner (both girls); the closed
eye is smooth skin with a thin lash arc (`socket.closed_fill`). Shape: every T-150 front metric is inside its band on both eyes (auburn 11/28 -> 28/28,
third girl 9/28 -> 28/28). Blink: 0 sclera / iris pixels on both girls. **Boy: not changed, see the question below.**

## What changed
`auburn/girl_auburn_bun_glasses.eyes.override.json`, `third/girl_white_hair_blue_dress.eyes.override.json`
(`face.eyes` only; they replace the T-137 F1a / F1b eye overrides; the F1b fringe override is used as it is).

| key (`face.eyes.`) | auburn T-137 -> T-156 | third T-137 -> T-156 | effect |
|---|---|---|---|
| `lash.thick_m`, `flare`, `srgb` | 3.4 -> 1.9 mm, 0.6 -> 1.0, [96,58,42] -> [70,40,28] | 3.4 -> 1.7 mm, 0.6 -> 1.0, [70,44,36] -> [60,37,30] | warm dark brown liner, thinner than the band |
| `lash.span_deg`, `lash.strands` | 52 -> 41; 6 lashes at 22-39 deg, 3-4.8 mm, 1.3 mm wide | 56 -> 41; same | liner reaches the outer corner; short outer lashes |
| `lash.lower_strands.count` | 0 (as F1a) | 3 -> 0 | they showed as two dark specks |
| `lids.trim.lo_outer_deg` / `lo_inner_deg` | 62 / none -> 0.4 / 0.4 | same | lower lid shell (the pale crease) cut to the speck the blink seam needs |
| `lids.closed_fit.lash_curve` | none -> as F1b, span [-0.45, 0.62] | span -> [-0.45, 0.62] | closed-eye lash curve |
| `socket.corner_deg` | 42 -> 37 | 46 -> 36 | narrower opening (width, H/W, D/W, no inner white) |
| `lids.upper_edge_deg` / `lower_edge_deg` | 38 / -36 -> 34.5 / -41.5 | 38 / -36 -> 33.5 / -39 | arch, lower lid, white above |
| `iris.radius` (`pupil` = half) | 0.47 -> 0.46 | 0.462 -> 0.458 | D/spacing |
| `lids.upper_roll_deg` | -18 -> 6 | -18 -> 1 | corners level, outer corner angle |
| `lids.upper_yaw_deg` (new, opt-in) | 8 | 8 | lid peak over the middle of the opening |
| `lids.lower_curve`, `lids.trim.up_outer_deg` | 0.15 -> 0.6, 72 -> 44 | same | lower corners; no upper shell flap past the outer corner |
| `lids.closed_fit.shell_subsurface`, `shell_occlusion_tint` (new, opt-in) | 0.0, 0.5 | 0.0, 0.5 | closed lid tone close to the skin |
| `lids.closed_fit.sink_m` (new, opt-in) | not set | 0.005 | closed upper shell under the socket skin |
| `socket.closed_fill` (new, opt-in) | `extra_m` 0, 12 smoothing passes, blend 10 deg | `extra_m` -6 mm, 12 passes | the skin closes the opening on a full blink |
| `lids.closed_fit.lash_curve.out_m` | 2 -> 8 mm | 2 -> 3 mm | closed lash arc in front of the closed skin |
| `socket.cover_softness` | 0.3 -> 0.12 | 0.3 (unchanged) | lower skin shelf under the eye |

The lash keys are separable: drop the `lash` block to keep the T-137 lash on the new shape.

Shared code, opt-in: `pipeline/charsys/face_v3/lids.py` `lid_yaw` (`lids.upper_yaw_deg` / `lower_yaw_deg`). A lid
edge is close to a circle about the eye's forward axis, so its peak sat over the iris, at 0.63 W from the outer
corner (band <= 0.586) whatever the roll (tried -6 .. +14 deg): the nose-side skin makes the opening narrower on the
inner side. The yaw turns the lid and its lash about the eye's vertical axis; the eyeball does not move. Key
absent = the previous return value, bit for bit (unit test).
Two more opt-ins in `fit_closed_lids` (same file), both absent = unchanged code path (static tests):
`closed_fit.sink_m` pushes the middle of the closed upper shell inwards (weight c^3, upper shell only), so it no
longer comes through the socket skin; `closed_fit.shell_occlusion_tint` scales the occlusion-driven warmth / crease
tints in the lid's copy of the skin material, which tinted the convex shell differently from the concave skin.

`socket.closed_fill` (`face_v3/socket.py` + `lids.py`, opt-in). The skin did not move when a lid closed, so the
closed eye was the carved opening (third girl: a bowl with a fold, her eyeball flattens behind it) or the lid shell
on top of it (auburn: a dome with an edge). With the key set, `lid_socket_v3` stores, per side, the displacement that
takes the opening's skin out to the cover it already has beyond the eye corners (`extra_m` shifts that radius; a
few Laplacian passes), as a point attribute; `fit_closed_lids` adds it to the skin's key of every lid key that
closes fully (Blink, the sided blink, the winks) and removes the attribute. The skin keys get an in-between
(`<key>@75`), which the existing in-between drivers play, so the skin only closes over the last quarter of the
control: a half blink still shows the eye under the lid. Without the key no attribute is written and nothing is read.
Default-path proof: the previous override built before and after this change gives identical vertex and shape-key
data for 201 of 207 meshes, the skin included; the other six (lid shells, ears) also differ between two builds of
the same code and input (build noise, checked by building twice).

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
| opening_h_w | 0.948 ±0.073 | **0.831** | **0.833** | 0.902 | 0.902 |
| iris_d_w | 0.742 ±0.045 | 0.707 | 0.709 | 0.737 | 0.737 |
| iris_d_spacing | 0.369 ±0.018 | **0.389** | **0.389** | 0.381 | 0.381 |
| iris_x_from_outer_w | 0.623 ±0.038 | **0.585** | 0.586 | 0.625 | 0.625 |
| iris_y_from_top_h | 0.500 ±0.049 | **0.551** | **0.551** | 0.508 | 0.508 |
| white_above_w | 0.056 ±0.041 | **0.106** | **0.106** | 0.080 | 0.080 |
| white_below_w | 0.028 ±0.044 | 0.017 | 0.017 | 0.035 | 0.035 |
| white_inner_w | 0.000 ±0.042 | **0.058** | **0.056** | 0.000 | 0.000 |
| white_outer_w | 0.248 ±0.044 | **0.181** | **0.181** | 0.246 | 0.246 |
| arch_w | 0.504 ±0.050 | 0.507 | 0.511 | 0.540 | 0.541 |
| inner_angle_deg | 142.504 ±9.485 | 138.933 | 138.229 | 148.016 | 147.998 |
| outer_angle_deg | 142.178 ±9.962 | **126.543** | **126.969** | 137.294 | 137.294 |
| inner_drop_w | 0.006 ±0.087 | **-0.092** | **-0.090** | 0.022 | 0.024 |
| apex_from_outer_w | 0.516 ±0.070 | 0.568 | 0.570 | 0.528 | 0.528 |

In tolerance: before 11/28, after 28/28. left / right = image left / right (the viewer's); bold = out of band.

### Third girl, front
| metric | target front | before left | before right | after left | after right |
|---|---|---|---|---|---|
| opening_h_w | 0.952 ±0.075 | **0.787** | **0.796** | 0.902 | 0.902 |
| iris_d_w | 0.751 ±0.049 | **0.656** | **0.663** | 0.758 | 0.758 |
| iris_d_spacing | 0.356 ±0.022 | 0.377 | 0.377 | 0.374 | 0.374 |
| iris_x_from_outer_w | 0.619 ±0.048 | **0.565** | **0.571** | 0.624 | 0.624 |
| iris_y_from_top_h | 0.498 ±0.047 | **0.553** | **0.553** | 0.512 | 0.512 |
| white_above_w | 0.038 ±0.048 | **0.108** | **0.109** | 0.070 | 0.070 |
| white_below_w | 0.022 ±0.048 | 0.021 | 0.021 | 0.058 | 0.058 |
| white_inner_w | 0.009 ±0.044 | **0.095** | **0.085** | 0.000 | 0.000 |
| white_outer_w | 0.237 ±0.061 | **0.176** | 0.178 | 0.245 | 0.245 |
| arch_w | 0.509 ±0.059 | 0.540 | 0.547 | 0.460 | 0.461 |
| inner_angle_deg | 142.863 ±10.364 | **130.926** | **132.161** | 147.142 | 147.102 |
| outer_angle_deg | 140.768 ±11.999 | **121.145** | **121.888** | 138.345 | 138.345 |
| inner_drop_w | -0.020 ±0.055 | **-0.077** | **-0.076** | -0.032 | -0.031 |
| apex_from_outer_w | 0.528 ±0.077 | 0.550 | 0.554 | 0.530 | 0.526 |

In tolerance: before 9/28, after 28/28. left / right = image left / right (the viewer's); bold = out of band.

### Auburn girl, oblique (yaw -35, informative)
| metric | target oblique_near | target oblique_far | before left | before right | after left | after right |
|---|---|---|---|---|---|---|
| opening_h_w | 0.987 ±0.035 | 1.775 ±0.035 | **0.879** | **1.256** | **0.908** | **1.401** |
| iris_d_w | 0.680 ±0.035 | 0.950 ±0.035 | **0.623** | **0.797** | **0.634** | **0.855** |
| iris_d_spacing | 0.416 ±0.015 | 0.310 ±0.015 | **0.434** | **0.348** | 0.425 | **0.340** |
| iris_x_from_outer_w | 0.653 ±0.035 | 0.537 ±0.035 | 0.653 | 0.505 | 0.681 | 0.550 |
| iris_y_from_top_h | 0.500 ±0.035 | 0.507 ±0.035 | **0.542** | **0.544** | 0.512 | 0.504 |
| white_above_w | 0.040 ±0.035 | 0.100 ±0.035 | **0.165** | **0.282** | **0.132** | **0.251** |
| white_below_w | 0.033 ±0.035 | 0.050 ±0.035 | **0.072** | **0.150** | **0.095** | **0.184** |
| white_inner_w | 0.007 ±0.035 | 0.000 ±0.035 | 0.030 | **0.084** | 0.000 | 0.000 |
| white_outer_w | 0.313 ±0.035 | 0.062 ±0.035 | **0.165** | **0.101** | 0.312 | **0.116** |
| arch_w | 0.516 ±0.035 | 0.961 ±0.035 | 0.529 | **0.705** | 0.502 | **0.881** |
| inner_angle_deg | 143.475 ±8.000 | 158.878 ±8.000 | 141.714 | **150.707** | 147.180 | **149.635** |
| outer_angle_deg | 142.646 ±8.000 | 160.233 ±8.000 | **88.904** | **150.367** | **131.918** | 154.226 |
| inner_drop_w | -0.007 ±0.035 | -0.050 ±0.035 | **-0.200** | **0.142** | **-0.158** | **0.483** |
| apex_from_outer_w | 0.547 ±0.035 | 0.525 ±0.035 | **0.638** | **0.480** | **0.586** | **0.452** |

In tolerance: before 5/28, after 11/28. left / right = image left / right (the viewer's); bold = out of band.

## Evidence
- `*/eyes_100.jpg`: 100 % eye crops, open, front and 3/4 (T-137 build, T-156, references), Cycles 8 spp.
- `*/eyes_closed_100.jpg`: 100 % crops, Blink, front (top T-137 build, bottom T-156), 8 spp.
- `*/strict.jpg`: strict sheets, Cycles 16 spp.
- `preview.jpg`: the cheap previews of the final builds (4 spp, hair and clothes hidden; top open, bottom Blink; front and 3/4).

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
  the shell cannot be removed completely (an empty or off-centre shell fails the build); 0.4 deg leaves a speck.
- **Ledge under the auburn lower lid (review point 2).** Reduced, not gone: the skin has to come out over the
  eyeball below the opening. `cover_softness` 0.12 takes the pleat out; lower values were not tried.
- **Closed fill.** The skin closes over the last quarter of the Blink control, not as a wipe with the lid edge. The
  auburn eyeball does not flatten, so her closed skin sits at the lid cover radius (a soft mound, lash arc 8 mm out);
  with a lower mound a speck of eyeball showed at the outer corners (182 px at `extra_m` -1.5 mm, 7 px now).
  New skin keys (`Blink`, `Blink.L/R`, the winks and their `@75`) are added to `body_skin`, so the candidate's
  shape-key list differs from the published versions'. Squint / Laugh / Smile do not close fully and are unchanged.
- **Lashes** are flat separate strands and read slightly comb-like at 100 %.
- **Oblique (G02) targets: not reached** (11/28). Yaw is not matched to G02 (-35 deg, the eye-crop view), the lens is
  not modelled, and the far eye is too wide.
- Inherited from T-137: the lid-patch tone edge on the closed lids.

## Question for the Supervisor: boy
Not changed. His references (hero24, val27) show a thick, flat, dark upper-lid band and no separate lashes, and
2.2.0 has exactly that (`lash.thick_m` 2.6 mm, [30,20,18], no strands). A thin liner with outer lashes would move
him away from his references. His closed eye shows no lash line; the closed-eye lash curve lives in
`face_v3/lids.py` and he is `face_generic/2`, so that needs a generator decision, not an override.

`python3 pipeline/charsys/tests/test_face_r5.py --blender blender`: 24/24 (14 existing + 10 for the opt-ins: guards,
no spec under `assets/` uses lid yaw, `sink_m`, `shell_occlusion_tint` or `closed_fill`, overrides touch `face.eyes` only,
unchanged without the keys, peak shift with the yaw).
No test, threshold or golden changed. Not run: ctest, verify_charsys, face_system_test, expression sheets, pupil
pixels (pupil radius 0.235 -> 0.23 and 0.231 -> 0.229 of the eye radius).

Rebuild: `build_character.py -- --spec <spec> --out <dir> --no-glb --no-compare --override <...>` (auburn: 0.13.0
spec + this override; third: T-126a spec + T-126 hands, hair, dress, materials + T-137 fringe + this override);
sheets: `python3 docs/evaluation/characters/T-137/tools/face_sheets.py <part.json> strict|eyes --out <dir>`.
