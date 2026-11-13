# Plush Studio — character production pipeline analysis
## Experimental character: the dark-haired boy in the yellow hoodie

_Date: 2026-11-13. Analysis and planning only: no source code was changed, nothing was modelled or rigged, no
images were generated. Tags used throughout: **[V]** verified in this environment, **[A]** assumption, **[R]**
recommendation._

---

## 1. Executive summary

- **[V] Blender works here headless, as a Python module.** `bpy` 5.3.0 (Blender 5.3 as a Python module) installs
  from PyPI into a scratch virtual environment. A smoke test then ran headless: modelling operators, UV unwrap,
  armature with automatic weights, shape keys, hair curves, geometry nodes, Principled/SSS/hair materials,
  keyframes, `.blend` save, glTF/FBX/Alembic/USD/OBJ export and a Cycles CPU render all passed. EEVEE also ran,
  but at 27 s for a 96×96 image without a GPU, so it is not usable here. Neither a Blender binary nor `bpy` is
  installed in the project environment, and the official Blender download server is blocked by this environment's
  network policy.
- **[V] Plush Studio cannot ingest a Blender asset today.**
  - No importer exists for any interchange format.
  - Meshes have no UVs, and textures are procedural only.
  - Skeleton bones have no rest orientation; rest frames are axis-aligned.
  - Skinning (4 influences per vertex), morph targets, curve rendering and the material set are compatible in
    principle and reusable.
- **[R] Architecture.** Blender becomes an **offline asset-creation backend**, run as a separate process with
  versioned Python scripts and file-based jobs.
  - The `.blend` file is the master asset.
  - Plush Studio receives an exported package: glTF 2.0 for mesh, skin, shape keys, UVs and animation; a Plush hair
    file for the curves; a manifest for Plush-specific material, rig-role and expression data.
  - Plush Studio stays the production environment: scenes, actions, director, life layer and final output.
- **[R] Biggest risk.** Reference-level sculpted forms (face, hair clumps, fleece folds) produced by scripted modelling
  without a human artist. This needs your decision (section 9).
- **[R] Recommended first task.** Build the reference package and a camera-matched comparison harness in Blender
  (section 15), so every model is judged against the references objectively before rigging starts.

**Requirement change to confirm.** Your second directive said Blender must not be required (TD-01). This brief makes
Blender a backend tool. That holds if routine use only consumes exported assets, but creating or editing a
character's master asset will need Blender or `bpy` installed (section 8.6).

**Project status you may not have seen:** after Iteration 3, **Iteration 4 was completed** and is waiting for your
review (`docs/ITERATION_04_ACCEPTANCE_REPORT.md`). It includes a rebuilt version of this boy as an SDF character.
Both checkpoints are preserved in git (Iteration 3 = `db01ad6`, Iteration 4 = `89d7a92`, bundle
`/home/user/plush-studio-iteration4.bundle`).

---

## 2. Reference image inventory and classification

### 2.1 Received
| # | File (copied to `docs/references/`) | Content | Class | Use for the boy |
| --- | --- | --- | --- | --- |
| 7 | `char_C_boy.jpg` | Original single-character render, front, slightly from above | **Dedicated original** | Final authority for identity and look |
| 4–6 | `char_A_white_hair.webp`, `char_B_brown_hair.webp`, `lineup.webp` | Other two characters / lineup | Group/context | Style and relative scale only |
| 1–3 | `classroom_*.webp`, `video_watertable.mp4` | Scenes with all three | Group/context | Lighting, scale relations, behaviour |
| 8 | `boy_pipeline/08_boy_turnaround_proportions_expressions_clothing_sheet.webp` | 5-view turnaround; hair-only renders (front/back/side/top); proportion brackets (head/torso/leg/width); 5 expressions; clothing breakdown (hoodie front/back, joggers, backpack front/back, sneakers front/side/back/sole); 3 material swatches; skeleton silhouettes front/side; hoodie wireframe; T-pose; modular parts (bald head, hair, hoodie, trousers, shoes) | Design sheet + technical | Primary sheet for turnaround, proportions, clothing parts |
| 9 | `boy_pipeline/09_group_turnaround_sheet_all_three.webp` | Rows per character; boy row: front/¾/side/back, 6 facial expressions, hair construction (cards over a scalp mesh), clothing parts incl. backpack in two colours, skeleton front/back, 2 key poses; bottom row: boy from 4 angles beside the others | Group design sheet | Boy rows only; style consistency |
| 10 | `boy_pipeline/10_rig_overview_mockup_all_three.webp` | Image of a "Blender 4D" window with three rigged characters, finger controls and face markers | **Concept mock-up, not a real screenshot.** Menus are garbled ("Meathing", "Sceting", "Termise Fonts") and the product name does not exist. **No such rig exists in this project.** | Intended rig layout only (bone placement, finger controls) |
| 11 | `boy_pipeline/11_boy_facial_topology_spec.webp` | Head topology: eye edge loops, mouth/lip loops, jaw/cheek flow, ear junction; ¾ wireframe; eyelid open/blink/squint; mouth neutral-frown/open | Technical (topology) | Edge-loop layout of the head; hair as sculpted clump shapes. Some labels point at the wrong part (e.g. "Mouth & Lip Loops" arrow at the ear) |
| 12 | `boy_pipeline/12_boy_facial_rig_blendshape_blueprint.webp` | Facial controls (brow in/out, upper/lower lids, eye targets, cheeks, jaw root, mouth main/corners), 15 blendshapes, eyelid states, jaw/mouth controls, outliner hierarchy | Technical (face rig) | Target list of face controls and shapes. Axis numbers on the ruler are meaningless (130, 50, 200, 10 …) |

| 18 | `boy_pipeline/18_hand_topology_finger_rig_poses_contact_weights.webp` | Hand topology (wrist/palm loops, 3 loops per joint), finger skeleton, 9 required poses, thumb opposition range, 6 hand-object contacts (boat, pencil, toy, cup, release, flat surface), wrist/palm/deformation weight heatmaps. Labelled "Character A (plush design study)" | Technical (hand) | Topology, joints, pose list, contact cases |
| 19 | `boy_pipeline/19_boy_body_topology_joint_deformation_poses.webp` | Boy in A-pose (front, ¾) with topology and dimension arrows (no numbers); skeleton front/side with IK circles; shoulder, armpit, elbow, hip and knee deformation details; poses: arms up, bow, sit, walk, kneel; backpack | Technical (body) | Rest pose, joint loops, deformation tests |
| 20 | `boy_pipeline/20_boy_skeleton_hierarchy_skin_weights_control_rig.webp` | "character_c_reference_01": bone names, hierarchy tree, joint orientation (bone Y along length, pre-bent elbow/knee for IK), weight heatmaps, knee/spine deformation tests ("preserve hoodie bulk, no crushing"), control rig (HEAD/CHEST/HIPS/ROOT, IK hands/feet, elbow/knee poles) | Technical (rig) | Skeleton and controls specification |
| 21 | `boy_pipeline/21_boy_hair_geometry_groom_material_spec.webp` | Clump masses (crown spikes, downward fringe, side/back clusters), hybrid method (base-mesh clumps + curves/fine fibres 0.5–1 mm), flow arrows, colour-coded groups, material #2D2D2D, roughness 0.95, SSS | Technical (hair) | Hair construction and material |
| 22 | `boy_pipeline/22_boy_hair_rig_secondary_motion.webp` | Hair chains DEF-hair.fringe.01–03, DEF-hair.crown.01–04, DEF-hair.side_L/R, MCH-hair.master, ORG-head; delay/overshoot/settling; spring settings (stiffness 0.65, damping 0.80, gravity 0.3) | Technical (hair rig) | Secondary-motion specification |
| 23 | not stored (seen in conversation) | Clothing topology and deformation: A-pose half-render/half-wireframe (front, ¾, back with backpack), hoodie/joggers/shoe breakdown with seam and stitch details, ribbed cuffs/hem, hood lining, stretch/fold zones for arm raise, elbow bend, reach, sit, walk | Technical (clothing) | Garment construction and deformation zones |
| 24 | not stored (seen in conversation) | "01_Material_Identification": hero render with material notes for hair, skin, eyes, hoodie, straps, trousers, footwear; swatches (roughness, plush, fibres, fuzz) | **High-quality look reference** + material description | Materials; also a second identity reference next to #7 |
| 25 | not stored (seen in conversation) | UV organization: T-pose and A-pose with checker and seams; face/head, hair-mass, hoodie, pants, shoes/accessories UV layouts; fibre-direction overlays; Blender UV stretch view | Technical (UV) | Seams, layouts, texture/fibre direction |
| 26 | not stored (seen in conversation) | "C_reference_01": hand contact zones, grasp types (precision pinch, power grasp, two-finger pinch, support), pick-up and release sequences, foot-to-floor, leaning on a table, sitting, arm/hand IK | Technical (interaction) | Contact and interaction specification |

None of these is a 3D mesh, rig, UV set or skin-weight map. They are pictures.

### 2.2 Coverage of the requested categories (after the uploads of #18–#26)
| Requested category | Now covered by | Still missing |
| --- | --- | --- |
| Hand topology, finger rigging | #18 (topology, MCP/PIP/DIP and thumb CMC/MCP/IP joints, 9 required poses, thumb opposition) | Hand **proportions** for this boy (see §2.3, item 7) |
| Body topology, joint deformation | #19 (A-pose topology, shoulder/elbow/hip/knee loops, test poses), #20 (knee 90°, spine bend/twist), #23 (stretch/fold zones) | — |
| Skin-weight guides | #18 (wrist, palm, deformation heatmaps), #20 (body heatmaps) | Numeric weights (pictures only) |
| Hair rig, secondary motion | #22 (chains, hierarchy, spring settings) | — |
| Hair geometry, groom | #21 (hybrid clump meshes + fibres, flow, material) | — |
| Clothing topology, deformation | #23 (hoodie, joggers, shoes, seams, stitching, deformation zones), #19 | Cloth behaviour (simulation vs. correctives): not specified |
| UV mapping | #25 (seams, per-part layouts, checker validation, texture direction) | Texel density and texture resolution targets |
| Materials, textures | #24 (qualitative, all parts), #21 (hair: #2D2D2D, roughness 0.95, SSS) | Numeric values for skin, hoodie, trousers, shoes, eyes, straps |
| Object interaction, contact points | #26 (contact zones, 4 grasp types, pick-up/release, foot/lean/sit contact, IK), #18 (boat, pencil, toy, cup, release, flat surface) | — |
| Animation deformation tests | #19 (arms up, bow, sit, walk, kneel), #20, #23 | — |
| Full integration | #24 (hero render with all materials) | — |
| Real-world scale | — | **Height in cm**: dimension arrows in #19/#23 carry no numbers |

Upload history: #13–#17 were byte-identical to #8–#12. #18–#22 arrived as new files. #23–#26 were visible in the
conversation but **were not stored as files in this workspace**, so they are not yet in `docs/references/boy_pipeline/`.

### 2.3 Conflicts found (reported, not resolved)
1. **Name/letter.**
   - The boy is **"C"** in this project and in #12.
   - He is **"A"** in #8 and #11, and in the row label of #9.
   - **[R]** Use a stable ID, `boy_yellow_hoodie`, and drop letters.
2. **Default pose.** The original (#7) has one hand in the trouser pocket. #8 has both arms down. #9 has hands in
   pockets in several views. Pose is not identity; please choose the rest pose for the turnaround.
3. **Backpack.**
   - The original shows only dark navy/plum straps.
   - #8 shows a dark purple-grey felt backpack.
   - #9 shows a plum backpack with an orange zip line, plus a second, lighter mauve backpack in its breakdown.
   - Please choose the colour and details.
4. **Head-to-height ratio** (measured on the images, ±3%).
   - About 0.37 on the original. It is photographed slightly from above, which enlarges the head.
   - About 0.33 on the #8 proportion sheet.
   - **[R]** Use #8's front view for measurements and #7 for look.
5. **Hair construction.**
   - #11 shows smooth sculpted clump shapes.
   - #9 shows hair cards over a scalp mesh.
   - The renders (#7, #8) show felted, fuzzy clumps with a few stray strands.
   - **[R]** Sculpted clump meshes plus a short-fibre groom for the felt surface; not cards.
6. **Sole.** The sole is white rubber with a white toe cap; the tread is brown in #8's sole view. Not
   contradictory, but the tread colour appears only once.
7. **Hand proportions.** #18 and #26 show long, slender five-finger hands. #7, #8, #19 and #24 show short, chubby,
   stubby hands. **[R]** Proportions from #7/#24; topology, joints and pose list from #18.
8. **Hand material.** #26 renders the hand as dark grey fleece, like a glove. Every other reference shows bare peach
   skin. Most likely a material demo; please confirm the hands are bare skin.
9. **Rest pose for rigging.**
   - A-pose (arms about 45° down) in #19, #23 and #25.
   - T-pose in #8 and #25.
   - Arms close to the body in #20.
   - **[R]** A-pose for modelling and rigging; the hand-in-pocket stance is a pose, not the rest pose.
10. **Skeleton naming and hierarchy.** Three naming schemes, and a hierarchy that disagrees with itself:
    - Naming: #12 uses `CTRL_…`; #20 uses `L_UPPER_ARM`, `IK_HAND_L`, `PV_ELBOW_L`; #22 uses Rigify-style
      `DEF-/MCH-/ORG-`.
    - #20's tree omits neck, calf and foot, which its own labels show.
    - #22 parents the hair to "Spine3", which does not exist in #20 (spine_01, spine_02, chest).
    - **[R]** Blender side: Rigify-style `DEF-`/`ORG-`/`MCH-` with `.L/.R` suffixes, controls named after #20/#12,
      and a role map in the manifest for Plush.
11. **Hair shape.** The sculpted hair in #19, #23 and #25 is softer and wavier, with rounder tufts. #7, #8, #11, #21,
    #22 and #24 show spikier felted clumps. Hair authority: #7/#24; construction method: #21.
12. **Hair colour.**
    - #21 specifies neutral charcoal #2D2D2D.
    - The lit hair in #7 averages a slightly warm #302A26.
    - Close in value; the warmth may come from lighting.
    - **[R]** #2D2D2D albedo, checked by matched renders.
13. **Backpack colour (update).** #8, #23 and #24 agree on dark charcoal grey with a slight purple tint. #9 (plum,
    orange zip) is the outlier. **[R]** Charcoal-plum grey, unless you decide otherwise.
14. **Character letter (update).** "A" in #8, #11 and #18; "C" in #12, #20, #22 and #26. Still mixed.

---

## 3. Canonical visual description of the boy

Taken from #7 (authority), #8 and #11; measurements are approximate ratios read off the images.

- **Overall.** Chibi plush figure with a large head. Head including hair is about 0.33 of the height (#8). Torso
  (shoulder to hoodie hem) about 0.29. Legs including shoes about 0.36.
- **Head.** Rounded, wide and soft, with full low cheeks and a small chin. Pink ears are clearly visible at the sides,
  below the hair, at eye-to-mouth height. Skin is warm, light peach with pink blush on the cheeks and ear rims.
- **Eyes.**
  - Large and wide-set: spacing about 0.47 of face width on #7.
  - Half-lidded and sleepy: the upper lid covers about 40% of the iris, with a dark lash line.
  - Brown iris with a darker rim and a small highlight; little visible white.
- **Brows.** Short, thin and dark brown-black, slightly lowered at the inner ends (sulky). Partly under the fringe.
- **Nose and mouth.**
  - Nose: a small soft button.
  - Mouth: small, closed, slightly downturned (frown). The expressions in #8 and #12 open it into a D shape with
    teeth for happy, surprised and laugh.
- **Hair.** Near-black (very dark brown in shadow), felted wool with visible fibres.
  - Large tousled volume, about 1.3× the skull width.
  - Thick pointed clumps of mixed sizes: crown clumps pointing up and out, side clumps flaring out and down.
  - Fringe of pointed clumps down to the brows.
  - A few stray thin strands on top.
- **Hoodie.** Mustard-yellow teddy fleece, loose and slightly oversized.
  - Hood lying on the back.
  - Cream drawstrings with darker tips.
  - Kangaroo pocket.
  - Ribbed cuffs and hem; sleeves bunch at the wrists.
- **Trousers.** Black fuzzy fleece joggers, slightly baggy, gathered at the ankles.
- **Shoes.** Yellow canvas/felt sneakers with white rubber soles and toe caps; brown tread underneath (#8).
- **Backpack.** Dark charcoal-plum felt backpack: rounded rectangle with a front pocket and a top handle (#23); straps
  of flat woven dark-grey webbing with adjuster buckles (#24).
- **Details from #23/#24.**
  - A cream undershirt collar shows inside the hoodie neckline (also faintly in #7).
  - The hood has a slightly darker mustard lining.
  - Shoulder, hood and side seams are double-stitched.
  - The drawstring cords are textured, with frayed ends.
  - Cream socks show between the trouser cuffs and the shoes.
  - The shoes have two cream straps across the top, not laces.
  - Eyes are semi-glossy resin with inset pupils.
  - Skin is soft matte with subtle SSS and a peach-fuzz texture.
  - The hoodie is heavyweight fleece/bouclé; the trousers are felted or rough-knit and heavily textured.
- **Hands.** Short, chubby, five-fingered, bare skin. In the hero renders (#7, #24) the left hand rests in the
  trouser pocket.
- **Personality.** Sleepy, sulky and cool. A slight forward slouch and an asymmetric stance (a hand in a pocket).

---

## 4. Existing architecture assessment (inspected source, not reports)

7,176 lines of C++ (engine 5,429; Studio 905; render CLI 207; tests 635), plus Python generator scripts.

| Area | What exists (verified in code) | Status |
| --- | --- | --- |
| Geometry | `Mesh` = positions, normals, rest positions, triangle indices. **No UVs, tangents or material IDs** | Implemented, limited |
| Modelling | SDF primitives (ellipsoid, capsule, round cone, round box, disc), smooth union/subtract, mirror, noise and relief patterns; surface-nets mesher with brick culling | Implemented |
| Character representation | `.character.json`: skeleton (name, parent, **head position only**), SDF parts, fuzz layers, explicit lock curves, expressions as SDF edits, default pose/expressions. The rig is **built at load time** (meshing, automatic weights, morphs) | Implemented. **No mesh-based character type** |
| Skinning | 4 joints/weights per vertex; linear and dual-quaternion skinning | Implemented, reusable |
| Expressions | Morph targets (sparse per mesh), weighted per frame | Implemented, reusable for imported shape keys |
| Animation | Tracks (vec3, smooth/linear/step), Euler XYZ per bone, two-bone IK, eye look-at, attach, fingers (curl/thumb/spread/point, contact grasp), life layer, actions, director | Implemented. **Assumes axis-aligned rest frames** (finger curl axes, IK, aim along +z) |
| Hair | Surface fuzz; lock curves with felt core and fibre halo; felted SDF clump volumes; fibre LOD | Implemented |
| Scenes | `.scene.json`: objects (box, SDF, paper boat, water), characters, lights, camera, tracks, actions, director | Implemented |
| Rendering | Embree CPU path tracer: MIS, DOF, glass/water, fibre BSDF (Chiang), plush/standard BSDFs, random-walk SSS, OIDN, AgX, adaptive sampling | Implemented. **Procedural textures only; no image textures or normal maps** |
| Asset management | JSON files in folders plus git; generator scripts (`tools/charkit.py`) | Minimal: no asset library, no versioned manifests |
| UI (Studio) | ImGui/OpenGL 3.3: outliner, inspector, timeline, hair-lock editor, in-app path tracing, save/reopen | Experimental: no undo, no gizmos, no mesh editing |
| Interchange | **None** (no glTF, FBX, OBJ, Alembic or USD) | Missing |
| Tests | 24 unit tests, 3 image regressions (milestone 01, v2 face, A/B/C lineup) | Implemented |

Known limitations: `BUGS_AND_ISSUES.md` (notably BUGS-03/17 mirror data, BUGS-21 mouth pockets, BUGS-22 no
collisions, BUGS-25 build times).

---

## 5. Reusable existing features

- **Without changes:**
  - Path tracer, the fibre BSDF for felt hair, random-walk SSS (same method as Cycles), denoising, tone mapping.
  - Scenes, actions, director, life layer and the water table.
  - Fibre generation from curves (hair-curve import feeds it).
  - Skinning (4 influences) and morph-target playback.
  - The CLI render queue and video output.
  - The test harness and image regressions.
- **With changes:**
  - Skeleton: needs rest orientations.
  - Hands, IK and look-at: must use bone orientations and role names instead of axis assumptions.
  - Materials: need image textures and UVs.
  - Studio: needs mesh-character display and the existing hair/lock tools adapted to imported curves.
- **As reference only:**
  - The Iteration 4 SDF boy, for proportions and as a blockout guide. Its surface-nets topology is unsuitable for
    production deformation: no edge loops around the eyes and mouth.

## 6. Missing or insufficient capabilities (for a Blender-made character)
1. Asset import: glTF reader (mesh, skin, inverse bind matrices, morph targets, UVs, materials, animations).
2. A mesh-based character asset type next to SDF characters.
3. Bone rest orientation throughout animation (pose evaluation, IK, look-at, fingers, life layer, actions).
4. UVs, image textures (base colour, roughness, normal, masks) and tangents in renderer and Studio preview.
5. Hair-curve import (positions, radii, clump IDs, root UVs), plus a groom-to-fibre mapping.
6. Bone role map (which bone is head, hand.L, finger chains, eyes, lids, jaw). Actions, life, hands and the director
   need it.
7. Material translation table from Blender Principled/Hair BSDF to Plush materials.
8. Asset manifest, versioning, validation reports, LODs.
9. A runner that launches Blender jobs from Plush Studio and reports progress and errors.
10. Secondary motion for hair and clothing: not implemented anywhere today, in either Plush or exported data. #22
    specifies damped spring chains: stiffness 0.65, damping 0.80, gravity 0.3. **[V-knowledge]** Blender has no
    built-in spring-bone feature; its settings panel in #22 resembles an add-on. **[R]** Implement spring chains in
    Plush, simulated from the shot start with a per-shot cache. Unlike the life layer this is stateful, so it needs a
    cache to keep frames independently renderable.
11. Pose-driven corrective shapes. #20 and #23 ask for no crushing and preserved hoodie bulk. Blender drives
    correctives with drivers, which Plush cannot run. **[R]** Export correctives as morph targets plus a small
    "weight from joint angle" table that Plush evaluates.
12. Fibre/flow direction maps. #21 and #25 give fleece and hair a direction per region. Plush fuzz today has a single
    comb origin per layer. **[R]** Read a direction map in UV space.
13. Environmental contact actions. #26 shows sitting, leaning on a table and foot-to-floor contact. Plush actions have
    walk, reach and touch only; sit and lean are missing.

---

## 7. Blender environment and capability assessment

| Item | Finding |
| --- | --- |
| Blender binary installed | **No** [V] |
| `bpy` module | **Installable from PyPI: 5.1.0–5.3.0 for this Python 3.13.** Tested 5.3.0 in a scratch venv outside the project, 1.1 GB [V] |
| Official downloads (download.blender.org) | **Blocked** by this cloud environment's network policy (proxy 403) [V]. Could be allowed in the environment settings if needed |
| Ubuntu package | Blender 4.0.2 available via apt (older) [V], not installed |
| Headless/background | Yes, `bpy.app.background = True` [V] |
| Python control | Yes, full `bpy` API including operators in background mode [V] |
| Tested OK [V] | Mesh modelling ops, subdivision modifier, UV smart project, armature with automatic weights, shape keys, hair curves (new curves type), geometry-nodes modifier, Principled BSDF with SSS, Principled Hair BSDF, keyframes, `.blend` save, glTF (skin + morph + UV + animation verified inside the file), FBX, Alembic, USD, OBJ export, Cycles CPU render |
| EEVEE | Ran, but 27 s for 96×96 without a GPU: impractical here [V]. On your computer it depends on your GPU [A] |
| glTF limits [V] | Hair curves are not carried (glTF has no curve primitive): they need a separate export |
| Add-ons in the module build [V] | glTF, FBX, BVH, SVG, UV-layout I/O present; others (e.g. Rigify) not checked [A: Rigify may need the extensions platform] |
| Your computer | Unknown: OS, CPU, GPU, RAM never measured [A] |

Smoke test script and results: `docs/references/boy_pipeline/blender_smoke_test_*`.

---

## 8. Proposed Blender ↔ Plush Studio integration architecture [R]

```
 Plush Studio (C++)                         Blender backend (separate process)
 ───────────────────                        ──────────────────────────────────
 Asset panel / job runner  ── job.json ──▶  blender -b (or python+bpy) runs
                                            pipeline/blender/<task>.py
                           ◀─ result.json ─  (+ log, renders, exported files)
 Importer (glTF + hair +   ◀── export/ ───  export_plush.py: .glb, hair, manifest
 manifest) → mesh character
 Scenes, actions, director,
 life layer, renderer, video
```

1. **Process boundary.** Blender is always a separate process (`blender --background --python …` or a `python` with
   `bpy`), never linked into Plush Studio.
   - Crashes stay isolated.
   - Blender versions stay swappable.
   - **[A]** It also keeps Plush Studio's code licence independent of Blender's GPL. Please have this checked before
     distributing.
2. **Jobs are files.**
   - `job.json`: task, inputs, versions, seed.
   - `result.json`: status, outputs, hashes, warnings, timings.
   - Deterministic, scriptable, easy to test in CI.
   - A persistent worker (socket) can come later for interactive editing.
3. **Master asset.** The `.blend` file holds geometry, armature, weights, shape keys, drivers, UVs, grooms and
   materials. It is created and changed only by versioned pipeline scripts, plus optional artist edits, each saved
   as a new version.
4. **Exchange package** (what Plush Studio loads):

   | Data | Format | Why |
   | --- | --- | --- |
   | Meshes, skin, inverse binds, shape keys, UVs, base materials, test animations | **glTF 2.0 (.glb)** | Open, complete for skinned meshes, small readers exist (cgltf, MIT) |
   | Hair curves | Plush curve file (binary + JSON header, written by a Blender script) | glTF has no curves. Alembic/USD readers are heavy dependencies for one use |
   | Plush-specific data | `asset.json` manifest: material mapping (fibre BSDF, SSS radius, fuzz layers), bone roles, expression map, LODs, versions, hashes | Things neither format expresses |
   | Textures | PNG (8/16-bit), EXR for displacement if used | Standard |
5. **What stays native in Blender:** drivers, constraints, geometry-nodes trees, cloth/physics settings, sculpt
   layers, edit history. These are **baked** on export, to shape keys, curves or bone animation, because Plush
   cannot execute them.
6. **Routine use without Blender.** Animating, staging, directing and rendering use only the exported package, so
   end users need Blender only when a master asset is created or changed. Recommendation: Plush Studio locates or
   bundles a pinned Blender, or the `bpy` module, behind an "Edit asset in backend" action.
7. **Rendering.**
   - **(A)** Plush renderer for everything (current direction; needs UV/texture support).
   - **(B)** Plush-driven Cycles as an optional final or reference renderer.
   - **[R]** Use Cycles for asset-approval turntables in Stages 3–4: they are available immediately while the asset
     lives in Blender.
   - **[R]** At Stage 7, render the same shot in both renderers and decide with measured quality, time and memory.

## 9. Recommended character modelling workflow

The decisive question is **who shapes the forms**.

| Option | How | Fidelity risk | Notes |
| --- | --- | --- | --- |
| 1. Scripted modelling (autonomous) | Parametric base meshes with designed edge loops, built from measurements of #8/#11. Subdivision, lattice/proportional shaping, curve-driven clump meshes, scripted cloth drape for the hoodie. Iterate with camera-matched comparison renders | **High** for subtle sculpted shapes (cheeks, clump forms, fleece folds) | Fully reproducible; each look iteration is a render loop, as in Iteration 4 |
| 2. Human artist in Blender | An artist sculpts/models from the references; the pipeline validates, rigs, exports | Lowest | Needs a person; the pipeline still automates everything after the model |
| 3. Hybrid | Scripts build topology, proportions, UVs, rig scaffolding and validation; an artist does a short sculpt pass on face and hair | Low–medium | **[R] Best quality per effort** if an artist is available |

Image-to-3D generators are excluded: the project rule is no generative AI in the pipeline, unless you change it.

Steps for the model, whichever option you choose:
1. Comparison rig: cameras and lights that reproduce the reference views (front, sides, back, ¾ from #8, the #7
   angle).
2. Blockout: primitive proportions matched to #8's brackets; review.
3. Head with production topology: eye and mouth loops as in #11, ear junction, a separate eyeball, eyelid geometry
   for blinks.
4. Body and hands: five fingers with three joints each (the current SDF hand has two-segment stub fingers),
   deformation loops at shoulders, elbows, hips and knees.
5. Clothing as separate meshes (hoodie, hood, pocket, cuffs, drawstrings, joggers, sneakers, backpack) fitted over
   the body.
6. Hair: sculpted clump shells per #11, a scalp mesh, then a short-fibre groom.
7. Visual approval: same cameras and lighting as the references, side by side.

## 10. Proposed technical asset structure [R]

```
assets/characters/boy_yellow_hoodie/
  asset.json              id, version (semver), blender version, pipeline commit, files + SHA-256,
                          bone roles, expression map, LODs, material map
  CHANGELOG.md
  references/             copies + reference_index.json (classification, priorities, conflicts)
  source/
    boy_yellow_hoodie_v0001.blend   master (geometry, rig, shapes, UVs, groom, materials)
  textures/               <part>_<map>.png (2K default; 4K face/hair only if justified)
  export/
    boy_yellow_hoodie.glb           full detail
    boy_yellow_hoodie_lod1.glb      preview/animation LOD
    hair.plushcurves                curves + radii + clump ids
    anim/*.glb                      validation clips
  validation/
    compare_<view>.png, turntable_*.png, deformation_*.png, report.json
pipeline/blender/           build_*.py, rig_*.py, export_plush.py, validate.py, render_compare.py (+ tests)
```

Versioning:
- Masters are never overwritten: each change produces a new `vNNNN` file and a git tag.
- Binaries go in **Git LFS**, which needs a remote (BUGS-09: none configured yet).
- Bundle backups continue.

## 11. Required deliverables per stage

| Stage | Deliverables |
| --- | --- |
| 1 Reference & plan | `reference_index.json`, conflict decisions (from you), canonical spec (§3 approved), comparison camera/light rig `.blend`, pinned Blender version |
| 2 Modelling | `v0001.blend` (meshes, no rig), mesh stats and topology report, comparison renders per view |
| 3 Visual approval | Side-by-side sheet (reference vs model, same views); **your written approval** |
| 4 Materials/UV/hair | UV layout images, textures, materials, groom, Cycles lookdev turntable, material map in `asset.json` |
| 5 Rig & deformation | Armature, weights, finger and face controls, the 15 shape keys from #12, corrective shapes, deformation test renders (arms up, squat, fist, all expressions), weight validation report |
| 6 Animation tests | Idle, walk, blink/gaze, expression sweep, pick-up/put-down clip as `.blend` actions + exported `.glb`; renders |
| 7 Integration | Plush importer (glTF, hair, manifest), mesh-character type, rest-oriented skeleton, UV textures, bone roles; the boy in a Plush scene driven by actions; regression images; the A-vs-B renderer decision |
| 8 Canonical asset | Frozen `v1.0.0` package, manifest with hashes, CHANGELOG, LFS/bundle backup, re-export script that rebuilds the package from the master |

## 12. Implementation milestones (each ends with renders and tests)
1. Reference package and comparison harness.
2. Blockout → proportions approval.
3. Head and face topology → face approval.
4. Hair shapes → silhouette approval.
5. Body, hands, clothing → full-model approval (**gate: no rigging before this**).
6. UVs, materials, groom.
7. Rig, weights, face controls, shape keys.
8. Deformation and animation tests.
9. Plush import path (in parallel from milestone 5; independent of the model).
10. Integration shot and renderer decision.
11. Canonical v1.0.0.

## 13. Technical risks and dependencies
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Reference fidelity via scripted modelling | High | Option 3 (artist pass); strict comparison harness; small approval steps |
| Rest-orientation refactor in Plush animation (IK, hands, life, actions assume axis-aligned bones) | High | Do it behind tests, with existing scenes as regressions; keep SDF characters working |
| Hair interchange and render cost (fibres) | Medium–high | Clump meshes plus procedural fibres in Plush (already fast); export only guide curves |
| Blender version drift (API changes) | Medium | Pin one release (check which is LTS before pinning [A]); run the scripts in CI |
| Getting Blender onto your computer, and its licence when bundling | Medium | Separate process; a pinned installer or `bpy` venv; legal check of GPL obligations before distribution [A] |
| This environment: Blender download blocked; only `pip bpy` works | Low | Use `bpy` from PyPI or ask to allow the host |
| Missing references (hands, UVs, deformation, hair rig) | Medium | Supply them, or accept documented conventions |
| Secondary motion (hair, cloth) absent in Plush | Medium | Bake in Blender per shot first; spring bones in Plush later |
| Memory: high-res meshes + groom + 4K textures | Medium | LODs, 2K textures, fibre LOD; Iteration 4 already peaks at 7.7 GB |
| Your hardware unknown | Medium | Measure on your computer at Stage 1 |
| Spring-chain secondary motion is stateful (frames no longer independent) | Medium | Per-shot simulation cache; deterministic fixed-step solver |
| Bone count grows to roughly 90–100 deform bones (body ~22, fingers 30, face ~16, hair ~20–30) | Medium | Skinning stays 4 influences per vertex; profile posing time per frame |

## 14. Estimated complexity and critical bottlenecks
Rough, in focused sessions; [A] until measured:
- Stage 1: 1.
- Stages 2–3 (scripted): 4–8, depending on fidelity iterations. With an artist, mostly their time.
- Stage 4: 2–4.
- Stage 5: 3–5.
- Stage 6: 2–3.
- Stage 7: 4–6. The importer, rest orientations, UV/texture support and bone roles are the largest engine changes.
- Stage 8: 1.

**Critical bottlenecks:**
1. Sculpt-level fidelity of face and hair.
2. The rest-orientation refactor.
3. Hair groom quality versus render time.

## 15. Recommended first implementation task (after your approval)
**Stage 1 — reference package and Blender comparison harness:**
1. Pin the backend: `bpy` 5.3 in a project venv, or allow a Blender binary download. Your choice.
2. Write `references/reference_index.json`: classification, priority and the conflicts in §2.3.
3. Get your decisions on those conflicts and on the modelling option (§9).
4. Build `compare_rig.blend` by script. Cameras matching #8's front, side and back, and #7's angle; neutral lighting
   close to the sheets; an output layout that places reference and render side by side.
5. Validate the harness by loading the current Iteration 4 boy (exported from Plush as OBJ) as a stand-in and
   producing the first comparison sheet.

This touches no engine code and produces the yardstick every later stage is judged by.

**Waiting for your approval and decisions:**
- The modelling option (1, 2 or 3).
- The ID, the default pose and the backpack colour.
- The Blender install route.
- Confirmation that the earlier no-Blender requirement is lifted for asset creation.
