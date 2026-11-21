# T-171: hands round 2 and 3: finger separation, pre-shape, finger-by-finger close, soft contact, grip

Branch `t-171-claude-hands-r2`. Round 3 input `origin/main` `7135087` (boy 2.3.0 / girl 0.14.0 CURRENT).
Status: **CHECKPOINT (round 3)**: candidates for owner review. Nothing is on by default. Round file: `ROUND.md`.

## Round 3 (owner review 2026-11-21): owner summary
- **What was wrong, measured on the boy's own mesh** (not on the solver's finger model, as round 2 did):
  the palm sat 9.6 mm inside the cup; the thumb was turned 138 deg from rest (178 deg on the proposed site) with its
  second joint bent 75 deg backwards: this is the "bends the wrong way"; only two of the three finger joints ever moved
  (the last, longest segment stayed straight: the "too open"); the hand was thumb down with the forearm twisted
  124 deg against it; on the way in 5-13 mm of the hand passed through the cup.
- **What is fixed, as three new opt-in keys inside `fingerClose`** (section R3.1): the palm no longer enters the cup
  (0.0 mm), nothing enters it on the way in (0.0 mm), the thumb stays in its natural range (36 deg from rest, laid
  back 23 deg, never turned round), every finger bends in all three joints and rests on the cup with its pad.
- **Thumb up is possible, but it hides the hand in this shot.** With the right hand thumb up at the boy's side his
  forearm comes between the shot camera and the hand. So there are two fixed variants in the clip: **authored grasp
  point (hand visible, thumb down)** and **thumb up (hand mostly hidden)**. Your choice, or a staging change.
- **Not fixed:** the fingers do not reach further round the cup than before (they reach less far: the cup no longer
  sinks into the palm); the carry after the pick-up with the thumb-up variant (wrist bends up to 93 deg, section R3.5).
- **Decisions for you:** section R3.6.

### R3.1 The new keys (all inside `"fingerClose": {...}`, each off unless given)
| key | effect |
| --- | --- |
| `"wrap": true` | fingers: all joints flex together into an arch until the finger touches (the rig's own third finger segment included), then the joints beyond the touching segment go on; skin thickness measured on the character's mesh (boy: finger 10.8 mm, thumb 11.8 mm; the skeleton guess was 13.0). Thumb: searched inside its range only (opposition, abduction -20..30 deg, flexion; laid back at most 33 deg where the cup needs the room). Palm: the cup rests where the palm ends and the fingers begin, as far off the hand as the palm's measured surface needs for this cup radius (tracks `hand.<s>.wrap`, `hand.<s>.seat`) |
| `"grip": "natural"` | upright round props: the grasp point turns about the prop's axis by the smallest angle at which the hand takes it thumb up with the fingers within 30 deg of the forearm for some allowed elbow, and that elbow is keyed (track `<who>/elbow.<hand bone>`). The asset is not changed (a turned socket in the scene's copy, as `visibleGrip` does) |
| `"clear": metres` | the way in: the hand rises with its palm towards the prop and its fingers hanging, then swings the fingers level in the palm's own plane; where digits or palm still come closer than `clear`, the wrist moves out. The contact is unchanged |

`fingerClose: true` is still exactly round 2 (same held grasp). The solver changes are one new branch
(`HandPose::wrap`); without the track the hand pose is the old code path.

Files: `engine/anim/animation.h/.cpp` (wrap search, track), `engine/scene/interaction.cpp` (keys, mesh measures, seat,
natural grip, elbow track, clear), `engine/scene/verbs.cpp` (the palm check follows a turned grasp point),
`tests/test_grasp_contact.cpp` (2 new cases). `hand_shape.*`, `collision.cpp`, `actions.cpp`, `clip_layers.cpp`, content,
CMake files and assets: not changed.

### R3.2 Variants (e910 s010, boy R picks up the cup, contact f76)
| variant | what |
| --- | --- |
| `base` | the current default |
| `r2site` | round 2: `fingerClose` + rest hand on the proposed cup site (the column the owner preferred) |
| `r3site` | `r2site` + `wrap` + `clear 0.006`: authored grasp point, so the planner still turns the hand **thumb down** |
| `r3` | `r3site` + `grip natural`: **thumb up** |

The proposed cup site is a copy under the build folder (socket `grip` at 50 mm, band 0-100 mm); `content/assets` is unchanged.

### R3.3 Numbers (`measure_t171`, `measures/r3_*.json`, table from `summarize_r3.py`)
Every vertex the hand bone or a bone below it carries, against the cup as a capped solid (stricter than the open cup).

| variant | thumb side at hold | deepest in the cup on the way in f50-75, mm (palm / thumb / fingers) | deepest in the cup held f84, mm (palm / thumb / fingers) | thumb turned from rest, deg | least joint bend, deg (negative = backwards) | index joints held, deg | fingers off the cup held, mm (largest) | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold f84, deg | wrist bend in the carry f100-135, deg (largest) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | down | 7.8 / 4.2 / 5.0 | 9.6 / 0.0 / 0.4 | 138 | -18 | 24, 30, 0 | -0.2 | 74, 76, 77, 78, 79 | 14 | 10 / -124 | 57 |
| r2site | down | 7.9 / 0.0 / 12.6 | 9.6 / 0.0 / 0.3 | 178 | -75 | 24, 31, 0 | -0.1 | -, 76, 77, 79, 80 | 28 | 8 / -127 | 53 |
| r3site | down | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | -23 | 14, 8, 6 | -0.1 | 76, 76, 76, 78, 80 | 4 | 20 / -120 | 58 |
| r3 | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | -23 | 14, 8, 6 | -0.1 | 76, 76, 76, 78, 80 | 4 | 45 / -74 | 93 |

- **In the cup:** default palm 9.6 mm held and up to 7.8 / 4.2 / 5.0 mm (palm / thumb / fingers) on the way in.
  r3site and r3: 0.0 on the way in; held palm 0.0, thumb 0.8, fingers 0.2 mm (the search tolerance).
- **Wrong way:** thumb 138 -> 36 deg from rest. The -23 deg left is the thumb laid back into the palm's plane (the cup is
  wider than the hand is long); no finger joint is negative.
- **Closed:** index joints 24 / 30 / 0 deg -> 14 / 8 / 6 deg. Smaller angles, but all three joints, and the pads lie on
  the cup instead of a straight last segment pointing past it.
- **Wrist:** the default's hand is in line with the forearm (10 deg) but twisted 124 deg; r3 (thumb up) halves the twist
  (74 deg) and bends 45 deg. 30 deg was the target; the body is in the way of the elbow that would give it.
- **Hand-over later in the shot** (hands apart, boy R - girl L, `--pair`): default 62 mm, r3site 70 mm, r3 18 mm at the
  nearest (25 mm at the contact f114). No hand meets the other. No load warning in any variant.

### R3.4 Sheets and clips
PICTURES

### R3.5 Limits
- **Carry with `r3`:** the elbow is planned for the contact pose. In the carry and the hand-over (f100-135) the wrist
  bends up to 93 deg (default 57) and the elbow rises above the shoulder. A per-frame elbow plan for carry / pass is
  the next step; the carry lives in `actions.cpp` (T-175's file).
- **Reach of the fingers:** the boy's fingers are 35 mm long from the knuckle, the palm is 23 mm thick, the cup is
  80 mm wide and as tall as the hand. Without the palm sinking in, the fingers cover about 40 deg of the cup.
- **Staging:** the hanging hand starts under the table edge, the cup is 18 cm from the shoulder of a 27 cm arm, 5 cm
  from the table edge, beside a wide body. Every grip here is cramped; this is not something the hand planner can undo.
- `grip natural` was measured in e910 only. In the unit-test scene it gives thumb up with a wrist bend of 84 deg:
  where no allowed elbow gives a straight wrist it still turns the hand up.
- Girl: the old test package keeps 2.7 mm of the thumb in the cup with `wrap` (3.2 mm without). Girl 0.14.0 was not
  rendered; the hand-over receiver uses the same keys.
- The mesh is unchanged (released boy 2.3.0).

### R3.6 Decisions and recommendations
1. **Which fixed variant:** `r3site` (hand visible, thumb down, all contact fixes) or `r3` (thumb up, hand mostly
   hidden, carry not solved). Recommendation: `r3site` now; thumb up together with a staging change (cup in front of
   the boy, further from him), then `r3` needs no forward elbow.
2. **`wrap` and `clear` as part of `fingerClose`'s defaults** once you have seen the clip: recommended for `wrap` (it
   removes the palm in the cup and the turned thumb on every wrap grasp); `clear` after a second shot.
3. **Cup site** (socket 50 mm, band 0-100 mm): still recommended; still a content change for you to approve.
4. **T-157 (a):** unchanged from round 2: not recommended as the default.
5. Follow-ups: per-frame elbow for carry / pass; a "press" depth so the plush palm gives and the fingers reach
   further; `planArmLift` popping in sit / stand (reported by T-175, not looked at here).

### R3.7 Tests and default path
- Default path: e910 s010 bake (192 frames) from a clean `origin/main` `30999cf` build and from this branch: sha256
  `b72f987116cec18d...` on both (main `7135087` changes no engine file).
- `plush_tests`: 245 cases pass (2 new). New: bad values are load errors; `wrap` keys the tracks, the palm's grip point is
  on the socket, no hand vertex deeper than the limit (boy 19.4 -> 0.0 mm, girl 3.2 -> 2.7 mm), thumb turned 135 -> 34
  and 153 -> 32 deg, no finger joint backwards; `grip natural` turns a thumb-down grasp thumb up and keys the elbow,
  `"site"` leaves every key as it was; `clear` adds the waypoint, is never deeper in the cup on the way in and keeps
  the contact.
- No golden, threshold or existing test was changed.

---
# Round 2 (2026-11-20/21, superseded where round 3 says so)

## Owner summary
- **What you can switch on:** one key on a grasp, `"fingerClose"`. The hand then opens and takes the cup's shape on the
  way in, the fingers land one after the other (index first, little last) and each one slows down before it touches.
- **Motion is better, the held hand is not:** see the sheets (section 4). On today's cup site the opt-in hand still
  looks fused, and the rest hand hardly changes.
- **What it does not fix by itself:** the fingers still overlap on the cup with today's cup grasp site, with or without
  the T-157 wider band. The boy's hand is as tall as the cup (four fingers need 104 mm, the cup is 100 mm, the site's
  band is 45 mm). They stop overlapping only when the hand is centred on the cup (column "proposed site" in the sheets).
- **Decisions for you** (section 6): (1) keep `fingerClose` as an opt-in candidate or make it the verb default;
  (2) T-157 option (a) as default: **not recommended** as it stands; (3) the cup grasp site change; (4) two findings
  that were there before this task (thumb-down grip, the hand grazing the cup on the way up).

## 1. The opt-in
Action key `"fingerClose": true | {...}` on `reach` / `grasp` / `place` / `handover` and on the verbs `pick_up`, `pass`,
`place` (passed through). Absent or `false`: every generated key is as before. Only keys change; the hand solver
(`engine/anim/animation.cpp`) is untouched.

| key | default | effect |
| --- | --- | --- |
| `preshape` | 0.5 | grasp weight held during the reach: each finger goes part of the way from the open pose to its contact pose, so the open hand already has the object's shape (0 = off) |
| `stagger` | 2 | frames between fingers landing, index first; opening runs the other way (T-051 track `hand.<s>.stagger`) |
| `close` | 6 | frames of the final close, ending at contact for the index (at most half the reach) |
| `settle` | [0.12, 3] | soft contact: the last 12 % of the close takes 3 frames. The weight never passes 1, so a finger cannot press into the prop |
| `widen` | – | [lo, hi] metres: keys the T-138 band fit and the T-157 (a) wider band on a banded grasp |
| `rest` | – | a hand-shape pose for the hand before the reach and after the release (e.g. a curl cascade that tells the fingers apart) |

The stagger reads every finger's pose late (the little finger 3 steps), so with the opt-in the open hand is keyed that
much earlier: the little finger opens when the hand opened before and the others lead it.

Files: `engine/scene/interaction.cpp` (keys), `engine/scene/verbs.cpp` (3 pass-through lines),
`tests/test_grasp_contact.cpp` (3 new cases). `hand_shape.*`, `collision.cpp`, `animation.*`, `actions.cpp`,
`clip_layers.cpp`, content and CMake files: not changed.

## 2. Variants (e910 s010, boy R picks up the cup: reach f62, contact f76)
`make_variants.py` on run_shot's resolved scene:

| variant | what |
| --- | --- |
| `base` | the current default |
| `t157a` | T-157 (a) alone: band 40-95 mm, old timing |
| `r2` | `fingerClose: true` |
| `r2a` | `r2` + `widen [0.005, 0.005]` (T-157 a) |
| `r2s` | `r2a` + the separated rest hand (`rest`) |
| `r2site` | `r2` + rest hand on a **copy** of the prop library with the proposed cup site: socket `grip` at 50 mm (now 66), band 0-100 mm (now 45-90). The copy is under the build folder; `content/assets` is unchanged |

## 3. Numbers (`measure_t171`, `measures/`, table from `summarize.py`)
The cup is taken as a capped solid cylinder (stricter than the real open cup). Skin radius 13 mm (half the finger-root
spacing). Digits: thumb, then index..little by anatomy.

| variant | lands at frame (thumb, index..little) | largest curl step, deg/frame (thumb / fingers) | held fingertips apart, mm (i-m, m-r, r-l) | held tip gap, mm | min skin clearance in the close f69-100, mm | approach graze f58-68, mm | tip heights held, mm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | 74, 76, 77, 78, 79 | 47 / 14 | 28.0, 8.5, 28.1 | 0.00 | -5.01 | -6.98 | 44, 34, 62, 71, 98 |
| t157a | 74, 76, 77, 78, 79 | 65 / 21 | 19.9, 17.7, 19.6 | 0.00 | -5.01 | -6.98 | 41, 41, 59, 76, 94 |
| r2 | 76, 76, 77, 79, 80 | 20 / 5 | 28.0, 8.5, 28.1 | 0.00 | -0.57 | -7.32 | 44, 34, 62, 71, 98 |
| r2a | 76, 76, 77, 79, 80 | 23 / 9 | 19.9, 17.7, 19.6 | 0.00 | -0.00 | -7.32 | 41, 41, 59, 76, 94 |
| r2s | 76, 76, 77, 79, 80 | 23 / 9 | 19.9, 17.7, 19.6 | 0.00 | -0.00 | -8.30 | 41, 41, 59, 76, 94 |
| r2site | 76, 76, 77, 79, 81 | 26 / 4 | 24.9, 24.8, 25.0 | 0.00 | -0.00 | -13.79 | 13, 13, 38, 62, 87 |

Reading it:
- **Finger by finger:** the fingers land over 4-5 frames (before: 3), the thumb with the index instead of 2 frames ahead.
- **No pop:** the largest joint step per frame drops from 47° to 20° (thumb) and 14° to 5° (fingers) in `r2`.
- **No penetration:** held tip gaps are 0.00 mm in every variant. During the close nothing goes deeper than -0.6 mm
  (`base` and `t157a`: -5.0 mm). `clear` excludes the digit roots; the thumb root sits
  5.0 mm inside the skin margin in every variant (wrist placement, as reported in T-157).
- **Separation in the grasp:** fingertips 26 mm apart is side by side. `base` has two fingertips 8.5 mm apart (overlap),
  T-157 (a) 17.7-19.9 mm (still overlapping by 6-8 mm), the proposed site 24.8-25.0 mm.
- **Approach graze (was there before):** on the way up from the side of the body the little finger passes 7 mm inside
  the cup's volume at f65-66 in `base`. The opt-in does not make the default site worse by more than 1.3 mm; the lower
  proposed site makes it 13.8 mm. This is the reach path, not the fingers.

## 4. Sheets and clips
Cycles 12 spp, 480x360 (shot camera 1280x720), frames f62-f84 of the pick-up. Columns: current default | opt-in on
today's site (`r2s`) | opt-in on the proposed site (`r2site`). `r2` and `r2a` were measured, not rendered.

| file | what |
| --- | --- |
| `strict_reach_close.jpg` | camera 'left' (the fingers on the cup wall), f64-f82, one frame per row |
| `strict_back_rest.jpg` | camera 'close' (back of the hand) f70 / 76 / 78 / 81, last row the hand at rest f44 |
| `shot_size.jpg` | the same frames as the shot camera shows them: a 160x120 px box, enlarged 3x |
| `reference_reach.jpg` | 10 consecutive frames of the reach in `video_paperboat.mp4` |
| `clips/pickup_f62-84_24fps.mp4`, `..._8fps.mp4` | the three columns side by side, camera 'left', real time and 3x slow |

What the pictures show (my reading; the owner decides):
- **Proposed site (right column): the four fingers lie side by side on the cup, clearly told apart**, from f76 on. This
  is the only column without the fused look. Its lowest finger ends level with the table top (tip centre 13 mm above
  the cup base, skin radius 13 mm).
- **Opt-in on today's site (middle): the held hand is not better than the default, and arguably worse.** The fingers
  still cross, and the lowest finger is bent downwards out of line (f76-f82). That is the T-157 (a) band at work on a
  hand this wide.
- **Motion:** the clip shows the difference the numbers describe: in the default the fingers snap shut between f74 and
  f78; with the opt-in they are already part-closed at f72-f74 and land one after the other until f80.
- **Rest (last row of `strict_back_rest.jpg`): the difference is small.** The rest pose changes the curl of each finger
  by a few degrees; at shot size it is hardly visible. Finger separation at rest is **not** achieved by pose alone.
- **Reference timing:** in the reference the hand is open and shaped for all of the roughly 8 visible frames before it
  touches the paper. With the opt-in the hand is open 10 frames before contact (f66) and at the pre-shape 6 frames
  before (f70); the default is open 6-7 frames before and unshaped until 3 frames before.

## 5. Tests and default path
- Default path: e910 s010 bake (192 frames) from a clean `origin/main` build and from this branch: sha256
  `ef71de3867389779…` on both.
- `plush_tests`: 243 cases pass (3 new). New cases: absent/false = same keys and bad values are load errors; pre-shape,
  landing order, slow landing, same held grasp, no digit deeper in the cup than the default path on any frame (boy and
  girl test hands; largest fingertip step per frame 19.0 → 6.1 mm and 15.8 → 4.7 mm); `widen` and `rest` keys.
- No golden, threshold or existing test was changed.

## 6. Recommendations and open decisions
1. **`fingerClose`:** keep opt-in for now; a shot switches it on per verb. Making it the default for verbs changes every
   existing grasp bake (owner decision, new goldens).
2. **T-157 (a) as default: not recommended as it stands.** It moves every contact into its band (T-157's result holds),
   but on the current boy hand the fingers still overlap by 6-8 mm and the index and little finger are bent sideways
   to reach the band (their curl grows from 41° to 66° and 60°, table above). 5 mm per end does not solve what the owner
   rejected in T-138.
3. **Proposed instead: fix the cup's grasp site** (`content/assets/felt_cup.asset.json`, outside this write-set and a
   default change): socket `grip` at 50 mm, `side_a` band 0-100 mm. Fingers side by side, no sideways bend, all contacts
   in the band. Cost: the wrist arrives 16 mm lower, so the approach graze grows (see 4 below) and the e910 goldens of
   this shot change. `side_b` (the girl's side) would need the same treatment.
4. **Findings that were there before this task** (not changed here):
   - **Thumb-down grip.** In e910 the boy holds the cup with the thumb at the bottom and the little finger on top
     (root heights at f100: thumb 23, index 27, middle 53, ring 79, little 105 mm). The reach planner turns the hand so
     that the fingers never point back at the body. T-157's note "f0 = index" came from this; the bones are named
     correctly (f3 = index).
   - **Approach graze** (section 3).
   Both are reach planning (`interaction.cpp` plan / reach path). I can take them in a follow-up if wanted.

## 7. Limits of this checkpoint
- The mesh is unchanged (released boy 2.3.0): where two fingers overlap on the cup the skin still merges. Pose alone
  cannot remove that; the site change avoids the overlap.
- "One reference-matched reach": the e910 reach is compared with the reach in `video_paperboat.mp4` (`reference_reach.jpg`).
  A new shot that copies the reference action (flat hand onto paper) was **not** built.
- Clips cover the pick-up only (f62-f84, camera 'left'); the hand-over to the girl uses the same keys and is measured by
  the tests, not rendered.
- Render cost on this runner: about 19 minutes to build one Blender scene for 81 frames and about 45 s per frame.

## Reproduce
```
python3 pipeline/production/run_shot.py --shot episodes/e910_showcase/shots/s010/shot.scene.json --blender blender --stages prepare
B=episodes/e910_showcase/shots/s010/build
python3 docs/evaluation/interaction/T-171/make_variants.py $B/shot.resolved.scene.json
sh docs/evaluation/interaction/T-171/build_measure.sh && build/fast-dev/measure_t171 $B/t171_r2.scene.json --hand boy R 58 100
FRAMES=28-108 sh docs/evaluation/interaction/T-171/bake_blend.sh $B/t171_r2s.scene.json $B/t171_r2s
sh docs/evaluation/interaction/T-171/render_views.sh $B/t171_r2s 62 84
```
