# Milestone 2026-11-14: CP-2 face (F06) and hair (H28) quality

| Item | Result |
| --- | --- |
| Changed | `face.py`: `lips_jaw/2` (lip and seam layout, lip offsets, shaded interior), closed-lid thickness, flatten and lash options, `add_smile_coupling`. `hair.py`: per-family irregularity controls. `build_character.py`: wiring (eyes into blink, smile coupling) |
| Experiments | Face F03 → F06; hair H27, H28, H29; combined H28+F06; each step one hypothesis (H27 changed two groups and was split into H28/H29) |
| Face F06 | Neutral: one thin line (0% interior). Blink: no dome, dark lash curve, eye covered. Smile: corners +7 mm, cheeks raised, eyes narrowed 37.2 → 31.9%. JawOpen: shaded depth, 64% interior |
| Hair H28 | IoU 0.8493 (best), contour 2.92%, #7 front 2.97% (H26 3.63%); irregular crown with a dominant front tuft; coverage kept |
| Metric vs visual | No conflict for the adopted candidates. H27 was worse both numerically and visually |
| Generic | All new behaviour is driven by `spec.face` / `spec.hair` parameters and landmarks; defaults keep F01/F02/H26 reproducible |
| Tests | `face_test.py` per variant; `hair_experiments.py` (6 measured views + 8-view review); `verify_charsys` PASS (67/0) |
| C++ engine | Not changed |
| Limitations | Faint closed-lid rim; subtle smile; small JawOpen without teeth or tongue geometry; corner stretch 3.5× on JawOpen; crown tufts fewer and coarser than the references; small crown-top gap |
| Protected | v6, 1.0.0, baselines unchanged; nothing published |
