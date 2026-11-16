# T-019B shared material fibres

Status: **implementation/checks PASS; VISUAL_TARGET aggregate FAIL (2/11 presets, 13/30 applicable metric rows).**
Targets were not changed. This report records the timeboxed physical result rather than weakening acceptance.

## Face gate first

| Check | Result | Evidence |
| --- | --- | --- |
| Boy 1.1.0 `face_test.py` | PASS | neutral eye 37.2%, Blink 0.0%, Smile corner lift +4.5 mm, JawOpen 13.6 mm; maximum skin stretch 1.0 |
| Girl `face_system_test.py --no-render` | PASS | 28 controls, 34 states, ten gaze cases; zero lid/glasses overlaps and 0.0% eye visibility in every blink gaze |
| Girl render-mode presentation step | environment-only FAIL | numeric stages passed, then Pillow was unavailable; the documented `--no-render` test passed |

No face source required a merge fix.

## Shared Geometry Nodes fibres

`builder.shared_fibre_node_group()` builds one reusable `PS Shared Surface Fibres/1` group. A dedicated native
`CURVES` object reads any source mesh through Object Info, distributes points by `density_per_cm2`, creates and
resamples short curves, applies stochastic length plus authored curl/lean, tapers the radius, and assigns a
base-colour-derived Principled Hair BSDF. There is no character or garment branch. `wide` LOD is density x 0.25.

The requested `fibres` fields are `enabled`, `density_per_cm2`, `length_mm`, `curl`, `lean`, and `lod`. They are on
for felt, wool yarn, fleece, cotton knit, felt hair, and the new shared boot-fleece preset; skin, buttons/plastic,
glasses/acrylic, woven cotton, and denim are off.

## Measurement corrections

- PNGs are decoded as exact RGB8 display samples instead of passing through Blender's image buffer.
- The physical reference projects to 204.8 px (valid `H >= 180`), then each ROI is resampled to `H = 256` before
  the VISUAL_TARGET 9 px/31 px kernels are applied.
- Saturation uses a co-planar neutral card for linear-RGB channel adaptation.
- Sheen uses the sphere highlight ROI; fuzz and saturation use the flat patch.
- Eleven Cycles frames were rendered at 480 x 576, 8 spp, CPU + OIDN and losslessly stacked. No Cycles render
  dimension exceeded 640 px.

## Final metrics

Values are `fuzz RMS / sheen P90:P50 / saturation retention %`. A dash is not applicable.

| Preset | Fuzz | Sheen | Saturation | Preset |
| --- | ---: | ---: | ---: | --- |
| felt | 1.2475 FAIL | 1.0470 FAIL | 83.4104 PASS | FAIL |
| wool yarn | 2.5679 FAIL | 1.0344 FAIL | 81.3729 PASS | FAIL |
| fleece | 3.0087 PASS | 1.0370 FAIL | 84.2523 PASS | FAIL |
| cotton knit | 2.2813 FAIL | 1.0374 FAIL | 89.8189 PASS | FAIL |
| woven cotton | 2.1187 FAIL | 1.0399 FAIL | 90.1145 PASS | FAIL |
| denim | 2.0722 FAIL | 1.0461 FAIL | 81.9025 PASS | FAIL |
| felt hair | 1.5540 FAIL | 1.0333 FAIL | 101.4458 PASS | FAIL |
| boot fleece | 2.1320 FAIL | 1.0350 FAIL | 66.4196 FAIL | FAIL |
| buttons/plastic | 0.2475 PASS | - | 91.8508 PASS | PASS |
| glasses/acrylic | 1.3636 PASS | - | - | PASS |
| skin-felt | 0.4558 PASS | 1.0570 FAIL | 97.0052 PASS | FAIL |

Before T-019: 2/10 presets and 12/27 metric rows passed. Final: 2/11 presets and 13/30 rows pass. Real fibres made
the largest fuzz changes on fleece (2.2773 -> 3.0087), wool yarn (1.3785 -> 2.5679), felt hair
(0.6869 -> 1.5540), and boot fleece (0.7160 -> 2.1320). Sheen remains systemically below its minimum; this is a
recorded failure, not a claim that the target is unreachable.

## Render cost and girl regression

Matched 480 x 576 swatches at 8 spp + OIDN: fibres on 36.71 s total / 3.337 s per frame; fibres off 36.28 s total /
3.298 s per frame, a +0.039 s (+1.2%) mean cost. Matched 240 x 480 girl views: fibres on 1.398 s per frame versus
1.348 s off (+3.7%).

The final four-view girl turnaround is 480 px high, 8 spp + OIDN. Against the same current master rendered without
fibres, mean RGB differences are 0.112-0.171/255 (maximum 20-54/255 depending on view). The T-016 curl/rope
silhouette, bun, fringe, band, and flowers remain intact.

## Checks

| Check | Result |
| --- | --- |
| `test_material_presets.py` | PASS 54/54 |
| shared GN Blender probe | PASS; same node group on close/wide objects, density 10,000 -> 2,500 points/m2 for felt |
| `groom_generic_test.py` | PASS 9/9 |
| `test_export_engine.py` | PASS 8/8 |
| `verify_charsys.py` with a new empty output | PASS |
| Boy legacy compatibility | PASS; boy has no material assignment, frozen files/specs are unmodified, and `verify_charsys` geometry/store/reuse checks pass |
| Girl face/groom | PASS; face gate above and T-016 groom silhouette visually retained |
| VISUAL_TARGET material aggregate | FAIL; table above |

The configured Python 3.14 executable was denied by the managed host, so plain-Python checks used Blender's bundled
Python 3.13.13. Blender work used 5.3.0 CPU-only.

## Evidence and reproduction

- `metrics_before.json`, `metrics_wip_r6.json`, `metrics_after.json`
- `swatch_sheet.png`, `swatches.json`
- `girl_turnaround.png`, `girl_compare.json`
- `timings.json`

```powershell
$Blender = 'D:/Animation/tools/blender-5.3/blender.exe'
& $Blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- `
  --out docs/evaluation/materials/T-019/swatch_sheet.png `
  --metadata docs/evaluation/materials/T-019/swatches.json `
  --width 480 --height 576 --samples 8 --lighting character_neutral/1 --fibres-lod close
& $Blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- `
  --image docs/evaluation/materials/T-019/swatch_sheet.png `
  --metadata docs/evaluation/materials/T-019/swatches.json `
  --out docs/evaluation/materials/T-019/metrics_after.json
```

`measure_swatches.py` intentionally exits 1 while the aggregate is false.
