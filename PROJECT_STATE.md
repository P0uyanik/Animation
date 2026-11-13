# Project state

_Last updated: 2026-11-13, iteration 4 (character fidelity, materials, natural animation, hands, director).
Status: **waiting for your review and approval — iteration 5 has not been started.**_

## Summary
Plush Studio is a standalone C++ application for making stylized plush/felt/wool 3D animation without
Blender, cloud services or a GPU. The full pipeline now runs end to end on a CPU: soft SDF modeling →
automatic rigging → keyframe animation → procedural fur/fuzz and yarn hair → path-traced rendering →
denoising → filmic tone mapping → PNG sequence → H.264 video. A first desktop app (Plush Studio) can
open the milestone scene, preview it, edit shapes, materials, lights, camera and bone keys, and path trace in-app.

## Milestone 01 (first version rendered and reviewed)
White-haired girl in a sunlit classroom looking down at a paper boat and reaching for it, 48 frames @ 24 fps.
- Scene: `content/scenes/milestone01_classroom.scene.json`
- Character: `content/characters/girl_white_hair.character.json`
- Output: `docs/milestone01/milestone01_640x360.mp4` (48 frames, 640x360, 32 spp, rendered in 21 min on 4 cores)
- Stills: `docs/milestone01/` (full frame, head close-up, contact sheet, Studio screenshot)

## Iteration 4 (current — awaiting your approval)
- Characters A/B/C reconstructed against the references (`docs/ITERATION_04_PHASE_A_ANALYSIS.md`): larger wide-set
  eyes, shorter upper face and fuller chin, felted fringes/crowns/clumps, hair mass under the locks, bigger buns and
  bow (A), bell skirt + ribbed hem (A), V-neck vest with felt motifs (B), loose hoodie + wide joggers (C), mouths with
  teeth and tongue. Comparison sheets: `docs/iteration4/compare_*_ref_it3_it4.jpg`.
- Materials: random-walk subsurface scattering for skin; ribbed cuffs and hems.
- Animation: life layer (breathing, weight shift, blinks, head follows gaze), actions (look, expression, reach,
  touch, walk) compiled to generated tracks, articulated fingers with contact grasp, automatic camera director.
  Reference: `docs/ACTIONS_AND_DIRECTOR.md`.
- Benchmark: `content/scenes/watertable_v4.scene.json` (30 fps, 180 frames; no hand-made keys).
- Report: `docs/ITERATION_04_ACCEPTANCE_REPORT.md`. Evidence: `renders/it4/` (stills, expression sheets, animation),
  copies of the key images in `docs/iteration4/`.

## Iteration 3
- Three reference characters built with `tools/charkit.py`: `girl_white_hair` (A), `girl_brown_glasses` (B),
  `boy_dark_hair` (C), each with layered explicit hair locks, lashes, distinct faces/personality and garments.
- Milestone 03: `content/scenes/milestone03_watertable.scene.json` — the three around a water table; B folds a
  paper boat and sets it on rippling water; A and C react. Test scenes: `test_lineup`, `test_expressions_girl_white_hair`.
- Studio: hair-lock editor, curve tubes in the viewport, scripted edit → save → reopen test.
- Frozen for regression: milestone 01 (`girl_white_hair_m01`), milestone 02 + face test (`girl_white_hair_v2`).
- Reports: `docs/ITERATION_03_REFERENCE_GAP_ANALYSIS.md`, `docs/ITERATION_03_ACCEPTANCE_REPORT.md`.

## Look iteration 2
Milestone 02: the improved character picks up the paper boat from a play table (3 s, 72 frames): eyes lead
via look-at, surprised brows and "oh" mouth, lean-in, IK reach, grasp (object attaches to the hand), lift,
blink, smile. Scenes: `content/scenes/milestone02_classroom.scene.json`, face test `test_face.scene.json`.
Character generator: `tools/make_girl_v2.py` (reproducible edits on top of the frozen milestone-01 asset).
Assessment: `docs/SCALABILITY_ASSESSMENT.md`.

## Build & test status
- Linux (Ubuntu 24.04, GCC 13): builds cleanly; 24 unit test cases + 3 look-regression tests (milestone 01, neutral
  face v2, A/B/C lineup) pass (iteration 4).
- Studio verified under a virtual display with software OpenGL (screenshots of viewport and in-app path tracing).
- Windows: not built yet (vcpkg manifest prepared).

## Measured performance (cloud build machine: 4-core Xeon 2.1 GHz, 15 GB RAM, no GPU)
| Render | Time |
| --- | --- |
| 960x540, 64 spp, full fibres (~1.6M) | 77 s |
| 640x360, 32 spp, full fibres | 25–35 s per frame |
| 480x270, 16 spp, preview density | 5 s |
| Iteration 4: water table v4 (3 characters, SSS), 640x360, 12 spp | ~29 s per frame (21.5 s render + 7.1 s scene update) |
| Iteration 4: 1280x720 group still, 96 spp | 3–5 min; peak memory 7.7 GB |
Your computer's numbers will differ; unknown until you run it.

## Hardware
The user's computer has not been inspected (work happens in a cloud container). Design assumption: any x86-64
CPU, any OpenGL 3.3 GPU, 16 GB RAM. Provide specs when convenient to tune budgets.

## Repository layout
See `README.md`. Decisions: `TECHNICAL_DECISIONS.md`. Status per feature: `FEATURE_STATUS.md`.
Known problems: `BUGS_AND_ISSUES.md`. What to do next: `NEXT_STEPS.md`. History: `DEVELOPMENT_LOG.md`.

## Important environment notes for continuation
- Dependencies on the build container: apt packages listed in README; Open Image Denoise 2.3.3 prebuilt in
  `/home/user/deps/oidn-2.3.3.x86_64.linux` (re-download if the container was recycled).
- No Git remote is configured yet; the session sends a git bundle as a backup. Attach a GitHub repo for durable storage.
