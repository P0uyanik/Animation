# Milestone 2026-11-14: CP-2 generic face and hair system step

| Status category | Items |
| --- | --- |
| Experimental | F07, F08, **F09** (face candidate); H30–H35; G01 (test configuration) |
| Technically verified | F09 face test; G01 synthetic proportions; hair synthetic-head test; H28 reproducibility (0.0 m); `verify_charsys` PASS |
| Visually reviewed (by me) | F09 (better smile and JawOpen than F06); H30/H34/H35/H31/H32/H33 (none better than H28) |
| Approved for production | none |

| Item | Result |
| --- | --- |
| Changed | `face.py` (smile intensity/asymmetry, JawOpen shaping, jaw band start and corner-centred ramp), `hair.py` (placement abstraction with real-scalp placement, scalp base, configurable cap face cut, fringe block, lock-shape variation with per-family opt-out, felt shader), `face_test.py` (per-side corner lift), `hair_experiments.py` (robust summary), new `tests/hair_generic_test.py` |
| Face | F09: Smile corners +9.6 mm (asymmetric L 11.6 / R 7.7), eyes narrow to 25.7%; JawOpen 25.5 mm, chin drop 9.7 mm, interior 64%; visible corner stretch 3.48 → 3.30 (not solved) |
| Hair | H28 stays best. Lock construction: spikes or wider; felt shader ineffective; real-scalp placement works but needs re-tuning (skin patch) |
| Metric vs visual | H30 had the best IoU (0.8502) but a visually bad spike: the visual judgement wins |
| Genericity evidence | G01 (face, different proportions) and the synthetic egg head (hair) pass; independence from boy names and proportions shown for these modules. Other topology and hairstyle types are not shown |
| C++ engine | Not changed |
| Expensive operations | 7 hair variant runs (about 2 min each), 4 face builds and tests, 1 synthetic face build, 2 close-up diagnostics, 1 regression |
