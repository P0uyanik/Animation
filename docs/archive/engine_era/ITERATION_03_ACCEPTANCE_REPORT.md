# Iteration 3 — acceptance report

_Date: 2026-11-13. Hardware for every number here: cloud build container, 4-core Intel Xeon @ 2.1 GHz, 15 GB RAM,
no GPU. Your computer has not been measured; nothing below is a measurement of it._

**Verdict:** stable checkpoint. The three reference characters exist, are recognisable side by side, and act together
in a water-table scene. Visual quality is clearly better than Milestone 02 but **not yet at reference quality**
(see "Still below the references"). Status words: Implemented · Tested · Visually inspected · Incomplete · Not tested.

## Evidence against the acceptance criteria
| Area | Evidence (renders/it3/ unless noted) | Status |
| --- | --- | --- |
| Character design | `lineup_front_1280x960.png` — A, B, C | Implemented, visually inspected |
| Character consistency | `lineup_front`, `lineup_threequarter_960x720`, `lineup_side_960x720` (same assets, three yaws) | Visually inspected; automated guard only for the v2 face (see Regression) |
| Hair | `hair_A_closeup_1000x800.png`, `faces_ABC_preview.png` — layered locks, coiled buns, spiral curls, clumps, fibre halo | Implemented, visually inspected; fringe still reads as cords |
| Face | `face_A_happy_1200x900.png`, `face_B_900.png`, `face_C_900.png` — lashes, lids, brows, glasses | Implemented, visually inspected; mouth-corner crease when smiling |
| Expressions | `expression_sheet_A_10.png` — neutral, happy, surprised, sad, annoyed, blink, look left/right/down, look at camera | Implemented, visually inspected |
| Clothing | `cloth_A_dress.png` (knit geometry), `cloth_B_vest_blouse.png` (blouse, buttons, knit vest, pockets), `cloth_C_hoodie.png` (fleece, pocket, strings, straps) | Implemented; seams and motifs incomplete |
| Materials | Knit (dress, vest), fleece (hoodie, joggers), felt (shorts, bow, hair cores), suede (boots), skin, glass, water | Implemented; skin subsurface scattering not implemented |
| Group composition | `group_watertable_1280x720.png` | Implemented, visually inspected |
| Animation | `docs/milestone03/m03_watertable_640x360.mp4` — 72 frames, 3 s | Implemented, rendered (35.3 min total, 29.2 s/frame average) |
| Interaction | Fold (staged), hold (attach), reach (IK), release, float, ripples, gaze/reactions | Implemented; grasp is attach-based, fingers do not pose |
| Environment | Classroom scene file (walls, windows, shelf, books, cushions, drawings, water table, pebbles), editable as JSON and in Studio's inspector | Implemented; prop authoring UI limited to existing object types |
| Camera | Full body (lineup), group (milestone 03), face close-ups, clothing close-ups, camera push-in | Implemented |
| Rendering | 1280x960, 1280x720 and 1200x900 finals | Implemented |
| Performance | Table below | Measured on the cloud machine only |
| Regression | Milestone 01, face (v2) and new A/B/C lineup reference images | Tested: pass (3 image regressions) |
| Editor | `studio_hair_edit.png`, `studio_reopened.png` — hair-lock panel, curve tubes in the viewport | Implemented; edits driven by a script using the same functions as the buttons, not clicked by a person |
| Project management | Edit → save → close → reopen: lock count 40 → 41 and a new camera key survive the round trip | Tested (automated) |

## Render measurements (cloud machine)
| Render | Resolution | Samples (adaptive 0.1) | Scene build | Render |
| --- | --- | --- | --- | --- |
| Lineup front (3 characters) | 1280x960 | 64 | 2.8 s | 52.9 s |
| Lineup three-quarter / side | 960x720 | 64 | 2.8 s | 27.8 s / 26.0 s |
| Face A close-up | 1200x900 | 120 | 1.9 s | 166 s |
| Face B / C close-up | 900x900 | 80 / 56 | 5.6 s / 4.8 s | 68 s / 61 s |
| Hair A close-up | 1000x800 | 96 | 4.9 s | 118 s |
| Clothing close-ups | 800x600 | 48–64 | 4.5–5.2 s | 29–37 s |
| Group water table | 1280x720 | 96 | 3.1 s | 160 s |
| Milestone 03 animation | 640x360 x 72 frames | 32 | 3.3 s per frame (+18 s once) | 29.2 s per frame, 35.3 min total |

**Memory:** peak resident memory while rendering a milestone 03 frame (3 characters, ~5.2M triangles, ~6M fibre
segments after level of detail): **3.0 GB** (sampled every 0.5 s).
| Character builds (A / B / C) | — | — | 6.8 s / 4.6 s / 3.9 s | — |

## Tests run
- `plush_tests`: 16 unit test cases (time, curves, SDF mesh, skin weights, skinning, IK, eye aim, DQ skinning, morphs,
  energy conservation, pdf consistency, scene JSON, determinism, fibre orientation, lock groups, glass shadows) — pass.
- `regression_milestone01`, `regression_face_neutral`, `regression_lineup_abc` — pass (milestone 01 untouched).
- Studio round trip (`--script-hair-edit`, then `--script-verify` in a new process) — pass.

## Still below the references
1. Skin: no subsurface scattering; close-ups look slightly matte/plastic.
2. Fringe of A reads as separate cords; B's crown/parting is too regular; overall hair lacks the soft "felted mass" of the references.
3. Mouth corners crease in smile shapes; no teeth/tongue for open mouths.
4. Garments lack seams, cuffs with ribbing, the skirt's relief pattern and the vest's embroidered motifs.
5. Hands: fingers do not pose (grasp is an attachment); no finger contact on the paper.
6. Paper folding is a staged blend, not a crease-by-crease fold.
7. The classroom is sparser than the references (no bunting, posters with real drawings, toy shelves).
8. The water-table action is small in the wide shot; camera cuts to close-ups (step-keyed camera) are possible but not used yet.
9. Editing is numeric for hair; no drawing locks in the viewport, no undo, no gizmos; new characters are made by script.
