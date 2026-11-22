# T-190 · Finger and thumb joint limits (engine, every hand path)

Branch `t-190-claude-finger-limits` from `origin/integration/t-187` `44f9fb3`. Owner report ~04:20 CET 22 Nov: in the
T-187 paper-boat test hand joints bend the wrong way, despite T-171 round 3. **Status: diagnosis done, fix design sent
to the supervisor; no engine change yet.**

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

The keyed hand shapes and the single search bend the right way: checked on the boy's mesh (hand study, section 4).
