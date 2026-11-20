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
| T-155 | C | t-155-claude-candidates-r2 | (HELD by owner ~16:25 CET; bundled into the next version set) | T-154 | — |
| T-156 | E | t-156-claude-eye-targets | `pipeline/charsys/face_v3/lids.py`, eye/lash materials and overrides, `pipeline/charsys/tests/test_face_r5.py`, `docs/evaluation/characters/T-156/**` | T-137 | — |
| T-159 | E | t-159-claude-ears | `pipeline/charsys/face_features.py` (shape_face_v2 only), `pipeline/charsys/face_generic.py` (build_ears only), `pipeline/charsys/tests/test_face_front_fade.py`, `pipeline/charsys/tests/test_ears_shape.py`, `tools/ci/blender_shards.json` (its units), `tools/check_all.py` (registration), `docs/evaluation/characters/T-159/**` | T-158 | — |
| T-168 | E | t-168-claude-boy-face | `pipeline/charsys/face_v3/lower_face.py`, `pipeline/charsys/face_features.py` (build_nose only), `pipeline/charsys/tests/test_face_t168.py`, `tools/check_all.py` (registration), `docs/evaluation/characters/T-168/**` | T-159 (merge order) | — |
| T-167 | E | t-167-claude-hair-r7 | `pipeline/charsys/groom_r6.py`, `pipeline/charsys/tests/test_hair_r6.py`, `docs/evaluation/characters/T-167/**` | T-160, T-169 | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
