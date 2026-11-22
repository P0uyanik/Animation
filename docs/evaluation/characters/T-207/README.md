# T-207: velvet / flock hair looks (hair step H1, opt-in)

Owner direction 2026-11-22 ~19:10 CET ([OWNER_DECISIONS](../../../process/OWNER_DECISIONS.md)): the reference hair reads
as **velvety / flocked**: short, dense, soft fibres with a velvet-like sheen. It does not read as long combed yarn.
T-206 probe D is not locked. All views are weighted equally. This task builds three candidate looks as an **opt-in**
groom option and puts them next to the references, today's release and T-206's probe D. **The owner picks from the
sheets. Nothing here is a default or a new character version.** Released packages, bakes, goldens and episodes are
not touched.

## Sheets (pick from these)

| Character | All views (reference \| current \| V1 \| V2 \| V3 \| D × front / 3/4 / side / back) | 100 % close-ups |
|---|---|---|
| girl_auburn_bun_glasses 0.14.0 | [girl_hair_looks.jpg](sheets/girl_hair_looks.jpg) | [girl_hair_100.jpg](sheets/girl_hair_100.jpg) |
| boy_yellow_hoodie 2.3.0 | [boy_hair_looks.jpg](sheets/boy_hair_looks.jpg) | [boy_hair_100.jpg](sheets/boy_hair_100.jpg) |
| girl_white_hair_blue_dress 0.1.0 | [third_hair_looks.jpg](sheets/third_hair_looks.jpg) | [third_hair_100.jpg](sheets/third_hair_100.jpg) |

Renders: 768 px, Cycles 16 spp + OIDN, CPU with 4 threads, one render at a time, T-202 camera (70 mm) and
character_neutral/1 light, neutral face, master A-pose. Each tile shows its seconds per frame. Close-ups are 384 px
crops at 100 % of those renders. The reference close-up (G04 / B04 / W04 upload) is scaled. All four views have a
reference (the back views come from the sheet back views).

## The looks

| Look | What it is | Strands (girl / boy / third) | Render time vs current, sum of 4 views (girl / boy / third) |
|---|---|---|---|
| current | released groom: felt + halo + flyaway fibre layers on the lock meshes | 296k / 435k / 1.39M | — |
| **V1 flock** | dense short fibres (2.5–5 mm, 0.11 mm radius, 300k/m²) lying at about 22° along the lock flow, slight frizz. Felt, halo and flyaway layers hidden. Mild sheen on the lock shader, softer dark breakup | 683k / 500k / 1.04M | +4 % / −7 % / −16 % |
| **V2 velvet shader** | shader only: albedo breakup 0.8–1.2 (was 0.1–1.9), sheen 0.8–1.0 with a lighter tint, stronger fresnel rim, finer micro-normal. Felt fuzz kept at 0.6 length and 0.25 density. Halo and flyaways hidden | 69k / 104k / 511k | −13 % / −16 % / −29 % |
| **V3 flock + edge fuzz** | V1 plus a sparse layer of longer (up to 11 mm), finer, brighter, frizzed fibres. It grows only where the **rest mesh is convex or open**: lock edges, rounded rims, tips, sheet borders. The selection is a mesh attribute and never depends on the camera or the light | 810k / 549k / 1.11M | +16 % / 0 % / −9 % |
| D combed (T-206) | T-206 probe D: hair_curves strands combed along the locks (`options/hair_curves/D_combed.json`, plus hair_bow skipped), felt and halo at half length and ×0.7, flyaways ×0.2 | 377k / 419k / 1.25M | +29 % / +3 % / +19 % |

What the sheets show (my reading; the owner decides):
- **V1 and V3** turn the "carpet" fuzz into a smooth, brushed velvet surface. At 100 % the short fibres give a fine nap
  with a direction along the lock. V3's edge fuzz is subtle under this front-ish key light. It shows mostly on the
  silhouette (bun rims, ringlet edges), not as a halo.
- **V2** is the lightest and smoothest, close to suede or velvet, and the cheapest to render. The lock-shape modelling
  shows more clearly here than in any other look.
- **D** keeps the strongest visible fibre direction (combed yarn), which the owner said is not the target.
- **Boy:** the reference is a fluffy fleece / terry texture. Today's release is closer to it than V1–V3 are. The
  velvet looks make his spiky locks read as smooth sculpted shapes.
- **Third character:** all looks are close. V1/V3 soften the lock texture, V2 brightens it.
- **Still missing in every look:** the bright, soft fuzzy halo in the reference photos. It comes mostly from their
  strong backlight, which our neutral light does not have. The volume is also unchanged in every look (flock adds
  ≤ 5 mm), so the hair stays larger than in the references. That is hair step H2, its own task after T-183/T-194.
- **Seen once the fuzz is reduced (V1/V2/V3):** a stair-step edge at the girl's forehead hairline (fringe/cap mesh
  border). Today's halo fibres hide it. It belongs to the mesh, not the look. Fix it in H2, or keep the edge fuzz
  denser on open borders.

## How it is built

`pipeline/charsys/groom/flock.py` (new). Options `"plush-studio.hair-flock/1"`, with every block optional
(`velvet`, `fibres`, `flock`, `edge`):
- **velvet** sets named `PS …` nodes of the hair meshes' own lock material (`M_hair`): albedo variation, roughness,
  nap sheen, sheen roughness and tint, rim weight and power, bump strengths. A node a material lacks is reported, not
  added.
- **fibres** hides or scales the existing `PS Shared Surface Fibres/1` layers by their `ps_groom_fibres` name.
- **flock / edge**: strands are made in numpy in the mesh's **rest shape**. Roots are area-weighted and seeded per
  mesh and layer. Each strand leans along the lock flow (`ps_fibre` V, else dynamics chain, else down; the same flow
  field as T-141), with seeded spread, lean and length. Faces hidden under other hair, the body or garments get no
  strands: a ray along the face normal hits a rendered mesh within 4 mm. Blender's own `Frizz Hair Curves` and
  `Set Hair Curve Profile` node groups follow. T-141's `Follow Surface` node group then moves the strands with the
  deformed mesh. The fibres use the mesh's felt-fibre material (Principled Hair BSDF), with a `ps_fibre_tone` attribute.
  The edge layer uses a tone/roughness-scaled copy.
- **Edge mask**: per-vertex mean convex curvature from the vertex normals (a sphere of radius R gives 1/R), turned
  into a weight by a smoothstep over [25, 110] /m, with weight 1 on open borders and a 0.03 base. Rest mesh only.
- Options: [options/V1.json](options/V1.json), [V2.json](options/V2.json), [V3.json](options/V3.json),
  [D.json](options/D.json) (fibre part of D) and [hair_curves/D_combed.json](options/hair_curves/D_combed.json).

**Groom key (opt-in), absent = today's build.** `flock.apply_spec(hair_spec, objects)` returns `None` and touches
nothing when `hair_spec` has no `"flock"` key. Tested: the scene hash over every object, mesh, curves count, modifier
input, material node input and node group is unchanged. Wiring it into the build needs a hook in `groom_r6.py`
(owned by T-183), so it is a patch here and not an edit:
[groom_r6_flock_hook.patch](groom_r6_flock_hook.patch). `build()` becomes a wrapper. Without the key it calls the
unchanged body (`_build`) with the same arguments. With the key it validates the options, builds without the key,
then applies the finish to the built objects. It applies cleanly to a40db3b (`git apply --check`). Re-check after
T-183 merges.

## Determinism and cost

- Two separate builds per character and look gave the same hashes ([results.json](results.json), `two_run_hash`).
  V1 and V3: identical rest-strand sha and evaluated-point sha for all three characters (e.g. girl V1
  `31012aff…` / `325f303f…`, V3 `dc7b7082…` / `bda86507…`). D (hair_curves): identical guide, curve and point counts. A
  third V1 girl build during tuning also gave `31012aff…`. Strands do not depend on the camera (tested with two
  cameras).
- Build time of the finish: 4–6 s per character. Render time is in the table above and per tile.
- The review renders use all cores and are not bit-exact (like T-202 / T-206). The hashes cover the strand geometry.

## Tests

- `pipeline/charsys/tests/test_hair_flock.py` (new, 39 checks, Blender part on a synthetic tube): validation, absent
  key = bit-identical, null blocks change nothing, two-run hash, camera independence, other seed = other strands,
  strand count = density × area, roots on the surface, short strands leaning along the flow, felt hide/scale, velvet
  set/missing, follow under a bone bend (same counts, roots stay on the bent surface), hidden-face cull under a
  sleeve, convexity 1/R on a sphere, edge weight on a plane and its border, CLI refuses to overwrite its input or
  write into assets/characters. Registration in the TESTS manifest is left to the Supervisor (T-203 renames it).
  Suggested line: `blender test_hair_flock.py hair-curves`.
- `test_hair_curves.py`: the "groom/ holds only hair_curves.py" check now allows `flock.py`, and the "no shared code
  references it" scan skips the groom/ folder and the flock test (37/37 pass).

## Expected contact impact (checks after T-183/T-194 merge)

Flock fibres sit 0.2 mm above the lock surface and reach ≤ 5 mm (V3 edge ≤ 11 mm before frizz). They are render-only
curves: no collision shapes, no dynamics chains. Lock meshes, colliders and dynamics are unchanged. Expected:
hair-vs-body contact numbers unchanged. Fibres on lock undersides can poke into the collar or shoulders by up to the
fibre length, as today's halo and flyaway fibres already do. The hidden-face cull removes fibres on faces already in
contact at rest.

## Reproduce (repository root, scratch output)

    docs/evaluation/characters/T-207/sheets.sh girl <work dir> 768 16     # also boy, third
    python3 docs/evaluation/characters/T-207/compose.py <work dir>
    python3 pipeline/charsys/tests/test_hair_flock.py

`sheets.sh` builds V1–V3 with `flock.py --options options/<look>.json`, and D with `hair_curves.py` +
`flock.py --options options/D.json`, then renders with `render_views.py`.
