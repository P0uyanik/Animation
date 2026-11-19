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
| T-134 | E | t-134-claude-reach | `engine/anim/body_mechanics.*`, `engine/anim/principles.*`, `engine/anim/secondary.*`, `engine/scene/interaction.cpp`, `engine/scene/interaction.h`, `engine/scene/verbs.cpp`, `engine/scene/verbs.h`, `tests/test_reach_mechanics.cpp`, `tests/CMakeLists.txt`, `episodes/e910_showcase/shots/s010_e1/**`, `docs/evaluation/animation/T-134/**`, `scene.cpp` | — | — |
| T-135 | E | t-135-claude-reach-measures | `tools/motion_checks/reach/**`, `docs/evaluation/animation/T-135/**` | — | — |
| T-136 | E | t-136-claude-blink-gaze | `engine/scene/scene.cpp`, `engine/scene/scene.h`, `engine/scene/face_layer.cpp`, `engine/scene/face_layer.h`, `engine/anim/personality.cpp`, `engine/anim/personality.h`, `tests/test_blink_schedule.cpp`, `tests/test_gaze_chain.cpp`, `episodes/e910_showcase/shots/s010_e23/**`, `docs/evaluation/animation/T-136/**` | — | — |
| T-137 | E | t-137-claude-faces | `pipeline/charsys/face_v3/lids.py`, `pipeline/charsys/tests/test_face_r5.py`, `docs/evaluation/characters/T-137/**`, `content/emotions/boy_interested.emotion.json`, `content/personality/boy_yellow_hoodie.json`, `docs/evaluation/characters/T-137/` | — | — |
| T-139 | E | t-139-claude-animcheck | `tools/animcheck/animcheck.py`, `tools/animcheck/acting.py`, `tools/animcheck/tests/**`, `docs/evaluation/animation/T-139/**` | — | — |
| T-124 | E | t-124-claude-render-opt | `docs/evaluation/rendering/T-124/**`, `tools/render_bench/**`, `pipeline/charsys/render_profiles.json`, `pipeline/charsys/shot_render.py`, `pipeline/charsys/render_engine.py` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
