# T-216 checkpoint

- Done: face_generic/4 (pipeline/charsys/face_generic_v4.py, face_v4/knobs.py, face_v4/chains.py), registered in
  versions.py; build_character.py calls complete_inbetween_chains for face_generic/4+ only.
- Knob design d0 (design0.override.json, layered after T-215 proposal.json): builds, knob-free PASS, face_parity
  --strict PASS (sweep 56/56, max 0.000119 mm). Measures: front 15/27 (eye_to_chin -2.41 -> -1.55, but jaw/cheek
  worse: the chin drop lengthens a narrow lower face). Fit must widen the lower face with the chin.
- Next: controls.json over knob params, t204-sens + t204-search (tools/fit/run.py, unchanged), then acceptance.
