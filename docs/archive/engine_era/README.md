# Engine-era look iterations (archived 2026-11-17, T-071)

Archived 2026-11-17, superseded by the Blender production path (TD-37..TD-42 in
[TECHNICAL_DECISIONS.md](../../../TECHNICAL_DECISIONS.md), [docs/PRODUCTION_PIPELINE.md](../../PRODUCTION_PIPELINE.md)).
These are the reports and renders of look iterations 1–4 (2026-11-13), when the characters were SDF models rendered
by the C++ engine's path tracer. The engine-era characters and scenes themselves are **not** archived: they are the
inputs of the CTest image regressions (`content/characters/`, `content/scenes/`).

| File / folder | Original path |
| --- | --- |
| [ITERATION_03_REFERENCE_GAP_ANALYSIS.md](ITERATION_03_REFERENCE_GAP_ANALYSIS.md) | `docs/ITERATION_03_REFERENCE_GAP_ANALYSIS.md` |
| [ITERATION_03_ACCEPTANCE_REPORT.md](ITERATION_03_ACCEPTANCE_REPORT.md) | `docs/ITERATION_03_ACCEPTANCE_REPORT.md` |
| [ITERATION_04_PHASE_A_ANALYSIS.md](ITERATION_04_PHASE_A_ANALYSIS.md) | `docs/ITERATION_04_PHASE_A_ANALYSIS.md` |
| [ITERATION_04_ACCEPTANCE_REPORT.md](ITERATION_04_ACCEPTANCE_REPORT.md) | `docs/ITERATION_04_ACCEPTANCE_REPORT.md` |
| [SCALABILITY_ASSESSMENT.md](SCALABILITY_ASSESSMENT.md) | `docs/SCALABILITY_ASSESSMENT.md` (after iteration 2) |
| `milestone01/` | `docs/milestone01/` (milestone 01 video, stills, Studio screenshot) |
| `milestone02/` | `docs/milestone02/` (milestone 02 video, stills, face sheet) |

Still in place, on purpose: `docs/milestone03/` and `docs/iteration4/` are the output folders of
`tools/make_it4_comparison.py` (a tool reference), so they move only together with the engine-era generators (T-069
plan C5). Their reports above mention them by their unchanged paths.

**Do not run the engine-era generators** that are still in `tools/` (`charkit.py`, `make_girl_v2.py`,
`make_lineup.py`, `make_face_test.py`, `make_milestone02.py`, `make_milestone03.py`, `make_watertable_v4.py`,
`make_expression_sheet.py`, `make_it4_comparison.py`, `render_iteration*_evidence.sh`): several of them overwrite
CTest regression inputs in `content/scenes/` and `content/characters/` (T-069 §2.6). Archiving them is T-069 plan C5
(code, full tier; not part of T-071).
