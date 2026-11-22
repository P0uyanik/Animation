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
| s020 auburn hand.L f45-46, boy hand.R f137-138 | interaction.cpp orient weight + `applyOrientConstraints` slerp | orient weight 0 -> 1 in 4 frames, and clip hand vs planned grip ~180 deg apart: the shortest-path slerp flips side (open, ROUND.md next 2) |
| s030 f93, all three | (none: staging) | step keys on every position / yaw and on camera.position / target / lens at 93: classified "cut" |

## Before / after (continuity_t198 on the resolved scenes; frames with a bone over the limit, not cut / fast)

| shot | before | after (session 1) |
|---|---|---|
| s010 | 17 (hands 109-281 mm, forearms to 147 deg, fingers 28-36 deg) | 0 (peak forearm 33 deg / f) |
| s020 | 9 (head 95 / 115, chest-carried arm 113 mm, hands 79 / 56) | 4 (hands only: auburn 48 / 79, boy 55 / 56 deg) |
| s030 | 0 (f93 cut, 3 characters, 1.1-1.6 m) | 0 (f93 cut) |

f101 in s010 is also a camera cut (the R touch started on it); the ramp fix removes its jump anyway.

## Goldens

3 of the interaction golden hashes change (exchange, e907 s010, e907 s010_calibrated); numbers per frame pending
(ROUND.md next 1). Not re-recorded.
