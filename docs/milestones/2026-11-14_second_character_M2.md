# Milestone 2026-11-14: second character M2, generic body and rig fitting

| Item | Result |
| --- | --- |
| Status | Experimental; technically verified; visually reviewed by me; **not approved** |
| New shared systems | `body_generic.py`, `rig_profiles/rigify_human_metarig.json` (fitting + default weight rules), spec-driven components, `main_generic`, `body_measure.py`, `deform_test.py` |
| Girl | M1 targets met (crown 0.970, eye line 0.706, hands 0.375, legs 75 mm); 0 unweighted vertices; engine: reach, grasp (both hands), walk, idle supported; look-at bone only; blink and expressions unsupported (no face yet) |
| Synthetic G02 | 1.5 m slim body, profile-default weights: builds and rigs, measurements as specified |
| Boy | Unchanged (`verify_charsys` PASS, `ctest` 4/4) |
| Bugs found | face skin bound to eye bones (fixed in the shared defaults + test); chibi-only threshold in the measure tool (fixed) |
| Open | hip crease (7.0×), shoulder armpit (4.4×), finger-curl peaks (about 4.3×); toe, wrist twist and spine not tested; body symmetric by design |
| Engine | Unchanged; tests extended to 3 packages |
