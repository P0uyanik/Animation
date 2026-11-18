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
| T-090b | E | t-090b-codex-fit-proposals | `docs/evaluation/characters/T-090b/**` | `tools/fit/**` (stable), `tools/review/**` (stable) | — |
| T-093 | D | t-093-claude-garments | `pipeline/charsys/garments_v2/**`, `pipeline/charsys/tests/test_garments_v2*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-093/**`, `docs/evaluation/characters/T-093/**` | `pipeline/charsys/garments/**` (stable), `pipeline/charsys/body_generic.py` (stable), `pipeline/charsys/build_character.py` (stable), `pipeline/charsys/groom_hybrid.py` (stable), `pipeline/charsys/versions.py` (stable), `pipeline/charsys/materials/**` (stable), `tools/review/**` (stable), `tools/fit/**` (stable), `assets/characters/*/spec/*.json` (stable), `assets/characters/*/references/**` (stable) | `garment` |
| T-089 | D | t-089-claude-face-eyes-r3 | `pipeline/charsys/face_generic_v3.py`, `pipeline/charsys/face_v3/**`, `pipeline/charsys/face_library/expressions_v3.json`, `pipeline/charsys/tests/test_face_v3*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-089/**`, `docs/evaluation/characters/T-089/**` | `pipeline/charsys/face_generic.py` (stable), `pipeline/charsys/face_features.py` (stable), `pipeline/charsys/face_library/expressions.json` (stable), `pipeline/charsys/build_character.py` (stable), `pipeline/charsys/versions.py` (stable), `pipeline/charsys/materials/**` (stable), `tools/review/**` (stable), `tools/fit/**` (stable), `assets/characters/*/spec/*.json` (stable), `assets/characters/*/references/**` (stable) | `face_generic` |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
