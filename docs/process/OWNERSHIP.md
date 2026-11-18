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
| T-085 | A | t-085-claude-renderer-optional | `CMakeLists.txt`, `cmake/**`, `engine/CMakeLists.txt`, `tests/CMakeLists.txt`, `apps/**/CMakeLists.txt`, `vcpkg.json`, `.github/ci-dependencies.json`, `.github/scripts/install_ci_dependencies.ps1`, `.github/workflows/checks.yml`, `tools/check_all.py`, `tests/test_engine.cpp`, `tests/test_render.cpp`, `apps/render-cli/main.cpp`, `docs/evaluation/process/T-085/**` | — | — |
| T-087 | E | t-087-claude-review-recipe | `tools/review/**`, `tools/fidelity/run.py`, `tools/fidelity/ci.py`, `tools/fidelity/tests/**`, `docs/process/REVIEW_RECIPE.md`, `docs/process/IMPLEMENTER_PROMPT.md`, `docs/evaluation/process/T-087/**` | — | — |
| T-088 | A | t-088-claude-version-switch | `tools/version_switch.py`, `tools/tests/test_version_switch.py`, `docs/process/ASSET_STORE.md`, `docs/evaluation/process/T-088/**` | `pipeline/charsys/asset_store.py` (stable), `tools/regression/*` (stable), `tools/fidelity/*` (stable) | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
