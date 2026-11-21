# Claude session clone profiles (T-180, measured 2026-11-21)

Input: origin/main `b9c0d4e`. Measurement only: no code, test, asset or history change. Machine: 4 vCPU cloud
container, Blender 5.3.0 (bpy module wrapper at `/usr/local/bin/blender`), gate command
`python3 tools/check_all.py --base origin/main --blender /usr/local/bin/blender --task T-180 --full`.

## 1. Measurements

Light clone as started (depth 1, partial `blob:none`, sparse): `.git` 61 MB, worktree 87 MB (excluding `.git`).
`git config remote.origin.partialclonefilter` = `blob:none` (it IS a blob-filtered partial clone); shallow = true.
Sparse list at start: `.github apps archive assets/references cmake content docs/architecture docs/archive docs/audit
docs/characters docs/iteration4 docs/milestone03 docs/milestones docs/process docs/references docs/second_character
docs/tasks engine episodes pipeline tests tools` (no `assets/characters`, no `docs/evaluation`).

| Run | Sparse paths | Wall time | Result |
|---|---|---|---|
| 1 | light (as started) | 26 m 57 s | gate **crashed** in the Blender tier (`deform`): missing `docs/evaluation/characters/fidelity_baseline.json`; no report written. Before that: CTest 1/2 FAIL, plush_tests 238/240, Python tests 4 failing files, doc links FAIL, many Blender units FAIL |
| 2 | + `assets/characters` + `docs/evaluation/characters` + `docs/evaluation/process` | 67 m 53 s | CTest 1/2 FAIL (plush_tests 239/240), Python 5 failing files, doc links FAIL, Frozen assets FAIL, Blender: verify_charsys, boy fingerprint, material presets, regression boy + girl FAIL (baselines missing), girl_white_hair_blue_dress PASS |
| 3 | + all `docs/evaluation` | interrupted by a worker restart at about 13:49 (about 35 min in) | before the restart: CTest 2/2 PASS (285 s), plush_tests 240/240 PASS, doc links PASS, Python tests 1 error (see below), Blender units charsys to export-determinism, boy2 PASS |
| 3b | same (shards of the interrupted tail, `--blender-shard K/5`) | shard 5 (export-determinism, boy2, deform) 9 m 33 s; shard 3 (shot-eyes, emotions) 6 m 44 s; shard 1 (charsys, face, material presets, engine selector, materials-r2, **fidelity regression**, T-159 units) 16 m 33 s | all three PASS; regression boy_yellow_hoodie PASS (fidelity 69.66), girl_auburn_bun_glasses PASS (63.41), girl_white_hair_blue_dress PASS |

Sizes of what was added (worktree, `du -sh`): `assets/characters` 368 MB, `docs/evaluation` 295 MB in total
(`docs/evaluation/characters` 206 MB, `docs/evaluation/process` 972 KB). `.git` after the adds: 374 MB, then 606 MB
(`assets/characters` + `docs/evaluation/characters` + `process`), then 683 MB (all `docs/evaluation`).
Note: the 374 MB step was inflated by one `git ls-tree -l` I ran on the partial clone, which fetched blobs lazily;
treat 61 MB to about 683 MB as the honest range, not the intermediate values. Add times: `git sparse-checkout add
docs/evaluation` took 5 s (blobs were mostly local by then); the first two adds were not timed separately.

Timings, from log timestamps of run 3 (the C++ build was cached): CTest 285 s, plush_tests about 290 s inside CTest,
Python tests and doc links about 20 s, Blender tier about 3 to 4 min for the early units, then roughly 15 min up to
`garment` (hair/groom family), `deform` 2 to 5 min per character, regression about 11 min or more.

## 2. Not sparse problems (report, not fixed)

- **Write-set**: `no claim for T-180 in docs/process/OWNERSHIP.md or docs/tasks`. Process issue of this task; would
  fail on a full clone too.
- **`test_recipe.ValidateTests.test_input_shas_are_checked_against_git`**: needs commit `ab9fd4c` (the T-087 input),
  absent in a depth-1 clone. `git fetch --depth=1 origin ab9fd4c` fails (an abbreviated SHA cannot be fetched), so it
  needs the full 40-character SHA or a deeper clone. Cause is shallow history, not a sparse path. I did not confirm
  that it passes on a full clone.
- **Frozen assets** needs `docs/evaluation/boy_pilot/cloud_v6_baseline/**` (run 2). `deform` needs
  `docs/evaluation/characters/fidelity_baseline.json`. The regression needs `docs/evaluation/regression/baselines/**`.
  Other single files seen: `docs/evaluation/animation/T-106/performance.csv`,
  `docs/evaluation/materials/T-015/legacy_materials.override.json`, `docs/evaluation/process/T-087/*.recipe.json`.
  Doc links pointed at `docs/evaluation/{animation,review,showcase,T-144}`.

I did not isolate the exact minimal subset of `docs/evaluation` per test class (each full run costs 30 to 70 min).
The evidence supports: character/Blender/regression/frozen tests need `assets/characters` and
`docs/evaluation` (at least `characters`, `process`, `boy_pilot`, `regression`, `animation/T-106`, `materials/T-015`);
doc-link checking needs most of `docs/evaluation`. Narrowing further is left to a follow-up.

## 3. The two profiles (`create_session` parameters)

**LIGHT** (code, docs, process, C++ app/engine work without character regression):

```
clone_depth: 1
blob_limit_kb: <not set; the measured light clone is already partial>   # see note
sparse_checkout_paths: [.github, apps, archive, assets/references, cmake, content, docs/architecture, docs/archive,
  docs/audit, docs/characters, docs/iteration4, docs/milestone03, docs/milestones, docs/process, docs/references,
  docs/second_character, docs/tasks, engine, episodes, pipeline, tests, tools]
```

Footprint 61 MB `.git`, 87 MB worktree. It builds and runs the gate's C++ build, but the full gate is not green:
character, Frozen-assets, doc-link and Blender tests fail on missing paths. Use `--fast`-tier checks only.

**FULL** (character, render, test work; anything that runs the full gate or Blender units):

```
clone_depth: 1
blob_limit_kb: <not set>
sparse_checkout_paths: LIGHT list + [assets/characters, docs/evaluation]
```

Footprint about 683 MB `.git`, about 750 MB worktree. Result with these paths: every gate unit PASS except the two
items in section 2. If only `docs/evaluation/characters` + `process` + `assets/characters` are added, expect the
failures of run 2.

Note on `blob_limit_kb`: the session's existing clone reports `partialclonefilter=blob:none`; I did not test a numeric
`blob_limit_kb` value, so it is not recommended here.

## 4. How a task adds paths on demand

```
git sparse-checkout add assets/characters docs/evaluation      # blobs come from the promisor remote
git fetch --depth=1 origin <full-40-char-sha>                  # only for a commit the test needs (not abbreviated)
```

Adds take seconds to a few minutes; do not run `git ls-tree -l` or `git log -p` over unfetched trees (they pull blobs).
