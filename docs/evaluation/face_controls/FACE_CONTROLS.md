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

## F02: lips, mouth interior and jaw (`lips_jaw/1`), plus the F01 Blink (2026-11-14, not approved)
Override: `experiments/face/F02_lips_jaw_cavity.json`. Code: `pipeline/charsys/face.py` (`build_mouth_lips`,
`cut_mouth_and_cavity`, `add_jaw`).

How it works:
- The lips are upper and lower strips meeting at a seam; they are closed at rest.
- A dark mouth interior hangs between the inner lip edges. Its top follows the head and its bottom follows the jaw,
  so it fills exactly the gap between the lips.
- The jaw is a deforming `DEF-jaw` bone added to the generated rig. Its pivot comes from the ear landmarks, and
  `face_JawOpen` drives its rotation.
- Jaw weights come from the mouth line and the pivot: sharp at the lip seam, widening past the corners, fading
  towards the cheeks and the back.
- Character data comes from `spec.face.mouth` (size, frown, smile, jaw angle) and the built geometry (mouth line,
  face surface, landmarks).

A boolean cut was tried first and rejected: the head is a closed surface, so a difference only dented it (no hole),
and the cavity showed through as a dot.

| Measure (`face_test.py`) | 1.0.0 | F02 |
| --- | --- | --- |
| Cavity visible, mouth closed | n/a | 0% |
| JawOpen: interior visible in the opening | none (dark patch) | 64% of the probe grid |
| JawOpen: chin drop (jaw bone) | 0 | 6.7 mm |
| JawOpen: lip opening at the centre | 13.6 mm (patch stretch) | 19.9 mm |
| Smile corner lift (relative to the centre) | +4.5 mm | +7.0 mm |
| Blink: lid proud / eye visible | 6.0 mm / 0% | 3.75 mm / 0% |
| Max skin stretch outside the opening (JawOpen) | 1.0 | 3.5×, localized at the mouth corners |

Reuse proof:
- The F02 build (glb included) was published to a **temporary** store in the scratchpad, not the real store.
- `reuse_test.py` passes all checks there: 411 bones / 74 deforming including `DEF-jaw`, glTF skeleton 74 with 4
  morph targets, episode link and override, master unchanged.
- `reuse_test.py` now reads the expected bone counts from the version manifest instead of the boy's 410/73.

Evidence: `F02_review_1.0.0_vs_F02.jpg`.
- Rows: neutral, Blink, Smile, JawOpen.
- Columns: 1.0.0 front, F02 front, 1.0.0 ¾, F02 ¾.
- All from identical cameras.

Limitations:
- The interior is flat and dark, with no teeth or tongue; depth comes from colour only.
- Skin stretch concentrates at the mouth corners.
- Smile moves only the mouth: no cheek or eye coordination yet.
- The closed lid is still slightly rounded.
