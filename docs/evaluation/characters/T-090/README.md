# T-090 reference-fit results

The boy's best proposal scored **70.53 / 100** (+2.84) and the girl's scored **67.61** (+0.25). Both started from the approved spec at `12559bb86671ea6d72697faa9877b4db5e250c30` with no starting overrides. Each search used seed 2, three builds and nine 320 × 640 Workbench passes. The proposals await owner review.

| Character and pose | Start → best | Front | Three-quarter | Side | Upper lid edge | Inner brow position |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Boy 2.0.0, arms down | 67.70 → 70.53 | 71.76 → 74.13 | 69.78 → 74.74 | 61.54 → 62.73 | 6° → 16.94° | 0.400 → 0.508 |
| Girl 0.11.0, A-pose | 67.37 → 67.61 | 71.90 → 72.05 | 65.20 → 65.41 | 65.00 → 65.38 | 43° → 48.85° | 0.550 → 0.705 |

The boy's largest gain was at three-quarter, where visible-eye IoU rose from 0.286 to 0.430. The girl's front eye IoU moved from 0.391 to 0.396, while her annotated inner brow error increased from 0.047 to 0.056 head heights. The girl's Workbench review renders her glasses lenses opaque. The fit pass omits the lenses so the overlay shows the measured eye openings.

## Review evidence

| Character | Overlays | Review images | Numerical evidence | Proposed override |
| --- | --- | --- | --- | --- |
| Boy | [Start](boy/start.jpg) · [Best](boy/overlay.jpg) | [First frame](boy/preview.jpg) · [Six-row Workbench sheet](boy/workbench-sheet.jpg) | [Start → best by landmark and view](boy/scores.csv) · [All trials](boy/scores.json) | [Proposal](boy/proposal.json) · [Bounds](boy/bounds.json) |
| Girl | [Start](girl/start.jpg) · [Best](girl/overlay.jpg) | [First frame](girl/preview.jpg) · [Six-row Workbench sheet](girl/workbench-sheet.jpg) | [Start → best by landmark and view](girl/scores.csv) · [All trials](girl/scores.json) | [Proposal](girl/proposal.json) · [Bounds](girl/bounds.json) |

Grey shows the reference figure, magenta the aligned candidate contour, teal the annotated eye region and gold the visible candidate eye pixels. White lines join reference landmarks to their measured positions. Scores average figure IoU, annotated eye IoU and normalised landmark agreement in each view. Higher is better for the composite and IoU. Lower is better for the individual landmark errors in the CSVs.

Both `recipe.py preview` runs passed. Upper arms measured 12° from vertical in both boy columns and 32° in both girl columns. The reviewed previews preceded the 320 px Workbench renders. Each six-row sheet uses the T-087 renderer, pose checks and compositor, with reference, approved and candidate columns and identical cameras for both builds.

| Character | Recipe | Preview record | Workbench sheet record |
| --- | --- | --- | --- |
| Boy | [Input](boy/recipe.json) · [Resolved](boy/recipe.resolved.json) | [Pose and cameras](boy/preview.json) | [Settings, cameras and times](boy/workbench-sheet.json) |
| Girl | [Input](girl/recipe.json) · [Resolved](girl/recipe.resolved.json) | [Pose and cameras](girl/preview.json) | [Settings, cameras and times](girl/workbench-sheet.json) |

## T-087 strict Cycles sheets

| Character | Strict sheet | Recipe |
| --- | --- | --- |
| Boy, approved 2.0.0 | [Reference, approved and fit candidate](boy/strict-sheet.jpg) | [Boy strict recipe](boy/strict-recipe.json) |
| Girl, approved 0.11.0 | [Reference, approved and fit candidate](girl/strict-sheet.jpg) | [Girl strict recipe](girl/strict-recipe.json) |

Both strict recipes passed the 2-spp, 120 px Cycles preview before the 16-spp, 360 px sheet render. Both use `fit: head` for the front and three-quarter face cameras. On both 840 x 2048 JPEGs, the approved and candidate face rows show the full head from hair top to chin at both angles. The T-087 reference crops clip the boy's hair and chin in front view and the girl's bun at both angles.

## Wall time

Each trial includes a procedural build, three Workbench frames, registration, scoring and its overlay. The two searches ran concurrently. Times below are wall seconds per character. Preview and sheet times are additional to the fit totals.

| Character | Start | Proposal 1 | Proposal 2 | Fit total | Preview | Workbench sheet |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Boy | 210.6 s / 67.70 | 224.1 s / 70.48 | **220.7 s / 70.53** | **655.6 s** | 39 s | 71.9 s |
| Girl | 179.5 s / 67.37 | **207.0 s / 67.61** | 143.3 s / 66.71 | **530.0 s** | 48 s | 78.4 s |

## Reproduction and checks

Run from the repository root with Blender 5.3.0 and Python with NumPy and Pillow. This run used Python 3.12.14 because the specified Python 3.14 executable returned access denied. Each recipe identifies the base spec and its current published baseline. The winning override was applied last, and the resulting canonical spec hash was checked against the winning Blender build before reuse in review.

```sh
python tools/fit/run.py --spec assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0.spec.json --bounds docs/evaluation/characters/T-090/boy/bounds.json --views val27_front,val27_threequarter_right,val27_side_right --seed 2 --budget 3 --height 640 --blender <exe> --out build/reproduce-boy
python tools/fit/run.py --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.11.0.spec.json --bounds docs/evaluation/characters/T-090/girl/bounds.json --views sheet30_front,sheet30_front_left,sheet30_left --seed 2 --budget 3 --height 640 --blender <exe> --out build/reproduce-girl
```

- Fit unit and integration tests passed, 7/7. The repository Python check in `tools/check_all.py` also passed. Its fixed list runs separately from fit test discovery.
- Existing review-recipe tests passed, 17/17. Replaying the search and scorer over the saved Workbench passes reproduced both winners, all six build-spec hashes and all 18 view scores.
- The guarded-path check reports that `tools/fit/tests/test_fit.py` needs the supervisor approval trailer at merge.
