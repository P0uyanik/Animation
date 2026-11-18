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
| T-097D | C | t-097d-claude-reaction-playback | `engine/scene/actions.cpp`, `engine/scene/scene.{h,cpp}`, `tests/test_reaction_playback.cpp`, `tests/CMakeLists.txt`, `docs/PRODUCTION_PIPELINE.md`, `docs/evaluation/animation/T-097D/**` | `engine/scene/reaction.{h,cpp}` (stable), `engine/scene/emotion.{h,cpp}` (stable) | — |
| T-107 | E | t-107-codex-bc-review | `docs/audit/round2_bc_review/**` | — | — |
| T-091 | D | t-091-claude-hair-r4 | `pipeline/charsys/groom_r4.py`, `pipeline/charsys/groom_r4/**`, `pipeline/charsys/tests/test_hair_r4*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-091/**`, `docs/evaluation/characters/T-091/**` | `pipeline/charsys/groom_hybrid.py` (stable), `pipeline/charsys/versions.py` (stable) | `groom` |
| T-089b | D | t-089b-claude-face-polish | `pipeline/charsys/face_generic_v3.py`, `pipeline/charsys/face_v3/**`, `pipeline/charsys/tests/test_face_v3*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-089b/**`, `docs/evaluation/characters/T-089b/**` | `tools/fit/**` (stable) | — |
| T-093b | D | t-093b-claude-garment-completion | `pipeline/charsys/garments_v2/**`, `pipeline/charsys/tests/test_garments_v2*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-093b/**`, `docs/evaluation/characters/T-093b/**` | `tools/fit/**` (stable) | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
