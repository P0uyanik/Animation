# T-087 evidence: review recipe and fidelity fixes

- `boy_1.1.0_vs_2.0.0.recipe.json`: the boy's previous approved 1.1.0 vs the current 2.0.0 (both published), compare
  variant (arms down, the pose of reference #27). Run with:
  `recipe.py preview` (2 spp, 120 px: 50 s), then `recipe.py sheet` (Cycles 16 spp, 360 px: 5 min, both columns in one
  run). Blender: bpy 5.3.0 module (Python 3.13) behind a `blender` wrapper, CPU.
  - `boy_1.1.0_vs_2.0.0/boy_1.1.0_vs_2.0.0_strict.jpg`: the standard strict sheet (840 x 2048).
  - `boy_1.1.0_vs_2.0.0/preview/preview.jpg` + `preview.json`: the recorded first frame the sheet required.
  - `recipe.resolved.json`, `sheet.json` (cameras, pose probe: upper arm 5.5 deg (1.1.0) and 12 deg (2.0.0) from
    straight down, Blender version, seconds), `log.txt`.
  - The first `sheet` call without a preview was refused; a preview of an earlier recipe edit was rejected as
    "made for a different recipe" (both in the run log of this task, not repeated here).
- `girl_0.10.0_vs_0.11.0.recipe.json`: the T-081 strict comparison as a recipe; the girl's references are an A-pose
  turnaround, so the A-pose master is requested explicitly (`compare.allow_apose`). Validated (unit tests), not
  rendered (the T-081 sheet already exists).
- `tools/fidelity/run.py` on the published 2.0.0 master (no compare file next to it) now stops with: "...
  boy_yellow_hoodie_compare.blend does not exist next to boy_yellow_hoodie_master.blend ... The A-pose master is never
  used as a silent fallback." (before T-087 it rendered the A-pose master with only a warning).
