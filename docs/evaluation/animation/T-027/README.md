# T-027 evidence: acting quality (2026-11-16)

**Status:** implemented and measured. Nothing is approved or published. Script-made clips; not a reviewed acting pass.

**Environment:** bpy 5.3.0 module (Python 3.13) behind a `blender` CLI wrapper; engine Release build with the official
OIDN 2.3.3 prebuilt (`-DPLUSH_OIDN_ROOT`); Cycles (bpy) at 640×360, 16 samples, denoising on (OIDN), ~6 s/frame on
4 CPU threads. Cast: **boy 1.1.0** (`boy_yellow_hoodie.spec.json` + the existing `1.1.0.override.json`, unpublished)
and the **girl** built from her current spec. Baseline = `main` at e94f3bc (the commit this branch started from).

## What changed (root causes from the review)
| Finding | Fix |
| --- | --- |
| shoulder, elbow, wrist rotate in sync | `clip_principles.perform()`: successive breaking, the proximal joint leads (elbow +1–1.5 frames, wrist +2–3, fingers +3–4.5), distal follow-through |
| no anticipation / overshoot / settle | `move()`: counter-move, overshoot, damped settle, C1 at every phase joint |
| hips and spine do not take part | `support()`: pelvis hike and shift towards the action side, spine/chest counter-rotation, trunk turn/lean; `plant_legs()` IK keeps the feet planted in the idle's weight shift |
| uniform spacing | `ease()` profiles; acting clips keyed every frame (authored spacing) |
| characters without a body idle look static and symmetric | automatic base idle (`clip_layers.cpp`, opt out `"autoIdle": false`); `idle_relaxed` is now an asymmetric contrapposto stance with weight drift, breathing travelling up the chain and arm overlap |

## 1. Retarget tolerances and T-002 smoothness (thresholds unchanged)
`t002_clip_measurements.json`, `t002_summary.txt` — `measure_clips.py` on boy 1.1.0, girl and the neutral mannequin.

| Clip | C2 boy vs girl dir / twist (limit 2.0 / 5.0°) | C3 engine vs Blender dir / twist (limit 1.0 / 3.0°) |
| --- | --- | --- |
| idle_relaxed | 0.0000 / 0.0000 | 0.0585 / 0.0487 (180 frames) |
| wave | 0.0001 / 0.0000 (was 0.95: the trunk is now driven) | 0.0351 / 0.0293 |
| point | 0.0000 / 0.0000 (was 0.94) | 0.0514 / 0.0331 |
| sit_down / stand_up | 0.0000 / 0.0000 | 0.0392 / 0.0341 |
| dense_test | 0.0000 / 0.0000 | 0.0000 / 0.0000 |

C4: all 22 boundary windows, both loop seams (0.32°/frame = 1.00 × interior max, limit 1.25) and 16 entry/exit checks
pass (`{"C2": true, "C3": true, "C4": true}`).

**T-003 emotions** (`t003_emotions_summary.json`, `test_emotions.py`, same packages): AC2, AC3, AC4, AC6 pass (AC4 worst
ratio 0.83, main 0.89; single-emotion max 10.65°/frame on both). **AC5 fails on main too**: `look_keeps_gaze` 1.57° on
main → 3.43° on the branch (limit 0.5°); every other AC5 item passes. Open issue, see below.

## 2. Automatic base idle
- e000 and e900 (no base clip) now idle; `measure_shot.py` gaze and smoothness PASS (`auto_idle_e000_pilot/`,
  `auto_idle_e900_workflow_test/`).
- Shots with a base clip, same new clips, main engine vs branch engine (`engine_only_bake_check.json`): e903
  **byte-identical**; e901 / e902 differ only on thigh / shin / foot during the walk spans (the base idle's legs now
  follow the walk while it owns them).
- Life-layer blink defaults are unchanged; e902/e903 keep their `blinkInterval: 100`.

## 3. Principle metrics before / after (`clip_principles_before_after.json`, `.txt`)
Each clip on both characters (life off, no auto idle), a gesture over its own version's `idle_relaxed`. Boy shown
(girl within a few %). Ease ratio: lower = more eased; arc: path deviation / chord; symmetry 1 = mirror-symmetric.

| Clip / chain | effector ease | joint ease | arc curvature | anticipation | overshoot/settle | micro rms ° | symmetry |
| --- | --- | --- | --- | --- | --- | --- | --- |
| idle_relaxed arms L / R | 0.84→0.70 / 0.87→0.92 | – | – | – | – | 1.55→1.82 / 1.33→1.65 | **0.99→0.87** |
| idle_relaxed trunk | **1.01→0.72** | – | – | – | – | 0.99→0.77 | |
| wave arm.R | 0.26→0.30 | 0.28→0.33 | **0.062→0.182** | **no→yes** | **no→yes** | | 0.04→0.00 |
| wave trunk | **1.02→0.30** (trunk now moves) | – | – | – | – | 0.99→1.60 | |
| point arm.R / trunk | 0.48→0.34 / 1.01→0.45 | 0.27→0.34 | 0.215→0.189 | **no→yes** | **no→yes** | | |
| gest_shrug arm.L | 0.10→0.35 | 0.11→0.32 | 0.163→0.193 | **no→yes** | **no→yes** | | 0.99→0.91 |
| gest_yawn arm.L / R | 0.25→0.24 / 0.29→0.44 | 0.25→0.25 / 0.29→0.22 | 0.278→0.293 | **no→yes** | **no→yes** | | 0.99→0.82 |
| emo postures (happy, sad, angry, surprised) | holds | | | | | | 0.98–0.99→0.92–0.95 |

**Reading it honestly:** anticipation, settle, asymmetry, trunk participation and idle spacing improve clearly. The
old gestures were already eased by Blender's Bézier keys; the new arm moves are slightly *less* eased (joint ease
0.27–0.29 → 0.32–0.34, shrug 0.11 → 0.32) because anticipation and settle take part of each beat and the main moves
use power 1.5–1.6 to keep peak speeds at the old level (wave 15.8 vs 15.2°/frame, point 9.4 vs 6.3, shrug 10.7 vs
10.5, yawn 9.4 vs 7.0; emotion AC4 requires ≤ 12). Arc curvature of the raise/lower moves is about unchanged (a
rotating shoulder already sweeps an arc relative to the shoulder); the swings now arc (0.06 → 0.18).

## 4. Visible proof: `episodes/e906_acting_test` (2.5 s, 75 frames, 30 fps)
- `e906_old_vs_new_640x360.mp4` (left: old clips, no idle = main's behaviour; right: new clips + automatic idle) and
  `e906_contact_sheet_old_top_new_bottom.jpg` (frames 1, 11, … 71).
- New shot: no base clip (both auto idle), life layer on with default blink timing; no automatic blink falls in 2.5 s,
  so the boy's reaction blink is an `expression` action (frames 12–16). The girl waves (left arm, speed 1.25, from
  frame 3), the boy waves back small (weight 0.7, speed 1.5, from frame 17); both start from held rest frames and end
  inside the shot. The old variant (`make_old_variant.py`, untracked) plays the old clips with speeds scaled to the
  same durations and `"autoIdle": false`.
- `measure_shot.py` (`e906_new/`, `e906_old/`): new gaze PASS, smoothness PASS; old smoothness **FAIL** (boy
  forearm.R 12.03°/frame at frame 19: the old wave blends from the package A-pose in 2 frames — there is no idle under
  it). Shot principles (new / old): boy idle micro-motion 1.05° / 0.16° (arms), 0.43° / 0.17° (trunk); boy symmetry
  index 0.29 / 0.51; girl wave arc 0.293 / 0.051; anticipation and settle detected in both (in the old shot the
  detector also sees the A-pose blend-in as a counter-move).

## Reproduce
```
blender -b --factory-startup -P pipeline/clips/build_mannequin.py -- --out <m>
blender -b --factory-startup -P pipeline/clips/make_clips.py -- --mannequin <m>/neutral_mannequin.blend --out content/clips --blend-out <m>/clips.blend
blender -b --factory-startup -P pipeline/clips/make_emotion_clips.py -- --mannequin <m>/neutral_mannequin.blend --out content/clips
blender -b --factory-startup -P pipeline/clips/measure_blender.py -- --blend <m>/clips.blend --out <m>/poses.json
blender -b --factory-startup -P pipeline/charsys/export_engine.py -- --blend <m>/neutral_mannequin.blend --profile pipeline/charsys/rig_profiles/humanoid_rigify.json --out <m>/pkg
python3 pipeline/production/run_shot.py --shot episodes/e906_acting_test/shots/s010/shot.scene.json --blender blender --run-dir new --resolution 640 360 --samples 16 --video
python3 pipeline/clips/measure_clips.py --boy <boy pkg> --girl <girl pkg> --mannequin <m>/pkg --blender-poses <m>/poses.json --out build/t027/t002
python3 pipeline/clips/test_emotions.py --boy <boy pkg> --girl <girl pkg> --out build/t027/t003
python3 pipeline/clips/measure_shot.py --clips-before <old clips dir> --clips-after content/clips --package boy=<pkg> --package girl=<pkg> --out <dir>
python3 episodes/e906_acting_test/make_old_variant.py   # then run_shot on shots/s010/build/old_variant/shot.scene.json
```
Packages: the e906 shot cache (`shots/s010/build/packages/boy_77a6…`, `girl_3904…`). Measurement output folders must be
inside the repository (clips resolve upward from the scene).

## Open issues
- `test_emotions.py` AC5 `look_keeps_gaze` fails on main (1.57°) and more on the branch (3.43°): eyes run into the
  T-006 gaze limits; an emotion posture replaces the idle's head offset. Needs a look/emotion-layer decision.
- The engine walk alone exceeds 12°/frame on the thighs at every step; the T-002 "wave during walk: blend-out" window
  passes only for wave lengths that avoid those frames (90 frames does; 72 did not).
- Pelvis tilt does not move the hip joints of top-level Rigify thighs (≈1–2 mm foot error at the idle's 1° tilt).
- Eyes sit at the 30° gaze limit in e906 (the look targets are far to the side).
