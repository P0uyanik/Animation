# T-193: ready-made hair systems instead of our own? (research)

Owner, 22 Nov ~04:20 CET: look for existing code, open-source libraries and ready-made hair systems that we could
use instead of building our own, and compare them with continuing T-183. Research only: nothing in the pipeline,
packages, bakes or goldens changes. Date of all checks: **2026-11-22**.

## Short answer

- **Nothing on the list can be dropped in and fix the problem.** Every system we can use (open-source or bundled with
  Blender) either uses the same kind of colliders we already have (spheres and capsules on bones), or is
  experimental and showed new problems in a small test (hair stretched to 2.4 times its length, ringlets tangled
  into a ball, locks thrown upwards).
- **Why the owner still sees hair in the table and in her body:** T-183 measured one shot (`e909 s010`, no table),
  and our hair only collides with spheres riding on her bones. The engine has no colliders for props such as a
  table, and spheres cannot follow every fold of a body, a garment or a bent back.
- **Recommendation: hybrid.** Keep our engine chain solver for the motion (it is deterministic, baked and already
  in the pipeline). Add one new step at render time in Blender: after each frame's bones are set, push every lock
  out of the **real meshes** (body, garments and props such as the table), keeping each lock's length. In a small
  test this took ringlets from 120 of 120 frames inside the body (up to 67 mm) to **0 frames**, with the curls'
  shape and length unchanged, and the same result on every run. It does not need hand-made spheres for props.
  Estimate **3-4 task-days**, details below.
- **Keep watching Blender's own new hair simulation** (bundled with Blender 5.3, marked "Experimental"). It is the
  most promising ready-made option for later, not for now.

## What was tested (small headless scenes in bpy 5.3.0, the same build as `tools/bpy_blender.py`)

Scene for all tests: a soft torso (a 0.24 m wide cylinder skinned to three bones, so it bends like a body), a
head on top, eight locks 0.32 m long rooted on the head (four in front and at the sides, four at the back), and a
table in front. Over 120 frames she stands still, leans forward over the table (frames 24-56), holds the lean
and straightens up (88-120). The locks are either a **guide** (a 16-point centre line, like one of our chains) or
a **ringlet** (a 48-point spiral, 15 mm radius, 5 turns). Each test measures, every frame, how many hair points
lie more than 1 mm inside the torso or the table, how deep, how much the locks stretch, and a SHA-256 of all hair
positions to check that a second run gives the same result.

| Test | Torso: frames with hair > 1 mm inside, worst depth | Table | Lock length, worst | Same on 2nd run | Time (120 frames, 8 locks) |
|---|---|---|---|---|---|
| Locks fixed to the head, no contact (what goes wrong) - ringlets | 120 of 120, 66.6 mm | 0 | 1.00 | - | - |
| **Contact push-out on the real meshes** (hybrid) - guides | 8, 3.2 mm | 0 | 1.00 | yes (stateless) | 0.5 s |
| **Contact push-out on the real meshes** (hybrid) - ringlets | **0** | 0 | 1.00 | yes (stateless) | 1.9 s |
| Blender GN *Hair Dynamics*, default steps (10 x 15) - guides | 29, 3.6 mm | 0 | **1.31** | yes | 15 s |
| Blender GN *Hair Dynamics*, 30 x 30 steps - guides | 33, 6.4 mm | 0 | **2.40** | yes | 25 s |
| Blender GN *Hair Dynamics*, 30 x 30 - ringlets | 61, 18.5 mm | 0 | **1.76** | yes | 28 s |
| Blender GN *Hair Dynamics*, 30 x 30 + "Edge Contacts" - guides (first scene) | 35, 46.2 mm | 0 | 1.58 | - | 132 s |
| Blender **Cloth** on one ribbon per lock (quality 10) | 1 (rest pose only), 3.5 mm | 0 | 1.00 | yes | 12 s |

All numbers: `results/T-193_probe_summaries.json`. Scripts: `tests/` (throwaway, not part of the pipeline).
Frames from the side (front of her to the right, table in beige, body points in grey):

- `T-193_projection_vs_gn_guide.png` - top row: contact push-out on ringlets (pink: locks fixed to the head,
  passing through her back; blue: after the push-out, lying on her back with their curls intact). Bottom row:
  Blender Hair Dynamics on guides; the locks move naturally, but some stretch and one is thrown back over her
  head (f72).
- `T-193_gn_ringlet_vs_cloth_ribbon.png` - top row: Blender Hair Dynamics on ringlets: in the lean the curls
  tangle into a ball at her neck and stay bunched after she straightens (f110). Bottom row: Cloth ribbons: locks
  thrown upwards and sideways in the lean (f50, f72), stuck forward after it (f110); with no head collider (it
  had to be removed, because the pinned roots sit inside the head and the ribbons blew up) the ribbons also pass
  through the head (120 frames, up to 81 mm).

What the tests do **not** show: the push-out test moves locks that are fixed to the head, so it shows contact
only, not swing (in production the swing comes from our engine bake). In the final scene no rigidly-fixed lock
reached the table, so the table push-out was not exercised (the table is just one more mesh to it); the
simulations did drop locks onto the table, with 0 mm inside it. An earlier version of the scene had the bent
torso sinking into the table; hair squeezed between two overlapping solids could not get out (up to 20 mm). The
same will happen in real shots wherever the body or a garment already passes through a prop.

## Ranked options

| # | Option | Look (clumped plush locks, ringlets) | Contact: body, garments, props | Deterministic, headless bpy 5.3, fits the engine bake | Licence | Maintenance / lock-in | Effort |
|---|---|---|---|---|---|---|---|
| 1 | **Hybrid: our engine solver + Blender contact push-out on real meshes** (new, small) | Keeps today's lock shapes; push-out moves whole lock centre lines, curls ride along | Any mesh: body, garments, table, chairs; per frame | Yes: stateless per frame, same result every run; runs in `shot_render.py` after the bones are set | Ours | Ours, ~300 lines | **3-4 task-days** |
| 2 | **Blender GN *Hair Dynamics*** (bundled in 5.3 `geometry_nodes_dynamics_assets.blend`, XPBD solver, "Physics (Experimental)") | Guides move naturally; ringlets tangle (no lock-vs-lock contact); stretch 1.3-2.4 x under contact | Mesh colliders incl. deforming ones; **closed meshes only** (manual); garments are open shells and would need thickening | Yes (same hash twice), headless works; but the hair state lives in Blender, not in the engine bake (motion checks, previews and the engine would not see it) | Part of Blender (GPL); renders are not affected. Licence of the bundled asset file not checked (blender.org blocked) | Experimental: "may change significantly" | 6-10 task-days + retuning when Blender changes |
| 3 | Wiggle 2 and its forks (bone springs in Blender; one-click bake to keys) | Same chain idea as ours | Per-bone head/tail spheres against collision objects | Runs in frame handlers of an add-on; bake works headless in principle (not tested) | GPL-3 (fine for our renders; the add-on code would have to stay GPL in the repo) | Original last commit 2024-04-18; several community forks for 4.2-5.x | 3-5 task-days, little gain over ours |
| 4 | VRM spring bones (VRM add-on for Blender, `spring_bone1`) | Same chain idea as ours | Spheres and capsules only, exactly like ours | Frame handlers, live in the viewport | MIT or GPL-3 (dual), active (commit 2026-11-21) | Active | No gain: same collider model |
| 5 | Blender Cloth / Soft Body on ribbons or lock tubes | Ribbons can carry a lock; tubes are heavy | Mesh colliders; pinned roots inside the head cause blow-ups; unstable in our lean | Yes (same hash twice), point cache | Part of Blender | Stable, old | 5-8 task-days of tuning, uncertain |
| 6 | PositionBasedDynamics library (C++, Cosserat rods, Python bindings `pyPBD`) | Rods with bend and twist | Distance-field colliders (would need SDFs of body and props per frame) | Deterministic CPU; would sit in the engine | MIT | Active (commit 2026-09-01) | 10-15 task-days |
| 7 | NVIDIA Warp / Newton (cable and rod solvers) | Rods, cables | Mesh and SDF contacts | GPU-first; large dependency | Apache-2.0 | Very active | 10-15 task-days |
| 8 | Research code: dismech-rods (discrete elastic rods), libWetHair | Physically accurate rods | Limited | C++ research builds | dismech-rods **GPL-3**; libWetHair MPL-2.0 | Research | Not worth it |
| 9 | AMD TressFX 4.1 | Real-time game hair | GPU, capsule/SDF colliders | DirectX 12 / Vulkan, Windows; no headless CPU path | MIT | Last commit 2020-01-24 | Not usable here |
| 10 | Paid: Houdini Indie (Vellum hair), Ornatrix, HairFarm | Excellent | Excellent (Houdini) | Separate application; Houdini Indie is limited to under $100k revenue a year; Ornatrix is for Maya / 3ds Max / Cinema 4D / Unreal (no Blender build found); HairFarm is a 3ds Max plug-in | Commercial | Lock-in, yearly fees (Houdini Indie about $299 a year) | Pipeline rewrite; not recommended |

## Recommendation and plan (option 1, hybrid)

Keep T-183's engine chain solver (motion, anchors, preroll, determinism; `docs/SECONDARY_MOTION.md`). Add a contact
step at render time that works on the real meshes:

1. **Contact push-out on chain joints** (1.5-2 task-days). In `pipeline/charsys/shot_render.py`, after
   `apply_frame` has set the bones for frame *f*: evaluate the body, garment and prop meshes (props are already
   loaded by `setup_props`), build one BVH per mesh, and walk every `DYN-*` chain from its root: keep each segment's
   length; a joint closer than its *core* radius plus a margin to a surface is pushed out along the surface normal;
   rewrite the pose-bone rotations and key them. Use a small core radius (the lock's inner bundle, ~10-15 mm), not
   T-183's outer spiral radius (up to 53 mm), so the locks do not stand off and fan out. Output for frame *f*
   depends only on the bake at *f* (optionally *f-1..f+1* for smoothing), so render order and restarts do not
   change it. Opt-in per shot, like T-183.
2. **Fibre-level touch-up** (1 task-day). A Geometry Nodes step on the hair fibres: the few curl points that still
   sit inside a surface after step 1 are pushed out, with a falloff along the strand so curls do not crease.
3. **Measure and show** (0.5-1 task-day): T-183's `measure_body.py` extended with props (table), on `e909 s010`
   plus one shot at a table; before/after close-ups as the owner asked in round 2.

Optional, later: give the engine solver static box/plane colliders taken from the scene's props (about 1 task-day)
so the swing itself already reacts to the table, and the push-out has less to correct.

**Effort: 3-4 task-days** (steps 1-3), against an open-ended fifth-plus round of sphere tuning in T-183, and against
6-10 task-days plus ongoing risk for switching to Blender's experimental Hair Dynamics.

## Risks

- **No sliding or bounce from the push-out.** It corrects position only; a lock pushed out of the table does not
  slide or settle the way a simulation would. It can pop when contact starts or ends; smoothing over neighbouring
  frames helps. If the look is not enough, the engine colliders for props (optional step) give the motion itself.
- **Overlapping solids.** Where the body or a garment already passes through a prop (e.g. a thigh through a table
  edge, the seated thigh through the shorts in T-184), hair squeezed in between cannot be outside both. The test
  scene showed this until it was fixed. Body/prop contact has to be right first.
- **Hidden skin residue from T-183** (neck skin folding over the hairline) is a body-skinning issue and stays.
- **Render time:** BVH builds of body and garments per frame, a few seconds per frame at full resolution
  (to be measured in step 3).
- **GN Hair Dynamics** may change in a later Blender; if it matures (no stretch under contact, lock-vs-lock contact,
  open meshes), it could replace the engine solver for hair. Re-test on each Blender update (the probe script
  takes a minute).

## Questions for the owner

1. Approve the hybrid (engine motion + render-time push-out on real meshes, 3-4 task-days)?
2. Is "hair lies on the table / on her back without sliding" acceptable for now, or must the hair visibly slide and
   settle on props (then add the engine prop colliders, about +1 task-day)?
3. Which shots with a table should be the test shots, besides `e909 s010`?
4. Paid tools (Houdini, Ornatrix, HairFarm) are not recommended (separate applications, yearly fees, no Blender
   pipeline). Keep them off the table?

## Network: what was reachable from this container (2026-11-22)

Reachable: `pypi.org`, `gitlab.com`, `registry.npmjs.org`, `proxy.golang.org`, `archive.ubuntu.com`, and git
transport to `github.com` (used for shallow, no-checkout clones of licence and README files only; nothing was
built or run). Facts about blocked sites were taken from a web search tool, not fetched from here.

Blocked by the agent proxy ("no rule or network setting allows this host") or no answer; not worked around:

| Host | Why we would want it |
|---|---|
| `www.blender.org`, `docs.blender.org`, `projects.blender.org`, `download.blender.org`, `studio.blender.org` | Blender manual for Hair Dynamics, release notes, bundled asset licence |
| `extensions.blender.org` | Wiggle 2 forks, other physics add-ons |
| `github.com` (web pages) and `api.github.com` | Release pages, issues (git transport works) |
| `gpuopen.com` | TressFX documentation |
| `ephere.com`, `hairfarm.ms` | Ornatrix / HairFarm product pages and prices |
| `www.sidefx.com` | Houdini licences and prices |
| `superhivemarket.com`, `blendermarket.com` | Paid Blender hair add-ons |
| `vrm.dev` | VRM spring-bone specification |
| `arxiv.org`, `www.cs.columbia.edu` | Papers (discrete elastic rods, wet hair) |
| `huggingface.co`, `www.youtube.com`, `www.google.com`, `crates.io`, `deb.debian.org` | Not needed for this task (only probed) |

## Sources (checked 2026-11-22)

- Blender 5.3.0 bpy wheel in this container: `datafiles/assets/nodes/geometry_nodes_dynamics_assets.blend`
  (node groups *Hair Dynamics*, *Collider*, *XPBD Solver*, *Rod Bend/Twist Constraint*, ...) and
  `procedural_hair_node_assets.blend` (*Attach Hair Curves to Surface*, *Clump*, *Curl*, ...). Read directly.
- Blender manual, *Hair Dynamics* node (5.3): experimental, XPBD solver, "only colliders with closed meshes are
  supported", residual error should stay below 1 -
  [docs.blender.org/manual/en/5.3/.../hair_dynamics.html](https://docs.blender.org/manual/en/5.3/modeling/geometry_nodes/simulation/hair_dynamics.html) (via web search; host blocked here).
- Blender 5.0 Geometry Nodes release notes (bundles and closures, the base of the dynamics assets) -
  [developer.blender.org/docs/release_notes/5.0/geometry_nodes](https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/).
- Wiggle 2: [github.com/shteeve3d/blender-wiggle-2](https://github.com/shteeve3d/blender-wiggle-2) (GPL-3, last
  commit 2024-04-18, read via git); forks for Blender 4.2-5.x on
  [extensions.blender.org/add-ons/wiggle-2](https://extensions.blender.org/add-ons/wiggle-2/) (via web search).
- VRM add-on: [github.com/saturday06/VRM-Addon-for-Blender](https://github.com/saturday06/VRM-Addon-for-Blender)
  (MIT OR GPL-3.0-or-later, commit 2026-11-21; `editor/spring_bone1`: sphere and capsule colliders).
- AMD TressFX: [github.com/GPUOpen-Effects/TressFX](https://github.com/GPUOpen-Effects/TressFX) (MIT, last commit
  2020-01-24, DirectX 12 / Vulkan).
- PositionBasedDynamics: [github.com/InteractiveComputerGraphics/PositionBasedDynamics](https://github.com/InteractiveComputerGraphics/PositionBasedDynamics) (MIT, commit 2026-09-01, Cosserat rod demos).
- NVIDIA Warp [github.com/NVIDIA/warp](https://github.com/NVIDIA/warp) (Apache-2.0, commit 2026-11-21; PyPI
  `warp-lang` 1.19.0) and Newton [github.com/newton-physics/newton](https://github.com/newton-physics/newton)
  (Apache-2.0, commit 2026-11-21, cable/rod examples).
- dismech-rods: [github.com/StructuresComp/dismech-rods](https://github.com/StructuresComp/dismech-rods) (GPL-3,
  commit 2026-10-18). libWetHair: [github.com/nepluno/libWetHair](https://github.com/nepluno/libWetHair) (MPL-2.0,
  commit 2026-10-17).
- Houdini Indie price and revenue limit: [sidefx.com/products/houdini-indie](https://sidefx.com/products/houdini-indie/),
  [shade.inc pricing summary 2026](https://shade.inc/blog/sidefx-houdini-pricing-2026-fx-core-indie-license-costs) (via web search).
- Ornatrix licence change (Sept 2025; Maya / 3ds Max / Cinema 4D / Unreal):
  [cgchannel.com](https://www.cgchannel.com/tag/ornatrix-ue) (via web search). No Blender build found.
- T-183 status: `docs/evaluation/characters/T-183/README.md` on `t-183-claude-hair-contact@a41bedf` (summary only);
  owner decisions 2026-11-21 in `docs/process/OWNER_DECISIONS.md`.

## Files

- `tests/gn_hair_dynamics_probe.py` - the scene, Blender Hair Dynamics on guides or ringlets.
- `tests/cloth_ribbon_probe.py` - the same scene, Cloth on ribbons.
- `tests/contact_projection_probe.py` - the same scene, the stateless push-out on real meshes.
- Run any of them: `python3 tools/bpy_blender.py -b --factory-startup -P <script> -- OUT.json [--mode=guide|ringlet]
  [--sub=N --cs=N] [--len=M] [--png=OUT.png]`.
- `results/T-193_probe_summaries.json`, `T-193_projection_vs_gn_guide.png`, `T-193_gn_ringlet_vs_cloth_ribbon.png`.
