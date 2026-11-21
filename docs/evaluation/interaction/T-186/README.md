# T-186: with `grip: "natural"` the cup stays where it is until the lift

Branch `t-186-claude-natural-grip-cup` from `main` `3f6ea7c`. Engine only (`engine/scene/interaction.cpp`) + one unit
test (`tests/test_grasp_contact.cpp`). Shots measured on T-185's files (`t-185-claude-adopt-r3-grasp` `6d83d07`, a local
checkout; nothing of T-185 changed here): e910 `s010`, `s010_e23`, `s010_e1` with T-185's r3 keys and cup copy; e909
`s010` with T-185's `e909_variants.py` `r3pick` (R3 on her pick-up) and `r3keys` (R3 on pick-up, pass and place).
"Before" = `main` engine, "after" = this branch.

## Owner summary
- **Fixed: from the moment the hand closes on the cup to the start of the lift, the cup does not move at all**
  (0.000 mm, 0.0000 deg) in e910 s010, s010_e23 and e909 s010 (girl). Before: e910 s010 sank 13.9 mm into the table
  and slid 14.3 mm; s010_e23 12.3 mm / 15.7 mm; e909 slid 14.3 mm on the table.
- The lift itself is also cleaner: in e910 the cup now rises straight from f82 (before it was still 13 mm in the table
  and 17-22 mm off sideways in the first lift frames).
- r3's hand is kept: nothing of the hand in the cup on the way in (0.0 / 0.0 / 0.0 mm palm / thumb / fingers in e910;
  0.0 / 0.4 / 0.0 in e909), thumb turned 36 deg (e910) and 31 deg (e909) from rest, thumb up, same landing frames.
- **One cost, e909 girl only:** while she holds the cup still, her elbow now swings out to keep her forearm out of her
  body (it is 2.4-4.1 mm from it), so her wrist bend at the hold is 56 deg instead of r3's 37 (her default grasp: 56).
  Before the fix it was the moving cup that kept her arm out. e910's boy is unchanged (43 vs 45 deg).
- The e909 beat test now passes on the r3 bake (12 of 12; the cup leaves the table at f69 as pinned). Before: 11 of 12.
- Default path (no `grip: "natural"`) byte-identical: e909 default bake and e910 s010_e1 bake identical to `main`,
  goldens unchanged, `plush_tests` and `plush_prop_tests` pass.
- Not in scope, unchanged: the boy's hand going 22.9 mm through the cup as it opens after the place in e909 `r3keys`
  (T-185 finding; the cup itself stays put after the place, 0.000 mm, before and after).

## Cause
The cup is the hand's from the contact on (parent switch at the contact). Between the contact and the lift the hand
moved: the arm-body pass (`armClearancePass`, T-047) pushes the wrist target out of the body where the arm gets too
close, eases the push in time (an envelope that may change by `kPushRate` = 4 mm per frame) and caps it to 0 at a
contact. With the natural elbow the arm comes very close to the body on the way in (e910 s010: a 115 mm need at f58,
while the IK fades in); the envelope of that need crosses the contact and comes back after it at 4 mm per frame, so
the held hand, and the cup with it, went down and sideways (f77 -2.8 / -2.8 mm, f78 -5.6 / -5.8, ... f81 -13.9 /
-14.3). T-134 `reachMechanics` (s010_e1) already stops a ramp at pinned frames, which is why s010_e1 never moved. In
e909 the girl's arm also needs a push while she holds (her body moves towards the held arm, and the elbow swing of the
way in decays), so there the cup slid in 2-frame steps.

## Fix (`engine/scene/interaction.cpp`, opt-in path only)
1. A natural grip writes `<who>/collision.still.<hand>`: 1 from its contact to the first frame of the hand's next move
   (the `hold` lift, a `place` or a hand-over), 0 outside. Nothing evaluates it; only `grip: "natural"` writes it, so
   no other scene has it.
2. Arm-body pass (wrist push): no push in that span, no ramp carried across it (as T-134 does at pinned frames), the
   push grows from 0 before the span as towards any contact, and after it eased in over 6 frames (quadratic, then 4 mm
   per frame), so the push does not drag the cup along the table in the lift's first, slow frames (with a plain 4 mm
   ramp the e909 cup moved 4.2 mm sideways at f68 and the beat test failed, leaves f68).
3. Elbow swing (`writeArmPole`) in that span: where the planned swing would let the forearm come within the margin of
   the body (the envelope decaying from the way in while the hand cannot move), the swing goes on from the previous
   frame by at most `kSwingRate`, taking the angle nearest the planned one that keeps the margin, else the one with the
   largest gap; after the span it joins the planned swing at `kSwingRate`. The hand and the cup do not move with the
   swing. Without this step the girl's forearm went 7.4 mm into her body in e909 (f61-71).

## Numbers
### Cup, contact -> lift start (`cup_span.py`, cup world pose against frame 1; per-frame values in `measures/cup_*.txt`)
| shot | span | before: largest move / lowest below the table / slide / rotation | after |
| --- | --- | --- | --- |
| e910 s010 | f76-81 (lift moves it from f82) | 20.0 mm / -13.9 mm / 14.3 mm / 0.0000 deg | 0.000 / 0.000 / 0.000 mm / 0.0000 deg |
| e910 s010_e23 | f76-81 | 20.0 / -12.3 / 15.7 mm / 0.0000 deg | 0.000 / 0.000 / 0.000 mm / 0.0000 deg |
| e910 s010_e1 | f76-81 | 0.000 (T-134 already) | 0.000 (bake identical to before) |
| e909 s010 girl, r3pick | f57-67 (lift from f68) | 14.3 / -0.6 / 14.3 mm / 0.0000 deg | 0.000 / 0.000 / 0.000 mm / 0.0000 deg |
| e909 s010 girl, r3keys | f57-67 | 14.3 / -0.6 / 14.3 mm / 0.0000 deg | 0.000 / 0.000 / 0.000 mm / 0.0000 deg |
| e909 s010 r3keys, boy's place -> end | f221-286 | 0.000 | 0.000 |

e910 s010 per frame (y = into / out of the table, mm; x slide): before f77 y -2.77 x -2.88, f78 -5.56 / -5.76, f79
-8.35 / -8.62, f80 -11.14 / -11.49, f81 -13.94 / -14.34, f82 -11.60 / -13.00 (lift), f84 +3.96 / -4.84; after f77-81
0.00 / 0.00, f82 +1.38 / +0.34, f84 +11.37 / +2.77. e909 r3pick: before x +2.47, 3.31, 6.21, 6.21, 9.21, 9.21,
11.86, 11.86, 14.14, 14.14 mm (f58-67), f68 +15.42; after f58-67 0.00, f68 +0.58 (y +0.70), f69 +2.27 (y +2.69).

### The hand (T-171 `measure_t171` + T-185 `summarize.py`; `measures/*_t186.json`, "before" = T-185's committed measures)
| variant | thumb side at hold | deepest in the cup on the way in, mm (palm / thumb / fingers) | deepest in the cup held, mm | thumb turned from rest, deg | lands at frame | wrist bend / twist at hold, deg | wrist bend in the carry, deg |
| --- | --- | --- | --- | --- | --- | --- | --- |
| e910 s010 before | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | 76, 76, 76, 78, 80 | 45 / -74 | 93 |
| e910 s010 after | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | 76, 76, 76, 78, 80 | 43 / -74 | 93 |
| e910 s010_e23 before | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | 76, 76, 76, 78, 80 | 43 / -79 | 96 |
| e910 s010_e23 after | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | 76, 76, 76, 78, 80 | 42 / -78 | 96 |
| e910 s010_e1 before / after | up | 0.1 / 6.5 / 0.2 | 0.0 / 0.8 / 0.2 | 36 | 69, 74, 75, 78, 80 | 24 / -64 | 35 |
| e909 girl default (no r3) | up | 14.0 / 5.0 / 0.0 | 14.0 / 0.0 / 0.0 | 174 | 55, -, -, -, 60 | 56 / -59 | 65 |
| e909 girl r3pick before | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 31 | 57, 57, 57, 59, 61 | 37 / -30 | 61 |
| e909 girl r3pick after (r3keys the same) | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 31 | 57, 57, 57, 59, 61 | **56 / -50** | 61 |

e910 hold f84, way in f50-75; e909 contact f58, hold f66, way in f32-57, carry f88-162. In e910 the hand up to the
contact is bit-identical to before (the bakes first differ at f77). e909 boy (`r3keys`, receives f132, places f221):
hold 0.0 / 0.8 / 0.2 mm, place and release 22.9 / 2.2 / 20.1 mm, before and after.

### Arm against the body while the hand holds still (`armgap.cpp`: `armClearanceAt`, mm, negative = inside)
| shot | before | after |
| --- | --- | --- |
| e910 s010 boy R f76-86 | 16.6-24.7 | 15.3-22.4 |
| e910 s010_e23 boy R f76-86 | 14.3-28.8 | 13.1-23.3 |
| e909 girl L f57-69 | 4.2-7.7 | 2.4-4.1 (without fix step 3: down to -7.4) |

The girl's forearm meets the lower torso: her body comes towards the held arm during the hold. Keeping the forearm
out of it without moving the hand needs the elbow; the cost is her wrist bend (56 deg at the hold). Measured
alternatives for step 3 (threshold of "keeps the forearm out"): contact 0.5 mm -> wrist 49 deg, arm -0.9 mm into the
body; 2 mm -> 52 deg / +0.3 mm; 3 mm -> 54 deg / +1.2 mm; the margin (chosen, the planner's own) -> 56 deg / +2.4 mm.
No bake warns ("arm passes into the body") before or after.

## Tests
- New: `tests/test_grasp_contact.cpp` "fingerClose grip natural (T-186): the prop stays where it is from the contact
  until the lift starts": the r3 grasp (wrap, grip natural, clear 0.006) of a cup close in front of the boy package,
  lift 8 frames after the contact. Cup pose constant f20-28 (moved <= 0.01 mm, axes <= 1e-5), arm not in the body
  there, the lift still lifts 12 cm, the span track keyed f20-28 only, none without `grip: "natural"`. On `main` it
  fails: the cup moves 7.08 mm before the lift.
- `plush_tests` and `plush_prop_tests` (fast-dev): all pass, golden bake hashes included
  (`tests/golden/interaction_hashes.json` unchanged).
- `PLUSH_E909_BAKE=<bake> python3 -m pytest tests/acting/test_e909_beats.py`: 12/12 on the default, r3pick and r3keys
  bakes (before: r3pick 11/12, cup leaves f58 instead of f69).

## How to reproduce
```
git worktree add --detach <t185> origin/t-185-claude-adopt-r3-grasp      # T-185's shots (read-only here)
cd <t185>
python3 pipeline/production/run_shot.py --shot episodes/e910_showcase/shots/s010/shot.scene.json --blender blender --stages prepare   # and s010_e23, s010_e1, e909 s010
python3 docs/evaluation/interaction/T-185/e909_variants.py episodes/e909_two_char_acting/shots/s010/build/shot.resolved.scene.json e909_s010 base r3pick r3keys
<repo>/build/fast-dev/apps/render-cli/plush-render episodes/e910_showcase/shots/s010/build/shot.resolved.scene.json --bake s010.json --frames 1-150
python3 <repo>/docs/evaluation/interaction/T-186/cup_span.py 76 81 1 s010.json        # e909: 57 67 1
python3 <repo>/docs/evaluation/interaction/T-186/cup_frames.py s010.json 70 90
g++ -std=c++23 -O3 -DNDEBUG -I <repo>/engine <repo>/docs/evaluation/interaction/T-186/armgap.cpp -L<repo>/build/fast-dev/engine \
  -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o armgap
./armgap build/t185/e909_s010/r3pick/scene.json girl L 50 80
<repo>/build/fast-dev/measure_t171 <scene> --hand boy R 47 150 > m.json   # from <t185> (its content/assets); T-171 build_measure.sh
```
