# T-142 steps 2–4: evidence (Linux, local container)

Input `5d0947c`. Baseline: the same commit built in a separate worktree (renderer OFF, as in the Linux gate).

| Check | Result |
|---|---|
| Tag | `backup/20261119T224500Z/legacy-engine-renderer-2026-11-19` → `0f68267` (annotated; made by backup.yml from request branch `archive/backup-20261119T224500Z-legacy-engine-renderer-2026-11-19`) |
| Build (`PLUSH_BUILD_STUDIO=ON`, `PLUSH_BUILD_TESTS=ON`, Release, gcc, Ninja) | pass, 0 warnings. Builds `plush-studio`, `plush-render` and `plush_tests`; no Embree/OIDN needed |
| ctest | 1/1 pass (`plush_tests`, 180 s) |
| doctest case list | 218 cases before and after; `--list-test-cases` output identical (`test_cases_after.txt`) |
| shot_workflow tests (`-sf=*test_shot_workflow*`) | pass, 186/186 assertions |
| `tools/ci/tests/test_t127_shards.py` | PASS |
| Bake hashes, base vs new `plush-render --bake` | 5/5 Blender-free scenes byte-identical (`bake_compare.txt`). The 7 `content/scenes/eval` shots need Blender-built packages and fail identically (rc 1) on both; the full gate covers them. The `test_bake_golden` hashes (boy/girl/engine) pass inside `plush_tests`. |
| Studio smoke (xvfb, Mesa llvmpipe, GL 4.5) | `plush-studio milestone01 --play --screenshot …`: scene opens and the timeline plays (frame 1 → 5.97 after 120 UI frames), rc 0 (`studio_scene_playing.png`). `plush-studio --shot e900…/s010`: Production panel works with Prepare and Render (bake + Blender) (`studio_shot_production.png`) |

## Removed tests

| Test | Covered | Why removed |
|---|---|---|
| `tests/test_render.cpp`: 5 cases (energy conservation, BSDF pdf, deterministic render, subsurface walk, glass) | `engine/render` only | its code was removed |
| CTest `regression_milestone01`, `regression_face_neutral`, `regression_lineup_abc` | `plush-render` image mode with `--compare` | image mode was removed. The PNGs stay (frozen manifest). |
| CTest `renderer_tests_skipped` | skip marker for the above | nothing left to skip |

Before: 218 doctest cases plus 2 CTests (renderer OFF), or 223 plus 4 (renderer ON job). After: 218 doctest cases plus 1 CTest.
Active-test edits: only the 3 unused `render/*.h` includes in `tests/test_engine.cpp`, and the T-127 fixture, which loses the renderer job and report and nothing else.

Not run here: Windows build, the full sharded gate, the broken-commit probe, and manual runs of the Windows nightly and backup workflows. These follow the Supervisor's integration merge.
