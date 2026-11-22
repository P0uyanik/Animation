# T-210 grasp / release finger curls under the per-frame limit (follow-up of T-198; state: ROUND.md)

## Cause (measured, `rows_t210.cpp`)

The contact search closes the fingers by the grasp weight `<who>/hand.<side>.grasp.weight`: 0 at contact - 4, 1 at
contact (interaction.cpp `keyClose`, actions.cpp reach), and opens them 1 at release, 0 at release + 5 (interaction.cpp
`release`: put down, hand-over giver; actions.cpp reach). The keys are clamped cubic (smoothstep): the middle step of a
4-frame ramp is 0.344 of the curl, of a 5-frame ramp 0.296. The boy's distal finger joints (f0b-f3b.R) turn ~92 deg
over the ramp: 31.7 deg / f closing (f contact - 2, - 1), 27.3 deg / f opening (release + 3); limit 25 deg / f at
24 fps (MotionLimits 600 deg/s, relative to the parent). e901 girl R (30 fps, limit 20): 31.7 closing, 22.8 / 26.7 /
21.6 opening.

## Fix (interaction.cpp, end of `finishInteractions`, after the T-198 orient pass)

For each generated grasp weight track (authored keys win) and each pair of neighbouring keys 0 -> 1 (close) or 1 -> 0
(open): the per-frame peak of that hand's finger bones over the ramp, on the pose as it plays back. Only when over the
limit, the ramp's flat-end key moves one frame at a time (close: earlier, over weight-0 frames; open: later), never past
another key, at most 8 frames, until the peak is under the limit (else the lowest found). The key keeps its value and
interpolation, so the ramp is the same ease over the longer span; every other key and every track under the limit is
bit for bit. Result: close at contact - 6, open at release + 6 (24 fps boy); contact - 7 / release + 7 (30 fps girl).
Same pattern as the T-198 touch curl (measured, only over the limit), but generic over all grasp weight ramps (grasp,
pick-up, reach, hand-over giver / receiver, put down) because they share one track.

## e901 boy walk start (hand.R 81 mm at f223, 1.01 x at 30 fps): left recorded

Not a curl ramp: the walk turns the body to its direction in 6 frames (actions.cpp walk: yaw keys start, start + 6;
0 -> 90 deg, 21.7 deg / f at f223); the hand at arm's length travels 81 mm. A fix would change the body yaw (every
bone), outside this task. The baseline row keeps the corrected cause.

## Ratchet

`tests/golden/continuity_baseline.json`: 125 rows -> 1 (the walk start). The test still fails on a new row or a grown
value (checked: mm 80.5 recorded -> "grew"; frame renamed -> "new snap"). New test case in
`tests/test_motion_continuity.cpp`: a visibleGrip-like grasp has no finger rows and its grasp weight is above 0 at
contact - 4.

## Goldens

15 of 20 `interaction_hashes.json` goldens change (fingers of the grasping hand only): [golden_delta.md](golden_delta.md).
Re-recorded after the R7 Supervisor's approval (main 694d4fa): `PLUSH_GOLDEN_WRITE=1 plush_tests -tc="golden*"`, checked
that exactly those 15 entries changed. `tests/test_verbs.cpp:710` (T-112b pinch: the 0 key of its grasp weight, over the
limit, moved from contact - 4 = 16 to 15; 0 rows after) pins the new key (write-set granted in the same decision).

## Evidence tools (not part of the gate)

- `rows_t210.cpp`: unexempt rows of one shipped scene (test cast) + track values / bone travel per frame.
- `golden_dump_t210.cpp`: every golden scene of test_bake_golden.cpp (its goldenScenes(), compiled in); `report` mode =
  rows per golden. Build lines in the headers.
