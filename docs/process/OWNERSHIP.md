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
| T-078 | E | `t-078-claude-progress-video` | `docs/evaluation/showcase/T-078/**` | — | — |
| T-081 | D | `t-081-claude-girl-0-11-0` | `assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.11.0*`, `pipeline/charsys/face_generic.py`, `pipeline/charsys/face_features.py`, `pipeline/charsys/body_generic.py`, `pipeline/charsys/body_helpers.py`, `pipeline/charsys/tests/test_face_v2*.py`, `docs/evaluation/characters/T-081/**`, `assets/characters/girl_auburn_bun_glasses/versions/**`, `docs/evaluation/characters/fidelity_baseline.json` (girl entry), `docs/evaluation/regression/baselines/girl_auburn_bun_glasses/**` | `pipeline/charsys/versions.py` (stable) | `face_generic`, `body_generic` |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
