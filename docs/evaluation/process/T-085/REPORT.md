# T-085 report: frozen engine renderer optional in the build (2026-11-18)

1. **Task:** T-085. Make the frozen engine path tracer an optional build component: `PLUSH_BUILD_RENDERER`,
   default OFF.
2. **Result:** complete locally. CI evidence is the run on this branch, reported to the Supervisor.
   The write-set was widened by the Supervisor (proposal A+B+C) to include `tests/test_engine.cpp`,
   `tests/test_render.cpp` and `apps/render-cli/main.cpp`.

## 3. Files changed

| Path | Purpose |
|---|---|
| `CMakeLists.txt` | `option(PLUSH_BUILD_RENDERER ... OFF)` |
| `cmake/Dependencies.cmake` | Embree and OIDN are looked up only when ON. The OpenGL/GLFW/imgui deps load only when the studio app is built (`PLUSH_BUILD_STUDIO_APP` = studio AND renderer). |
| `engine/CMakeLists.txt` | `plush_render` is defined only when ON. |
| `apps/render-cli/CMakeLists.txt` | `plush-render` is always built. With ON it links `plush_render` and gets `PLUSH_HAS_RENDERER=1`. |
| `apps/render-cli/main.cpp` | `#ifdef PLUSH_HAS_RENDERER` guards only: the render header include, the denoiser log line, and the image-render path. With OFF, an image render exits 1 with an error; `--bake` is unchanged. |
| `apps/studio/CMakeLists.txt` | `plush_shot_workflow` is always built. `plush-studio` is built only with the renderer. |
| `tests/CMakeLists.txt` | `test_render.cpp` and `plush_render` are linked only when ON. With OFF, the `renderer_tests_skipped` ctest entry (Skipped) stands in for the 3 image regressions, which are not registered. |
| `tests/test_engine.cpp` | The 5 renderer TEST_CASEs and the `albedoEstimate` helper were removed (moved). No other change. |
| `tests/test_render.cpp` | New file: a 12-line header plus the moved blocks, verbatim. |
| `vcpkg.json` | `embree` moved into a `renderer` manifest feature. |
| `.github/ci-dependencies.json` | `libembree-dev` moved to `apt.renderer_packages`. |
| `.github/scripts/install_ci_dependencies.ps1` | New `-Renderer` switch (Embree apt packages + the pinned OIDN). `-Cpp` no longer installs either. |
| `.github/workflows/checks.yml` | New `renderer` job (the only ON build). It writes `check_all.json` with the existing "C++ build"/"C++ tests" names, so the verdict merges them into the existing lines (10-line limit). It is added to the verdict's `needs`. The linux and windows install steps are relabelled; triggers and concurrency are unchanged (T-086). |
| `tools/check_all.py` | Skip reporting only: reads `PLUSH_BUILD_RENDERER` from `CMakeCache.txt` and adds a skipped subcheck, shown on the C++ tests summary line. |

Evidence in this folder: `moved_tests.diff.ansi` (raw `git diff --color-moved=plain`; view it with `less -R`),
`moved_tests_check.py` and `moved_tests_check.txt`, `doctest_cases*.txt`, `bake_on_off_main_sha256.txt`,
`ctest_renderer_on.txt` and `ctest_renderer_off.txt`, `check_all_local_summary.txt` and `check_all_local.json`.

## 4. Implementation notes

- Only `engine/render/pathtracer.cpp` needs Embree. Nothing under `engine/render/**` changed.
- With OFF:
  - no renderer target (`plush_render`, `plush-studio`) is built;
  - `find_package(embree)` is never called;
  - `ldd plush-render` shows no Embree or OIDN.
- `plush-render` keeps its name and path, because `run_shot.py`, `tools/animcheck/run_gate.py` and the studio
  workflow call `plush-render --bake`.
- Skip reporting:
  - ctest: `renderer_tests_skipped ... Skipped` and "The following tests did not run";
  - check_all summary: `PASS C++ tests: renderer tests SKIPPED (PLUSH_BUILD_RENDERER=OFF): 5 path tracer doctest cases + 3 image regressions; run by the linux renderer CI job`.
- Windows: the gate builds OFF, so the vcpkg manifest install no longer builds Embree (it was most of the
  1.4 h dependency build). This has not been measured on GitHub yet: the windows job runs only on
  staging/main pushes.
- Assumption: `glfw3` and `glew` stay base vcpkg/apt dependencies. They are small, and the studio app still
  needs them with ON.

## 5. Tests run (this container: Ubuntu, gcc, cmake 3.28, ninja, 4 to 6 threads)

| What | Result |
|---|---|
| OFF configure + build, before Embree was installed in the container (`build/off`) | PASS, 48/48 targets, 1 min 19 s, 0 warnings after the `(void)` fix |
| OFF ctest | 1 passed, 1 skipped (`renderer_tests_skipped`), 51 s |
| `python3 tools/check_all.py --base origin/main --build-dir build/quality-gate` (fresh build dir, OFF) | **3 min 20 s** wall total; C++ build PASS 80.7 s; C++ tests PASS 106.9 s (CTest, `plush_tests` 124/124 cases and 36310 assertions, animcheck all PASS); Python tests and links PASS 8.0 s; Frozen assets PASS; Shared-systems lint PASS |
| check_all FAILs, expected locally | **Guarded paths** (CI files need Supervisor approval); **Write-set** (the claim-row widening lives on integration/round2-a5, not yet in this branch's base); **Blender tier** (full tier triggered by `engine/` and `apps/` paths; no bpy in this container; CI runs it). |
| ON build, with Embree 4.3 (apt) and OIDN 2.3.3 (pinned prebuilt, sha256 verified) | PASS, includes `plush-studio` and `plush-render` |
| ON ctest | **4/4 PASS**: `plush_tests` (129 cases); `regression_milestone01`; `regression_face_neutral`; `regression_lineup_abc` (70 s) |
| doctest case list, ON vs main ab9fd4c built the same way | **identical**: 129 cases on both. OFF has 124, exactly the 5 moved cases fewer. |
| Bake ON vs OFF vs main: 3 animcheck shots + `milestone02_classroom` | **byte-identical** sha256 for all 4 (`bake_on_off_main_sha256.txt`) |
| OFF `plush-render scene --frame 1` | exit 1, `built without the renderer (PLUSH_BUILD_RENDERER=OFF): only --bake is available` |
| Verbatim move check | 174 removed lines in 3 blocks, 0 added to `test_engine.cpp`. The moved part of `test_render.cpp` is identical. color-moved shows 0 plain-removed lines; the only plain-added lines are the 8 non-blank header lines. |

**Not tested locally:**
- the Blender tier (no bpy);
- the Windows build (no Windows host);
- `install_ci_dependencies.ps1` (no pwsh here).

CI covers the linux paths. Windows is covered only on staging/main pushes.

## 6. Baselines

No file under `engine/render/`, `assets/`, `tests/regression/` or `content/` changed. The frozen image regressions
pass unchanged with ON, using the same thresholds (0.03). No test was loosened: every case still runs, and with ON
the case list is identical to main.

## 7. Visual results

None needed: the image regressions are the visual check, and they pass unchanged.

## 8. Open points for the Supervisor

- The new `renderer` job runs on every trigger, adding about 5 to 10 min of Linux CPU per run (ccache keyed
  separately). T-086 can scope it with triggers.
- The verdict treats the renderer job through its report, because `combine_check_reports.py` was outside the
  write-set. A failed ON build or ctest shows as `FAIL C++ build/C++ tests: linux-renderer:quality-renderer: ...`.
  If the job dies before its `always()` report step (for example, cancelled), the verdict does not catch it.
  Adding `"renderer": True` to the required jobs in that script would close the gap (one line, for a later task).
- `tools/check_all.py` keeps configuring with the default (OFF). Developers who want the renderer run
  `cmake -DPLUSH_BUILD_RENDERER=ON`.

## 9. Commits

Branch `t-085-claude-renderer-optional`: f4e50e3 (implementation) and the evidence commit that follows it.

## 10. Resource use

Token usage: not available. Builds: one OFF, one ON, one main ON (for the case-list comparison), and one fresh
check_all build. No repeated renders.
