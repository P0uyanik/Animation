# T-069: codebase audit — outdated, deprecated, unused, duplicate and legacy items (report only)

Reviewer: independent audit, read-only (only this folder was written). Branch `t-069-claude-legacy-audit` from
`origin/staging`. At audit time `origin/staging` and `origin/main` were the same commit (`c6f990e`), so this is an
audit of `main`.

## 0. Summary

- **The code is in better shape than the question suggests.** Most "legacy-looking" things are still load-bearing.
  Examples: the engine-era SDF characters in `content/characters` feed the frozen CTest image regressions and the C++
  unit tests. `body_v6.py`, `hair.py` and `face.py` are what the boy's published 1.0.0 and current 1.1.0 build with.
  `pipeline/blender/boy_pilot/**` is frozen and `verify_charsys.py` uses it. They stay.
- **Nothing should be consolidated in the shared character systems.** Every apparent duplicate
  (`body_v6`/`body_generic`, `face.py`/`face_generic`, `boy_pilot/geom.py`/`charsys/geom.py`, `hair.py`/`groom.py`,
  `boy_pilot/fingerprint.py`/`fingerprint_v2.py`) is either a frozen file or a released, pinned version
  ([CHARACTER_SYSTEM_VERSIONS.md](../../../CHARACTER_SYSTEM_VERSIONS.md): released versions are immutable). Merging
  any of them would change published or current characters.
- **What is actually stale or unneeded:**
  1. Seven root status documents (`CURRENT_STATUS.md` and others) stopped at T-010 / iteration 4 on 2026-11-15. Two
     of them are on the Implementer's mandatory reading list, so they mislead every new task. `README.md` says
     "No Blender", which contradicts the architecture.
  2. Two committed logs (`pip.log`, `oidn.log`) and a UI state file (`imgui.ini`) at the root.
  3. About 20 one-off evidence or iteration scripts with no importer and no test. Several of them **overwrite CTest
     regression inputs** if anyone runs them.
  4. 34 boy hair/face experiment overrides that are superseded by the groom/1 and T-044 path. Two of them (F09 and
     H28) are frozen and still waiting for the owner.
  5. `CHARACTER_SYSTEM_VERSIONS.md` omits `export/5`.
- **The most valuable finding is not something to delete:** 18 Python test files are **not run by the gate**. One
  of them, `tools/lipsync/test_lipsync.py`, reports success without running any test when started the documented way
  (it has no `unittest.main()`).
- **Repository weight cannot be recovered by cleanup.** The `.git` pack is 352 MiB, and the HEAD tree is 272 MB,
  151 MB of it in `docs/evaluation/`. Deleting files from HEAD shrinks a checkout but not the history, and history
  rewrites are forbidden. The removable code and data listed below add up to under 0.5 MB.

Outcome: **Remove (safe)** only the three root files (`pip.log`, `oidn.log`, `imgui.ini`). **Consolidate** three
things, all in docs or tests and none in shared code: the root status docs, the versions doc, and gate test wiring.
**Archive** six groups: engine-era generators, one-off clip scripts, boy experiments, hair_study, historical docs, and
optionally engine-era scenes. **Owner decision:** eight questions (§7). Everything else is **Keep**.

## 1. Method and evidence rules

- Inventory: `git ls-files` (1 432 tracked files). Grouped by top folder and by size (`du -b` per tracked file).
- Reference graph for every tracked `*.py|*.sh|*.cpp|*.json|*.ps1` under `pipeline/ tools/ apps/ engine/ content/
  .github/scripts/ episodes/`: `git grep -l -w -F <basename>` and, for Python, `<module stem>`. References were split
  into code/config (`*.py *.sh *.cpp *.h *.json *.yml *.txt CMakeLists *.cmake *.ps1` outside `docs/`) and docs.
  Script: `scratchpad/refs.py` (not committed; the commands are reproduced inline below).
- Python import graph: for each module `m`, `git grep -lE "(import|from) +([a-z_.]*\.)?m\b|[\"'/]m\.py"` over
  `*.py *.sh *.yml *.txt CMakeLists.txt`.
- Python dead functions: `ast` scan of top-level `def`/`class` across all tracked `.py`. A name is reported when it
  occurs only once in all tracked `.py/.json/.sh/.yml/.txt` text, which is its definition.
- C++ dead functions: names declared in `engine/**/*.h` and `apps/**/*.h`, counted with `git grep -w -c` over
  `*.cpp *.h`.
- Build, gate and CI wiring: `CMakeLists.txt`, `engine/CMakeLists.txt`, `tests/CMakeLists.txt` (CTest),
  `tools/check_all.py` (`check_python_tests`, Blender tier), `pipeline/charsys/verify_charsys.py`,
  `tools/regression/run.py`, `.github/workflows/*.yml`, `tools/cleanup/run_tests.py` (unittest discovery).
- Protection lists: `tools/frozen_manifest.txt` (blobs and scopes), `tools/guarded_paths.txt` (need a
  `Supervisor-Approved:` trailer), `tools/shared_character_allowlist.txt` (character-name lint baseline),
  `tools/regression_paths.txt` (tiers), and the running tasks' write-sets in
  [OWNERSHIP.md](../../../process/OWNERSHIP.md).
- **Unused** means no code, config, CMake, CI or gate reference. Documentation references are listed separately,
  because a script that is only documented is a manual tool, not dead code.
- **Limits.** Dynamic loading by computed path is not visible to a grep: `content/clips/<name>.clip.json` and
  `content/emotions/<name>.emotion.json` are found by name at run time
  ([engine/scene/actions.cpp](../../../../engine/scene/actions.cpp) lines 709 and 753), and
  `garments/evaluate.py:62` reads **every** clip. Those folders were checked against their loaders, not only by
  grep. Blender-only tests were not run: no Blender was needed for a report-only task.

## 2. Inventory and classification

Legend: **K** keep (required) · **R** remove (safe) · **C** consolidate · **A** archive · **O** owner decision.
Archive means `git mv` into `docs/archive/<area>/` (or the task's evidence folder) with a note. It is never a
deletion, and the history keeps everything regardless.

### 2.1 Root files

| Item | Evidence | Class |
| --- | --- | --- |
| `pip.log` (164 B: a pip upgrade notice from a session venv), `oidn.log` (10 B: `OIDN_DONE`) | Added by the T-034 merge `6c24774`. `git grep "pip\.log\|oidn\.log"`: only `docs/tasks/T-069.md`. No tool reads them. | **R** (also add `*.log` to `.gitignore`) |
| `imgui.ini` (637 B, Dear ImGui window layout) | Written by `plush-studio` into its working directory. [T-001 report](../../../milestones/2026-11-15_T-001_studio_shot_pipeline.md) §"Working directory" says the tracked copy is unchanged by tests. No code reads the tracked copy: ImGui creates it when it is missing. | **R** + `.gitignore` entry. Risk: none for tests. A user's first Studio run gets the default window layout. |
| `CURRENT_STATUS.md` (says "Latest: T-010"), `NEXT_TASK.md` (T-003 era), `NEXT_STEPS.md` ("run `reproduce_v6.py`", pre-charsys), `PROJECT_STATE.md` ("iteration 4 … iteration 5 has not been started"), `FEATURE_STATUS.md`, `BUGS_AND_ISSUES.md`, `DEVELOPMENT_LOG.md` | `git log -1`: all last changed 2026-11-15 (T-002/T-003/T-010). The live status is in `docs/process/TASK_LOG.md` and `docs/ROADMAP.md` (2026-11-17). [IMPLEMENTER_PROMPT.md](../../../process/IMPLEMENTER_PROMPT.md) still tells every Implementer to read `CURRENT_STATUS.md` and `NEXT_TASK.md` first. They describe `hair_clumps/2` as "the next step" and omit groom/1, garment/1, versions, the gate and T-04x–T-06x. | **C** (Supervisor). Either regenerate `CURRENT_STATUS.md`/`NEXT_TASK.md` from TASK_LOG/ROADMAP and archive the other five, or archive all seven and change the Implementer reading list. |
| `README.md` | Line 4: "No Blender, no cloud, no GPU required". This contradicts TD-37..42 and the Implementer prompt (Blender is the production backend). 41 inbound references, so it stays. | **K**, but fix the text (doc task) |
| `TECHNICAL_DECISIONS.md` | The decision log, referenced by the Implementer prompt | **K** |

### 2.2 Character data and versions

| Item | Evidence | Class |
| --- | --- | --- |
| `assets/characters/boy_yellow_hoodie/versions/1.0.0/**` (published, 20 MB incl. `.glb` and `.blend`) | Frozen (manifest), published, `test_store.py` and `reuse_test.py` via `verify_charsys` | **K** |
| `boy_yellow_hoodie.spec.json` + `1.1.0.override.json` | `fidelity_baseline.json` current boy, regression guard. The override is frozen. | **K** |
| `boy_yellow_hoodie.2.0.0-dev.spec.json` | `test_boy2_face.py`, `test_hoodie.py`, T-058 (unpublished Boy 2.0 work in progress) | **K** |
| `girl_auburn_bun_glasses.spec.json`, `0.10.0.override.json`, `dynamics.override.json` | Fidelity baseline (current girl), e904 shots, consolidation evidence | **K** |
| `girl_white_hair_blue_dress/references/**` (106 files) | Reference intake. GATE §3: "references only, not buildable yet". | **K** |
| `experiments/face/F09_*`, `experiments/hair/H28_*` | Frozen. "Awaiting owner review" (TASK_LOG). | **K** (frozen) / **O** (approve or reject) |
| `experiments/hair/H00–H35` except H28 (33 files, 62 KB), `experiments/face/F01–F08` (8 files, 12 KB) | Code consumer: only `pipeline/charsys/hair_experiments.py` (globs the folder) and `review_views.py` (`H00_reference`). No test, gate or CI reference. H20–H25 are the only users of `hair_clumps/2`. Superseded by groom/1 (T-033) and the approved hybrid C → `hair_v3` (T-044). | **O** → then **A**. Only once F09/H28 are decided: the H/F series documents the CP-2 history, so archive them with `hair_experiments.py`. Keep H28/F09 where they are (frozen paths). |
| `experiments/generic_tests/G01–G03` | No code reference. Docs: 1–3 (CP-2 generic face/body tests). | **A** (with the H/F series) |
| `content/characters/*.character.json` (5 SDF characters from iterations 1–4) | CTest: `regression_milestone01` → `milestone01_classroom` → `girl_white_hair_m01`; `regression_face_neutral` → `test_face` → `girl_white_hair_v2`; `regression_lineup_abc` → `test_lineup` → `boy_dark_hair`, `girl_brown_glasses`, `girl_white_hair`. `tests/test_engine.cpp:593`, `test_face_layer.cpp:32`, `test_imported_character.cpp:476` (`boy_dark_hair`); `test_body_mechanics.cpp:22`, `test_interaction.cpp:19` (`girl_white_hair`). | **K** (all five). These "old engine-era characters" are regression inputs, not unused. |
| `content/personality/*.draft.json` | No code consumer yet: a planned feature, documented in `SCHEMA.md` | **K** (planned data) |
| Boy "1.1.0 published" (as stated in the T-069 prompt) | `versions/index.json` lists **only 1.0.0** (`status: reference`, `pointers.approved: null`). 1.1.0 exists only as an override that the fidelity baseline uses as "current". `frozen_manifest.txt` has a scope `versions/1.1.0/*` that matches no files. | **O**: not a cleanup item, but the Supervisor should correct the wording ("current", not "published") or record the owner's publication decision. Do **not** delete the empty scope line: it prevents an unapproved 1.1.0 folder from appearing. |

### 2.3 Shared character systems (`pipeline/charsys`), legacy versus generic

None of these may be consolidated. The reason is in each row.

| Pair / item | Evidence | Class |
| --- | --- | --- |
| `body_v6.py` (legacy builder) vs `body_generic.py` | `body_v6.py` is frozen (manifest). Registry: `body_v6/1`, `face body_v6/1`, `garment body_v6/1`, `accessories body_v6/1`, `materials body_v6/1`, all used by the boy (CHARACTER_SYSTEM_VERSIONS table). `build_character.py` dispatches on the pin. | **K** (frozen, published) |
| `face.py` vs `face_generic.py` | `face.py` is imported by `build_character.py` and `face_generic.py`. It implements the boy's `body_v6/1` face keys. | **K** |
| `hair.py` (`hair_clumps/1`, `/2`) vs `groom.py` (`groom/1`) + `groom_felt.py` | `hair.py` is imported by `build_character.py`, `groom.py`, `hair_generic_test.py` (gate Blender tier) and `tools/fidelity/ci.py`. `hair_clumps/1` is the boy's current groom. `groom_felt.py` is imported by `groom.py`, used by groom/1 (the girl). `hair_clumps/2` is registered, with no character using it (only experiments H20–H25). | **K**. `hair_clumps/2` could be marked `RETIRED` (a status change, which the versions doc allows when no character pins it), but **O**: retiring it disables H20–H25 rebuilds, so do it together with the experiment archive. |
| `pipeline/blender/boy_pilot/geom.py` (466 lines) vs `pipeline/charsys/geom.py` (510 lines) | 56 differing lines: charsys is a superset fork. The boy_pilot copy is frozen and used by `build_boy_pilot.py` / `reproduce_v6.py` (frozen v6 reproduction). | **K** (intentional fork, frozen) |
| `boy_pilot/fingerprint.py` vs `charsys/fingerprint_v2.py` | Format 1 is used by `verify_charsys.py:80` against the frozen v6 baseline. Format 2 is used by `check_all.py`, `regression/run.py` and the determinism tests. | **K** (two formats, both used) |
| `boy_pilot/preview.py` vs `experiments/hair_study/preview.py` | Different purpose (pilot close-ups vs T-049 cheap head previews). The first is frozen. | **K** / see hair_study below |
| `pipeline/charsys/experiments/hair_study/**` (T-049, 113 KB) | Imported only inside the folder (`primitives.py` imports `groom`, `groom_felt`). `docs/tasks/T-044.md` lists it as running-task input ("T-049 report + prototypes"). | **K now**, **A after T-044 is in main** |
| `hair_experiments.py`, `review_views.py` (CP-2 orchestrators) | No importer. `hair_experiments.py` imports `compare_harness`, `compare_sheet`, `pilot_metrics`. Listed in `tools/shared_character_allowlist.txt` (guarded). Docs: `docs/evaluation/hair_experiments/`. | **A** with the H/F experiments (allowlist lines must be removed in the same change; guarded → Supervisor trailer) |
| `episode.py`, `asset_store.py`, `render_engine.py`, `render_calibration.py`, `determinism.py`, `shot_render.py`, `accessories.py`, `face_features.py`, `body_helpers.py`, `spec.py`, `versions.py`, `export_engine.py`, `garments/**`, `materials/**` | Each has importers in production code or in gate tests (import graph in §1) | **K** |
| `materials/render_swatches.py` (+ `measure_swatches.py`) | No code caller of `render_swatches`. Docs: 10 (T-015/T-019/T-026/T-028 swatch sheets). The material evaluation entry point, needed for T-066/T-067. | **K** (manual tool, upcoming tasks) |
| `pipeline/charsys/tools/*.py` | `groom_turnaround` (regression/fidelity), `garment_pose_eval`, `measure_colour`, `turnaround_sheet` (gate garment test) are used. `extract_reference_views.py`: no code, docs 2 (girl reference intake). | **K** (`extract_reference_views` is the generic reference-intake tool for the third character) |

### 2.4 Engine and apps (C++)

| Item | Evidence | Class |
| --- | --- | --- |
| All `engine/**` sources | Each `.cpp` is in `engine/CMakeLists.txt`. Headers are included. | **K** |
| `engine/model/character.*`, `sdf.*`, `engine/fuzz/**`, `engine/render/**` (engine-era SDF characters and path tracer) | Used by CTest image regressions, `plush-render`, Studio preview and unit tests. Architecture: "its path tracer is for previews and image regressions". | **K** |
| `apps/export-obj` (`plush-export-obj`) | Built by the root `CMakeLists.txt:27`. Used only by the iteration-4 Blender comparison workflow ([BLENDER_COMPARISON_HARNESS.md](../../../BLENDER_COMPARISON_HARNESS.md)). No test. | **O** (cheap to keep: about 100 lines and one target. Remove only together with the comparison-harness archive.) |
| `core::setLogLevel` (`engine/core/core.h:25`) | Declared and defined, never called (`git grep -w setLogLevel`: 2 hits, both the definition) | **K** (public API, trivial; not worth a full-tier change) |
| `SecondaryMotion::chainCount()` (`engine/anim/secondary.h:92`) | No caller | **K** (one-line accessor; `engine/anim/**` is in T-061's write-set) |

No other unused C++ functions were found (266 declared names scanned; only the two above plus `Frame::fromXZ` and
`ticksToFrame`, which have one caller each).

### 2.5 Python dead functions (no caller anywhere)

| Function | File | Class |
| --- | --- | --- |
| `mirror_pose`, `mirror_root`, `lagged`, `side_pose`, `blend_pose` | `pipeline/clips/clip_principles.py:101,105,241,320,325` | **O**: helpers from the clip-authoring library, unused by the current clip set. Removing them cannot change any output, but the file is the clip authoring library (full tier) and T-061 works on clips. Leave them until T-061 lands, then decide. |
| `lerp_pose`, `arm_pose` | `pipeline/clips/make_clips.py:80,101` | same as above |
| `_part_mat` | `pipeline/charsys/garments/hoodie.py:64` | **K**: `garment/1` is released (immutable by policy) |
| `_p` | `pipeline/charsys/body_generic.py:40` | **K**: `body_generic/1` is released, and the file is in T-065's write-set |
| `crown_locks` | `tools/charkit.py:421` | goes with the charkit archive (§2.6) |

### 2.6 Engine-era generators and comparison tools (iterations 2–4)

These scripts produced the SDF-character scenes and the iteration-3/4 evidence. **Warning:** most of them *write*
into `content/scenes` or `content/characters`, and three of those outputs are CTest regression inputs. Running them
today would silently rewrite regression inputs, so they are a hazard as well as dead weight.

| Script | Writes | Code refs | Doc refs | Class |
| --- | --- | --- | --- | --- |
| `tools/charkit.py` (770 lines) | the three iteration-3 characters | 0 | 6 | **A** |
| `tools/make_girl_v2.py` | `content/characters/girl_white_hair_v2.character.json` (input of `regression_face_neutral`) | 0 | 2 | **A** |
| `tools/make_lineup.py` | `content/scenes/test_lineup.scene.json` (**input of `regression_lineup_abc`**) | 0 | 0 | **A** |
| `tools/make_face_test.py` | `content/scenes/test_face.scene.json` (**input of `regression_face_neutral`**) | 0 | 0 | **A**. Its name matches `**/*_test.py`, so it is guarded **and** counted as a test source by `check_all.is_test_source`. Moving it needs a `Supervisor-Approved:` trailer. |
| `tools/make_milestone02.py`, `make_milestone03.py`, `make_watertable_v4.py`, `make_expression_sheet.py`, `make_it4_comparison.py` | milestone02/03, watertable_v4, test_expressions scenes, an iteration-4 sheet | 0 | 0–2 | **A** |
| `tools/render_iteration3_evidence.sh`, `render_iteration4_evidence.sh` | renders into `docs/milestone03`, `docs/iteration4` | 0 | 1 | **A** |
| `pipeline/plush_views.py`, `pipeline/triptych.py` | iteration-4 comparison sheets | 0 | 1 | **A** |
| `pipeline/compare_sheet.py`, `pipeline/pilot_metrics.py`, `pipeline/blender/compare_harness.py` | – | imported by the frozen `reproduce_v6.py` (and `compare_harness` by `tools/fidelity/blender_render_side.py`, `groom_turnaround`, `garment_pose_eval`) | – | **K** |
| `content/scenes/milestone02_classroom`, `milestone03_watertable`, `watertable_v4`, `compare_it4_boy`, `test_expressions_*` (3), `test_hand_poses` | no test, no gate. `milestone01`, `test_face` and `test_lineup` **are** CTest inputs and stay. | 0–1 (generators) | 1–6 | **O**: archive or keep as engine-renderer demo scenes. `content/**` is full tier. Studio opens `milestone01` by default (`apps/studio/main.cpp:1531`), not these. |

Archive these together (one task) with a README in `docs/archive/engine_era/` that says "do not run: these
overwrite regression inputs". Size: about 120 KB, negligible.

### 2.7 Clip pipeline and one-off task evidence scripts

| Item | Evidence | Class |
| --- | --- | --- |
| `content/clips/*.clip.json` (18) incl. `dense_test` | Loaded by name (`actions.cpp:709`). `garments/evaluate.py:62` samples **every** clip as a garment test pose, so removing one changes garment evaluation. `dense_test` is used by `make_clips.py` and `measure_clips.py`. `test_clip_files.py` (gate) validates them all. | **K** |
| `content/emotions/*.emotion.json` (9) | Loaded by name (`actions.cpp:753`). `test_face_layer.cpp`, `test_emotions.py` | **K** |
| `pipeline/clips/{build_mannequin,export_clip,make_clips,make_emotion_clips,measure_blender,measure_clips,measure_shot,clip_tools,clip_principles,retarget}.py`, `mannequin.json` | The clip authoring and measurement toolchain. Entry points are run by hand (`blender -P`), and `retarget` is imported by `export_engine.py`. | **K** |
| `pipeline/clips/test_emotions.py` | Guarded test, not in the gate (§3) | **K** |
| `pipeline/clips/t010_sheets.py`, `t014_contact_sheet.py`, `t022_contact_sheet.py`, `make_t014_shot.py` | Task-specific evidence scripts (T-010/T-014/T-022). 0 code refs. `make_t014_shot.py` is in the character-name allowlist. | **A** → move to their task evidence folders (`docs/evaluation/animation/T-010/` and so on), as later tasks already do (`docs/evaluation/characters/T-058/make_spec.py`). The allowlist lines move with them (guarded). |
| `pipeline/clips/make_test_shot.py`, `make_emotion_shot.py`, `emotion_sheets.py` | Generators of the e901/e902 test shots, which `content/scenes/eval/make_eval_shots.py` and `test_emotions.py` build on | **K** |

### 2.8 Episodes and evaluation shots

| Item | Evidence | Class |
| --- | --- | --- |
| `episodes/e000_pilot`, `e900`, `e901`, `e902`, `e903`, `e905`, `e906` | Referenced by `tests/test_shot_workflow.cpp`, `test_run_shot_workflow.py`, `test_clip_pipeline.py`, `test_emotions.py`, `test_shot_eyes.py` and `content/scenes/eval/make_eval_shots.py`. GATE §1.1 exempts pre-T-062 shots. | **K** |
| `episodes/e904_secondary_motion` (2 shots) | 0 code refs, 3 doc refs (T-021 secondary-motion evidence) | **K** (pre-T-062 evidence shots are explicitly kept by GATE §1.1) |
| `content/scenes/eval/**` | Cast check (`tools/check_cast.py`, gate) | **K** |

### 2.9 Tools, gate and CI

Every file in `tools/regression`, `tools/cleanup`, `tools/fidelity`, `tools/lipsync`, `.github/**`,
`tools/check_all.py`, `check_cast.py`, `check_doc_links.py`, `integrate.py`, `backup_repository.py`, `bpy_blender.py`
and `simulate_quality_gate.py` has a caller in CI, the gate or the process docs, or is the gate itself. Class **K**.
`pipeline/blender/install_blender.sh` + `BLENDER_VERSION` (5.3.0) is the only path to an official Blender binary,
as opposed to the bpy module. It is documented for local reproduction. Class **K**.

### 2.10 Documentation

| Item | Evidence | Class |
| --- | --- | --- |
| [CHARACTER_SYSTEM_VERSIONS.md](../../../CHARACTER_SYSTEM_VERSIONS.md) | Exporter row says "export/1-3 (retired), export/4". `versions.py:134` registers **`export/5`** (T-056), and `export_engine.py:48` has `EXPORTER_DEFAULT = "5"`. The doc contradicts the code. | **C** (doc fix; follows T-056) |
| `docs/ITERATION_03_*`, `ITERATION_04_*`, `CHARACTER_PIPELINE_REVIEW.md` (0 inbound links), `SCALABILITY_ASSESSMENT.md`, `PROJECT_STATUS_AND_ARCHITECTURE_AUDIT.md` (1 inbound, but on the Implementer reading list), `docs/milestone01–03`, `docs/iteration4` (31.8 MB of images) | Historical reports from before the Supervisor/Implementer process | **A** (move to `docs/archive/`; `check_doc_links.py` will flag inbound links, so fix them in the same change). Except `PROJECT_STATUS_AND_ARCHITECTURE_AUDIT.md`: **O**, because the Implementer prompt cites it. Check whether it is current before archiving it. |
| `docs/evaluation/**` (648 files, 151 MB), incl. the 23 `.py` evidence scripts and the `.txt` logs | Task evidence behind approvals. Partly frozen (`boy_pilot/**`, `T-014`, `face_controls`, `hair_experiments`, `second_character`), partly guarded (`regression/baselines`). | **K**. Removal would not shrink `.git` anyway (§5). |
| `docs/references/**`, `assets/characters/*/references/**` | Frozen or reference intake | **K** |

### 2.11 Exact duplicate files (same blob)

There are 14 groups (`git ls-tree -r -l HEAD`, grouped by blob ID) with 1.66 MB of redundant **working-tree** bytes.
Git stores each blob once, so these cost **0 bytes** of repository size. The largest are reference uploads copied
per character (for example `girl_auburn_bun_glasses/references/uploads/ref_32.webp` =
`girl_white_hair_blue_dress/references/uploads/03_lineup_three_characters_rigged.webp` =
`docs/references/boy_pipeline/10_rig_overview_mockup_all_three.webp` (frozen)). The rest are before/after metric
JSONs shared between consecutive tasks, and the frozen `pilot_v6_*` = `cloud_v6_baseline/*` pairs. Class **K**:
per-character reference folders are self-contained by design ([REFERENCE_INTAKE.md](../../../process/REFERENCE_INTAKE.md)),
and both copies of the pilot pair are frozen.

## 3. Tests that the gate never runs (important)

[GATE.md](../../../process/GATE.md) says the gate runs "Python unit tests". In fact `check_all.check_python_tests`
runs exactly four scripts plus `tools/cleanup/run_tests.py`. Its Blender tier adds `face_test`, `hair_generic_test`,
`groom_generic_test`, `garment_generic_test`, `test_material_presets`, `test_determinism`, `test_export_engine`, and
`verify_charsys` adds `test_store` and `reuse_test`. **Not run by the gate, CI or `verify_charsys`:**

| Test | Needs Blender | Run here |
| --- | --- | --- |
| `pipeline/charsys/tests/test_versions.py` | no | **72/72 PASS**. It guards the version registry, the core of T-043, yet runs nowhere automatically. |
| `tools/fidelity/tests/test_metrics.py` | no | **35/35 PASS** |
| `tools/lipsync/test_lipsync.py` | no | `python3 tools/lipsync/test_lipsync.py` **runs 0 tests and exits 0**: the file has no `unittest.main()`. With `python3 -m unittest discover -s tools/lipsync`: 9/9 OK. TASK_LOG records "9/9 tests" for T-054a, so it was run the second way. |
| `pipeline/charsys/tests/test_boy2_face.py` | spec part no | 3/3 PASS without Blender |
| `test_hoodie.py`, `test_render_engine.py`, `test_shot_eyes.py`, `test_export_determinism.py`, `groom_dynamics_test.py`, `face_system_test.py`, `deform_test.py`, `pipeline/production/tests/test_run_shot_workflow.py`, `test_clip_pipeline.py`, `pipeline/clips/test_emotions.py` | yes | not run (no Blender needed for this report) |

(`tools/cleanup/tests/test_*.py` do run, through `run_tests.py`'s unittest discovery.)

Class **C**: add the three fast tests to `check_python_tests` (`test_versions.py`, `test_metrics.py`,
`python -m unittest discover -s tools/lipsync`), and add `if __name__ == "__main__": unittest.main()` to
`test_lipsync.py`. Decide (**O**/Supervisor) which Blender tests join the full tier or a nightly job. None of these
tests should be deleted: they are guarded and they cover released versions.

## 4. Risk notes per proposed change

| Change | What could break | What proves it safe |
| --- | --- | --- |
| Remove `pip.log`, `oidn.log`, `imgui.ini` (+ `.gitignore`) | Nothing reads them. Studio recreates `imgui.ini`. | `git grep` (no hits outside T-069), fast gate (C++ build, CTest, Studio scripted test `tests/test_shot_workflow.cpp`) |
| Status docs consolidate/archive | Implementer onboarding (reading list), doc links | `python3 tools/check_doc_links.py`, update of IMPLEMENTER_PROMPT reading list |
| Fix `CHARACTER_SYSTEM_VERSIONS.md` (export/5), `README.md` line 4 | none (docs) | link check |
| Wire fast tests into the gate | gate runtime (+ <5 s), gate becomes stricter | run `check_all.py` once. `tools/check_all.py` and `tests/**` are guarded → trailer |
| Archive engine-era generators (§2.6) | Nobody can regenerate `test_lineup` / `test_face` / milestone scenes from the old path, but the outputs themselves stay, so CTest is unaffected | CTest `regression_*` unchanged (inputs untouched), `git grep` of the moved names, link check. `make_face_test.py` is guarded. |
| Archive one-off clip evidence scripts (§2.7) | Allowlist lines become stale: the character-name lint references them by path | Update `tools/shared_character_allowlist.txt` in the same commit (guarded). Shared-systems lint PASS. |
| Archive boy H/F/G experiments + `hair_experiments.py` + `review_views.py` (after the owner decides on F09/H28) | H-series rebuilds become impossible from `main` (the history keeps them). F09/H28 stay because they are frozen. `pipeline/**` and `assets/**` are full tier. | Full tier: the all-character regression must show the boy and the girl **identical to main** (no spec or override changes). `hair_generic_test` (gate) still passes, because it uses `hair.py`, not the experiments. |
| Retire `hair_clumps/2` (status only) | Specs pinning it fail loudly, by design. No character pins it (`git grep hair_clumps/2`: experiments H20–H25 only). | `test_versions.py`, full regression |
| Archive `hair_study/` after T-044 | T-044 reads it | Wait until T-044 is in main |
| Archive historical docs (§2.10) | inbound links | link check |

Never touch: anything listed or scoped in `tools/frozen_manifest.txt`, `tests/regression/*.png` (including the
unreferenced but frozen `lineup_abc_320x240_it3.png`), `tests/data/**`, `docs/evaluation/regression/baselines/**`,
`content/characters/**`, the three CTest scenes, `assets/characters/boy_yellow_hoodie/versions/1.0.0/**`, and current
spec/override files.

## 5. Repository weight: what cleanup can and cannot do

- `.git` pack: **352 MiB**. HEAD tree: **272 MB** (`docs/evaluation` 151 MB, `assets` 40 MB, `docs/milestone0x` +
  `iteration4` 32 MB, `tests/data` 29 MB (frozen), `docs/references` 16 MB (frozen)).
- Everything classified R or A above totals **under 0.5 MB**. Archiving moves, it does not delete. Removing files
  from HEAD reduces the size of a fresh checkout only. The history and the backup bundles keep every blob, and a
  history rewrite is forbidden (Implementer rules; backups never delete tags).
- The only real lever is **future growth**: 26 evidence files in `docs/evaluation` are over 1.3 MB each, together
  58.6 MB (the largest is `T-032/*/sheets/overview.png` at 4.7 MB). **O**: an evidence-size policy for future tasks,
  such as JPEG or a long-edge cap for review sheets with PNG only for metric-bearing images. I did not measure how
  much such a policy would save. This is a process decision, not a cleanup task.

## 6. Cleanup plan (small, conflict-free tasks)

Running tasks and their write-sets ([OWNERSHIP.md](../../../process/OWNERSHIP.md)): T-044 (hair v3, presets.json),
T-060 (CI/CMake), T-061 (`engine/anim`, `engine/scene/*`, `tools/check_all.py`, `tools/regression_paths.txt`,
`content/clips/**`, `tests/CMakeLists.txt`), T-064 (fidelity tools, fidelity baseline), T-065 (`body_generic`,
`body_helpers`, `face_generic`, `face_features`, `face_library`). Each task below avoids those files or waits for them.

| # | Task | Write-set | Waits for | Tier | Size effect |
| --- | --- | --- | --- | --- | --- |
| C1 | Root hygiene: delete `pip.log`, `oidn.log`, `imgui.ini`; `.gitignore` += `*.log`, `imgui.ini` | those 4 paths | – | fast | −0.8 KB |
| C2 | Doc truth fixes: `README.md` line 4, the `CHARACTER_SYSTEM_VERSIONS.md` exporter row (export/5), the groom table note for `hair_clumps/2` | 2 docs | – | fast | 0 |
| C3 | Status docs: refresh `CURRENT_STATUS.md` + `NEXT_TASK.md` from TASK_LOG/ROADMAP. Archive `PROJECT_STATE.md`, `NEXT_STEPS.md`, `FEATURE_STATUS.md`, `BUGS_AND_ISSUES.md`, `DEVELOPMENT_LOG.md` to `docs/archive/root_status/`. Fix inbound links. Supervisor updates `IMPLEMENTER_PROMPT.md`. | root `*.md`, `docs/archive/root_status/**`, linking docs | Supervisor decision (C vs archive all) | fast | 0 |
| C4 | Gate coverage: add `test_versions.py`, `test_metrics.py`, and lipsync discovery to `check_python_tests`; add `unittest.main()` to `test_lipsync.py` | `tools/check_all.py`, `tools/lipsync/test_lipsync.py` (both guarded) | **T-061** (owns `tools/check_all.py`) | fast | 0 |
| C5 | Archive engine-era generators (§2.6) to `docs/archive/engine_era/` with a "do not run: overwrites regression inputs" README | `tools/make_*.py`, `tools/charkit.py`, `tools/render_iteration*_evidence.sh`, `pipeline/plush_views.py`, `pipeline/triptych.py`, `docs/archive/engine_era/**` | – (`make_face_test.py` needs a Supervisor trailer) | full (`pipeline/**`) | −120 KB checkout |
| C6 | Move one-off clip evidence scripts (§2.7) into their task evidence folders, with allowlist lines | `pipeline/clips/t0*_*.py`, `make_t014_shot.py`, `docs/evaluation/animation/T-0{10,14,22}/**`, `tools/shared_character_allowlist.txt` | – | full | −11 KB |
| C7 | Owner decides F09/H28 → then archive the boy H/F/G experiments + `hair_experiments.py` + `review_views.py` (allowlist), optionally retire `hair_clumps/2` | `assets/characters/boy_yellow_hoodie/experiments/{hair,face,generic_tests}/**` except F09/H28, the two scripts, `versions.py` (one status line), allowlist | owner; **T-044** (boy hair) and **T-065** (depends on `versions.py` as stable) | full | −90 KB |
| C8 | Archive `pipeline/charsys/experiments/hair_study/` | that folder | **T-044** in main | full | −113 KB |
| C9 | Archive historical docs (§2.10) and decide on the leftover engine-era scenes (§2.6 last row) | `docs/ITERATION_0*`, `docs/milestone0*`, `docs/iteration4`, `CHARACTER_PIPELINE_REVIEW.md`, `SCALABILITY_ASSESSMENT.md`, selected `content/scenes/*` | owner (scenes); C3 (links) | fast (docs) / full (scenes) | 0 repo; −32 MB checkout if moved out of the default sparse path, otherwise 0 |

C1, C2, C5 and C6 can run in parallel now: their write-sets are disjoint from each other and from all running tasks.
C3 and C9 touch the same links, so run them in sequence. C4 waits for T-061; C7 waits for the owner, T-044 and T-065;
C8 waits for T-044.

## 7. Owner decisions requested

1. Boy F09 (face) and H28 (hair) candidates: approve or reject. This unblocks C7.
2. Root status files: refresh two and archive five, or archive all seven (C3).
3. Engine-era demo scenes (`milestone02/03`, `watertable_v4`, `compare_it4_boy`, `test_expressions_*`,
   `test_hand_poses`): keep as engine demos, or archive.
4. Retire `hair_clumps/2` once its experiments are archived.
5. `apps/export-obj`: keep, or archive together with the iteration-4 comparison workflow.
6. The boy's 1.1.0 is "current", not published in the asset store: confirm the wording, or record the publication.
7. Which Blender-only tests should join the full tier or a nightly run (§3).
8. Evidence image size policy for future tasks (§5).

## 8. Honest uncertainty

- Text search cannot see calls that are built from strings at run time. I checked the known dynamic loaders (clips,
  emotions, garment test poses, experiments glob, `fidelity_baseline.json`), but a manual workflow documented only
  in someone's notes would be invisible.
- "Docs-only" tools (for example `render_swatches.py`, `extract_reference_views.py`, `install_blender.sh`) are
  manual tools, and I kept them on purpose. Their usefulness is a judgement call, not a proof.
- Blender-dependent tests were not executed, so I make no claim about whether they currently pass.
- The Python dead-function scan covers top-level definitions only. Nested helpers and methods were not scanned.

## 9. Files

- `docs/evaluation/review/T-069/README.md`: this report (the only file written).
