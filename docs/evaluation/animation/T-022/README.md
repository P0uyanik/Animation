# T-022 evidence: believable hand interaction (e905_props_test/s010)

**Shot** `episodes/e905_props_test/shots/s010/shot.scene.json` (written by `episodes/e905_props_test/make_shot.py` from the
package skeletons): 72 frames at 24 fps (3 s), 640×360. The boy (spec + `boy_yellow_hoodie.1.1.0.override.json`,
unpublished build) grasps a felt cup (`content/assets/felt_cup.asset.json`, preset `felt`) from a small table with
his right hand (contact f17), lifts it (f19–30), hands it to the girl (current spec) who grasps its lower grip with
her right hand (contact f46); he lets go (f51) and looks at her; she draws it towards herself (f52–68).
Only shared actions: `grasp`, `hold`, `handover`, `hold` (+ idle base clips, a look, `happy` emotion on the girl).

**Commands**
```bash
python3 episodes/e905_props_test/make_shot.py --boy-package <build>/packages/boy_* --girl-package <build>/packages/girl_*
python3 pipeline/production/run_shot.py --shot episodes/e905_props_test/shots/s010/shot.scene.json \
    --blender <blender> --run-dir t022 --video
python3 pipeline/clips/t022_contact_sheet.py --frames <build>/runs/t022/render --bake <build>/runs/t022/bake.json \
    --out docs/evaluation/animation/T-022
# measure_e905.cpp: build command in its header; output -> e905_measurements.json
```
Blender: bpy 5.3.0 (Python 3.13 venv) behind a `blender` wrapper. Cycles 16 samples, OIDN denoising.

**Results**
| Check | Result |
| --- | --- |
| Contacts (engine, `e905_measurements.json`) | boy palm → `grip` at f17: 0.00003 mm; girl palm → `grip_b` at f46: 0.00003 mm; boy still on `grip` at f46: 0.00006 mm |
| Prop jump across parent switches | f17: 0.0001 mm, f46: 0.0004 mm |
| Cup in hand while held (palm → socket drift) | boy f17–46 ≤ 0.0001 mm, girl f46–72 ≤ 0.0001 mm (no slide) |
| Cup upright | min cos to +Y = 1.0 over the shot |
| Max cup speed | 13.8 mm/frame |
| Compile warnings | none |
| Bone reconstruction in Blender | boy 0.0008 mm, girl 0.0004 mm |
| Render | 30.4 s setup + 482.9 s render (6.71 s/frame); whole run 516 s wall clock; mp4 72 frames, 3.000 s |

`e905_contact_sheet.png`: beats f1, f17, f30, f46, f51, f72 (top) with a crop following the cup (bottom).
`e905_s010.mp4`: the rendered shot. `e905_shot_render.json`: Blender report (prop: `prop.felt_cup`, cylinder,
preset `felt` found).

**Visual notes (honest)**: the grasp reads as a mitt wrapped round the cup side (plush hands have a thumb and one
finger digit); fingers do not visibly interpenetrate in the crops, but no collision check exists. The girl's hand is
on the far side of the cup, partly hidden. Girl boots/hair look as in the known T-026 issues (not touched here).
