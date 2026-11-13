# Reference comparison harness (evaluation phase, `boy_yellow_hoodie`)

Purpose: judge any candidate model of the boy against the reference package from the **same camera angles**, in Blender
and in Plush Studio, with silhouette measurements. This is the yardstick for approving the model and for TD-35's
Blender-vs-C++ comparisons. Evaluation tooling only: no engine changes, no final character.

## Pieces
| File | Role |
| --- | --- |
| `assets/characters/boy_yellow_hoodie/references/reference_index.json` | All uploads (SHA-256, class, priority, stored or duplicate), decisions, missing data, and **16 camera-matched views**: crop box, yaw, elevation, lens estimate, pose, backpack, whether a silhouette can be measured |
| `pipeline/reference_views.py` | Crops each view from the reference sheets; extracts silhouettes for views on plain backgrounds (6 views: #7 and five from #27) → `references/views/` |
| `apps/export-obj` (`plush-export-obj`) | Writes a posed Plush scene frame as OBJ + MTL (meshes; straps/cords as tubes; fibres skipped). A separate tool that links the unchanged engine |
| `pipeline/blender/compare_harness.py` | Runs inside Blender headless: imports the subject (OBJ or glTF), neutral studio lighting, one camera per view, Cycles renders with transparent background, `cameras.json` (Blender and Plush coordinates), optional `.blend` of the rig |
| `pipeline/plush_views.py` | Renders the same cameras with Plush Studio's renderer (full fibre look) in one run |
| `pipeline/compare_sheet.py` | Sheet per view: reference, Blender render, Plush render, silhouette overlay; `measurements.json` |
| `pipeline/blender/install_blender.sh` + `BLENDER_VERSION` | Pinned official Blender: download, SHA-256 verification, unpack to `~/.plush-studio/blender/<version>/` |

## Conventions
- **Yaw** is defined by what is visible, not by sheet labels (the labels in #8 and #29 contradict each other):
  - 0 = camera in front;
  - +90 = camera on the character's left, face pointing screen-left;
  - −90 = his right side;
  - 180 = behind.
- **Elevation and lens** are estimates (about 6° above eye level and 70 mm for the turnaround sheets; 18° and 50 mm
  for the original #7).
- **Framing:** the subject's full height fills 94% of a 360×720 frame. Silhouettes are compared after scaling to the
  reference figure's height and aligning feet and centre, so framing differences do not count.
- **Coordinates:** Plush is Y-up with the character facing +Z; Blender is Z-up with the character facing −Y; plush
  (x, y, z) = blender (x, z, −y). Verified: Blender and Plush renders of the same camera line up.

## Measurements (`measurements.json`)
| Measure | Definition |
| --- | --- |
| `iou` | Silhouette overlap with the reference, 0–1 |
| `head_fraction` | Head + hair height ÷ figure height. The head ends at the narrowest row between 22% and 50% of the height |
| `width_head` / `width_torso` / `width_legs` / `width_feet` | Widest extent in the 0–38 / 38–65 / 65–92 / 92–100% bands ÷ figure height |
| `aspect` | Figure height ÷ widest extent |

Limits:
- Silhouettes ignore interior detail (face, colours). The sheet is for judging those by eye.
- Reference silhouettes include the backpack straps; #27's back views show no backpack.
- Pose differences count against IoU, e.g. hands in pockets vs. arms down.

## Run
```
build/apps/export-obj/plush-export-obj content/scenes/compare_it4_boy.scene.json --out renders/compare/it4_boy/it4_boy.obj
python3 pipeline/reference_views.py
<blender> -b --factory-startup -P pipeline/blender/compare_harness.py -- --subject renders/compare/it4_boy/it4_boy.obj \
    --index assets/characters/boy_yellow_hoodie/references/reference_index.json --out <out>/blender --fill 0.94
python3 pipeline/plush_views.py --scene content/scenes/compare_it4_boy.scene.json --cameras <out>/blender/cameras.json --out <out>/plush
python3 pipeline/compare_sheet.py --index assets/characters/boy_yellow_hoodie/references/reference_index.json \
    --blender <out>/blender --plush <out>/plush --out <out>/report --label "<subject>"
```
