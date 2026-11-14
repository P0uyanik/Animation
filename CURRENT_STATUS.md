# Current status (2026-11-14)

**CP-2 (hair_clumps/2): target reached by an experimental candidate; awaiting owner approval.**

Completed and tested:
- Character production pipeline `pipeline/charsys/` (TD-37); published `boy_yellow_hoodie` 1.0.0 (reference).
  Store tests 19/19 and reuse tests (reopen, pose, episode link/override, glTF, master unchanged) pass.
- `hair_clumps/2` generator with lock families and a scalp cap (`pipeline/charsys/hair.py`).
- Best candidate **H25**: hair contour 2.93% (target ≤ 3.0%, v6 3.40%), IoU 0.8455, head width +4.1% (v6 +5.7%),
  no visible scalp; 8-angle sheet `docs/evaluation/hair_experiments/cp2_hair_clumps_v2_sheet.jpg`.
- Regression: the v1 hair path still rebuilds v6 geometry exactly (0.0 m).

Not done / limitations:
- H25 not published or approved (identity change: owner decision).
- Smooth cap patch behind the ear; crown tufts thinner than the refs; side/back-¾ views still 3.5–3.7%.
- Your local Blender 5.2 runs (`reproduce_v6.py`, `verify_charsys.py`) not yet reported.
- Fur is evaluation-only (not in master/glb); no USD/Alembic.

Protected: v6 + frozen baseline, version 1.0.0, reproduction script, C++ engine. Iteration 5 not started.
