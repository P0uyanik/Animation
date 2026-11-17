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
| T-060 | A | `t-060-codex-windows-ci` | `.github/workflows/checks.yml`, `.github/scripts/install_ci_dependencies.ps1`, `.github/ci-dependencies.json`, `CMakeLists.txt`, `cmake/**`, `vcpkg.json`, `docs/evaluation/process/T-060/**` | — | — |
| T-061 | C | `t-061-claude-animation-principles` | `engine/anim/**`, `engine/scene/clip_layers.cpp`, `engine/scene/actions.cpp`, `engine/scene/scene.{h,cpp}`, `engine/scene/emotion.{h,cpp}`, `engine/CMakeLists.txt`, `tests/test_anim_principles.cpp`, `tests/CMakeLists.txt`, `tools/animcheck/**`, `tools/check_all.py`, `tools/regression_paths.txt`, `content/clips/**`, `docs/evaluation/animation/T-061/**` | — | — |
| T-064 | A | `t-064-claude-fidelity-fixes` | `tools/fidelity/**`, `docs/evaluation/characters/fidelity_baseline.json`, `docs/CHARACTER_FIDELITY.md`, `assets/characters/*/references/annotations/**`, `docs/evaluation/characters/T-064/**` | — | — |
| T-065 | B | `t-065-claude-face-v2` | `pipeline/charsys/body_generic.py`, `pipeline/charsys/body_helpers.py`, `pipeline/charsys/face_generic.py`, `pipeline/charsys/face_features.py`, `pipeline/charsys/face_library/**`, `pipeline/charsys/tests/test_face_v2*.py`, `docs/evaluation/characters/T-065/**` | `pipeline/charsys/versions.py` (stable) | `face_generic`, `body_generic` |
| T-071 | A | `t-071-claude-docs-cleanup` | `*.md`, `pip.log`, `oidn.log`, `imgui.ini`, `.gitignore`, `docs/archive/**`, `docs/ITERATION_0*`, `docs/milestone0*/**`, `docs/iteration4/**`, `docs/CHARACTER_PIPELINE_REVIEW.md`, `docs/SCALABILITY_ASSESSMENT.md`, `docs/CHARACTER_SYSTEM_VERSIONS.md`, `docs/process/IMPLEMENTER_PROMPT.md`, `tools/lipsync/test_lipsync.py`, `docs/evaluation/review/T-071/**` | `tools/check_all.py` (stable) | — |
| T-072 | A | `t-072-claude-code-cleanup` | `archive/engine_era/**`, `archive/experiments/**`, `tools/make_*.py`, `tools/charkit.py`, `tools/render_iteration*_evidence.sh`, `pipeline/plush_views.py`, `content/scenes/milestone0*.scene.json`, `content/scenes/watertable_v4.scene.json`, `content/scenes/compare_*.scene.json`, `content/scenes/test_*.scene.json`, `archive/scenes/**`, `pipeline/clips/t0*_*.py`, `pipeline/clips/make_t014_shot.py`, `docs/evaluation/animation/T-0{10,14,22}/**`, `tools/shared_character_allowlist.txt`, `assets/characters/boy_yellow_hoodie/experiments/**`, `pipeline/charsys/hair_experiments.py`, `pipeline/charsys/review_views.py`, `pipeline/charsys/versions.py`, `pipeline/charsys/experiments/hair_study/**`, `docs/evaluation/review/T-072/**` | `pipeline/charsys/groom_hybrid.py` (stable) | — |
| T-070 | D | `t-070-claude-hair-v3-r2` | `pipeline/charsys/groom_hybrid.py`, `pipeline/charsys/tests/test_hair_v3*.py`, `pipeline/charsys/materials/presets.json`, `docs/evaluation/characters/T-070/**` | — | `groom` |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
