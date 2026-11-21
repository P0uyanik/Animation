# T-171 round file (keep current; a fresh session takes over from here)

Round 3, 2026-11-21. Branch `t-171-claude-hands-r2`, input `origin/main` `7135087` (merged). Status: **CHECKPOINT**.

## Owner feedback this round answers (2026-11-21 ~12:30Z)
- "opt-in + proposed cup site" is the most natural direction; fingers too open: close them more around the cup.
- Defects: fingers bend the wrong way (outward), finger positions unclear, hands do not move properly relative to the body.
- Include: thumb-down grip in e910 (reach planner), little finger ~7 mm into the cup on the way in.
- Everything stays opt-in. The cup site stays a build-folder variant. T-157 (a) stays opt-in.

## Targets
| target | measure (`measure_t171`, on the mesh) | state |
| --- | --- | --- |
| nothing of the hand inside the cup, held | `mesh_in_mm` at f84 | r3 / r3site: palm 0.0, thumb 0.8, fingers 0.2 mm (default: palm 9.6 mm) |
| nothing inside on the way in | `mesh_in_mm`, largest f50-75 | r3 / r3site: 0.0 (default 7.8 / 4.2 / 5.0 mm) |
| no digit bent backwards or turned round | `turn_deg`, `flex_deg` | thumb turned 36 deg (default 138, r2site 178); thumb laid back 23 deg; fingers only flex |
| fingers closed round the cup | `flex_deg`, pictures | all three joints flex (14 / 8 / 6 deg), pads on the cup; they reach less far round than the default (see open defects) |
| thumb up | `thumb_up` | r3: up. r3site: down (authored grasp point) |
| hand and arm | `wrist_deg` | r3: bend 45, twist -74 at hold. Default: 10 / -124. Carry: r3 up to 93 deg bend (open) |

## Current overrides (variants, `make_variants.py`; all on the build-folder copy of the cup with the proposed site)
- `r3site`: `fingerClose {rest, wrap: true, clear: 0.006}`: authored grasp point, hand thumb down.
- `r3`: `r3site` + `grip: "natural"`: grasp point turned about the cup's axis, thumb up, elbow keyed forward.
- Proposed cup site (unchanged from round 2): socket `grip` at 50 mm, `side_a` band 0-100 mm.

## Open defects / decisions
1. **Thumb up hides the hand from the shot camera.** With the right hand thumb up at the boy's side the forearm (elbow
   forward) is between the camera and the hand. Owner picks: r3site (visible, thumb down) or r3 (thumb up, hidden), or a
   staging change (cup further from the boy / in front of him).
2. **Carry and hand-over with r3:** wrist bend up to 93 deg at f100-135 (default 57), elbow above the shoulder. The elbow
   is planned for the contact pose only. Needs a per-frame elbow plan for carry / pass (touches `actions.cpp` carry: T-175).
3. **Fingers reach less far round the cup** than in the default: the cup now rests where the fingers begin, not 23 mm
   further into a palm it used to sink into. Closing further means letting the plush palm give (a "press" depth): not done.
4. Staging: the boy's hanging hand starts under the table edge, 18 cm from the cup with a 27 cm arm. Any grip is cramped.
5. Girl (old test package): 2.7 mm of the thumb stays in the cup with `wrap` (3.2 mm without).
6. From T-175: popping on hands in sit / stand comes from `planArmLift` (arm-body clearance): not looked at this round.

## Sheets and clips (round 3)
- `r3_strict_pickup.jpg`, `r3_back_shot.jpg`, `clips/r3_pickup_f62-84_24fps.mp4`, `clips/r3_pickup_f62-84_8fps.mp4`.
- Round 2 (superseded, kept): `strict_reach_close.jpg`, `strict_back_rest.jpg`, `shot_size.jpg`, `clips/pickup_f62-84_*.mp4`.

## How to continue
```
python3 pipeline/production/run_shot.py --shot episodes/e910_showcase/shots/s010/shot.scene.json --blender blender --stages prepare
B=episodes/e910_showcase/shots/s010/build
python3 docs/evaluation/interaction/T-171/make_variants.py $B/shot.resolved.scene.json base r2site r3site r3
sh docs/evaluation/interaction/T-171/build_measure.sh           # measure_t171 + preview_t171 (same flags as the engine)
build/fast-dev/measure_t171 $B/t171_site/t171_r3.scene.json --hand boy R 47 150 > measures/r3_r3.json
build/fast-dev/preview_t171 $B/t171_site/t171_r3.scene.json --out /tmp/pv --hand boy R --frames 68,76,84 \
    --view hi 0.16 0.90 0.30 -0.01 0.53 0.0 85                  # 9 s: the cheap preview, digits coloured
FRAMES=58-86 sh docs/evaluation/interaction/T-171/bake_blend.sh $B/t171_site/t171_r3.scene.json $B/r3_r3
```
Read sheets as crops of at most 1024 px.
