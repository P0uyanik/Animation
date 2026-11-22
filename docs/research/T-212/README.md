# T-212 · Keep Blender for face fitting. Change the bake and acceptance checks.

Fit existing spec controls first. Add Warp, Hook or Lattice for persistent contour errors. Pilot **auburn** to exercise the brow bind, glasses and blink. Estimate **1–2 task-days for the pilot within 18–24 for all three**. Expand once a clean rebuild improves held-out likeness and its exported expressions match Blender. Budget uncertainty centres on feature placement and export parity. [T-211](../T-211/REPORT.md) · [T-209](../T-209/REPORT.md)

| Risk | Evidence and decision |
|---|---|
| Coupled cheek and jaw controls | A 4 mm Warp gave 0.0000 mm beyond 30 mm on auburn. Its round falloff can change cheek and jaw curvature together. Check each knob against front and profile traces. Taper the neck weights and drop redundant controls. |
| Fit time and feature attachment | Warp / Hook / Lattice took 15 / 17 / 21 ms on stripped skin. Time a **scored multi-view trial**. The brow bind failed on concave faces. Warping a triangulated copy directly gave 0.128 mm maximum follow error. Verify its vertex correspondence and update it every trial. Regenerate final lids and seat glasses rigidly. [Local run](deformers-auburn.json) |
| Expression and engine mismatch | Editing Basis preserved the tested smile delta (0.0000 mm error). The probe removed the captured Warp key before that test. With a live GN cheek offset, the Blink delta changed by 2.923 mm. Bake on neutral skin before rig and mask evaluation, remove fit helpers, rebuild lid keys. Export reads evaluated rest vertices and raw key-minus-Basis deltas. Compare reconstructed neutral, half-blink and smile+blink against Blender within export quantization. Check corrective weights too. Pin the Blender build and rerun parity on upgrades. [Probe](../T-211/probes/deformer_probe.py) · [Exporter](../../../pipeline/charsys/export_engine.py) |
| False confidence in a score | T-204’s auburn exposed cheek spans 12% vs 32% of head height because a lock covers it. Fit hair separately. Match camera and smile, use trace tolerance bands on the 99–590 px references, omit hidden points, reserve a reference for owner sheet review. Use Workbench masks and surface landmarks for fitting. At full blink T-211 still found 8/519 visible near-eye samples at 45°. Check a close-up mask and lid intersections because nearest BVH distance has no sign. [T-204 staged report](../../../build/in/docs/evaluation/characters/T-204/README.md) · [Blink measurements](../T-211/probes/measure_girl_auburn_bun_glasses.json) |

| Free alternative | Where it earns its cost |
|---|---|
| Bounded fit on existing controls | Preferred first pass. Select controls by finite differences. Reuse the seeded search, penalize large edits and check held-out contours. [Fit tool](../../../tools/fit/README.md) |
| Sculpt / multires | For a stubborn contour, transfer an approved sculpt to a base-resolution key with matching vertex order. Each sculpt adds upkeep. |
| Geometry Nodes capture | Set Position can supply a custom falloff. Capturing evaluated positions by stable vertex ID adds bake code. Reserve it for a falloff the standard modifiers cannot express. |
| Image-to-3D proxy | A CPU visual hull from owned masks can guide silhouette review. Hair occlusion and inconsistent drawings leave cheek depth ambiguous. |
| More work in the engine | Keep gaze, visemes and expression weights there. A second rest-face deformer adds another implementation to keep in sync with Blender. |

Offline assessment from repository evidence and prior knowledge. All proposed probes fit Blender/Python on the MX350 and need no external model weights for commercial output.

**Replay** (PowerShell, repository root `60f8d21`). Blender 5.3.0 build `02f0899d78e3`. Ledger | 1 headless probe · 0 renders · 0 asset builds · 0 CI.

```powershell
$scratch = (New-Item -Force -Type Directory build/T-212).FullName
$env:TEMP = $env:TMP = $env:BLENDER_USER_RESOURCES = $scratch
$env:LOCALAPPDATA = $env:APPDATA = $env:USERPROFILE = $scratch
$env:PYTHONDONTWRITEBYTECODE = '1'
$id = 'girl_auburn_bun_glasses'
$master = (Resolve-Path "assets/characters/$id/versions/0.14.0/${id}_master.blend").Path
& 'D:/Animation/tools/blender-5.3/blender.exe' -b --factory-startup --offline-mode -t 1 `
  --python-exit-code 1 -P docs/research/T-211/probes/deformer_probe.py `
  -- $master "$scratch/deformers.json" *> "$scratch/blender.log"
```
