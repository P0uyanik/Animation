# M2: generic body generation and rig fitting (2026-11-14, experimental, awaiting review)

Status:
- Technically verified: the tests below.
- Visually reviewed by me: the deformation sheets.
- Not approved; nothing published.
- The boy's v6, 1.0.0 and baselines are unchanged.

## What was built
| Piece | File | Shared or character data |
| --- | --- | --- |
| Generic body generator `body_generic/1`: head, neck, torso loft, arms, legs, feet as one remeshed skin, plus 5-finger hands (3 joints per finger) | `pipeline/charsys/body_generic.py` | shared |
| Joint set derived from the body parameters (one definition for mesh and skeleton); `spec.rig.joints` overrides any joint | `body_generic.joints`, `hand_frames` | shared |
| Rig fitting from data | `pipeline/charsys/rig_profiles/rigify_human_metarig.json` (bone → joints, finger map, removals, eye bones) + `fit_metarig_from_joints` | shared (profile) |
| Skinning: heat weights, then role rules (`skin`, `hand`; never object names), then the legacy cleanup, nearest-bone fallback, optional per-role smoothing, 4-influence limit | `rule_predicate`, `rig_generic`; profile `default_weight_rules`; `spec.rig.weight_rules` / `weight_smooth` | shared + per-character overrides |
| Component map from the spec (`spec.components`); the legacy map is the default | `build_character.organise(..., components)` | shared |
| Generic build entry (only for `spec.body.generator = body_generic/1`) | `build_character.main_generic` | shared |
| Girl base body | `assets/characters/girl_auburn_bun_glasses/spec/…spec.json` (`body.params`, measured values in metres with provenance) | character data |
| Tests | `tests/body_measure.py`, `tests/deform_test.py` (any Rigify charsys master); C++ behaviour tests now on 3 packages | shared |

## Results
**Girl vs. the M1 reference measurements** (`docs/evaluation/second_character/M2_girl_measure.json`):

| Measure | Built | Target | Pass |
| --- | --- | --- | --- |
| Crown height | 0.970 m | 0.97 m ±2% | yes |
| Eye line (fraction of the 1.10 m total) | 0.706 | 0.706 ±0.01 | yes |
| Hand tips | 0.375 m | 0.374 m ±5% | yes |
| Leg width | 75.1 mm | 75 mm ±5% | yes |
| Leg centre | ±52 mm | ±52 mm | yes |

The first build missed legs (−12%) and hands (−11%). Those were my parameter estimates; I corrected them and
recorded the change in the spec provenance.

**Deformation** (`deform_test.py`: left side, FK controls, posed by intent; the 8 poses are listed in the table; max
and 99th-percentile edge stretch).

| Pose | Girl (generic, smoothed) | Synthetic G02 (generic, profile defaults) | Boy 1.0.0 (legacy) |
| --- | --- | --- | --- |
| shoulder raise 70° | 4.39 / 1.18 | 2.23 / 1.09 | 2.74 / 1.00 |
| shoulder forward 60° | 4.02 / 1.14 | 1.78 / 1.04 | 2.36 / 1.00 |
| elbow 90° | 1.81 / 1.01 | 1.67 / 1.01 | 2.41 / 1.00 |
| wrist 60° | 2.05 / 1.00 | 1.83 / 1.00 | 1.92 / 1.00 |
| hip forward 80° | **6.98 / 1.30** | 4.46 / 1.30 | **9.83** / 1.00 |
| knee 90° | 2.17 / 1.10 | 1.83 / 1.03 | 5.65 / 1.00 |
| ankle 30° | 1.22 / 1.05 | 1.25 / 1.02 | 1.36 / 1.00 |
| fingers curl 70° | 4.20 / 1.00 | 4.49 / 1.15 | 4.28 / 1.00 |

Sheets: `M2_deform_girl_m2.png`, `M2_deform_synthetic_G02.png`, `M2_deform_boy_1.0.0_baseline.png`.
- No tearing at any joint.
- The boy's p99 of 1.00 reflects his many rigid parts.

Per-role weight smoothing (`weight_smooth`) lowered every peak on the girl's skin (hip 7.7 → 7.0, wrist
4.9 → 2.05, shoulder 5.4 → 4.4) at a slightly higher p99.

**Engine** (`tests/test_imported_character.cpp`, now boy + fixture + girl; 269 assertions pass). The girl exports
through the **unchanged** `humanoid_rigify` profile: 73 bones, 39 roles.

| Behaviour | Girl M2 result |
| --- | --- |
| Reach | 0 mm |
| Grasp | both hands, 5 fingertips on the object (gap 4.5 mm) |
| Walk | step 74.6 mm from her 234 mm legs; 1/59 frames with both feet moving |
| Idle | supported |
| Look-at | the bone aims (0°); there are no eye meshes yet |
| Blink and expressions | reported **unsupported** (no face yet) |

**Synthetic configuration G02** (`experiments/generic_tests/G02_body_synthetic.json`; engineering test, not a
character):
- The body: 1.5 m, slim and non-chibi, small head, long limbs, 40° arms, long fingers.
- It has no character weight rules, so it uses the profile defaults only.
- Result: builds and rigs with 0 unweighted vertices; crown 1.504 m (target 1.50), head width 0.169 m (0.17); joints
  exactly as specified.

**Boy unchanged:** `verify_charsys` PASS (build equals v6 geometry; store and reuse tests); `ctest` 4/4 including
the frozen image regressions.

## Problems found and fixed
- **The face skin followed the eye bones.** Heat weighting bound part of the girl's face to the gaze bones, so gaze
  deformed the skin (14 mm). Eye bones are now denied for the skin role in the shared profile defaults, and a C++
  test asserts that gaze deforms nothing when there are no eye meshes.
- `body_measure.py` used a fixed 0.75 m head-height threshold (a chibi assumption). It now measures relative to the
  eye bones.

## Problematic joints (not solved)
1. **Hip flexion** creates a crease in the lower torso (girl 7.0× peak, synthetic 4.5×, the boy's legacy rig 9.8×).
   Needs corrective shapes or a dedicated hip loop and weight profile.
2. **Shoulder raise** stretches the armpit on the chibi torso (4.4×).
3. **Finger curl peaks** (about 4.2–4.5×) come from the compressed inner finger surface. They are similar for all
   three bodies (the hands are not smoothed).
4. **Not tested:** toe bones (Rigify has them; not posed), wrist twist, spine bending, clavicle shrug.

## Assumptions and limits
- The generator is **left/right symmetric** (one parameter set per side). Asymmetric body details are not supported;
  her asymmetries (fringe part, flower positions) belong to hair and accessories. Her missing right-side reference is
  recorded, not assumed away.
- Humanoid only: the Rigify human metarig profile.
- The torso and shoulders are estimates inside the clothing silhouette; they can only be validated once garments
  exist (M5).
- The girl's head width is the skull only; ears and face come in M3.

## Reusability
**Shared now:**
- body generation, joint derivation, rig fitting (profile data), role-based weight rules with profile defaults,
  smoothing;
- the component map from the spec, the generic build entry, the engine export;
- the measurement and deformation tests.

**Character-specific (spec data):**
- body parameters, joint overrides, weight-rule overrides, smoothing amounts, component map, skin colour.

**The boy on the legacy path** (compatibility baseline, unchanged):
- `body_v6` part builders (head, face, hoodie, hands, legs, shoes, backpack);
- `fit_metarig` with literal joint coordinates;
- `allowed_bones` by object name;
- the legacy `COMPONENTS` default;
- `rig_character`.

**Convergence plan** (not done in M2; it needs the face and garment milestones):
1. Express the boy's joints as `spec.rig.joints`, copied from the legacy constants, and his body as
   `body_generic` parameters under the clothes. Check that the generic fitting reproduces his bone positions
   exactly.
2. Rebuild his face (M3) and outfit (M5) with the shared modules. Compare against v6 with the existing harness:
   silhouette, metrics, deformation, engine tests.
3. If equal or better, publish as a new boy version with your approval. Only then retire `body_v6`.

**For the third character:**
- Extract views and masks with `extract_reference_views.py`.
- Write body parameters from the measured silhouette.
- Rely on the profile's default weight rules.
- Build with `body_generic/1`, then run `body_measure`, `deform_test` and the engine behaviour tests.

No new code is needed for a humanoid body. This is shown for two different configurations (the girl and the
synthetic G02); it is **not** a proof of full reusability: face, hair, garments and accessories are still ahead.
