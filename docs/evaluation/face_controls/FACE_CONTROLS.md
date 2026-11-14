# Facial controls: Blink and Smile fixes (2026-11-14, experimental F01)

Test: `pipeline/charsys/tests/face_test.py <master.blend> <out>`. It drives the rig's `face_*` controls, measures
with ray casts and mesh distances, and renders front and ¾ close-ups.

| Measure | 1.0.0 (v6 keys) | F01 (`lid_seam/1` + `corner_lift/1`) |
| --- | --- | --- |
| Blink: eyeball visible from the front | 0% | 0% |
| Blink: closed lid proud of the eyeball | 6.0 mm (skin-coloured ball over each eye) | **3.75 mm**; dark lash seam visible |
| Blink: closing angle | 62° fixed (overshoots the lower lid) | **41.1°**, computed from the lid edges (−4.5° and −42.6°) + 3° overlap |
| Smile: mouth-corner lift relative to the centre | +4.5 mm (neutral −3.5) | **+7.0 mm**, widened ×1.12 |
| JawOpen opening | 13.6 mm (dark patch; no cavity, no jaw) | unchanged |

Evidence: `F01_blink_smile_vs_1.0.0.jpg`.
- Top row: 1.0.0, Blink front, Blink ¾, Smile.
- Bottom row: F01.

Implementation:
- `pipeline/charsys/face.py`, selected by `spec.face.blink` and `spec.face.smile`; the default keeps the v6 keys.
- Override file: `assets/characters/boy_yellow_hoodie/experiments/face/F01_lid_seam_smile.json`.
- The drivers from the `face_*` rig controls work unchanged: the face test drives the controls.

Regression: `verify_charsys.py` passes (67 checks, 0 failures). The default build still equals v6, and 1.0.0 is
unchanged.

**Not adopted or published** (identity-level face change: owner approval).

Open items:
- The closed lid is still slightly rounded.
- JawOpen has no mouth cavity and no jaw rotation.
