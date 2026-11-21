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
| T-175 | E | t-175-claude-locomotion | `pipeline/clips/import_bvh.py`, `pipeline/clips/tests/test_import_bvh.py`, `content/clips/mocap/**`, `engine/anim/foot_lock.h`, `engine/anim/foot_lock.cpp`, `engine/scene/clip_layers.cpp`, `engine/scene/actions.cpp` (walk/sit/stand only), `tests/test_foot_lock.cpp`, `engine/CMakeLists.txt` (one plush_anim source line), `docs/evaluation/animation/T-175/**` | T-174 | — |
| T-171 | E | t-171-claude-hands-r2 | `engine/anim/hand_shape.h`, `engine/anim/hand_shape.cpp`, `engine/scene/interaction.cpp`, `engine/scene/verbs.cpp`, `engine/scene/collision.cpp`, `tests/test_grasp_contact.cpp`, `tests/test_hand_shape*.cpp`, `docs/evaluation/interaction/T-171/**` (final list in its first STATUS) | T-157 | — |
| T-172 | C | t-172-claude-test-video | `docs/evaluation/video/T-172/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
