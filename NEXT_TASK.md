# Next task

1. **Owner:** review `docs/evaluation/hair_experiments/cp2_hair_clumps_v2_sheet.jpg` and decide on H25.
   If approved: build from the spec + H25 override into a scratch folder, publish as 1.1.0 with
   `--identity-change-approved-by "<owner, date>"`, run `tests/reuse_test.py` on 1.1.0.
2. **Next engineering milestone (no approval needed, priority 3: rigging/facial controls):** fix the known face-rig
   defects from the pilot report — closed lids bulging over the eyes (Blink), and Smile/JawOpen too weak (no jaw
   rotation, no mouth cavity) — as charsys modules, measured with `pipeline/blender/boy_pilot/rig_tests.py`
   renders, built into a scratch folder only (no publish without approval).
