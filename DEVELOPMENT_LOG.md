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
