# T-134: reach mechanics for verb and IK reaches (E1a / E1b / E1c)

Input `37901c4` (`integration/r5-start`), branch `t-134-claude-reach`. Task: [docs/tasks/T-134.md](../../../tasks/T-134.md).

Everything is behind the opt-in scene key `reachMechanics` (absent / `null` / `false` = off; `true` = shared defaults;
an object = field overrides, see `ReachMechanics` in `engine/anim/principles.h`). Without the key no track is written
and no code path changes: the full `plush_tests` run (golden bake hashes included) passes unchanged.

Evidence shot: `episodes/e910_showcase/shots/s010_e1/shot.scene.json` = the T-117 shot `s010` plus the key, written by
[make_e1_shot.py](make_e1_shot.py). `s010` itself is untouched. Two reaches are measured:

| Reach | Frames | Length |
|---|---|---|
| boy, right hand, `pick_up` of the cup | f57 → contact f76 (the T-117 notes say f77; the expanded scene and the bake say f76) | 19 f |
| girl, left hand, receiver of the `pass` | f104 → contact f114 | 10 f |

Measures are my own until T-135's `tools/motion_checks/reach` lands: [measure_reach.py](measure_reach.py) reads two
bakes (before / after) and reports the wrist pivot's speed per frame, the body's offset against the `before` bake
along the reach direction, and what moves after the contact. Previews: [preview_strip.py](preview_strip.py)
(Cycles 8 samples, 480×270, same frames of both bakes).

## E1a: ease in / out and anticipation

`"reachMechanics": {"ease": true, "anticipation": true}` · strip: [e1a_preview_strip.jpg](e1a_preview_strip.jpg) ·
numbers: [e1a_measures.json](e1a_measures.json).

The strip shows f52-f77 (boy's reach) and f104-f114 (girl's reach), `before` above and E1a below. At this size the
difference is small: the clearest frames are f66 / f70 (his hand is further along its path and his shoulder is
forward) and f108 / f111 (her hand). The timing change shows in the numbers below, not in stills.

What it does (`engine/scene/interaction.cpp`, `reachTo` and `applyReachLead`):
- **Ease.** The wrist target travels one curve through the reach's three points (start, approach, contact) on a
  slow-in / slow-out profile, keyed every frame. Before, three smooth keys: their path has a corner at the approach
  point, and the wrist nearly stops there in the middle of the reach.
- **Anticipation.** From 6 f before the reach (f51 for the boy, f98 for the girl; the hips 3 f earlier) the torso first moves a little away from the prop, then leans and turns
  towards it, hips → spine → chest → shoulder → wrist, each 1.4 f before the next. The lead is full at 60 % of the
  reach, held to the contact and given back over 14 f. IK arms are solved again from the moved shoulder, so wrists
  stay on their targets; the eyes keep their aim; the neck takes back 70 % of the torso's turn.
- The lead is reduced in quarter steps if it would cost the reaching arm room against the body at the contact
  (the girl's reach in e910 keeps the full lead).
- With the key on, the collision planner's wrist push no longer resumes after a pinned frame. Without this, the
  girl's hand moved 8 mm in the 3 frames after her contact (a ramp from before the contact coming back).

### Wrist speed (mm / frame, wrist pivot)
| | before | E1a |
|---|---|---|
| boy f57-76 | 7.1 6.7 5.9 5.9 10.4 16.3 22.6 27.4 **30.1** 29.4 24.8 17.1 **5.3** 6.1 10.5 12.6 12.2 9.2 3.7 | 7.6 7.2 6.9 6.5 8.1 14.5 20.7 28.1 33.7 **35.3** 29.2 16.5 10.7 10.7 7.5 4.5 2.7 3.0 2.6 |
| girl f104-114 | 3.3 5.4 22.8 49.3 **52.4** 21.4 **12.2** 18.0 16.0 6.9 | 3.9 3.1 15.9 41.1 **60.0** 35.3 26.3 16.4 7.1 3.7 |

| Measure | boy before | boy E1a | girl before | girl E1a |
|---|---|---|---|---|
| Speed humps in the reach | 2 (stall to 5.3 at f69) | 1 | 2 (dip to 12.2 at f110) | 1 |
| Peak speed, mm/f | 30.1 | 35.3 | 52.4 | 60.0 |
| Speed in the last frame before contact, mm/f | 3.7 | 2.6 | 6.9 | 3.7 |
| Speed over the last 4 frames, mm/f | 12.6 12.2 9.2 3.7 | 4.5 2.7 3.0 2.6 | 12.2 18.0 16.0 6.9 | 26.3 16.4 7.1 3.7 |
| Largest speed change between frames, mm/f² | 12.4 (f69) | 19.9 (f68) | 32.3 (f109) | 37.5 (f109) |
| Wrist speed in the 4 f after contact, mm/f | 0.0 | 0.0 | 0.0 | 0.0 |

### Body lead (offset against `before` along the horizontal reach direction, mm)
| | first moves | counter move | at reach start | when the wrist has done 10 % | maximum |
|---|---|---|---|---|---|
| boy shoulder (`upperArm.R`) | f50 | −2.0 | −1.2 | +0.8 (f59) | +10.2 (f67) |
| boy chest | f50 | −0.4 | 0.0 | +0.6 | +1.9 (f67) |
| girl shoulder (`upperArm.L`) | see note | — | +8.6 | +21.1 (f107) | +27.0 (f111) |
| girl chest | f96 | −1.2 | +2.0 | +4.3 | +4.5 (f111) |

The girl's shoulder numbers include a second effect: her arm differs from `before` from f79 on, because the collision
planner's arm lift is planned over the whole shot and re-plans for the new reach path. Her chest row is the lead alone.

Feet: largest offset against `before` 0.63 mm (both characters). `run_shot --stages prepare,bake`: 0 warnings, as before.

### Honest limits of E1a
1. **The peak is higher and the deceleration after it is sharper than before** (boy 35.3 → 16.5 mm/f within two
   frames, largest speed change 19.9 against 12.4 mm/f²). The target itself is smooth; the actual wrist is the IK
   target blended in by the IK weight (full only 6 f before contact) plus the planner's wrist push, whose envelope is
   a linear ramp up and down (4 mm/f). I tried two fixes and dropped both:
   - rounding the planner's ramps: no gain in the reach, and the held cup crept 5 mm in the settle frames;
   - full IK weight early in the reach: smooth slow-out, but an abrupt start and a new warning (girl's arm 15 mm
     into the body at f108).
2. **The hand is already moving when the reach starts** (boy 7 mm/f from about f30). That is the planner's arm lift
   (rate-limited ramps), present in `before` as well; E1a does not touch it.
3. **The lead is small on these characters** (arms are 18 cm long): the boy's chest moves 2 mm, his shoulder 10 mm.
   Whether it reads at shot scale is for the strip and the Supervisor to judge; `leanDeg`, `twistDeg` and `shoulderM`
   are scene overrides.
4. `tools/motion_checks` popping: 63 issues before, 66 with E1a. Inside the two reach windows the same events are
   flagged in both (the girl's 10 f reach, the boy's fingers at the grasp); the three extra are a finger joint at
   f43 and f152 and the boy's palm at f68 (21 mm/f², the deceleration of point 1). Interpenetration: 4 and 4.
5. Hips: the lead turns the hips about their own pivot, so a pivot-offset measure shows 0 for them.

### Tests
`tests/test_reach_mechanics.cpp` (5 cases): the settings parse and are off by default; the ease and lead profiles;
and on the boy, girl and engine skeletons: no `reach.*` track without the key, contact within 5 mm, one speed hump
with a slow first and last frame, the shoulder moving away and then ahead of the wrist, the lead given back, feet
within 4 mm. Full `plush_tests`: 220 cases pass.

## E1b: curved wrist arcs

`"reachMechanics": {"ease": true, "anticipation": true, "arcs": true}` (E1a + arcs) · path plot:
[e1b_wrist_paths.jpg](e1b_wrist_paths.jpg) (one dot per frame, seen so the bend shows; grey `before`, red E1a, blue
E1b) · strip: [e1b_preview_strip.jpg](e1b_preview_strip.jpg) · numbers: [e1b_arcs.json](e1b_arcs.json),
[e1b_measures.json](e1b_measures.json) · script: [measure_arcs.py](measure_arcs.py).

What was straight: the reaches already bend (they pass an approach point), but **every carry and the giver's way to
the hand-over point were exact straight lines** (arc 0.000). What E1b does (`arcMove` and `reachTo` in
`engine/scene/interaction.cpp`):
- **Carry (`hold`) and the giver's bring in a hand-over** travel a shallow arc: the mid point is 12 % of the chord
  away from the chord, on the side away from the shoulder (the hand swings round its arm's joints), less if the arm
  could not reach that far. Start, end and timing are unchanged, so the prop arrives where and when it did.
- **Reach**: the approach point is the direction the hand arrives from, no longer a point the curve must pass. The
  bend is spread over the whole reach instead of sitting just before the contact, and it is at least 12 %.
- `place` is unchanged: it already lowers the prop from 3 cm above the target.

arc = largest deviation of the wrist path from its chord / chord length.

| Move | chord | before | E1a | E1b |
|---|---|---|---|---|
| boy carry f81-97 | 130 mm | 0.000 | 0.000 | **0.120** (15.6 mm) |
| boy brings the cup to the hand-over f100-110 | 73 mm | 0.000 | 0.000 | **0.120** (8.8 mm) |
| girl carry f136-156 | 47 mm | 0.000 | 0.001 | **0.120** (5.6 mm) |
| boy reach f57-76 | 136 mm | 0.313 | 0.394 | 0.344 |
| girl reach f104-114 | 147 mm | 0.351 | 0.391 | 0.264 |

The reach curve also takes back most of E1a's limit 1 (wrist pivot, mm/frame):

| | boy before | boy E1a | boy E1b | girl before | girl E1a | girl E1b |
|---|---|---|---|---|---|---|
| Speed humps | 2 | 1 | 1 | 2 | 1 | 1 |
| Peak speed | 30.1 | 35.3 | 29.6 | 52.4 | 60.0 | 52.6 |
| Largest speed change, mm/f² | 12.4 | 19.9 | 13.1 | 32.3 | 37.5 | 28.2 |
| Last 4 frames | 12.6 12.2 9.2 3.7 | 4.5 2.7 3.0 2.6 | 3.2 1.8 1.3 0.2 | 12.2 18.0 16.0 6.9 | 26.3 16.4 7.1 3.7 | 23.0 14.3 6.3 3.6 |

Boy E1b, f57-76: 7.7 7.4 6.8 6.1 6.6 11.2 17.3 23.2 27.8 29.6 26.7 18.5 9.2 8.5 5.7 3.2 1.8 1.3 0.2.
Girl E1b, f104-114: 4.2 4.2 14.6 36.6 52.6 33.6 23.0 14.3 6.3 3.6.

Carry timing: the speed per frame differs from `before` by at most 1 mm/f (the arc is a little longer than the
chord). The cup: largest speed 12.2 mm/f before and after, largest acceleration 3.5 → 3.8 mm/f², upright throughout.
Bake: 0 warnings. `tools/motion_checks`: popping 64 issues (before 63, E1a 66), interpenetration 4.

### Honest limits of E1b
1. **The reaches still have a bend near each end** (path plot, first and fourth panel). At the start it is the hand
   leaving the planner's arm-lift drift; at the end the hand comes down onto the grip from the approach side. The
   girl's 10 f reach changes direction sharply at f109-110, as it does in
   `before`; that is where her largest speed change is.
2. **The arcs are small in the picture**: 16 mm, 9 mm and 6 mm on carries of 130, 73 and 47 mm. They show in the
   path plot; in the strip they are hard to see. `arc` is a scene override (0 to 0.4).
3. The arc side is geometric (away from the shoulder), not chosen for the camera. In e910 the boy's carry bends
   sideways, away from his body (14 mm at f89), and slightly up (2 mm).
4. The boy's deceleration after his peak is still quick (26.7 → 18.5 → 9.2 mm/f), for the reason given under E1a.
5. Hand-over giver's return and `place`'s return after the release are not arced (the IK weight fades there).

### Tests
Three more cases in `tests/test_reach_mechanics.cpp` (boy, girl, engine skeleton): a carry is straight without the
key (< 0.03) and an arc with it (0.12), with the same ends and the same speed per frame; the reach's arc is above
0.1 and its contact stays within 5 mm.

## E1c: overlap and secondary motion

`"reachMechanics": true` (everything on; this is what `s010_e1` now holds) · offsets over time:
[e1c_offsets.jpg](e1c_offsets.jpg) (chest, head and hair against `before`; left E1b, right E1c) · strip:
[e1c_preview_strip.jpg](e1c_preview_strip.jpg) · numbers: [e1c_overlap.json](e1c_overlap.json),
[e1c_measures.json](e1c_measures.json) · script: [measure_overlap.py](measure_overlap.py).

What it does (the lead tracks in `reachTo`, the neck in `applyReachLead`):
- **Torso and shoulder** follow the lead through the body-mechanics follow-through response (`followKernel`,
  settles in 8 f, 12 % overshoot of a step) instead of the plain envelope.
- **Settle at the contact**: when the hand stops, the body runs on past its lead by a quarter of it, swings back
  and comes to rest (a damped swing, period 12 f), while the lead is given back.
- **Head**: the neck's counter turn has its own response, 2 f later and looser (settles in 12 f, 20 % overshoot).
  The head first goes with the torso, then catches up, and swings once after the contact.
- **Hair**: nothing is added. The characters' spring chains (`DYN-*` bones, `anim/secondary.h`) answer the head's
  motion; `secondary.*` is untouched.
- The wrists stay on their IK targets, as in E1a.

| Measure (against `before` unless said) | boy E1b | boy E1c | girl E1b | girl E1c |
|---|---|---|---|---|
| Head rotation, largest during the reach | 1.10° | 1.87° (f64) | 1.31° | 3.52° (f107) |
| Head rotation after the contact, every 2nd frame | 0.91 0.84 0.68 0.46 0.23 0.08 0.00 | 1.13 1.01 0.11 0.77 0.90 0.50 0.07 | 1.28 1.18 0.96 0.64 0.33 0.11 0.03 | 1.38 1.48 0.23 1.09 1.30 0.72 0.11 |
| Chest rotation at the contact | 3.04° | 3.29° | 4.28° | 4.65° |
| Chest rotation after the contact, every 2nd frame | 3.04 2.81 2.27 1.52 0.77 0.26 0.04 | 3.29 3.22 2.52 1.46 0.60 0.15 0.02 | 4.28 3.94 3.18 2.13 1.09 0.36 0.05 | 4.65 4.57 3.57 2.08 0.85 0.21 0.04 |
| Head pivot against E1b after the contact, largest | — | 1.7 mm (f83) | — | 2.0 mm (f121) |
| Chest pivot against E1b after the contact, largest | — | 0.6 mm (f77) | — | 0.8 mm (f115) |
| Hair (any `DYN-*` bone), largest offset | 15.7 mm | 21.5 mm (f65) | 23.8 mm | 35.0 mm (f109) |
| Hair against E1b after the contact, largest | — | 12.8 mm (f84) | — | 11.8 mm (f123) |
| Head and chest back within 0.5 mm of `before` | f86 / f85 | f84 / f84 | f125 / f123 | f122 / f123 |

The head row after the contact is the settle: with E1b the head eases back in one go; with E1c it passes through
(0.11° / 0.23° two to four frames after the contact), swings about 1° to the other side and comes to rest within
12 f. The hair shows it most: its curve in the plot keeps swinging after the contact.

Unchanged by E1c: the reach speed profile (boy peak 29.6 mm/f, largest change 13.1 mm/f²; girl 52.7 and 28.2), the
carry arcs (0.120), wrist speed after both contacts (0.0). Bake: 0 warnings. `tools/motion_checks`: popping 63
issues (before 63, E1b 64), interpenetration 4. Feet: 0.70 mm.

### Honest limits of E1c
1. **Head and torso overlap is at the edge of what shows**: about 1° of head swing and 1 to 2 mm at the head pivot,
   on characters whose reach lead is itself small. In the strip I cannot point to it. The hair is the part that
   reads (12 mm against E1b after the contact). `settleAmount`, `headOvershoot`, `headLagSec` and the lead sizes are
   scene overrides; I did not raise the defaults without a judgement on E1a's lead size first.
2. **Hair runs long**: the girl's hair is still more than 0.5 mm from `before` until f172 (E1b: f153), the boy's
   differs to the end of the shot in both (his spring chains do not come back to the same state once disturbed).
   The girl's hair has three visible swings after her contact (plot, bottom right); whether that is lively or too
   busy is a judgement call. Stiffness and damping are the characters' own `dynamics`, not changed here.
3. The pivot-offset measure cannot show the head lagging the chest (both rise at the same frame): the head's pivot
   rides on the torso. The lag is in the head's rotation (largest at f64 / f107, before the chest's largest).
4. No hand or finger overlap was added: the hand must stay on the grip.

### Tests
Three more cases (boy, girl, engine skeleton): with overlap the shoulder runs past the plain lead after the contact
and swings back below it, the head differs from the plain lead during the reach and after the contact, nothing steps,
the contact stays within 5 mm, and everything is back where it is without the mechanics by the end of the scene.

## Status of the three items
| Item | State | Main open point |
|---|---|---|
| E1a ease + anticipation | works, measured | lead is small on 18 cm arms; the hand's drift before the reach (planner) is untouched |
| E1b arcs | works, measured | arcs of 6 to 16 mm are small in the picture; reaches still bend near each end |
| E1c overlap + settle | works, measured | head / torso settle is about 1°; only the hair clearly reads |

All three wait for T-135's `tools/motion_checks/reach` to be re-measured with the shared tool; the numbers above are
from the scripts in this folder.
