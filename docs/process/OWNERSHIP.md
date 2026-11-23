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
| T-219 | C | t-219-claude-hair-release | `pipeline/charsys/groom_r6.py`, `pipeline/charsys/groom/**`, `pipeline/charsys/tests/test_hair_flock.py`, `pipeline/charsys/release_rule.py`, `pipeline/charsys/release_manifest.json`, `pipeline/charsys/tests/test_release_rule.py`, `assets/characters/girl_auburn_bun_glasses/versions/**`, `assets/characters/girl_white_hair_blue_dress/versions/**`, `assets/characters/girl_auburn_bun_glasses/spec/candidates/T-219/**`, `assets/characters/girl_white_hair_blue_dress/spec/candidates/T-219/**`, `docs/evaluation/characters/T-219/**` | `pipeline/charsys/versions.py` (stable), `pipeline/charsys/build_character.py` (stable) | — |
| T-218 | P | t-218-claude-contact-audit | `pipeline/production/contact_audit.py`, `pipeline/production/tests/test_contact_audit.py`, `docs/evaluation/production/T-218/**` | `pipeline/charsys/hair_pushout.py` (stable), `docs/evaluation/characters/T-194/**` (stable), `docs/evaluation/characters/T-183/**` (stable) | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
