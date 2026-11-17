# Engine-era generators (iterations 2–4) — archived, DO NOT RUN

**Do not run these scripts: they overwrite regression inputs. Kept for history only.**

Most of them write into `content/scenes/` or `content/characters/` with paths relative to the current directory.
Several of those outputs are CTest image-regression inputs (`content/scenes/test_lineup.scene.json`,
`content/scenes/test_face.scene.json`, `content/characters/girl_white_hair_v2.character.json` and the three
iteration-3 characters). Running a script from the repository root would silently rewrite them.

Archived by T-072 (owner decision 2026-11-17, "T-069 audit recommendations approved"; audit
`docs/evaluation/review/T-069/README.md` §2.6, item C5). The files were moved with `git mv` and are byte-identical
to the originals; `git log --follow` shows their history.

| Archived file | Former path | What it produced |
| --- | --- | --- |
| `tools/charkit.py` | `tools/charkit.py` | the three iteration-3 SDF characters (`content/characters/{girl_white_hair,girl_brown_glasses,boy_dark_hair}.character.json`) |
| `tools/make_girl_v2.py` | `tools/make_girl_v2.py` | `content/characters/girl_white_hair_v2.character.json` (input of `regression_face_neutral`) |
| `tools/make_lineup.py` | `tools/make_lineup.py` | `content/scenes/test_lineup.scene.json` (input of `regression_lineup_abc`) |
| `tools/make_milestone02.py` | `tools/make_milestone02.py` | `content/scenes/milestone02_classroom.scene.json` |
| `tools/make_milestone03.py` | `tools/make_milestone03.py` | `milestone03_watertable.scene.json` (now in `archive/scenes/`) |
| `tools/make_watertable_v4.py` | `tools/make_watertable_v4.py` | `watertable_v4.scene.json` (now in `archive/scenes/`) |
| `tools/make_expression_sheet.py` | `tools/make_expression_sheet.py` | `test_expressions_<character>.scene.json` (now in `archive/scenes/`) |
| `tools/make_it4_comparison.py` | `tools/make_it4_comparison.py` | iteration-4 comparison sheets (`docs/iteration4`) |
| `tools/render_iteration3_evidence.sh` | `tools/render_iteration3_evidence.sh` | iteration-3 renders (`docs/milestone03`) |
| `tools/render_iteration4_evidence.sh` | `tools/render_iteration4_evidence.sh` | iteration-4 renders (`docs/iteration4`) |
| `pipeline/plush_views.py` | `pipeline/plush_views.py` | Plush-renderer views for the iteration-4 Blender comparison harness (`docs/BLENDER_COMPARISON_HARNESS.md`) |

Not archived here (still in place, see `docs/evaluation/review/T-072/README.md`):

- `tools/make_face_test.py`: a guarded path (`**/*_test.py`), moving it needs a `Supervisor-Approved:` trailer. It
  writes `content/scenes/test_face.scene.json` (a CTest input) from `content/scenes/milestone02_classroom.scene.json`,
  which therefore also stays.
- `pipeline/triptych.py`: outside the T-072 write-set.
- `apps/export-obj`: waits for T-060 (root `CMakeLists.txt`).
