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
| T-127 | E | t-127-claude-ci-speed | `.github/workflows/**`, `.github/scripts/**`, `tools/check_all.py`, `tools/ci/**`, `docs/process/GATE.md`, `docs/evaluation/ci/T-127/**` | — | — |
| T-125 | E | t-125-claude-motion-checks | `tools/motion_checks/**`, `docs/evaluation/animation/T-125/**` | — | — |
| T-131 | D | t-131-claude-version-switch | `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/versions/index.json`, `docs/evaluation/characters/fidelity_baseline.json`, `docs/evaluation/regression/baselines/{boy_yellow_hoodie/2.2.0,girl_auburn_bun_glasses/0.13.0}/**`, `docs/evaluation/characters/T-131/**` | `assets/characters/*/versions/{2.2.0,0.13.0}/**` (stable) | `boy_yellow_hoodie`, `girl_auburn_bun_glasses` |
| T-126a | B | t-126a-claude-body-face | `assets/characters/girl_white_hair_blue_dress/spec/**`, `docs/evaluation/characters/T-126/body_face/**` | — | `girl_white_hair_blue_dress` |
| T-126b | B | t-126b-claude-hair | `pipeline/charsys/groom_r5.py`, `pipeline/charsys/tests/test_hair_r5.py`, `docs/evaluation/characters/T-126/hair/**` | — | `groom` |
| T-126c | B | t-126c-claude-dress | `pipeline/charsys/garments_v3/**`, `pipeline/charsys/tests/test_garments_r3.py`, `pipeline/charsys/cloth_sim/**`, `docs/evaluation/characters/T-126/dress/**` | — | `garment` |
| T-126d | B | t-126d-claude-materials | `pipeline/charsys/materials/presets_third.json`, `pipeline/charsys/materials/builder.py`, `docs/evaluation/characters/T-126/materials/**` | — | — |
| T-117 | C | t-117-claude-showcase | `episodes/e910_showcase/**`, `docs/evaluation/animation/T-117/**` | engine, content, characters (read-only) | — |
| T-124 | E | t-124-claude-render-opt | `docs/evaluation/rendering/T-124/**`, `tools/render_bench/**`, `pipeline/charsys/render_profiles.json`, `pipeline/charsys/shot_render.py`, `pipeline/charsys/render_engine.py` | — | — |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
