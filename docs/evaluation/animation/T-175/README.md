# T-175 · Locomotion layer from CMU mocap (round 2: owner style review)

Brief: [`docs/tasks/T-175.md`](../../../tasks/T-175.md). Basis: [T-174 section 5](../T-174/README.md). Branch
`t-175-claude-locomotion`. Round file (targets, overrides, open defects, paths): [`ROUND.md`](ROUND.md).
**Status: CHECKPOINT, round 2. Stopped for the owner's review; nothing is wired into other shots (opt-in).**

## What to look at
| File | What |
| --- | --- |
| [`clips/walk.mp4`](clips/walk.mp4) | walk loop on the boy and the auburn girl, 3 s (three cycles), fixed side-on camera, floor stripes every 20 cm |
| [`clips/sit_stand.mp4`](clips/sit_stand.mp4) | stand, sit down on a stool, hold, stand up on the spot, stand (frames 104–225, 5.1 s) |
| [`sheet_r2.jpg`](sheet_r2.jpg) | the one sheet: full frame and a crop that follows each character, the same frames as the round 1 sheets (`sheet_boy.jpg`, `sheet_girl.jpg`, kept for comparison) |
| [`feet_lock.json`](feet_lock.json), [`feet_nolock.json`](feet_nolock.json) | feet numbers with and without the foot-lock |
| [`motion_checks_r2.json`](motion_checks_r2.json) | the popping / garment issues that are left, by part of the shot |

Renders are the review profile (Cycles, 640×360, 16 samples, H.264): for judging motion, not image quality. A cheap
preview (four frames at 8 samples) was checked first. Characters: boy 2.3.0 and auburn girl 0.14.0 (the current versions
after the R3 release; round 1 showed 2.2.0 / 0.13.0). The third girl is not in the shot (same shots as the checkpoint).

## Owner feedback (2026-11-21) and what changed
| Feedback | Change | Measured (review shot, engine bake) |
| --- | --- | --- |
| Walk: not bouncier, keep the up-down | root motion unchanged; hips travel 9.6 mm (boy) / 12.4 mm (girl) per cycle as before | the one-frame pelvis dips at toe-off (3–4 mm) are gone |
| Walk: softer, gentler footsteps | the foot's path and rotation are low-passed around landing and toe-off (`soft_step`), the knee no longer locks straight (`soft_knee`), 60 % of the foot's pitch (`foot_pitch`), planted soles flat (`foot_flat`) | ankle acceleration at a footfall 25–33 → 8.9 mm/frame² (test packages); no popping flag left on feet, toes, soles, ankles |
| Walk: feet sink slightly into the ground | `sole_floor`: no point of the shoe mesh goes under the ground; the review shot stands the characters on the floor | lowest shoe point −0.09 mm (round 1 style: toe up to 40 mm under its rest level, plus 27 / 30 mm from the package origin, see below) |
| Sit: upright 90° | `seat_lean` 0 while seated (20 % of the source lean on the way down / up) | seated trunk lean < 1° |
| Sit: hands at the sides | `seat_pose`: arms hang at the sides (30° from straight down, 12° elbow), head level | see sheet rows f150 |
| Stand-up: no ~90° turn, no extra step | `cmu_stand_up` is `cmu_sit_down` played backwards; `--no-turn` removes the hips' turn (the subject turns 33° while sitting down) | hips turn 0.14°, feet never leave their rest positions (0.1 mm) |
| Stand-up: the boy's legs intersect | `foot_home`: both feet stay on the character's own rest foot positions, the legs follow by IK | least knee gap 131 mm (boy), 110 mm (girl) on the test packages |
| Black hands at stand-up | the mocap clips carry no hand (wrist) roles (importer default; `--hands` keeps them) | preview and review frames: hands shaded normally |
| Popping flags on footfalls | soft step (above); arms: `--smooth-arms 2`, `arm_out` 25° in the walk | walk popping issues 75 (lock off) → 33; what is left: "Open" below |
| Garment under skin when seated | upright sit with level thighs | boy: no seated flag any more; girl's shorts: still −58 mm, garment side, outside this claim |

## Numbers
### Feet (`measure_feet.py`, frames where a foot_plant contact fully holds a foot)
| Character | Clip | Slide off → on | Planted ankle vs rest, off → on | Lowest shoe point vs floor, off → on |
| --- | --- | --- | --- | --- |
| boy | `cmu_walk` | 7.3 → 1.4 mm | +10.7..+18.3 → +0.0..+1.9 mm | −19.6 → −0.09 mm |
| boy | `cmu_sit_down` | 21.5 → 0.00 mm | +5.6..+16.1 → ±0.00 mm | −15.9 → +0.03 mm |
| boy | `cmu_stand_up` | 85.8 → 0.00 mm | +7.0..+42.4 → ±0.00 mm | −14.2 → +0.03 mm |
| girl | `cmu_walk` | 7.7 → 1.3 mm | +10.0..+18.5 → +0.0..+1.0 mm | −18.0 → −0.01 mm |
| girl | `cmu_sit_down` | 25.4 → 0.00 mm | −12.2..+9.3 → ±0.00 mm | −31.8 → −0.01 mm |
| girl | `cmu_stand_up` | 89.1 → 0.00 mm | −9.8..+39.3 → ±0.00 mm | −29.7 → −0.01 mm |
| **worst** | | **89.1 → 1.4 mm** (limit 3) | | **−31.8 → −0.09 mm** |

- The walk's planted ankles now rise up to 1.9 mm at the two ends of a plant (and slide up to 1.4 mm there): that is
  the soft step rounding the landing and the toe-off. Round 1 held 0.13 mm with a footfall that stopped in one frame.
- "off" = the same clips with `foot_lock` false (`shots/review_nolock`). With the lock off the sit / stand feet follow
  the source (which steps and turns); the reversed stand-up slides most.

### Motion check (`tools/motion_checks/run.py`, thresholds unchanged, nothing excluded)
| Part | Popping, lock off → on | Garment under skin, lock off → on |
| --- | ---: | ---: |
| walk (f1–98) | 75 → 33 | 1 → 17 |
| sit / stand (f104–230) | 44 → 46 | 4 → 4 |

- **Walk, what is left (33):** hair spring chains (`DYN-*`, hair meshes: 29) and the boy's trousers at the knee on
  toe-off (4: 9.8 mm/frame², ratio 0.49; limits 8 and 0.45). None on feet, toes, soles, ankles, shins or hands.
- **Sit / stand, what is left (46):** hair spring chains and hair meshes; hands and fingers when a clip hands over to
  or from the idle and when the arms settle (the arm-body clearance planner lifts clip-driven arms with a rate-limited
  profile: `engine/scene/interaction.cpp`, not a T-175 file); one blouse and one cuff vertex. None on legs or feet.
- **Garment, walk:** with the lock the pelvis sits 10–18 mm lower (planted feet on the ground instead of floating), so
  the legs bend more: boy trousers −16..−20 mm, girl shorts −28 mm (round 1 had the same kind of flags with the lock).
  **Garment, seated:** boy passes; girl shorts −58 mm (25 of 1032 sampled vertices), gusset −15 mm; boy trousers −12 mm
  only at the deepest bend on the way down / up. Not visible from the review camera. This is garment skinning at a
  deep hip bend (`pipeline/charsys/garments_v2/`), outside this claim; reported, not edited.

### Opt-in (existing shots unchanged)
- A clip without a `style` block takes the old code path (test "a clip without a style block is not touched").
- Full C++ suite: 249 of 249 test cases (774,597 assertions), `test_bake_golden.cpp` included.
- Engine bakes of existing shots, a build of `origin/main@30999cf` against this branch, byte for byte:

  | Shot | Frames | sha256 (both builds) |
  | --- | ---: | --- |
  | `e909_two_char_acting/s010` | 286 | `3b8317123f75a89a…` |
  | `e907_exchange/s010_verbs` | 129 | `a605f4e3469676e5…` |
  | `e908_boy_acting/s010` | 173 | `cfaac49b24405c9c…` |
  | `e901_clip_test/s010` | 440 | `4755202d7497e92a…` |

## Open (for the Supervisor / owner)
1. **Girl's shorts under the skin while seated** and the trousers / shorts flags in the walk: garment side, see above.
2. **The packages rest under their origin**: the lowest rest vertex of the shoes is 27.1 mm (boy 2.3.0) / 29.5 mm (girl
   0.14.0) under the character origin (the same in 2.2.0 / 0.13.0), so a character placed at floor height sinks by that
   in every shot. The foot-lock's ground is that rest sole level; the review shot raises the characters' scene position
   by it (`make_review_shot.py` `SOLE`). A package or scene rule is outside this claim. The girl's dark boot soles
   are visible now that the boots stand on the floor.
3. **Hand-over to other actions**: the idle and every other action stand on straight legs at the rest pose; the
   mocap clips keep a soft knee. The blend between them (8–10 frames in the review shot) covers it.
4. Walk arms: `arm_out` 25° gives the arms the clearance the wide torso needs (the clearance planner lifted them
   11–43° anyway); one number per clip if the owner wants them closer or further.
5. Not done, as in round 1: third girl, run / turn / idle clips, the walk action on clips, the pointer in
   `docs/ANIMATION_CLIPS.md` (outside this claim).

## How it works
### Importer (`pipeline/clips/import_bvh.py`, pure Python, no Blender)
```
python3 pipeline/clips/import_bvh.py --asf 35.asf --amc 35_01.amc --name cmu_walk --out content/clips/mocap \
    --loop auto --style walk --tempo 1.125 --smooth-arms 2 --source-id 35_01
python3 pipeline/clips/import_bvh.py --asf 14.asf --amc 14_32.amc --name cmu_sit_down --out content/clips/mocap \
    --frames 195:345 --origin-frame 345 --origin-feet --no-turn --style sit --seat 28:30 --source-id 14_32
python3 pipeline/clips/import_bvh.py --asf 14.asf --amc 14_32.amc --name cmu_stand_up --out content/clips/mocap \
    --frames 195:345 --origin-frame 345 --origin-feet --no-turn --reverse --style sit --seat 0:2 --source-id 14_32
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
- **Round 2 options:** the hand (wrist) roles are left out unless `--hands` (noisy in the source); `--no-turn` removes
  the hips' turn about the vertical frame by frame; `--origin-feet` puts the x/z origin between the ankles (a clip
  whose feet stay at home); `--reverse` plays the range backwards; `--smooth-arms N` low-passes the arm rotations
  (binomial, N frames); a preset with `foot_home` plants both feet for the whole clip.

### Style block (per clip, read by `engine/scene/clip_layers.cpp`; keys: `engine/anim/foot_lock.h`)
| Key | Meaning | walk | sit / stand |
| --- | --- | ---: | ---: |
| `lean` | share of the trunk lean kept (hips, spine, chest, neck; the turn about the vertical is kept; the thighs are compensated) | 0.6 | 0.2 |
| `seat_lean`, `seat_pose`, `seat_blend` | while the clip's `seat` contact holds: the lean share, and local rotations per role that replace the clip's; eased over `seat_blend` clip frames | – | 0, arms at the sides + head level, 14 |
| `head_level` | share of the remaining lean that the head undoes | 0 | 0.5 |
| `stride`, `tempo` | scale of the horizontal root motion; clock multiplier | 1.0, 1.125 | 1.0, 1.1 |
| `arm_swing`, `arm_out` | arm motion around the clip's mean arm pose; degrees the upper arms are turned outward (wide torsos) | 0.85, 25 | 1.0, 0 |
| `foot_lock`, `foot_in`, `foot_release` | the pin on `foot_plant` contacts and the clip frames over which it eases in and lets go | on, 2, 8 | on |
| `soft_step` | clip frames over which the locked foot's path and rotation are low-passed (landing, touch-down, toe-off) | 3.5 | – |
| `soft_knee` | share of the leg's length from which a pinned leg only approaches full stretch (the pelvis gives earlier, the knee does not lock and snap) | 0.94 | 0.94 |
| `foot_pitch`, `foot_flat` | share of the foot's pitch / roll kept; share of the rest removed while planted | 0.6, 1.0 | 1.0, 1.0 |
| `sole_floor` | no point of the shoe (the mesh the foot bone and its children carry) goes under the level of its lowest point at rest | on | on |
| `foot_home` | planted feet stand on the character's own rest foot positions and point as at rest | – | on |

**Timing against `content/timing/calibrated.timing.json`** (unchanged from round 1): the walk cycle is 24 frames
(`beat_interval`, a step every 12 frames); sit-down and stand-up take 28 scene frames each.

### Foot-lock (`engine/anim/foot_lock.{h,cpp}`, hook in `clip_layers.cpp`)
For a clip action whose clip has `"foot_lock": true`, every foot the clip plants gets a target (ankle position and
foot rotation) and two-bone leg IK onto it:
1. **Ground offset.** The clip's root is shifted vertically so that every plant begins with its ankle at the rest
   height (keyed per plant, interpolated). Not with `foot_home`.
2. **Locked foot.** While a plant holds, the ankle stays where it was when the plant began (or on the foot's rest
   position with `foot_home`); between plants it is the clip's own foot. The pin eases in and lets go.
3. **Soft step.** That locked path and the foot's rotation are low-passed over ±`soft_step` clip frames. A landing
   foot is behind the clip's own, never ahead, so the leg needs no extra reach.
4. **Sole.** The foot's pitch and roll are scaled and laid flat while planted; the ankle is raised by what a pitched
   shoe would sink (`sole_floor`, from the rest vertices the foot carries; cached per rig).
5. **Reach.** If the short leg cannot reach its target, the pelvis drops by the missing amount (softly with
   `soft_knee`) instead of the foot lifting off.
6. **Blends.** While the layer blends in or out the targets start from the foot of the layers under it, so a foot
   that stands still under both stays where it is.

Everything is evaluated from the frame number alone (no state), so any frame bakes identically on its own.

**Limits (known):**
- The pin is in character space: the character's own scene position and yaw must rest during a plant. Driving these
  clips along the `walk` action's path is not built (T-174 step 4); `engine/scene/actions.cpp` is unchanged.
- Only clip actions (tier 2) are styled and locked, not base clips.
- The ground is the level of the shoe's lowest rest vertex (see "Open" 2).
- The stools in the review shot are placed from a first bake (`make_review_shot.py --seat-from`).

## Tests
- `pipeline/clips/tests/test_import_bvh.py` (pure Python): round trip 0.00005°, limb directions 0.00003° (unchanged);
  new `test_options`: hands out by default, `--no-turn` (33.2° → 0°), `--reverse`, `--origin-feet`, `--smooth-arms`,
  `foot_home` plants and the seat pose; the library clips have no wrist roles.
- `tests/test_foot_lock.cpp` (9 cases): the round 1 cases; the round 2 keys, seat weight, swing lookup, tilt scaling,
  soft knee, `pinFootTo`; the walk on two packages (no shoe point more than 0.5 mm under its rest level; 60 mm / 12 mm
  with the round 1 settings; no ankle pop frame; footfall acceleration at most half of the unlocked clip's); sit down
  + stand up on two packages (feet within 0.5 mm of their rest positions, hips turn ≤ 1°, seated lean ≤ 1°, knees
  never cross, the stand-up starts on the sit-down's last pose, no wrist roles).

**Registration lines for the Supervisor** (files outside this claim, unchanged from round 1):
- `tests/CMakeLists.txt`: add `test_foot_lock.cpp` to the `plush_tests` sources.
- `tools/check_all.py` `check_python_tests`: add
  `[sys.executable, str(ROOT / "pipeline/clips/tests/test_import_bvh.py")],  # T-175 mocap importer`.

Rebuild the review shot: `python3 docs/evaluation/animation/T-175/make_review_shot.py [--seat-from <bake.json>]`, then
`pipeline/production/run_shot.py --shot docs/evaluation/animation/T-175/shots/review/shot.scene.json --profile review`.
