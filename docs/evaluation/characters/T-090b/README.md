# T-090b fit proposals

Three independent fits start from the approved character specs at `bb8fada`. Each row links the winning override, the per-landmark and per-view scores, the target measurements and the review images. The face score uses the stock fit objective. The garment scores average trouser/shoe or blouse/shorts mask overlap across the three views. Each scale runs from 0 to 100.

| Proposal | Mean, start → best | Front | ¾ | Side | Evidence |
| --- | ---: | ---: | ---: | ---: | --- |
| [T-089 · girl face](girl-face/proposal.json) | 67.38 → 67.40 | 72.08 → 72.75 | 64.21 → 64.14 | 65.85 → 65.31 | [Scores](girl-face/scores.csv) · [Measurements](girl-face/measurements.csv) · [Preview](girl-face/preview.jpg) · [Strict sheet](girl-face/sheet.jpg) |
| [T-093 · boy trousers and shoes](boy-garments/proposal.json) | 61.10 → 63.90 | 61.82 → 65.37 | 60.03 → 63.44 | 61.46 → 62.89 | [Scores](boy-garments/scores.csv) · [Measurements](boy-garments/measurements.csv) · [Preview](boy-garments/preview.jpg) · [Strict sheet](boy-garments/sheet.jpg) |
| [T-093 · girl sleeves and shorts](girl-garments/proposal.json) | 48.98 → 49.30 | 56.77 → 57.64 | 45.49 → 45.61 | 44.67 → 44.66 | [Scores](girl-garments/scores.csv) · [Measurements](girl-garments/measurements.csv) · [Preview](girl-garments/preview.jpg) · [Strict sheet](girl-garments/sheet.jpg) |

## Fit decisions

**Girl face.** The approved face has no single eye-opening width or height field. With eye radius held at 42 mm, protrusion increased from 4.00 to 5.02 mm. Upper and lower lid edges moved from 43°/−46° to 45.40°/−47.40°, and upper lid curvature increased from 0.120 to 0.142. Cheek fullness decreased from 3.00 to 2.26 mm. The generator adds 7 mm of cheek roundness, giving an effective neutral bulge of 9.26 mm. The references lack a cheek landmark, so review that change in the strict face and side rows.

Front left/right eye widths moved from 24/24 to 25/24 px against 32/30 px in the reference. Front eye IoU rose from 0.395 to 0.415, and side eye IoU fell from 0.297 to 0.282. The lower lid-shell exposure fractions rose from 0.145/0.147 to 0.172/0.164. The small mean gain therefore comes with a more exposed lower lid and a poorer side match.

**Boy trousers and shoes.** The approved garment/1 spec lacks direct inseam, trouser-break fold and shoe-volume controls. Gusset depth fell from 0.700 to 0.242, raising the built gusset bottom from 153 to 243 mm. The front crotch-to-sole gap moved from 111 to 126 px toward the 143 px reference. Trouser length rose from 0.985 to 0.987. The three-quarter hem came within 5 px of its target (12 px at the start), while side hem error increased from 1 to 3 px. The strict side row shows a small skin-coloured gap above the shoe.

Shoe upper height fell from 72.0 to 63.5 mm, extra length from 12.0 to 6.1 mm and extra width from 6.0 to 1.3 mm. Front shoe area fell from 10,506 to 9,439 px² against a 6,120 px² reference. The two garment masks improved in all three views. The stock fit score fell from 69.17 to 68.34, primarily through eye-mask overlap following silhouette registration.

**Girl sleeves and shorts.** Sleeve length rose from 0.970 to 0.977 of the shoulder-to-wrist segment and sleeve puff from 24.0 to 27.2 mm. The front left blouse edge along the reference shoulder-to-palm axis reached 68.9% (67.8% at the start). The right stayed at 68.0%. These are visible mask extents. The left reference mask extends past the annotated palm, so its 116.8% value is sensitive to the annotation.

The approved shorts lack a dedicated leg-split control. The fit used length (0.240 → 0.281), gusset depth (0.800 → 0.558) and inner puff (0.800 → 0.344). Front shorts IoU rose from 0.711 to 0.724, but side IoU fell from 0.674 to 0.633 and the side hem ended 14 px below its reference. In the strict front row the hem still reads as a continuous band between the legs. The largest blouse improvement was in profile (0.220 → 0.260). The longer shorts and the small sleeve change are independent choices for T-093 to review.

The garment overrides carry the entire clothing list because the spec merger replaces arrays. To adopt a fit in the existing T-093 garment/2 candidate, transfer the winning numeric paths listed in its bounds file. This preserves the candidate-specific materials, accessories and break or split controls.

## Reproducing the fits

Use the spec named in each recipe and the adjacent `bounds.json`. Start with the approved spec alone. For each proposal, `tools/fit/run.py` used seed 4, a budget of three builds including the start, and 256 × 512 Workbench passes. The boy uses the arms-down compare pose and the girl uses the A-pose of the reference turnaround. The cameras below are in front, three-quarter and side order. The completed searches used nine builds and 27 fit frames. Garment mask checks used 18 additional Workbench frames from those same builds. The interruption added one completed boy baseline and one partial build.

| Proposal | Reference views | Scored landmarks | Search and review inputs |
| --- | --- | --- | --- |
| T-089 · girl face | sheet30_front, sheet30_front_left, sheet30_left | Eye centres, inner and outer corners on both sides, nose, mouth, chin | [Bounds](girl-face/bounds.json) · [All trials](girl-face/scores.json) · [Recipe](girl-face/recipe.json) · [Resolved](girl-face/recipe.resolved.json) · [Preview record](girl-face/preview.json) · [Sheet record](girl-face/sheet.json) |
| T-093 · boy trousers and shoes | val27_front, val27_threequarter_right, val27_side_right | Chin and nose | [Bounds](boy-garments/bounds.json) · [All trials](boy-garments/scores.json) · [Recipe](boy-garments/recipe.json) · [Resolved](boy-garments/recipe.resolved.json) · [Preview record](boy-garments/preview.json) · [Sheet record](boy-garments/sheet.json) |
| T-093 · girl sleeves and shorts | sheet30_front, sheet30_front_left, sheet30_left | Chin and nose | [Bounds](girl-garments/bounds.json) · [All trials](girl-garments/scores.json) · [Recipe](girl-garments/recipe.json) · [Resolved](girl-garments/recipe.resolved.json) · [Preview record](girl-garments/preview.json) · [Sheet record](girl-garments/sheet.json) |

The stock score for each view averages whole-figure mask overlap (IoU), visible eye-mask IoU and mean landmark agreement after registration to the reference. Higher is better. Landmark errors in `scores.csv` are distances in reference head heights, where smaller is better. For garments, chin and nose are the requested stock landmarks. The silhouette and visible eyes also affect the stock score. The garment tables retain that score alongside the selection score. The winning trial maximizes the mean of the two garment IoUs in each view, with equal weight for all three views and earlier trials winning ties.

The face measurements give the width and height of each visible eye in registered reference pixels. For garments, a second flat-colour Workbench pass on each of the same three builds labels all objects under the two corresponding `garment.<name>.` prefixes. It uses the fit camera and verifies an identical character silhouette before applying the recorded registration. Region IoU measures the visible fabric. Hem height is the lowest visible edge, with image y increasing downward. The front leg gap runs from the central silhouette opening to the sole. Front sleeve reach measures the furthest blouse pixel along each annotated shoulder-to-palm axis, within a corridor extending 20% of that distance on each side.

Review used Blender 5.3.0 and the T-087 recipe cameras and lighting. Each candidate's composed spec hash matched its winning build before reuse. Each `recipe.py preview` ran in Cycles at 2 samples and 120 px. After visual inspection, `recipe.py sheet` rendered the six rows in Cycles at 16 samples and 360 px, producing an 840 × 2048 JPEG. The recipes name the input commit. Per-proposal build hashes below identify the exact local candidates.

| Proposal | Winning trial | Composed candidate SHA-256 |
| --- | ---: | --- |
| T-089 · girl face | 2 | `17f21e33ff0261f5dc2761bd25d7267dcb1a9ceca1241ecfb624ed33c027678a` |
| T-093 · boy trousers and shoes | 1 | `d7665b57b14e1d313556215412ff77387efbea2fad9002cd6f4b3779696d137c` |
| T-093 · girl sleeves and shorts | 2 | `3c46b1bec56eff757ed0c3065f0eaf9053f02f32c87cf21defe1fedc11fd93c9` |

## Verification and wall time

All 7 fit tests and 17 review tests passed. Re-scoring the saved Workbench passes reproduced every trial's per-view score. The preview and sheet records match each recipe hash, pose and settings. Both columns contain all six camera views.

Build and render include the interrupted work and the resumed runs. The ledger counts each wall interval once, dividing overlap equally between active categories. Render includes mask registration, previews, diagnostic passes and sheets. Wait estimates the usage-limit pause from the WIP checkpoint at 20:26 UTC until work resumed at 21:36 UTC. CI time is zero.

ledger: build 16.44 · render 28.98 · tests 0.14 · ci 0 · wait 70.53 (min)
