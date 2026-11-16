# Integration batch 1: report

**Branch:** `integration/batch1`. It already held origin/main + T-037 (T-023/T-032) + T-020 + T-021. This batch merges:
- `origin/t-030-claude-eyes-hand-fix` (T-022 + T-030);
- `origin/t-027-claude-acting-quality` (T-027).

**Setup:**
- Build: Ninja Release with OIDN 2.3.3 (official tarball) and system Embree 4.3.
- Blender: bpy 5.3.0 in a Python 3.13 venv behind a `blender` wrapper.
- Renders: `run_shot.py`, 640×360, Cycles 16 samples + OIDN.

## Summary

Everything works together on the merged branch:
- **Eyes** sit in their sockets: ≤ 0.10 mm (limit 0.5 mm).
- **Arms** stay outside the body at full IK: boy +7.13 mm, girl +5.25 mm (required ≥ 0).
- **Hair dynamics** swing and respect the head collider.
- **Auto idle** is active.
- **Cup contacts** are exact.

Two things need the Supervisor:
1. **Approval for 10 guarded files.** All of them come from the merged task branches. Gate: 8 of 9 checks PASS; Guarded paths is the only FAIL.
2. **Changed numbers against each task's own evidence.** No merge or engine defect causes them. Each was traced by a control run to one of two causes:
   - **T-027's regenerated clips.** They change the T-021 hair-swing numbers and T-030's idle-arm numbers.
   - **The exporter v4 packages (T-030's DEF-parent fix and eye pivots).** They change the T-027 e906 metrics.

## 1. Conflicts and how they were resolved

### Merge 1: `t-030-claude-eyes-hand-fix` (commit be1acec)

| File | Resolution |
|---|---|
| `pipeline/charsys/export_engine.py` | Both bumped `EXPORTER_VERSION` to "3". Both features are kept in full: T-021's `export_dynamics()` / "dynamics" block, and T-030's `sphere_fit()` + `eye_pivots()` and the DEF-parent fix (that part auto-merged). `EXPORTER_VERSION = "4"`. The version comment documents 3 (T-021), 3 (T-030, parallel) and 4 (both). |
| `pipeline/charsys/shot_render.py` | Import conflict: kept both `import render_engine` (T-020 EEVEE option) and `from materials import builder` (T-022/T-030 props). The rest auto-merged: prop rendering, eye binding/measurement, arm handling, the engine option and bake-driven bones (including DYN chain bones). |
| `tests/CMakeLists.txt` | Builds both `test_secondary.cpp` and `test_interaction.cpp`. |

Exporter v4 packages carry `dynamics` (28 chains), `retarget` and `eye_pivots`.
- The boy's eye pivot moved 5.2 mm to the ball centre, as in T-030.
- The girl needs no pivot move.
- `run_shot` re-exported everything because the version changed.

### Merge 2: `t-027-claude-acting-quality` (commit e7994ef)

| File | Resolution |
|---|---|
| `engine/scene/scene.h` | `CharacterDesc` keeps both `Json dynamics` (T-021) and `bool autoIdle` (T-027). `SceneEvaluator` keeps T-027's `hasClipLayers` (counts the auto idle layer) and T-030's `armClearanceAt` / `clearanceModel`. |
| `engine/scene/scene.cpp` | After `compileActions()`: `prepareAutoIdle()` (T-027), then creation of the T-021 spring-chain solvers. The solvers read the asset and the dynamics override, not the clip layers, so the order does not matter. The scene JSON read/write already handles both `dynamics` and `autoIdle`. |

After each merge: C++ build clean, `plush_tests` 83/83 cases (21590 → 21591 assertions).

### Follow-up fix (commit 02e9d64): shared-systems lint

T-037's lint joined the branch before T-022/T-030 did, and it flagged `pipeline/clips/make_t022_shot.py`, which names the boy/girl spec files. That script authors one shot; it is not a shared system.
- It moved to `episodes/e905_props_test/make_shot.py`. This follows the precedent of `episodes/e906_acting_test/make_old_variant.py`.
- The content is unchanged apart from the usage line (ROOT has the same depth).
- The T-022 and T-030 README commands point to the new path.
- **No allowlist entry was added.**

## 2. check_all

Command:

```
python3 tools/check_all.py --base origin/main --build-dir build/cpp --artifacts-dir build/check --blender <wrapper>
```

Full run, on HEAD e7994ef (after both merges):

```
PASS Frozen assets
FAIL Guarded paths: REQUIRES SUPERVISOR APPROVAL: pipeline/charsys/shot_render.py, ... (10 files, below)
FAIL Shared-systems lint: new character reference: pipeline/clips/make_t022_shot.py:21-23 (boy_yellow_hoodie, girl_auburn_bun_glasses)
PASS C++ build
PASS CTest
PASS plush_tests
PASS Python tests
PASS Documentation links
PASS Blender tier: boy_yellow_hoodie score 64.49 (+0.00 vs baseline 64.49); girl_auburn_bun_glasses score 63.05 (+0.00 vs baseline 63.04)
```

Re-run of the failures only, after the lint fix:
- **Shared-systems lint:** PASS.
- **Documentation links:** PASS.
- **Guarded paths:** still FAIL, as expected. It is waiting for Supervisor approval.

### Guarded files needing Supervisor approval

All 10 come from the merged task branches. I added no trailers.

| File | From |
|---|---|
| `pipeline/charsys/shot_render.py` | T-020, T-030/T-022 (+ the one-line import resolution in merge 1) |
| `pipeline/charsys/tests/groom_dynamics_test.py` | T-021 |
| `pipeline/charsys/tests/test_export_engine.py` | T-030 |
| `pipeline/charsys/tests/test_render_engine.py` | T-020 |
| `pipeline/charsys/tests/test_shot_eyes.py` | T-030 |
| `pipeline/clips/measure_clips.py` | T-027 |
| `tests/CMakeLists.txt` | T-021 + T-030 (merge 1 resolution: both test files) |
| `tests/test_interaction.cpp` | T-030/T-022 |
| `tests/test_secondary.cpp` | T-021 |
| `tests/test_shot_workflow.cpp` | T-020 |

## 3. Measurements on the merged branch

Shots:
- **Canonical shots:** `e905_props_test` s010, `e904_secondary_motion` s010/s020, `e906_acting_test` s010.
- **Variants with dynamics:** the canonical e905/e906 cast the girl from her plain spec, and T-021 dynamics are opt-in through `girl_auburn_bun_glasses.dynamics.override.json`. So hair dynamics are **not** active in the canonical e905/e906. To check the three features together, `make_dynamics_variants.py` writes e905/e906 unchanged apart from that cast override, into `<shot>/build/batch1_dynamics/` (gitignored, like `make_old_variant.py`).
- **Decision for the Supervisor:** whether the canonical shots should cast the girl with the dynamics override.

### Eyes (T-030 eye-socket measurement in `shot_render.py`, every frame)

| Shot | Boy (mm) | Girl (mm) | Limit |
|---|---|---|---|
| e905 canonical | 0.101 (f17) | 0.002 | < 0.5 |
| e905 + dynamics | 0.101 (f17) | 0.002 | < 0.5 |
| e904 s010 | – | 0.0002 | < 0.5 |
| e906 canonical | 0.039 | 0.0016 | < 0.5 |
| e906 + dynamics | 0.039 | 0.0016 | < 0.5 |

Bone reconstruction error ≤ 0.0022 mm everywhere. With dynamics, the girl has 174 baked bones (the DYN chains included).

### Arm-to-body clearance (T-030 `measure_e905.cpp`, e905)

| | Boy right arm | Girl right arm |
|---|---|---|
| Min gap at full IK | **+7.13 mm** (T-030: +7.28) | **+5.25 mm** (T-030: +5.83) |
| Min gap at any IK weight | +1.24 mm (T-030: −8.87) | −20.2 mm (T-030: −24.9) |
| Deeper than the clip arm during IK fades | 0.0 mm (T-030: 0.29) | 0.0 mm |
| Upper arm / elbow half (reported only) | −67.3 mm (T-030: −79.3) | −26.8 mm (T-030: −30.1) |
| Arms on the idle clip only, no IK (not in T-030's scope) | boy L −14.5 mm (T-030: −9.0) | girl L −35.5 mm (T-030: −31.7) |
| Scene warnings | none | none |

The variant with dynamics gives the same numbers: dynamics do not affect arms.

### T-022 contacts and prop (e905)

| Measurement | Value | T-030 |
|---|---|---|
| Boy palm → grip at grasp | 0.00008 mm | 0.00007 |
| Girl palm → grip_b at hand-over | 0.00013 mm | 0.00007 |
| Palm → socket while held | ≤ 0.00018 mm | ≤ 0.00009 |
| Prop jump at the parent switches | 0.00016 / 0.00013 mm | – |
| Cup uprightness | cos 1.0 | – |
| Max cup speed | 16.8 mm/frame | 18.0 |

Every contact stays below 0.001 mm.

### Hair dynamics (T-021; `measure_dynamics.py`)

**e904, ON vs OFF tip offset (mm):**

| Chain | Max (T-021) | Frames 1, 7, 13, 19, 25, 31, 37, 43 |
|---|---|---|
| back_curls.06 | 137.9 (124) | 8 5 9 20 19 48 78 34 |
| back_curls.07 | 141.0 (121) | 8 4 9 20 19 49 91 32 |
| side_curls.02 | 115.3 (115) | 8 5 39 31 29 107 72 24 |
| side_curls.00 | 111.1 (111) | 8 4 41 32 29 104 55 19 |
| back_curls.03 | 129.3 (102) | |
| Median of the 28 chain maxima | 82.2 (70) | |

**Collider clearance (sphere + joint radius):**
- e904 ON, head: 0.03 mm. T-021 reported 0.0: the joints touch the surface and are held there.
- e904 OFF, head: 24.67 mm (T-021: 24.7).
- e904 ON, left shoulder sphere: −0.16 mm, a solver-tolerance touch. T-021 did not report shoulders; the control run with T-021's own clips gives −0.33 mm.

**Variants with dynamics.** Chain tips move against the head:
- e905: median 44.7 mm, max 61.9 mm; head-collider clearance ≥ 18.7 mm.
- e906: median 11.8 mm, max 13.6 mm (calm head motion); head-collider clearance ≥ 14.3 mm.

### Acting and auto idle (T-027)

**e906 canonical, `measure_shot.py`:**
- Gaze PASS, both characters.
- Smoothness PASS: boy 16.02 deg/frame (T-027: 15.88), girl 19.13 (T-027: 19.09).

**Auto idle** (`measure_auto_idle.py`, the bake against an `"autoIdle": false` bake):
- Trunk skin matrices differ by up to 0.02–0.04.
- The idle hands differ by 0.38–0.59.

So the automatic idle layer is active on both characters.

**Acting-principle metrics compared with `T-027/e906_new/summary.txt`:**

| Metric | T-027 | Batch 1 |
|---|---|---|
| Boy arm.L ease | 0.86 | 0.71 |
| Boy arm.L micro | 1.05° / 3.99 mm | 1.33° / 5.10 mm |
| Boy arm.R ease | 0.58 | 0.41 |
| Boy arm.R arc | 0.265 | 0.269 |
| Boy arm.R micro | 1.04° / 3.89 mm | 1.33° / 5.01 mm |
| Boy symmetry | 0.291 | 0.293 |
| Girl arm.L arc | 0.293 | 0.169 |
| **Girl arm.R ease** | **0.66** | **1.79** |
| Girl symmetry | 0.002 | 0.014 |
| Boy gaze, max down | 4.35° | 5.9° |
| Girl gaze, max down | 2.92° | 4.39° |

Anticipation and settle flags are unchanged.

## 4. Regressions: values changed against each task's evidence

All changes were traced with control bakes on the merged engine:

| Changed values | Control | Result | Cause |
|---|---|---|---|
| **T-021** hair swing larger: max 124 → 141 mm, median 70 → 82 mm | e904 with T-021-era `idle_relaxed`/`wave` clips | Reproduces the T-021 table exactly (124/121/115/111, median 70, same back_curls.03 sequence). The T-021 exporter alone gives the batch-1 numbers. | **T-027's regenerated clips.** The head moves differently, so the hair swings more. Collision is unaffected. |
| **T-030** clearance: full-IK gaps +7.13/+5.25 (from +7.28/+5.83); idle-clip arms deeper (boy L −9.0 → −14.5, girl L −31.7 → −35.5) | e905 with T-030-era `idle_relaxed` | Reproduces the T-030 measurement file's values exactly | **T-027's regenerated `idle_relaxed`** (e905 has an explicit base clip, so auto idle does not apply there). Full-IK clearance still ≥ 0; the idle-arm rows were outside T-030's scope, but the idle arms now sit deeper in the conservative body envelope. |
| **T-027** e906 metrics (table above) | e906 packages exported with the T-027 branch's exporter (v2) | Reproduces T-027's `summary.txt` byte for byte | **Exporter v4 (T-030):** shoulders/upper arms now follow the chest, and the boy's eyes pivot at the ball centre. T-027 measured and tuned its clips on packages without that fix. Worth a look: **girl arm.R ease 0.66 → 1.79** (her right arm now speeds up at the ends of its moves instead of easing in and out) and **girl arm.L arc 0.293 → 0.169** (flatter). Gaze and smoothness still PASS. |
| **T-022** contacts | – | All < 0.001 mm, effectively unchanged | – |

No merge resolution changed any task's numbers: every difference disappears when the other task's upstream input (clips or exporter) is swapped back.

**Visual notes** (`batch1_contact_sheet.png`):
- Eyes are centred in both characters' sockets in every close-up.
- No forearm enters the body at the reach, hand-over or release.
- The cup ends in the girl's hand.
- The boy waves in e906.
- As in the T-030 evidence, the cup is hidden by the boy's fist from this camera around the grasp and hand-over.
- T-030's open asset issue remains: the boy's hoodie sleeve stretches along the shoulder→wrist chord.

## 5. Evidence files (`docs/evaluation/integration/batch1/`)

**Videos (640×360):**
- `e905_s010_canonical.mp4` (72 frames)
- `e905_s010_with_dynamics.mp4` (72 frames)
- `e904_s010_dynamics_on.mp4` (48 frames)
- `e906_s010_canonical.mp4` (75 frames)
- `e906_s010_with_dynamics.mp4` (75 frames)

**Contact sheet:** `batch1_contact_sheet.png`.
- Blocks: e905 + dynamics, e904, e906 + dynamics.
- Close-ups under each beat: eyes, head/hair, and right forearm/hand with the measured gap.

**Measurements:**
- `e905_measurements.json`, `e905_dynamics_variant_measurements.json` (from `measure_e905.cpp`).
- `e904_dynamics_on_vs_off.json`, `e905_dynamics_variant_hair.json`, `e906_dynamics_variant_hair.json`.
- `e906_canonical/` (gaze, smoothness and principles checks + `summary.txt`).
- `e906_auto_idle_check.json`.

**Controls:**
- `e904_dynamics_control_t021_clips.json`
- `e905_control_t030_clips_measurements.json`
- `e906_control_t027_exporter_summary.txt`

**Scripts:**
- `make_dynamics_variants.py`
- `measure_dynamics.py`
- `measure_auto_idle.py`
- `contact_sheet.py`

Run folders (gitignored) are `<shot>/build/runs/batch1` and `<shot>/build/batch1_dynamics/build/runs/batch1r`. The control bakes are in `<shot>/build/batch1_t021clips|batch1_t030clips|batch1_t027exporter|batch1_t021exporter|batch1_noautoidle`.

Frozen data was not touched: boy 1.0.0/1.1.0, v6, tests/data, image baselines, docs/references (Frozen assets PASS). No test or threshold was changed.
