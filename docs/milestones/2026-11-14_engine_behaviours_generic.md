# Milestone 2026-11-14: generic engine behaviours (walk, hands, blink, expressions)

| Item | Result |
| --- | --- |
| Changed (engine) | `legLength`, `walkStep` (leg-scaled step, scaled gait, double support); `HandFrame` + generic curl/spread/thumb axes, 2+ digit hands; `LifeParams::blinkLids` + morph blink in scene evaluation; `expressionMap` + `resolveExpression` + `SceneEvaluator::warnings()`; importer reads `expressions`, `walk`, `hands` and derives hand frames |
| Changed (pipeline) | Profiles carry expression maps; exporter writes `expressions` / `expressions_missing`; blink capability accepts a blink expression |
| Reused | Existing actions, life layer, IK, grasp search, tests and packages (re-exported from the unchanged 1.0.0) |
| Boy 1.0.0 package | reach, look-at, expressions, blink (morph), grasp (both hands), walk (1/59), idle: all supported |
| Fixture (engineering test) | reach, look-at, expressions (smile missing → warning), blink (Squint), walk (0/59), idle supported; grasp unsupported (no fingers, by design) |
| Generality proofs | Rotated hand gives identical fingertips (≤ 0.0001 mm); 3-digit hand grasps; 1-digit hand reports no hand |
| Compatibility | Defaults reproduce previous behaviour; ctest 4/4 including the 3 frozen image regressions; chibi walk improved (2/59, was up to 6) |
| Tests | ctest 4/4 (181 assertions in imported-character tests), exporter tests 8/8, verify_charsys PASS |
| Limitations | Humanoid profiles only; grasp tested with a stick across the hand; no cadence limit for short legs |
| Protected | v6, 1.0.0, baselines unchanged; nothing published |
