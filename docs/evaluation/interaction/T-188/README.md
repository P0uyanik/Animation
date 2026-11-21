# T-188: the r3 thumb-up grasp on the girl's pick-up in e909

Branch `t-188-claude-e909-r3-grasp` from `main` `f049713` (contains T-185 and T-186). Changed: `episodes/
e909_two_char_acting/make_shot.py` and the two shots it writes (`s010`, `s010_t113 = make_shot.py --candidate`).
No engine, test, golden or asset change. `s010_t183` (T-183) not touched.

## Owner summary
- The girl's left-hand pick-up of the cup in e909 `s010` and `s010_t113` now uses T-171's r3 grasp (`fingerClose`
  {rest, wrap, grip "natural", clear 0.006}, the same keys as e910's `R3`), on her `pick_up` only = T-186's `r3pick`.
- Her palm is no longer in the cup: on the way in 14.0 -> 0.0 mm (s010), 1.6 -> 0.0 mm (s010_t113); held and through
  the hand-over 14.3 -> 0.0 mm (s010), 8.1 -> 1.1 mm (s010_t113). Thumb up, turned 31 / 36 deg from rest instead of
  174 / 168. Finger joints step at most 17 deg per frame in the close instead of 66 / 61.
- The cup does not move from the contact to the lift (0.000 mm), it leaves the table at f68 as before, and does not
  move after the place (0.000 mm). `tests/acting/test_e909_beats.py` on the new bake: 12 of 12.
- **Known cost (accepted):** her wrist bend at the hold is 56 deg in s010 (default 56; r3 before T-186 was 37) and
  63 deg in s010_t113 (default 57). In the carry it is lower than the default (61 / 59 vs 65).
- In s010_t113 (candidate cast) her fingers stop 1.0 mm off the cup (only the thumb lands; the default lands them) and
  the thumb is 2.5 mm into the cup held (T-171 R3.5's girl case). Not visible at the shot camera (clip below).
- The boy is unchanged (no key on the pass or place: with them his release goes 22.9 mm through the cup, T-185).

## Why not T-171's cup site
T-171's proposed site (socket `grip` y 0.05, `side_a` band 0-0.1) is the boy's side (set a); her set b (`grip_b`,
`side_b`) is not changed by it (T-185: `r3site` = `r3pick` on every girl column). It would only move the boy's
receive, which is out of scope, so the cup stays the released `content/assets` one and no
`episodes/e909_two_char_acting/content/assets` copy is written.

## Numbers
Before = the same resolved scene without `fingerClose` (= `main`'s shot), after = this branch; same engine (`main`
fast-dev). `measure_t171` (T-171 tool), `summarize.py` (T-185), `cup_span.py` (T-186); `measures/*.json`,
`measures/table_*.md`. Contact = the frame her index lands in the default bake.

### Girl L (set b)
| shot | variant | thumb side at hold | deepest in the cup on the way in, mm (palm / thumb / fingers) | deepest in the cup held, mm (palm / thumb / fingers) | held through hold, carry and hand-over (to f162), mm | thumb turned from rest, deg | lands at frame (thumb, index..little) | largest joint step in the close, deg/frame | wrist bend / twist at hold, deg | wrist bend in the carry f88-162, deg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s010 (contact f58, way in f32-57, hold f66) | before | up | 14.0 / 5.0 / 0.0 | 14.0 / 0.0 / 0.0 | 14.3 / 0.0 / 0.0 | 174 | 55, -, -, -, 60 | 66 | 56 / -59 | 65 |
| s010 | after | up | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 0.0 / 0.4 / 0.0 | 31 | 57, 57, 57, 59, 61 | 17 | **56** / -50 | 61 |
| s010_t113 (contact f57, way in f31-56, hold f65) | before | up | 1.6 / 4.8 / 0.0 | 6.0 / 0.0 / 0.0 | 8.1 / 0.0 / 0.0 | 168 | 55, 57, 58, 59, 60 | 61 | 57 / -61 | 65 |
| s010_t113 | after | up | 0.0 / 0.0 / 0.0 | 0.0 / 2.5 / 0.0 | 1.1 / 2.5 / 0.0 | 36 | 57, -, -, -, - | 17 | **63** / -58 | 59 |

s010 after = T-186's `r3pick after` row, column for column. s010_t113 after = T-185's `r3pick` row (T-186 did not
measure it); fingers off the cup held: 1.0 mm (before 0.4).

### Cup (bake, world pose against frame 1)
| shot | variant | contact -> lift f57-67: largest move / lowest / slide / rotation | first frame it moves (lift) | after the place f221-286 |
| --- | --- | --- | --- | --- |
| s010 | before / after | 0.000 mm / 0.000 / 0.000 mm / 0.0000 deg, both | f68 / f68 | 0.000 mm, both |
| s010_t113 | before / after | 0.000 mm / 0.000 / 0.000 mm / 0.0000 deg, both | f68 / f68 | 0.000 mm, both |

The cup's pose from f200 to the end is identical before and after (both shots).

### Boy R (receives f133, places f221) - unchanged
| shot | hold f134-215 (palm / thumb / fingers) | place and release f216-237 |
| --- | --- | --- |
| s010, s010_t113, before and after | 9.6 / 0.0 / 0.4 mm | 16.1 / 0.0 / 8.5 mm |

## Tests
- `PLUSH_E909_BAKE=build/t188/s010/after.json python3 -m pytest tests/acting/test_e909_beats.py`: 12 passed (cup
  leaves f69, back f221 as pinned; no engine warning). The default bake: 12 passed. No bake log of either shot warns.
- `plush_tests` and `plush_prop_tests` (fast-dev, `ctest`): pass, golden bake hashes included
  (`tests/golden/interaction_hashes.json` unchanged; no engine change here).

## Clip and sheet
CLIPS_SECTION

## How to reproduce
```
python3 episodes/e909_two_char_acting/make_shot.py && python3 episodes/e909_two_char_acting/make_shot.py --candidate
python3 pipeline/production/run_shot.py --shot episodes/e909_two_char_acting/shots/s010/shot.scene.json --blender blender --stages prepare   # and s010_t113
B=episodes/e909_two_char_acting/shots/s010/build
python3 -c "import json;s=json.load(open('$B/shot.resolved.scene.json'));[a.pop('fingerClose',None) for a in s['actions']];s.pop('x_t188');json.dump(s,open('$B/before.resolved.scene.json','w'))"
build/fast-dev/apps/render-cli/plush-render $B/shot.resolved.scene.json --bake build/t188/s010/after.json    # before likewise
PLUSH_E909_BAKE=build/t188/s010/after.json python3 -m pytest tests/acting/test_e909_beats.py
python3 docs/evaluation/interaction/T-186/cup_span.py 57 67 1 build/t188/s010/after.json
sh docs/evaluation/interaction/T-171/build_measure.sh
build/fast-dev/measure_t171 $B/shot.resolved.scene.json --hand girl L 36 175 > measures/e909_s010_girlL_after.json  # boy: --hand boy R 88 240
python3 docs/evaluation/interaction/T-185/summarize.py measures --prefix e909_s010_ --from 50 --contact 58 --carry 88 162 girlL_before girlL_after
FRAMES=44-72 BUILD=$B sh docs/evaluation/interaction/T-171/bake_blend.sh $B/shot.resolved.scene.json build/t188/blend_after
HI_CAM="-0.24 0.90 0.30 -0.07 0.53 0.01 85" HI_FRAMES=46,52,56,58,62,66 SHOT_FRAME=66 sh docs/evaluation/interaction/T-185/render_views.sh build/t188/blend_after 50 70
python3 docs/evaluation/interaction/T-185/make_clip.py clips/e909_pickup_f50-70 50 70 before=build/t188/blend_before/views after=build/t188/blend_after/views
python3 tools/review/shot_sheet.py docs/evaluation/interaction/T-188/strict_sheet.json
```
