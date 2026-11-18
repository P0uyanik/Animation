# Review recipe: how every visual task is compared (T-087)

One JSON per visual task locks **what** is compared and **how**, so every owner sheet looks the same and no render is
wasted on the wrong pose or version. Tool: `tools/review/recipe.py`. Examples:
`docs/evaluation/process/T-087/*.recipe.json`.

## 1. Write the recipe
| key | what it locks |
|---|---|
| `inputs` | the input SHAs (`{"main": "<sha>"}`); each must be a commit in the repository |
| `baseline.version` | the published baseline (`versions/index.json`); must be the current approved version unless `allow_not_current` is true |
| `candidate` | one of: `{"version"}` (published), `{"spec", "overrides", "sha"}` (built into `<out>/build/`), `{"blend"}` |
| `compare` | `variant` (`compare` = arms down, `master` = A-pose) and the matching `pose` (`arms_down` / `apose`) |
| `cameras` | lens, one elevation, body/face framing (fixed target and frame height, not framed per model) and the six rows: `front`, `threequarter`, `side`, `back`, `face_front`, `face_threequarter`. A row names a `reference_view` (its yaw comes from `reference_index.json`) or a reference file + crop + `yaw_deg` |
| `light.calibration` | the light rig (`pipeline/charsys/render_calibration.json`, normally `character_neutral/1`) |
| `render` / `preview` | samples and width of the sheet render (Cycles) and of the cheap preview (Cycles ≤ 8 spp or Workbench, ≤ 240 px) |
| `ai_target` (optional) | Higgsfield images per row; shown as a column labelled "AI target" |

Refusals (no silent fallback): an A-pose input (`variant: master`) needs `compare.allow_apose: true`; a variant that
differs from the one the references match (`fidelity_index.json` `render_variant`) needs
`compare.allow_variant_mismatch: true`; a `*_master.blend` given for the compare variant, a version or spec without
`rig.comparison_pose`, an unknown SHA, version, file, yaw or light rig are errors.

## 2. Run it
```
python3 tools/review/recipe.py validate <recipe.json>
python3 tools/review/recipe.py preview  <recipe.json> --blender <exe> --out <dir>   # minutes
#   look at <dir>/preview/preview.jpg: right versions, pose, framing, references?
python3 tools/review/recipe.py sheet    <recipe.json> --blender <exe> --out <dir>   # the long render
```
- `preview` renders one cheap frame of every view of every column in one Blender run, probes the arm pose of each
  column (upper arm from straight down: arms down ≤ 20°, A-pose ≥ 25°) and records `preview/preview.json`.
- `sheet` refuses to start without a passing preview **of the same recipe** (any edit to the recipe needs a new
  preview). `--skip-preview "<reason>"` overrides it; the reason is written to `log.txt` and `sheet.json`.
- Both record the recipe next to the outputs (`recipe.json`, `recipe.resolved.json`) with the render result (cameras,
  pose probe, Blender version, seconds).

## 3. The standard strict sheet
`<dir>/sheet.jpg` (≤ 2048 px): columns **original reference | previous approved | candidate** (| AI target); rows
**front, 3/4, side, back, face front, face 3/4**. Every column is rendered in the same run with identical cameras,
lights, world, exposure, samples and resolution; face controls are zeroed. Layout as the T-081 sheet
(`docs/evaluation/characters/T-081/girl_0.10.0_vs_0.11.0_strict.jpg`). This sheet is the single visual deliverable
for the owner; commit it (JPEG) with the recipe, `recipe.resolved.json` and `sheet.json`, not the PNG renders.

## 4. Fidelity numbers (tools/fidelity)
- The score is a regression signal. A drop of more than 2 points is reported as **needs owner review** (gate PASS
  with a warning and a summary line); the owner decides on the strict sheet. Regression image checks are unchanged.
- `tools/fidelity/run.py` never falls back to an A-pose master: a missing compare variant is an error
  (`--variant master` measures the master on purpose and is recorded). Reference views may hide parts the reference
  does not show, but never a garment (`garment.*`); `fidelity.json` records the objects actually hidden.
