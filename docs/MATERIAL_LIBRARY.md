# Shared plush material library

T-015 adds opt-in, data-driven Cycles materials under
`pipeline/charsys/materials/`. The ten presets are `felt`, `wool yarn`,
`fleece`, `cotton knit`, `woven cotton`, `denim`, `felt hair`,
`buttons/plastic`, `glasses/acrylic`, and `skin-felt`.

`presets.json` owns the physical response and the VISUAL_TARGET acceptance
ranges. `builder.py` is the single Blender builder. It accepts a preset, an
sRGB base-colour override, a physical reference size, and optional nested
overrides. It builds the Principled surface, reference-scaled fibre bump,
roughness, sheen/fuzz response, and an optional grazing-angle sheen layer. The
silhouette layer is disabled in every preset by default for render speed.

## Character opt-in

The legacy material path remains the default. A character opts in only through
`spec.materials.assignments`:

```json
{
  "skin": {
    "preset": "skin-felt",
    "base_color_srgb": [202, 176, 169],
    "reference_size_m": 0.29278
  }
}
```

Known semantic slots are currently `skin`, optional `eyes`, an accessory name
such as `glasses`, and `<accessory>_lens`. Nested `overrides` may tune a preset
for a deliberate art-direction exception; use them sparingly so swatches remain
representative. Unknown presets and malformed colours/reference sizes fail spec
validation.

The generic face layers the preset onto the existing blush and procedural-eye
graphs instead of replacing their colour inputs. Glasses use the same builder
for frame and lens. The H31 felt-hair entry point delegates to the shared module
through a node-for-node legacy adapter, so specs that do not opt in keep their
existing render.

## Swatches and metrics

The Blender commands are recorded in
`docs/evaluation/materials/T-015/README.md`. The swatch scene reuses
`compare_harness.studio_lighting`, renders at 640 px wide, and writes exact
patch ROIs plus render/total timings. The measurement script reads those ROIs and reports fuzz RMS,
sheen P90/P50, and saturation retention against the ranges in `presets.json`.
