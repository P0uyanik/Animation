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
    "hide_body_faces": true,
    "collision": {"enabled": true, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 3},
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

## Body masks (`hide_body_faces`, per-item `mask_body`)

Production clothes do not keep skin under a garment: in extreme poses it pokes
through. `hide_body_faces` (default `false`) sets the default for every item and
`mask_body` overrides it per item. For each masked shell-based item (tops, vests,
dresses' bodices, shorts/trousers, footwear) the body faces copied into that
item's shell are recorded on the body mesh as the FACE attribute
`ps_cover.<item>`. Nothing is deleted. After rigging, `bind_to_body` builds the
vertex group `ps_garment_mask` from the worn items (vertices whose every face is
covered) and a `MASK` modifier `garment_body_mask` (inverted) hides exactly the
fully covered faces; the boundary ring under hems and cuffs stays. Skirts cover
no faces and never mask. `set_active_items(body, garments, items)` switches the
worn set (outfits) and rebuilds mask and collision weights; it is deterministic.
The engine exporter keeps all body vertices and drops the masked triangles.

## Post-skinning collision (`collision`)

Every garment piece gets, after its `Armature` modifier, `passes` (1--4, default
3) `SHRINKWRAP` modifiers (`body_collision`, `body_collision.2`, ...):
nearest surface point, `OUTSIDE`, `offset_m` (default 2 mm), limited to the
vertex group `ps_collision`. The target is `garment.collider.<body>`, a hidden,
never-rendered object that shares the body mesh and weights and is deformed by
the same rig without the mask, so hidden skin still pushes clothes outward.
Extra passes resolve vertices that the first projection pushed into an
adjacent body part in deep creases. `ps_collision` weights come from the rest
pose: 1 where the vertex hangs over visible skin or lies within `radius_m` of
it, falling to 0 over `falloff_m`; vertices deep over masked skin are not
moved. It is a modifier stack, so it bakes and evaluates identically in viewport,
render and caches. Set `collision.enabled` to `false` to omit it.

Articulation helpers from the first iteration (`articulation_allowance_m`,
`front_articulation_rise_m`, `front_centre_ease_m`) remain available as item
fields but default to 0; masks plus collision replace per-pose offset tuning.

`max_influences` is 1--4. Four copies the body's complete smooth weights. A
dominant-source value of 1 is useful for thick plush clothes: it keeps an
outward shell offset rigid at tight joints where a multi-bone linear blend can
invert the offset. In both modes the bone choice and weights originate from the
nearest body surface.
