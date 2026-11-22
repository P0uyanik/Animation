# T-190 · Finger and thumb joint limits (engine, every hand path)

Branch `t-190-claude-finger-limits` from `origin/integration/t-187` `44f9fb3`. Owner report ~04:20 CET 22 Nov: in the
T-187 paper-boat test hand joints bend the wrong way, despite T-171 round 3. **Status: READY for review.** Design approved by
the Supervisor 12:11Z 22 Nov; the default change waits for the owner (section 6). Round file: `ROUND.md`.

## 1. Diagnosis (numbers)

Tool: `measure_t190.cpp` (`build_measure.sh`): for every character hand and every frame of a resolved shot, each digit
joint's rotation from rest as [flex, side, twist] in a frame built from the rest skeleton (flex > 0 = towards the palm,
flex < 0 = bent backwards). `summarize.py` lists the joints out of range (thresholds in its header) with the frames and
the driver of the hand at those frames, read from the hand tracks. Raw scans: `measures/before_*.jsonl.gz`; table:
`measures/before_table.md` / `.json` (T-187 scenes: rendered ranges only; e909 / e910: all frames).

| scene | where | joint | measured | driven by |
| --- | --- | --- | --- | --- |
| T-187 s020 (shots 3-4) | auburn girl, left hand, f49-176 (pick-up, carry, hand-over) | thumb end joint | -87.5 deg backwards, 87.5 deg sideways, up to +87.4; **flips by up to 175 deg from one frame to the next** (89 frames with a jump > 25 deg) | per-finger box-face grasp search |
| | same | thumb base | rolled 67 deg about its length; 59 frames with a jump > 25 deg (largest 133) | same |
| T-187 s020 (shot 4) | boy, right hand, f142-208 (receives the boat, holds it) | thumb base | -39 deg backwards, held | same |
| T-187 s030 (shot 5a) | all six hands, f92-93 (as `idle_relaxed` blends in before the cut) | thumb base | -25 deg backwards, rolled 61 deg (girls) | clip layer |
| T-187 s010 (shots 1-2) | - | - | none in the rendered range (thumbs of the pre-roll `idle_relaxed`, f1-14, are hidden) | - |
| e909 s010 | boy, right hand, f131-225 (receives the cup) | thumb base | -143 deg (turned round), rolled 76 deg; end joint 45 deg sideways | per-finger band grasp search |
| | same | three knuckles | 30-32 deg sideways | same (band spread search) |
| e909 / e910 s010 | every hand without a hand action, whole shot | thumb base | -31 deg backwards, girl rolled 75 deg; her end joint -19 .. -28 deg | clip layer (`idle_relaxed` base clip) |
| e910 s010 | both grasping hands (T-171 r3 `wrap`) | thumb base | -25 deg: the lay-back T-171 r3 reported (thumb in the palm's plane); nothing else | wrap search |

No finger joint bends backwards in T-187 (smallest finger flex 0.0 deg in all three scenes; e909: one knuckle -9 deg
from a clip). In T-187 every wrong-way joint is a thumb joint.

## 2. Cause: three code paths pose a hand, only one has a range

1. **Per-finger grasp search** (`engine/anim/animation.cpp` `applyHandPosePerFinger`, T-051 band / T-112c box face).
   The thumb is aimed anywhere on a half circle (0-180 deg round the object), curled from -48 to +80 deg and its end
   joint to 87.5 deg about an axis that is not its hinge; among near-equal solutions a different one wins each frame.
   T-171 r3's thumb range exists only in the `wrap` branch, and `engine/scene/interaction.cpp` keys `hand.<s>.wrap`
   only for round props (shape "wrap", line 1256): **on a box face the shot's `fingerClose.wrap` is dropped
   silently** (the boat is a box), and a `pass` receiver without `fingerClose` never has it (e909).
2. **Clip layers** (`applyClipFingers` -> `applyClipSample`). Clips carry finger and thumb tracks (`idle_relaxed`,
   gestures). The retarget lands the rest thumb of these rigs laid back and rolled; it is applied after the hand pose,
   unlimited. Hands with a hand action are not affected (the hand-pose system owns them).
3. **No joint limit anywhere.** `HandPose` clamps curl inputs to 0..1; the searches, clips, keyed bone rotations and
   the rigs' third finger segments have no range.

The keyed hand shapes and the single search bend the right way: checked on the boy's mesh (a Cycles hand study of
thumb 0 / 0.5 / 1, fist and opposition from two cameras; not kept, the poses are unchanged by this task).

## 3. Fix (system level; no shot, clip or content file changed)

| where | what |
| --- | --- |
| `engine/anim/animation.h` | `HandLimits` (the ranges below), `applyHandLimits(skeleton, pose, side)`, `HandPose::limits` (default on) |
| `engine/anim/animation.cpp` | the clamp (a joint inside its range is left bit for bit; outside, it is rebuilt from its clamped angles); called as the last step of `applyHandPose` (keyed shapes, single search, per-finger search, wrap); the per-finger grasp search (band / box face) solves its **thumb inside the range** with the wrap branch's thumb search (now one shared function, deterministic: equal contacts give the same pose every frame) and its finger search only sees poses inside the range; track `hand.<s>.limits` |
| `engine/scene/clip_layers.cpp` | the same clamp after the clip layers' finger pass (3 lines) |
| `tests/test_hand_limits.cpp` | new, 4 cases (not yet in `tests/CMakeLists.txt`: the Supervisor registers it) |

Ranges (degrees): knuckle flex -15..90, spread +-30; middle joint 0..110 and third segment 0..90 as hinges (8 deg of
play off the axis); thumb base opposition 0..60, abduction -20..30, flex -33..66 (33 back = as far as T-171 r3's wrap
lays the thumb beside the palm); thumb end joint 0..60 as a hinge.

**One switch:** track `<who>/hand.<s>.limits` with x = 0 turns all of it off for that hand (clamp, in-range thumb,
finger bounds, clip clamp): the poses before T-190, bit for bit. Absent = on.

## 4. Result (same scans, `measures/after_*`)

| scene | hand | before | after |
| --- | --- | --- | --- |
| T-187 s020 | girl L, grasp f49-176 | thumb end joint -87.5 back / 87.5 sideways, base rolled 67; 89 frames with a jump > 25 deg (largest 175) | every thumb joint in range; largest step of any digit joint 21.3 deg / frame (the close), 0 in the hold |
| T-187 s020 | boy R, grasp f142-208 | thumb base -39 back with 64 sideways | laid back 27 (inside the 33 limit), not sideways; largest step 18.8 |
| T-187 s030 | six hands, f92-93 | thumb base -25 back, rolled 61 | flexed forward 16, roll 11 |
| e909 s010 | boy R, grasp f131-225 | thumb base turned round (-143), 3 knuckles 30-32 sideways | laid back 25, knuckles inside 30 |
| e909 / e910 | free hands (idle clip) | thumb -31 back, rolled 75 | in range |
| e910 s010 | both T-171 r3 wrap hands | - | **unchanged: 0.0 deg on every joint, every frame** (also e909 girl L) |
| T-187 s010 | girl's touching hands (keyed shapes) | - | unchanged: 0.0 deg |

`measures/after_table.md` still lists 5 rows "bent backwards": all are the thumb laid back 25-27 deg beside the palm
(the lay-back the Supervisor ruled to keep), and 12 "pop" rows in T-187 s010: fingers of a keyed touch shape closing
28-36 deg in one frame (not a wrong-way bend, not a grasp, unchanged by this task; follow-up if wanted).

## 5. Sheets (Cycles 16 spp, 400x300 tiles, `closeup.py`; camera on the thumb side, from below, table left out)

| file | what |
| --- | --- |
| `sheet/before_after_T187_girl.jpg` | T-187 s020 f70 / f74 / f75 / f100, the girl's left hand on the boat. Before: the thumb stands out as a stub (f70, f74), is somewhere else one frame later (f75) and gone behind the hand at f100. After: the thumb lies under the fingers, the same in all four frames |
| `sheet/before_after_boy_clip.jpg` | row 1: T-187 s020 f180, the boy's right hand: before the thumb is bent back along the wrist, after it points forward under the boat. Row 2: e909 s010 f150, the boy's receiving hand: from this camera the thumb is behind the hand in both columns, the numbers carry this one (-143 -> -25 deg). Row 3: T-187 s030 f92, an idle-clip hand: before the thumb is rolled and laid back, after it lies forward beside the fingers |

## 6. Tests and goldens that move (nothing edited; needs Supervisor / owner approval)

Full suite on this branch: 259 cases, **251 pass, 8 fail** (56 assertions); with `tests/test_hand_limits.cpp`
registered locally its 4 cases pass (25,987 assertions). Input `44f9fb3`: all pass.

**Golden bake hashes** (`tests/golden/interaction_hashes.json`): 6 of 20 scenes change, the six content scenes. In all
six only the thumbs of clip-driven free hands move (`golden_delta.cpp`, limits on vs the switch off, `measures/golden_delta.md`):

| golden scene | frames | hands | digit joint, deg (max) | fingertip, mm (max) | any other bone |
| --- | --- | --- | --- | --- | --- |
| `content/scenes/eval/exchange` | 66 of 66 | boy L, girl R | 74.4 | 19.4 | 0 |
| `content/scenes/eval/handover` | 72 of 72 | boy L, girl L | 74.4 | 19.6 | 0 |
| `episodes/e901_clip_test/shots/s010` | 440 of 440 | boy L, boy R, girl L | 74.4 | 19.7 | 0 |
| `episodes/e905_props_test/shots/s010` | 72 of 72 | boy L, girl L | 74.4 | 19.6 | 0 |
| `episodes/e907_exchange/shots/s010` | 66 of 66 | boy L, girl R | 74.4 | 19.4 | 0 |
| `episodes/e907_exchange/shots/s010_calibrated` | 129 of 129 | boy L, girl R | 74.4 | 19.4 | 0 |

The 14 `test_interaction/*` goldens are unchanged.

**Assertions** (all are T-051 / T-112 / T-138 / T-157 criteria on the thumb of a per-finger grasp, written for the
thumb that could turn anywhere):

| test | assertion | was required | now |
| --- | --- | --- | --- |
| `test_hand_shapes.cpp:171` cup, both bands, 3 skeletons (x12) | thumb tip on the far side of the cup from the fingers | < 0 | 17-18 mm short of the far side: a thumb in range does not reach round an 80 mm cup (T-171 r3 found the same for the wrap) |
| `test_hand_shapes.cpp:170` (x8), `test_grasp_contact.cpp:134 / 157` (x6) | every tip inside the band | <= 0 | thumb 0.9-8.5 mm outside |
| `test_hand_shapes.cpp:168` (x4), `test_grasp_contact.cpp:140 / 207 / 216` (x7) | every tip within 2 mm of the surface | <= 2 mm | thumb 3.1-4.4 mm |
| `test_grasp_contact.cpp:139` (x4), `:226` (x3) | band fit pulls the contacts into a narrow band | by >= 1 mm | the thumb is the outermost contact and no longer moves |
| `test_hand_shapes.cpp:221` (x2), `test_verbs.cpp:886` (x2), `:1208` (x2): flat palm on a box face / tray | every tip within 2 mm of the face | <= 2 mm | thumb skin 4.6 mm into the face |

## 7. Decisions for the Supervisor / owner

1. **Default on?** With the default on, the 6 golden hashes and the assertions above have to be re-recorded / rewritten
   for an in-range thumb (thumb: in range, steady, tip as near as its range allows). With the default off nothing moves
   and shots opt in per hand; then T-187 stays wrong until its shots key the track.
2. **Thumb lay-back 33 or 45 deg.** A flat palm on a box face (tray, the boat's end) needs the thumb about 43 deg back
   to lie on the face: measured, with 33 the thumb skin is 4.6 mm in the face, with 40 it is 2.5 mm, with 45 the three
   box-face assertions pass (the wrap keeps its own 33 either way, so T-171 r3 stays unchanged). Shipped: 33, as ruled.
3. **Follow-ups, not in this write-set:** `engine/scene/interaction.cpp:1256` drops `fingerClose.wrap` on box faces
   (finger wrap, seat and `clear` are still not applied to boxes; only the thumb is fixed here); clip thumbs are in
   range now but not the authored relaxed curl (thumb reference of the clip retarget, `pipeline/clips/retarget.py`,
   `engine/model/clip.h`); the keyed touch shape's 28-36 deg / frame finger close in T-187 s010.

## 8. Commands
```
cmake --preset fast-dev && cmake --build build/fast-dev -j4
sh docs/evaluation/interaction/T-190/build_measure.sh
python3 pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/s020/shot.scene.json --blender <b> --stages prepare
(cd episodes/e912_paper_boat/shots/s020/build && ../../../../../build/fast-dev/measure_t190 shot.resolved.scene.json > joints.jsonl)
python3 docs/evaluation/interaction/T-190/summarize.py e912_s020=joints.jsonl --from-to e912_s020 41 208
build/fast-dev/apps/render-cli/plush-render <build>/shot.resolved.scene.json --bake bake.json
python3 docs/evaluation/interaction/T-190/closeup.py --bake bake.json --cast <build>/cast.json --scan joints.jsonl --hide table,stool \
    --tiles T187_s020_f070_girl_L=auburn:L:70:under --out out/after
python3 tools/review/shot_sheet.py docs/evaluation/interaction/T-190/sheet/sheet_girl.json
build/fast-dev/golden_delta "$PWD"      # build line in golden_delta.cpp
```
