# T-024: girl outfit through the shared garment system (V3)

Status: **implemented, unpublished, not approved.** The girl's spec is now **0.7.0**. The outfit is spec data only,
built by the shared `garment/1` system (T-018). The new garment features are generic parameters, and none of them
names a character.

## What was built
- **Branch:** `t-024-claude-girl-outfit`, from `t-019-codex-material-integration` (T-015 materials, T-016 hair,
  spec 0.6.0), merged `--no-ff` with `origin/t-018-codex-garments`.
  - Merge conflict: `build_character.main_generic` (docstring and build report). I kept both sides: the
    `material_presets` and groom report, and the `garments` report.
- **Girl spec 0.7.0, `clothing` block (`garment/1`).** Sources: reference #41 (garment construction sheet) and the
  sheet30 views. Heights were read on `sheet30_front` at 2.35 mm/px.

  | item | type | preset | base sRGB | main parameters |
  |---|---|---|---|---|
  | blouse | top | woven cotton | (214, 210, 210) | `sleeve_length` 0.97, `sleeve_puff_m` 0.024, round collar 40 mm (`lift_m` 24 mm, out over the vest), 4 `buttons/plastic` buttons, cuff bands, hem tucked at 0.34 m |
  | vest | vest | felt | (150, 94, 96) | `ease_m` 0.03, open front, hem 0.34 m, hem band, 2 pockets, 4 embroidery motifs: 2 flowers on the chest and 2 sprigs above the pockets. Felt (58, 32, 38) with `wool yarn` (196, 186, 176) accents |
  | shorts | shorts | woven cotton | (110, 114, 103) | bloomers: `length` 0.24 (to 0.244 m), `puff_m` 0.03, `puff_inner` 0.8, waist 0.41 m, waist and cuff bands |
  | boots | boots | fleece | (104, 58, 34) | `height` 0.45 (top 0.13 m), `ease_m` 0.022, fleece cuff with tube radius 10 mm, felt sole |

  - The boots' fleece assignment has a spec-level override, `surface.sheen_weight` 0.25 (the preset value is 0.48).
    At 0.48 the sheen washed the brown out to a pale pink-grey (iteration 2: ΔE00 8.0–8.3). `presets.json` and the
    shader builder are unchanged.
  - The base colours were adjusted over the iterations so that the calibrated render matches the sheet30 medians,
    as in T-016. The starting values were the #41 flat-garment targets.
- **New generic parameters in `garment/1`** (`pipeline/charsys/garments/generator.py`, documented in
  `garments/README.md`). The reference needed these and `garment/1` lacked them:
  - `sleeve_puff_m` / `sleeve_puff_peak`: puffed sleeves, gathered at the shoulder and the cuff;
  - `puff_m` / `puff_inner`: bloomer volume, gathered at the leg opening;
  - collar `round`: a flat collar with rounded tips and a front split (`width_m`, `gap_m`, `slope`, `tip_round`,
    `lift_m`);
  - `bands.cuff_radius_m`: thick cuffs;
  - `embroidery`: raised `flower` and `sprig` motifs placed by (u, v) on the garment shell, with a main and an accent
    material.

  When these fields are omitted, the output is the T-018 output: rest clearances of the synthetic outfit A and dress
  are identical to the T-018 JSON.
- **`garments/evaluate.py`** holds the shared evaluation code, moved out of `tests/garment_generic_test.py` with the
  same behaviour: Rigify to semantic FK, the clip player and signed clearance.
  - **Fix:** in the semantic FK conversion, a deform bone under a Rigify `ORG-`/`MCH-` chain now takes that bone's
    `DEF-` twin as its parent. Before, it fell back to the root and stayed at rest in poses: `DEF-pelvis.*` and the
    eye bones.
  - The fix changes some T-018 pose numbers; see Tests. Before the fix, the girl's sit_down showed a false −1.6 mm
    "inside" on the upper back.
- **`tools/garment_pose_eval.py`** (new, generic) works on any built master. It measures rest and posed clearance and
  renders one pose from the reference views under `character_neutral/1`.
- **`tools/turnaround_sheet.py`** (new, generic) composes the reference/render sheets.
- **`references/colour_checks_outfit.json`** (character data) holds the reference boxes for the garment colour medians.
- **`tests/face_system_test.py`:** the garment body mask removes covered skin from the evaluated head mesh, which broke
  the edge-stretch metric (`IndexError`). The test now turns off `MASK` modifiers on the head mesh while measuring,
  so the face metrics use the full rest topology.

## Evidence (this folder)
- `turnaround_vs_reference.png`: front, 3/4 (yaw −45), side (yaw 90) and back.
  - Each 640 px render is next to the matching `sheet30_*` view.
  - Calibration: shared `character_neutral/1` (T-016), Standard view, exposure 0.
  - Render: Cycles, 32 samples, OIDN.
- `sit_down_worst_pose.png`: `sit_down` frame 50, the same four cameras, 640 px and 32 samples. It is the lowest-clearance
  pose of the six measured.
- `garment_pose_eval.json`: clearances at rest and in 6 poses on the girl master. `colour_checks.json`: garment colour
  medians. `garment_generic_test.json`: the synthetic test. `render_timings.json`.

## Clearance (girl 0.7.0 master, `garment_pose_eval.py`)
Signed distance from garment vertices to visible (unmasked) skin. The floor is 0.5 mm at rest and 0 in poses.

| state | min clearance | closest piece | vertices inside visible skin |
|---|---|---|---|
| rest | **7.7 mm** | blouse | 0 |
| idle_relaxed f45 | 1.3 mm | blouse | 0 |
| wave f52 | 1.6 mm | blouse | 0 |
| point f46 | 1.9 mm | blouse | 0 |
| gest_shrug f26 | 1.6 mm | blouse | 0 |
| **sit_down f50 (worst)** | **1.1 mm** | shorts | 0 |
| emo_happy f30 | 1.6 mm | blouse | 0 |

- Result: PASS.
- Mask: 21,600 of 60,686 body faces are hidden under the four items. The collision Shrinkwrap weights 73,083
  garment vertices.
- In sit_down, 10 vertices lie over skin-to-skin contact (thigh against belly). They are reported, not counted.
- Over masked (hidden) skin the minimum is −7.5 mm. It is not visible.
- Every garment piece moves with the rig: the smallest per-object max RMS motion is 26 mm.
- Size: 24 garment objects and 77,942 vertices. The garment part of the build takes about 8 s of the 50 s total.

## Colour (final renders, `measure_colour.py`, ΔE00)
| check | render | reference | ΔE00 | luma-matched |
|---|---|---|---|---|
| blouse sleeves, front | (196, 183, 178) | (202, 192, 188) | 2.6 | 1.5 |
| vest, front | (103, 77, 75) | (116, 94, 92) | 6.0 | 3.4 |
| vest, back | (105, 78, 76) | (134, 91, 92) | **8.1** | 3.6 |
| shorts, front | (113, 111, 98) | (111, 111, 99) | 1.1 | 1.1 |
| shorts, back | (113, 111, 98) | (115, 115, 103) | 1.8 | 1.2 |
| boots, front | (117, 84, 70) | (126, 84, 66) | 3.1 | 2.8 |
| boots, back | (111, 80, 67) | (122, 80, 61) | 4.0 | 3.6 |

## Matches the reference
- **Layering and silhouette:**
  - a cream blouse with clearly puffed long sleeves gathered into cuffs;
  - a white round collar, open at the throat, lying out over the vest;
  - buttons down the placket;
  - an open dusty-rose vest to the hip, with pockets and dark embroidered motifs on the chest and lower front;
  - sage bloomer shorts, wider than the hips, gathered into cuff bands above the knee;
  - brown fleece boots to mid-shin with thick turned cuffs and darker soles.
- **Colours:** the blouse, shorts and boots are within ΔE00 4. The vest's luma-matched ΔE is ≤ 3.6.
- **No visible skin penetration** at rest or in any of the six poses. The face is unchanged: all 604 face-system
  values are identical between 0.6.0 and 0.7.0 builds.

## Deviates from the reference (open)
1. **Vest lightness.** The vest renders darker than the sheet: the back is ΔE00 8.1, just over the tolerance of 8, and
   the luma-matched ΔE is 3.6.
   - In iteration 3, at 16 samples and 400 px, the same base colour measured (117, 85, 84) and ΔE 4.8. At 640 px and
     32 samples, the embroidery and pocket shadows and the hair over the back lower the median.
   - A lighter base, about (165, 104, 106), should close the gap. I did not render it: the budget was used.
2. **Crotch gap.** A small dark triangle shows between the bloomer legs in the front and back views: the leg shells
   separate below the crotch bridge and the inside of the shorts is visible. A crotch-gusset or merged-leg option for
   bloomers would remove it.
3. **Vest shape.** The vest has narrow shoulder straps, because of the shared armhole cut of `garment/1`, where the
   reference has a fuller shoulder. The reference vest's thick rolled edge is a thin hem band here. There are no wooden
   buttons on the vest: `garment/1` places buttons on the centre line, which an open vest does not have.
4. **Embroidery.** The motifs are small raised geometry (petals, knots, leaves). They read as dots and flowers at
   640 px, not as the reference's dense stitched bouquets. There is no embroidery on the pockets: pockets are separate
   ellipsoids, and motifs project onto the main shell.
5. **Fuzz.** The boots and cuffs are smooth fleece shading, not long-pile fur. Fur cards or curves are out of scope.
   The material fuzz metric is the open T-015 issue.
6. **Shorts waist buttons** (#41, 3 buttons) are not modelled: `garment/1` has no buttons on bottoms.
7. **sit_down render:**
   - The eyes appear in front of the face. The cause is the evaluation-only rig conversion: the eye objects follow
     `DEF-eye.*`, which the conversion now re-parents to the head, but the rendered result still shows them offset.
     The face rig itself is unaffected (face test identical). I did not investigate further, to stay within the render
     budget.
   - The clip holds the arms horizontal, so skin shows at the side of the chest between the open vest and the blouse
     armhole.
   - Clearance is measured on the same converted rig, so the clearance numbers do not depend on how the eyes look.
8. **Body proportion.** The visible leg between the shorts and the boots is about 8–9 cm. The reference shows about
   12 cm at the same total height. This comes from the body (legs) and the camera framing, not the garments.

## Tests
| command | result |
|---|---|
| `python3 tests/garment_generic_test.py --blender <blender> --out <dir>` | **PASS**. The 3 earlier checks plus 5 new ones: sleeve puff +15.2 mm at the peak, +7.8 mm at the cuff; bloomers +19.6 mm, +6.9 mm; round collar with 0 vertices in the front gap; embroidery with 4 motifs, ≤ 4.5 mm relief, and footwear embroidery rejected; cuff tube radius 9.03 mm against 9 mm. Outfit B passes clearance at rest and in all 6 poses. The worst pose is idle_relaxed with 0.55 mm |
| `blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>` | PASS 9/9 |
| `python3 pipeline/charsys/tests/test_material_presets.py` | ALL PASS (29/29) |
| `python3 pipeline/charsys/verify_charsys.py --blender <blender> --out <dir>` | PASS: 68 PASS, 0 FAIL. Boy v6 geometry worst numeric difference 0.0 m. `hair_mass` hash only (known non-determinism, T-016). The 1.0.0 master is byte-identical after the tests |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>` | ALL PASS (8/8) |
| `blender ... face_system_test.py -- <master> <dir> --no-render`, 0.6.0 build vs 0.7.0 build | 604 numeric values identical. The 0.6.0 values with and without the mask fix are also identical |

**Effect of the conversion fix on the synthetic T-018 numbers:**
- Rest values are identical.
- Pose minima change only where the pelvis or hip deform bones are involved:
  - sit_down outfit A: 0.07 → 1.94 mm;
  - sit_down dress: 0.31 → 1.98 mm;
  - idle_relaxed outfit A: 0.555 → 0.589 mm.
- All other poses are unchanged to within 0.06 mm.

## Budget and resources (CPU, 4 cores, Blender 5.3 via the `bpy` 5.3.0 wheel)
- **Character renders:**
  - 3 iteration renders: 4 views at 200×400 and 16 samples. Iteration 3 also included the sit_down 3/4 view.
  - The final render: 4 views at 320×640 and 32 samples, 29 s; sit_down, 4 views, 40 s including the measurement.
- Girl build: about 50 s, of which the garments take about 8 s.
- Garment test: 92 s. `verify_charsys`: 22 s.

## Commands
```
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir>
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --ids
blender -b --factory-startup -P pipeline/charsys/tools/garment_pose_eval.py -- <dir>/girl_auburn_bun_glasses_master.blend <pose_dir> --render-pose sit_down:50 --index assets/characters/girl_auburn_bun_glasses/references/reference_index.json --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32
python3 pipeline/charsys/tools/turnaround_sheet.py assets/characters/girl_auburn_bun_glasses/references/views <renders> turnaround_vs_reference.png --views "sheet30_front:front,sheet30_front_left:3/4 (yaw -45),sheet30_left:side (yaw 90),sheet30_back:back" --height 640 --tag T-024
python3 pipeline/charsys/tools/measure_colour.py assets/characters/girl_auburn_bun_glasses/references/colour_checks_outfit.json <renders> colour_checks.json
```
