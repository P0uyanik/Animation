# T-185: the T-171 r3 cup grasp ("fixed, thumb up") used in the shots

Branch `t-185-claude-adopt-r3-grasp` from `integration/r5-batch1` `554e403` (now `main`). Owner decision 2026-11-21
~19:20 CET: T-171 round 3 column 3, variant `r3`, integrated and used by the shots that pick up the cup. Per shot only:
`fingerClose` defaults, the engine, `content/assets`, `tests/golden/*` and every golden are unchanged.

## Owner summary
- **e910 (s010, s010_e1, s010_e23): r3 is on** and the real shot gives T-171's r3 numbers exactly: nothing of the hand
  in the cup on the way in (default 7.8 / 4.2 / 5.0 mm palm / thumb / fingers), palm 0.0 mm held (default 9.6), thumb
  turned 36 deg from rest (default 138), thumb up. The e910 s010 bake is identical to T-171's own `r3` scene but for
  the scene path recorded in it.
- **e909 (s010, s010_t113): r3 is on for the girl's left-hand pick-up only.** Her hand: palm 14.0 -> 0.0 mm in the cup
  held (s010), thumb turned 174 -> 31 deg, all fingers land. Putting the keys on the pass as well would have helped the
  boy's hold but made his release after the place worse (his hand through the cup 23 mm instead of 16): left as released.
- **Known limits, logged by the owner, not fixed here:** with r3 the wrist bends up to 93 deg in the carry and the
  hand-over (e910; default 57); no finger press depth (the fingers reach less far round the cup than the default,
  whose palm sank into it); in e910's camera the thumb-up hand is mostly hidden behind the sleeve.

## What changed (files)
| file | change |
| --- | --- |
| `episodes/e910_showcase/make_shot.py` | `R3` (T-171 `make_variants.py` `SEP` + `R3`, key for key) on the shot's verbs (`pick_up`, `pass`); `--derived` adds it to `s010_e1` / `s010_e23` (their own keys stay); writes the cup copy below; `x_t185` note in the shot |
| `episodes/e910_showcase/content/assets/felt_cup.asset.json` | **a copy of `content/assets/felt_cup.asset.json` with only two values changed**: socket `grip` y 0.066 -> 0.05 and `side_a` band [0.045, 0.09] -> [0.0, 0.1] (T-171's proposed cup site, which r3 was measured on). A text copy, so `diff content/assets/felt_cup.asset.json episodes/e910_showcase/content/assets/felt_cup.asset.json` shows exactly those two lines: a later promotion to `content/assets` is that one diff. The engine (`scene.cpp` `loadSceneAsset`) and `shot_render.py` take the nearest `content/assets` above the scene, so every e910 shot uses it |
| `episodes/e910_showcase/shots/s010*/shot.scene.json` | regenerated (`make_shot.py --derived`): `fingerClose` on pick_up and pass, `x_t185` |
| `episodes/e909_two_char_acting/make_shot.py` | the same `R3` on the girl's `pick_up` only; `x_t185` note |
| `episodes/e909_two_char_acting/shots/s010{,_t113}/shot.scene.json` | regenerated (`make_shot.py`, `--candidate`) |

Not touched: e907 (s010_verbs is e910's run-time base; e910 adds its keys itself), e905, e911, e909 `s010_t183` (T-183).

## e910 numbers (`measure_t171`, boy R; `measures/table_e910.md`)
Every vertex of the hand bone and below against the cup as a capped solid; T-171 R3.3 columns (`summarize.py` = T-171's
`summarize_r3.py` with the contact read from the measures; on e910 it gives T-171's frames f76 / f50-75 / f84 / f100-135).

| variant | thumb side at hold | deepest in the cup on the way in f50-75, mm (palm / thumb / fingers) | deepest in the cup held f84, mm (palm / thumb / fingers) | thumb turned from rest, deg | least joint bend, deg (negative = backwards) | index joints held, deg | fingers off the cup held, mm (largest) | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold f84, deg | wrist bend in the carry f100-135, deg (largest) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| e910_before | down | 7.8 / 4.2 / 5.0 | 9.6 / 0.0 / 0.4 | 138 | -18 | 24, 30, 0 | -0.2 | 74, 76, 77, 78, 79 | 14 | 10 / -124 | 57 |
| e910_after | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | -23 | 14, 8, 6 | -0.1 | 76, 76, 76, 78, 80 | 4 | 45 / -74 | 93 |
| e910e1_before | down | 9.4 / 17.7 / 0.5 | 9.6 / 0.0 / 0.4 | 138 | -18 | 24, 30, 0 | -0.2 | 70, 76, 77, 78, 79 | 14 | 11 / -127 | 57 |
| e910e1_after | up | 0.1 / 6.5 / 0.2 | 0.0 / 0.8 / 0.2 | 36 | -23 | 14, 8, 6 | -0.1 | 69, 74, 75, 78, 80 | 4 | 24 / -64 | 35 |
| e910e23_before | down | 13.8 / 4.3 / 17.0 | 9.6 / 0.0 / 0.4 | 138 | -18 | 24, 30, 0 | -0.2 | 74, 76, 77, 78, 79 | 14 | 10 / -125 | 58 |
| e910e23_after | up | 0.0 / 0.0 / 0.0 | 0.0 / 0.8 / 0.2 | 36 | -23 | 14, 8, 6 | -0.1 | 76, 76, 76, 78, 80 | 4 | 43 / -79 | 96 |

- **s010 = T-171 r3, row for row** (T-171 `measures/table_r3.md` rows `base` and `r3`). Hand-over (`--pair boy R girl
  L`): hands apart 62 mm (default) -> 18 mm at the nearest, 25 mm at the contact f114, as T-171 measured.
- **s010_e23** (T-136 blink/gaze opt-ins): the same, carry wrist bend 96 deg (93 in s010).
- **s010_e1** (T-134 `reachMechanics`): held as r3, but the arm comes in on another path and the thumb still grazes the
  cup on the way in, f67-72, up to 6.5 mm at f70 (default here: 17.7 mm at f73). Better than before on every column;
  not tuned (r3 is used exactly as measured).

## e909: measured before adopting (girl L, set b = site side_b; boy R receives and places)
Variants (`e909_variants.py`, each with its own cup folder under `build/t185/`): `base` (as released), `r3pick` (R3 on
her pick_up only: **adopted**), `r3keys` (R3 on pick_up, pass and place), `r3np` (pick_up and pass), `r3site` / `r3sitenp`
(+ T-171's side_a site, his side), `r3siteb` (+ side_b centred as well, her side: not T-171's, measured for reference).
Contact = the frame her index lands in `base`: f58 (s010), f57 (s010_t113); held = contact + 8.

s010 (current cast):

| variant | thumb side at hold | deepest in the cup on the way in f32-57, mm (palm / thumb / fingers) | deepest in the cup held f66, mm (palm / thumb / fingers) | thumb turned from rest, deg | least joint bend, deg (negative = backwards) | index joints held, deg | fingers off the cup held, mm (largest) | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold f66, deg | wrist bend in the carry f88-162, deg (largest) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | up | 14.0 / 5.0 / 0.0 | 14.0 / 0.0 / 0.0 | 174 | -14 | 12, 16, 0 | 0.8 | 55, -, -, -, 60 | 66 | 56 / -59 | 65 |
| r3pick | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 31 | -12 | 23, 6, 5 | 0.0 | 57, 57, 57, 59, 61 | 17 | 37 / -30 | 61 |
| r3keys | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 31 | -12 | 23, 6, 5 | 0.0 | 57, 57, 57, 59, 61 | 17 | 37 / -30 | 61 |
| r3site | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 31 | -12 | 23, 6, 5 | 0.0 | 57, 57, 57, 59, 61 | 17 | 37 / -30 | 61 |
| r3siteb | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 21 | -21 | 90, 50, 40 | 1.0 | 57, -, 57, 59, 61 | 17 | 31 / -23 | 50 |

s010_t113 (T-113 candidate cast):

| variant | thumb side at hold | deepest in the cup on the way in f31-56, mm (palm / thumb / fingers) | deepest in the cup held f65, mm (palm / thumb / fingers) | thumb turned from rest, deg | least joint bend, deg (negative = backwards) | index joints held, deg | fingers off the cup held, mm (largest) | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold f65, deg | wrist bend in the carry f88-162, deg (largest) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | up | 1.6 / 4.8 / 0.0 | 6.0 / 0.0 / 0.0 | 168 | -39 | 15, 19, 0 | 0.4 | 55, 57, 58, 59, 60 | 61 | 57 / -61 | 65 |
| r3pick | up | 0.0 / 0.0 / 0.0 | 0.0 / 2.5 / 0.0 | 36 | -23 | 5, 6, 5 | 1.0 | 57, -, -, -, - | 17 | 63 / -58 | 59 |
| r3keys | up | 0.0 / 0.0 / 0.0 | 0.0 / 2.5 / 0.0 | 36 | -23 | 5, 6, 5 | 1.0 | 57, -, -, -, - | 17 | 63 / -58 | 59 |
| r3site | up | 0.0 / 0.0 / 0.0 | 0.0 / 2.5 / 0.0 | 36 | -23 | 5, 6, 5 | 1.0 | 57, -, -, -, - | 17 | 63 / -58 | 59 |
| r3siteb | up | 0.0 / 0.0 / 0.0 | 0.0 / 1.2 / 0.0 | 44 | -40 | 5, 6, 5 | 1.0 | 57, -, -, -, - | 17 | 58 / -46 | 63 |

Her hand through the hold, carry and hand-over (f66-162, deepest in the cup, palm / thumb / fingers): s010 14.3 / 0 / 0
-> 0.0 / 0.4 / 0.0 mm; s010_t113 8.1 / 0 / 0 -> 1.1 / 2.5 / 0.0 mm. The thumb with 2.5 mm in s010_t113 is the girl case
T-171 R3.5 names (2.7 mm with `wrap` on the old test package).

The boy's right hand (receives at f132, places at f221), deepest in the cup, palm / thumb / fingers, mm:

| variant | hold f134-215 | place and release f216-237 |
| --- | --- | --- |
| base, r3pick (identical) | 9.6 / 0.0 / 0.4 | 16.1 / 0.0 / 8.5 (f227-230) |
| r3keys | 0.0 / 0.8 / 0.2 | 22.9 / 2.2 / 20.1 (f223-231) |
| r3np | 0.0 / 0.8 / 0.2 | 22.9 / 2.2 / 19.9 |
| r3sitenp | 0.0 / 0.8 / 0.2 | 25.9 / 2.5 / 22.4 |

So with the key on the pass his hold is fixed (as e910's) but his hand goes deeper through the cup as it opens after the
place, over more frames; the place key itself is not the cause (`r3np`). That is worse in one measure, so the pass stays
as released and only her pick-up takes r3. Recommendation (not done here): the release after a place needs the same
"clear" treatment as the way in before r3 goes on e909's pass.

In s010_t113 her fingers end 1.0 mm off the cup (they do not land, index joints 5 / 6 / 5 deg) where the default lands
them; in s010 (current cast) they land (23 / 6 / 5 deg). Everything else in her rows is better or equal.

Both e909 shots after `run_shot --stages prepare` bake identically to `r3pick` (but for the recorded scene path).

## Review clip and sheet
CLIP_SHEET

## Tests
- `plush_tests` (fast-dev): all pass, including the golden bake hashes (`tests/golden/interaction_hashes.json`
  unchanged; none of the shots above is in it). No test, threshold or golden changed.

## How to reproduce
```
python3 episodes/e910_showcase/make_shot.py --derived ; python3 episodes/e909_two_char_acting/make_shot.py [--candidate]
python3 pipeline/production/run_shot.py --shot episodes/e910_showcase/shots/s010/shot.scene.json --blender blender --stages prepare
B=episodes/e910_showcase/shots/s010/build
python3 docs/evaluation/interaction/T-185/before_scene.py $B/shot.resolved.scene.json e910     # build/t185/e910/before.scene.json
sh docs/evaluation/interaction/T-171/build_measure.sh
build/fast-dev/measure_t171 $B/shot.resolved.scene.json --hand boy R 47 150 > measures/r3_e910_after.json
python3 docs/evaluation/interaction/T-185/summarize.py measures e910_before e910_after
python3 docs/evaluation/interaction/T-185/e909_variants.py episodes/e909_two_char_acting/shots/s010/build/shot.resolved.scene.json e909_s010
FRAMES=58-86 BUILD=$B sh docs/evaluation/interaction/T-171/bake_blend.sh <scene> <out>; sh docs/evaluation/interaction/T-185/render_views.sh <out> 62 84
```
