# M3: one reusable facial production system (2026-11-14, experimental, awaiting review)

Status:
- Technically verified: the tests below.
- Visually reviewed by me: the sheets listed below.
- **Not approved; nothing published.** The boy's v6, 1.0.0, frozen baselines and the F09/H28 candidates are
  unchanged.

## Phase A: assessment and plan (written before implementation)
**What existed and was reused:**
- `face.py`:
  - lid-seam blink (`lid_seam/1`, computed closing angle);
  - lips with a seam, interior and jaw bone (`lips_jaw/2`);
  - smile coupling (cheeks, lower lids).
- The rig-property control layer (`face_<Name>` drives every shape key of that name).
- The engine expression map (TD-39).

These already took their sizes from the spec and the geometry. Their only character coupling was a duck-typed
"B" object: `G`, `Z["mouth"]`, `EYE_R`, `face_y` (the boy passes `body_v6`).

**Gaps:**
1. The eyes were the boy's half-closed shells: no rest openness, no highlights, spherical and forward-looking only.
2. Four expression keys, with no library.
3. No teeth or tongue.
4. No accessories module.
5. `face_test.py` used the boy's object names.

**Plan:**
1. A `FaceContext` (the same duck type, ray-casting the real head mesh) so the girl's face reuses `face.py`
   unchanged.
2. A generic eye builder in an eye frame (size, ellipsoid scale, yaw and pitch, lid planes, lashes, highlights).
3. Oral layers on the mouth interior.
4. A two-layer expression library: action units plus presets.
5. A glasses accessory placed from landmarks.
6. Generalised tests; validation on the boy (regression), the girl and a synthetic face.

All new behaviour in shared code is opt-in, so the boy's legacy outputs cannot change.

## What was built
| Piece | File | Shared or character data |
| --- | --- | --- |
| Generic face build (`spec.face.generator = face_generic/1`): face layout, eyes, lids, lashes, brows, ears, nose, blush, mouth, action units, preset bake | `pipeline/charsys/face_generic.py` | shared |
| Expression library: 13 action units, 14 presets from reference #34, 2 optional presets, engine names | `pipeline/charsys/face_library/expressions.json` | shared |
| Opt-in extensions of the existing modules (defaults unchanged):<br>• lower-lip drop and extra lip shapes;<br>• interior that follows the lip shapes;<br>• oral layers (teeth, tongue);<br>• jaw-weight floor for faces on a full-body skin;<br>• partial-closure blink keys | `pipeline/charsys/face.py` | shared |
| Eye material: highlights, ellipsoid scale, sclera colour (defaults unchanged) | `pipeline/charsys/geom.py` | shared |
| Accessories: `glasses/1` (rim shape, size from eye spacing, wrap, bridge, temples routed over obstacles, optional lenses) | `pipeline/charsys/accessories.py` | shared |
| Build integration | `build_character.main_generic` (generic path only) | shared |
| Engine export: per-character expression names merged over the rig profile's map | `export_engine.py` (Python only) | shared |
| Tests:<br>• `face_system_test.py` (new; any generic face);<br>• `face_test.py` (part names from the rig; boy defaults unchanged);<br>• C++ semantic-expression test | `pipeline/charsys/tests/`, `tests/test_imported_character.cpp` | shared |
| Girl face, expressions and glasses | `spec.face`, `spec.accessories` (spec 0.3.0) | character data |
| Synthetic face G03 | `assets/characters/boy_yellow_hoodie/experiments/generic_tests/G03_face_synthetic.json` | test data |

### Generic capabilities and their configuration
- **Eyes** (`spec.face.eyes`):
  - geometry: radius, protrusion out of the face, ellipsoid `scale`, outward `yaw_deg`, `pitch_deg`;
  - iris and pupil sizes and colours, sclera colour, any number of `highlights` (x, z, r);
  - lid rest openness and shape (`upper_edge_deg`, `upper_back_tilt`, `lower_edge_deg`, `lower_tilt`, gaps,
    thickness);
  - lash line (span, thickness, flare to the outer corner), outer lashes (count, lengths), lower lash hint;
  - `lid_tracking`: the lids follow a fraction of the gaze.

  The eye centre is placed from the head surface, and the eye bones are moved to the eye centres.
- **Blink:**
  - `Blink.L` and `Blink.R` via `lid_seam/1` in each eye's frame, with in-between keys at 25/50/75% on the true arc;
  - `timing` data (close, hold, open, mean interval) is stored in the master and the spec.
- **Mouth** (`spec.face.mouth`, `lips_jaw/2`):
  - neutral curve (`frown_m` < 0 gives a closed smile), lip and line colours;
  - extra shapes `MouthFrown`, `MouthWide`, `MouthO` (width, upper lift, lower drop, corner curve);
  - jaw angle, pivot and weight bands;
  - `oral.teeth_upper` / `teeth_lower` / `tongue` (depth, width, colour, relief).
- **Expressions** (`spec.face.expressions`): global intensity, per-preset scale, per-preset weight overrides,
  optional presets.
- **Glasses** (`spec.accessories.items[]`): rim radius (absolute or fraction of the eye spacing), aspect,
  superellipse shape, offset, eye and skin clearances, wrap, wire radius, bridge, temples, lenses, material.

## Results
### Girl (`girl_auburn_bun_glasses`, spec 0.3.0)
From `docs/evaluation/second_character/M3_face_system_test_girl.json`. "Eye" is the share of front rays over the
eye opening that reach the eyeball. Both sides are equal unless shown.

| State | Eye % | Mouth open mm | Corner lift mm | Teeth % / tongue % | Brows mm | Max face stretch |
| --- | --- | --- | --- | --- | --- | --- |
| Neutral (closed soft smile) | 76.1 | 5.6 (lip height) | +2.2 | 0 / 0 | 0 | 1.00 |
| Blink | **0.0** | 5.6 | +2.2 | 0 / 0 | 0 | 1.00 |
| Smile = Happy (open smile) | 75.2 | 26.4 | +12.8 | **18.4 / 12.2** | 0 | 1.41 |
| Laugh | 0.0 | 31.7 | +14.2 | 23.0 / 0.4 | 0 | 2.07 |
| Surprise | 77.9 | 21.5 | +2.5 | 5.4 / 5.0 | +6.0 | 1.84 |
| Sadness | 68.1 | 5.6 | −2.8 | 0 / 0 | +1.5 (inner up) | 1.00 |
| Anger | 76.1 | 5.6 | −1.8 | 0 / 0 | −3.5 | 1.00 |
| Confusion | 76.1 | 5.6 | +0.2 | 0 / 0 | +4.6 / −1.4 | 1.00 |
| Squint | 0.0 (closed arcs, as #34) | 5.6 | +4.2 | 0 / 0 | 0 | 1.16 |
| Frown | 76.1 | 5.6 | −4.5 | 0 / 0 | −0.9 | 1.00 |
| MouthOpen | 76.1 | 21.9 | +5.5 | 9.5 / 10.1 | 0 | 2.55 |

Other girl results:
- **Per-eye blink:** LeftEyeClosed / RightEyeClosed close one eye only (0% / 76.1%).
- **Partial blinks:** eye visible 68 → 50 → 33 → 17 → 0% at 0.15 / 0.35 / 0.5 / 0.65 / 0.85.
- **Eyeball and lids:** 0 eyeball/lid triangle intersections in every state.
- **Gaze** (eye controls at ±20° yaw, ±12° pitch, open and blinking): 0 intersections; closed eyes stay 0% visible;
  the eye rotates exactly as commanded.
- **Glasses:** 0 intersections with the face, skin, ears, lids or brows in every state (34 states incl. partial
  blinks) and every gaze; smallest frame-to-skin gap 1.55 mm; the frame never blocks the eye opening (0%).
- **Build:** about 40 s; 28 face controls (13 action units + 15 presets); 144 in-between drivers, all simple
  expressions (no Python auto-run needed).

**Girl body unchanged from M2** (M3 master):
- `body_measure`: crown 0.970 m, hand tips 0.375 m, legs 75.1 mm.
- `deform_test`: the same peak stretch at every joint as M2 (shoulder 4.39, hip 6.98, fingers 4.20).

**Engine** (`tests/test_imported_character.cpp`, new package `girl_auburn_bun_glasses_m3`, 694 assertions pass):

| Behaviour | Girl M3 |
| --- | --- |
| Look-at | eye axis error 0°, eye meshes move (11 mm) |
| Life-layer blink | uses her `Blink` morph |
| Semantic expressions | happy, sad, surprised, angry, laugh, squint, confused, frown, blink, jawOpen: all resolve, reach full weight and move the face (2.9–61.6 mm) |
| Reach, grasp, walk, idle | unchanged from M2 |

The M2 package (no face) still reports blink and expressions as unsupported.

### Synthetic face G03 (engineering test, not a character)
Configuration:
- the G02 body: 1.5 m, small head;
- small ellipsoid eyes turned 12° outwards and 4° down, half-closed lids, no outer or lower lashes, one highlight,
  green iris;
- thick low brows, larger ears, a wide flat slit mouth without teeth or tongue, no blush;
- rectangular dark glasses without lenses;
- expression intensity 0.7 with per-preset overrides.

No code change was needed. Results:
- It builds 26 controls; Blink 0%; partial blinks are monotonic; 0 eyeball/lid intersections in all states.
- The build reports a warning for the ellipsoid eyes.
- Gaze: up/down is clean; ±20° yaw gives 606 eyeball/lid intersections (the limitation below).
- **Glasses:** the first G03 build put the temples through its high, large ears (112 intersections). This was a
  generic defect, now fixed: temples route over obstacles and are re-projected outside the head. After the fix:
  0 intersections in all states, smallest skin gap 0.4 mm.

### Boy regression (no change allowed)
- **F09 rebuilt with the M3 code:**
  - `face_test.py` gives all 36 values identical to `docs/evaluation/face_controls/face_test_F09.json`, with both
    the old and the generalised test;
  - every face, lid, lash, brow, mouth and jaw array is identical.
- **Ears and hair:** these differ only in vertex order. The same shapes match to 7.5e-9 m (ears) and 2.4e-7 m
  (hair) by nearest vertex. This is pre-existing: two builds of the unchanged HEAD code differ the same way (see
  Findings).
- `verify_charsys.py`: PASS (build from spec equals v6, geometry fingerprint, store tests, reuse test).
- `ctest`: 4/4, including the three frozen image regressions.

## Visual review (my judgment, separate from the numbers)
Evidence in `docs/evaluation/second_character/`:
- `M3_neutral_vs_ref30.jpg`, `M3_expressions_vs_ref34.jpg`;
- `M3_girl_expressions.png`, `M3_girl_action_units.png`, `M3_girl_gaze.png`, `M3_girl_views.png`;
- `M3_face_test_boy_F09_vs_girl.jpg`;
- `M3_G03_expressions.png`, `M3_G03_gaze.png`.

**Close to the references:**
- large, fully open round eyes filling about half of each rim;
- brown iris with a large upper highlight and a small lower one;
- a dark upper lash line with outer lashes;
- round thin copper frames centred slightly above the eyes, with temples to the ears;
- a small nose with blush;
- a small closed soft-smile neutral mouth;
- an open smile showing upper teeth and a pink tongue;
- the expression set reads as in #34: one-eye closures, wide-open, surprise with an O mouth and raised brows,
  sadness with inner brows up and drooping lids, anger with lowered brows, confusion with one brow raised.

**Differs:**
1. **Closed eyes look rounded:** the lids cover a 14 mm protruding eye. #34 draws closed eyes almost flat. See the
   limitation below.
2. **Brows:** higher and thinner than in #30 (data: `brows.height`, `thick_m`).
3. **Ears:** smaller than in #30 (data: `ears.radii_m`).
4. **Lash line:** lighter than the reference's.
5. **Face shape:** the cheeks and jaw are the M2 head ellipsoid, narrower than the reference's round cheeks
   (body milestone, not face).
6. **Colour:** the test renders use a neutral grey light, so their muted colour is not comparable with the warm
   reference renders.
7. **No hair:** the face reads bald (hair is M4).

## Problems found and fixed during M3
- **Linear blink morphs pass through the eye.** A 95° lid rotation stored as one morph moves the lid along a chord:
  at 50% the lid edge is at 0.68 of the eye radius, inside the eyeball, so every partial blink and preset (Squint,
  Laugh, Sadness, reduced intensities) showed the open eye.
  - Fix (generic, opt-in): partial-closure keys at 25/50/75% on the true arc, driven piecewise; presets baked from
    the arc. Error about 0.8 mm of chord.
  - The boy's legacy blink (62–70°) has the same mid-blink effect; it is **not** changed (his path is frozen).
- **Flattened closed lids expose the eye under gaze:** 20–35% visible at 20° with `flatten` 0.3. The girl uses
  `flatten` 0. This trade-off is measured; see the limitations.
- **Ellipsoid eyes cut the lids under gaze:** 816 intersections at 20° in a girl test build. Kept as a supported
  but flagged option (build warning). The girl uses spherical eyes.
- **Lid tracking** (linear-blend skinning) shrinks the shell by about 0.6 mm at 20°: closed-lid offset raised to
  1.2 mm.
- **Glasses temples** cut through large ears, and after lifting, through the skull side: obstacle routing plus
  re-projection.
- **Lens material** looked milky (coat plus alpha): now a plain low-alpha surface.

## Findings (not caused by M3; not fixed)
- **Vertex order:** the boy's `ear.L`, `ear.R` and `hair_mass` vertex order changes between builds of identical code
  (seen between the stored F09 build, a HEAD rebuild and the M3 rebuild). The shapes are equal to 2.4e-7 m.
  - Harmless for rigid parts and for the geometry fingerprint used by `verify_charsys`.
  - It would matter for anything keyed on vertex indices of these objects (e.g. future morphs on hair).

## Limitations and unsupported face structures
1. **Rounded closed eyes on protruding eyes.** A gaze-safe closed lid must stay a shell concentric with a spherical
   eye, so it is as round as the eye's protrusion. Flatter closed lids need either gaze suppression while the lids
   close (Blender driver plus an engine change) or a flatter eye design; both are proposed, not done.
2. **Non-spherical eyes:** correct when static or with small gaze; the eye bones rotate the mesh rigidly, so large
   gaze cuts the lids. Iris-sliding gaze (shader or UV) is not implemented.
3. **Engine blink and expressions are linear morphs:** the engine does not use the in-between keys, so a mid-blink
   briefly shows the lid inside the eye (0.07 s close, 0.14 s open for the girl). Supporting morph in-betweens is a
   possible engine change (not made; needs your approval).
4. **Engine jaw:** engine `jawOpen` drives the lip morph only (2.9 mm). The `DEF-jaw` bone rotation is a Blender
   driver; the engine evaluates no drivers. Presets with JawOpen open less in the engine than in Blender.
5. **Blink timing:** stored per character, but the engine life layer still uses one global timing. Using it needs
   a small engine change (proposed, not made).
6. **Teeth and tongue are colour/relief layers on the interior surface,** not separate 3D meshes: correct from the
   front and three-quarter, flat from extreme angles.
7. **Mouth types:** horizontal slit mouths only (`lips_jaw/2`). Beaks, muzzles and snouts need another generator.
   Confusion's slanted mouth is approximated (symmetric shapes only; `smile_asymmetry` gives a lop-sided smile).
8. **Lid tracking** is a fixed fraction of the gaze, not pitch-only tracking.
9. **Lens:** not exported to the engine (no transparent materials there); the frame is.
10. **Symmetry:** one parameter set per side. The missing right-side reference of the girl is not assumed away; her
    face is symmetric by data, not by assumption of the code.
11. **Unsupported structures:**
    - more than two eyes, or a single eye;
    - eyes not on a front-facing head (side eyes);
    - ears that are not ellipsoids (cat or elf ears: the builder would need a shape option);
    - noses other than a bump;
    - faces without a ray-castable front surface;
    - glasses on heads without ear landmarks (the temples then end at a fallback point).

## How future characters get easier
A new humanoid face is a `spec.face` block, a `spec.accessories` block and an optional expression tuning, with no
code:
1. Measure the layout in the reference views (the M1 tool chain), and choose eye, lid, lash, brow and mouth values.
2. Build with `body_generic/1`; the face, glasses and 13 action units, plus the 14 presets, come out.
3. Run:
   - `face_system_test.py` (states, gaze, glasses, sheets);
   - `face_test.py`;
   - the engine export, then the C++ package tests (blink and semantic expressions are tested automatically when
     present).

The G03 synthetic face shows a strongly different face from the same code.

## Convergence of the boy (not done; needs your approval)
The boy's v6 eyes (half-closed shells) are expressible in the generic eye builder:
- `upper_back_tilt` −0.18;
- a low `upper_edge_deg`;
- his `lips_jaw/2` mouth config.

A migration would rebuild his face with `face_generic/1`, compare it with v6 and F09 in the existing harness and
`face_test`, and publish a new version only with your approval. Until then he stays on the legacy path.
