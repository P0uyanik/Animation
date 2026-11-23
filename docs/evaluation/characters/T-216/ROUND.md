# T-216 checkpoint

- Done: face_generic/4 (pipeline/charsys/face_generic_v4.py, face_v4/knobs.py, face_v4/chains.py), registered in
  versions.py; build_character.py calls complete_inbetween_chains for face_generic/4+ only.
- Knob design d0 (design0.override.json, layered after T-215 proposal.json): builds, knob-free PASS, face_parity
  --strict PASS (sweep 56/56, max 0.000119 mm). Measures: front 15/27 (eye_to_chin -2.41 -> -1.55, but jaw/cheek
  worse: the chin drop lengthens a narrow lower face). Fit must widen the lower face with the chin.
- Next: controls.json over knob params, t204-sens + t204-search (tools/fit/run.py, unchanged), then acceptance.
- Fit (3 sens rounds, final lattice design; search 30 builds seed 216): objective P2 0.556 -> trial 6 0.386, but
  chin drop ~29 mm puts the chin over the blouse collar: face_parity --strict FAILS (collar shrinkwrap flips nearest
  surface; 1-3 vertices up to 16 mm). Lattice/warp floor_m added (neck static) - still fails. Variant B (lattice
  chin dz 0, warp 15.8 mm) passes strict. Garment clearance caps the chin drop. Testing C (bridge only), D (B+bridge).
- Final: candidate = C (bridge Warp -3 mm) + T-215 P2: front 23/27, side 3/7, 3/4 held out 13/24; parity --strict PASS;
  determinism PASS (T-056 rule); glasses rigid. P3-chin* (trial 6) shown on sheets, fails parity (collar).
  Gate (check_all default, full Blender tier): all PASS except test registry (TESTS.manifest outside write-set).
  READY sent to R8 Supervisor session_01NPjxeNFfmkruSmnvcb3uSH.
