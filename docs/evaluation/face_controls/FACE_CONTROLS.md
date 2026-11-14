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

## F03–F06: closure, closed lids, coordinated smile, open-mouth depth (2026-11-14, experimental, not approved)
Overrides are in `experiments/face/`; each step changes one group of parameters. Code is in
`pipeline/charsys/face.py`:
- `lips_jaw/2`;
- `add_blink_lid_seam` options `closed_thickness_m`, `flatten`, `flatten_lash`;
- `add_smile_coupling`.

| Step | Change (hypothesis) | Result |
| --- | --- | --- |
| F03 | Skin-tone lips with a thin dark seam band; closed lid hugging the eye (0.6 mm off, 1.0 mm thick); smile coupling (cheeks, corner skin follows the lips, lower-lid squint); shaded interior | Lid 3.75 → 1.6 mm proud, but still a **dome** (the eyeball protrudes); neutral mouth showed a "double line" |
| F04 | Closed eye flattened 45% along its forward axis (eyeball `Blink` key; lid and lash follow); matte line material | No dome; the lash became too faint; the double line persisted |
| F05 | Close-up diagnosis: the double line was the **cast shadow** of lips floating 1.2 mm off the skin. Lip edges now lie on the skin (0.2 mm), with the seam bulging 1.2 mm; flatten 0.38 | Single mouth line |
| **F06** | The lash is not flattened (it stays a dark closed-eye line) | **Candidate** |

Measured with `face_test.py`; the 1.0.0 → F02 → F06 progression:

| Measure | 1.0.0 | F02 | **F06** |
| --- | --- | --- | --- |
| Neutral: interior visible | n/a | 0% | 0% (one thin line, as in 1.0.0) |
| Blink: eye covered | 0% visible | 0% | 0% |
| Blink: closed lid vs. original eye surface | +6.0 mm (ball) | +3.75 mm | **−1.1 mm** (eye front flattened; dark lash curve) |
| Smile: corner lift | +4.5 mm | +7.0 mm | +7.0 mm, plus cheeks raised (1,494 head vertices, radius 40 mm from landmarks) and eyes narrowed (open area 37.2 → 31.9%) |
| Smile: max skin stretch | 1.0 | 1.0 | 1.57 (cheek deformation; no corner tearing) |
| JawOpen: interior visible / chin drop / opening | — | 64% / 6.7 mm / 19.9 mm | 64% / 6.7 mm / 19.8 mm, with shaded depth (reddish edges, dark throat, tongue tint) |

Evidence (identical cameras):
- `F06_review_1.0.0_F02_F06.jpg`
- `combined_H28_F06_vs_1.0.0.jpg`, with the H28 hair
- `F05_review_1.0.0_F02_F05.jpg` (intermediate)

**Generic** (all parameters in `spec.face`; placement from geometry and landmarks):
- The lip layout is relative to the spec's mouth width, height and frown.
- The seam band, lip material and lip offsets are parameters.
- The closed-lid geometry derives its angle from the lid edges; offset, thickness and flatten are parameters.
- Smile coupling: the cheek centres come from the eye and mouth-corner landmarks, with radii as fractions of the
  eye-to-corner distance; corner skin follows the lips' own Smile key; the squint is an angle.
- Interior colours and row count are parameters.

**Assumptions that remain:**
- Eyes look along −Y at rest, and lids are shells around a spherical eye (flatten and squint use this).
- The mouth is a horizontal slit at `Z.mouth` on a surface that `face_y` can ray-cast.
- Landmarks named `eye_L/R` and `mouth` exist.
- Only one smile shape; no per-side asymmetry.

**Limitations:**
- A faint circular outline of the flattened lid remains when closed.
- Smile cheek motion is subtle.
- JawOpen is small. It has no teeth or tongue geometry (shading only), and skin stretch at the mouth corners is
  unchanged (3.5×).
- Expressions are not tested on a second face.

## F07–F09 and the synthetic-proportions check (2026-11-14, experimental, not approved)
| Step | One change group | Result (`face_test.py`) |
| --- | --- | --- |
| F07 | Smile: `smile_intensity` 1.25, `smile_asymmetry` 0.15; coupling `intensity` 1.3, `asymmetry` 0.15, cheek raise 4 mm | corners +9.6 mm (L 11.6 / R 7.7: asymmetry works); eyes 31.9 → 25.7% open; stretch 1.82 |
| F08 | JawOpen: `jaw_open_deg` 7, `jaw_lip_round` 0.9, `jaw_upper_lift_m` 2.5 mm, `jaw_band_start` 0.45 | opening 19.8 → 25.5 mm, chin drop 6.7 → 9.7 mm; visible stretch 3.48 → 3.32 |
| **F09** | `jaw_corner_center` 1: outside the lip corners the jaw ramp is centred on the mouth line | stretch 3.30. The stretch locator shows the remaining 3.3× just outside the corners; the 5× edges are inside the opening and hidden by the interior. No tearing is visible |

Evidence: `F09_review_F06_vs_F09.jpg` (neutral, Smile, JawOpen; front and ¾), `face_test_F09.json`.

**Synthetic proportions (G01)**
- Override: `experiments/generic_tests/G01_face_synthetic_proportions.json`. It is an engineering test configuration,
  not a design.
- Inputs: the F09 face settings on eyes 76 mm apart (64), eye radius 32 mm (37), and a mouth 12 mm lower and 36%
  wider.
- Every criterion holds:
  - blink covers the eye (0%);
  - neutral interior 0%;
  - Smile corners +9.6 mm;
  - JawOpen interior 67%, chin drop 9.7 mm;
  - 0 unweighted vertices.
- Derived values adapt: the closing angle becomes 46° (41° on the boy) and the cheek radius 47.6 mm (40 mm); the jaw
  pivot follows the ear landmarks.

This shows the face modules adapt through landmarks and spec values. It does **not** show support for different
face topology (another head mesh or mouth type); that needs a second production character.

**Status:**
- F09: experimental; technically verified (face test, regression).
- F09: visually reviewed by me, not by you.
- Not approved.
