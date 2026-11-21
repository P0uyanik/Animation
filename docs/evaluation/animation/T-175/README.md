# T-175 · Locomotion layer from CMU mocap (first delivery for owner style review)

Brief: [`docs/tasks/T-175.md`](../../../tasks/T-175.md). Basis: [T-174 section 5](../T-174/README.md). Branch
`t-175-claude-locomotion`. **Status: CHECKPOINT. Stopped for the owner's style review before any wider use.**

## What to look at
| File | What |
| --- | --- |
| [`clips/walk.mp4`](clips/walk.mp4) | walk loop on the boy and the auburn girl, 3 s (three cycles), fixed side-on camera, floor stripes every 20 cm as a slide reference |
| [`clips/sit_stand.mp4`](clips/sit_stand.mp4) | sit down on a low stool, hold, stand up with a small step, 4.7 s (frames 104–215) |
| [`sheet_boy.jpg`](sheet_boy.jpg), [`sheet_girl.jpg`](sheet_girl.jpg) | one sheet per character: full frame and a crop that follows the character (walk cycle, sit, stand) |
| [`feet_lock.json`](feet_lock.json), [`feet_nolock.json`](feet_nolock.json) | feet-planted numbers with and without the foot-lock |

Renders are the review profile (Cycles, 640×360, 16 samples, H.264): they are for judging motion, not image
quality. Characters: boy 2.2.0 and auburn girl 0.13.0, the current versions on `origin/main`. **The third girl is not
included**: her released package (0.1.0) is not on `origin/main` yet (only spec candidates are), and the release branch
is outside this task.

## Defects visible in the clips (not fixed in this delivery)
- **The boy's hands render black during the stand-up** (from about frame 170; sheet rows f182 and f198). The clips
  drive the hand (wrist) role from CMU's wrist data, which is noisy; the likely cause is an extreme wrist twist. Not
  investigated further. Proposed fix for the next round: leave the hand roles out of the mocap clips' mask (or limit
  the wrist), then re-render.
- **The stand-up turns the characters about 90° and ends looking down**: the CMU subject steps away to the side
  while rising. This is in the source take (owner question 3).
- **Heads tilt down a little in the walk** (the subject looks at the floor ahead). `head_level` is 0 for the walk; it
  can be raised.
- The stools are small and mostly hidden behind the legs.

## Questions for the owner (style review)
1. **Walk:** is this the right amount of "real" for the plush characters, or should it be bouncier and more
   cartoon-like? The clip keeps 60 % of the adult's trunk lean and 85 % of the arm swing, and one cycle takes 24
   frames. All four are one number each in the clip (`lean`, `arm_swing`, `tempo`, `stride`).
2. **Sit / stand:** the adult bends far forward to sit on a low stool. The clip keeps 35 % of that lean and the head
   undoes half of the rest (`head_level`). More upright still, or fine?
3. **The stand-up ends with a small step forward** (every CMU stool take does). Keep it, or should I look for / cut
   a take that stays on the spot?
4. **Footfalls:** the walk's feet stop within one or two frames, as real footsteps do. The popping check flags
   that (with and without the foot-lock, see below). Accept it as the nature of a walk, or soften the landings?

## Result against the acceptance criteria
| # | Criterion | Result |
| --- | --- | --- |
| 1 | Importer | `pipeline/clips/import_bvh.py`: CMU role maps (ASF/AMC and BVH names), folded spine and neck joints, 24 fps, licence + attribution in each clip, `contacts.foot_plant` filled. Tests: round trip 0.00005°, limb directions 0.00003° |
| 2 | Starter clips | `content/clips/mocap/`: `cmu_walk` (loop), `cmu_sit_down`, `cmu_stand_up`, CMU only, with [`ATTRIBUTION.md`](../../../../content/clips/mocap/ATTRIBUTION.md). No run, turn or idle clip yet (see "Not done") |
| 3 | Foot-lock + style filter | two-bone leg IK pin on `foot_plant` frames; per-clip `style` block read by `clip_layers`. **Slide while planted 0.13 mm** (limit 3 mm; 35.4 mm without the lock). Popping: the lock adds none; the walk's own footfalls are flagged either way |
| 4 | Opt-in only | a clip without a `style` block takes the old code path; the full C++ suite with the bake goldens passes; existing shots bake byte-identical to `origin/main` (section "Opt-in") |
| 5 | First delivery | this folder. Boy and auburn girl; third girl not possible here |

## Feet-planted numbers (current boy 2.2.0 and girl 0.13.0, review shot)
Measured from the engine bake by [`measure_feet.py`](measure_feet.py) on the frames where a clip's `foot_plant` contact
fully holds a foot. Slide = the ankle's worst horizontal distance from where its plant began. Height = planted ankle
height against the character's own rest ankle height (+ floating, − sinking).

| Character | Clip | Slide, lock off | Slide, lock on | Height, lock off | Height, lock on |
| --- | --- | ---: | ---: | --- | --- |
| boy | `cmu_walk` | 7.3 mm | 0.06 mm | +10.7 .. +18.3 mm | -0.00 .. +0.00 mm |
| boy | `cmu_sit_down` | 23.6 mm | 0.00 mm | +6.2 .. +15.0 mm | -0.00 .. +0.00 mm |
| boy | `cmu_stand_up` | 35.4 mm | 0.13 mm | +9.2 .. +17.6 mm | -0.01 .. +0.70 mm |
| girl | `cmu_walk` | 7.7 mm | 0.10 mm | +10.0 .. +18.5 mm | -0.00 .. +0.00 mm |
| girl | `cmu_sit_down` | 27.3 mm | 0.00 mm | -11.8 .. +11.7 mm | -0.00 .. +0.00 mm |
| girl | `cmu_stand_up` | 20.6 mm | 0.10 mm | -10.4 .. +18.5 mm | -0.02 .. +0.69 mm |
| **worst** | | **35.4 mm** | **0.13 mm** | **-11.8 .. +18.5 mm** | **-0.02 .. +0.70 mm** |

- **Floating before:** up to +18.5 mm (7 % of the leg) and −11.8 mm. The source's rest pose has splayed legs and adult
  hip proportions, so "hips above ankles" in leg lengths does not carry over exactly.
- **After:** every plant begins at the rest ankle height and stays within 0.13 mm of where it landed.
- **Popping** (`tools/motion_checks/run.py` on the same two bakes, issues outside the camera cut):

  | | Walk | Sit / stand |
  | --- | ---: | ---: |
  | lock off | 48 | 48 |
  | lock on | 41 | 46 |

  The lock adds no popping. **The "no popping" criterion is not met by the check's own rule on the walk:** the
  flagged walk issues are the footfalls (shoe soles and toes stop within one or two frames at this pace) and they are
  there without the lock too. The sit / stand issues are hair and hand follow-through at the seat contact and during the
  step, also the same without the lock. Nothing was excluded or re-thresholded; this is owner question 4.
- **Garment check:** the same run reports trousers / dress vertices under the skin while seated (worst −38 mm, limit
  −5 mm) and at full stride. This is the known rigid-hip limit of the packages with deep leg bends
  (ANIMATION_CLIPS §9, T-174 risks), present with and without the lock. It needs the garment / rig side and is not
  changed here; please look at the hips and knees in `sit_stand.mp4`.
- The review shot uses `"animPrinciples": false` (plain clip clock) so that the script can map scene frames to clip
  frames exactly. The lock itself does not depend on that setting, but its numbers under eased clocks are not
  measured here.

## How it works
### Importer (`pipeline/clips/import_bvh.py`, pure Python, no Blender)
```
python3 pipeline/clips/import_bvh.py --asf 35.asf --amc 35_01.amc --name cmu_walk --out content/clips/mocap \
    --loop auto --style walk --tempo 1.125 --source-id 35_01
python3 pipeline/clips/import_bvh.py --asf 14.asf --amc 14_32.amc --name cmu_sit_down --out content/clips/mocap \
    --frames 195:345 --style sit --seat 26:30 --source-id 14_32
python3 pipeline/clips/import_bvh.py --asf 14.asf --amc 14_32.amc --name cmu_stand_up --out content/clips/mocap \
    --frames 660:900 --origin-frame 195 --style sit --seat 0:2 --source-id 14_32
```
(each with the `--description` stored in the clip). Sources are the official files from
`http://mocap.cs.cmu.edu/subjects/<nn>/`; they are not stored in the repository.
- **Same retarget math as every other clip** (`retarget.py`, ANIMATION_CLIPS §8): limb directions transfer exactly to
  any proportions.
- **Folding:** CMU has `lowerback` between the hips and the spine, and two neck joints. The folded role keeps its own
  joint's twist and is swung to point exactly at the next pivot. T-174 measured 11–50° hips and 8–17° neck error
  without this; now 0°.
- **Heading and ground:** the take is turned to face (a loop: to travel along) +Z. Root height is measured from the
  lowest ankle of the take.
- **Loop:** `--loop auto` finds the best gait cycle and spreads the small seam mismatch over the cycle. The clip
  carries `root.cycle_offset`, so the walk travels.
- **Contacts:** a foot is planted where its ankle is within 2 % of a leg length of its lowest height and nearly
  still. A plant across a loop's seam is one contact whose end runs past the last frame.
- **Sloped takes:** `x_mocap.plant_height_spread` records how level the plants are. CMU 07_01 (used by T-174) turned
  out to walk up a slight slope (0.03 leg lengths per step); 35_01 is level (0.008) and replaced it.
- Also reads BVH (`--bvh`, `--rest-frame`) with the cgspeed joint names.

### Style block (per clip, read by `engine/scene/clip_layers.cpp`)
```
"style": {"version": 1, "preset": "sit", "lean": 0.35, "head_level": 0.5, "stride": 1.0, "arm_swing": 1.0,
          "tempo": 1.1, "foot_lock": true, "foot_lead": 5, "foot_release": 10}
```
| Key | Meaning | walk | sit / stand |
| --- | --- | ---: | ---: |
| `lean` | share of the trunk lean kept (hips, spine, chest, neck; the turn about the vertical is kept; the thighs are compensated so the legs keep their directions) | 0.6 | 0.35 |
| `head_level` | share of the remaining lean that the head undoes, so a big head stays up | 0 | 0.5 |
| `stride` | scale of the horizontal root motion. Root motion is stored in leg lengths, so 1 already means "the source's stride in this character's own leg lengths" | 1.0 | 1.0 |
| `arm_swing` | scale of the arm motion around the clip's mean arm pose (`arm_center`) | 0.85 | 1.0 |
| `tempo` | clock multiplier | 1.125 | 1.1 |
| `foot_lock`, `foot_lead`, `foot_in`, `foot_release` | the pin, and the clip frames over which it eases in before / into a plant and lets go after it | on, 3, 2, 6 | on, 5, 2, 10 |

**Timing against `content/timing/calibrated.timing.json`:** the references show no locomotion, so the clips are
set on the calibrated beats instead of on real-time mocap.
- Walk: one cycle is 27 clip frames; `tempo` 1.125 makes it **24 frames = `beat_interval`** (one stride per primary
  beat, a step every 12 frames). At that pace the boy covers 0.42 m per second.
- Sit down: the hips' main drop takes 13 frames (`settle` 12, `reach` 16); the whole clip 28 frames.
- Stand up: the main rise takes 16 frames (`reach` 16); with the step, 45 frames.

### Foot-lock (`engine/anim/foot_lock.{h,cpp}`, hook in `clip_layers.cpp`)
For a clip action whose clip has `"foot_lock": true`:
1. **Ground offset.** For each plant, the height its ankle misses the rest ankle height by is keyed at the plant's
   start and interpolated between plants. The clip's root is shifted by that. This removes the floating.
2. **Pin.** While a plant holds, the ankle stays where it was when the plant began (two-bone leg IK; the foot keeps
   its own orientation). The pin eases in over the landing and lets go over `foot_release` frames.
3. **Reach.** If the short leg cannot reach its pinned ankle (late in a stance), the pelvis drops by the missing
   amount instead of the foot lifting off.
4. **Floor.** No ankle goes under its rest height.

Everything is evaluated from the frame number alone (no state), so any frame bakes identically on its own.

**Limits (known):**
- The pin is in character space: the character's own scene position and yaw must rest during a plant. A clip that
  walks by its own root motion (as here) is fine. Driving these clips along the `walk` action's path is not built
  (T-174 step 4); `engine/scene/actions.cpp` is unchanged.
- Only clip actions (tier 2) are styled and locked, not base clips.
- A hand-over between two clips is a normal blend; the lock does not span it. `cmu_stand_up` starts where
  `cmu_sit_down` ends (same take, same origin), and the seated clip must stay at full weight until the stand-up
  has blended in (see `make_review_shot.py`).
- The stool height in the review shot comes from the clip's `seat` contact, whose `height_ratio` is an estimate
  (seat top 0.2 leg lengths under the seated hip pivot).

## Opt-in (existing shots unchanged)
- No existing clip has a `style` block; `clip_layers.cpp` reads it only for clip actions, and without it the
  sample, the root and the clock are computed exactly as before.
- Full C++ suite: 246 of 246 test cases pass (774,507 assertions), with `tests/test_bake_golden.cpp` and the new `test_foot_lock.cpp` (registered locally only, see below).
- Byte comparison of engine bakes (`plush-render --bake`), a build of `origin/main@80e7620` against this branch, on
  the same resolved scenes: **identical in all four**.

  | Shot | Frames | Bake sha256 (both builds) |
  | --- | ---: | --- |
  | `e909_two_char_acting/s010` | 286 | `6fb630081d7f40d5…` |
  | `e907_exchange/s010_verbs` | 129 | `73318de52e4a6b50…` |
  | `e908_boy_acting/s010` | 173 | `e77ab85fbac64d64…` |
  | the actions of `e901_clip_test/s010` on the current cast (a temporary copy: clips, mirror, base idle, walk, reach, `sit_down` / `stand_up`) | 440 | `6dec1bb8f497e9a4…` |
- Python: `test_import_bvh.py` and `test_clip_files.py` pass. Shared-systems lint, write-set and doc links pass.

## Tests
- `pipeline/clips/tests/test_import_bvh.py` (pure Python): BVH round trip of `dense_test` (17 roles × 120 frames,
  worst 0.00005°) and its 24 fps resample; a synthetic ASF/AMC take with the extra CMU joints played on a chibi
  skeleton (12 roles, worst 0.00003°, folded hips and neck included); contacts, ground and loop on a synthetic gait;
  every library clip validated, licensed and listed in `ATTRIBUTION.md`.
- `tests/test_foot_lock.cpp`: style parsing, lean with leg compensation, head level, arm swing, stride; plant lookup
  (loop seam, ease-in, release); the pin; the three CMU clips on the two test packages (slide ≤ 3 mm, ankles within
  3 mm of rest height, no added popping); a neutral style block equals no block bit for bit.

  | Test packages (boy 1.0.0 / girl m3) | Slide off → on | Planted ankle vs rest, off → on |
  | --- | --- | --- |
  | `cmu_walk` | 9.6 / 9.2 mm → 0.06 / 0.07 mm | +11..+17 mm → ±0.002 mm |
  | `cmu_sit_down` | 35.9 / 43.0 mm → 0.002 / 0.001 mm | −12..+17 mm → ±0.0002 mm |
  | `cmu_stand_up` | 52.9 / 57.6 mm → 0.12 / 0.09 mm | −13..+18 mm → −0.03..+0.5 mm |

**Registration lines for the Supervisor** (files outside this claim):
- `tests/CMakeLists.txt`: add `test_foot_lock.cpp` to the `plush_tests` sources.
- `tools/check_all.py` `check_python_tests`: add
  `[sys.executable, str(ROOT / "pipeline/clips/tests/test_import_bvh.py")],  # T-175 mocap importer`.

## Not done / open
- **Third girl:** see the top.
- **Run, turn, idle:** not included. A run take (35_17) imports and loops, but its stance is too short for the plant
  detector as tuned for walking, so it would play without a lock; it is left out rather than shipped half-done.
- **Walk action on clips** (T-174 step 4): not built; see the limits.
- **`docs/ANIMATION_CLIPS.md`** (sections 8 and 9 say mocap conversion and foot-lock are "not implemented") is outside
  this claim and still needs a pointer to this work.
- The review shot is evaluation material, not an episode shot. Rebuild it with
  `python3 docs/evaluation/animation/T-175/make_review_shot.py` and `pipeline/production/run_shot.py`.
