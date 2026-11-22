# T-198 Motion Continuity Guard (work in progress; state: ROUND.md)

Detect and correct unnatural frame-to-frame jumps of hand targets, head rotation and gaze; keep intended fast moves
and camera cuts. Per-frame speed limit (engine `MotionLimits`, `engine/anim/animation.h`): body bones 1080 deg/s and
2.4 m/s (45 deg / 100 mm per frame at 24 fps, the T-183 snaps.py threshold), fingers 600 deg/s relative to their
parent (25 deg / frame); eyes, DEF and chain bones not measured. Intended by data only
(`continuityExemptions`, `engine/scene/interaction.h`): "cut" = a `camera.*` or the character's own position / yaw
key that steps at the frame; "fast" = an action with `"fast": true` (start .. end + 1).

## Causes (e912, measured with `trace_t198.cpp`, ablations on copies of the resolved scenes)

| snap | path | mechanism |
|---|---|---|
| s010 auburn hands f79, 101, 116, 131, 146, 161 (ramp in) | `actions.cpp` ikRamps (touch) | full weight at contact - 6, minus the elbow lag 2.4 f: ramp 78 -> 79.6, weight .21 / .84 / .98 |
| s010 f98, 120, 135, 150, 165, 180 (ramp out) | ikRamps | touch holds to contact + 10 = 98 but end = 97: out ramp keyed 98 -> 97 (inverted): weight 0 at 97, 1 at 98, then a half-IK hold to the next touch |
| s010 fingers 28-36 deg / f (T-190) | touch hand-shape keys | curl relaxed -> closed from start to contact - 8 = 2 frames |
| s020 auburn head f109-111, f133-136, chest f133 | look keys + lag average + assistGazeWithNeck | the look switch boy -> white keys a straight path that passes through her own head (all three sit in a row); the lagged mean of target positions collapses onto the head; the assist passes oscillate for such a near target (residual -67 / +82 / -91 / +92 deg) and the last pass picks a different branch each frame |
| s020 auburn hand.L f45-46, boy hand.R f137-138 | interaction.cpp orient weight + `applyOrientConstraints` slerp | clip hand vs planned grip ~170-180 deg apart, weight 0 -> 1 in 3-4 frames: the shortest-path slerp flips side (auburn), or the turn is simply too fast for the ramp (boy) |
| s030 f93, all three | (none: staging) | step keys on every position / yaw and on camera.position / target / lens at 93: classified "cut" |

## Fixes (each only where the measured per-frame peak is over the limit; every other key bit for bit)

| fix | where | trigger | what |
|---|---|---|---|
| touch IK ramps | `actions.cpp` ikRamps | arm (upper arm, forearm, hand) over the limit in a ramp; an inverted out ramp | out ramp rebuilt before `zero`; ramps lengthened (lag first, then earlier start), up to 8 tries |
| touch finger curl | `actions.cpp` touch | fingers over the limit while closing | closes later (at most contact - 4) |
| look arc | `actions.cpp` look | the straight shift passes within 0.6 x the nearer end's distance of the looker's head AND the head chain (head to root) measures over the limit with the straight keys | 2 keys on an arc round the head; `<who>/continuity.lookArc` marks start .. start + 16 |
| lagged look direction | `animation.cpp` laggedLookTarget (life head follow, gaze assist) | only on `continuity.lookArc` frames, when the lagged mean point collapses toward the head (r < 0.75) | the mean direction blended in |
| assist search | `animation.cpp` assistGazeWithNeck | the assist passes diverge (excess rises) | 5 / 1 / 0.25 deg grid for the smallest neck turn with the least excess |
| orient blend | `interaction.cpp` finishInteractions (last pass) | clip hand vs plan > 150 deg in an orient weight ramp AND (the shortest path flips side, or the hand turns over the limit) | per-frame keys of the blend with a sticky hemisphere (weight 1); if still over, the blend starts earlier (ends later for a release) by 2 frames at a time, at most 12, over weight-0 frames, eased |

## Before / after (e912, `tools/motion_checks/continuity.py` on bakes of the resolved scenes; frames with a bone over the limit, not cut / fast)

Before = `0cb0053`, after = this branch; `plush-render <resolved> --bake`; the engine's `continuity_t198` agrees on both.

| shot | before | after |
|---|---|---|
| s010 | 17 (hands 109-281 mm, forearms to 147 deg, fingers 28-36 deg) | 0 (peak forearm 33 deg / f) |
| s020 | 9 (head 95 / 115, chest-carried arm 113 mm, hands 79 / 56) | 0 (auburn hand.L peak 34, boy hand.R 39 deg / f; head under the limit) |
| s030 | 0 (f93 cut, 3 characters, 1.1-1.6 m) | 0 (f93 cut) |

f101 in s010 is also a camera cut (the R touch started on it); the ramp fix removes its jump anyway.

## Goldens (`golden_dump_t198.cpp` + `golden_delta_t198.py`: every bone's world turn / travel per frame, two builds)

- Round 1 changed exchange, e907 s010, s010_calibrated: boy head <= 29 deg, neck 19.5, eyes <= 39.5 deg, <= 0.8 mm,
  f60-66 / f110-121: the look arc + lag direction fired on his look switch through his own head, though its peak was
  33-35 deg / f (under the limit). Gated by the measured peak (look arc row above): all 6 content goldens bit-identical.
- The orient blend changes `test_interaction/visibleGrip/boy` (frames 11-14, hand.R and the 19 bones it carries): it had
  a 147 deg one-frame hand flip at f11; after it the peak is 25 deg / f. Re-recorded (Supervisor approval);
  per-frame table in [golden_delta.md](golden_delta.md).

## Recorded rows (ratchet) and follow-up T-210

The shipped content scenes (test packages as cast) still have 125 unexempt rows, recorded with their causes in
[continuity_baseline.json](continuity_baseline.json). The test fails if a row is added or a value grows:

| scene | frames (character, hand) | bones | peak | cause |
|---|---|---|---|---|
| eval/exchange, e907 s010 | boy R f16-17; f54 | 8 fingers each; 4 | 31.7; 27.3 deg | grasp closes in the 2 frames before contact 18; handover giver opens at release 51 + 3 |
| eval/handover, e905 s010 | boy R f15-16; f54 | 8; 4 | 31.7; 27.3 deg | grasp contact 17; handover release 51 + 3 |
| e907 s010_calibrated | boy R f28-29; f85 | 8; 4 | 31.7; 27.3 deg | grasp contact 30; handover release 82 + 3 |
| e901 s010 (30 fps, finger limit 20 deg / f) | girl R f243-244; f276-278 | 6; 3 / 6 / 3 | 31.7; 22.8 / 26.7 / 21.6 deg | reach closes before contact 245; opens after release 274 |
| e901 s010 | boy hand.R f223 | 1 | 81 mm (1.01 x at 30 fps) | walk start 220: the arm swing starts |

T-210 (after this merge): grasp / reach close and handover / reach release curl timing (as the touch curl fix), which
removes the finger rows (golden change, numbers first). The e901 walk-start row is one frame at 1.01 x.

## Tests

`tests/test_motion_continuity.cpp` (registration in tests/CMakeLists.txt: Supervisor at merge): bone classes and the
limit; exemptions by data; a touch ending before contact + 10 (no weight rise after contact, 0 snaps); a look through
the head (arc + marker, 0 snaps) and a clear one (no marker); visibleGrip boy (no hand.R snap); the ratchet over the 6 shipped content scenes (`continuity_baseline.json`). Unchanged calm motion:
test_bake_golden. `tools/motion_checks/tests/test_continuity.py`: the bake check (limit, cut, fast, classes).
