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
| T-175 | E | t-175-claude-locomotion | `pipeline/clips/import_bvh.py`, `pipeline/clips/tests/test_import_bvh.py`, `content/clips/mocap/**`, `engine/anim/foot_lock.h`, `engine/anim/foot_lock.cpp`, `engine/scene/clip_layers.cpp`, `engine/scene/actions.cpp`, `tests/test_foot_lock.cpp`, `engine/CMakeLists.txt`, `docs/evaluation/animation/T-175/**` | T-174 | — |
| T-171 | E | t-171-claude-hands-r2 | `engine/anim/hand_shape.h`, `engine/anim/hand_shape.cpp`, `engine/anim/animation.h`, `engine/anim/animation.cpp`, `engine/scene/interaction.cpp`, `engine/scene/verbs.cpp`, `engine/scene/collision.cpp`, `tests/test_grasp_contact.cpp`, `tests/test_hand_shape*.cpp`, `docs/evaluation/interaction/T-171/**` | T-157 | — |
| T-172 | C | t-172-claude-test-video | `docs/evaluation/video/T-172/**` | — | — |
| T-180 | G | t-180-claude-clone-profiles | `docs/process/CLONE_PROFILES.md` | — | — |
| T-182 | G | t-182-claude-test-registry | `tools/check_all.py`, `tools/guarded_paths.txt`, `tools/ready.py`, `tools/tests/test_test_registry.py`, `pipeline/charsys/tests/TESTS`, `pipeline/clips/TESTS`, `pipeline/clips/tests/TESTS`, `pipeline/production/tests/TESTS`, `tests/TESTS`, `tests/acting/TESTS`, `tests/props/TESTS`, `tools/animcheck/tests/TESTS`, `tools/ci/tests/TESTS`, `tools/cleanup/TESTS`, `tools/fidelity/tests/TESTS`, `tools/fit/tests/TESTS`, `tools/lipsync/TESTS`, `tools/regression/tests/TESTS`, `tools/tests/TESTS`, `tools/motion_checks/TESTS`, `tools/perf_extract/tests/TESTS`, `tools/review/tests/TESTS`, `tools/tests/test_task_kit.py`, `docs/process/GATE.md`, `docs/evaluation/process/T-182/**` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
