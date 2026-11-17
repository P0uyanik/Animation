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
| T-041 | A | `t-041-claude-gate-claims` | `tools/check_all.py`, `tools/integrate.py`, `tools/regression/**`, `tools/regression_paths.txt`, `tools/simulate_quality_gate.py`, `tools/backup_repository.py`, `tools/guarded_paths.txt`, `.github/workflows/checks.yml`, `.github/workflows/backup.yml`, `.github/scripts/**`, `.github/ci-dependencies.json`, `docs/process/OWNERSHIP.md`, `docs/process/GATE.md`, `docs/evaluation/process/T-041/**`, `docs/evaluation/regression/baselines/**` | `pipeline/charsys/build_character.py` (stable), `pipeline/charsys/fingerprint_v2.py` (stable) | — |
| T-043 | B | `t-043-claude-spec-versions` | `pipeline/charsys/spec.py`, `pipeline/charsys/build_character.py`, `pipeline/charsys/versions.py`, `pipeline/charsys/body_helpers.py`, `pipeline/charsys/body_generic.py`, `pipeline/charsys/face_generic.py`, `pipeline/charsys/groom.py`, `pipeline/charsys/garments/**`, `pipeline/charsys/export_engine.py`, `assets/characters/*/spec/*.json`, `pipeline/charsys/tests/test_versions*.py`, `docs/CHARACTER_SYSTEM_VERSIONS.md`, `docs/evaluation/characters/T-043/**` | — | — |
| T-046 | C | `t-046-claude-facial-animation` | `engine/scene/emotion.{h,cpp}`, `engine/anim/animation.{h,cpp}`, `engine/scene/scene.{h,cpp}`, `engine/scene/actions.cpp`, `engine/scene/face_layer.{h,cpp}`, `engine/CMakeLists.txt`, `content/emotions/**`, `content/clips/**`, `tests/test_face_layer.cpp`, `tests/CMakeLists.txt`, `tests/test_emotions*.cpp`, `docs/evaluation/animation/T-046/**` | — | — |
| T-040r1 | C | `t-040-claude-pose-clearance` | `engine/scene/interaction.{h,cpp}`, `engine/model/**`, `tests/test_interaction.cpp`, `docs/evaluation/animation/T-040/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
