# T-077: gate wiring of the ungated tests + check_assets, and the 3 failing tests

Branch `t-077-claude-gate-wiring` from `origin/staging` (`e449ef1`; merged with `origin/staging` again before READY:
already up to date). Task: [docs/tasks/T-077.md](../../../tasks/T-077.md). Sources:
[T-071 report §4–§5](../../review/T-071/README.md), [check_all_wiring.diff](../../review/T-071/check_all_wiring.diff),
`tools/check_assets.py` (T-075).

## 1. Task and result

1. **T-077:** wire the passing ungated tests and `check_assets` into the gate, and find the root cause of the 3 failing
   tests.
2. **Result: complete.** AC1: wired. AC2: all three root causes found with evidence. None can be fixed inside this
   write-set without loosening a threshold, so all three stay unwired (see §4). AC3: the gate passes except
   Guarded paths (`tools/check_all.py`).

## 2. Files changed

| File | Purpose |
| --- | --- |
| `tools/check_all.py` (guarded) | 4 fast Python tests, 5 Blender-tier subchecks (T-071 diff), and `check_assets.py` in the Frozen-assets stage |
| `docs/evaluation/process/T-077/README.md` | this report |
| `docs/evaluation/process/T-077/evidence/*` | gate summary, probe outputs, the experiment script and diff (scratch copies; no repo test changed) |

`tools/regression_paths.txt` is **not changed**. `tools/check_assets.py` already falls under `fast tools/**`, so no
rule is needed. Changing the file would also force a full-tier run on this branch.

## 3. What was implemented (AC1)

- **Python tests (fast tier)**, as in the T-071 diff: `pipeline/charsys/tests/test_versions.py` (73/73),
  `tools/fidelity/tests/test_metrics.py` (48/48), `tools/lipsync/test_lipsync.py` (9 OK) and
  `pipeline/charsys/tests/test_boy2_face.py` (3/3; spec part, no Blender). Together they add about **1 s**. The whole
  stage takes 5.2 s, most of it the cleanup tests that were already there.
- **Blender tier**, as in the T-071 diff (adapted to the current file, which has moved since `e007f48`):
  `render engine selector`, `groom dynamics` (json `pass`), `export determinism` (quick), and one boy
  2.0.0-dev build shared by `test_boy2_face` (11/11) and `test_hoodie` (28/28). Time added, from the log timestamps of
  the gate run: 0 + 1 + 4 + 59 = **about 64 s**, almost all of it the boy 2.0.0-dev build. Other Blender jobs were
  running on the same 4 cores at the same time, so this is an upper bound. T-071 measured 64 s.
- **`tools/check_assets.py` in the frozen/guarded stage:** new `check_frozen_and_assets(base, logs)` runs the frozen
  manifest check and `check_assets.py --base <gate base> --json <logs>/check_assets.json`. It reports both on the
  existing "Frozen assets" line, with two subchecks: `Frozen assets` and `Published versions`. This keeps the
  summary at 9 lines (the limit is 10). It adds about 0.2 s warm and 3 s cold. Log: `logs/check-assets.log`.
- **Not wired, on purpose:**
  - `test_clip_pipeline` and `test_run_shot_workflow` pass, but take more than 10 minutes each when cold, so they
    stay nightly (T-071).
  - `face_system_test` has no pass/fail limits.
  - The three failing tests (§4).

  The T-071 table lists 10 passing tests, or 11 rows when `test_boy2_face` is counted once per tier. The two
  nightly tests are part of that count. I read "self-contained Blender ones" and "keep the added time small" as
  excluding them. If the Supervisor wants them in the full tier anyway, that adds 2 × >10 min cold.

## 4. Root causes of the 3 failing tests (AC2)

Environment: bpy 5.3.0 module (Python 3.13, pinned wheel) through `tools/bpy_blender.py`, **not** an official Blender
binary. `plush-render` was built by the gate (`build/quality-gate`) with OIDN 2.3.3 prebuilt (sha256 checked).
Current character versions: boy 1.1.0 and girl 0.10.0, from e901/e905 `run_shot` prepare with cast `current`.

### 4.1 `deform_test.py`: IndexError on generic-body masters (MASK modifier)

- **Reproduced:** girl 0.10.0 published master gives
  `IndexError: index 39172 is out of bounds for axis 0 with size 39169` (line 100). Boy 1.1.0 runs to the end.
- **Cause:** `body_skin` has the modifier stack `['ARMATURE', 'MASK']`: 62 310 vertices in the mesh, 39 169 after
  evaluation. `EDGES` takes indices from `o.data.edges` (the unmasked mesh), but `world_pts` reads the evaluated,
  masked mesh. The guard `len(P1) != len(P0)` compares two evaluated meshes, so it never catches this.
- **Evidence for the fix:** a scratch copy with the MASK modifiers disabled after loading (as `face_test.py:35`
  does) runs all 8 poses on the girl: `missing: []`
  ([deform_nomask_experiment.diff](evidence/deform_nomask_experiment.diff)). That copy also shows very large stretch
  on the girl (`max_stretch` 280 at shoulder_raise; p99 1.057). These are probably the skin vertices hidden under
  the clothing. The script has no limits, so nothing judges them.
- **Not fixed here:** the fix belongs in `pipeline/charsys/tests/deform_test.py`, which is guarded and outside the
  write-set. It is also a measurement script with no limits, so it is not a gate test even once it is fixed.

### 4.2 `test_shot_eyes.py`: girl "baked bones reproduced 0.829 mm" (limit < 0.01 mm)

- **Reproduced:** 8/9 checks pass, and only that one fails
  ([test_shot_eyes.log](evidence/test_shot_eyes.log)). The eye checks pass: boy 0.078 mm, girl 0.0006 mm.
- **The bone:** a scratch copy of `shot_render.py` records the per-bone error
  ([shot_eyes_perbone.json](evidence/shot_eyes_perbone.json)). Only one bone exceeds the limit:
  **`DYN-back_curls.01.4`, 0.829 mm at frame 72**. It is the last segment of a girl hair-dynamics chain, with
  `use_connect = True`. All other girl bones are ≤ 0.003 mm, and all boy bones are ≤ 0.0008 mm.
- **Mechanism, measured on the bake itself (`bake.json`):**
  - For each DYN bone, I compared the joint point carried by the child's skin matrix with the same point carried by
    the parent's matrix.
  - At frame 72 the `back_curls.01.4` joint is **0.8294 mm** apart, which is exactly the reported error.
  - The engine's spring-chain output is not joint-continuous. In Blender those DYN bones are connected, so their
    location keys are ignored and the rig cannot reproduce the gap.
- **Engine source of the gap:**
  - In `SpringChainSolver::step` (`engine/anim/secondary.cpp`), each iteration first sets the segment length
    (`p[k] = p[k-1] + dir * length`) and then applies the collider projection (`p[k] = q + nrm * minD`). The
    projection does not restore the length.
  - `write()` places every bone rigidly at `x[k]`, pointing at `x[k+1]`. So any length error shows up as a gap at
    the next joint.
  - The girl's package has colliders: head, torso, shoulder_l and shoulder_r.
- **The test understates it:** `shot_render` checks the reconstruction on only 3 frames (1, 36, 72). Over all 72
  frames the bake has joint gaps on 19 frames, **up to 16.7 mm** (`DYN-back_curls.13.4`, frame 67).
- **Not fixed here:** the fix is either in the engine (keep segment lengths after the collider push; lane C,
  `engine/anim/secondary.cpp`) or in the Blender apply (`shot_render.py`, guarded: unconnected DYN bones, or
  reproducing stretch). Both are outside this write-set, and the test file is guarded. This is a decision for the
  Supervisor.

### 4.3 `test_emotions.py`: AC5 `boy_reach_keeps_hand` 0.056 m, plus new AC2/AC6 failures

**Reproduced:** `boy_reach_keeps_hand` 0.05608 m, the same as T-071 and T-046. Since T-071, AC2 and AC6 also fail
for `happy/laugh`, `sad/cry`, `afraid` and `sleepy` (AC2 body vs plain clip 1.0–3.1°, limit 0.001°)
([test_emotions_fails.txt](evidence/test_emotions_fails.txt)).

**AC5 root cause: the scene's cup is out of the current boy's reach.**

- `plush-render` warns on both scenes:
  `reach 'cup': 'boy' cannot reach ... at frame 140 even leaning (174 mm short)`.
- The cup is about 447 mm from the boy's right shoulder (the reach goes across the body). The arm is 232 mm, and the
  IK runs at full stretch: shoulder to hand is 232 mm on every frame from 136 to 165, with and without the emotion.
- So the hand position is the shoulder plus a straight arm. The angry posture moves the right shoulder 63–67 mm, and
  that carries the hand 48–56 mm. The test assumes the IK reaches its target.
- **Check:** I moved the pedestal and cup 0.40 m to the boy's right side and 0.08 m closer, and kept everything else.
  Both warnings disappear. The hand drift is **0.0 mm on frames 143–163**, with a residual of up to **3.7 mm only
  around contact (frames 138–142) and put-down (frames 164–167)**. That is still above the 1 mm limit; its cause (IK
  ramp or the frozen-wrist clearance frames) is not investigated.
- `animPrinciples: false` does not change AC5 (0.05608 m both ways).
- At T-003 and T-027 the check passed (5e-7 m). I could not bisect: the frozen boy 1.0.0 test package has no
  `retarget` block and fails with `KeyError`. My guess is that the boy's proportions, the walk end point or the
  reach planning changed since then. **Not verified.**

**AC2/AC6 root cause: T-061's animation principles are on by default.**

- Plain clip actions get eased, successive blends (`L.principles = true`, `engine/scene/actions.cpp:921`; succession
  offsets per rank in `ClipLayer::envelopeRank`). Emotion posture and gesture layers never set `principles`.
- AC2 compares the emotion's body with "the posture clip played as a plain clip action with the same timing". That
  reference now blends differently.
- **Evidence:** the same unchanged test, with only `animPrinciples: false` added to every scene
  ([emo_noprinciples.py.txt](evidence/emo_noprinciples.py.txt)), gives AC2, AC3, AC4 and AC6 **PASS** and 0 FAIL
  lines. Only AC5 fails.

**Not fixed here:**

- AC5 needs a reachable scene in `test_emotions.py`, which is guarded and outside the write-set, plus a look at the
  3.7 mm contact/put-down residual in the engine.
- AC2/AC6 need a decision: either the test's reference scene opts out of the principles, or the engine gives
  emotion layers the same principles as clip actions.

## 5. Tests executed

| Command | Result |
| --- | --- |
| `python3 tools/check_all.py --base origin/staging --task T-077 --blender <bpy wrapper>` | PASS: Frozen assets (+ Published versions), Write-set, lint, C++ build (131 s), C++ tests (CTest, plush_tests, animcheck), Python tests and links, Blender tier (709 s, 14/14 subchecks incl. the 5 new). **FAIL: Guarded paths: `tools/check_all.py`** (needs a `Supervisor-Approved:` trailer; expected). [gate_summary.txt](evidence/gate_summary.txt) |
| `check_python_tests()` alone | PASS, 5.7 s, all scripts (counts in §3) |
| `python3 tools/check_assets.py --base origin/staging` (via the gate) | PASS: 2 stores (boy 1.0.0 and 1.1.0; girl 0.10.0) |
| `deform_test.py` on girl 0.10.0 / boy 1.1.0 masters | girl IndexError, boy runs; scratch no-MASK copy runs on the girl |
| `python3 pipeline/charsys/tests/test_shot_eyes.py --blender <wrapper>` | 8/9; girl 0.829 mm (216 s) |
| `python3 pipeline/clips/test_emotions.py --boy/--girl <e901 packages> --out build/t077/emo` | AC3, AC4 PASS; AC2, AC5, AC6 FAIL (33 s) |
| same, `animPrinciples:false` (scratch wrapper) | AC2, AC3, AC4, AC6 PASS; AC5 FAIL |
| reachable-cup scenes (scratch) | no reach warnings; hand drift 0 mm on frames 143–163, 3.7 mm max at contact/put-down |

**Not tested:**

- The full tier (all-character regression). This branch is fast-tier (`tools/**`); GitHub CI on the branch is the
  record.
- Windows.
- An official Blender binary.

## 6. Baselines

- Frozen assets PASS, and `check_assets` PASS against `origin/staging`.
- CTest, including the frozen image regressions, PASS.
- No test file, threshold, asset, spec or engine file changed. The diff is `tools/check_all.py` plus this folder.
- All experiments ran on scratch copies outside the repository.
- `episodes/*/build/` and `build/` are git-ignored outputs.

## 7. Visual results

None (no renders needed).

## 8. Open questions for the Supervisor

1. **Approve `tools/check_all.py`** (guarded) with a `Supervisor-Approved:` trailer.
2. `test_shot_eyes`:
   - Who fixes the joint gaps in the spring chains: the engine (lane C) or `shot_render`?
   - Should the reconstruction check cover every frame, not only 3? Today it hides up to 16.7 mm.
3. `test_emotions` AC5: a task to make the reach scene reachable (guarded test change) and to explain the 3.7 mm
   contact/put-down residual.
4. `test_emotions` AC2/AC6: should emotion layers follow the T-061 principles (engine), or should the AC2 reference
   opt out (test)?
5. `deform_test`: apply the MASK fix (guarded test).
6. `test_clip_pipeline` and `test_run_shot_workflow`: nightly job, or the full tier at about 20 minutes extra?

## 9. Commits

Branch `t-077-claude-gate-wiring`. The commits are listed in `RELAY_LOG.md`.

## 10. Resource use

Token usage is not available.

Repeated work:

- The e905 prepare and bake ran twice: once in the test and once for the probe.
- The boy 2.0.0-dev build runs in the gate only.
