# T-045: body mechanics (shoulders, clavicles, torso, weight shift)

Branch `t-045-claude-body-mechanics` (from `origin/staging`; staging merged before the gate). Implementer report.

## 1. Task and objective
Owner feedback "bodies look robotic, little shoulder and torso motion": a shared, data-driven engine layer that makes
shoulders, torso and legs take part in what the arms do, tuned per character from the personality draft profiles.

## 2. Result: complete (AC1–AC5), with the limits in §8
- AC1–AC3 are implemented and tested (10 new test cases; every existing test unchanged and passing).
- AC4: one 5.5 s shot (both characters, idle → reach → wave), rendered twice in Cycles (16 samples + OIDN):
  before (layer off) and after (layer on). Side by side: `t045_before_after.mp4`. Keyframes next to the reference
  stills: `before_after_sheet.jpg`. Curves: `body_curves.jpg`.
- AC5: gate result in §5.
- **The layer is opt-in** (scene character `"bodyMechanics"`), so every existing shot, bake and test is unchanged.
  Turning it on in existing shots or by default is a Supervisor/owner decision (§8).

## 3. Files changed
| File | Purpose |
| --- | --- |
| `engine/anim/body_mechanics.h`, `.cpp` (new) | The layer: rig binding, driver measurement, follow-through kernels, idle weight shift, posture, clavicles, torso, weight shift, pivot carry, leg IK; personality / override / limit parsing |
| `engine/anim/animation.h`, `.cpp` | `Pose::offset`: optional per-bone pivot translation (empty by default = identical output), honoured by `boneGlobals` (so IK, skinning and bakes see it) |
| `engine/scene/scene.h`, `scene.cpp` | Scene character field `bodyMechanics` (load/save as written); per-character setup; per-frame driver cache; filtered input; the hook in `kinematicGlobals` after life and before constraints (IK, look-at) |
| `engine/scene/actions.cpp` | Builds the layer when actions compile (actions see it while planning reaches/contacts); no driver cache while compiling |
| `engine/CMakeLists.txt`, `tests/CMakeLists.txt` | New source and test files |
| `content/rig_profiles/body_mechanics.json` (new) | Shared rig profile: clavicle and hip-helper candidate names, limits |
| `tests/test_body_mechanics.cpp` (new) | 10 test cases (§5) |

Documentation and evidence (this folder): `README.md`, `make_shot.py` (writes `shot_before/` and `shot_after/`),
`plot_curves.py`, `make_sheet.py`, `t045_before_after.mp4`, `before_after_sheet.jpg`, `body_curves.jpg`,
`curves_summary.json`. Not changed: `engine/scene/interaction.*`, `engine/model/**`, `engine/scene/face_layer.*`,
`emotion.*` (no hook was needed), pipeline, tools, clips, frozen files.

## 4. What was implemented
**Placement.** `kinematicGlobals`: clips → expression bones → life → lid blink → **body mechanics** → constraints (IK,
hand pose, look-at) → arm poles / orient constraints → clip fingers. Because the layer runs before IK, IK targets and
contacts are reached exactly with the moved shoulders, and the look-at aims the eyes after the torso and head moved.

**Drivers** (per integer frame, pose after clips, before the layer; cached, random access). Per arm: elevation above
its rest elevation (shoulder → wrist direction; the clip pose blended with the arm IK target by its weight), forward
reach (forward component beyond a dead zone × extension) and outward reach; legs: standing (thighs near vertical);
walk ownership from the existing walk spans.

**Follow-through / overlap.** Drivers pass through discrete impulse responses of a delayed damped spring: damping from
the profile's `overshoot`, natural frequency from `settle_frames` (2 % settle), delay from `anticipation_frames`
(× 0.35, 1–4 f); frame values at 24 fps converted to the scene rate. Three responses: shoulders (half settle, no
delay: they lead), torso (full settle, delayed, overshoot: it overlaps), weight (double settle, no overshoot: the
body's mass does not wobble with a waving hand). Fractional frames interpolate between integer frames (secondary
motion and the renderer stay smooth).

**Mechanics.**
- Clavicle: shrug = limit × (elevation − 25°)/110° (scapulohumeral rhythm, starts above ~25°), protraction = limit ×
  forward reach (+ posture bias), applied in character axes about the clavicle pivot; the arm pivot rides on it.
- Torso: forward lean into reaches (`lean_toward_task`), twist toward the reaching arm with the pelvis counter-rotating
  (−30 %), side bend away from a raised arm and into a sideways reach; 40 % spine / 60 % chest; the neck takes back
  `headStabilize` (0.6) of it. Amplitude × `torso` × (0.5 + `gesture_amplitude`).
- Weight shift: a slow idle alternation (hold time 9 s at energy 0 → 4.5 s at energy 1, per-hold amount varies,
  1.3 s transfer) blended toward the reaching side while reaching; pelvis translation (`pelvis_shift` × leg length),
  roll (free hip drops), spine/chest counter-roll; only while standing and not walking.
- Feet stay planted: pelvis lowered by exactly what the support leg lacks (only what the layer adds), then two-bone leg
  IK to the feet of the pose before the layer, sole orientation restored; a straight knee is pre-bent 4° forward so
  it always bends forward.
- Posture rest layer from the profile: slouch (spine/chest forward, neck compensates), shoulders forward
  (protraction bias), head pitch (neck 40 % / head 60 %).
- **Pivot carry** (`Pose::offset`): bones whose skeleton parent is not their anatomical carrier follow the carrier's
  motion relative to the rest pose: the clavicle rides on the chest (with rotation), the arm pivot on the clavicle (or
  the chest), the thighs and hip helpers on the hips. On the imported Rigify packages the clavicle, arm and thigh
  bones are unparented, so before T-045 their pivots stayed fixed when the torso bent (limit noted since T-002); with
  the layer on, a 15° spine bend now carries the arm pivot to within 0.0001 mm of the chest-carried position
  (46 mm off without).

**Data, no character names in engine code.** Bones by shared role names (`hips`, `spine`, `chest`, `neck`, `head`,
`upperArm/forearm/hand`, `thigh/shin/foot` `.L/.R`); clavicle and hip-helper candidates (`clavicle`, `shoulder`,
`DEF-shoulder`; `DEF-pelvis`) and limits from `content/rig_profiles/body_mechanics.json` (built-in neutral defaults
if absent). Scene JSON per character:
`"bodyMechanics": true` (shared neutral tuning) or `{"personality": "<profile id>", <field overrides>, "limits": {}}`;
the profile is found as `content/personality/<id>.json`, else `<id>.draft.json`. Fields read from the profile:
`tempo.settle_frames`, `tempo.overshoot`, `tempo.anticipation_frames`, `energy.level`, `energy.gesture_amplitude`,
`posture.slouch`, `posture.head_pitch_deg`, `posture.shoulders_forward`, `posture.weight_shift`,
`posture.lean_toward_task`; a missing field keeps the neutral default (schema rule). `head_tilt_deg` and
`rest_hands` are not used (T-053 / T-051 scope).

**Assumptions.** (1) "Defaults neutral" read as: off unless a shot enables it; when enabled without a profile, the
shared mid tuning, zero posture. (2) Counter-balance direction for a raised arm (bend away) and weight toward a
reaching arm are my choices; the references do not show either (extrapolation).

## 5. Tests executed
- `build/tests/plush_tests`: **104/104 test cases pass** (94 existing unchanged + 10 new; 33 591 assertions).
  `ctest`: **4/4 pass** (OIDN 2.3.3; the three image regressions unchanged).
- New `tests/test_body_mechanics.cpp` (boy 1.0.0 and girl m3 packages, toy fixture, engine SDF character):
  | Test | Key numbers |
  | --- | --- |
  | off by default; `false` = absent (bit-identical globals, `Pose::offset` empty); scene round trip | — |
  | clavicles shrug/protract with elevation, within limits; resting side only rides on the chest; proportional | wave peak elevation 112° / 124° above rest; clavicle max 12.5° / 14.2° (limit 22°); arm pivot rise 20 / 18 mm |
  | torso leans and twists into an IK reach with follow-through; head stabilised; wrist on target | chest lean hold 6.0°, peak 6.3° (≈ 4 % overshoot), twist 7.5°, back to 0 after; lags at f28; head turns 3.9° vs chest 9.7°; wrist on target < 1 mm |
  | weight shift: pelvis over the support leg, free knee bends forward, feet planted | pelvis ±18–20 mm at weight_shift 1; feet ≤ 0.1 mm, 0° sole change; free knee +18–24° |
  | pivot carry of arm and thigh pivots | arm pivot 0.0001 mm from the carried position (46 mm without) |
  | rigs without clavicles / bare skeleton | no layer warnings, finite globals; bare skeleton untouched |
  | personality profiles tune it; overrides win; unknown profile → one warning, neutral | boy rest chest pitch +4.4°, girl 0.0° |
  | follow kernel / idle signal well formed | kernel sums to 1, overshoot within request + 0.03 |
  | random access deterministic | bit-identical in any order and across evaluators |
  | **interaction contacts with the layer on (AC3)** | grasp and place on boy and girl, layer on (neutral, boy and girl profiles): palm-to-grip ≤ 0.0006 mm, place ≤ 0.0005 mm (limit 5 mm) |
- Full gate: `python3 tools/check_all.py --base origin/main --build-dir build --blender <bpy 5.3 wrapper>` → see §5a.
- Blender used: **bpy 5.3.0 module** (Python 3.13) through `tools/bpy_blender.py`; no Blender binary was available.
- Not tested: walking shots with the layer on (the walk gate is implemented and unit-checked only through the driver);
  sitting clips with the layer on (the standing gate turns weight shift and leg IK off); the third character (not
  built).

### 5a. Gate
After `git merge origin/staging` (clean), in the foreground session's background job (the gate takes > 10 min):
```
PASS Frozen assets
FAIL Guarded paths: REQUIRES SUPERVISOR APPROVAL: tests/CMakeLists.txt, tests/test_body_mechanics.cpp
PASS Shared-systems lint
PASS C++ build
PASS CTest
PASS plush_tests
PASS Python tests
PASS Documentation links
PASS Blender tier
```
The only FAIL is the guarded-path trailer an Implementer cannot give itself (every test file is guarded).

## 6. Baselines
The layer is off unless a scene sets `bodyMechanics`; no existing scene, clip, package or test data was edited. The
first test case shows bit-identical output with the layer absent / off; all 94 existing test cases and the 4 ctest
image regressions pass unchanged; no frozen file is touched (gate "Frozen files").

## 7. Visual results
Shot: `make_shot.py` → `shot_before/`, `shot_after/` (only difference: `bodyMechanics` with each character's
personality draft). 132 frames at 24 fps, 640×360, Cycles 16 samples + OIDN, ~13 s/frame; boy published 1.0.0, girl
built from her spec (experimental). Two renders were used (the budget).
- `t045_before_after.mp4`: before | after.
- `before_after_sheet.jpg`: frames 1, 32, 46, 90, 100, 126, before/after, under the reference stills (`char_C`, `#29`,
  `char_B`, `ref_46`).
- `body_curves.jpg` (+ `curves_summary.json`): clavicle vs chest, chest lean/twist/side bend, pelvis x, right shoulder
  height, knees, head pitch; dashed = before, solid = after.

| Channel (after vs before) | Boy | Girl |
| --- | --- | --- |
| Clavicle vs chest | 0 → 2.4° at rest (shoulders forward), 7.0° in the wave | 0 → 0° at rest, 5° in the touch, 10.8° in the wave |
| Chest lean forward | rest ≈ 3–5° (slouch), 7.7° in the touch | rest 0° (upright), 8.5° in the touch |
| Chest twist | ±2.3° | up to 5.1° toward the reach |
| Pelvis x | −12 … +8 mm (slow idle shift, toward the waving arm) | −6 … +2.5 mm |
| R shoulder height | +10 mm in the wave | +17 mm in the wave |
| Head pitch at rest | 1° → 16° (head pitched toward the object) | unchanged |
| Knees | support ≈ 5°, free leg up to 26° | support ≈ 5°, free leg up to 20° |

**Against the references (checklist row T-045).**
- Boy slouch, head pitch, shoulders forward (`char_C`, `C1`): now present at rest (before: upright, chin level).
- Boy weight on one leg (`#29`): slow alternation with long holds, a bent free knee; small amplitude (low energy).
- Boy low body motion (`WT`): idle motion stays slow; no quick moves (owner decision 2026-11-17).
- Girl upright (`char_B`, `ref_46`): rest chest 0°, no slouch; she leans further and twists more into the touch
  (lean-in, `WT f022`–`f060`), brisker shoulder response (gesture 0.6).
- Leaning on a rim (`WT`, `CW`) is not covered: it needs a contact action (T-051 / interaction scope).
- Identity: no change to proportions, faces, hair, clothes (same packages, same masters).
- Extrapolation (not in the references): clavicle shrug amounts, counter-balance side bend, weight toward the reaching
  arm, idle weight-shift cadence.

## 8. Problems, limitations and open questions
1. **Opt-in.** Existing shots do not change. Question: enable it in `run_shot` shots by default (e.g. whenever life is
   on, with the cast's personality profile), or per shot? A default-on switch would change existing bakes.
2. **Girl's wave hand** is hidden behind her hair/head in both renders (the `wave` clip on her proportions, mirrored
   or not); not caused by this task.
3. **Hair spring-chain tips stretch** while the head pitches down (girl `DYN-nape_curls.00.4` up to 27.7 mm before,
   26.9 mm after; `shot_render` reports it as `max_bone_error_mm` 19 / 28 mm in the touch frames of both renders).
   Pre-existing collision push in the secondary-motion solver, not caused by this layer; worth a task.
4. The touch action's automatic look pitches both heads down ~50°: pre-existing, both renders.
5. Profiles are drafts (T-053a); values are used as they are. `head_tilt_deg` is not applied.
6. The arm's aim is kept when the clavicle moves (the clip intent wins); the glenohumeral angle is not reduced by the
   shrug share. Good enough at these amplitudes; a later refinement.
7. The gate needs a Supervisor trailer for `tests/CMakeLists.txt` and `tests/test_body_mechanics.cpp` (guarded
   paths: every test file), as for earlier tasks.

## 9. Commits
Branch `t-045-claude-body-mechanics`: `608d719` (implementation, evidence), merge of `origin/staging`, and the report commit (the head of the branch; see `RELAY_LOG.md`).

## 10. Resource use
Token usage: not available. Renders: 2 (before, after), each split into frame chunks to stay inside the command
time limit; 8 frames of a first "after" chunk were rendered with a camera that cut off the girl's bun and were
discarded (re-rendered after the camera change). Engine previews (not Cycles) were used to check framing and poses.
