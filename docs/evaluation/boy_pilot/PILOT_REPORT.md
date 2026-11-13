# Automated Blender character production test: `boy_yellow_hoodie` pilot (v6)

_2026-11-13. Scope: the automated pilot described in `docs/BOY_HYBRID_PRODUCTION_FEASIBILITY.md` §9, without any human
artist (product-owner decision). Built entirely by Blender Python scripts. The C++ engine is unchanged, Blender is not
integrated into Plush Studio, and iteration 5 has not been started._

## 1. Blender used, and the installation on your computer
| Item | Finding |
| --- | --- |
| Blender on your computer | **Not reachable from this session.** This session runs in a cloud container. No folder on your computer is shared with it (checked: none listed), and no Blender binary exists in the container. Nothing was downloaded or installed |
| Blender used for this test | Official **Blender 5.3.0 as a Python module** (`bpy`, PyPI), in a scratch environment outside the project: the same one used for the earlier feasibility tests. Headless, Cycles CPU |
| Your installation | Every script takes the Blender command as a parameter. The run commands for your own Blender are in §8; they were not executed with it, so its version and Python access are **not verified** |

## 2. What was built (all automated)
`pipeline/blender/boy_pilot/build_boy_pilot.py` builds the master in about 10 s, headless:

| Area | How it is built |
| --- | --- |
| Proportions | Every height and width comes from the reference measurements (colour-segmented profiles of #27 and #7; face landmarks annotated on #27 and #7). Total height 1.10 m |
| Head and face | Lofted superellipse head with brush-style shaping (sockets, full low cheeks, button nose, soft chin) |
| Eyes | Separate eyeballs with a procedural brown iris and pupil. Half-closed upper-lid shells with a thick lash line; lower lids |
| Mouth and brows | Small frown mouth; thin dark brows (sulky inner ends) |
| Ears | Pink |
| Hair | Felted clump meshes in 6 groups (fringe chunks to the brows, crown tufts, crown centre, top layer, flaring sides, 4 back layers), plus stray strands, over a hair mass. Noise-displaced felt surface plus about 400k fibres |
| Hoodie | Mustard teddy-fleece body with ribbed hem and cuffs, hood roll and hood, kangaroo pocket, cream undershirt, drawstrings with darker tips |
| Lower body | Charcoal fleece trousers, cream socks |
| Shoes | Chunky yellow felt shoes with cream toe cap, sole and two straps |
| Backpack | Charcoal-plum body, pocket and handle; webbing straps with buckles |
| Fur | Short fibres on the hair, hoodie, trousers and shoes |
| Pose | A-pose (TD-36) |
| Materials | Albedos found by **automatic colour calibration** (`calibrate_colors.py`). The loop renders a region-ID image, measures each region in the same height bands as the references, and corrects the albedo in linear space. Converged in 9 iterations |
| Rig | Rigify human metarig fitted to the measured joints → 410 bones, 73 deforming. IK/FK arms and legs with poles, 3-joint fingers and thumb, eye bones (gaze) |
| Weights | Automatic (heat) weights, then a per-object allowed-bone filter, a fill from the nearest weighted vertex, a 4-influence limit and normalisation. A nearest-bone fallback covers objects where heat weighting fails silently. Rigid parts are bound to one bone |
| Shape keys | Blink (lids and lashes), BrowDown, Smile, JawOpen |
| Exports | `boy_yellow_hoodie_pilot_master.blend` (A-pose, rigged); `…_compare.blend` (arms lowered through the rig as in #27, fur on the posed surfaces); `…_pilot.glb` (meshes, 73-joint skin, weights, 4 morph targets) |

## 3. Results against the pilot criteria (feasibility §9), same 6 measured views as the baseline
| Criterion (target) | Iteration 4 baseline | **Pilot v6** | Pass? |
| --- | --- | --- | --- |
| Mean silhouette IoU (≥ 0.88) | 0.789 | **0.841** (#27 views 0.84–0.85; #7 0.81) | **No** (improved) |
| Head + hair fraction of height (±5%) | +15.3% | **+3.9%** | Yes |
| Head width (±7%) | +12.8% | +5.6% | Yes |
| Torso width (±7%) | −4.4% | −5.4% | Yes |
| Leg width (±7%) | −14.1% | −9.1% | **No** (improved) |
| Feet width (±7%) | −30.3% | −7.6% | **No**, borderline (improved) |
| Mean outline distance (no target set) | 1.72% of height | **1.43%** | — (improved) |
| Hair outline distance (≤ 3% of head height) | 3.27% | **3.40%** | **No** (not better than baseline) |
| Face landmarks, #27 front (±8%) | not measurable | eye spacing +7.2, mouth +3.9, nose +6.3, chin +8.1, ear width −8.0, eye line −1.7 | **No** (2 of 6 just over) |
| Face landmarks, #7 (±8%) | not measurable | nose +25, chin −19, eye line −12, others within ±9 | **No** (see §5) |
| Colour ΔE2000 per region (≤ 8) | not measured | hair 3.6, hoodie 2.0, trousers 3.9, shoes 3.9, cream 2.2; skin 1.5–2.6 in front views | Yes, except skin in the back views (11.5 / 22.7: ears and neck too dark and saturated) |
| Automation: rig + weights + export headless, no manual step | — | Yes. 0 unweighted vertices after cleanup; glTF round trip keeps 73 joints, 54 skinned meshes and 4 morph targets | Yes |
| Your visual approval of face and hair | — | **pending** | — |

Evidence (`docs/evaluation/boy_pilot/`):
- `pilot_v6_vs_it4_measured_views.jpg`: reference | Iteration 4 | pilot, 6 measured views.
- `pilot_v6_vs_it4_visual_views.jpg`: the same for the #29 and #8 views.
- `pilot_v6_face_closeups.jpg`, `pilot_v6_turnaround.jpg`, `pilot_v6_rig_expression_tests.jpg`.
- `pilot_v6_metrics.json`, `pilot_v6_silhouette_measurements.json`, `pilot_v6_rig_tests.json`,
  `pilot_color_calibration_history.json`.
- The Iteration 4 baseline (`renders/compare/it4_boy/…` and `docs/evaluation/blender_harness/`) is unchanged.

## 4. Rig and expression tests (rendered; see `pilot_v6_rig_expression_tests.jpg`)
| Test | Result |
| --- | --- |
| Arms raised, elbows 90°, hip and knee bend, head turn and tilt (FK controls) | Deform without tearing. Trousers, straps and cuffs stay with their bones after the weight fixes. Hair follows the head |
| Gaze (eye controls) | Irises rotate with the eye bones |
| Blink | Lids close, but the closed lids **bulge out over the eyes** (the lid shell is too large) |
| Smile / JawOpen | Visible but small. The mouth is a surface patch: **no jaw rotation, no teeth or mouth cavity** |
| BrowDown | Barely visible: the brows are under the fringe, as in the references |

## 5. What does not work yet (by impact on identity)
1. **Hair silhouette.**
   - It is chunky and felted, but reads as a rounded mop. The references have a messier, spikier outline: fewer,
     longer tufts sticking up and out, with gaps.
   - Hair outline distance is 3.40% of head height: no better than Iteration 4 (3.27%).
   - An attempt at more irregular tufts (v4) made every outline metric worse and was reverted, based on the
     measurements.
2. **Surface texture.** Mean colours match, but the reference hoodie and trousers have strong pile texture
   (bouclé/teddy). The pilot's fur is short and the surfaces read smoother and more saturated.
3. **Face.**
   - Landmarks are within ±8% on #27, except the chin (+8.1%) and ear width (−8.0%).
   - On #7 several ratios fail. #7 itself disagrees with #27 by about 8–10%, and its estimated camera elevation (18°)
     is uncertain.
   - Closed lids bulge; the mouth has no real opening.
4. **Legs and shoes.** The trousers are about 9% too narrow; the feet are about 8% too narrow.
5. **Ears and neck colour.** Too dark and saturated from behind (ΔE 11.5–22.7). From the front, skin matches
   (ΔE 1.5–2.6).
6. **Reproducibility.** Rebuilding gives identical geometry (largest difference 0.24 µm), but modifier evaluation
   changes the vertex order, so files are not byte-identical. A canonical vertex-sort step is needed for
   hash-stable exports.
7. **Fur.** The fur curves are generated once on the posed comparison surfaces and do not follow the rig. The master
   carries no fur. glTF cannot carry curves (known; USD/Alembic needed).

## 6. Iterations, all measured with the same harness
| Version | Change | Mean IoU | Notes |
| --- | --- | --- | --- |
| v1 | first full build | 0.809 | ears rotated about the world origin (bug); hair 7.5 cm too tall |
| v2 | ears fixed, face from landmarks, hair height and width | 0.827 | harness framing bug found (rig widgets counted) |
| v3 | eye spacing, mouth, chin; harness fixes; #27 views without the backpack body (§2.6 item 20) | 0.830 | |
| v4 | irregular hair, slimmer soles | 0.822 | **reverted**: all outline metrics worse |
| v5 | weight scoping, blink direction, gaze shader, ear colour | 0.825 | silent heat-weight failure on the cuffs found |
| v6 | nearest-bone fallback | **0.841** | current result |

Harness fixes made along the way (evaluation tooling, not the engine):
- `.blend` subjects can be loaded.
- The subject's own materials can be kept.
- Landmark projection.
- Rig widgets are no longer rendered or counted in the framing box.
- Parts a reference view does not show can be hidden, declared per view in the index.

## 7. Performance (cloud container, 4 CPU cores, no GPU)
- Build, master + compare + glTF: 10.4 s.
- Colour calibration: about 2 min for 4 iterations.
- Harness: 16 views in 135 s.
- Region renders and metrics: about 1 min.
- Rig tests: about 1.5 min.

## 8. Running it with your own Blender (not executed here)
Run from the repository root; replace `blender` with your Blender executable:
```
blender -b --factory-startup -P pipeline/blender/boy_pilot/build_boy_pilot.py -- --out out/pilot --stage all
blender -b --factory-startup -P pipeline/blender/compare_harness.py -- --subject out/pilot/boy_yellow_hoodie_pilot_compare.blend --index assets/characters/boy_yellow_hoodie/references/reference_index.json --out out/pilot/harness --keep-materials --fill 0.94
python3 pipeline/compare_sheet.py --index assets/characters/boy_yellow_hoodie/references/reference_index.json --blender out/pilot/harness --out out/pilot/report
```
The scripts need only Blender's bundled modules (bpy, numpy, Rigify) and, for the sheets and metrics, a Python with
numpy and Pillow.
