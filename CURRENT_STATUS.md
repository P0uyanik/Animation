# Current status (2026-11-14)

**CP-2 (hair_clumps/2): target reached by an experimental candidate; awaiting owner approval.**

Completed and tested:
- Character production pipeline `pipeline/charsys/` (TD-37); published `boy_yellow_hoodie` 1.0.0 (reference).
  Store tests 19/19 and reuse tests (reopen, pose, episode link/override, glTF, master unchanged) pass.
- `hair_clumps/2` generator with lock families and a scalp cap (`pipeline/charsys/hair.py`).
- Best candidate **H25**: hair contour 2.93% (target ≤ 3.0%, v6 3.40%), IoU 0.8455, head width +4.1% (v6 +5.7%),
  no visible scalp; 8-angle sheet `docs/evaluation/hair_experiments/cp2_hair_clumps_v2_sheet.jpg`.
- Regression: the v1 hair path still rebuilds v6 geometry exactly (0.0 m).

- Facial controls (experimental F01, `pipeline/charsys/face.py`): Blink no longer turns the eyes into skin balls
  (lid 6.0 -> 3.75 mm proud, lash seam visible, computed closing angle 41 deg), Smile corner lift +4.5 -> +7.0 mm.
  Test `pipeline/charsys/tests/face_test.py`; evidence `docs/evaluation/face_controls/`. Regression
  `verify_charsys.py` PASS (67/0).

- Hair H26 (dense rows + fanned crown, spec override): contour 2.99%, IoU 0.8463, head width +2.0%; fixes the
  H25 review points (cap patches, nape, back density, crown). Evidence `docs/evaluation/hair_experiments/H26_*`.
- Face F02 (`lips_jaw/1` + F01 Blink): real mouth opening with dark interior, `DEF-jaw` bone driven by
  `face_JawOpen` (6.7 mm chin drop), closed mouth hides the interior (0%). Temp-store reuse test PASS (411/74 bones,
  glTF, episode link). Evidence `docs/evaluation/face_controls/F02_review_1.0.0_vs_F02.jpg`.
- Reusability assessment `docs/CHARACTER_REUSABILITY.md`. Regression `verify_charsys.py` PASS (67/0).

Not done / limitations:
- H25/H26 (hair) and F01/F02 (face) not published or approved (identity changes: owner decision); H25 and F01 reviewed and not approved.
- F02: flat interior (no teeth/tongue), skin stretch at mouth corners (3.5x), Smile without cheek/eye coordination; closed lid slightly rounded.
- H26: crown tufts form a regular ring; #7 front 3.63%.
- Smooth cap patch behind the ear; crown tufts thinner than the refs; side/back-¾ views still 3.5–3.7%.
- Your local Blender 5.2 runs (`reproduce_v6.py`, `verify_charsys.py`) not yet reported.
- Fur is evaluation-only (not in master/glb); no USD/Alembic.

Protected: v6 + frozen baseline, version 1.0.0, reproduction script, C++ engine. Iteration 5 not started.
