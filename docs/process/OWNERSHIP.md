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
| T-183 | B | t-183-claude-hair-contact | `engine/anim/secondary.h`, `engine/anim/secondary.cpp`, `tests/test_secondary.cpp`, `pipeline/charsys/groom_contact.py`, `pipeline/charsys/groom_r6.py`, `pipeline/charsys/tests/test_hair_contact.py`, `pipeline/charsys/release_rule.py`, `pipeline/charsys/tests/test_release_rule.py`, `docs/process/GENERATOR_PINS.md`, `episodes/e909_two_char_acting/shots/s010_t183/**`, `docs/SECONDARY_MOTION.md`, `docs/evaluation/characters/T-183/**` | — | — |
| T-187 | V | t-187-claude-paper-boat | `episodes/e912_paper_boat/**`, `docs/evaluation/video/T-187/**` | — | — |
| T-188 | E | t-188-claude-e909-r3-grasp | `episodes/e909_two_char_acting/make_shot.py`, `episodes/e909_two_char_acting/shots/s010/**`, `episodes/e909_two_char_acting/shots/s010_t113/**`, `episodes/e909_two_char_acting/content/assets/**`, `docs/evaluation/interaction/T-188/**` | — | — |
| T-189 | R | t-189-claude-world-reuse-survey | `docs/evaluation/world/T-189/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
