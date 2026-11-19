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
| T-051 | C | t-051-claude-finger-grasps | `engine/anim/animation.{h,cpp}` (hand pose only), `engine/anim/hand_shape.{h,cpp}`, `engine/CMakeLists.txt`, `content/hand_shapes/**`, `tests/test_hand_shapes.cpp`, `tests/CMakeLists.txt`, `docs/evaluation/animation/T-051/**` | `engine/scene/**` (T-112b) | — |
| T-109 | D | t-109-claude-face-r4 | `pipeline/charsys/face_generic_v3.py`, `pipeline/charsys/face_v3/**`, `pipeline/charsys/face_library/**` (mouth shapes, additive), `pipeline/charsys/tests/test_face_v4*.py`, `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-109/**`, `docs/evaluation/characters/T-109/**` | materials (T-110), groom, garments (read-only) | — |
| T-107 | E | t-107-codex-bc-review | `docs/audit/round2_bc_review/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
