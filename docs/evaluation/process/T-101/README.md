# T-101: the 3 old failing tests from T-077 (round 3)

Branch `t-101-claude-old-tests` from `integration/round3` (input `f550cbd`). Task: [docs/tasks/T-101.md](../../../tasks/T-101.md).
Root causes: [T-077 README §4](../T-077/README.md). Current versions (fidelity baseline, unchanged on
`integration/round3` and `main` at the end of the task): **boy_yellow_hoodie 2.0.0, girl_auburn_bun_glasses 0.11.0**.
Blender: bpy 5.3.0 module (Python 3.13) through `tools/bpy_blender.py`, not an official Blender binary.

## 1. Result

**Complete.** All three tests pass on the current versions and run in the gate's Blender tier. No limit was loosened
and no check removed. Two checks were added: deform_test now fails on harness errors, and AC5 now checks the reach is
reachable.

| Test | Before (current versions) | Root cause fixed where | After |
| --- | --- | --- | --- |
| `pipeline/charsys/tests/deform_test.py` | IndexError (girl) | test harness: edges came from the unmasked mesh | 8/8 poses on both masters, exit 0 |
| `pipeline/charsys/tests/test_shot_eyes.py` | passes its 3 sampled frames, but girl chain gaps of 0.37 mm at frame 48 (see below) | engine: `SpringChainSolver` (`engine/anim/secondary.cpp`); test: all-frames check | 10/10 PASS (§6) |
| `pipeline/clips/test_emotions.py` | AC2, AC3, AC4, AC5, AC6 FAIL | test scene data and stated intent (§4) | AC2–AC6 PASS |

## 2. Files changed

| File | Purpose |
| --- | --- |
| `engine/anim/secondary.cpp` | segment length restored after a collider push; exact `arc()` (atan2) |
| `tests/test_secondary.cpp` | new case: a collider push on inner joints keeps the chain joint-continuous (< 0.01 mm) |
| `pipeline/charsys/tests/deform_test.py` | vertices and edges both from the evaluated mesh; exit 1 on a missing control or an unmeasured mesh |
| `pipeline/charsys/tests/test_shot_eyes.py` | `--cast current` (default): runs a copy of the shot on the current versions; `--bake-engine`; new check: spring chains joint-continuous over all baked frames (< 0.01 mm) |
| `pipeline/clips/test_emotions.py` | reachable cup; principles and collision planning stated per scene; `--blender` prepares the current versions |
| `tools/check_all.py` (guarded) | Blender tier: `deform_test` per current published master, `test_shot_eyes`, `test_emotions` |
| `docs/evaluation/process/T-101/**` | this report and its evidence |

## 3. Fixes

### 3.1 deform_test (T-077 §4.1)

- `EDGES` was read from `o.data.edges` (the unmasked mesh, girl 62 310 vertices). The positions came from the
  evaluated mesh, which the garment MASK modifier reduces to 39 169 vertices. Both now come from the evaluated mesh
  (`world_pts(o, edges=True)`).
- So deform_test measures the visible skin, as before on meshes without a mask. A MASK in vertex-group mode is
  static, so the topology is the same in every pose; the existing `len(P1) != len(P0)` guard still checks that.
- New: a skipped mesh is recorded in `unmeasured_meshes`, and the script exits 1 when a control is missing or a mesh
  is unmeasured. There are still no stretch limits; it is a measurement, as before.
- Results: [deform_test_girl_auburn_bun_glasses.json](evidence/deform_test_girl_auburn_bun_glasses.json) and
  [deform_test_boy_yellow_hoodie.json](evidence/deform_test_boy_yellow_hoodie.json).
  - p99 stretch is 1.0–1.22 on both characters.
  - The max stretch values are large: girl 128 at hip_forward_80, boy 96. Nothing judges them, as in T-077.
    **Not investigated** (a candidate for a body or weights task).

### 3.2 Spring chains (T-077 §4.2)

Two sources of joint gaps were found. `write()` places each chain bone rigidly at `x[k]`, pointing at `x[k+1]`, and in
Blender the DYN bones are connected. So any error in segment length or direction shows up as a gap at the next joint.

1. **Collider push** (the T-077 cause). The push in `step()` set `p[k] = q + n * minD` after the length step and never
   restored the length.
   - Now, after a push, the joint swings back onto its segment length around `p[k-1]`. Push and length alternate (at
     most 16 passes, 2e-5 m tolerance after the first) until the joint is outside every collider. The length is always
     restored last.
   - A joint that touches no collider takes exactly the old path.
2. **`arc()` precision** (new). `acos(dot)` near 1, plus the identity cut-off at `dot > 1 - 1e-7`, lost up to
   ~4.5e-4 rad.
   - Alone, this gave gaps of 0.01–0.045 mm on 3–8 cm segments, on chains with no collider contact (e904 s020: 48
     frames above 0.01 mm).
   - Replaced by `atan2(|a x b|, a . b)`.

Tests (doctest):
- New case `a collider push keeps the chain joint-continuous (T-101)`. A sphere beside the middle of the chain
  pushes inner joints.
  - Old solver: gap 0.046 mm, FAIL. New solver: 0.00008 mm, PASS.
  - The joint stays outside the sphere: 64.998 mm ≥ 65 − 0.1.
- The existing collision test is unchanged and passes. It only pushed the tip, which leaves no visible gap, so it
  could not see this.

**test_shot_eyes on the current versions.** With the input engine, e905 with cast "current" passes all 9 original
checks (girl "baked bones reproduced" 0.0015 mm). shot_render samples only frames 1, 36 and 72, and the current girl's
worst gap, 0.367 mm, is at frame 48. On girl 0.10.0 (T-077) the worst gap fell on frame 72.

So the test now also measures every spring-chain joint over all baked frames, with the same 0.01 mm limit as
"baked bones reproduced". This is a new check; no existing check changed. Results on e905 with cast current are in
§6: the input engine fails it, the final engine passes.

### 3.3 test_emotions (T-077 §4.3)

- **AC5:** the cup stood across the boy's body, out of reach. The current boy is 121 mm short even leaning
  (plush-render warning), so the IK ran at full stretch and the hand followed the emotion's shoulder.
  - The cup now stands in front of his right shoulder, at (−0.30, 0.495, 0.28). There are no reach or arm-body
    warnings, and the hand drift is 2.3e-7 m on frames 140–165 (limit 1 mm, window unchanged).
  - New check `boy_reach_reachable`: there must be no `reach 'cup'` warning for the boy.
  - The placement search is in [reach_try.py.txt](evidence/reach_try.py.txt). Nearby placements: (−0.29, 0.46,
    0.28), (−0.31, 0.50, 0.28), (−0.26, 0.48, 0.30) and (−0.32, 0.48, 0.26/0.30) give 0.0 mm.
  - **Limitation:** other reachable placements give 1.4–10 mm. Where the arm leans or the clearance pass acts, the
    reach's wrist and hold keys are computed from the posture-dependent shoulder at contact (`engine/scene/actions.cpp`,
    `wristFor`/`toBody`). So the check holds for this placement, not for every placement. Not changed: that file is
    outside the write-set.
- **AC2/AC3/AC4/AC6:** see §4.

## 4. Stated intent in test_emotions (Supervisor-approved 2026-11-19)

Every scene now states the animation principles (T-061) and the arm-body collision planning (T-047/T-082). Each
carries a `"reason"` in the scene itself (`animPrinciples: {"enabled": …, "reason": …}` and one
`{"type": "collision", "enabled": …, "reason": …}` action per character), and the module docstring explains it. The
limits are unchanged.

- **AC2, AC3, AC4, AC6: both off.** These ACs measure the emotion layer itself, the same body-independent motion on
  both characters, against its definition.
  - **Principles:** T-061 eases plain clip actions but not emotion layers. So with principles on, AC2's reference
    ("the posture clip as a plain clip action with the same timing") blends differently.
    - Unchanged test: happy/laugh 3.1°, sad/cry 1.9°, afraid 1.5°, sleepy 1.0° (limit 0.001°), and AC6 fails with them.
    - Principles off: ≤ 1.7e-6°.
  - **Collision planning:** it bends each character's arms around its own body, so the same emotion produces
    different arms on each character.
    - With principles off and collision on: AC2 boy vs girl up to 10.9° (sad; limit 2°), AC3 upperArm ratios
      0.42–1.04 (limit 0.475–0.525), AC4 boy entry 1.16° (limit 0.001°) and two windows at 1.06× and 1.01× of the limit.
    - Collision off as well: boy vs girl 0.000°, ratios 0.5000 ± 1e-5, entry/exit 0.0°.
- **AC5: both on** (production defaults, stated explicitly). AC5 layers an emotion on walk, look, wave and reach as in
  a real shot.
- **Where those systems are tested:**
  - Collision planning: `tests/test_collision.cpp`, `tests/test_interaction.cpp` (T-047/T-082).
  - Principles: `tests/test_anim_principles.cpp` and `tools/animcheck` (T-061; gate step `animcheck`).

Evidence:
- [emotions_unchanged_test.txt](evidence/emotions_unchanged_test.txt): the unchanged test on the current packages.
- [emotions_principles_off_collision_on.txt](evidence/emotions_principles_off_collision_on.txt)
- [emotions_collision_off_experiment.txt](evidence/emotions_collision_off_experiment.txt)
- [emotions_final.txt](evidence/emotions_final.txt) and [emotion_measurements.json](evidence/emotion_measurements.json)

## 5. Bake changes (AC4 of the task: reported before merge)

Every episode shot (13) was prepared with its own cast and baked with the input engine (`f550cbd`) and with this
branch's engine. Each old bake reproduces byte for byte with the old engine.

Tables: [bake_compare_final.txt](evidence/bake_compare_final.txt), and
[bake_compare_collider_only.txt](evidence/bake_compare_collider_only.txt) for the collider fix alone. Scripts:
[joint_gaps.py.txt](evidence/joint_gaps.py.txt) and [bake_diff.py.txt](evidence/bake_diff.py.txt).

In every shot, only DYN (spring-chain) bones change. Every non-DYN bone, every morph and the non-character data (camera,
lights, objects) are identical.

| Shot | Max DYN joint move | DYN bones changed | Largest joint gap: old → new |
| --- | --- | --- | --- |
| e000_pilot s010 (girl) | 1.71 mm | 166 | 0.0037 → 0.0002 mm |
| e900_workflow_test s010 | — (byte-identical, no chains) | 0 | — |
| e901_clip_test s010 (girl) | **136.8 mm** | 166 | **23.8 mm (75 frames) → 0.0002 mm** |
| e902_emotion_test s010 (girl) | 1.56 mm | 166 | 0.032 → 0.0002 mm |
| e903_test_video s010 (girl) | 0.0016 mm | 166 | 0.0103 → 0.0002 mm |
| e904_secondary_motion s010 (girl) | **97.7 mm** | 166 | **14.2 mm → 0.0002 mm** |
| e904_secondary_motion s020 (girl) | 0.0001 mm | 166 | 0.045 (48 frames) → 0.0002 mm |
| e905_props_test s010 (girl) | 1.19 mm | 166 | 0.367 → 0.0002 mm |
| e906_acting_test s010 (girl) | 0.0045 mm | 166 | 0.0113 → 0.0002 mm |
| e907_exchange s010 (boy / girl) | 0.098 / 0.0001 mm | 96 / 112 | 0.0039 / 0.0015 → 0.0002 mm |
| e907_exchange s010_calibrated (boy / girl) | 0.065 / 0.0002 mm | 96 / 112 | 0.0091 / 0.0038 → 0.0002 mm |
| e908_boy_acting s010 (boy) | 0.0155 mm | 96 | 0.0021 → 0.0002 mm |
| e908_girl_acting s010 (girl) | 0.0002 mm | 112 | 0.0065 → 0.0002 mm |

- The large moves (e901, e904 s010) are on chains that the old solver tore apart at the colliders. Those chains then
  follow a different path.
  - It is not an instability: in e901 the farthest a chain's last joint moves from its rest distance to the head is
    132 mm in the old bake and 126 mm in the new one.
  - These shots' hair motion will look different: the old curls detached and re-attached.
- The arc fix alone moves joints by at most 0.0002 mm (e901, collider fix vs final).
- The image regressions (ctest `regression_milestone01`, `regression_face_neutral`, `regression_lineup_abc`) pass
  unchanged.

## 6. Tests executed

- C++ (Release, renderer ON with Embree 4.3.0 and OIDN 2.3.3 prebuilt):
  - `ctest`: 4/4 pass, before and after (plush_tests, regression_milestone01, regression_face_neutral,
    regression_lineup_abc).
  - `plush_tests -tc="secondary motion*"`: 7/7 test cases.
- `deform_test.py` on boy 2.0.0 and girl 0.11.0 published masters: exit 0, `missing: []`, `unmeasured: {}`.
- `test_shot_eyes.py` (e905, cast current), 9/9 PASS:
  - boy eye 0.0052 mm, bones 0.0015 mm;
  - girl eye 0.0092 mm, bones 0.0015 mm.
- `test_emotions.py --blender` (e901 cast current, final engine): AC2, AC3, AC4, AC5 and AC6 all PASS. AC4 worst ratio
  0.83, entry/exit 0.0°, hand drift 2.3e-7 m.
- `tools/check_all.py` wiring: the new `t101_checks` was run directly with the final engine (deform_test ×2,
  test_shot_eyes, test_emotions). The full Blender tier (verify_charsys, regression and so on) was **not** run here;
  the gate runs it.
- Fast gate tools: `test_gate_tools.py`, `fidelity/tests/test_ci.py`, `test_run_shot_current.py` and
  `check_doc_links.py` pass.

## 7. Notes for the gate

- The Blender tier gets about 30 minutes longer:
  - deform_test: about 4–5 minutes per character, most of it 8 workbench renders;
  - test_shot_eyes: prepare, bake and a 72-frame `--blend-only`, about 15–17 minutes;
  - test_emotions: about 3 minutes plus prepare.
- test_shot_eyes and test_emotions need `plush-render`. check_all passes the gate build's binary, and fails both
  subchecks (never skips them) when the C++ build failed.
- The engine finds `content/` above a scene file, so both tests write their copied shot and scenes under
  `build/test_tmp/` (git-ignored). test_emotions run by check_all copies only `emotion_measurements.json` to the
  artifacts.
