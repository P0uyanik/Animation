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

One active owner per file (owner 2026-11-21 ~11:20Z, T-176 P9): claims are file- or glob-level only; a write-set cell
holds back-ticked globs and nothing else (no "(… only)" sub-file splits; `claims --check-all` rejects them and any overlap
between active rows, also on every ledger push). A claim is temporary: it is released when the task merges or is
abandoned (the Supervisor removes the row in the same ledger commit) and handed over only through a ledger edit. A fix
round inside one file runs in sequence or as one task. Owner guidance (~12:00Z): claims as narrow as possible (specific files,
not whole folders); new files need no claim beyond the task's own folder; shared append-only registries (test
registration, ledger rows) are added by the Supervisor at merge, never locked; reading is never blocked (a read overlap
is a warning naming the other task); an overlap is reported with the conflicting task so the Supervisor can sequence or
split.

| Task | Lane | Branch | Write-set | Depends on | Versions bumped |
| --- | --- | --- | --- | --- | --- |
| T-194 | B | t-194-claude-hair-pushout | `pipeline/charsys/shot_render.py`, `pipeline/production/run_shot.py`, `pipeline/charsys/hair_pushout.py`, `pipeline/charsys/tests/test_hair_pushout.py`, `docs/evaluation/characters/T-194/**` | T-183 | — |
| T-201 | R | t-201-claude-preview-eevee | `pipeline/charsys/render_profiles.json`, `pipeline/charsys/render_engine.py`, `pipeline/charsys/tests/test_render_profiles.py`, `tools/pc/render_package.py`, `docs/evaluation/rendering/T-201/**` | `pipeline/charsys/shot_render.py` (stable), `pipeline/production/run_shot.py` (stable) | — |
| T-213 | C | t-213-claude-face-parity | `pipeline/charsys/face_parity.py`, `pipeline/charsys/tests/test_face_parity.py`, `docs/evaluation/characters/T-213/**` | `pipeline/charsys/export_engine.py` (stable), `assets/characters/**` (stable) | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
