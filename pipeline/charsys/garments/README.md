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
`dress`, `skirt`, `shoes`, `boots`, `hoodie` (T-058), `sneakers` and `backpack` (T-068, below). Ratios (`sleeve_length`, `length`,
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

## Cloth rest shape, thickness and edges (T-034)

All optional and generic; with none of these fields the geometry is unchanged (the boy and every older spec build
byte-identically).

**`drape`** (any shell-based item: tops, vests, dress bodices, shorts/trousers, footwear) runs Blender's cloth solver
once at build time on the item's offset shells (`garments/drape.py`). The body is the collider in its rest pose
(only the faces within `collider_reach_m` of the shell, inflated to the item's ease so a thin collision shell
suffices). The cloth settles under gravity. The settled shape replaces the shell's rest shape, and then skinning,
masks, post-skinning collision and the rest clearance projection run exactly as before. Other pieces of the item,
such as bands, buttons, pockets, edge rolls and embroidery, follow the settled panel: each takes the displacement
of the nearest shell face. The solidified inner layer is rebuilt along the settled normals, so the cloth keeps an
even thickness through the folds.

| field | meaning |
|---|---|
| `enabled` | default `false` |
| `fabric` | `cotton`, `knit`, `felt`, `denim`. Blender cloth mass, tension/compression/shear/bending stiffness, air damping, collision thickness and friction (`drape.FABRICS`) |
| `overrides` | per-field fabric overrides (`mass`, `tension`, `compression`, `shear`, `bending`, `air_damping`, `thickness_m`, `friction`) |
| `pin` | list of `edges` (open edges held by their band or finish), `volume` (shell areas at the plain ease stay fitted; only puff/bloomer volume drapes), `top` (the item's top band carries the weight, as a vest hangs from the shoulders) |
| `edge_band_m`, `volume_band_m`, `top_band_m` | falloff of each pin (defaults 12, 6 and 30 mm) |
| `gather` (0–0.5) | the free cloth is grown by this share before it settles. It no longer fits the volume it came from, so it buckles into gathers against the pinned bands. With the `volume` pin, the growth is proportional to the designed extra volume (fullness), so the run into a cuff stays smooth |
| `gravity` (0–1) | share of Earth gravity. Plush garments are stuffed and stiff, so less than 1 keeps puffs round |
| `frames`, `quality`, `seed`, `jitter_m`, `smooth` | fixed solver frames (default 30) and steps per frame (6). A seeded jitter of free vertices breaks the symmetry so folds form, and is reproducible. `smooth` is a Laplacian relax of the free vertices after the solve |
| `parts.<main|bodice>` | per-part overrides of any of the above (for example `{"bodice": {"enabled": false}}` on a dress) |

The solve runs in a private scene with no self-collision and a fixed frame count, so a build is bit-reproducible
(`tests/garment_generic_test.py` check `drape_deterministic`). The build report carries per-shell `drape` statistics:
free vertices, mean/max movement, collider faces and seconds.

**`edge_finish: "rounded"`** (any shell item, or `defaults`) rounds the solidified rim of the shell: the rim edges
get a 2-segment bevel of half the thickness, so the hems, cuffs and openings read as soft cloth with real thickness
rather than a cut sheet. `thickness_m` still sets the thickness.

**`bands.edge_roll_m` + `bands.edge_style`** now work on every shell type, not only tops: bottoms (waist and leg
openings) and footwear (boot tops). `rolled` (default, as in T-025) is cloth turned over the edge. `piped` is a cord
centred on the rim, with material part `piping`, falling back to `edge`, `band` and then `main`.

## Hand-made surface detail (`surface_detail`, T-034, materials)

`surface_detail` is an optional material preset section (`materials/presets.json`, `materials/builder.py`
`_surface_detail`). It sits between the weave/fibre scale and the silhouette scale:
- domain-warped **lumps**: felt lumpiness and uneven stuffing under the cloth. Fields: `lump_scale_per_reference`,
  `lump_strength`, `lump_albedo`;
- **fibre-direction streaks**: object coordinates stretched by `fibre_direction`. Fields:
  `fibre_scale_per_reference`, `fibre_strength`, `fibre_albedo`;
- **`irregularity`**: a domain warp of both, so nothing reads machine-regular;
- `distance_fraction`: the bump distance, as a share of the reference size.

It drives the shading normal and, very lightly (at most ±30 %, ±3–6 % in the presets), the albedo. Those are the two
guide passes that OIDN preserves, and the features are several pixels wide at turnaround scale, so the detail
survives denoising.

It is enabled on `felt`, `woven cotton`, `cotton knit`, `denim`, `fleece` and `boot fleece`. `skin-felt` carries a
tuned block that is disabled: a character opts in with `"overrides": {"surface_detail": {"enabled": true}}`. It works
on any garment or skin assignment through the same overrides.

## Garment detail types (T-068)

All generic and opt-in; with none of these types or fields, every existing spec builds exactly as before (no
character data in the code, every size is spec data scaled by the generic body measures).

**`sneakers`** (`garments/sneakers.py`). A low chunky shoe built around the `body_generic` foot rather than offset
from it, so it reads as a sneaker whatever the foot shape. Parts per foot: `main.<side>` (the upper: a dome over a
superellipse plan, open around the ankle), `sole.<side>` (a flat slab whose rim wraps up the upper), `toe_cap.<side>`
(a cap over the front of the upper; its edge follows the region boundary, not the face grid), `laces.<side>_<k>`,
`collar.<side>` (a padded roll around the opening) and `tongue.<side>`. Fields: `height_m`, `length_extra_m`,
`width_extra_m`, `plan_n`, `dome_n`, `toe_flare`, `toe_drop`, `sole {thickness_m, wrap_m, margin_m}`,
`opening {radius_m, length_m, offset_m}`, `toe_cap {length, slope, thickness_m}`, `laces {count, radius_m, span,
start, end}`, `collar {radius_m, rise_m, falloff_m, back_share}` (the upper rises around the opening into an ankle
collar, more at the heel), `tongue {width_m, thickness_m}`; any block can be `false`. Material parts: `main`, `sole`,
`toe_cap` (else `sole`), `laces` (else `band`, else `sole`), `collar`, `tongue` (else `main`). Pieces are rigid to the
foot; the foot inside the shoe is recorded as covered (masked when `hide_body_faces`).

**`backpack`** (`garments/backpack.py`). Worn through the clothing list, after the garments it sits on: the bag
(`main`, a superellipsoid whose body side is flattened onto the outer clothing) lies on the upper back, with a front
`pocket`, `zip.main`/`zip.pocket` with pullers and a top `handle`. Two `strap.<side>` run from under the bag's top
edge over the shoulder, down the front of the chest and back under the arm into the bag's side. The strap path is
projected from the torso skin through the clothing layers lying on it (`straps.layer_gap_m`; a sleeve beyond a larger
gap is never used) and passes under a hood. Bag, pocket, zips and handle are rigid to the upper back; every strap
vertex copies the weights of the nearest torso vertex (`ps_body_vertex`), never an arm vertex. Fields: `width_m`,
`height_m`, `depth_m`, `top_drop_m`, `clearance_m`, `roundness`, `puff`, `pocket {width, height, depth_m, drop}`,
`zip {radius_m, puller_m}`, `straps {width_m, thickness_m, shoulder, front_drop_m, lift_m, layer_gap_m}`,
`handle {radius_m, width_m}`. Material parts: `main`, `pocket`, `strap`, `zip` (else `band`), `puller` (else `zip`),
`handle` (else `strap`). A backpack covers no skin (`mask_body` is rejected). `accessories.py` (`accessories/1`)
rejects a `backpack/1` item with a pointer here: accessories are rigid to the head bone.

**Hoodie hood volume** (`hood`, `hoodie` only): `rim_back_radius_m` (thicker roll at the back and sides),
`bag_fullness` (switches the bag to a full pillow whose body side hugs the hoodie and the neck), `bag_rise_m`,
`bag_taper`, `bag_n`, `bag_gap_m`, `edge_radius_m`, `edge_drop` (the opening-edge roll on the bag). Without
`bag_fullness` / `rim_back_radius_m` the T-058 hood is built unchanged.

**`armhole: "closed"`** (`top`, `shirt`, `hoodie`, `dress` with sleeves): the torso panel keeps the faces of the
armhole region, so with a dropped shoulder the sleeve and torso panels meet under the arm and no skin shows there.
Default `"cut"` (unchanged). `sleeve_start` (0-0.1, `top`, `shirt`, `dress`; default 0.10) is the share of the arm
where the sleeve panel begins; 0 covers the whole shoulder cap (with `armhole: "closed"`, a sleeve without a gap at
the shoulder).

**Gathered skirt with hem rib** (`skirt`, and a `dress`'s skirt): `gathers {count, depth_m, waist_depth_m}` adds soft
outward folds (fullness) growing from the waist to the hem; `bands.hem_rib {height_m, ridges, relief_m, thickness_m,
lift_m, gather}` adds a knitted rib band (`band.hem_rib`, material part `band`) over the skirt's lower edge, with
vertical rib ridges; the folds are drawn in towards the band (`gather` = the share kept at the hem). Either field
switches the skirt to finer rings; without them the T-018 skirt is built unchanged.

**Vest details**: `pockets.shape: "patch"` (default `"puff"`, the ellipsoid pockets) makes flat patch pockets sewn
onto the panel, conformed to its surface, with rounded bottom corners (`corner`), a soft bulge (`depth_m`), an
optional rolled top edge (`top_roll_m`, part `pocket_edge`, else `edge`, else `pockets`) and a gap to the open front
(`inset_m`); the object names stay `pocket.<side>`, so embroidery targets and pocket buttons work unchanged.
Embroidery style **`cross_stitch`** is a counted cross-stitch decal from a `pattern` grid (rows of equal length;
`x` = embroidery material, `o` = accent, `.` = empty; at most 40 x 40) with cell size `stitch_m` (default
`size_m` / cells); every stitch is conformed to the target surface, so decals wrap curved panels, pockets and boots.
