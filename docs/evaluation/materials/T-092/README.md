# T-092: materials, fabric separation and skin warmth (round 2, Phase B)

Branch `t-092-claude-materials`, input `4910b69`. Path B: evaluation only. Nothing is published, approved or
version-bumped (T-094 does that).

## Owner evidence
| file | what |
|---|---|
| `boy_yellow_hoodie_strict.jpg` | T-087 strict sheet: reference \| 2.0.0 (approved) \| 2.0.0 + T-092 candidate. Compare variant (arms down), character_neutral/1, Cycles 16 spp, 360 px |
| `girl_auburn_bun_glasses_strict.jpg` | the same for 0.11.0. A-pose master, as the sheet30 references show (T-087 recipe) |
| `patch_sheet.jpg` | per material: a macro patch and a shot-size patch, before \| after, under neutral and warm light; ΔE00 and seconds per tile |
| `*_preview.jpg` | the cheap first frames (`recipe.py preview`, 2 spp, 120 px) |
| `<character>/` | `recipe.resolved.json`, `sheet.json` (render seconds per column), `log.txt` |
| `patch_metrics.json`, `patches_render.json` | the patch numbers and every tile's render seconds |
| `identity/` | proof that boy 2.0.0 and girl 0.11.0 build identically on the input SHA and on this branch |

## What changed (implemented)
- **New opt-in family `presets/3`** (`pipeline/charsys/materials/presets_r2.json`, self-contained defaults):
  - `hoodie fleece/3`: soft, even fleece;
  - `trouser pile/3`: a quiet, short, dense dark pile;
  - `vest felt/3`: dense, smooth felt, with no nap speckle;
  - `cuff fleece/3`: cream sherpa with long fading fibres;
  - `brushed cotton/3`: a quiet blouse and shorts cloth;
  - `skin-felt/3`: skin-felt/2 plus a redder subsurface, a lower dye-tinted rim sheen, warmer creases, and an
    **occlusion warmth** layer. The warmth is albedo only, and it is warmer and deeper in shadow, under hair and
    glasses, and between the fingers.
- **One uniform fibre halo per fabric preset**, through the existing `PS Shared Surface Fibres/1` group. Colour and
  lean variation are low, with a root and tip fade. There is no new fibre system. The skin halo is the existing rim
  sheen; skin has no fibre curves, as in presets/2.
- **`builder.py`**: presets/3 resolves after presets/1 and presets/2, plus the `skin.warmth` layer, the `preset_family`
  and `is_r2_preset` helpers, and validation.
- **`garments/generator.py`**: one condition. It also accepts presets/3 ids (approved by the Supervisor).
- **Warm judging rig** `character_warm_indoor/1`, in this task's own `materials/r2_lights.json`. It uses the
  neutral geometry with 3800/3200/4200 K lights, normalised to the neutral rig's luminance.
  `render_calibration.json` is unchanged.
- **Candidate overrides** in `assets/characters/*/spec/candidates/T-092/` (written by `make_candidates.py`). They
  change only material keys:
  - boy: skin, hoodie, trousers;
  - girl: skin, vest (base colour 118/82/80), blouse, shorts, boot cuff band (cream 240/222/196).
  The garments list is the approved one with only material keys changed. The materials pin stays `presets/2`.

## Patch results (neutral rig, shot-size, ΔE00 to the reference target; before → after)
| material | ΔE00 | shot fuzz (HF RMS) | seconds macro / shot (before → after) |
|---|---|---|---|
| boy hoodie | 2.82 → 3.55 | 10.9 → 4.4 | 8.9/0.54 → 10.2/0.55 |
| boy trousers | 4.36 → 3.88 | 4.0 → 1.4 | 5.5/0.41 → 4.9/0.45 |
| boy skin (sphere) | 9.10 → 9.00 | 0.41 → 0.42 | 6.5/0.43 → 8.6/0.51 |
| girl vest | 6.50 → 3.07 | 2.0 → 0.6 | 6.6/0.46 → 3.9/0.42 |
| girl blouse | 1.55 → 1.49 | 1.3 → 0.4 | 3.0/0.27 → 3.1/0.31 |
| girl shorts | 5.53 → 5.71 | 0.63 → 0.38 | 3.1/0.26 → 3.0/0.30 |
| girl boot cuff | 34.9 → 4.22 | 0.76 → 1.43 | 9.0/0.59 → 18.6/0.99 |
| girl skin (sphere) | 7.26 → 7.30 | 0.42 → 0.42 | 5.9/0.40 → 8.3/0.45 |

The warm-rig ΔE values are in `patch_metrics.json`. They are high for every material by design: the targets were
taken under neutral light.

The skin warmth acts where light is occluded, so an open sphere barely changes. Judge it on the strict-sheet faces
and hands.

## Render time
| render | seconds |
|---|---|
| patch run, 64 tiles | 231 |
| boy sheet, 2.0.0 column | 374 |
| boy sheet, candidate column | 434 (+16 %) |
| girl sheet, 0.11.0 column | 525 |
| girl sheet, candidate column | 595 (+13 %) |

All renders: CPU, 4 cores, bpy 5.3.0 module (not a Blender binary).

## Tests
- `pipeline/charsys/tests/test_materials_r2.py` (plain Python): 104/104.
- `pipeline/charsys/tests/test_materials_r2_graphs.py` (bpy): 52/52.
  - Golden: `materials/r2_frozen_graphs.json`, written from the input SHA's builder.
  - A one-value mutation of presets.json makes it fail.
- Unchanged and still passing: `test_material_presets` 54/54, `test_skin_presets` 24/24, `test_skin_material` 10/10,
  `tools/tests/test_version_switch.py` 52/52.

## Limitations and open points
- **Hands:** they are only slightly warmer on the strict sheets. The occlusion warmth does not reach the +20 L* limb
  gap from the audit. The base colour was deliberately not changed, because the audit warns that a colour-only fix
  overcorrects the face. The next step is an owner decision: a lower skin albedo, or a stronger warmth.
- **Boot cuff:** the material is now cream fleece with soft fibres. The cuff's tube outline (geometry) is T-093's
  work.
- **Hoodie:** ΔE rises slightly (2.8 → 3.6). The approved base colour is a little more saturated than the
  reference target, and the old noisy texture had lowered the median. The base colour was kept.
- **For T-094:**
  - `tools/version_switch.py` does not know the presets/3 ids yet (the Supervisor has noted this);
  - T-094 must set `generators.materials = presets/3`.
- **Not tested:** the engine export and `run_shot` with the candidates (the task does not ask for them). The ctest
  image regressions are unaffected: no engine or C++ change.
