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
| T-097-boy | C | t-097-boy-claude-acting | `content/personality/boy_yellow_hoodie.json`, `content/clips/boy_*.clip.json`, `content/emotions/boy_*.emotion.json`, `episodes/e908_boy_acting/**`, `tests/acting/test_boy_signature.py`, `docs/evaluation/animation/T-097-boy/**` | `engine/scene/reaction.{h,cpp}` (stable), `tools/animcheck/**` (stable) | — |
| T-097-girl | C | t-097-girl-claude-acting | `content/personality/girl_auburn_bun_glasses.json`, `content/clips/girl_*.clip.json`, `content/emotions/girl_*.emotion.json`, `episodes/e908_girl_acting/**`, `tests/acting/test_girl_signature.py`, `docs/evaluation/animation/T-097-girl/**` | `engine/scene/reaction.{h,cpp}` (stable), `tools/animcheck/**` (stable) | — |
| T-107 | E | t-107-codex-bc-review | `docs/audit/round2_bc_review/**` | — | — |
| T-089b | D | t-089b-claude-face-polish | `pipeline/charsys/face_generic_v3.py`, `pipeline/charsys/face_v3/**`, `pipeline/charsys/tests/test_face_v3*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-089b/**`, `docs/evaluation/characters/T-089b/**` | `tools/fit/**` (stable) | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
