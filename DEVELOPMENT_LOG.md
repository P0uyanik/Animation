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
