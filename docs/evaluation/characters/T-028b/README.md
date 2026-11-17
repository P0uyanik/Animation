# T-028b Girl material regressions: blouse, boots, hair colour

Status: **done, pending Supervisor review.** The three regressions from the Supervisor's review of
`T-028/girl_turnaround_before_after.png` are fixed visually:
- the blouse is matte;
- the boots are warm-brown fleece;
- the hair is auburn again.

The cost is on the swatch sheet: 19 of 30 target rows pass, against 25 for T-028. Following the owner's rule (visual
match first), I am reporting this rather than tuning for the metric. No target or threshold changed. Nothing was
published or approved.

Branch `t-028b-claude-material-fixes`, from `t-028-claude-sheen-fibres` (a6414f0).

## Visual result (judged against the reference sheet first)

`girl_turnaround_before_after.png`:
- top row: the reference next to "before" (T-028 head a6414f0);
- bottom row: the reference next to "after" (this branch);
- 4 views, 640 px, 32 spp + OIDN, `character_neutral/1`.

`closeups_vs_reference.png` shows the reference crop, before and after for the blouse, vest, boots and hair.

| Area | Before (T-028) | After (T-028b) | Still off |
| --- | --- | --- | --- |
| **Blouse** | Glittery white: pale flecks and streaks over a grey speckle | Soft, even matte cotton, as in the reference; the shading reads as cloth | The weave is barely visible at 640 px. The reference shows none either, so I left it subtle. The collar edges still show the T-025/T-026 rolled-edge fuzz |
| **Shorts** (same preset) | Pale streaks | Plain matte sage | — |
| **Boots** | Rusty orange streaks on dark, saturated, orange-red fleece | Warm tan-brown fleece with a soft, even nap and fibres; no streaks | The reference fleece is a little more open and lighter at the cuff. The boot shape (toe bulbs) is geometry and is not part of this task |
| **Vest** | Bouclé fibres (kept), but too pink and saturated | Same bouclé fibres, now in the reference's mauve-brown | The reference vest is a denser, flatter felt with shorter fibres. Ours still reads a little "towel-like" at the close-up |
| **Hair** | Grey-mauve (ΔE00 11.2 back / 8.4 front) | Auburn: ΔE00 **3.1 back / 2.7 front** (T-016 had 5.8 / 7.0) | At the close-up, the auburn leans slightly terracotta and the yarn reads smooth/clay-like. The reference shows fuzzy wool strands. That is hair geometry / groom fibres, outside this task's file area |

## Why the hair had gone grey (item 3)

The calibration was **not** the cause. `character_neutral/1` differs from the T-016 profile only in the key and fill
direction:
- the key moved from 35/45° to 30/40°;
- the fill moved from −50/15° to −20/10°;
- both strengths were renormalised to the same front irradiance.

The cause is the `wool yarn` preset, which the girl's hair uses:
1. **Sheen weight 0.10 → 0.50.** T-016 round 2 set the sheen to 0.10 because a white sheen over the dark auburn yarn
   was "the main cause of the grey lift" (T-016 README: ΔE 4.8 at 0.20, 2.4 at 0.10). T-019's WIP commits (4f18946,
   then f377ccc) rebuilt the preset from an older copy, with `sheen_weight 0.5` and `specular_ior_level 0.42`. That
   silently undid T-016.
2. **The sheen and the silhouette rim layer are white.** Principled's sheen tint is white, and the rim layer (weight
   0.9 on wool yarn) is a Principled with sheen 1.0. Over a dark, saturated albedo, both lift towards grey.
3. **T-028's nap layer** doubled the yarn albedo on clump tips (`value_gain 1.0`), with sheen ×1.8 on the same tips.
   This added lighter, less saturated patches.

### Fix (shared path, no character names)

- **New `surface.sheen_tint` (0..1, default 0, validated) in `materials/builder.py`.** It blends Principled's sheen
  tint from white towards the base colour's hue at full value. The silhouette rim layer's sheen gets the same tint.
  The sheen keeps its light-dependent lift, but stays in hue, as dyed fibres do. With the default of 0, every preset
  without the field renders exactly as before.
- **`wool yarn`:**
  - sheen 0.5 → 0.3 with `sheen_tint` 1.0;
  - nap `value_gain` 1.0 → 0.3, `sheen_gain` 0.8 → 0.5, `roughness_drop` 0.35 → 0.2.

  The specular, fibres and micro relief are unchanged.

## Blouse (item 1)

The cause was T-028's slub/nap layer on `woven cotton`:
- `value_gain` 1.0 doubles a near-white albedo, so it clips;
- `roughness_drop` makes those tips glossier;
- `micro_relief.color_strength` 0.7 adds a ±70% albedo grain at 96/reference.

Together they made the sparkle and the grey speckle.

`woven cotton` now has:
- the nap layer off;
- micro `color_strength` 0.7 → 0.2 and `roughness_variation` 0.38 → 0.15;
- `sheen_tint` 0.6.

The weave bump (fibre kind `weave`) is unchanged, so the cloth keeps a subtle structure without speckle.

## Boots (item 2)

The causes:
- `boot fleece` had nap `value_gain` 1.2 and `fibre_gloss` 0.85. Glossy Principled Hair fibres on clump tips throw
  saturated TRT glints, which showed as the orange streaks.
- Fibre `color_variation` was 0.9 (strands from 10% to 190% value).
- `saturation_compensation` was 1.08.
- The girl's boot colour, (104, 58, 34), was a saturated orange-brown.

Preset changes:
- nap `value_gain` 0.25, `sheen_gain` 0.4, `roughness_drop` 0.15, `fibre_gloss` 0.15;
- fibre `color_variation` 0.4;
- micro `color_strength` 0.45;
- `saturation_compensation` 1.0;
- `sheen_tint` 0.8.

Fibre density and length are unchanged, so the fleece keeps its fuzz.

Girl spec colours (material fields only), set from measured render/reference medians (iteration 2 → 3):

| Field | Before | After |
| --- | --- | --- |
| Boots main | (104, 58, 34) | (132, 88, 68) |
| Boots band | (112, 64, 40) | (138, 94, 74) |

## Vest (item 4)

I kept T-028's felt fibres (the bouclé read is closer to the reference than the smooth T-026 vest) and calmed them:
- fibre `color_variation` 0.8 → 0.45;
- nap `value_gain` 0.8 → 0.4;
- `fibre_gloss` 0.5 → 0.15;
- `sheen_tint` 0.6.

The vest base colour in the spec changes from (150, 94, 96) to (144, 104, 104), which is less saturated. The vest had
measured too pink: saturation 0.42 against the reference's 0.32.

`felt` is also used for the hair flowers, band and boot soles. They look unchanged at turnaround scale.

## Metrics (for information)

### Character colour checks (`colour_checks.json`)

All values are ΔE00 of the render median against the reference median.

| Check | before (T-028) | after (T-028b) |
| --- | ---: | ---: |
| hair_back | 11.16 | **3.14** |
| hair_front | 8.43 | **2.67** |
| blouse_sleeves_front | 2.79 | 3.01 |
| shorts_front / back | 1.24 / 1.50 | 1.22 / 1.30 |
| vest_front / back ¹ | 8.44 / 6.73 | **5.61 / 5.14** |
| boots_front / back ¹ | 11.41 / 10.66 | **1.76 / 2.80** |

¹ **Measurement caveat.** `groom_turnaround.py --ids` gives the material slots a palette that repeats after about 22
slots. For example, `M_garment.boots.main` has the same id colour as `M_hair_flower`, and `M_garment.blouse.main` the
same as `M_garment.vest.main.001`. The generated fibre curves also hide the garment slot. So `measure_colour.py`
reports wrong medians for garments with fibres: its "boots_front" equals the flower median. For the vest and boots I
used `measure_fibre_garments.py` (in this folder) instead. It takes the slot's pixels where its id colour is unique,
plus the fibre pixels (pixels with no known id), inside a vertical band that only that garment occupies. The
`groom_turnaround.py` palette should get unique ids. That file is outside my area (`groom*`), so I did not change it.

The blouse median from `measure_colour.py` may include a few vest pixels for the same reason. Visually, the blouse is
clearly closer to the reference.

### Swatch sheet (`metrics_after.json`; `metrics_before.json` is T-028's final sheet)

The setup is the same as T-028: 480 × 576, 8 spp + OIDN, `character_neutral/1`, close LOD.

| Preset | fuzz T-028 | fuzz T-028b | sheen T-028 | sheen T-028b | sat % T-028 | sat % T-028b |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| felt | 3.22 ✓ | 2.92 ✗ | 1.06 ✗ | 1.05 ✗ | 99.3 ✓ | 104 ✓ |
| wool yarn | 5.67 ✓ | 5.17 ✓ | 1.05 ✗ | 1.04 ✗ | 93.5 ✓ | 98.4 ✓ |
| fleece | 4.44 ✓ | 4.42 ✓ | 1.06 ✗ | 1.06 ✗ | 104 ✓ | 104 ✓ |
| cotton knit | 4.38 ✓ | 4.36 ✓ | 1.09 ✓ | 1.09 ✓ | 101 ✓ | 101 ✓ |
| woven cotton | 3.82 ✓ | 0.90 ✗ | 1.09 ✓ | 1.01 ✗ | 90.5 ✓ | 93.5 ✓ |
| denim | 2.91 ✗ | 2.91 ✗ | 1.11 ✓ | 1.11 ✓ | 83.1 ✓ | 83.1 ✓ |
| felt hair | 5.77 ✓ | 5.77 ✓ | 1.10 ✓ | 1.097 ✗ ² | 92.3 ✓ | 92.3 ✓ |
| boot fleece | 3.19 ✓ | 2.41 ✗ | 1.09 ✓ | 1.05 ✗ | 103 ✓ | 100 ✓ |
| buttons/plastic | 0.23 ✓ | 0.23 ✓ | (1.03) | (1.03) | 87.1 ✓ | 87.1 ✓ |
| glasses/acrylic | 1.49 ✓ | 1.49 ✓ | (1.01) | (1.01) | (39.7) | (39.7) |
| skin-felt | 0.49 ✓ | 0.49 ✓ | 1.01 ✗ | 1.01 ✗ | 97.1 ✓ | 97.1 ✓ |

Values in brackets have no target.

² `felt hair` is unchanged by this task. Its sheen patches are 1.104 / 1.095 / 1.097 against T-028's 1.099 / 1.103 /
1.112. The fibre distribution seed is shared and the fibre node group is regenerated per sheet, so this is render
noise at the 1.10 edge.

**Reading the metric losses.** The woven-cotton and boot-fleece rows passed in T-028 only because of the speckle and
streak layer that the Supervisor rejected:
- woven cotton fuzz 0.9 and sheen 1.01 is what a soft, matte, even cotton measures in this harness;
- boot fleece fuzz 2.41 and sheen 1.05 is what the calmer fleece measures.

Meeting both the reference look and these ranges needs a light-dependent fine structure, as T-028 "Remaining" already
said, not an albedo layer. `measure_swatches.py` exits 1, as it did for T-026 and T-028.

## Render budget

- **Iteration renders: 3 of 4.**
  1. Presets + `sheen_tint`: turnaround and boots, vest and hair close-ups.
  2. Calmer felt fibres, with `--ids` for measurement: turnaround and vest close-up.
  3. Measured boot and vest colours: turnaround and boots and vest close-ups.
- **Finals:**
  - before (worktree at a6414f0) and after turnarounds with boots, vest and hair close-ups;
  - one swatch sheet.

Times (CPU, bpy 5.3.0):

| Render | before | after |
| --- | ---: | ---: |
| Girl build | 55.5 s | 56.1 s |
| Turnaround views, 640 px, 32 spp | 9.8–12.0 s | 9.8–12.0 s |
| Boots close-up | 29.0 s | 32.1 s |
| Vest close-up | 49.9 s | 48.0 s |
| Hair close-up | 29.0 s | 28.8 s |

## Checks

| Command | Result |
| --- | --- |
| `python3 pipeline/charsys/tests/test_material_presets.py` | PASS 54/54 (test unchanged) |
| `python3 tests/garment_generic_test.py --blender <blender> --out <dir>` | PASS (rc 0), worst pose clearance 0.0005 m |
| `blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>` | PASS (rc 0, no FAIL lines) |
| `python3 pipeline/charsys/verify_charsys.py --blender <blender> --out <dir>` | PASS: build, geometry fingerprint ok (boy byte-identical), asset store, reuse |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>` | PASS 8/8 |

`git diff a6414f0 -- assets/characters/boy_yellow_hoodie tests/data docs/references` is empty. All `targets` blocks
in `presets.json` are identical to a6414f0. The groom/hair geometry, `face_generic`, the engine and the clips are
untouched. The girl's spec `spec_version` is unchanged (0.7.1). Only material colour fields changed.

## Reproduce

Blender: there is no binary on this host, so a Python 3.13 venv with `bpy==5.3.0` runs behind a `blender` wrapper
that accepts `-b --factory-startup -P <script> -- <args>`.

```bash
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir> --no-glb --no-compare
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend \
  assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> \
  --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --ids \
  --closeup "boots:0:10:0,-0.05,0.12:0.40" --closeup "vest:0:5:0,-0.1,0.55:0.36" --closeup "hair:135:10:0.02,0.06,0.93:0.30"
python3 pipeline/charsys/tools/turnaround_sheet.py assets/characters/girl_auburn_bun_glasses/references/views <renders> <sheet.png> \
  --views sheet30_front:front,sheet30_front_left:front-left,sheet30_left:left,sheet30_back:back --height 640 --tag after
python3 pipeline/charsys/tools/measure_colour.py assets/characters/girl_auburn_bun_glasses/references/colour_checks.json <renders> <out.json>
python3 docs/evaluation/characters/T-028b/measure_fibre_garments.py <renders> <out.json>     # numpy, Pillow, scipy
blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- --out docs/evaluation/characters/T-028b/swatch_sheet.png \
  --metadata docs/evaluation/characters/T-028b/swatches.json --width 480 --height 576 --samples 8 --lighting character_neutral/1 --fibres-lod close
blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- --image docs/evaluation/characters/T-028b/swatch_sheet.png \
  --metadata docs/evaluation/characters/T-028b/swatches.json --out docs/evaluation/characters/T-028b/metrics_after.json
```

## Remaining

- **Hair close-up:** slightly terracotta, and it reads smooth like clay rather than fuzzy wool. The fix would be
  groom-level fibres or yarn geometry (the other agent's hair work), not this material path.
- **Vest:** the fibres are a little long and shaggy for the reference's dense felt. A shorter `length_mm` and a
  higher density on `felt` would be the next step. I didn't try it: it changes every felt use and needs a render.
- **Swatch rows lost** on woven cotton and boot fleece (see above): the metric/look conflict needs an owner decision,
  or a light-dependent fine-structure layer.
- **`groom_turnaround.py --ids` palette collisions** make the garment colour checks unreliable (see the caveat
  above).
