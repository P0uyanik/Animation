# T-072: code and asset cleanup from the T-069 audit

Branch `t-072-claude-code-cleanup` from `origin/staging` (`debd84f`). Source: [T-069 audit](../T-069/README.md)
§2.2, §2.3, §2.6, §2.7, §6 (C5–C8) and the owner decisions of 2026-11-17 ("T-069 audit recommendations approved",
[OWNER_DECISIONS.md](../../../process/OWNER_DECISIONS.md)).

**Result: complete except C8 (hair_study): kept, see §3 (one link outside the claim).** 60 files moved with `git mv` and byte-identical
(rename similarity 100 %), 2 moved with a one-line root-depth fix (97 %), 1 status change in `versions.py`, 4 new
READMEs, 1 command line updated in the T-010 README. No code behaviour change; all CTest and regression inputs untouched.

## 1. How each item was verified

For every item: `git grep -n -I <name>` over the whole tree (code, `CMakeLists.txt`/`tests/CMakeLists.txt`, CI
`.github/**`, `tests/**`, `tools/**` incl. the gate and `regression_paths.txt`, `episodes/**`, evidence scripts under
`docs/evaluation/**/*.py|sh`, docs, task files), excluding the T-069 report itself. Dynamic loaders checked: folder
globs in code (`git grep "directory_iterator|glob("`): only `hair_experiments.py` globs `experiments/hair/` (archived
with it); `check_cast.py` globs `content/scenes/eval/**` only; the scene loader scans `content/assets` only; Studio
opens `milestone01_classroom` (`apps/studio/main.cpp:1531`). Markdown links to moved paths:
`tools/check_doc_links.py` PASS, and no `](…)` link names any moved file.

"Code refs" below = references outside the moved files themselves, the archived siblings and prose docs.

## 2. Moved files

### 2.1 Engine-era generators → `archive/engine_era/` (C5) — README "do not run: overwrites regression inputs"

| From | To | Code/CI/test/gate refs | Doc refs (text only, not links) |
| --- | --- | --- | --- |
| `tools/charkit.py` | `archive/engine_era/tools/` | 0 | root status docs, `TECHNICAL_DECISIONS.md:141`, `docs/BOY_BLENDER_PIPELINE_ANALYSIS.md:304`, `docs/ITERATION_04_ACCEPTANCE_REPORT.md:24` |
| `tools/make_girl_v2.py` | same | 0 | `DEVELOPMENT_LOG.md`, `PROJECT_STATE.md` |
| `tools/make_lineup.py` | same | 0 | – |
| `tools/make_milestone02.py` | same | 0 | – |
| `tools/make_milestone03.py` | same | 0 | – |
| `tools/make_watertable_v4.py` | same | 0 | `DEVELOPMENT_LOG.md`, `docs/ACTIONS_AND_DIRECTOR.md:6` |
| `tools/make_expression_sheet.py` | same | 0 | – |
| `tools/make_it4_comparison.py` | same | 0 (only `render_iteration4_evidence.sh`, archived too) | `NEXT_STEPS.md:38` |
| `tools/render_iteration3_evidence.sh` | same | 0 | – |
| `tools/render_iteration4_evidence.sh` | same | 0 | `NEXT_STEPS.md:38` |
| `pipeline/plush_views.py` | `archive/engine_era/pipeline/` | 0 | `docs/BLENDER_COMPARISON_HARNESS.md:14,50` |

### 2.2 Engine-era demo scenes → `archive/scenes/` (owner decision 3)

None of these is named in `tests/CMakeLists.txt` (only `milestone01_classroom`, `test_face`, `test_lineup`), in any
C++/Python test, tool, CI file or app. Their only code consumers were the archived generators above.

| From `content/scenes/` | Refs outside archived files |
| --- | --- |
| `compare_it4_boy.scene.json` | `docs/BLENDER_COMPARISON_HARNESS.md:46,50` |
| `milestone03_watertable.scene.json` | `PROJECT_STATE.md:48` |
| `watertable_v4.scene.json` | `docs/ACTIONS_AND_DIRECTOR.md:6`, `docs/PROJECT_STATUS_AND_ARCHITECTURE_AUDIT.md:27`, iteration-4 report, T-001 evidence (history) |
| `test_expressions_boy_dark_hair.scene.json`, `test_expressions_girl_brown_glasses.scene.json`, `test_expressions_girl_white_hair.scene.json` | `PROJECT_STATE.md:49` |
| `test_hand_poses.scene.json` | `DEVELOPMENT_LOG.md:123` |

### 2.3 One-off clip evidence scripts → task evidence folders (C6)

| From | To | Change | Evidence |
| --- | --- | --- | --- |
| `pipeline/clips/t010_sheets.py` | `docs/evaluation/animation/T-010/` | `ROOT` +2 `..`; usage docstring path | 0 code refs; T-010 README command updated |
| `pipeline/clips/make_t014_shot.py` | `docs/evaluation/animation/T-014/` (new folder + README pointing to `docs/evaluation/characters/T-014/`, which is outside the claim) | `ROOT` +2 `..` | 0 code refs. Output of old vs new location compared: `cmp` identical. |
| `pipeline/clips/t014_contact_sheet.py` | `docs/evaluation/animation/T-014/` | none | 0 refs |

`tools/shared_character_allowlist.txt` (guarded) was **not** changed: the lint only fails on occurrences above the
allowlisted count, so the two stale `make_t014_shot.py` lines (and the `hair_experiments.py` / `review_views.py`
lines, §2.4) are harmless. The lint passes. The Supervisor may delete those four lines later with a trailer.

### 2.4 Boy CP-2 experiments → `archive/experiments/` (C7; F09/H28 rejected by the owner)

| From | To | Evidence |
| --- | --- | --- |
| `assets/characters/boy_yellow_hoodie/experiments/hair/` H00–H12, H20–H27, H29–H35 (28 files) | `archive/experiments/boy_yellow_hoodie/hair/` | only consumer `hair_experiments.py` (glob) and `review_views.py` (`H00_reference`), both archived; no test/CI/gate ref |
| `…/experiments/face/F01–F08` (8) | `archive/experiments/boy_yellow_hoodie/face/` | no code ref; docs `docs/evaluation/face_controls/FACE_CONTROLS.md` (text) |
| `…/experiments/generic_tests/G01–G03` (3) | `archive/experiments/boy_yellow_hoodie/generic_tests/` | no code ref; docs `FACE_CONTROLS.md:138`, `docs/second_character/M2_GENERIC_BODY_RIG.md:68`, `M3_FACE_SYSTEM.md:51`, historical build-report JSONs |
| `pipeline/charsys/hair_experiments.py` | `archive/experiments/charsys/` | no importer; docs `docs/CHARACTER_PRODUCTION_PIPELINE.md:57`, `HAIR_EXPERIMENTS.md:10` |
| `pipeline/charsys/review_views.py` | `archive/experiments/charsys/` | no importer; doc `HAIR_EXPERIMENTS.md:138` |

### 2.5 `hair_clumps/2` retired (status only)

`pipeline/charsys/versions.py`: `REGISTRY.retire("groom", "hair_clumps/2")` appended after the built-in block (the
registration line itself is unchanged, per "never edit an existing line"). Pins: `git grep hair_clumps/2` finds no
spec, override, episode, content or fidelity-baseline pin; only H20–H35 (archived) and the frozen H28. Not affected:
`hair_generic_test.py` (gate) calls `hair.py` directly, not the registry; `test_versions.py` "contradicts" check
still raises the expected error. `test_versions.py`: 71/71 PASS (before: 72/72; the removed check is the
per-released-version loop entry "released groom hair_clumps/2 resolves", expected after retiring).

**For the Supervisor (T-071 owns the doc):** `docs/CHARACTER_SYSTEM_VERSIONS.md` line 61 should mark it retired, e.g.
`| groom | hair_clumps/1, hair_clumps/2 (retired, T-072), groom/1 | …`.

## 3. Kept, and why

| Item | Why kept |
| --- | --- |
| `assets/characters/boy_yellow_hoodie/experiments/face/F09_jaw_corner_center.json`, `…/hair/H28_irregular_crown_only.json` | **Frozen** (`tools/frozen_manifest.txt` lines 16–17; F09 also used by `tools/simulate_quality_gate.py:113`). Rejected by the owner but frozen files are not moved. To archive: Supervisor updates the manifest (+ `simulate_quality_gate.py`). Note: H28 pins the now-retired `hair_clumps/2`, so it cannot be rebuilt from `main`. |
| `tools/make_face_test.py` | Guarded (`**/*_test.py`); moving needs `Supervisor-Approved: tools/make_face_test.py`. Hazard: rewrites the CTest input `test_face.scene.json` if run. Archive later with that trailer. |
| `content/scenes/milestone02_classroom.scene.json` | Input of `make_face_test.py` (still in place). Move together with it. |
| `content/scenes/milestone01_classroom`, `test_face`, `test_lineup`, `eval/**` | CTest regression inputs / Studio default / evaluation shots |
| `pipeline/triptych.py` | Listed in T-069 §2.6 but outside the T-072 write-set |
| `pipeline/clips/t022_contact_sheet.py` | **Imported** by `docs/evaluation/animation/T-030/contact_sheet.py:17` and `docs/evaluation/integration/batch1/contact_sheet.py:21` (`from t022_contact_sheet import project`) |
| `pipeline/charsys/experiments/hair_study/**` (C8) | T-044 reached `origin/staging` during this task (merge `665ec6a`/`dd4984a`), and nothing imports the folder (`git grep` of `hair_study`, `primitives`, `study_build`, `scorecard` in `groom_hybrid*.py`, `hair_v3*`, `test_hair_v3*`, T-044 evidence: no import). **But** `docs/evaluation/characters/T-049/README.md:157` has a Markdown link to `pipeline/charsys/experiments/hair_study/README.md`; that file is outside the T-072 claim, so moving the folder would fail the link check. To finish C8: claim that one line too, `git mv pipeline/charsys/experiments/hair_study archive/experiments/hair_study`, and point the link at `../../../../archive/experiments/hair_study/README.md`. |
| `pipeline/compare_sheet.py`, `pilot_metrics.py`, `pipeline/blender/compare_harness.py` | Imported by frozen `reproduce_v6.py` and fidelity tools (T-069: K) |
| `content/characters/**`, `tests/data/**`, `tests/regression/**`, baselines, published versions | Regression inputs / frozen |

## 4. `apps/export-obj` (owner decision 5) — steps for later (after T-060 releases root `CMakeLists.txt`)

1. `git mv apps/export-obj archive/engine_era/apps/export-obj`.
2. Remove `add_subdirectory(apps/export-obj)` from root `CMakeLists.txt` (line ~27) and any `install`/target refs
   (`git grep -n "export-obj\|plush-export-obj"`: CMake, `.github/**`, `tools/**`, `vcpkg.json`).
3. Move `docs/BLENDER_COMPARISON_HARNESS.md` to `docs/archive/` (T-071's area) or mark it historical; it references
   `plush-export-obj`, `plush_views.py` and `compare_it4_boy` (all archived by then).
4. Gate: C++ build + CTest (fast/full), link check.

## 5. Stale text references for the doc owner (no broken links; text only)

`docs/ACTIONS_AND_DIRECTOR.md:6` (watertable_v4 example), `docs/BLENDER_COMPARISON_HARNESS.md:14,46,50`,
`docs/CHARACTER_PRODUCTION_PIPELINE.md:57,62`, `docs/evaluation/hair_experiments/HAIR_EXPERIMENTS.md:10,138`,
`docs/second_character/M2_GENERIC_BODY_RIG.md:68`, `docs/second_character/M3_FACE_SYSTEM.md:51`, and the root status
docs T-071 is archiving. Each could get "(archived in T-072, see `archive/…`)".

## 6. Tests

`python3 tools/check_all.py --base origin/main --task T-072 --full --blender <bpy 5.3.0 wrapper>` (local, OIDN 2.3.3
prebuilt). First run on `501a69d`; re-run after `git merge origin/staging` (T-044 et al.) on the final commit:

```
PASS Frozen assets
PASS Guarded paths
PASS Write-set: T-072: 68 changed path(s) vs origin/staging, all inside the claim
PASS Shared-systems lint
PASS C++ build
PASS C++ tests                (CTest 4/4 incl. the 3 image regressions; doctest 33591/33591 assertions)
PASS Python tests and links
PASS Blender tier: full tier; regression boy_yellow_hoodie PASS (fidelity 64.06), girl_auburn_bun_glasses PASS (fidelity 65.42), girl_white_hair_blue_dress PASS
```

No guarded path was changed, so no trailer is needed. Blender: bpy 5.3.0 module via `tools/bpy_blender.py`, not a
Blender binary. Also: `test_versions.py` 71/71; `make_t014_shot.py` old vs new output identical; `t010_sheets.py`
resolves the same repository root.
