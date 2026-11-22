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
| T-183 | B | t-183-claude-hair-contact | `engine/anim/secondary.h`, `engine/anim/secondary.cpp`, `tests/test_secondary.cpp`, `pipeline/charsys/groom_contact.py`, `pipeline/charsys/groom_r6.py`, `pipeline/charsys/tests/test_hair_contact.py`, `pipeline/charsys/release_rule.py`, `pipeline/charsys/tests/test_release_rule.py`, `docs/process/GENERATOR_PINS.md`, `episodes/e909_two_char_acting/shots/s010_t183/**`, `docs/SECONDARY_MOTION.md`, `docs/evaluation/characters/T-183/**`, `engine/scene/scene.cpp`, `engine/scene/scene.h`, `episodes/e912_paper_boat/shots/s010_t183/**`, `episodes/e912_paper_boat/shots/s020_t183/**`, `episodes/e912_paper_boat/shots/s030_t183/**` | — | — |
| T-194 | B | t-194-claude-hair-pushout | `pipeline/charsys/shot_render.py`, `pipeline/production/run_shot.py`, `pipeline/charsys/hair_pushout.py`, `pipeline/charsys/tests/test_hair_pushout.py`, `docs/evaluation/characters/T-194/**` | T-183 | — |
| T-199 | R | t-199-claude-compositor-look | `pipeline/charsys/render_engine.py`, `pipeline/charsys/render_profiles.json`, `pipeline/charsys/tests/test_render_profiles.py`, `docs/evaluation/rendering/T-199/**` | — | — |
| T-203 | G | t-203-claude-tests-manifest-rename | `pipeline/audio/tests/TESTS`, `pipeline/audio/tests/TESTS.manifest`, `pipeline/charsys/tests/TESTS`, `pipeline/charsys/tests/TESTS.manifest`, `pipeline/clips/TESTS`, `pipeline/clips/TESTS.manifest`, `pipeline/clips/tests/TESTS`, `pipeline/clips/tests/TESTS.manifest`, `pipeline/production/tests/TESTS`, `pipeline/production/tests/TESTS.manifest`, `tests/TESTS`, `tests/TESTS.manifest`, `tests/acting/TESTS`, `tests/acting/TESTS.manifest`, `tests/props/TESTS`, `tests/props/TESTS.manifest`, `tools/animcheck/tests/TESTS`, `tools/animcheck/tests/TESTS.manifest`, `tools/ci/tests/TESTS`, `tools/ci/tests/TESTS.manifest`, `tools/cleanup/TESTS`, `tools/cleanup/TESTS.manifest`, `tools/fidelity/tests/TESTS`, `tools/fidelity/tests/TESTS.manifest`, `tools/fit/tests/TESTS`, `tools/fit/tests/TESTS.manifest`, `tools/lipsync/TESTS`, `tools/lipsync/TESTS.manifest`, `tools/motion_checks/TESTS`, `tools/motion_checks/TESTS.manifest`, `tools/perf_extract/tests/TESTS`, `tools/perf_extract/tests/TESTS.manifest`, `tools/regression/tests/TESTS`, `tools/regression/tests/TESTS.manifest`, `tools/review/tests/TESTS`, `tools/review/tests/TESTS.manifest`, `tools/tests/TESTS`, `tools/tests/TESTS.manifest`, `tools/check_all.py`, `tools/ready.py`, `tools/tests/test_test_registry.py`, `tools/tests/test_task_kit.py`, `docs/process/GATE.md`, `docs/evaluation/process/T-203/**` | — | — |
| T-198 | E | t-198-claude-motion-continuity | `engine/anim/animation.h`, `engine/anim/animation.cpp`, `engine/scene/interaction.h`, `engine/scene/interaction.cpp`, `engine/scene/actions.cpp`, `tests/test_motion_continuity.cpp`, `tools/motion_checks/continuity.py`, `docs/evaluation/interaction/T-198/**` | T-190 | — |
| T-207 | B | t-207-claude-hair-flock | `pipeline/charsys/groom/hair_curves.py`, `pipeline/charsys/groom/flock.py`, `pipeline/charsys/groom_felt.py`, `pipeline/charsys/tests/test_hair_curves.py`, `pipeline/charsys/tests/test_hair_flock.py`, `docs/evaluation/characters/T-207/**` | T-183 (groom_r6.py hook after its merge) | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
