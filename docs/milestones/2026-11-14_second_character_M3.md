# Milestone 2026-11-14: second character M3, one reusable facial production system

| Item | Result |
| --- | --- |
| Status | Experimental; technically verified; visually reviewed by me; **not approved**; nothing published |
| New shared systems | `face_generic.py` (eyes, lids, lashes, brows, ears, nose, blush, action units, preset bake), `face_library/expressions.json` (13 action units, 14 presets from #34, 2 optional), `accessories.py` (`glasses/1`), opt-in extensions of `face.py` and `geom.eye_material`, `face_system_test.py`; `face_test.py` generalised |
| Girl | Open eyes with highlights and lashes; Blink 0% eye; per-eye blinks; partial blinks on the true arc; neutral closed soft smile; Happy/Smile with teeth 18% and tongue 12% of the mouth area; 14 + 2 presets; glasses with 0 intersections in 34 states and 10 gaze cases; gaze clean (0 eyeball/lid intersections) |
| Synthetic G03 | Very different face from the same code (ellipsoid outward eyes, half-closed lids, slit mouth without teeth, rectangular glasses): builds and passes, except the documented ellipsoid gaze limit |
| Engine | No C++ engine change. Export merges per-character expression names; new package `girl_auburn_bun_glasses_m3`: look-at moves her eyes, life blink uses her morph, 10 semantic expressions resolve and move the face; 694 assertions |
| Boy | Unchanged: F09 face_test 36/36 identical, face arrays identical, `verify_charsys` PASS, `ctest` 4/4 |
| Bugs found and fixed | linear blink morphs pass through the eye (in-between keys on the arc); glasses temples through ears and skull (obstacle routing); milky lens |
| Open | rounded closed lids on protruding eyes; ellipsoid eyes under gaze; engine uses linear morphs (no in-betweens), no jaw bone in engine expressions, global blink timing; brows, ears and lash weight differ from #30 (data) |

Details: `docs/second_character/M3_FACE_SYSTEM.md`.

Agents: one primary agent, no subagents. Token and cost figures are not available to me and are not estimated.
