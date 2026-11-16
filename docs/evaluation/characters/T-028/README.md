# T-028 Sheen layer, garment fibres, boot fleece

Status: **partly reached.**

- **Sheen:** passes on 5 of 9 presets (T-026: 0 of 9): cotton knit, woven cotton, denim, felt hair and boot fleece.
  Felt, fleece, wool yarn and skin-felt still fail.
- **Garment fibres:** bound generically in `garment/1`. The girl's boots use `boot fleece`; its fuzz is 3.19 (≥ 3, PASS).
- **Fuzz:** cotton knit and woven cotton reach target. Denim reaches 2.91, 3% short.
- **Visual cost:** at target strength the layer brings visible artefacts on the girl (see "Visual assessment"). I am
  reporting this rather than hiding it.

No VISUAL_TARGET value or test threshold changed: the `targets` blocks in `presets.json` are byte-identical. Nothing
was published or approved. The boy has no garment/1 clothing and no material opt-in, so he is unaffected (see Checks).

## What changed (shared code only, no character names)

### 1. Mid-scale nap/clump highlight layer (`pipeline/charsys/materials/builder.py`, `presets.json`)

The new preset section is `nap`. Its defaults are off, so presets without a `nap` block render exactly as before.
Fields: `scale_per_reference`, `detail`, `roughness`, `distortion`, `threshold`, `softness`, `anisotropy` (3),
`value_gain`, `value_shadow`, `sheen_gain`, `roughness_drop`, `fibre_gloss`, `bump_strength`, `distance_fraction`.
`validate_library` checks them all.

How the layer works:
- **Mask.** A reference-scaled noise, stretched per axis into streaks along the nap, passes through a smoothstep
  window (`threshold ± softness`). The result is a sparse 0..1 clump-tip mask.
- **Surface shader.** On a clump tip:
  - the albedo is lifted by `value_gain`;
  - the Principled sheen weight grows by `sheen_gain`;
  - the roughness drops by `roughness_drop`, so the tip is glossier;
  - an optional broad bump can be added.
- **Fibres.** The generated fibres evaluate the same mask, because the Curves object shares its surface's
  transform and therefore its object coordinates:
  - they receive the same albedo gain;
  - their Principled Hair roughness falls by `fibre_gloss` (fully on a clump, by half elsewhere), so clump fibres
    throw strand-shaped glints.

**Reference scaling for fibres.** Fibre length and density are authored at the library reference (0.256 m → H).
`add_fibres_geometry` now scales length × k and density / k², where k = `reference_size_m` / 0.256. The swatch sheet
uses k = 1, so it is unchanged by this rule.

### 2. Garment fibres (`pipeline/charsys/garments/generator.py`, README)

- Each garment material stores its resolved assignment (`ps_material_assignment`).
- `build()` calls the new `add_fibres(piece, clothing.fibres_lod)` for every piece. It attaches the shared group
  wherever the piece's preset enables fibres.
- The fibre object:
  - is parented to its piece with an identity transform, so it follows the rig and the collision;
  - is reported per item;
  - is hidden together with its piece by `set_active_items`;
  - is never part of the returned garment list. The engine export takes meshes only.
- `clothing.fibres_lod` (`close` | `wide` | `off`) is validated.
- `boot fleece` is now an allowed garment preset.

### 3. Girl spec

The boots' `material` and `materials.band` now use `boot fleece` instead of `fleece`. Colours, `reference_size_m` and
the existing `sheen_weight 0.25` override are unchanged.

### 4. Fuzz tuning (presets)

| Preset | Change |
| --- | --- |
| boot fleece | Density 26 → 36 fibres/cm², fibre colour variation 0.8 → 0.9, micro albedo 0.72 → 0.9 |
| cotton knit | Density 8 → 16, colour variation 0.25 → 0.5, micro relief scale 40 → 80, micro albedo 0.55 → 0.7 |
| woven cotton | Micro relief scale 40 → 96 (a 2.7 px pitch, inside VISUAL_TARGET's 1.5–4 px weave pitch), micro albedo 0.54 → 0.7 |
| denim | Micro relief scale 40 → 96, micro albedo 0.9 → 0.95 |

Woven cotton and denim keep `fibres.enabled = false`, as `test_material_presets` requires.

## Metrics (swatch sheet, 480 × 576 per preset, 8 spp + OIDN, `character_neutral/1`, close LOD)

`metrics_before.json` is the T-026 final sheet: the same pipeline, without this task's changes.
`metrics_after.json` and `swatch_sheet.png` are the final sheet. The rule is VISUAL_TARGET step 3 (3 patches, median),
as in T-026.

| Preset | fuzz before | fuzz after | sheen P90/P50 before | sheen after (patches) | sheen target | saturation % after |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| felt | 3.24 ✓ | 3.22 ✓ | 1.045 ✗ | 1.059 ✗ (1.059 / 1.064 / 1.056) | 1.08–1.22 | 99 ✓ |
| wool yarn | 5.25 ✓ | 5.67 ✓ | 1.039 ✗ | 1.051 ✗ (1.064 / 1.051 / 1.047) | 1.10–1.28 | 94 ✓ |
| fleece | 4.03 ✓ | 4.44 ✓ | 1.040 ✗ | 1.061 ✗ (1.061 / 1.050 / 1.065) | 1.08–1.22 | 104 ✓ |
| cotton knit | 2.51 ✗ | **4.38 ✓** | 1.031 ✗ | **1.090 ✓** (1.090 / 1.063 / 1.115) | 1.08–1.22 | 101 ✓ |
| woven cotton | 2.10 ✗ | **3.82 ✓** | 1.032 ✗ | **1.091 ✓** (1.096 / 1.091 / 1.089) | 1.08–1.22 | 91 ✓ |
| denim | 1.98 ✗ | 2.91 ✗ (3% short) | 1.041 ✗ | **1.113 ✓** (1.126 / 1.080 / 1.113) | 1.08–1.22 | 83 ✓ |
| felt hair | 5.55 ✓ | 5.77 ✓ | 1.064 ✗ | **1.103 ✓** (1.099 / 1.103 / 1.112) | 1.10–1.28 | 92 ✓ |
| boot fleece | 2.65 ✗ | **3.19 ✓** | 1.063 ✗ | **1.094 ✓** (1.100 / 1.094 / 1.091) | 1.08–1.22 | 103 ✓ |
| skin-felt | 0.49 ✓ (< 3) | 0.49 ✓ | 1.006 ✗ | 1.006 ✗ (layer off, see below) | 1.12–1.32 | 97 ✓ |
| buttons/plastic | 0.23 ✓ | 0.23 ✓ | — | — | — | 87 ✓ |
| glasses/acrylic | 1.52 ✓ | 1.49 ✓ | — | — | — | — |

Rows passing: 17/30 before, **25/30** after. Presets passing every row: 2/11 before, **6/11** after (cotton knit, woven
cotton, felt hair, boot fleece, buttons/plastic, glasses/acrylic; denim fails only on fuzz). `measure_swatches.py`
still exits 1 because the aggregate fails.

## How the values were chosen (budget: 4 iteration renders, all used)

The iteration sheets were rendered through a scratch driver that injects temporary preset variants into the library.
Measurement used the same `render_swatches.py` / `measure_swatches.py` code.

1. **Iteration 1** (18 swatches): broad clumps at 40–50% coverage, albedo lifted on clumps and darkened between them.
   - Sheen rose only to 1.04–1.07.
   - Woven cotton and skin read as camouflage.
   - Measured relative-luminance σ against P90/P50 confirmed T-026's estimate: P90/P50 ≈ 1 + σ.
2. **Iteration 2** (18): positive-only sparse streaks (~4% coverage). They looked like paint flecks and barely moved
   the metric.
3. **Offline calibration** (no render): synthetic clump fields were applied to the real T-026 sphere and patch crops
   and passed through the exact measurement functions.
   - Cloth needs about 15% coverage, a ~5 px correlation length and a ~+30% display lift.
   - Fine 2–3 px flecks at 6–10% coverage are the cheapest route for low-relief cloth.
   - For skin, every setting that reached 1.12 pushed skin fuzz past its 3/255 ceiling.
4. **Iteration 3** (18): mid-scale clumps at two gains. Cotton knit, woven cotton, denim and boot fleece passed, but
   as bleach-like mottling. Rejected visually.
5. **Iteration 4** (16): clumps with milder albedo plus `fibre_gloss`. Low-relief cloth used fine slub flecks. The
   final presets take exactly one tested variant each (no interpolated values):
   - variant A: felt, fleece, wool yarn, woven cotton;
   - variant B: felt hair, cotton knit, boot fleece, denim.

Felt, fleece and wool yarn stay at the milder setting. The stronger bracket (B) gained only +0.002 to +0.012
(felt 1.060, fleece 1.070, wool yarn 1.063), still failing, at more visible mottling.

### Why skin-felt is not reached

The skin target (1.12–1.32) must be met with fuzz < 3/255. The calibration showed the conflict:
- Fine highlights that reach 1.12 raise skin fuzz to 4–7.
- Mid-scale patches stay at 1.04–1.05, even at a gain that already looks blotchy (iteration 3: 1.044 / 1.051 with
  visible mottling).

The face uses this preset, so the layer stays off for skin. Reaching the skin row would need light-dependent detail,
for example a real fine pore or felt-grain specular map with a sharper lobe. It does not need a painted layer.

## Visual assessment (girl, `girl_turnaround_before_after.png`, `closeups_before_after.png`)

**Better:**
- The boots now carry boot-fleece fibres and read as plush instead of smooth clay. Their fuzz shows at 640 px, which
  T-026 listed as missing.
- The vest's felt fibres read as the bouclé named in the spec description.

**Worse, and I recommend the supervisor review it before this is merged as the girl's look:**
- *Boots:* variant B's clumps show as orange streaks and mottling. The boots also read lighter and more orange than
  the reference boot colour.
- *Blouse and shorts:* woven cotton's slub flecks show as pale sparkle and streaks on the plain blouse and the sage
  shorts.

So the passing sheen rows for woven cotton and boot fleece come with visible noise at character scale. A per-character
softening, for example `overrides.nap.value_gain` in the girl's spec, is possible without code changes. I did not
render it: it would exceed the render budget.

## Render time per frame (CPU, 4 cores, bpy 5.3.0)

| Render | before | after |
| --- | ---: | ---: |
| Swatch, 480 × 576, 8 spp + OIDN (mean of 11) | 1.85 s (T-026) | 3.37 s |
| Girl turnaround view, 320 × 640, 32 spp (mean of 4) | 5.72 s | 9.79 s |
| Boots close-up, 640 × 640, 32 spp | 13.3 s | 26.9 s |
| Vest close-up, 640 × 640, 32 spp | 30.5 s | 45.4 s |
| Girl build, `--no-glb --no-compare` | 48.6 s | 53.7 s |

The girl now carries 779,535 garment fibre curves:
- boot shells 379k (k = 0.586 → 105 fibres/cm²);
- boot cuffs and lining 182k;
- soles 72k;
- vest and pockets 81k;
- embroidery 65k (k = 0.195: 0.8 mm fibres, below a pixel at 640 px).

`clothing.fibres_lod: "wide"` reduces all of them to a quarter.

Timings are in `swatches.json` (`render_s`), `turnaround_timings_before.json` and `turnaround_timings_after.json`.

## Evidence

| File | What |
| --- | --- |
| `metrics_before.json` | T-026 final metrics |
| `metrics_after.json`, `swatch_sheet.png`, `swatches.json` | Final swatch sheet |
| `girl_turnaround_before_after.png` | Reference next to before (T-026 head 644befd), then reference next to after. 4 views, 640 px, 32 spp + OIDN, the same `character_neutral/1` calibration (unchanged by this task) |
| `closeups_before_after.png` | Boots and vest, before (top) and after (bottom) |

```bash
blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- --out docs/evaluation/characters/T-028/swatch_sheet.png \
  --metadata docs/evaluation/characters/T-028/swatches.json --width 480 --height 576 --samples 8 --lighting character_neutral/1 --fibres-lod close
blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- --image docs/evaluation/characters/T-028/swatch_sheet.png \
  --metadata docs/evaluation/characters/T-028/swatches.json --out docs/evaluation/characters/T-028/metrics_after.json
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json \
  --out <dir> --no-glb --no-compare        # before: same command in a worktree of 644befd
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend \
  assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> \
  --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 \
  --closeup "boots:0:10:0,-0.05,0.12:0.40" --closeup "vest:0:5:0,-0.1,0.55:0.36"
python3 pipeline/charsys/tools/turnaround_sheet.py assets/characters/girl_auburn_bun_glasses/references/views <renders> <out> \
  --views sheet30_front:front,sheet30_front_left:front-left,sheet30_left:left,sheet30_back:back --height 640 --tag after
```

Blender: no binary on this host, so `bpy==5.3.0` (Python 3.13 venv) runs behind a `blender` wrapper that accepts
`-b --factory-startup -P <script> -- <args>`.

## Checks

| Command | Result |
| --- | --- |
| `python3 pipeline/charsys/tests/test_material_presets.py` | PASS 54/54 (test unchanged) |
| `python3 tests/garment_generic_test.py --blender <blender> --out <dir>` | PASS (rc 0): reference and extreme bodies, all clip poses, worst pose clearance 0.0005 m; fibres are attached in the test outfits (e.g. vest 6, boots 4, dress 11, fur_boots 8 fibre objects) and the garment checks are unaffected |
| `blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>` | PASS (rc 0) |
| `python3 pipeline/charsys/verify_charsys.py --blender <blender> --out <dir>` | PASS: build, geometry fingerprint ok (boy byte-identical to v6), asset store, reuse |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>` | PASS 8/8 |

`git diff t-026-claude-girl-visual -- assets/characters/boy_yellow_hoodie tests/data docs/references` is empty, and so are the
`targets` lines of `presets.json`.

## Render budget

- Iterations 1–4 as above: 4 iteration renders.
- Finals: one swatch sheet, the girl before turnaround with close-ups, and the girl after turnaround with close-ups.
- No final was rendered twice.

## Remaining

- **Sheen, felt / fleece / wool yarn** (1.05–1.06): an albedo layer can't close the gap without mottling. The
  remaining lever is stronger, light-dependent fibre highlights: a glossier R lobe or more fibre coverage on the
  sphere.
- **Skin-felt sheen:** conflicts with the < 3 fuzz ceiling under a painted layer (see above).
- **Denim fuzz** 2.91: 3% short. A slightly stronger micro albedo or a white-weft twill albedo term would close it.
- **Girl look:** the visible flecks on woven cotton and the boot mottling need an owner decision. Options:
  - accept them;
  - soften them per character through `overrides.nap`;
  - make the layer light-dependent in a follow-up.
- **Fibre stability under deformation:** `Distribute Points on Faces` (random) runs on the evaluated, deformed piece.
  Area changes under animation can make single fibres pop. Not tested in motion here. Distributing on the rest
  shape would fix it.
- **Embroidery fibres** are below a pixel at turnaround scale. A minimum fibre length or a skip at very small
  `reference_size_m` would save about 65k curves.
