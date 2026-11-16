# Shared plush material library

T-015 adds opt-in, data-driven Cycles materials under
`pipeline/charsys/materials/`. The eleven presets are `felt`, `wool yarn`,
`fleece`, `cotton knit`, `woven cotton`, `denim`, `felt hair`,
`boot fleece`, `buttons/plastic`, `glasses/acrylic`, and `skin-felt`.

`presets.json` owns the physical response and the VISUAL_TARGET acceptance
ranges. `builder.py` is the single Blender builder. It accepts a preset, an
sRGB base-colour override, a physical reference size, and optional nested
overrides. It builds the Principled surface, reference-scaled fibre bump,
roughness, sheen/fuzz response, and an optional grazing-angle sheen layer.

T-019 adds real surface fibres through one shared, parameterised Geometry
Nodes group (`PS Shared Surface Fibres/1`). `add_fibres_geometry` creates a
native `CURVES` object driven from any mesh through Object Info, scatters short
curves by physical density, applies length/curl/lean, and shades them with a
base-colour-derived Principled Hair BSDF. It contains no character or garment
branches. Presets expose only physical/LOD controls:

```json
"fibres": {
  "enabled": true,
  "density_per_cm2": 1.0,
  "length_mm": 4.6,
  "curl": 0.35,
  "lean": 0.35,
  "lod": 0.25
}
```

Use `lod="close"` for authored density, `lod="wide"` for the preset's 0.25
density multiplier, and `lod="off"` for no curve object. Fibres are enabled on
felt, wool yarn, fleece, cotton knit, felt hair, and boot fleece. Skin, plastic,
acrylic, woven cotton, and denim leave them off.

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
`compare_harness.studio_lighting`. Its 480 px-wide single-column evidence layout
keeps the 0.256 m reference above the VISUAL_TARGET measurement-scale floor and
writes exact square patch ROIs plus render/total timings. The measurement script
reads exact RGB8 PNG bytes, normalises valid `H >= 180 px` crops to `H = 256`,
uses a co-planar neutral card for saturation adaptation, and measures sheen in
the sphere highlight ROI. It reports fuzz RMS, sheen P90/P50, and saturation
retention against the unchanged ranges in `presets.json`. T-019 renders each
swatch independently at 480 x 576 and stacks the PNG samples afterward, so no
Cycles render exceeds 640 px.
