# Next task

1. **Owner review (waiting):**
   - H26 hair: `docs/evaluation/hair_experiments/H26_review_views_1-4.jpg` and `H26_review_views_5-8.jpg`.
   - F02 face: `docs/evaluation/face_controls/F02_review_1.0.0_vs_F02.jpg`.
   - Nothing is published until you decide. If approved: one combined build (spec + H26 + F02), published as 1.1.0
     with `--identity-change-approved-by`, then `reuse_test.py` and `face_test.py` on it.
2. **Next engineering milestone (no approval needed): coordinated expressions as a reusable layer.**
   - Smile also raises the cheeks and slightly narrows the eyes. Add cheek bulge and lower-lid lift shape keys,
     generated from landmarks.
   - Reduce the mouth-corner skin stretch (softer jaw weights at the corners).
   - Measured with `face_test.py`; experimental override only.
3. Later (see `docs/CHARACTER_REUSABILITY.md`):
   - bridge charsys rigs to the engine's character-independent actions (needs your go-ahead: engine change);
   - second-character integration test.
