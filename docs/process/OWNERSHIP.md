# File claims (plan §3)

A task may start only if its write-set does not overlap a running task's write-set, it does not depend on files
another running task is changing, and it bumps no version another running task bumps. Supervisor updates this table
on every assign and close. (`tools/integrate.py claims --check` will automate this, T-041.)

| Task | Lane | Write-set (summary; full list in docs/tasks/T-NNN.md) | Depends on |
| --- | --- | --- | --- |
| T-041 | A | tools/check_all.py, tools/integrate.py, tools/regression/**, tools/regression_paths.txt, tools/simulate_quality_gate.py, tools/backup_repository.py, tools/guarded_paths.txt (additions), .github/workflows/checks.yml, backup.yml, .github/scripts/**, docs/process/OWNERSHIP.md, docs/process/GATE.md | build_character.py CLI (stable) |
| T-043 | B | pipeline/charsys/{spec,build_character,versions,body_helpers,body_generic,face_generic,groom,export_engine}.py, garments registration, assets/characters/*/spec/*.json (pins only) | — |
| T-046 | C | engine/scene/{emotion,scene,face_layer}.*, engine/anim/animation.*, engine/scene/actions.cpp, engine/CMakeLists.txt, content/emotions/**, content/clips/**, tests/CMakeLists.txt, tests/test_face_layer.cpp, tests/test_emotions*.cpp | — |
| T-040r1 | C | engine/scene/interaction.*, engine/model/**, tests/test_interaction.cpp | — |
| T-048 | A | .github/workflows/cleanup.yml, tools/cleanup/**, docs/process/CLEANUP.md | backup refs + backup.yml result (T-041; interface fixed in the task) |

Supervisor-only files: docs/process/TASK_LOG.md, docs/ROADMAP.md, docs/process/OWNER_DECISIONS.md, docs/tasks/**.
