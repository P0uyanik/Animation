# T-015 shared plush material evidence

Status: implementation and compatibility checks are complete. The frozen boy
1.0.0 path and all requested Blender-backed tests pass. The measured swatch
target does **not** pass: only 2/10 presets pass all applicable material rows
(7/27 applicable metric checks). This file records that result rather than
retuning the acceptance ranges or overstating the evidence.

No version was published or approved, and no pointer was changed.

## Evidence inspected

| File | Result |
| --- | --- |
| `swatch_sheet.png` | 480 x 5760, ten sphere/patch pairs, Cycles CPU, 8 samples, OIDN, AgX, exposure 0. The clear acrylic is intentionally low contrast. |
| `swatches.json` | Blender 5.3.0; 100 x 100 px flat patch ROIs; the 0.256 m reference spans about 205 px, above the VISUAL_TARGET `H >= 180 px` validity floor. Render 113.10 s, total 121.46 s. |
| `metrics.json` | Hashes the final sheet and metadata. Aggregate `pass` is false. |
| `girl_head_before.png` | 480 x 480 legacy/null-assignment build; framing and geometry are clean. |
| `girl_head_after.png` | 480 x 480 opt-in build; framing matches before and the visible change is material-only. Decoded before/after difference: max 73/255, mean 0.870290/255. |

The first metric run was invalid for two independent reasons and was replaced:

1. Blender 5.3 exposes loaded PNG samples as display-sRGB, but the measurement
   code applied the sRGB transfer function a second time. That suppressed
   saturation and local contrast.
2. The original two-column 480 x 720 sheet produced 60 x 32 px measurement
   crops and projected the physical reference below the `H >= 180 px` floor.

`measure_swatches.py` now reads the display samples directly. The sheet uses a
single stacked column at 480 px wide, yielding square 100 px patch crops and a
reference projection of about 205 px. No extreme shader retuning was retained:
experiments that forced numerical passes produced visibly wrong mottled felt,
grid-like yarn, and over-fuzzy knit.

## Measured material result

Values are `fuzz RMS / sheen P90:P50 / saturation retention %`. A dash means
the preset declares that metric not applicable.

| Preset | Measured | Applicable checks | Preset result |
| --- | --- | --- | --- |
| felt | 3.0102 / 1.0368 / 51.7296 | PASS / FAIL / FAIL | FAIL |
| wool yarn | 0.4558 / 1.0031 / 44.1630 | FAIL / FAIL / FAIL | FAIL |
| fleece | 0.3704 / 1.0019 / 32.4399 | FAIL / FAIL / FAIL | FAIL |
| cotton knit | 0.4140 / 1.0018 / 40.8362 | FAIL / FAIL / FAIL | FAIL |
| woven cotton | 0.5105 / 1.0028 / 46.8019 | FAIL / FAIL / FAIL | FAIL |
| denim | 1.4643 / 1.0116 / 75.2242 | FAIL / FAIL / PASS | FAIL |
| felt hair | 0.7142 / 1.0080 / 55.6809 | FAIL / FAIL / FAIL | FAIL |
| buttons/plastic | 0.3805 / - / 99.2318 | PASS / - / PASS | PASS |
| glasses/acrylic | 0.3561 / - / 5.0764 | PASS / - / - | PASS |
| skin-felt | 0.3941 / 1.0030 / 86.3248 | PASS / FAIL / PASS | FAIL |

The output therefore remains useful as measured evidence, but it does not meet
the reusable VISUAL_TARGET material pass rule. The fibrous cloth presets need
a follow-up shader/measurement calibration task; that should not be hidden in
T-015 by weakening targets.

## Frozen-character compatibility

The comparison used commit `573a065989e3f285ad66019f055b3c3d51f24bc8`
and the frozen file
`assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend`.
Both the origin tool and current tool rendered `canon29_front` at 480 x 720,
Cycles CPU, 8 samples, and OIDN. Comparing decoded RGBA channel bytes produced:

| Measurement | Result |
| --- | ---: |
| maximum absolute pixel difference | 0/255 |
| mean absolute pixel difference | 0/255 |
| changed RGBA channel samples | 0 of 1,382,400 |

This is an exact pixel pass. `verify_charsys.py` independently rebuilt the boy,
matched the frozen v6 geometry (`worst_numeric_m: 0.0`, no missing/extra/count
mismatches), passed store tests, and passed reuse against version 1.0.0.

The WIP change to `pipeline/blender/boy_pilot/preview.py` was reverted. The file
now matches commit 573a065 exactly; evidence sizing does not alter a shared
character preview tool.

## Requested checks

The configured Python 3.14 executable was not executable in the managed
workspace. Plain-Python drivers were run with Blender's Python 3.13.13 and the
requested Blender 5.3.0 executable. `face_system_test.py` requires Pillow only
for contact-sheet assembly; this host used a workspace-local Blender image shim
for that presentation step without changing the test or its assertions.

| Check | Result | Detail |
| --- | --- | --- |
| `verify_charsys.py --blender ...` | PASS | build, fingerprint, v6 geometry, store, and reuse all pass |
| `test_export_engine.py --blender ...` | PASS | 8/8 checks |
| `face_test.py` | PASS | exited 0; neutral, Blink, Smile, JawOpen metrics and eight renders written |
| `face_system_test.py` | PASS | exited 0; controls, expressions, blink progression, gaze, overlap, and contact-sheet stages completed |
| `test_material_presets.py` | PASS | 28/28 checks |
| frozen boy 1.0.0 pixel identity vs 573a065 | PASS | max 0, mean 0, zero changed channels |
| VISUAL_TARGET swatch metrics | FAIL | 2/10 presets; 7/27 applicable metric rows |

Generated check outputs are under `renders/materials/T-015/checks/` and the
compatibility renders are under `renders/materials/T-015/byte_identity/`.

## Reproduction

```powershell
$Blender = 'D:/Animation/tools/blender-5.3/blender.exe'
$Python = 'D:/Animation/tools/blender-5.3/5.3/python/bin/python.exe'
$Evidence = 'docs/evaluation/materials/T-015'
$BuildRoot = 'renders/materials/T-015'

& $Blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- `
  --out "$Evidence/swatch_sheet.png" `
  --metadata "$Evidence/swatches.json" `
  --width 480 --height 5760 --samples 8 `
  --save-blend "$BuildRoot/swatch_scene.blend"

& $Blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- `
  --image "$Evidence/swatch_sheet.png" `
  --metadata "$Evidence/swatches.json" `
  --out "$Evidence/metrics.json"

& $Python pipeline/charsys/verify_charsys.py `
  --blender $Blender --out "$BuildRoot/checks/verify_charsys-new"
& $Python pipeline/charsys/tests/test_export_engine.py --blender $Blender
& $Python pipeline/charsys/tests/test_material_presets.py
```

`measure_swatches.py` intentionally exits 1 while the aggregate material result
is false. No C++ build is required for T-015.
