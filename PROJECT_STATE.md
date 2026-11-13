# Project state

_Last updated: 2026-11-13, end of session 1 of implementation._

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

## Build & test status
- Linux (Ubuntu 24.04, GCC 13): builds with zero warnings; 10/10 test cases pass.
- Studio verified under a virtual display with software OpenGL (screenshots of viewport and in-app path tracing).
- Windows: not built yet (vcpkg manifest prepared).

## Measured performance (cloud build machine: 4-core Xeon 2.1 GHz, 15 GB RAM, no GPU)
| Render | Time |
| --- | --- |
| 960x540, 64 spp, full fibres (~1.6M) | 77 s |
| 640x360, 32 spp, full fibres | 25–35 s per frame |
| 480x270, 16 spp, preview density | 5 s |
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
