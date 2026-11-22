| golden scene | frames that differ | hands that differ | thumb joint, deg (max) | finger joint, deg (max) | fingertip, mm (max) | any other bone |
| --- | --- | --- | --- | --- | --- | --- |
| `content/scenes/eval/exchange/shot.scene.json` | 66 of 66 | boy L, girl R | 74.4 | 0.000 | 19.4 | 0.000 |
| `content/scenes/eval/handover/shot.scene.json` | 72 of 72 | boy L, girl L | 74.4 | 0.000 | 19.6 | 0.000 |
| `episodes/e901_clip_test/shots/s010/shot.scene.json` | 440 of 440 | boy L, boy R, girl L | 74.4 | 0.525 | 19.7 | 0.000 |
| `episodes/e905_props_test/shots/s010/shot.scene.json` | 72 of 72 | boy L, girl L | 74.4 | 0.000 | 19.6 | 0.000 |
| `episodes/e907_exchange/shots/s010/shot.scene.json` | 66 of 66 | boy L, girl R | 74.4 | 0.000 | 19.4 | 0.000 |
| `episodes/e907_exchange/shots/s010_calibrated/shot.scene.json` | 129 of 129 | boy L, girl R | 74.4 | 0.000 | 19.4 | 0.000 |

Thumb and finger joints are reported apart (round 2, 45 deg box-face lay-back; the same table as at 33 deg). The only
finger joint that moves, 0.525 deg in `e901_clip_test/shots/s010`, is the finger limit's back-flex bound (middle hinge
f<k>b never bent backwards). Two library clips hold the joint just past 0: `wave` at clip frame 26 (little finger f0b:
boy R at scene frames 36 and 256, girl L, mirrored, at 36; 0.525 deg) and `point` at clip frames 26-27 (index f3b: boy R
at 146-147; 0.300 / 0.282 deg). The finger tips move 0.04-0.07 mm. Accepted by the owner (~17:25 CET, 22 Nov) with the
6-golden update. Off-axis play and over-flex do not cause it: re-clamping with play 90 or middleFlex 180 gives the same angle.
