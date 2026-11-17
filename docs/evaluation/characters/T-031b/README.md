# T-031b: girl face round 2 (shape, skin tone, open-smile neutral, blush, eyes)

Branch `t-031b-claude-face-r2` (from `t-031-claude-face-v2`). Girl spec **0.9.0, unpublished**. Nothing was published or approved; the owner gives the final visual approval. Frozen items untouched: boy 1.0.0/1.1.0 and v6, tests/data, image baselines, docs/references.

## What changed (all shared and spec-driven; absent options = previous behaviour)

| area | change | where |
|---|---|---|
| Head shape | New optional `body.params.head` options: `lower_half_height` (centre to chin), `lower_roundness` (superellipse exponent of the front outline below the head centre; 2 = the old ellipsoid, 3-4 = full round cheeks, wide jaw, broad short chin), `lower_depth_roundness` (same for the side profile). `neck.top_radius` (neck thickening into the jaw). | `pipeline/charsys/body_generic.py` |
| Calibration | `character_neutral/1`: new soft warm **Front** fill (azimuth 0, elevation 8, strength 0.6, 5000 K, 60 deg source); key light softened (angle 18 -> 28 deg). Front-facing irradiance ~0.97 -> ~1.15. | `pipeline/charsys/render_calibration.json` |
| Skin path | Felt-skin **light bleed** option in the face skin (`face.skin.occlusion.bleed`, `bleed_srgb`, `bleed_face_radius_m`, `bleed_body`, `samples`): shaded skin re-emits warm scattered light in proportion to its occlusion, fully on the face and at a fraction elsewhere. One material for face and body, so they stay matched. | `pipeline/charsys/face_features.py`, `face_generic.py` |
| Mouth | `face.mouth.rest_mix` {shape key: weight} tunes the baked rest shape (the open-smile geometry with teeth, tongue and felt interior already existed from T-031). | `face_features.py`, `face_generic.py` |
| Girl spec | Head: lower_roundness 3.8, depth 2.3, chin_taper 0.3 -> 0.12, lower half 9 mm longer, neck top radius 0.055. Face: cheeks fuller and wider; eyes 9 mm lower, lids opened (43 / -53 deg); brows kept at the same height; **gentle open-smile neutral** (MouthWide 0.7 + MouthSmile 0.55), redder interior and tongue, mouth 4 mm wider; rosier, larger outer-cheek blush; skin bleed 0.72 on the face, 15% on the body. | `assets/.../spec/girl_auburn_bun_glasses.spec.json` |
| Synthetic face B | Own head shape (lower_roundness 2.7, longer softer oval lower face), own mouth mix and bleed values. | `pipeline/charsys/tests/fixtures/face_synthetic_b.override.json` |

**Identity note, for the owner to decide:** `identity.approved_decisions.neutral_expression` said "closed-mouth soft smile". The T-031b brief asks for the reference's open smile, so the line now says "gentle open smile ... owner to confirm at visual approval". Reverting means setting `face.mouth.rest_shape` back to `closed_smile`.

## Evidence (final build = iteration i5)

- `girl_face_front_vs_reference.png`, `girl_face_34_vs_reference.png`: 512 px crops, render next to the reference (#30 neutral tile / front-left).
- `girl_face_before_after_front.png`, `girl_face_before_after_34.png`: 0.8.0 (T-031) | 0.9.0 | reference.
- `girl_fullbody_front_vs_reference.png`: full body front, reference next to the aligned render (fidelity tool, shared calibration). `fidelity_after_sheet30_front(_left).png`: full fidelity sheets.
- `girl_expressions_sheet.png`: neutral (open smile), closed smile, smile, surprise, sadness, thinking.
- `synthetic_expressions_sheet.png`, `girl_vs_synthetic_same_system.png`: the second face (neutral, smile, surprise).
- `fidelity_face_before_after.json`, `skin_delta_e.json`, `face_system_test_summary.json`, `face_test_summary.json`.

## Numbers

Fidelity tool from origin/t-032-claude-fidelity, run read-only from a scratch overlay, views sheet30_front and sheet30_front_left. "Before" is T-031's final measurement (0.8.0 and the old calibration).

**Skin ΔE00 against the reference** (luma-matched ΔE00; ΔL*):

| region | front before | front after | 3/4 before | 3/4 after |
|---|---|---|---|---|
| skin_face | 14.9 (3.2; -17.1) | **2.3** (1.7; -2.0) | 15.6 (2.5; -18.5) | **3.4** (1.4; -4.1) |
| skin_limbs | 3.7 (0.6; -4.6) | 3.3 (2.3; +3.2) | 7.9 (0.2; -9.5) | **1.9** (1.9; +0.2) |

Face and body now match each other: at 3/4 the face renders (201,160,141) and the limbs (200,159,140). From the front the limbs are ~5 L* lighter than the face.

**Face landmarks** (error in head heights, lower is better):

| landmark | front before | front after | 3/4 before | 3/4 after |
|---|---|---|---|---|
| eye_L / eye_R | 0.030 / 0.031 | **0.006 / 0.010** | 0.010 / 0.079 | 0.024 / 0.088 |
| iris_L / iris_R | - | 0.011 / 0.015 | - | 0.024 / 0.076 |
| eye_inner_L / R | 0.029 / 0.024 | 0.062 / 0.058 | 0.040 / 0.014 | 0.034 / 0.011 |
| eye_outer_L / R | 0.010 / 0.006 | 0.026 / 0.039 | 0.057 / 0.040 | 0.025 / 0.043 |
| brow_inner_L / outer_L | 0.023 / 0.021 | 0.024 / 0.028 | 0.018 / 0.014 | 0.013 / 0.023 |
| nose / mouth / chin | 0.024 / 0.022 / 0.021 | **0.001 / 0.001 / 0.003** | 0.029 / 0.050 / 0.104 | 0.007 / 0.019 / 0.087 |
| mouth corners L / R | 0.021 / 0.012 | 0.008 / 0.014 | 0.070 / 0.035 | 0.023 / 0.017 |
| **mean of the visible face landmarks** | **0.0211** | **0.0203** | **0.0432** | **0.0343** |

- The means exclude the `neck` landmark (collar point, garment-dependent). The after means also include the irises, which T-031 did not report.
- Score (two views): 68.2 -> 69.7. Colour sub-score 0.61 -> 0.71; landmarks 0.83 -> 0.84; proportions 0.67 -> 0.68.

**Side effects of the shared calibration on the girl's other regions** (median ΔL*, ΔE00):

| region | before ΔL* (ΔE00) | after ΔL* (ΔE00) |
|---|---|---|
| blouse | -7.0 (5.2) | -1.5 (2.9) |
| boots | -1.4 (4.0) | +0.7 (3.1) |
| shorts | -2.6 (4.6) | +0.4 (4.8) |
| vest | +0.7 (2.6) | +3.7 (3.7) |
| hair | +6.6 (10.6) | +9.7 (11.3) |
| hair accessory | +7.9 (15.2) | +11.6 (15.1) |

The hair was already too light and less saturated (a groom/material issue, outside this task) and is now 3 L* lighter still.

## Checks

| check | result |
|---|---|
| face_system_test (girl 0.9.0) | 0 eyeball/lid and 0 glasses intersections in every preset, action unit and gaze pose. Blink 0% at rest and in every gaze. Eye visibility at rest 76.1% (0.8.0: 69.9%). Neutral now open: mouth 18.2 mm, teeth 7.7%, tongue 9.9%, interior 11.8%. |
| face_system_test (synthetic B) | 0 intersections everywhere, blink 0%, open-smile rest with teeth 8.7% and tongue 11.0%. |
| face_test (girl) | Runs. Blink 0%; lid_proud 4.92 mm (unchanged). Smile: mouth 39.1 mm, corners +20.5 mm, stretch 1.64 (0.7.1: 26.4 mm, 1.54). JawOpen stretch 3.73 (0.7.1: 2.94): both act on top of the already open rest. |
| test_material_presets | ALL PASS (54/54) |
| test_export_engine | ALL PASS (8/8) |
| verify_charsys | PASS: boy geometry equals v6 (worst difference 0.0 m; the known informational `hair_mass` exact-hash note); the master is byte-identical after all tests. |

The boy never goes through the new options (his spec has none, and he uses the legacy face). Note that the **shared calibration change also brightens the boy's renders** (Front fill), though his geometry is untouched. The owner should look at a boy render before approving.

## Visual assessment: what matches now

- **Face shape:** big, round, soft plush face. Full cheeks run down to a wide jaw and a broad, short chin. The chin now sits at the reference chin line, and the visible neck is much shorter. At 3/4 the cheeks round out under the glasses.
- **Skin:** warm peach felt instead of grey-beige, on the face and the body alike.
- **Mouth:** friendly open D-smile with upper teeth, a pink tongue and a red felt interior, at the reference position.
- **Blush:** round, rosy, soft felt patches on the outer cheeks, partly outside the rims as in #30. Clearly visible at 3/4.
- **Eyes:** centres, irises, nose and mouth match the front landmarks within 0.001-0.015 head heights. The openings are larger and rounder.

## Still differs, why, and proposals

1. **Eye size.** The fidelity tool still finds the eyes ~11% too narrow relative to the head height.
   - **Why:** a larger eyeball (44 or 46 mm tried) pushes the upper lid shell through the glasses rim's inner edge (12-24 intersecting triangles per eye in face_system_test), so the radius stays 42 mm.
   - **Proposal:** a follow-up task in the accessory area: rim radius / eye clearance in the glasses spec (`radius_eye_spacing` 0.433 -> ~0.46) or a rim that follows the lid shell. After that, the eye radius can go to 45-46 mm.
2. **Eye corners.** In the front view the corners sit 0.025-0.06 head heights (4-9 px) below the reference corners: the centres were lowered 9 mm to match, and the lid edges meet below the centre line.
   - **Proposal:** a lid "corner lift" option in the shared face (edge meeting points raised by a spec angle). One render-iteration of tuning.
3. **Mottled lower cheeks/chin.** Faint grey blotches on the lower cheeks and the chin. The fidelity tool also reports face fuzz +73% against the reference.
   - **Why:** the shared skin-felt fibre/micro-relief texture after denoising, not the AO (16 -> 32 samples changed nothing visible).
   - **Proposal:** a smoother face variant of skin-felt (lower micro-relief colour strength), measured with test_material_presets.
4. **Limb skin front.** From the front, limb skin is 3 L* lighter than the reference (and the face 2 L* darker); at 3/4 both are within 4 L* of the reference.
   - **Why:** the bleed is weighted by distance from the face; the A-pose arms near the hair get some of it.
   - **Proposal:** fine-tune `bleed_body` (0.15 -> 0.1) after the owner's look.
5. **Calibration side effects.** Vest +3.7 L* and hair +9.7 L* (hair was already too light). A front fill is how the turnaround sheet is lit, and it brought the blouse, limbs and face into range.
   - **Proposal:** fix the hair's tone in the groom/material task. If the owner prefers it, Front 0.6 -> 0.5 with face bleed 0.8 keeps the face while lifting the garments less.
6. **Smile on top of the open rest.** Smile/Laugh open wider than before (39 mm), and JawOpen stretches the skin more (3.7 vs 2.9), because they add to the open rest. SmileClosed from an open rest is still slightly open.
   - **Proposal:** library presets that subtract the rest mix (negative MouthWide) for SmileClosed and a reduced JawOpen weight for open-rest faces.
7. **Neck/collar.** The remaining visible neck is mostly the blouse collar sitting lower than in #30 (garment area, not changed).
8. **3/4 view landmarks.** In the 3/4 view the far eye and the chin are still ~15 px off. This was already so before (0.079 / 0.104).
   - **Why:** the reference front-left camera yaw is uncertain, not the face; the near-side landmarks agree within 0.02-0.03.
   - **Proposal:** the T-032 camera trial (`--reference-index`) to fit the yaw.

**Generality:** synthetic face B uses the same options with other values. It has a longer, softer oval lower face (roundness 2.7), its own mouth mix, bleed and blush, and green tilted eyes. Its sheet shows a clearly different face from the same code.

## Budget

- Five iteration renders, i1-i5. Each iteration was one build plus fidelity front/3-4 plus two 512 px close-ups:
  - i1: shape, smile, blush, eyes;
  - i2: front fill, bleed, eye/mouth/chin placement;
  - i3: bleed tint, bigger eye, blush;
  - i4: face-weighted bleed;
  - i5: final values, eye back to 42 mm.
- One low-resolution lighting diagnostic (160 px: hair/glasses/shadows toggled) before i1.
- Final: the expression sheets (girl, synthetic), the synthetic build, and the face-test renders. Spec values are unchanged after i5.
- Blender 5.3 came from the `bpy==5.3.*` wheel in a Python 3.13 venv with a `blender` wrapper.
