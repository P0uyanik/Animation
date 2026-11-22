# T-210 golden delta (numbers for the Supervisor before any re-record)

`golden_dump_t210.cpp` (every scene of tests/test_bake_golden.cpp goldenScenes(), every bone's world transform per
frame) on main `d0528dc` (before) and this branch (after), compared with `../T-198/golden_delta_t198.py`; rows from
`golden_dump_t210 report` (unexempt continuityReport rows, MotionLimits defaults).

15 of 20 goldens change, only in the right-hand finger bones of the character that grasps / lets go: f0a-f3a.R,
f0b-f3b.R, thumbA.R, thumbB.R (girl e901 only) and the DEF-f_*.03.R deform bones they carry (14 bones at most). No
other bone, character or frame. Max = largest difference of one bone's world rotation between the two builds at one
frame (the hand is partly closed / open where it was still open / closed before), control bones; mm = the DEF
fingertip bones. The 5 unchanged goldens (girl / engine packages, holdIntoBody/girl) had 0 rows before.

| golden | character | frames changed | max deg / mm | rows before (finger peak deg / f; hand.R in mm) | rows after |
|---|---|---|---|---|---|
| content/scenes/eval/exchange/shot.scene.json | boy | 13-17, 52-56 (10) | 56.7 / 11.6 | 20 rows; boy fingers 31.68 (20) | 0 rows |
| content/scenes/eval/handover/shot.scene.json | boy | 12-16, 52-56 (10) | 56.7 / 11.6 | 20 rows; boy fingers 31.68 (20) | 0 rows |
| episodes/e901_clip_test/shots/s010/shot.scene.json | girl | 239-244, 275-280 (12) | 74.2 / 13.6 | 25 rows; boy hand.R 80.98 (1); girl fingers 31.68 (24) | 1 rows; boy hand.R 80.98 (1) |
| episodes/e905_props_test/shots/s010/shot.scene.json | boy | 12-16, 52-56 (10) | 56.7 / 11.6 | 20 rows; boy fingers 31.68 (20) | 0 rows |
| episodes/e907_exchange/shots/s010/shot.scene.json | boy | 13-17, 52-56 (10) | 56.7 / 11.6 | 20 rows; boy fingers 31.68 (20) | 0 rows |
| episodes/e907_exchange/shots/s010_calibrated/shot.scene.json | boy | 25-29, 83-87 (10) | 56.7 / 11.6 | 20 rows; boy fingers 31.68 (20) | 0 rows |
| test_interaction/pickUpAndPlace/boy | actor | 15-19, 55-59 (10) | 56.7 / 11.6 | 20 rows; actor fingers 31.68 (20) | 0 rows |
| test_interaction/visibleGrip/boy | actor | 15-19 (5) | 56.7 / 11.6 | 16 rows; actor fingers 31.68 (16) | 0 rows |
| test_interaction/handover/boy_to_girl | giver | 13-17, 56-60 (10) | 56.7 / 11.6 | 20 rows; giver fingers 31.68 (20) | 0 rows |
| test_interaction/handover/girl_to_boy | receiver | 45-49 (5) | 56.7 / 11.6 | 16 rows; receiver fingers 31.68 (16) | 0 rows |
| test_interaction/holdIntoBody/boy | actor | 15-19 (5) | 56.7 / 11.6 | 16 rows; actor fingers 31.68 (16) | 0 rows |
| test_interaction/meetingPoint/boy_to_girl | giver | 13-17, 52-56 (10) | 56.7 / 11.6 | 20 rows; giver fingers 31.68 (20) | 0 rows |
| test_interaction/meetingPoint/girl_to_boy | receiver | 41-45 (5) | 56.7 / 11.6 | 16 rows; receiver fingers 31.68 (16) | 0 rows |
| test_interaction/sharedFollow/off | giver | 13-17, 57-61 (10) | 56.7 / 11.6 | 20 rows; giver fingers 31.68 (20) | 0 rows |
| test_interaction/sharedFollow/on | giver | 13-17, 57-61 (10) | 56.7 / 11.6 | 20 rows; giver fingers 31.68 (20) | 0 rows |

Content-scene grasp weight keys after (moved key only): exchange / e907 s010 close 0 at contact - 6 (was - 4), open 0
at release + 6 (was + 5); e901 girl (30 fps, finger limit 20 deg / f) close 0 at contact - 7, open 0 at release + 7.
