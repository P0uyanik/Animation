# Next task

1. **Owner review (waiting):**
   - F09 face: `docs/evaluation/face_controls/F09_review_F06_vs_F09.jpg`.
   - H28 hair: unchanged candidate; the new options are documented in
     `docs/evaluation/hair_experiments/HAIR_EXPERIMENTS.md`.
   - Nothing is published. If approved: combined build (spec + H28 + F09), 1.1.0 with
     `--identity-change-approved-by`, then the reuse, face and export tests.
2. **Recommended next engineering step: felted surface through fibres.**
   - Carry the per-character fur (`spec.fur`) into the master and the engine package. Today it exists only in the
     evaluation file; the shader-only approach was ineffective.
   - Measure close-ups against reference #7.
3. **Face:**
   - mouth-corner stretch: a corner skin-follow key for JawOpen, like the Smile coupling;
   - faint closed-lid rim.
4. **Hair:** re-tune a surface-placed variant of H28 (hairline, offset) so the real-scalp path can replace the
   ellipsoid for this character.
5. **Second-character readiness:** the items in `docs/CHARACTER_REUSABILITY.md`.
