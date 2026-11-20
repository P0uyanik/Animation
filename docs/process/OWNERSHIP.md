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
| T-137 | E | t-137-claude-faces | (lids.py and test_face_r5.py handed to T-156, which builds on this branch) `docs/evaluation/characters/T-137/**`, `content/emotions/boy_interested.emotion.json`, `content/personality/boy_yellow_hoodie.json`, `docs/evaluation/characters/T-137/` | — | — |
| T-156 | E | t-156-claude-eye-targets | `pipeline/charsys/face_v3/lids.py`, `pipeline/charsys/tests/test_face_r5.py`, `docs/evaluation/characters/T-156/**` | T-137 | — |
| T-157 | E | t-157-claude-grasp-options | `engine/scene/interaction.cpp`, `engine/scene/interaction.h`, `engine/anim/animation.cpp`, `engine/anim/animation.h`, `content/hand_shapes/**`, `tests/test_grasp_contact.cpp`, `docs/evaluation/animation/T-157/**` | — | — |
| T-155 | C | t-155-claude-candidates-r2 | `assets/characters/boy_yellow_hoodie/versions/2.3.0/**`, `assets/characters/girl_auburn_bun_glasses/versions/0.14.0/**`, `assets/characters/girl_white_hair_blue_dress/versions/0.1.0/**`, `assets/characters/*/versions/index.json` (candidate entries only), `spec/candidates/**` (new files only), `docs/evaluation/characters/T-155/**`, `docs/evaluation/characters/fidelity_baseline.json` (rebaseline citing owner ~08:20Z), `docs/evaluation/regression/baselines/*/2.3.0/**`, `docs/evaluation/regression/baselines/*/0.14.0/**`, `docs/evaluation/regression/baselines/*/0.1.0/**`, `assets/characters/*/spec/*.spec.json` (new version specs only), `docs/evaluation/fidelity/**` | T-154 | — |
| T-163 | E | t-163-claude-props | `content/assets/**` (new files only), `tests/props/**`, `docs/evaluation/props/T-163/**` | — | — |
| T-164 | C | t-164-claude-gate-comment | `.github/workflows/checks.yml` | — | — |
| T-165 | C | t-165-claude-task-kit | `tools/ready.py`, `tools/run_logged.py`, `tools/wait_gate.py`, `tools/render_queue.py`, `tools/review/shot_sheet.py`, `tools/tests/test_task_kit.py`, `tools/check_all.py`, `docs/process/IMPLEMENTER_PROMPT.md`, `docs/tasks/_TEMPLATE.md` | — | — |
| T-159 | E | t-159-claude-ears | `docs/evaluation/characters/T-159/**` (generator files named in the first CHECKPOINT) | T-158 | — |
| T-167 | E | t-167-claude-hair-r7 | `pipeline/charsys/groom_r6.py`, `pipeline/charsys/groom_r7.py`, `pipeline/charsys/tests/test_hair_r6.py`, `pipeline/charsys/tests/test_hair_r7.py`, `docs/evaluation/characters/T-167/**` | T-160 | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
