# Next task

1. **Owner decisions** (no further work needed before them):
   - **H25 hair:** review `docs/evaluation/hair_experiments/cp2_hair_clumps_v2_sheet.jpg`.
   - **F01 face:** review `docs/evaluation/face_controls/F01_blink_smile_vs_1.0.0.jpg`.
   - If both are approved: one combined build (spec + H25 + F01 overrides) into a scratch folder, published as
     1.1.0 with `--identity-change-approved-by "<owner, date>"`, then `tests/reuse_test.py` and
     `tests/face_test.py` on 1.1.0.
2. **Next engineering milestone (no approval needed):** JawOpen with a real mouth cavity.
   - A dark inner-mouth shell behind the mouth patch, plus a jaw bone rotation driven by `face_JawOpen`.
   - Built as a `face.py` generator; measured with `face_test.py` (opening, cavity visible, no face tearing).
   - Experimental override only; no publish.
