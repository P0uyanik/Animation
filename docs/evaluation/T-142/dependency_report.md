# T-142 step 1: legacy engine dependency report (CHECKPOINT, nothing removed)

Input `integration/t-140 @ 5d0947c`. Static audit of includes, CMake targets, callers in engine/apps/tests/tools/pipeline/CI.
Codex map `docs/audit/legacy_engine_deps/` was made at `37901c4`. Between the two commits only tools/motion_checks/reach and docs changed, so the comparison holds.

## 1. Remove (proven unused once the renderer job is gone)

| Path / symbol | Evidence |
|---|---|
| `engine/render/{pathtracer,bsdf,image}.{h,cpp}` (`plush_render`) | Built only with `PLUSH_BUILD_RENDERER=ON`. Its only includers are `apps/render-cli` (guarded by `PLUSH_HAS_RENDERER`), `apps/studio/main.cpp`, `tests/test_render.cpp` and `tests/test_engine.cpp:5-7`. In `test_engine.cpp` the includes are unused: the file uses no render symbol. |
| `apps/export-obj/` (`plush-export-obj`) | No caller in pipeline, tools or CI. The only mentions are root `CMakeLists.txt:31`, `tools/regression_paths.txt:39` and docs. |
| `tests/test_render.cpp` (5 cases) | Covers only `engine/render`. |
| CTests `regression_milestone01`, `regression_face_neutral`, `regression_lineup_abc`, `renderer_tests_skipped` | These run `plush-render` in image mode or report that it was skipped. |
| `content/scenes/test_lineup.scene.json`, `content/characters/girl_brown_glasses.character.json` | Only consumer: `regression_lineup_abc`. The name `girl_brown_glasses` in `reference_index.json` is a label only, not a file dependency. |
| `content/scenes/test_face.scene.json`, `tools/make_face_test.py` | Only consumers: `regression_face_neutral` and the generator script. |
| `PLUSH_BUILD_RENDERER`, Embree/OIDN, `PLUSH_OIDN_ROOT`, `plush_stb` | Found in `CMakeLists.txt`, `engine/CMakeLists.txt`, `cmake/Dependencies.cmake:10-45`, the vcpkg `renderer` feature, `ci-dependencies.json renderer_packages` and `install_ci_dependencies.ps1:8,157,160`. stb is used only by `render/image.cpp`. Studio would need stb_image only if decision D1 picks option B. |
| CI renderer job | `checks.yml` job `renderer` (l.225-317), plus `renderer` in the gate's `needs` (l.460). Also: `combine_check_reports.py:109,115`, `ci_status.py:39 REQUIRED_JOBS`, `check_all.py:490-512 renderer_skip`. `tools/ci/tests/test_t127_shards.py:63,67` needs a fixture edit only. |

## 2. Mixed files (remove the legacy part only)

- **`apps/render-cli/main.cpp`.** Keep the binary name and path, scene load, frame range, evaluator and `--bake`/`bakeShot`. Callers: `run_shot.py`, `measure_shot.py`, `measure_clips.py`, `test_emotions.py`, `test_shot_eyes.py`, and `PLUSH_RENDER_CLI` in `test_shot_workflow`. Remove the `#ifdef PLUSH_HAS_RENDERER` branches and these flags: `--out`, `--outdir`, `--video`, `--spp`, `--compare`, `--max-rmse`, plus any denoise and other image-only flags. `--preview` stays only if bake reads it; to be checked in step 3.
- **`apps/render-cli/CMakeLists.txt`.** Remove the `plush_render` link and the `PLUSH_HAS_RENDERER` define.
- **`tests/CMakeLists.txt`.** Remove the renderer `target_sources`, the skip test and the 3 regressions.
- **`tests/test_engine.cpp`.** Remove only the 3 unused `render/*.h` includes. No test case changes.
- **`cmake/Dependencies.cmake`, `vcpkg.json`, `ci-dependencies.json`, `install_ci_dependencies.ps1`, `regression_paths.txt`.** Remove the renderer entries only.
- **`apps/studio/`.** Needs decision D1 before any change.

## 3. Kept, and why

| Kept | Why |
|---|---|
| `engine/model/sdf.{h,cpp}`, **complete** | Collision and scene SDF. Used by scene `"kind":"sdf"` objects (`scene.cpp` `partFromJson`/`primToJson`/`meshSdfPart`) and by the legacy-rig fallback that `collision.cpp` uses through `SkinnedMesh`. Covered by `test_engine` mesher cases 91 and 119. |
| `engine/model/character.{h,cpp}`, **complete** | Holds the shared `CharacterAsset`, `CharacterRig`, `SkinnedMesh`, `MorphTarget`, `poseCharacter`, `walkStep`, `resolveExpression` and `expandInbetweens`. Users: `imported_character`, `scene`, `actions`, `collision`, `interaction`, `clip_layers`. The SDF-character builder in the same file is still a live fixture for **12 active-system test files**: `test_collision`, `test_interaction`, `test_hand_shapes`, `test_body_mechanics`, `test_verbs`, `test_bake_golden` (`kSdf` / "engine" golden hashes), `test_face_layer`, `test_emotion_blend`, `test_framing`, `test_gaze_legibility`, `test_imported_character` and `test_engine`. |
| `engine/fuzz/` | Part of the active evaluator: `scene.h:35,208-226,282` and 32 references in `scene.cpp`. The character builder uses it heavily (79 references). Tested by `test_engine` cases 239 and 320. |
| `content/characters/{boy_dark_hair,girl_white_hair}.character.json` | Fixtures of the active tests listed above. |
| `milestone01/02_classroom.scene.json`, `girl_white_hair_{m01,v2}.character.json` | Studio opens milestone01 (`main.cpp:1544`). Milestone02 holds the reference SDF scene objects. Removing them is optional; keeping them is lower risk. |
| `tests/regression/*.png` (4 files) | Listed in `tools/frozen_manifest.txt:149-152` and immutable. They stay as evidence after their tests are removed. |
| `apps/studio/{shot_workflow.*, shot_job_windows.cpp}`, `test_shot_workflow.cpp` | Production workflow library, built without the renderer. |

## 4. Test inventory

| | doctest cases | ctest entries |
|---|---|---|
| Before, renderer OFF (linux/windows gates) | 218 | 2: `plush_tests`, plus `renderer_tests_skipped` (skipped) |
| Before, renderer ON (linux renderer job) | 223 | 4: `plush_tests` plus 3 image regressions |
| After (every build) | **218** | **1**: `plush_tests` |

What gets removed: the 5 `test_render.cpp` cases, 3 image regressions and the skip marker. These cover only the path tracer and its image output. No active-system case, threshold or golden changes.

## 5. Decisions for the owner

- **D1: `apps/studio/main.cpp` (plush-studio UI).** IMPLEMENTER_PROMPT calls this app the product. It is not unused. It links `plush_render` for three things: the path-traced Render panel, `readImageRgb8` for production frames, and `bsdf.h` types.
  - A: keep the renderer and studio as they are, and remove only export-obj plus the dead includes.
  - B: decouple the studio. Delete the Render panel, replace `readImageRgb8` with stb_image, keep Production/Viewport/Timeline, then remove the renderer. This is a product-code change beyond pure removal.
  - C: remove `main.cpp` and keep only `plush_shot_workflow`.
  - Recommendation: **B**, if the owner wants the renderer gone. Otherwise A.
- **D2: branch protection.** `linux renderer` is a required check (`ci_status.py:39`). The owner must drop it from the repository settings in the same window as the merge, or merges block. A cloud session cannot change this.
- **D3: confirm** that the SDF character, `fuzz` and `character.*` stay out of T-142. Removing them means rewriting fixtures in 12 active test files and the `engine` golden hashes, which the binding conditions forbid. That can be a separate task.

## 6. Comparison with Codex T-151 (`deps.md`/`deps.csv`)

| # | Point | Codex | This report | Status |
|---|---|---|---|---|
| 1 | `engine/render/*`, `test_render.cpp`, `apps/export-obj/` | SAFE TO REMOVE | Remove | agree |
| 2 | `render-cli` | MIXED, keep `--bake` contract | Same | agree |
| 3 | `apps/studio` | MIXED: retire preview and procedural editor in `main.cpp`, keep `shot_workflow` | Agree on `shot_workflow`. `main.cpp` is the product UI, so it is not "genuinely unused". Owner decides (D1). | **disagree (scope)** |
| 4 | CI renderer job, `needs` edge, combine, `ci_status`, `check_all`, shard test | MIXED, remove | Same. I add `install_ci_dependencies.ps1`, the vcpkg feature, `regression_paths.txt`, and the branch-protection required check (D2). | agree, plus additions |
| 5 | `character.*`/`scene.*`/`fuzz` | MIXED: extract shared types, retire SDF-character authoring, fuzz and locks "after migrating callers" | KEEP whole in T-142. Migration would edit active tests and the `engine` golden hashes (binding conditions). `fuzz` is part of the evaluator. | **disagree** |
| 6 | Collision and scene SDF must stay (`sdf.*`, `kind:"sdf"`, collision fallback) | Keep | Keep `sdf.*` whole | agree |
| 7 | Legacy collision fixtures | "Migrate those cases before removing the legacy builder" | No migration: the builder is kept, so the fixtures are untouched | **disagree** (follows from 5) |
| 8 | `test_engine.cpp` cases 164/239/299/320 | "Separate" (remove or move) | Keep all cases; remove only the 3 render includes | **disagree** (follows from 5) |
| 9 | 3 image CTests | Retire | Retire, plus the skip marker | agree |
| 10 | Regression PNGs | Preserve (frozen) | Preserve | agree |
| 11 | Legacy scenes and characters | Preserve (mixed consumers) | Remove `test_lineup`, `test_face`, `girl_brown_glasses`, `make_face_test.py` (consumers are only removed tests). Keep the milestone scenes. | **minor disagree** |
| 12 | Desktop GLFW/GLEW/ImGui wiring | Retire | Only under D1 option C; options A and B keep it | depends on D1 |

ledger: build 0 · render 0 · tests 0 · ci 0 · wait 0 (min) · env setup no
