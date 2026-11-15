# T-015 shared plush material evidence

Status: implementation and non-Blender preparation are complete. Blender was
not available on this machine, so no render or measured metric has been
fabricated. The commands below create the pending evidence with the current
builder and measurement code.

## Prepared in this change

- Ten validated JSON presets and one Cycles node-graph builder.
- Explicit girl opt-ins for `skin-felt`, a `buttons/plastic` glasses frame,
  and `glasses/acrylic` lenses.
- `legacy_materials.override.json`, which sets `materials.assignments` to null
  and produces the visual "before" build without editing the character spec.
- A 640 px-wide sphere/patch swatch renderer using the existing neutral studio
  light from `pipeline/blender/compare_harness.py`.
- A metric script that writes actual fuzz RMS, sheen P90/P50, saturation, and
  per-range pass/fail results to `metrics.json` only after a swatch exists.

The frozen boy 1.0.0 directory and boy spec were not edited. The legacy H31
felt-hair function now delegates to a node-for-node copy in the shared builder;
characters without `materials.assignments` remain on their legacy paths.

## Checks completed without Blender

- PASS: `presets.json`, the girl spec, and the legacy override parse as JSON.
- PASS: PowerShell structural checks found exactly the ten requested presets,
  all silhouette layers disabled by default, all three metric keys per preset,
  only the three intended girl assignments, and no boy assignment.
- BLOCKED: `py -3 pipeline/charsys/tests/test_material_presets.py`. The Windows
  launcher is present at `C:\WINDOWS\py.exe`, but `py --list-paths` reports
  `No installed Pythons found!`; `py -3` exits 1 on this host.

## Pending Blender steps

Run from the repository root in PowerShell. Set `$Blender` to the installed
executable once Blender and a Python runtime are available.

```powershell
$Blender = 'C:\path\to\blender.exe'
$GirlSpec = 'assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json'
$Evidence = 'docs/evaluation/materials/T-015'
$BuildRoot = 'renders/materials/T-015'

py -3 pipeline/charsys/tests/test_material_presets.py

& $Blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- `
  --out "$Evidence/swatch_sheet.png" `
  --metadata "$Evidence/swatches.json" `
  --width 640 --height 960 --samples 64 `
  --save-blend "$BuildRoot/swatch_scene.blend"

& $Blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- `
  --image "$Evidence/swatch_sheet.png" `
  --metadata "$Evidence/swatches.json" `
  --out "$Evidence/metrics.json"

& $Blender -b --factory-startup -P pipeline/charsys/build_character.py -- `
  --spec $GirlSpec --override "$Evidence/legacy_materials.override.json" `
  --out "$BuildRoot/girl_before" --no-glb --no-compare

& $Blender -b --factory-startup -P pipeline/charsys/build_character.py -- `
  --spec $GirlSpec --out "$BuildRoot/girl_after" --no-compare

& $Blender -b --factory-startup -P pipeline/blender/boy_pilot/preview.py -- `
  "$BuildRoot/girl_before/girl_auburn_bun_glasses_master.blend" `
  "$BuildRoot/preview_before" 64 face_front

& $Blender -b --factory-startup -P pipeline/blender/boy_pilot/preview.py -- `
  "$BuildRoot/girl_after/girl_auburn_bun_glasses_master.blend" `
  "$BuildRoot/preview_after" 64 face_front

Copy-Item "$BuildRoot/preview_before/face_front.png" "$Evidence/girl_head_before.png"
Copy-Item "$BuildRoot/preview_after/face_front.png" "$Evidence/girl_head_after.png"
```

Expected evidence after those commands:

| File | Purpose |
| --- | --- |
| `swatch_sheet.png` | 640 px-wide sphere plus fabric patch for every preset |
| `swatches.json` | Render metadata, timing budget, and exact patch ROIs |
| `metrics.json` | Measured VISUAL_TARGET material metrics and pass/fail |
| `girl_head_before.png` | Girl head using the null-assignment legacy override |
| `girl_head_after.png` | Girl head using the T-015 opt-ins |

Run the requested checks after the builds. `verify_charsys.py` requires a new
or empty output directory.

```powershell
py -3 pipeline/charsys/verify_charsys.py --blender "$Blender" --out "$BuildRoot/verify_charsys"
py -3 pipeline/charsys/tests/test_export_engine.py --blender "$Blender"

& $Blender -b --factory-startup -P pipeline/charsys/tests/face_test.py -- `
  "$BuildRoot/girl_after/girl_auburn_bun_glasses_master.blend" `
  "$BuildRoot/face_test"

& $Blender -b --factory-startup -P pipeline/charsys/tests/face_system_test.py -- `
  "$BuildRoot/girl_after/girl_auburn_bun_glasses_master.blend" `
  "$BuildRoot/face_system_test"
```

No C++ build is required for T-015.

## Pending version creation

Only after the build and checks pass, publish the new girl candidate. This is
intentionally not run here because a publish requires real Blender outputs.

```powershell
py -3 pipeline/charsys/asset_store.py publish `
  --character girl_auburn_bun_glasses `
  --build "$BuildRoot/girl_after" `
  --version 0.4.0 `
  --notes 'T-015 shared skin-felt and glasses material opt-in'
```

Approval/pointer changes remain an owner action.
