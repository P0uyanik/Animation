# Boy CP-2 face/hair experiments — archived

The boy's (`boy_yellow_hoodie`) CP-2 experiment overrides and their orchestrators. Superseded by groom/1 (T-033),
hair v3 (T-044) and face v2 (T-065); the last candidates F09 (face) and H28 (hair) were **rejected by the owner on
2026-11-17**. Archived by T-072 (audit `docs/evaluation/review/T-069/README.md` §2.2/§2.3, item C7). Moved with
`git mv`, byte-identical. Results and sheets stay in `docs/evaluation/hair_experiments/` and
`docs/evaluation/face_controls/`.

**Not rebuildable from here:** the H20–H35 overrides pin `hair_clumps/2`, which is retired in
`pipeline/charsys/versions.py` (T-072), and the scripts expect the overrides under
`assets/characters/boy_yellow_hoodie/experiments/`. Use the git history (commit before T-072) to rebuild one.

| Archived | Former path | Count |
| --- | --- | --- |
| `boy_yellow_hoodie/hair/H00–H35` (without H28) | `assets/characters/boy_yellow_hoodie/experiments/hair/` | 28 |
| `boy_yellow_hoodie/face/F01–F08` | `assets/characters/boy_yellow_hoodie/experiments/face/` | 8 |
| `boy_yellow_hoodie/generic_tests/G01–G03` (synthetic face/body engineering configurations, CP-2 / M2 / M3) | `assets/characters/boy_yellow_hoodie/experiments/generic_tests/` | 3 |
| `charsys/hair_experiments.py` (runs the H variants: build → harness → sheet → metrics) | `pipeline/charsys/hair_experiments.py` | 1 |
| `charsys/review_views.py` (review sheets from existing renders) | `pipeline/charsys/review_views.py` | 1 |

**Left in place (frozen, `tools/frozen_manifest.txt`):** `experiments/face/F09_jaw_corner_center.json` and
`experiments/hair/H28_irregular_crown_only.json`. They are rejected, but frozen files are never moved without a
manifest change, which only the Supervisor makes.

Not archived yet: `pipeline/charsys/experiments/hair_study/` (T-049 prototypes): unused since T-044, but the T-049 report links into it
(see `docs/evaluation/review/T-072/README.md` §3).
