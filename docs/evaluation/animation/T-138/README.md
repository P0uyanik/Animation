# T-138 (E4): grasp contact accuracy — checkpoint 1 (BLOCKED on write-set)

Input `8f6c565` (`integration/t-134`). e910 s010 baked as is (`run_shot --stages prepare,bake`, bpy 5.3.0 module, 0
warnings); measured with T-051's `measure_t051` (scratch build), boy R `grip` band 45-90 mm, f79-137; girl L `grip_b`
10-55 mm. No engine code is committed: all levers below were scratch experiments (env-var switches, reverted).

## Baseline (reproduces T-117 §3.4)
| hand | tip gap | deepest | band out | thumb side | tip heights (thumb, index..little, mm) |
| --- | --- | --- | --- | --- | --- |
| boy R (f100) | 0.00 | +12.98 | **10.654** | -18.4 | 44.2, 98.5, 70.7, 62.2, 34.3 |
| girl L (f120) | 0.00 | +7.68 | inside (5.0 margin) | -20.6 | 47.4, 17.3, 27.5, 37.4, 50.0 |

Cause: hands_r2's fingertip skin radius is 13.0 mm (finger roots ~26 mm apart). The solver aims the contacts at
[lo + r, hi - r] = 58-77 mm (19 mm for four fingers); index and little cannot get there by spread (±30° bracket) and
stay at their natural heights. Four 26 mm fingers cannot fit 45 mm without overlapping (middle-ring tips are
already 8.5 mm apart at baseline).

## Levers tried (scratch, boy f100; girl unaffected unless noted)
| lever (where) | band out |
| --- | --- |
| roll the hand about the palm normal ±20/35/50° (interaction.cpp plan) | 18-29 mm (worse: wrapped tips spread further) |
| key the band wider by r (centres, not skin, in band) | 10.654 (index/little unchanged; girl 5.5 out) |
| per-finger base adduction `hand.R.f<k>.y` = 2 / 4 / 6 (interaction.cpp keys) | 6.54 / 2.75 / **0.79** (thumb and little at 44.2) |

The adduction lever is within the write-set but only biases the solver's spread bracket (base spread up to ±63°);
mid-ring tips end 5 mm apart. A real fix belongs in the band solver (`engine/anim/animation.cpp`,
`applyHandPosePerFinger`).

## Open questions (Supervisor)
1. Opt-in key: the scene's `interaction` options are parsed in `engine/scene/scene.cpp` (`interactionOptionsFromJson`
   rejects unknown keys); `scene.cpp` / `scene.h` are outside the write-set. Add them, or another opt-in carrier?
2. Solver: add `engine/anim/animation.cpp` (band step) to the write-set, or accept the adduction-key lever (0.79 mm,
   fingers pressed together), or change the content band (felt_cup, asset owner)?
