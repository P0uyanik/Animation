# File claims (plan §3)

A task may start only if its write-set does not overlap a running task's write-set, it does not depend on files
another running task is changing, and it bumps no version another running task bumps. Supervisor updates this table
on every assign and close.

Checked by `python tools/integrate.py claims --check T-NNN` (exit 1 on any overlap; `--list` prints the parsed
table). The gate check "Write-set" (`tools/check_all.py`) fails when a task branch changes a file outside its row.

Format (parsed by `tools/integrate.py`; keep it): one row per running task. Every write-set and depends-on entry is a
back-ticked, repository-relative glob: `*` stays inside one folder, `**` crosses folders, `{a,b}` expands, a
trailing `/` means the whole folder. A depends-on entry followed by `(stable)` only reads a stable interface: it is
reported as a warning, not a conflict. "Versions bumped" lists back-ticked version keys (e.g. `face_generic`); `—`
means none. Branch is the task's branch; a task branch without a row falls back to the "## Write-set" section of
`docs/tasks/T-NNN.md`.

| Task | Lane | Branch | Write-set | Depends on | Versions bumped |
| --- | --- | --- | --- | --- | --- |
| T-060 | A | `t-060-codex-windows-ci` | `.github/workflows/checks.yml`, `.github/scripts/install_ci_dependencies.ps1`, `.github/ci-dependencies.json`, `CMakeLists.txt`, `cmake/**`, `vcpkg.json`, `docs/evaluation/process/T-060/**`, `apps/studio/CMakeLists.txt`, `apps/studio/main.cpp`, `apps/studio/shot_job_windows.cpp`, `apps/studio/shot_workflow.{cpp,h}`, `tests/test_clips.cpp`, `tests/test_shot_workflow.cpp` | — | — |
| T-065 | B | `t-065-claude-face-v2` | `pipeline/charsys/body_generic.py`, `pipeline/charsys/body_helpers.py`, `pipeline/charsys/face_generic.py`, `pipeline/charsys/face_features.py`, `pipeline/charsys/face_library/**`, `pipeline/charsys/tests/test_face_v2*.py`, `docs/evaluation/characters/T-065/**` | `pipeline/charsys/versions.py` (stable) | `face_generic`, `body_generic` |
| T-070 | D | `t-070-claude-hair-v3-r2` | `pipeline/charsys/groom_hybrid.py`, `pipeline/charsys/tests/test_hair_v3*.py`, `pipeline/charsys/materials/presets.json`, `docs/evaluation/characters/T-070/**` | — | `groom` |
| T-066 | D | `t-066-claude-skin` | `pipeline/charsys/materials/skin_presets.json`, `pipeline/charsys/materials/builder.py`, `pipeline/charsys/materials/render_swatches.py`, `pipeline/charsys/materials/measure_swatches.py`, `pipeline/charsys/tests/test_skin*.py`, `docs/evaluation/characters/T-066/**` | — | `materials` |
| T-068 | D | `t-068-claude-garment-details` | `pipeline/charsys/garments/**`, `pipeline/charsys/accessories.py`, `pipeline/charsys/tests/test_garment*.py`, `docs/evaluation/characters/T-068/**` | — | `garment`, `accessories` |
| T-047 | C | `t-047-claude-collisions` | `engine/scene/collision.{h,cpp}`, `engine/scene/interaction.{h,cpp}`, `engine/scene/actions.cpp`, `engine/model/**`, `pipeline/charsys/export_engine.py`, `tests/test_collision.cpp`, `tests/test_interaction.cpp`, `docs/evaluation/animation/T-047/**` | — | `export` |
| T-053 | C | `t-053-claude-personality` | `engine/anim/personality.{h,cpp}`, `engine/anim/body_mechanics.cpp`, `engine/scene/scene.{h,cpp}`, `engine/scene/face_layer.{h,cpp}`, `engine/scene/emotion.{h,cpp}`, `engine/scene/clip_layers.cpp`, `content/personality/**`, `tools/animcheck/**`, `tests/test_personality.cpp`, `docs/evaluation/animation/T-053/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
