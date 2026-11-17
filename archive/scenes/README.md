# Engine-era demo scenes — archived

Engine-renderer demo and test scenes from iterations 2–4 that no test, CTest entry, tool, CI job or app uses.
Archived by T-072 (owner decision 2026-11-17, item 3: "archive, except any a test/CTest still uses"). Moved with
`git mv`, byte-identical.

The scenes reference their characters as `../characters/<name>.character.json`, so they only load from
`content/scenes/`. To view one, copy it back there (do not commit the copy) and open it with `plush-render` or Studio.

| Archived scene | Former path | Origin |
| --- | --- | --- |
| `compare_it4_boy.scene.json` | `content/scenes/` | iteration-4 Blender comparison harness (`archive/engine_era/pipeline/plush_views.py`) |
| `milestone03_watertable.scene.json` | `content/scenes/` | milestone 03 (`archive/engine_era/tools/make_milestone03.py`) |
| `watertable_v4.scene.json` | `content/scenes/` | iteration-4 water-table benchmark (`archive/engine_era/tools/make_watertable_v4.py`) |
| `test_expressions_boy_dark_hair.scene.json` | `content/scenes/` | expression sheets (`archive/engine_era/tools/make_expression_sheet.py`) |
| `test_expressions_girl_brown_glasses.scene.json` | `content/scenes/` | same |
| `test_expressions_girl_white_hair.scene.json` | `content/scenes/` | same |
| `test_hand_poses.scene.json` | `content/scenes/` | hand-pose visual check (iteration 3) |

Kept in `content/scenes/`: `milestone01_classroom` (CTest `regression_milestone01`, Studio default scene),
`test_face` (CTest `regression_face_neutral`), `test_lineup` (CTest `regression_lineup_abc`),
`milestone02_classroom` (input of the guarded `tools/make_face_test.py`) and `eval/**`.
