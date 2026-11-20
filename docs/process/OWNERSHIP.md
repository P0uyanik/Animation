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
| T-137 | E | t-137-claude-faces | (lids.py and test_face_r5.py handed to T-156, which builds on this branch) `docs/evaluation/characters/T-137/**`, `content/emotions/boy_interested.emotion.json`, `content/personality/boy_yellow_hoodie.json`, `docs/evaluation/characters/T-137/` | — | — |
| T-141 | C | t-141-claude-hair-curves | `pipeline/charsys/groom/**` (new opt-in module only; no edits to existing groom files), `pipeline/charsys/tests/test_hair_curves*.py`, `docs/evaluation/characters/T-141/**` | — | — |
| T-154 | C | t-154-claude-guard-allowlist | `pipeline/charsys/tests/owner_approved_candidates.json`, `pipeline/charsys/tests/test_hair_r5.py`, `pipeline/charsys/tests/test_hands_r2.py`, `pipeline/charsys/tests/test_guard_allowlist.py`, `tools/check_all.py` | — | — |
| T-156 | E | t-156-claude-eye-targets | `pipeline/charsys/face_v3/lids.py`, `pipeline/charsys/tests/test_face_r5.py`, `docs/evaluation/characters/T-156/**` | T-137 | — |
| T-158 | C | t-158-claude-deterministic-build | `pipeline/charsys/tests/test_build_determinism.py`, `docs/evaluation/characters/T-158/**` | — | — |
| T-155 | C | t-155-claude-candidates | `assets/characters/boy_yellow_hoodie/versions/2.3.0/**`, `assets/characters/girl_auburn_bun_glasses/versions/0.14.0/**`, `assets/characters/girl_white_hair_blue_dress/versions/0.1.0/**`, `assets/characters/*/versions/index.json` (candidate entries only), `spec/candidates/**` (new files only), `docs/evaluation/characters/T-155/**` | T-154 | — |
| T-160 | E | t-160-claude-hair-r6 | `docs/evaluation/characters/T-160/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
