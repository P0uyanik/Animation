# Shared garment generator (`garment/1`)

`garment/1` builds clothes from a `body_generic/1` surface and its measured
parameters. It has no character data. Main panels are offset body shells;
skirts are body-sized lofted shells. Seams, rib bands, cuffs, buttons, pockets,
and soles are separate procedural pieces. After the body is rigged, every piece
receives normalized weights copied from nearby body vertices.

The character spec uses this shape:

```json
{
  "clothing": {
    "generator": "garment/1",
    "hide_body_faces": false,
    "max_influences": 1,
    "defaults": {
      "thickness_m": 0.002,
      "ease_m": 0.008,
      "seam_radius_m": 0.0012
    },
    "garments": [
      {
        "type": "top",
        "name": "shirt",
        "sleeve_length": 0.75,
        "collar": "shirt",
        "buttons": {"count": 4},
        "bands": {"hem": true, "cuff": true, "rib_ridges": 2},
        "seam_lines": true,
        "material": {
          "preset": "woven cotton",
          "base_color_srgb": [205, 194, 186]
        }
      }
    ]
  }
}
```

Supported item types are `top`/`shirt`, `vest`, `shorts`, `trousers`,
`dress`, `skirt`, `shoes`, and `boots`. Ratios (`sleeve_length`, `length`,
`height`) are in `[0, 1]` over the corresponding limb span. Metric overrides
use a `_m` suffix. Shared fields are `thickness_m`, `ease_m` (alias
`offset_m`), `bands`, `seam_lines`, and `material`.

`materials` may override the inherited main assignment for `bodice`, `skirt`,
`band`, `seam`, `buttons`, `pockets`, or `sole`. Preset names are the T-015
library names. When that library is installed its node builder is used; the
fallback used by isolated tests preserves the same preset metadata.

`hide_body_faces` is opt-in. It deletes only body faces selected by shell-based
items; open boundaries remain under the garment. It is useful for export builds
where extreme poses would otherwise reveal covered skin.

`max_influences` is 1--4. Four copies the body's complete smooth weights. A
dominant-source value of 1 is useful for thick plush clothes: it keeps an
outward shell offset rigid at tight joints where a multi-bone linear blend can
invert the offset. In both modes the bone choice and weights originate from the
nearest body surface.
