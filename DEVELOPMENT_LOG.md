# Development log

## 2026-11-13 — Session 1: foundation to first rendered milestone

**Context change:** brief now requires a fully standalone app (no Blender), the existing unknown computer,
no GPU purchase, and fast delivery. Architecture revised accordingly (see TECHNICAL_DECISIONS.md TD-01…TD-14).

**Environment:** cloud container, Ubuntu 24.04, 4 cores, 15 GB, no GPU. Installed Embree 4.3, GLFW, GLEW,
glm, nlohmann/json, stb, doctest via apt; Open Image Denoise 2.3.3 prebuilt; Dear ImGui (docking) via FetchContent.

**Implemented**
- Engine modules: core (errors, logging, thread pool, ticks), geom (data model + JSON), anim (tracks,
  skeleton, pose, skinning), model (SDF primitives, surface-nets mesher, characters, auto skin weights),
  fuzz (surface fibres, yarn locks), scene (scene format, evaluator → frame snapshots), render (Embree path
  tracer, layered/plush/Chiang fibre BSDFs, procedural textures, DOF, OIDN, AgX tone mapping, PNG/HDR).
- `plush-render` CLI with resumable sequences and ffmpeg video encoding.
- Plush Studio desktop app (ImGui + OpenGL 3.3): viewport, outliner, inspector, timeline, in-app path tracing.
- Content: white-haired girl character; classroom milestone scene with 48-frame animation.

**Tested**
- 10 doctest cases: ticks, track interpolation, closed SDF mesh + area, skin weights, skinning identity,
  BSDF energy conservation, BSDF pdf consistency, scene JSON round trip, deterministic rendering, fibre orientation.
- Render tests by inspection: close-ups and full frames; Studio screenshots under Xvfb + Mesa llvmpipe.

**Look iterations**
1. First frame: shading OK; framing cut the head; fuzz invisible; locks hidden under the cap.
2. Found the denoiser removing sub-pixel fibres → fibre-aware albedo guide + denoise blend.
3. Lumpy cap displacement, stray fibres, locks draping from the widest point, bigger irises + upper lid.
4. Matte wool fibres for locks (were glassy); reframed camera to include the paper boat.

**Problems hit**
- Build process killed once (likely memory with parallel jobs + container restart); building with -j3 works.
- Camera-override argument parsing: negative numbers must be passed with a leading space or `=` is rejected.

**Milestone 01 animation:** 48 frames at 640x360, 32 spp, ~25 s/frame render + setup, 21 min total;
encoded to H.264. Head/eye/arm/chest keys and camera push-in play correctly; consecutive frames show mild
grain, no strong fibre flicker. Remaining look issues logged in BUGS_AND_ISSUES.md.

## 2026-11-13 — Look iteration 2 (quality before features)

**Goal:** close the gap to the references before adding features; keep milestone 01 as a regression test.

**Engine**
- Expressions as SDF morph targets (smile, mouth open), eyelid shells + lid bones (blink), brow bones.
- Geometric relief patterns on parts: strands (hair), knit (stitches), ribbed.
- Dual-quaternion skinning, Laplacian weight smoothing; two-bone IK, eye look-at, attach-to-bone.
- Owen-scrambled Sobol sampler; coverage-preserving fibre LOD; tile adaptive sampling (opt-in).
- Curves with surface materials shade as tubes (matte felt yarn cores under the fibres).

**Measurements (4-core cloud VM)**
- Sampler: RMSE at 64 spp vs 1024-spp reference 0.0271 → 0.0233; denoised 16 spp 0.0147 → 0.0133.
- Fibre LOD: 13.4M → 2.4M segments, frame 138 s → 108 s, RMSE 0.007.
- Adaptive sampling: max-pixel criterion gave nothing; mean-tile criterion at 0.1 gave −11%, RMSE 0.0034.
- 1280x720/128 spp final frame 219 s; close-up 960x540/128 spp 287 s.

**Content:** girl iteration 2 via `tools/make_girl_v2.py`: lids, brows, mouth on the measured surface (the old
mouth groove sat 4 mm behind the skin), larger fringe tufts, clumpy cap, 56 felt-cored locks, knit dress geometry,
collar part, soles, finger hands, head +6%. Milestone 02 scene with table, boat pick-up, expressions.

**Bugs found by tests:** IK rotation order (unit test caught a 7–42 mm miss); a test target outside arm reach.
**Regression:** milestone 01 still matches its reference (RMSE 0.016 ≤ 0.03) after all engine changes.

**Final milestone 02 render:** 72 frames at 640x360, 32 spp, adaptive 0.1, 4 threads: 22.8 s/frame average, 27.5 min total.

## 2026-11-13 — Iteration 3: reference-driven quality, three characters, interaction

**Analysis:** `docs/ITERATION_03_REFERENCE_GAP_ANALYSIS.md` (references + 5 s water-table video studied frame by frame).
**Engine:** explicit lock curves (Catmull-Rom, taper, helical curl, felt core, fibre halo) in bone-attached,
mirrorable lock groups; glass/water dielectric with a shadow-only scene; denoiser guides through glass; rippling
water height field; floating objects (yaw kept, tilt from the water); staged paper fold; default pose/expressions.
**Content:** character kit script; characters A, B, C; lineup, expression and group scenes.
**Studio:** hair-lock panel, tube preview of curves, `--script-hair-edit` / `--script-verify` round-trip test.
**Look iterations (each checked with renders):** cap read as a hat → slim base ending at the hairline + crown and
fringe locks; B's curls covered her face → curls only on back/sides; telephone-cord curls → thicker, looser; A's
noodle locks → denser layers with a longer halo; fogged lenses → guides through glass; hedgehog spikes → rounder clumps.
**Tests:** 16 unit tests + milestone 01 and face (v2) regressions green after every engine change.

## 2026-11-13 — Iteration 4, Phase B: character reconstruction

**Re-baselined `regression_lineup_abc`** on purpose: the characters were rebuilt to match the references (RMSE
0.0608 against the iteration-3 image, limit 0.03). The iteration-3 reference image is kept next to it as
`tests/regression/lineup_abc_320x240_it3.png`. Milestone 01 and the v2 face regressions are untouched and pass.

**Engine**
- Exact `disc` SDF primitive (glasses lenses; the flat-ellipsoid approximation produced a translucent band).
- SDF mesher evaluates in 8³ bricks: bricks far from the surface are filled from their centre value; bricks near it
  evaluate only primitives within reach. Unit test: identical vertex count and vertices on the exhaustive surface
  (max |sdf| 1.5e-8 m) for a 47-primitive clump part. Needed for felted hair parts with ~200 primitives.
- Expression morph targets: tangential relaxation (12 passes of neighbour averaging + re-projection) after
  projection, which removed crumpling around the mouth.

**Content (tools/charkit.py)**
- Face: larger deep-set wide eyes, iris 31–34°, shorter upper face, lower fuller chin (mouth ≈0.3 eye spacings above
  the chin, as measured on reference A), small embedded nose, finger bones.
- Mouth: the resting mouth is baked into the skin surface (A small open smile, B wide grin, C slight frown), with
  mouth interior parts (cavity, upper teeth, tongue) and a `mouthClose` fill expression. Morphing a hole open
  crumpled the skin and the lining covered the interior (tried and rejected, see renders/it4wip/mouths*.png).
- Hair: felted SDF clump volumes for A's fringe and crown, B's swept fringe and crown, C's whole head of spiky
  clumps (96 clumps); soft hair-mass volume under A's and B's locks; A's buns ×1.22, bow ×1.6; brim prim removed.
- Clothes: A bodice + bell skirt + ribbed hem band, arms rest 9° out; B darker dusty-rose V-neck vest with embroidered
  felt motifs; C looser hoodie (torso r 0.082/0.104, sleeves 0.046) and wider joggers gathered at the ankle.
- Fixed: an iteration-3 `add_frown` overrode the new frown with pre-iteration-4 coordinates (it moved the cheeks).

## 2026-11-13 — Iteration 4: materials (Priority 2)

- **Skin subsurface scattering (random walk).** Material fields `subsurface` (weight of the diffuse that scatters below
  the surface) and `subsurfaceRadius` (mean free path per channel, metres). The walk runs inside the closed skin mesh
  only (a per-mesh Embree scene, so eyes/teeth/tongue inside the head do not block it); Chiang 2016 albedo inversion;
  channel chosen in proportion to the current throughput (the first version picked channels uniformly and produced
  firefly specks on the face). Unit test (white-furnace style): base 0.5 → 0.526, base 0.95 → 0.949.
  Cost on a face close-up (480², 64 spp): 41.4 s → 46.0 s. Characters A/B/C: subsurface 0.75, radius 3.5/1.6/1.0 mm.
- Knitted rib bands as separate parts with vertical ribs around their own axis: A's sleeve cuffs, C's hoodie cuffs and
  hem. C's pouch pocket moved onto the looser hoodie surface (it had sunk inside, only its edges showed).

## 2026-11-13 — Iteration 4: articulated hands (Priority 4)

- `applyHandPose` / tracks `<char>/hand.L|R` = (curl, thumb, spread), `.index` (pointing), `.grasp` (object centre in
  the hand's rest frame), `.graspRadius`, `.graspAxis` (cylinder) and `.grasp.weight`. Default is a relaxed hand
  (curl 0.25, thumb 0.15) instead of flat fingers.
- Grasp: each finger's curl is found by bisection so its tip rests on the object surface (sphere or cylinder);
  fingers that cannot reach it close fully. Unit test: fist brings tips to the palm, pointing keeps the index
  straight, a 8 mm stick curls the first segment 27° vs 16° for a 16 mm stick, every tip ends 4.0–4.6 mm from the
  surface (the finger's own radius). Visual check: `content/scenes/test_hand_poses.scene.json` (open, relaxed,
  fist, point, two grasps).
- First thumb axis was mirrored wrongly for the right hand (a rotation axis mirrors as (x, −y, −z)); fixed before use.
- A's resting arms 13° out (the hands touched the bell skirt at 9°).

## 2026-11-13 — Iteration 4: natural animation (Priority 3)

- **Life layer** (`applyLife`, per character `"life": true` or an object with amounts; off by default so older scenes
  and the regressions are unchanged): breathing (chest, spine, shoulders; neck compensates), slow weight shift (hips
  tilt, spine counter-tilts, thighs compensate so feet stay), small head drift, automatic blinks at jittered
  intervals over any lid pose, and the head following the gaze with a lag (eyes jump first, head turns ~0.2 s later).
  Deterministic per frame (a function of frame and seed), so frames render independently.
- **Action compiler** (`engine/scene/actions.cpp`): scene `"actions"` (look, expression, reach, walk) compile into
  generated tracks held in `Clip::generated` — used only where no hand-made key exists, never written into the
  scene's animation; the actions themselves are saved. Reach: anticipatory hand opening, contact-search grip,
  attach, lift toward the body, place, release, hand returns, gaze follows the object, ripples when a floating
  object leaves/re-enters water, and leaning the upper body when the object is beyond arm's length (warning if still
  out of reach). Walk: eased root path, turning into the path, planted footsteps via foot IK, pelvis bob and lean,
  counter-swinging arms.
- Floating objects no longer ride the water while held.
- Tests: blink count over a minute (12–22) and determinism; breathing moves the chest; the head has turned 0° two
  frames after a gaze jump and 21° fifteen frames after; reach puts the wrist 51 mm from the object at contact
  (leaning 2°+), carries it ≥3 cm up and leaves it where placed; walk arrives exactly, 0 of 59 frames with both feet
  sliding, feet lift ~2 cm, feet together at the end.

## 2026-11-13 — Iteration 4: water table v4, director, Studio round trip

- `tools/make_watertable_v4.py` → `content/scenes/watertable_v4.scene.json`: 180 frames at 30 fps, no hand keys;
  staging iterated with low-res previews (`renders/it4wip/v4_sheet*.png`): first master shot too tight, boat too
  big for the hands (scale 0.45 now), A turned away from the camera (moved to the back-right corner), medium shot
  dropped as too short (timing changed), touch fingertip above the water (fixed by fingertip correction).
- Studio round trip on a copy of the v4 scene: `--script-hair-edit` saved (actions, director and life kept; only the
  script's hand-made camera key written; no generated keys baked), `--script-verify` reopened it, recompiled the
  same shot list, and the edit survived (C has no hair lock groups now, so the script's lock went to `lashes.L`,
  4 → 5). Screenshot `renders/it4/studio_v4_reopened.png`. Note: the scripted test only exits with `--screenshot`.
- Fixed before use: touch fingertip correction shifted every key of that hand's IK track, not just the action's.
- B's back view (evidence `hair_B_back`) showed curl roots as knobs below a bare band of scalp: curl roots moved up
  (elevation 30–50°, +7 cm length) under longer crown clumps (32, 16–30°). Lineup regression re-baselined again for
  this intentional change. Lineup/B evidence rendered before the fix is re-rendered.

## 2026-11-13 — Reference package and decisions (no code changes)
- Pipeline analysis for the yellow-hoodie boy: `docs/BOY_BLENDER_PIPELINE_ANALYSIS.md`. Blender checked in this
  environment: no binary installed, the download host is blocked, `bpy` 5.3 from PyPI works headless (scratch venv
  only).
- References archived in `docs/references/boy_pipeline/` (#8–#12, #18–#27; SHA-256 checked, no overwrites).
  - #13–#17 were duplicates.
  - #28 (expression library) and #29 (integration/validation blueprint) were shown in the conversation but never
    reached the upload store; they are recorded in the inventory as not stored.
- Decisions recorded: TD-35 (Blender as a background backend, subsystems replaced only on evidence) and TD-36
  (`boy_yellow_hoodie`, A-pose, charcoal-plum backpack, canonical identity protected).
- Iteration 5 not started; the engine is unchanged.
- Re-send: #28 (`28_boy_facial_expression_library.webp`) and #29 (`29_boy_production_integration_validation.webp`)
  stored and verified. The reference package is complete: 17 technical sheets, all stored.

## 2026-11-13 — Evaluation: Blender installation and reference comparison harness (no engine changes)
- Blender binary: allowing `download.blender.org` was approved, but the change never reached this session's gateway
  (403) and the environment reverted to no allowed hosts. Installer ready (`pipeline/blender/install_blender.sh`,
  SHA-256 verified, version pin pending). Blender 4.0 not used.
- Built:
  - reference index with 16 camera-matched views;
  - silhouette extraction;
  - `plush-export-obj` (a new tool; engine unchanged);
  - Blender harness, Plush same-camera renders, comparison sheet and measurements.
  - Docs: `docs/BLENDER_COMPARISON_HARNESS.md`.
- Interim run with the official Blender 5.3 `bpy` module. Iteration 4 boy: mean silhouette IoU 0.79. Head +15% of
  height, legs −14%, feet −30% in width vs. the references.
  - Evidence: `docs/evaluation/blender_harness/`.
- Tried and changed: #24's silhouette merged with label leader lines, so #24 is visual-only.
