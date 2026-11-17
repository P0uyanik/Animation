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
| T-044 | D | `t-044-claude-hair-v3` | `pipeline/charsys/hair_v3*.py`, `pipeline/charsys/groom_hybrid*.py`, `pipeline/charsys/materials/presets.json`, `pipeline/charsys/tests/test_hair_v3*.py`, `docs/evaluation/characters/T-044/**` | `pipeline/charsys/versions.py` (stable) | `hair` |
| T-058 | B | `t-039-codex-boy2-body` | `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.*`, `pipeline/charsys/body_generic.py`, `pipeline/charsys/spec.py`, `pipeline/charsys/build_character.py`, `pipeline/charsys/face_generic.py`, `pipeline/charsys/face_features.py`, `pipeline/charsys/garments/**`, `pipeline/charsys/tests/test_boy2*.py`, `pipeline/charsys/tests/test_hoodie*.py`, `docs/evaluation/characters/T-039/**`, `docs/evaluation/characters/T-058/**` | `pipeline/charsys/versions.py` (stable) | `body_generic`, `face_generic`, `garment` |
| T-060 | A | `t-060-codex-windows-ci` | `.github/workflows/checks.yml`, `.github/scripts/install_ci_dependencies.ps1`, `.github/ci-dependencies.json`, `CMakeLists.txt`, `cmake/**`, `vcpkg.json`, `docs/evaluation/process/T-060/**` | — | — |
| T-054a | A | `t-054a-codex-lipsync-tools` | `tools/lipsync/**`, `content/visemes/**`, `docs/LIPSYNC.md`, `docs/evaluation/animation/T-054a/**` | — | — |
| T-061 | C | `t-061-claude-animation-principles` | `engine/anim/**`, `engine/scene/clip_layers.cpp`, `engine/scene/actions.cpp`, `engine/scene/scene.{h,cpp}`, `engine/scene/emotion.{h,cpp}`, `engine/CMakeLists.txt`, `tests/test_anim_principles.cpp`, `tests/CMakeLists.txt`, `tools/animcheck/**`, `tools/check_all.py`, `tools/regression_paths.txt`, `content/clips/**`, `docs/evaluation/animation/T-061/**` | — | — |
| T-062 | A | `t-062-claude-current-cast` | `pipeline/production/run_shot.py`, `pipeline/production/tests/test_run_shot_current*.py`, `content/scenes/eval/**`, `tools/check_cast.py`, `docs/process/GATE.md`, `docs/evaluation/animation/T-062/**` | `tools/check_all.py` (stable) | — |
| T-063 | — | `t-063-claude-visual-review` | `docs/evaluation/review/T-063/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
