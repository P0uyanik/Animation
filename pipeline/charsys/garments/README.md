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
    "mask_margin_m": 0.015,
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

## Surface fibres (`fibres_lod`, T-028)

Every garment piece whose material preset enables `fibres` (felt, wool yarn,
fleece, cotton knit, felt hair, boot fleece) gets the shared Geometry Nodes
group `PS Shared Surface Fibres/1` through
`materials.builder.add_fibres_from_assignment`. Nothing is character-specific:
the piece's own assignment (preset, colour, `reference_size_m`, overrides)
drives it. Fibre length scales with `reference_size_m / 0.256` and density with
its inverse square, so the H-normalised look matches the swatch sheet.
`clothing.fibres_lod` is `close` (default), `wide` (preset LOD density) or `off`.
The Curves object `<piece>.fibres` is a child of its piece (it follows the rig
and the collision modifiers) and carries `ps_fibres_source`; `set_active_items`
hides it with its piece. It is not in the returned garment list, and the engine
exporter skips it (meshes only).

## Body masks (`hide_body_faces`, per-item `mask_body`)

Production clothes do not keep skin under a garment: in extreme poses it pokes
through. `hide_body_faces` (default `false`) sets the default for every item and
`mask_body` overrides it per item. For each masked shell-based item (tops, vests,
dresses' bodices, shorts/trousers, footwear) the body faces copied into that
item's shell are recorded on the body mesh as the FACE attribute
`ps_cover.<item>`. Nothing is deleted. After rigging, `bind_to_body` builds the
vertex group `ps_garment_mask` from the worn items (vertices whose every face is
covered) and a `MASK` modifier `garment_body_mask` (inverted) hides the fully
covered faces. Skin within `mask_margin_m` (default 15 mm, geodesic, rest pose)
of visible skin stays, so a camera looking past a hem, cuff or collar sees skin
rather than the hollow inside of the masked body. Skirts cover
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

## Volume, collar and decoration parameters (T-024)

All optional and generic; omitted values reproduce the T-018 geometry exactly.

| field | item types | meaning |
|---|---|---|
| `sleeve_puff_m` (0–0.1) | top, shirt, dress bodice | extra shell offset along the sleeve; a smooth 0→1→0 bump from the sleeve start (t 0.10) to the cuff, so the sleeve is gathered at both ends |
| `sleeve_puff_peak` (0–1, default 0.6) | same | where along the sleeve the puff peaks |
| `puff_m` (0–0.1) | shorts, trousers | bloomers: the volume grows from the waist to the seat (0.71 × `puff_m` at the hip line), peaks in the upper leg and gathers to 0 at the leg opening |
| `puff_inner` (0–1, default 0.35) | same | share of the puff on surfaces facing the other leg |
| `collar: {"type": "round", ...}` | tops | flat collar lying on the shoulders, split at the front with rounded tips: `width_m`, `gap_m` (front split), `slope` (drop per metre outwards), `tip_round` (rounded share of each half), `lift_m` (extra clearance so it lies out over a vest or jacket). Material part `collar`, else `main` |
| `bands.cuff_radius_m` (0–0.05) | tops, bottoms, footwear | tube radius of the cuff band (thick fur boot cuffs, gathered cuffs); the ring moves out so it stays outside the garment |
| `embroidery` | tops, vests, dresses, bottoms | raised motifs on the outside of the main shell. `motifs`: `u` (signed fraction of the local half width, + = the character's left), `v` (fraction from hem to top), `face` (`front`/`back`), `style` (`flower`: petals, centre knot and leaves; `sprig`: stem with alternating leaves), `size_m`, `relief_m`, `petals`, `leaves`, `rotation_deg`. `material` / `accent_material` (or `materials.embroidery` / `embroidery_accent`). Two objects: `garment.<item>.embroidery` and `.embroidery_accent`. A motif that misses the garment (e.g. in a vest's open front) is an error |

`garments/evaluate.py` holds the shared evaluation helpers (semantic FK rig conversion, clip player, signed
clearance) used by `tests/garment_generic_test.py` and `tools/garment_pose_eval.py`.

## Robustness and placement options (T-025)

All generic; when the new fields are omitted, the geometry on the reference body (the neutral `body_generic`
mannequin at 1.0 m) is bit-identical to T-024, except for the hip band fix below.

**Proportion-relative distances (`BodyFit`).** Every ease, offset, opening, placement, mask margin and collision
distance (spec values and the former height-fraction margins) is defined on the reference body and multiplied by
the ratio of the local body measure to `REFERENCE_BODY_M`. The arm-root radius is used for sleeves, the thigh
radius for legs and footwear, the mean torso depth for the torso, and the head height for collar defaults.
`mask_margin_m` and `collision.offset_m/radius_m/falloff_m` use the geometric mean of the limb and torso ratios.
Ratios are rounded to 1e-4. Decoration sizes (button, pocket, collar, cuff and embroidery sizes, thickness,
seam radius) are not scaled. The build report carries `body_fit` (measures and ratios).

**Armholes from body measurements.**
- The armhole depth below the shoulder line is (2/π) × the arm-root circumference (= 4 arm-root radii).
- The side cut keeps `ARMHOLE_SIDE_SHARE` (0.58) of the local torso half width. It never comes closer than
  1.25 arm-root radii to the shoulder joint, so the arm root always passes through the opening.

**Hip band.** Below the hip line, the shorts/trousers shell takes the whole hip ring down to one thigh radius. The
older band covered only the area between the leg centres, which left holes at the front and back of the hip that
bloomer volume opened.

| field | item types | meaning |
|---|---|---|
| `shoulder_width` (0–1) | top, shirt, vest, dress | fuller shoulders: at the shoulder line, the strap reaches this share of the way from the neck to the shoulder joint. It blends smoothly into the default armhole cut at the underarm |
| `bands.edge_roll_m` (0–0.03) | top, shirt, vest, dress | rolled edge (piping): a tube of this radius along every open edge of the main panel (front/neck/hem loop, armholes or sleeve ends). Material part `edge`, else `band`, else `main` |
| `crotch: {"type": "gusset", "depth", "width"}` | shorts, trousers | hammock panel between the legs, from just above the crotch down to `depth` (0–1, default 0.6) of the crotch-to-hem length. `width` (default 0.85) is its front/back reach as a share of the leg-panel radius. Object `garment.<item>.gusset`, part `gusset` (material falls back to `main`) |
| `buttons: {"placement": ...}` | see below | `centre` (default, T-018 behaviour, tops); `edge`: along the front edge(s) of an open garment, `side` both/left/right, `inset_m` from the opening, vertical span `v0`–`v1` between the hem and the armhole bottom; `waistband` (bottoms): `count` buttons across the front of the waistband, `spread` (fraction of the half width), `drop_m` below the top; `pockets` (vests): on each pocket's upper part; `positions`: explicit `[{u, v, face}]` on the main panel. Each button is oriented on the garment surface. An integer `buttons` on bottoms means `waistband` |
| `embroidery.motifs[].target` | all | `main` (default), `pocket.L` / `pocket.R` (vests), `main.L` / `main.R` (footwear). On targets other than a torso/bottoms `main`, `u`/`v` are fractions of the piece's rest bounding box |
| `embroidery` style `bouquet` | all | three flowers with leaves and a knot: dense enough to read at 640 px |
| `shaft_width_m` (0–0.1) | shoes, boots | extra shaft volume, reaching full width over the lower third of the shaft. A lining ring closes the opening between the leg and the widened shaft (part `lining`, material `lining`, else `band`) |
| `toe_volume_m` (0–0.1) | shoes, boots | extra volume over the front half of the foot, mostly on its top and front; the sole grows with it |
| `sole.width_m` (0–0.05) | shoes, boots | extra sole width and length |

`garments/evaluate.py` (T-025):
- **`test_poses(clips_dir)`.** The legacy six samples plus one sampled extreme per `content/clips/*.clip.json`.
  The extreme is the frame farthest from the clip's first frame; a static clip contributes its last frame. A new
  clip is a new test pose.
- **`inside_body`.** A majority vote of ray-crossing parity over 14 directions, so a ray that grazes a fold
  cannot decide alone.
- **`skin_contact`.** It has one documented tolerance, `SKIN_CONTACT_TOLERANCE_M` = 4.5 mm (2 × the 2 mm collision
  offset + the 0.5 mm rest floor). `clearance` counts a vertex as skin contact rather than poke-through in two cases:
  - the skin nearest to it faces other skin within that tolerance, or lies inside another body part;
  - the skin the garment vertex was built from (`ps_body_vertex`) is posed inside another body part (an upper arm
    sunk into the ribs, the hip front folded into a raised thigh).
