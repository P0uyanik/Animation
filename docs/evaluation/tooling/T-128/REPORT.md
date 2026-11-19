# T-128 tooling trial: report

Input `integration/t-128-prep @ b80dae6`, branch `t-128-claude-tooling-trial`. Measured 2026-11-19 in a cloud session:
4 vCPU, Ubuntu 24.04, GCC 13.3.0, CMake 3.28.3, Ninja, Python 3.13.18. The build is Release with the renderer OFF
(the gate's default), so the C++ tests are 215 doctest cases. Times are wall-clock seconds from single runs unless a
run count is given. They are session numbers, not CI numbers.

**Nothing here is a default.** No existing file is changed. CMakeLists.txt, the tests, the gate and CI are untouched.

## Summary

| Item | Verdict | Evidence |
|---|---|---|
| 2a ccache (session) | **adopt as opt-in** | A warm rebuild in a fresh build dir took 1.6 s instead of 115 s. Same 215/215 tests pass. |
| 2b mold linker | **reject** | Clean build 108 s vs 115 s (within noise). Incremental build 18.5 s vs 18.2 s. Link time is not the bottleneck. |
| 2c CI ccache 31 % | **proposed patch** (T-127 owns CI) | The reported rate is cumulative: `ccache -z` is never run (see below). |
| 3 OIIO / SSIM / VMAF | **do not add to the gate**. Offer OIIO and SSIM to T-124/T-125 as optional tools. | 28/28 verdicts match. Time saved: 0.15 s over 28 pairs. VMAF was not measured (see below). |
| 4 parallel tests | **adopt as opt-in helper** | Every serial and parallel run gave identical results. Python 12.2 s → 8.3 s, C++ 201 s → 112 s (`-j4`). |

## 2. Faster C++ builds

Opt-in files: `cmake/opt_in/fast_build.cmake` and the `fast-dev` preset in `CMakePresets.json`. Each tool is used only
if it is installed (`apt-get install ccache mold`).

| Build (renderer OFF, `-j4`) | base | mold only | ccache+mold, cold | ccache+mold, warm, new dir |
|---|---|---|---|---|
| clean | 114.9 | 108.0 | 109.8 | **1.6** (49/49 hits) |
| incremental, touch `tests/test_verbs.cpp` (3 runs) | 17.9 / 18.1 / 18.5 | 18.4 / 18.2 / 19.1 | – | – |

- ccache adds no measurable overhead when the cache is cold. It pays off when you rebuild the same sources: a new
  build dir, a branch switch, a worktree or `git stash`. One caveat: a test that only `touch`es a header measures
  nothing, because ccache hashes file content (0.3 s vs 104 s). A real header edit misses the cache as usual.
- mold links the doctest binary in well under a second either way. The time goes into compiling heavy TUs (one
  TU ≈ 18 s), so mold buys nothing here. It may matter later for the renderer/studio link, but that was not measured.
- Equivalence: `plush_tests` from the base build and from the ccache+mold build both report
  `215 | 215 passed | 0 failed`, and the base ctest run reports `2/2` (plush_tests plus the renderer-skipped marker).
  The ccache+mold binary was then run 6 more times in §4.

Use: `cmake --preset fast-dev && cmake --build --preset fast-dev && ctest --preset fast-dev`
(or `-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=cmake/opt_in/fast_build.cmake` on any build). Switch off one tool with
`-DPLUSH_FAST_MOLD=OFF` or `-DPLUSH_FAST_CCACHE=OFF`.

### 2c. CI ccache: why "31 %" is misleading. Proposed patch for T-127, not applied.

`checks.yml` restores `~/.cache/ccache` and prints `ccache --show-stats` after the gate, but never runs `ccache -z`
first. The stats file is restored together with the cache, so the 31 % is a running total over every earlier run
whose cache was inherited. It does not describe the current run. The key `ccache-linux-${{ github.sha }}` +
`restore-keys: ccache-linux-` is reasonable: it saves once per commit and restores the newest cache this branch can
see. The other contributor is GitHub's branch scoping: a new task branch can restore only its own caches or the
default branch's, not the integration branch's. That means a cold-ish cache on the first run. Proposed patch, the
same for the renderer job:

```diff
       - name: Gate
         if: steps.merge.outputs.clean == 'true'
         env:
           CHECK_ALL_BASE_REF: ${{ needs.plan.outputs.base }}
           CMAKE_C_COMPILER_LAUNCHER: ccache
           CMAKE_CXX_COMPILER_LAUNCHER: ccache
+          CCACHE_BASEDIR: ${{ github.workspace }}
+          CCACHE_COMPILERCHECK: content
         run: |
+          ccache -z
           status=clean
@@
-          ccache --show-stats | head -5 || true
+          ccache --show-stats -v | grep -E 'Hits|Misses|Cache size|Uncacheable' || true
```

Measure a few runs with the per-run numbers before changing the key. mold in CI is not proposed (see 2b).

## 3. Image/video comparison tools

`tools/dev/compare_bench.py`, using the pinned `requirements-tools.txt` in a venv, compares the gate's verdict
(`tools/regression/run.py`: `image_difference` + `within_noise`, imported unchanged) with OpenImageIO
`ImageBufAlgo.compare` (the engine behind `idiff`). Inputs are the 4 `tests/regression/*.png` images, each against 7
seeded variants: identical, ±1, ±3 and ±12 noise, +2 brightness, a 1 px shift, and a patch. That makes 28 pairs.

- **Verdicts: 28/28 identical. 0 mismatches.** The definitions are not identical, though. OIIO's RMSE is taken over the
  file's own channels (RGB), while the gate's is over RGBA after converting the image (alpha difference 0). Because
  of that, OIIO reads up to about 15 % higher (max |ΔRMSE| 0.0052). `changed_fraction` differs by up to 0.012 on
  the shifted variants. OIIO is not a drop-in replacement for the noise threshold. Two more things a caller must
  handle: OIIO premultiplies PNG alpha unless you set `oiio:UnassociatedAlpha`, and if one image is RGB and the other
  RGBA, OIIO reports RMSE 0.5 (the first run of this bench hit that).
- **Time: 278 ms (existing) vs 128 ms (OIIO) vs 767 ms (SSIM) over 28 pairs.** That saves about 5 ms per image, which
  is nothing next to a render that takes minutes.
- SSIM (scikit-image) adds a perceptual signal the gate does not have. A +2 brightness change scores 0.9998, a
  1 px shift 0.89–0.93. It could help the T-124/T-125 *review* views, but not as a gate verdict.
- **VMAF: not measured.** Ubuntu's ffmpeg 6.1.1 is built without `libvmaf`. Only the `ssim`, `psnr` and `vmafmotion`
  filters are present. A pinned static ffmpeg with libvmaf would be one more binary to vet. I did not fetch one.
- Recommendation: no new dependency in the gate. Offer `requirements-tools.txt` (OIIO, scikit-image) to T-124/T-125
  as optional session tools.

## 4. Parallel tests in a session

`tools/dev/parallel_tests.py`:

- **Python (`py`)**: runs exactly the gate's list. It gets the commands by calling
  `check_all.check_python_tests` with its runner patched to record instead of execute, so the list is never copied by
  hand. Each script runs as its own process.
- **pytest-xdist does not apply.** The gate runs plain scripts, not pytest, so `pytest -n` would change the test set.
- **C++ (`cpp`)**: splits the doctest binary into N shards by case index (`--order-by=name --first/--last`). It reads
  per-case verdicts from JUnit output and fails if any listed case was not run.
- **`ctest -j` does not apply.** ctest sees one real test (`plush_tests`) plus the skipped marker.
- Shared paths: several C++ tests write fixed names under `temp_directory_path()`, for example
  `t096_bad_interaction.scene.json` and `plush_t097d_acting`. Inside one run each name belongs to one case, so shards
  do not collide. Two runs at the same time would. The helper therefore gives every job its own `TMPDIR`.
  `test_bake_golden` writes the golden file only when asked to. `git status` was unchanged after all runs.

| Suite (same set every run) | serial ×3 | parallel `-j4` ×3 | results |
|---|---|---|---|
| Python, 23 scripts | 11.3 / 12.1 / 13.1 s | 7.8 / 8.5 / 8.7 s | 6/6 runs: identical per-script exit codes, 23/23 pass |
| C++ doctest, 215 cases (ccache+mold binary) | 202.7 / 198.4 / 202.7 s | 110.8 / 112.7 / 112.2 s | 6/6 runs: identical per-case verdicts, 215/215 PASS, 0 missing |

The Python gain is capped by `tools/cleanup/run_tests.py` (6.3 s on its own). The C++ gain is capped by the
slowest shard: shards are split evenly by case count, not by runtime.

Found during the trial and fixed in the helper: doctest's JUnit output lists each subcase as `case/subcase`. The first
version of the helper therefore reported 3 cases as "missing". The verdicts now roll subcases up to their parent case,
and all 6 runs were re-checked from their saved XML.

## Revert

Every change is a new file, and nothing existing references any of them. `git revert` of the T-128 commits (the tooling is in the first commit;
the later ones change only the helper and this report) restores the previous state exactly. You can also delete the files one by one: `CMakePresets.json`, `cmake/opt_in/`,
`tools/dev/parallel_tests.py`, `tools/dev/compare_bench.py`, `requirements-tools.txt`.
