# T-071: documentation cleanup from the T-069 audit + the tests the gate does not run

Branch `t-071-claude-docs-cleanup` from `origin/staging` (merged with `origin/staging` before READY). Source:
[T-069 audit](../T-069/README.md) §2, §3, §6 C1–C3, C9 and the docs parts of C5/C6. Task:
[docs/tasks/T-071.md](../../../tasks/T-071.md).

## 1. Result

**Complete**, with items kept on purpose where a reference forbids moving them (§3.3). No code behaviour change.
Only files inside the T-071 claim ([OWNERSHIP.md](../../../process/OWNERSHIP.md)) changed. The gate's Write-set
check confirms this: 35 paths, all inside the claim.

- Removed 3 root files and added 2 `.gitignore` entries.
- Archived 6 root status docs and 5 engine-era reports plus 2 render folders with `git mv`, into
  [docs/archive/](../../../archive/README.md) with an index per folder. `git log --follow` keeps the history.
- `CURRENT_STATUS.md` and `NEXT_TASK.md` are now pointers to the authoritative sources.
- Fixed the README (Blender line, architecture) and the versions doc (export/5, hair_clumps/2).
- Updated the Implementer reading list.
- `tools/lipsync/test_lipsync.py` now runs its 9 tests when started directly (before: 0 tests, exit 0).
- The 14 Python test files that nothing runs were each run here. 11 pass. 3 show pre-existing problems (§4).
- Wiring diff for `tools/check_all.py`: [check_all_wiring.diff](check_all_wiring.diff) (§5). The Supervisor applies
  it after T-061.

## 2. Evidence method

For every item:

- `git grep -n -F <name>` over the whole repository, excluding `docs/tasks/`, `OWNERSHIP.md` and the T-069 report.
- Code, CI and tool references were checked separately:
  `git grep -n -E "<names>" -- ':!*.md'`.
- `tools/frozen_manifest.txt`, `tools/guarded_paths.txt`, `tools/regression_paths.txt` and
  `tools/shared_character_allowlist.txt` were checked for each path.
- The running tasks' prompts (`docs/tasks/T-044|T-060|T-061|T-064|T-065.md`) were checked: none of them mention any
  moved item.
- `python3 tools/check_doc_links.py` was run after every step: exit 0 each time.

Every inbound mention found is plain text (back-ticked), not a Markdown link. That is why the link check stays green.

## 3. Documentation changes

### 3.1 Removed (obsolete and redundant, nothing reads them)

| Item | Evidence |
| --- | --- |
| `pip.log` (pip upgrade notice from a session venv) | No code, CI or tool reference. Only mentioned by the task files and the claim. |
| `oidn.log` (`OIDN_DONE`) | Same as above. |
| `imgui.ini` (Dear ImGui window layout) | Written by `plush-studio` into its working directory and recreated when missing. No code reads the tracked copy. One text mention in [T-001 report](../../../milestones/2026-11-15_T-001_studio_shot_pipeline.md) ("the tracked copy is unchanged by tests"): historical. C++ tests (incl. the Studio workflow test) PASS in the gate. |
| `.gitignore` | Added `*.log` and `imgui.ini`. No tracked `*.log` exists (`git ls-files '*.log'` is empty). |

No other document was deleted. Everything else was archived or kept.

### 3.2 Archived (`git mv`, index README per folder)

[docs/archive/root_status/](../../../archive/root_status/README.md). Superseded by
[TASK_LOG](../../../process/TASK_LOG.md), [ROADMAP](../../../ROADMAP.md) and
[DELIVERY_PLAN](../../../process/DELIVERY_PLAN.md). All of these stopped at T-010 / iteration 4 on 2026-11-15.

| Original | Inbound mentions (all plain text) |
| --- | --- |
| `CURRENT_STATUS.md` → `CURRENT_STATUS_2026-11-15.md` | `IMPLEMENTER_PROMPT.md` reading list (updated) |
| `NEXT_TASK.md` → `NEXT_TASK_2026-11-15.md` | `IMPLEMENTER_PROMPT.md` (updated) |
| `PROJECT_STATE.md` | `NEXT_STEPS.md` (archived together) |
| `NEXT_STEPS.md` | `PROJECT_STATE.md` (archived), `docs/CHARACTER_PRODUCTION_PIPELINE.md:164` ⚠ |
| `FEATURE_STATUS.md` | `PROJECT_STATE.md` (archived), `docs/PROJECT_STATUS_AND_ARCHITECTURE_AUDIT.md:6` ⚠ |
| `BUGS_AND_ISSUES.md` | archived docs, `DEVELOPMENT_LOG.md:37`, `docs/BOY_BLENDER_PIPELINE_ANALYSIS.md:309` ⚠ |

[docs/archive/engine_era/](../../../archive/engine_era/README.md). Superseded by the Blender production path
(TD-37..TD-42). These are iterations 1–4, the SDF characters in the engine.

| Original | Inbound mentions (all plain text) |
| --- | --- |
| `docs/ITERATION_03_ACCEPTANCE_REPORT.md` | `PROJECT_STATE.md` (archived) |
| `docs/ITERATION_03_REFERENCE_GAP_ANALYSIS.md` | `PROJECT_STATE.md` (archived), `DEVELOPMENT_LOG.md:67` |
| `docs/ITERATION_04_ACCEPTANCE_REPORT.md` | `PROJECT_STATE.md` (archived), `docs/BOY_BLENDER_PIPELINE_ANALYSIS.md:45` ⚠ |
| `docs/ITERATION_04_PHASE_A_ANALYSIS.md` | archived docs only |
| `docs/SCALABILITY_ASSESSMENT.md` | `PROJECT_STATE.md` (archived) |
| `docs/milestone01/` (5 files, 3.7 MB) | `PROJECT_STATE.md` (archived) only; not in the frozen manifest; no code reference (the CTest scene `content/scenes/milestone01_classroom.scene.json` is a different path and stays) |
| `docs/milestone02/` (5 files, 4.5 MB) | `SCALABILITY_ASSESSMENT.md` (archived) only |

⚠ = a plain-text mention in a doc **outside the T-071 claim**, so I could not edit it. The old path no longer exists,
but the archive index lists every original path. Suggested one-line fixes for the Supervisor or the next doc task:

- `docs/CHARACTER_PRODUCTION_PIPELINE.md:164`: "See `NEXT_STEPS.md`" → `docs/ROADMAP.md`.
- `docs/BOY_BLENDER_PIPELINE_ANALYSIS.md:45,309`: prefix the paths with `docs/archive/engine_era/` and
  `docs/archive/root_status/`.
- `docs/PROJECT_STATUS_AND_ARCHITECTURE_AUDIT.md:6`: `docs/archive/root_status/FEATURE_STATUS.md`.

### 3.3 Kept on purpose (proposed by T-069, but a reference forbids the move or the evidence is not conclusive)

| Item | Why it stays |
| --- | --- |
| `DEVELOPMENT_LOG.md` | `tests/CMakeLists.txt:15` (guarded, T-061's file) cites it for re-baselining the image regressions. Added a 3-line header saying it is historical and where later work is logged. |
| `docs/milestone03/`, `docs/iteration4/` | Output folders of `tools/make_it4_comparison.py` (lines 7, 60, 66), which is a tool reference. They move with the engine-era generators (T-069 C5, code, full tier). |
| `docs/CHARACTER_PIPELINE_REVIEW.md` | 0 inbound links, but it is an open Supervisor checklist ("completed when the owner provides the third character's reference package"). That package now exists (`girl_white_hair_blue_dress/references`), so the checklist may be due. Supervisor or owner decide. |
| `docs/PROJECT_STATUS_AND_ARCHITECTURE_AUDIT.md` | Not in the claim, and on the Implementer reading list (T-069 marks it **O**) |
| `docs/BLENDER_COMPARISON_HARNESS.md` and other docs | Not in the claim. They describe tools that still exist. |

### 3.4 Consolidated (one authoritative version)

- **`CURRENT_STATUS.md`, `NEXT_TASK.md`** (root): short pointer tables to `docs/process/TASK_LOG.md`, `OWNERSHIP.md`,
  `docs/ROADMAP.md`, `DELIVERY_PLAN.md`, `GATE.md`, the decision logs and the architecture docs. They contain no
  status of their own. The old text is archived (§3.2).
- **`README.md`**:
  - Removed "No Blender, no cloud, no GPU required". It contradicted TD-37..42.
  - Added a short description of the three parts (Studio / Blender backend / C++ engine) and the production path,
    with links to `PRODUCTION_PIPELINE.md`, `CHARACTER_REUSABILITY.md`, `CHARACTER_SYSTEM_VERSIONS.md` and `GATE.md`
    instead of repeating them.
  - Added the requirements as they are: C++ build CPU only; Blender 5.3 or bpy for character builds, final renders
    and the full tier.
  - Extended the box table with `pipeline/`, `assets/characters/`, `episodes/` and `tools/`.
  - The build and run sections are unchanged.
- **`docs/CHARACTER_SYSTEM_VERSIONS.md`**:
  - Exporter row: `export/1-3 (retired), export/4, export/5 (T-056)`.
  - New paragraph, matching the code:
    - `LEGACY_EXPORTER = "export/4"` is the default of unpinned specs (both current characters).
    - `EXPORTER_VERSION = "4"` is the run_shot cache key.
    - `EXPORTER_DEFAULT = "5"` applies to masters without an embedded spec.
    - Link to the T-056 evidence.
  - Groom row: `hair_clumps/2 (experiments only: no character pins it; used by the boy's hair experiments
    H20–H35, incl. the frozen H28 candidate)`.
  - Checked with `git grep '"generator": *"hair_clumps/2"' -- assets`: 16 experiment overrides, H20–H35. T-069 said
    H20–H25, which undercounts. **Correction for T-069 owner decision 4:** retiring `hair_clumps/2` would also
    disable rebuilding the frozen H28 candidate, which still awaits the owner. No spec or `fidelity_baseline.json`
    entry pins it.
- **`docs/process/IMPLEMENTER_PROMPT.md`** (reference lines only):
  - The reading list now names `docs/process/TASK_LOG.md` and `docs/ROADMAP.md`, and notes that the root files only
    point there.
  - "usually CURRENT_STATUS.md, NEXT_TASK.md" in the documentation rule became "usually a dated milestone or task
    report; TASK_LOG.md and ROADMAP.md are the Supervisor's". Otherwise Implementers would keep writing status into
    the pointer files.
  - **The Supervisor should confirm this wording.**
- No other duplicated process or architecture text was found inside the claim.
- `TECHNICAL_DECISIONS.md` is excluded by the task.
- The process docs outside the claim (`WORKFLOW.md`, `GATE.md`, `DELIVERY_PLAN.md`) each cover a separate subject.

### 3.5 Docs parts of C5/C6

The engine-era archive README warns: **do not run** the generators still in `tools/` (`charkit.py`, `make_*.py`,
`render_iteration*_evidence.sh`), because they overwrite CTest regression inputs. Moving those scripts (C5) and the
clip evidence scripts (C6) is code under `tools/` and `pipeline/`, which is outside the claim and full tier. Not done.

### 3.6 Scope addition: architecture docs (owner decision 2026-11-17, Supervisor message)

Source: [OWNER_DECISIONS.md](../../../process/OWNER_DECISIONS.md), "architecture: renderer freeze, CPU render
optimisation, docs, approved-asset preservation" (staging `7c32158`, merged), item 3 ("docs go with T-071").

- `README.md`: the introduction now describes the pipeline as it is:
  1. spec JSON → shared Blender generators;
  2. the engine owns animation and writes `plush.shot_bake/1`;
  3. Cycles renders the final shots;
  4. Python tools (`run_shot`, fidelity, regression, gate).

  Studio and `plush-render` are described as previews and existing tests only, with the renderer frozen. Build and
  run instructions are unchanged.
- `TECHNICAL_DECISIONS.md`: new **TD-43** "Engine renderer frozen; approved versions immutable (2026-11-17)". It says:
  - the engine renderer serves previews and existing image tests only;
  - look, material and render work happens only in Blender;
  - `engine/render/` is guarded;
  - approved versions are stored immutably in the asset store (T-075, in progress);
  - CPU render profiles come from T-074.

  Only this section was appended. TD-1..TD-42 are unchanged.
- `docs/process/IMPLEMENTER_PROMPT.md`: one new rule under "Architecture rules":
  - no new features in `engine/render/`;
  - look and render changes go to the Blender pipeline;
  - never write into `assets/characters/*/versions/`.

## 4. The tests the gate does not run

Reconciling T-069's "18": the gate runs 4 Python scripts and `tools/cleanup/run_tests.py`, and in the Blender tier
`face_test`, `hair_generic_test`, `groom_generic_test`, `garment_generic_test`, `test_material_presets`,
`test_determinism` and `test_export_engine`. `verify_charsys` adds `test_store` and `reuse_test`. Of the 32 tracked
`test_*.py` and `*_test.py` files:

- **14 test files run nowhere.** These are the table below.
- **4 are `tools/cleanup/tests/test_*.py`.** They do run, through `run_tests.py` (25 tests, 0 failures here; also in
  `cleanup.yml`). 14 + 4 = T-069's 18.
- **`tools/make_face_test.py` is not a test.** It is an engine-era scene generator that matches the `*_test.py`
  pattern.

Environment:

- Blender **bpy 5.3.0 module** (Python 3.13, wheel as pinned in `.github/ci-dependencies.json`), through
  `tools/bpy_blender.py`. **Not** an official Blender binary.
- C++ build with OIDN 2.3.3 prebuilt (sha256 checked) and Ubuntu 24.04 apt packages from `ci-dependencies.json`.
- 4-core cloud container.
- Times are wall-clock for one run.

| # | Test | Covers | Needs | Result here | Time | Proposed tier |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `pipeline/charsys/tests/test_versions.py` | T-043 version registry, pins, legacy defaults, spec parts | Python | **72/72 PASS** | 0.2 s | **fast** |
| 2 | `tools/fidelity/tests/test_metrics.py` | fidelity metrics (IoU, CIEDE2000, alignment…) | numpy, Pillow | **35/35 PASS** | 0.3 s | **fast** |
| 3 | `tools/lipsync/test_lipsync.py` | T-054a lip-sync extract/validate | Python | before the fix: **0 tests, exit 0**. After: **9/9 OK** (also from another cwd; `unittest discover` 9/9) | 0.3 s | **fast** |
| 4 | `pipeline/charsys/tests/test_boy2_face.py` | T-058 boy 2.0.0-dev face controls | spec part: Python. Build part: Blender + boy 2.0.0-dev master | no Blender: **3/3 PASS**. With Blender: **11/11 PASS** | 0.0 s / 2 s (+55 s shared build) | spec part **fast**; Blender part **full** |
| 5 | `pipeline/charsys/tests/test_hoodie.py` | T-058 shared hoodie garment (garment/1) | Blender + boy 2.0.0-dev master | **28/28 PASS** (without Blender it exits 2, so not usable in fast) | 2 s (+ shared build) | **full** |
| 6 | `pipeline/charsys/tests/test_render_engine.py` | T-020 render engine selector | Blender | **ALL PASS** | < 1 s | **full** |
| 7 | `pipeline/charsys/tests/groom_dynamics_test.py` | T-021 groom/1 dynamics chains (synthetic head) | Blender | **19/19 PASS**, json `pass: true` | 1 s | **full** |
| 8 | `pipeline/charsys/tests/test_export_determinism.py` (quick mode) | T-056 export/5 byte-reproducible, order-stable | Blender | **15/15 PASS** | 4 s | **full** |
| 9 | `pipeline/production/tests/test_clip_pipeline.py` | T-002 retarget block in every repo shot package, exporter-versioned cache | Blender, prepares every repository shot | **ALL PASS** (46 checks) | cold **> 590 s** (timed out once while still passing), 217 s second run, 6 s fully warm | **nightly** (too slow cold for the gate) |
| 10 | `pipeline/production/tests/test_run_shot_workflow.py` | T-001 run_shot contract: idempotent prepare, status, cancel, failure, CLI default | Blender, every shot | **ALL PASS** (84 checks) | cold **> 590 s** (timed out once while still passing), 220 s warm | **nightly** |
| 11 | `pipeline/charsys/tests/test_shot_eyes.py` | T-030 eye-socket alignment over a rendered shot (e905) | Blender, run_shot, shot_render | **FAIL 8/9**: `girl: baked bones reproduced 0.829 mm` (limit < 0.01 mm). Boy 0.0008 mm. The eye checks pass for both (boy 0.078 mm, girl 0.0006 mm). | 254 s | **nightly**, after the failure is understood |
| 12 | `pipeline/clips/test_emotions.py` | T-003 emotion AC2–AC6 on engine bakes | `plush-render` + prepared e901 packages; `--out` **must be inside the repository** (the engine looks for `content/clips` above the scene; with an `--out` in /tmp every bake fails "clip 'idle_relaxed' not found") | **FAIL**: AC2, AC3, AC4, AC6 PASS. AC5 FAIL: `boy_reach_keeps_hand` max hand drift 0.056 m during emotion + walk + reach. The other AC5 items pass. | 37 s (+ e901 prepare) | **nightly**, after the AC5 failure is understood (likely relevant to T-061, which owns `engine/scene/actions.cpp` / `clip_layers.cpp`) |
| 13 | `pipeline/charsys/tests/face_system_test.py` | face_generic/1 measurements (eye visibility, mouth, glasses overlaps…) | Blender + face_generic master | runs, exit 0 on the current girl (spec + 0.10.0 override). It is a **measurement script with no pass/fail limits**. | 59 s (`--no-render`) + 84 s girl build | **local** (evidence tool), or full tier once it has limits |
| 14 | `pipeline/charsys/tests/deform_test.py` | joint deformation stretch/compression per pose (measurement, no limits) | Blender + rigged master | boy 1.0.0 published master: runs (7 s). **Crashes** on the current girl and on boy 2.0.0-dev: `IndexError` (§4.1). | 7–8 s | **local** after the fix |

Commands, from the repository root (`B` = the blender wrapper):

```
python3 <test 1|2|3|4>
python3 pipeline/charsys/tests/test_boy2_face.py --blender $B --master <boy 2.0.0-dev master>
python3 pipeline/charsys/tests/test_hoodie.py    --blender $B --master <boy 2.0.0-dev master>
$B -b --factory-startup -P pipeline/charsys/tests/test_render_engine.py
$B -b --factory-startup -P pipeline/charsys/tests/groom_dynamics_test.py -- <out.json>
python3 pipeline/charsys/tests/test_export_determinism.py --blender $B --out <dir>
python3 pipeline/production/tests/test_clip_pipeline.py --blender $B --out <dir>
python3 pipeline/production/tests/test_run_shot_workflow.py --blender $B --out <dir>
python3 pipeline/charsys/tests/test_shot_eyes.py --blender $B
python3 pipeline/clips/test_emotions.py --boy <e901 boy pkg> --girl <e901 girl pkg> --out build/t071_emo
$B -b --factory-startup -P pipeline/charsys/tests/face_system_test.py -- <girl master> <out> --no-render
$B -b --factory-startup -P pipeline/charsys/tests/deform_test.py -- <master> <out>
```

Masters used:

- boy 2.0.0-dev: `build_character.py --spec boy_yellow_hoodie.2.0.0-dev.spec.json --no-glb --no-compare` (55 s).
- Current girl: spec + `girl_auburn_bun_glasses.0.10.0.override.json`, from `fidelity_baseline.json` (84 s).
- Boy 1.0.0: the published master.

These follow the current-versions rule. Boy 1.0.0 was used for deform only, as a second configuration.

### 4.1 Findings for the Supervisor (pre-existing; not fixed: outside the claim, and the tests are guarded)

1. **`deform_test.py` crashes on every generic-body master.**
   - Cause: it takes edge indices from the original mesh (`o.data.edges`) but positions from the evaluated mesh. The
     generic body's `body_skin` has a `MASK` modifier after the armature (girl: 62 310 → 39 169 vertices), so the
     indices run out of range.
   - `face_test.py:35` already handles `MASK` "as face_system_test.py".
   - Suggested fix: measure on an evaluated mesh with the `MASK` modifiers disabled, or take the edges from the
     evaluated mesh.
   - Its guard `len(P1) != len(P0)` compares two evaluated meshes, so it never catches this.
2. **`test_shot_eyes.py`**: the girl's baked bones are reproduced to 0.829 mm on e905 (limit 0.01 mm). Not
   investigated further. This branch changes no code, so the failure exists on `staging` as well.
3. **`test_emotions.py` AC5**: `boy_reach_keeps_hand` drifts 56 mm when an emotion is layered on walk + reach. It
   is pre-existing, and probably in the area T-061 is changing.
4. **`test_emotions.py` needs `--out` inside the repository.** Its docstring does not say so.

None of these tests was weakened, changed or deleted, except the `unittest.main()` addition.

## 5. Gate wiring diff (for the Supervisor after T-061 merges; `tools/check_all.py` is T-061's)

[check_all_wiring.diff](check_all_wiring.diff), against `tools/check_all.py` at `origin/staging` (`e007f48`).

- **Fast tier** (`check_python_tests`): adds `test_versions.py`, `test_metrics.py`, `test_lipsync.py` (needs this
  branch's `unittest.main()`) and `test_boy2_face.py` (spec checks without Blender). About 1 s in total.
- **Blender tier**: adds `test_render_engine`, `groom_dynamics_test` (json `pass`) and `test_export_determinism`
  (quick). It also adds one boy 2.0.0-dev build shared by `test_boy2_face` and `test_hoodie`. About 64 s in total.
- **Not wired** (nightly or local): `test_clip_pipeline`, `test_run_shot_workflow` (cold > 10 min each),
  `test_shot_eyes`, `test_emotions` (they fail today, §4.1), `face_system_test`, `deform_test` (measurement only;
  deform crashes).

Validation of the diff: applied locally, run, then reverted (`git checkout tools/check_all.py`; not committed):

- `py_compile` OK.
- `check_python_tests()`: PASS, 5.9 s, all 9 scripts.
- The new Blender block, run on its own with the exact code from the diff: 5/5 subchecks PASS
  (`render engine selector`, `groom dynamics`, `export determinism`, `test_boy2_face`, `test_hoodie`), 64 s.

```diff
--- a/tools/check_all.py
+++ b/tools/check_all.py
@@ -463,6 +463,10 @@
         [sys.executable, str(ROOT / "tools/fidelity/tests/test_ci.py")],
         [sys.executable, str(ROOT / "tools/regression/tests/test_gate_tools.py")],
         [sys.executable, str(ROOT / "pipeline/production/tests/test_run_shot_current.py")],  # T-062 cast check
+        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_versions.py")],  # T-043 version registry (T-071)
+        [sys.executable, str(ROOT / "tools/fidelity/tests/test_metrics.py")],  # fidelity metric functions (T-071)
+        [sys.executable, str(ROOT / "tools/lipsync/test_lipsync.py")],  # T-054a lip sync (T-071)
+        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_boy2_face.py")],  # T-058 spec checks, no Blender (T-071)
     ]
     cleanup_tests = ROOT / "tools/cleanup/run_tests.py"  # T-048 branch-cleanup tests, once merged
     if cleanup_tests.is_file():
@@ -748,6 +752,38 @@
         material_code, _ = run_logged([sys.executable, str(material_script)], material_log)
         add_subcheck(subchecks, "material presets", material_code == 0, "" if material_code == 0 else "material preset tests failed", material_log)
 
+    # T-071: self-contained Blender tests that ran nowhere before (each a few seconds, plus about a minute for the
+    # shared boy 2.0.0-dev build). Slow shot-level tests stay in the nightly/local list (T-071 report).
+    for name, command, json_out in (
+        ("render engine selector", [executable, "-b", "--factory-startup", "-P",
+                                    str(ROOT / "pipeline/charsys/tests/test_render_engine.py")], None),
+        ("groom dynamics", [executable, "-b", "--factory-startup", "-P",
+                            str(ROOT / "pipeline/charsys/tests/groom_dynamics_test.py"), "--",
+                            str(out / "groom_dynamics_test.json")], out / "groom_dynamics_test.json"),
+        ("export determinism", [sys.executable, str(ROOT / "pipeline/charsys/tests/test_export_determinism.py"),
+                                "--blender", executable, "--out", str(out / "export-determinism")], None),
+    ):
+        log = logs / f"blender-{name.replace(' ', '-')}.log"
+        code, _ = run_logged(command, log)
+        ok = code == 0 and (json_out is None or json_pass(json_out))
+        add_subcheck(subchecks, name, ok, "" if ok else f"{name} failed", log)
+
+    boy2_log = logs / "blender-boy2.log"
+    boy2_out = out / "boy2"
+    boy2_code, _ = run_logged([
+        executable, "-b", "--factory-startup", "-P", str(ROOT / "pipeline/charsys/build_character.py"), "--",
+        "--spec", str(ROOT / "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json"),
+        "--out", str(boy2_out), "--no-glb", "--no-compare",
+    ], boy2_log)
+    boy2_master = boy2_out / "boy_yellow_hoodie_master.blend"
+    for script in ("test_boy2_face.py", "test_hoodie.py"):
+        if boy2_code == 0 and boy2_master.is_file():
+            code, _ = run_logged([sys.executable, str(ROOT / "pipeline/charsys/tests" / script), "--blender", executable,
+                                  "--master", str(boy2_master)], boy2_log, append=True)
+        else:
+            code = 1
+        add_subcheck(subchecks, script[:-3], code == 0, "" if code == 0 else f"{script} failed", boy2_log)
+
     regression_details: list[str] = []
     if full:
         # The full regression measures fidelity for every character, so the affected-character run is not repeated.
```

A GATE.md §1 table update ("Python unit tests" → the explicit list) belongs with this diff. GATE.md is outside the
T-071 claim.

## 6. Gate, baselines, safety

Local gate on the merged branch (`c7f18dc`, `origin/staging` merged). The command was:

```
python3 tools/check_all.py --base origin/main --task T-071 --blender <bpy 5.3 wrapper> --regression-results <dir>
```

The regression results came from `tools/regression/run.py --character <id> --base origin/main --against origin/main`,
run once per character on this machine, as the CI per-character jobs do. Total time: 804 s for the gate, plus about
14 min for the three regression runs.

```
PASS Frozen assets
FAIL Guarded paths: REQUIRES SUPERVISOR APPROVAL: tools/lipsync/test_lipsync.py
PASS Write-set: T-071: 38 changed path(s) vs origin/staging, all inside the claim
PASS Shared-systems lint
PASS C++ build
PASS C++ tests
PASS Python tests and links
PASS Blender tier: full tier; regression boy_yellow_hoodie PASS (fidelity 64.08), girl_auburn_bun_glasses PASS (fidelity 65.37), girl_white_hair_blue_dress PASS
```

- **Every character is unchanged**: identical to `main` built on this machine.
- **The only FAIL is the expected guarded path.**
- Blender was the bpy 5.3.0 module, not an official binary.
- The regression and gate runs exceed the 10-minute foreground limit of this session's tool, so they ran as single
  background commands. Their results were waited for before READY.

- **GitHub run on `ede6863` (FAIL "Python tests: test_gate_tools.py")**: the cause is not in this branch.
  - CI trial-merged onto `origin/staging` = `3c718ed`, where `docs/process/OWNERSHIP.md` was emptied by mistake.
    `test_gate_tools.py` then fails exactly one check: "OWNERSHIP.md parses".
  - Reproduced: `ede6863` + `3c718ed`, no commit, gives `FAIL OWNERSHIP.md parses`, 1 failure.
  - Staging `3687e2b` restored the file. With it merged (branch `3f2d87e` and later), the test passes: 0 failures,
    locally and in a clean worktree with `CHECK_ALL_BASE_REF=origin/staging`.
  - The test was not edited.
- **Guarded paths that need a Supervisor trailer:**
  - `tools/lipsync/test_lipsync.py` (`**/test_*.py`): `Supervisor-Approved: tools/lipsync/test_lipsync.py`.
  - `.gitignore` is **not** guarded (not in `tools/guarded_paths.txt`), so it needs no trailer.
- **Frozen**: Frozen assets PASS. No file in `tools/frozen_manifest.txt` or its scopes was touched. `tests/data`,
  `tests/regression`, `content/**`, `assets/**` and the regression baselines are unchanged (`git diff --stat
  origin/staging...HEAD` lists only the files in §3).
- **Tier**: the deleted root files (`pip.log`, `oidn.log`, `imgui.ini`) are unknown paths in
  `tools/regression_paths.txt`. That makes the change set **full tier**, so the all-character regression ran (§6).
  A later rule could list root `*.log` / `imgui.ini` as fast. `regression_paths.txt` is T-061's and guarded.
- **No code behaviour change.** The only non-doc change is `unittest.main()` at the end of `test_lipsync.py`, under
  `if __name__ == "__main__"`.

## 7. Files changed

- Removed: `pip.log`, `oidn.log`, `imgui.ini`.
- `.gitignore`: `*.log`, `imgui.ini`.
- `tools/lipsync/test_lipsync.py`: `unittest.main()` (guarded).
- Docs:
  - `CURRENT_STATUS.md`, `NEXT_TASK.md`: pointers.
  - `README.md`: architecture and requirements.
  - `DEVELOPMENT_LOG.md`: historical header.
  - `docs/CHARACTER_SYSTEM_VERSIONS.md`: export/5, hair_clumps/2.
  - `docs/process/IMPLEMENTER_PROMPT.md`: reading list, status-file references, renderer/versions rule (§3.6).
  - `TECHNICAL_DECISIONS.md`: TD-43 appended (§3.6).
  - `docs/archive/README.md`, `docs/archive/root_status/README.md`, `docs/archive/engine_era/README.md`: indexes.
  - Moves: §3.2.
  - This report and [check_all_wiring.diff](check_all_wiring.diff).

## 8. Open questions for the Supervisor

1. Confirm the `IMPLEMENTER_PROMPT.md` wording (§3.4). It changes where Implementers write status.
2. The four plain-text mentions outside the claim (§3.2 ⚠).
3. `CHARACTER_PIPELINE_REVIEW.md`: is the third-character check due now?
4. The three pre-existing test failures (§4.1). Who fixes `deform_test`, and should `test_shot_eyes` and the
   `test_emotions` AC5 failure go to T-061 or a new task?
5. Nightly job for tests 9–12 (owner decision 7 in T-069).

Resource use: token usage not available. Repeated work:

- `test_run_shot_workflow` and `test_clip_pipeline` were run twice, because the first cold run hit the 10-minute
  foreground limit.
- The girl's regression was started three times. The first run hit the limit. The second failed at once on the
  first run's stale git worktree (fixed with `git worktree prune`). The third ran as one background command, because
  a single character's regression takes longer than the foreground limit.
