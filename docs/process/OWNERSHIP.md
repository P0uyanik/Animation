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
| T-114 | C | t-114-claude-two-char-acting | `episodes/e909_two_char_acting/**`, `tests/acting/test_e909_beats.py`, `docs/evaluation/animation/T-114/**` | engine, content (read-only) | — |
| T-124 | E | t-124-claude-render-opt | `docs/evaluation/rendering/T-124/**`, `tools/render_bench/**`, `pipeline/charsys/render_profiles.json`, `pipeline/charsys/shot_render.py`, `pipeline/charsys/render_engine.py` | — | — |
| T-119 | B | t-119-claude-garments-r3 | `pipeline/charsys/garments_v3/**`, `pipeline/charsys/materials/skin_presets_r3.json`, `pipeline/charsys/materials/builder.py`, `pipeline/charsys/tests/test_garments_r3.py`, `docs/evaluation/characters/T-119/**` | `pipeline/charsys/versions.py` (stable), `pipeline/charsys/build_character.py` (stable) | `garment` |
| T-123 | E | t-123-codex-readability | `tools/review/readability.py`, `tools/review/tests/test_readability.py`, `docs/evaluation/tools/T-123/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
