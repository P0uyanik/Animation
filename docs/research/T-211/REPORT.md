# T-211 · Blender-first review of the ten face points (research)

Owner follow-up to T-209, 2026-11-22 ~20:35 CET: "research all 10 points specifically from the perspective of
Blender's capabilities … make full use of Blender's existing capabilities instead of unnecessarily developing
solutions from scratch." Research only. No change to characters, generators, packages or CURRENT versions.
Branch `t-211-claude-blender-first-faces` from `main@c90315a`. It builds on [T-209](../T-209/REPORT.md) (the ten
points, fit-and-lock, the drift probe) and [T-196](../../audit/T-196/REPORT.md) (the engine plans the motion; Blender
builds, measures and corrects) and does not repeat them. **M** = measured here with headless bpy 5.3.0 on CPU,
**E** = estimate. Effort is in task-days. Probes are in the appendix (about 5 min CPU in total).

## Short answer

1. **We are already Blender-first in most places.** The face is built in Blender with relative shape keys, Rigify
   deform bones and drivers. `tools/fit` already renders masks with Workbench object colours and projects points
   with `world_to_camera_view`. Our code uses `mathutils` BVH and KD-trees. All 365–417 drivers in each of the three
   masters are SUM, AVERAGE or *simple expressions* (M: no Python expressions). That matters, because simple
   expressions also run with Python auto-exec off, which is how our headless builds run.
2. **The one big Blender-first win is the planned regional knobs (T-209 P3).** Don't write our own falloff
   deformers. Use Blender's **deform-only modifiers** as the knobs: Warp or Hook with a radius falloff for regions
   (cheek, jaw corner, temple), and a **Lattice** for the free head outline (its points *are* the outline control
   points). On all three skins (88–110k vertices) these move **0.000 mm outside their region**, re-evaluate in
   **11–18 ms** after a knob change, and are deterministic (M). That is fast enough for the fit loop to search
   modifier parameters without rebuilding anything.
3. **Blender already "rebuilds the expressions on the fitted face".** Apply the knob as a shape key
   (`modifier_apply_as_shapekey`), then fold it into Basis in edit mode. Blender moves every key that is relative to
   Basis by the same offset. Error **0.0000 mm** on all three masters (M). Expression motion is unchanged, so the
   T-209 per-key identity budgets stay valid, and the engine export (morph deltas) needs no change.
4. **Features can follow a reshaped skin with Surface Deform** during the fit, so no rebuild is needed per try.
   A brow follows the skin within **0.06–0.13 mm** (M). On the two girls the skin has 242–243 n-gons, and Blender
   refuses to bind to those ("concave polygons"). A triangulated binding copy with the same vertices works.
5. **Keep our own code where Blender has no equivalent:** the lid-seam blink (closing angle computed from the lid
   meshes), the eye-opening shape and lid droop, in-between key chains (Blender has no native in-between shape keys),
   the expression library, the engine face layer (gaze, blinks, visemes) and the identity card logic. Don't adopt the
   Rigify face rigs, Pose Library, Damped Track gaze, fSpy, the Movie Clip solver, EEVEE on CPU or a Geometry Nodes
   face (reasons in section A).
6. **Revised plan "Blender-first fit-and-lock":** about **16–21 task-days instead of 20–25**, and **8–9 Opus + 5–7
   Sonnet sessions instead of 9–11 + 6–8** (E). The lower risk is in P3: we wire tested Blender deformers instead
   of writing and validating our own. Section B has the details.

## Probe results (M, bpy 5.3.0, CPU, appendix for scripts)

| Check | Boy 2.3.0 | Auburn 0.14.0 | White-haired 0.1.0 |
|---|---|---|---|
| Warp (30 mm, smooth falloff, 4 mm move): outside radius / body / ms per re-eval | 0.000 / 0.000 mm / 13 ms | 0.000 / 0.000 / 11 | 0.000 / 0.000 / 11 |
| Hook (same falloff) | 0.000 / 0.000 / 14 | 0.000 / 0.000 / 11 | 0.000 / 0.000 / 15 |
| Lattice 3×3×3 on a head vertex group (one point moved) | 0.000 / 0.000 / 18 | 0.000 / 0.000 / 14 | 0.000 / 0.000 / 17 |
| GN Set Position knob (exposed inputs) | 0.000 / 0.000 / 24 | 0.000 / 0.000 / 16 | 0.000 / 0.000 / 15 |
| Deterministic (same hash twice) | yes, all | yes, all | yes, all |
| `modifier_apply_as_shapekey`: Warp / GN | works, 0.01 s / **refused** ("only deforming modifiers") | same | same |
| Edit-mode Basis change propagated to dependent keys (max error) | 0.0000 mm | 0.0000 mm | 0.0000 mm |
| All keys baked *through* a live knob stack: time / far-zone max / key-delta change | 0.37 s / 0.007 / 0.42 mm | 0.50 s / 0.074 / 2.9 mm | 0.42 s / 0.020 / 1.6 mm |
| Surface Deform brow on skin: bound? follow error | yes, 0.057 mm | **no** (243 n-gons); triangulated copy 0.128 mm | **no** (242); copy 0.109 mm |
| Drivers: SUM / AVERAGE / simple / Python | 40 / 171 / 206 / **0** | 40 / 155 / 190 / **0** | 40 / 167 / 176 / **0** |
| L/R split via key `vertex_group` + "new shape from mix" vs a weighted copy | exact (3e-5 mm), other side 0 | same | same |

Measuring (auburn master, full character loaded):

| Check | Result |
|---|---|
| Render-free blink check: `scene.ray_cast` from 5 yaws onto the eyeball; visible eyeball points at face_Blink 0 → 1 | front 86 → **3** of 506; 3/4 near eye 94 → **8** of 519; side 53 → **5** of 510. Small leftovers at the corners or grazing rays. Check them in P4. 2.98 s for 20 views |
| Closed upper lid to eyeball (BVH `find_nearest`) | min 0.01 mm, median 1.38 mm |
| `LM_*` projection at 8 yaws | works, but `LM_eye`, `LM_mouth` and `LM_nose` are interior points, so the ray test marks them occluded. Occlusion needs points on the surface |
| Mask pass at 256 px, full master: Workbench object colour / Cycles 1 spp + Object Index + Cryptomatte / EEVEE 1 spp | **3.4 s** / 13.0 s / **103 s** (no Vulkan, software path) |
| Compositor ID Mask in background mode | works (2.0 s for a 64 px Cycles scene). The pass is called `Object Index` in 5.3, not `IndexOB`. Read the mask back from the written file |
| Inventory (factory startup) | bundled Rigify has `faces.super_face`, `face.skin_eye`, `face.skin_jaw`, `skin.*`. The `poselib.*` operators, `grease_pencil.trace_image`, `image.import_as_mesh_planes` and the `clip.*` solver are all present. fSpy is not bundled |

5.x API notes for implementers (M): Geometry Nodes modifier inputs are now `mod.properties.inputs.<identifier>.value`
(`mod["Socket_n"]` raises). `Scene.compositing_node_group` is deprecated for 6.0.

## A. The ten points: built-in way vs our own code

**1 · Reusable, parameter-driven generator.** *Built-ins:* deform modifiers (Warp, Hook, Lattice, Simple Deform,
Displace, Mesh/Surface Deform), Vertex Weight Proximity for falloff groups, Geometry Nodes, shape keys.
*Ours:* `face_generic/3` builds skin, lids, eyes, brows, mouth and keys from about 340 spec values.
*Verdict:* keep the generator as the source of truth. Make the *new* T-209 knobs (outline, regional shape) a spec
list of built-in modifiers, for example `{"type": "WARP", "at": "LM_mouth+offset", "radius_m": 0.03, "move_m": [..]}`
or `{"type": "LATTICE", "points": 4, "offsets": {...}}`. At build time they are applied as a key and folded into
Basis. Don't move the face into Geometry Nodes: GN results can't be applied as shape keys (M), and the engine needs
stable vertex order and keys (T-209). *E 2–2.5* (instead of 3–4). *Risk:* low. The knobs are inspectable in the GUI.

**2 · Matching the references.** *Built-ins:* camera background images and reference image empties (GUI only,
not rendered), Import Images as Planes (built-in in 5.3), fSpy importer (free, GPL-3, not bundled), Movie Clip
tracking and solving, Grease Pencil `trace_image` (potrace).
*Ours:* `tools/fit`, using Blender Workbench and `world_to_camera_view`, plus T-204's reference traces.
*Verdict:* fSpy and the clip solver need perspective lines or one rigid object in a moving sequence. Our references
are styled turnaround drawings, and their yaw, elevation and lens are already in the reference index. So neither
gives anything we don't have. GP tracing would turn our reference masks into curves, but our numpy outlines already
do that headless. **Adopt** the knob search from point 1: the fit can search Warp and Lattice parameters at
11–18 ms per try with no rebuild. Use Surface Deform on a triangulated copy so lids, brows and glasses follow
inside the loop. Use planes in a Workbench render only for overlay review sheets, if wanted. *E:* no change
(2 + 0.5 per character). The sensitivity matrix over knob parameters takes seconds, not 30 builds.

**3 · Independent geometry controls.** *Built-ins:* Warp and Hook falloff (zero outside the radius), a Lattice on a
vertex group (zero outside the group), Simple Deform (taper, bend) and Displace with a vertex group, and attribute or
weight painting for hand-made regions. *Ours:* spec values feeding one outline function (they interact), and the
planned compact-falloff deformers. *Verdict:* **replace the planned deformers with Warp, Hook and Lattice.**
Independence is then exact by construction (0.000 mm off-region, M), and the drift probe's zone check stays as the
gate. The older spec knobs stay as they are (released versions are immutable). *Saves about 1–1.5 days.* *Risk:*
falloff shapes are fixed curves (smooth, sphere, root, sharp, linear, or a custom curve), which is enough for felt
plush.

**4 · Eye system.** *Built-ins:* Rigify `face.skin_eye`, Damped Track and Track To constraints, Copy Rotation with
influence (partial lid tracking), drivers. *Ours:* felt and layered eye shaders, trimmed lid shells, lid-seam blink,
`lid_bindings` tracking 0..1, and engine blinks and saccades. *Verdict:* keep ours. The engine plans gaze and writes
`DEF-eye` rotations into the bake, and the bake mutes constraints (T-196), so Damped Track would make two places
decide the gaze. Rigify skin eyes are bone-driven lids, which would duplicate the lid-seam work. **Adopt** the
render-free blink check: `scene.ray_cast` at 5 yaws plus BVH lid clearance. It costs 3 s and is gate-friendly
(M: 3–8 eyeball points still visible at Blink 1 on auburn, to be looked at in P4). This replaces T-209's
Workbench-mask sclera count. The eye-opening superellipse and lid droop stay our code (the lids are generated
shells). *E 1–1.5.*

**5 · Expression shape keys.** *Built-ins:* relative keys, "New Shape from Mix", a per-key `vertex_group`, Corrective
Smooth, drivers, apply-as-shape-key, edit-mode Basis propagation. *Ours:* the action-unit library, presets,
in-between chains `X@NN` with hat drivers, the L/R split, and pout. *Verdict:* keep the library and the in-between
chains (Blender has no native in-betweens). After a rest-face change, **use edit-mode Basis propagation** to carry
pure-delta keys onto the fitted face (0.0000 mm, M). Keys computed from the lids (blink) are still rebuilt by the
generator. Our L/R split duplicates key `vertex_group` + from-mix exactly (M). Replace it only if `face_generic/4`
touches that code anyway (about 45 lines, low value). Make combination correctives simple-expression drivers
(`a*b`, `min(a,b)`, `smoothstep`, all simple, M). Leave Corrective Smooth off the face: it changes only the Blender
render, not the engine's morphs, and the face has no joint folds. *E 1.5–2.*

**6 · Facial rig.** *Built-ins:* Rigify `faces.super_face` (legacy), `skin.*` chains, bone collections, Pose
Library and the Asset Shelf. *Ours:* Rigify deform rig, `face_<X>` properties driving keys, the jaw bone with preset
drivers, the engine `face_layer` and visemes. *Verdict:* keep it. Bone-based face rigs give the engine bones, but it
needs morph targets and controls. Pose Library and the Asset Shelf only help a person posing by hand in the GUI, and
nobody does (T-196). Put the face controls in a bone collection only if a GUI pose panel is ever wanted. Viseme
mapping (`MouthO`, `MouthPout`) is engine data, as in T-209. *E 0.5–1.*

**7 · Automation.** *Built-ins:* bpy headless, GN Bake nodes and modifier bakes, node-tool operators. *Ours:*
everything is already headless bpy 5.3, single-thread and deterministic. *Verdict:* no change. GN bakes belong to
the strands and flock (T-207), not the face skin. Node tools are interactive GUI operators. *E 0.*

**8 · Identity preservation.** *Built-ins:* linked libraries and library overrides (linked data is read-only),
evaluated depsgraph, BVH and KD-trees, the Asset Browser. *Ours:* `fingerprint_v2`, immutable version folders, and
the planned identity card. *Verdict:* identity is already locked the Blender way: shots link the immutable master
through overrides. The card itself must stay our data and our check, because Blender has no notion of "this face".
Build it from Blender parts: evaluated meshes at sampled bake frames, `ray_cast` visibility, BVH distances. The
Asset Browser adds nothing for headless reuse. *E 1.5–2.*

**9 · Validation at all angles.** *Built-ins:* Workbench object colour, Cycles Object Index and Cryptomatte, the
compositor ID Mask, `world_to_camera_view`, `scene.ray_cast`. *Ours:* T-202 sheets, `tools/fidelity`, the T-204
traces. *Verdict:* per check, **Workbench** object colour for masks (3.4 s at 256 px on the full master, much less
head-only). **Cycles** Object Index or Cryptomatte only where Workbench is wrong, such as transparent lenses (13 s).
**No EEVEE** in the cloud: 103 s on the software path. Geometry checks (blink, clearance, occlusion) are ray casts
with no render. Landmarks need surface points for occlusion tests, because `LM_*` are centres. *E 2–2.5* (instead
of 3–4 for the T-209 P1 measurer).

**10 · Production integration.** Everything above ends as the same data the engine reads today: Basis plus relative
keys, `face_*` properties, simple drivers, and `ps_engine_expressions`. `export_engine.py` reads key blocks, so knob
modifiers must be **applied and folded at build time, never left live** in the master. Otherwise the render and the
engine morphs would disagree. Licences: Blender, bundled Rigify and Pose Library are GPL-3, and their outputs
(meshes, renders) are unrestricted for commercial YouTube use. The fSpy importer and app are GPL-3, SKkeeper is
GPL-3 and ApplyModifierForObjectWithShapeKeys is MIT. All are free and none is needed. No paid add-ons are involved.

## B. Revised recommendation: Blender-first fit-and-lock

| Phase | T-209 | Blender-first change | E (T-209 → T-211) | Sessions (E) |
|---|---|---|---|---|
| P0 | owner decisions, merge T-204 | plus decision 7 below | 0.5 → 0.5 | Supervisor |
| P1 measurer | object-ID masks + `LM_*` projections at 8 yaws | Workbench object colour (as in `tools/fit`), plus `ray_cast` visibility on new surface landmarks and BVH distances. Cycles Object Index only for lenses | 3–4 → **2–2.5** | 1 Opus |
| P2 fit | F2 sensitivity matrix from about 30 builds, then CMA/Powell over spec values | spec values as before, **plus** live Warp/Lattice knob parameters (11–18 ms per try, no rebuild). Features follow through Surface Deform on a triangulated copy. Matrix in seconds | 2 + 0.5/char → **2 + 0.5/char** (faster runs, same dev) | 1 Opus + 2 Sonnet |
| P3 `face_generic/4` | our own outline control points and compact-falloff deformers; lid shape; glasses | `face.knobs` spec list → **built-in Warp, Hook and Lattice**, applied as a key and folded into Basis (dependent keys follow, 0.0000 mm). Our code only for the eye-opening superellipse, lid droop and glasses frame | 3–4 → **2–2.5** | 1–2 Opus |
| P4 expressions and rig | rebuild keys; 2–4 correctives; blink check from Workbench masks | pure-delta keys carried over by Basis propagation (only lid keys rebuilt); correctives as simple-expression drivers; **render-free ray-cast blink check** | 2–3 → **1.5–2.5** | 1 Opus |
| P5 identity card | card + gate + shot check | same, built from evaluated depsgraph, BVH and `ray_cast` | 2 → **1.5–2** | 1 Opus + 1 Sonnet |
| P6 release | per character | no change | 1–2/char → 1–2/char | 1–2 Opus + 2–3 Sonnet |

**Total: about 16–21 task-days instead of 20–25 (about 4 saved), 8–9 Opus + 5–7 Sonnet sessions instead of 9–11 +
6–8 (E), about $170–360 instead of $200–420 (E, scaled from T-209).** *Risk change:* P3 drops our largest new-code risk
(own falloff deformers and their off-region tests), and P2 needs fewer rebuilds. New risks are small. (a) Knob
modifiers left live would split render and engine, so add a build test that the master has no knob modifiers.
(b) Surface Deform needs a triangulated binding copy on the girls. (c) There are 5.x API changes (GN inputs, the
compositor group). Bpy is pinned at 5.3, so this only matters on a version bump.

**Where Blender genuinely can't do it, and why.** Landmarks on stylised references: no built-in detector (T-204
traces once). In-between shape keys: none native, so we keep our `@NN` chains. Lid closure geometry: the
computed lid-seam angle is our model. GN knobs as keys: refused by apply-as-shape-key (M). GN would need our own
capture, so use deform modifiers. EEVEE on cloud CPU: 30× slower than Workbench (M). Gaze and blinks in Blender:
the engine needs to plan them, and the bake mutes constraints. Identity as a concept: needs our card.

## C. Owner decisions (in addition to T-209 section D)

7. Approve **built-in deform modifiers (Warp, Hook, Lattice) as the `face_generic/4` shape knobs**, applied and
   folded into the stored face at build time, in place of our own deformers.

## Appendix

**Files** (`probes/`): `inventory_probe.py` → `inventory.json` (operators, bundled add-ons, Rigify face rigs,
simple-driver evaluation with auto-exec off). `deformer_probe.py` → `deformers_<id>.json` (knobs, keys through the
stack, apply-as-shape-key, Basis propagation, Surface Deform). `measure_probe.py` → `measure_girl_auburn_bun_glasses.json`
(ray-cast blink check, BVH lid clearance, landmark projection, Workbench, Cycles and EEVEE mask timings; the EEVEE
row comes from the first run of the same script). `compositor_probe.py` → `compositor.txt`. `driver_probe.py` →
`drivers.txt` (driver kinds, L/R split via key vertex group). All of them are read-only on the masters and never save.

**Reproduce** (repository root; master paths must be absolute):

    blender -b --factory-startup -P docs/research/T-211/probes/inventory_probe.py -- docs/research/T-211/probes/inventory.json
    blender -b --factory-startup -P docs/research/T-211/probes/deformer_probe.py -- $PWD/assets/characters/<id>/versions/<v>/<id>_master.blend <out.json>   # ~5 s
    T211_SKIP_EEVEE=1 blender -b --factory-startup -P docs/research/T-211/probes/measure_probe.py -- <master> <out.json> <scratch dir>   # ~25 s; ~2 min with EEVEE
    blender -b --factory-startup -P docs/research/T-211/probes/compositor_probe.py -- <scratch dir>
    blender -b --factory-startup -P docs/research/T-211/probes/driver_probe.py -- <master>

**Licences checked 2026-11-22** (LICENSE files via raw.githubusercontent.com): fSpy app and fSpy-Blender importer
GPL-3. SKkeeper GPL-3. ApplyModifierForObjectWithShapeKeys MIT. Blender, Rigify and Pose Library are GPL-3 and
bundled. Blender's GPL does not cover its output, so commercial use of renders and meshes is fine.

**Hosts.** Blocked by the proxy (curl status 000): `extensions.blender.org`, `docs.blender.org`,
`projects.blender.org` (the 5.3 manual and the extension site would have been useful for API checks, so the API was
probed directly instead). `api.github.com` returned 403. Reachable: `raw.githubusercontent.com`, `github.com`.
None of the blocked hosts is needed for the recommendation.
