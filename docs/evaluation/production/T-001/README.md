# T-001 evidence: Plush Studio ↔ shot pipeline (2026-11-15)

**Environment:**
- Blender: the bpy 5.3.0 module (Python 3.13) through a `blender` wrapper.
- GL: Mesa llvmpipe (LLVM 20.1.2), OpenGL 4.5 core, under Xvfb.
- Engine build: the image regressions were run with the official OIDN 2.3.3 prebuilt, a build dependency installed outside the repository (`-DPLUSH_OIDN_ROOT`); see Regression.

Renders are low resolution on purpose (320×180, 16 samples). Scripts and settings are listed at the end.

## R6: command line vs Studio (`equivalence_s010.json`)
**Setup:**
- Shot: s010, frames 5–7, 320×180, 16 samples.
- Command-line run: the M3.2 default command, outputs in `<shot>/build/`.
- Studio run: `--script-production`, run folder `<shot>/build/runs/<id>/`.
- Compared by `pipeline/production/tests/compare_runs.py`, run inside Blender.

| Field | Command line | Studio | Difference |
| --- | --- | --- | --- |
| Bake file | – | – | byte-identical (sha256) |
| Bake: camera per frame (position, target, up, lens, sensor, f-stop, focus) | – | – | max 0.0 |
| Bake: skinning matrices (all bones, both characters) | – | – | max 0.0 |
| Bake: morph control weights | – | – | max 0.0 |
| Bake: static fields (fps, frames, render, lights, objects, characters) | – | – | all equal |
| Bone reconstruction: boy | 73 bones, 0.0003 mm, 0.0° | same | equal |
| Bone reconstruction: girl | 73 bones, 0.0004 mm, 0.0°, `DEF-jaw` left to drivers | same | equal |
| Blender camera `matrix_world` (frames 5–7) | – | – | max 0.0 |
| Blender camera lens | – | – | max 0.0 |
| Frames | `frame_0005..0007.png` (3) | `frame_0005..0007.png` (3) | equal |
| Resolution / samples / denoise | 320×180 @ 100 %, 16, on | same | equal |
| Exposure / view transform | 0.4 / AgX | same | equal |
| `light_scale` (as light energies + world strength) | area 188.827, 46.576; sun 4.5; world 0.35 | same | equal |
| Pixels (8-bit RGBA) | – | – | 0 differing pixels in all 3 frames |

- **Cycles determinism:** Cycles was bit-deterministic here (same machine).
- **PNG bytes:** the files differ only in metadata (date, render time).
- **Before T-001:** the same command line run with `main`'s `run_shot.py` produced the same bake, resolved scene, cast.json and pixels.

## R1: idempotent prepare (`pipeline_workflow_tests.json`, `idempotent_prepare`)
**Method:** prepare runs twice on every shot. Before and after the second prepare, I recorded sha256, size and mtime (ns) of every file under:
- `assets/`;
- the published 1.0.0 version;
- the shot's `masters/` and `packages/`;
- `shot.resolved.scene.json` and `cast.json`.

| Shot | Files compared | Changed | Second prepare |
| --- | --- | --- | --- |
| e000_pilot/s010 | 126 | 0 | all cached: boy published (read only), package cached; girl master cached, package cached |
| e900_workflow_test/s010 | 119 | 0 | all cached: boy published (read only), package cached |

## R3: cancel during the Blender render (`studio_cancel_s010.json`, process lists)
**Setup:** s010 frames 1–120 at 320×180 / 16 samples. Studio cancelled it once 1 frame was finished, while Blender was rendering.

- **Process group before:** `run_shot.py` and Blender (`processes_before_cancel.txt`).
- **Process group after:** empty. No process names the run id in `processes_after_cancel.txt`.
- **Cancel itself:** graceful (SIGTERM), 0.05 s, no SIGKILL needed.
- **Run state:** `status.json` says `cancelled (SIGTERM)`, `frames_done` 1.
- **Frames:** the one frame on disk is a complete PNG.
- **Earlier runs:** 29 earlier run folders unchanged (size and mtime of every file); `latest` unchanged.

**Partial frames** (pipeline test, fake Blender that leaves half a PNG):
- After a SIGTERM to the process group, `frame_0012.png` (partial) is removed and `frame_0011.png` (complete) is kept.
- After a forced kill, `--mark-cancelled` gives the same result.

## R2: preview evaluation equals the bake (`studio_production_*.json`, `playback_check`)
**Method:** Studio's preview evaluator (the one the viewport draws from) is compared with the pipeline's bake at 12 frames of s010 and 9 frames of e900.

**Result:** camera, skinning matrices and morph weights differ by at most 0.0.

**The animation changes over time:**
- s010: the girl's root travels 0.31 m (walk); Smile 0→1 (boy); Laugh and Smile 0→1 (girl); camera 0.51 m push-in.
- e900: the boy's root travels 0.75 m; Smile 0→1; camera target moves 0.56 m.
- Timeline playback showed 31 (s010) and 33 (e900) distinct frames in 3 s.

## R5: viewer frame mapping
- **s010 run 5–7:** frames 1, 4, 8 and 120 show "not rendered in this run (run range 5-7)"; frames 5, 6 and 7 show `frame_0005..7.png`.
- **e900 run 20–22:** frames 11, 19, 23 and 70 show the message; frames 20–22 show their images.
- **Settings shown:** taken from the run's `status.json` (range, resolution, samples, light_scale, exposure).
- **Screenshots:** `studio_*_viewer_rendered_*.png` and `studio_*_viewer_not_rendered_*.png`.

## AC4: progress, responsiveness and failure
**Live progress:** stage and frame updates were recorded during the render. For s010:
- bake at 0.1 s;
- render 0/3, then 1/3, 2/3 and 3/3 frames;
- encode;
- done at 9.7 s.

**Responsiveness:** 71 UI frames were drawn while the job ran. The longest UI frame took 0.25 s (the scene reload after prepare).

**Failure:** a render with a missing Blender shows `FileNotFoundError: ... '/nonexistent/blender'` in the panel (`studio_s010_render_failure.png`). The run is marked failed.

## Regression (`regression_results.txt`)
- **Passing:**
  - `plush_tests`: 39/39, 19631 assertions (5 new workflow test cases).
  - `test_export_engine`: 8/8.
  - `verify_charsys`: PASS.
  - Studio round trip: `--script-hair-edit` then `--script-verify` on a copy of `watertable_v4`, `lashes.L` 4 → 5.
- **ctest: 4/4 (AC10 PASS).** with the official OIDN 2.3.3 prebuilt (a build dependency installed outside the repository, `-DPLUSH_OIDN_ROOT=<path>`), `ctest` is 4/4 on unchanged `main` 1ab1ade and on the branch e6e9246, with identical rmse (m01 0.0164, face_neutral 0.0004, lineup 0.0000). This was independently confirmed in the Supervisor environment (`ctest` 4/4, `plush_tests` 39 test cases / 19631 assertions).
  - Without OIDN (the first runs in this environment), `regression_milestone01` (rmse 0.0464) and
    `regression_face_neutral` (rmse 0.0406) failed identically on `main` and the branch.

## Scripts and settings
- **Command line:** `python3 pipeline/production/run_shot.py --shot episodes/e000_pilot/shots/s010/shot.scene.json --blender <blender> --frames 5-7 --resolution 320 180 --samples 16`
- **Studio:** `plush-studio --shot <shot> --blender <blender> --script-production <dir> --script-frames 5-7 --script-size 320 180 --script-samples 16`. The e900 run used `--script-frames 20-22`. The other flows use `--script-cancel <dir>` and `--script-fail <dir>`.
- **Pipeline tests:** `python3 pipeline/production/tests/test_run_shot_workflow.py --blender <blender> --out <dir>`
- **Comparison:** `blender -b --factory-startup -P pipeline/production/tests/compare_runs.py -- --a <cli dir> --b <studio run dir> --out <json>`
