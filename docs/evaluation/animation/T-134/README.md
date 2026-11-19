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
