# T-031: face system v2 (shared, spec-driven) and the girl's face at reference quality

Branch `t-031-claude-face-v2` (from origin/main). Girl spec **0.8.0, unpublished**: only `face` and the `metadata` version line changed. Nothing was published or approved. The owner gives the final visual approval.

## What was built (shared, character-independent)

New module `pipeline/charsys/face_features.py`, wired into `face_generic.py`. Every option is spec data under `spec.face`. When an option is absent, the face_generic/1 behaviour is unchanged, so older specs (girl 0.7.1, the M3 fixtures) build as before. The boy never uses this path; he stays on the legacy face.

| area | spec options |
|---|---|
| Eyes | `eyes.shader: "layered/1"`: iris inner/mid/outer colours, `limbal_srgb`/`limbal_width`, `vertical_gradient` (lighter lower iris, darker under the lid), radial `streaks`, soft-edged pupil, 1–2 emissive `highlights` (catchlights) with `catchlight_strength`/`softness`, `wet_coat` (clear coat weight/roughness), `sclera_edge_srgb`. Size `radius_m`, `spacing_m`, `offset_z_m`, tilt `roll_deg`. |
| Lids and lashes | `lids.upper_curve`/`lower_curve` (edge curvature; the shell rotates about the eye centre, so it never cuts the eyeball), thickness as before. `lash.strands` / `lash.lower_strands`: count, length (list from inner to outer), curl, span, width, outward lean, forward. |
| Brows | `brows.style: felt | embroidered` (shared `felt` preset; embroidered adds stitch relief). Shape (inner/outer/height/arch/drops/taper), thickness, depth, colour. |
| Nose | `nose.type: bump | small_round | button | minimal_line`, `size_m`, `offset_z_m` (button and line are separate objects named `nose`, rigid on the head bone; a spec using them lists `nose` under `components.face`). |
| Mouth | `mouth.rest_shape: closed_smile | open_smile | small_o` (baked into the basis; every action unit still works on top). Width and position as before (`half_width_m`, `layout.mouth_below_eye_m`). |
| Cheeks | `blush.intensity`, `softness`, `breakup` (felt patch edge), `nose_intensity`, `nose_radius_m`; `shape.cheek_roundness_m` (fullness). |
| Face skin | `skin.occlusion` {`distance_m`, `lift`, `warm_srgb`}: felt-skin occlusion compensation. The blush graph is also carried into the preset's rim layer. |
| Head shape | `shape.cheek_roundness_m`, `chin_forward_m`, `chin_drop_m`, `forehead_height_m`, `forehead_fullness_m` (+ radii/positions), sculpted before the features are placed. |
| Expressions | Library optional presets `SmileClosed` and `Thinking` (opt-in per spec). |

Tools and tests: `pipeline/charsys/tests/face_expression_sheet.py` (any master, chosen presets), and the fixture `pipeline/charsys/tests/fixtures/face_synthetic_b.override.json`. `face_test.py` now disables garment MASK modifiers on the head the same way `face_system_test.py` already did. Without that it crashed on the 0.7.1 girl too: the edge index was out of range.

## Evidence

- `girl_face_front_vs_reference.png`, `girl_face_34_vs_reference.png`: 512 px close-ups (final build) next to the reference face crop (#30 neutral tile; #30 front-left, upscaled from the sheet).
- `girl_face_before_after_front.png`, `girl_face_before_after_34.png`: 0.7.1 → 0.8.0 → reference. The 0.7.1 3/4 shot was rendered at yaw −35°, the 0.8.0 one at −45° (the sheet's front-left).
- `girl_expressions_sheet.png`: neutral, closed smile, open smile, surprised, sad, thinking. `face_system_test_all_presets.png`: every preset from the face test.
- `synthetic_face_b.png`, `synthetic_expressions_sheet.png`, `girl_vs_synthetic_same_system.png`: the second face.
- `fidelity_face_before_after.json`, `fidelity_before/after_sheet30_front.png`: fidelity tool (origin/t-032-claude-fidelity, run read-only from a scratch worktree, views sheet30_front and sheet30_front_left).
- `face_system_test_summary.json`, `face_test_summary.json`.

## Fidelity before (0.7.1) → after (0.8.0)

Face landmark error (head heights, lower is better):

| landmark | front before | front after | 3/4 before | 3/4 after |
|---|---|---|---|---|
| brow_inner_L | hidden | 0.023 | 0.063 | 0.018 |
| brow_outer_L | hidden | 0.021 | hidden | 0.014 |
| eye_L / eye_R | 0.030 / 0.031 | 0.030 / 0.031 | 0.011 / 0.081 | 0.010 / 0.079 |
| eye_inner_L / R | 0.037 / 0.032 | 0.029 / 0.024 | 0.033 / 0.011 | 0.040 / 0.014 |
| eye_outer_L / R | 0.023 / 0.007 | 0.010 / 0.006 | 0.051 / 0.062 | 0.057 / 0.040 |
| mouth corners L / R | 0.026 / 0.016 | 0.021 / 0.012 | 0.073 / 0.033 | 0.070 / 0.035 |
| nose / mouth / chin | 0.024 / 0.022 / 0.021 | 0.024 / 0.022 / 0.021 | 0.030 / 0.050 / 0.104 | 0.029 / 0.050 / 0.104 |
| **mean of the visible ones** | **0.0245** | **0.0211** | **0.0501** | **0.0432** |

The brows were hidden in the render (under the fringe) and are now visible in both views.

Colour (ΔE00 vs reference; luma-matched ΔE00; ΔL*):

| region | front before | front after | 3/4 before | 3/4 after |
|---|---|---|---|---|
| skin_face | 19.1 (5.3; −20.9 L*) | 14.9 (3.2; −17.1 L*) | 19.8 (4.2; −22.6 L*) | 15.6 (2.5; −18.5 L*) |
| skin_limbs | 9.5 (2.2; −11.4 L*) | 3.7 (0.6; −4.6 L*) | 13.2 (2.4; −14.9 L*) | 7.9 (0.2; −9.5 L*) |

Overall score (two views) 66.1 → 68.2; colour sub-score 54 → 61; landmark sub-score 82 → 83. The arms, hair and garment items in the ranking are outside this task.

## Face tests (final girl build)

- face_system_test: 0 eyeball/lid and 0 glasses intersections in every preset, action unit and gaze pose (0.7.1: also 0). The first 0.8.0 draft had 20 lash/rim intersections per eye at the outer corner. The lash span was reduced so they stay inside the rim.
- Blink closes fully (0% eye visible) at rest and under every gaze pose.
- Eye visibility at rest is 69.9%, down from 76.1%. That is the share of the 0.8 r disc, on a larger eye with a thicker upper lid.
- The mouth, jaw and smile numbers are unchanged from 0.7.1. For example, the open smile shows 18% teeth and 13% tongue.
- face_test: runs. Blink 0%. `lid_proud_mm` is 4.9 (0.7.1: 4.0), from the thicker upper lid (2.4 mm). JawOpen and Smile are unchanged.
- The synthetic face passes face_system_test with 0 intersections and blinks fully closed. Its open-smile rest shows teeth, tongue and interior.

Other checks:

| check | result |
|---|---|
| test_material_presets | ALL PASS (54/54) |
| test_export_engine | ALL PASS (8/8) |
| verify_charsys | PASS: boy geometry equals v6 (worst 0.0 m); the store master is byte-identical after the tests |

Boy: a build on origin/main and a build on this branch give identical geometry fingerprints for all 55 objects. The boy GLB is not byte-stable even between two builds on the same branch. One float in `hair_mass` (6e-8 m) changes from run to run, already listed by verify_charsys as an informational exact-hash note. That noise is pre-existing and not related to this change, which never touches the boy's legacy path. The 1.0.0/1.1.0 store files, v6, tests/data, baselines and docs/references are untouched.

## Visual assessment

**Matches the reference now:**
- **Eyes:** large, glossy brown plush eyes. The iris is layered: amber centre, brown body, dark limbal ring, lighter lower half. The pupil is large and dark. There is a big catchlight upper screen-right and a small one lower-left, as in #30 and #34. The clear coat reads wet. The upper lash line is thick and dark with curled strands towards the outer corner, plus short lower lashes.
- **Brows:** thick, dark-brown felt brows in the reference position just above the rims. They were hidden before.
- **Nose:** small, round and pink.
- **Blush:** soft pink felt patches on the cheeks.
- **Skin:** the face reads warmer and less grey (hue now matches; luma-matched ΔE 3.2).
- **Expressions:** all six expressions read correctly.

**Still differs (for the owner to judge):**
1. **Face lightness:** the face is still about 17–19 L* darker than the reference.
   - The face and body share one material, so their tones match. But the face receives less light than the limbs (it sits under the fringe, side curls and glasses, and the shared key light comes from screen-left).
   - Normals were checked: none face inward. Muting the bump changed nothing, and SSS off changed nothing.
   - The face path's occlusion compensation recovers part of it. The rest is the shared render calibration/exposure (`render_calibration.json`), which is outside this task's file area. The fidelity tool also attributes it to lightness.
2. **Mouth:** the neutral stays the approved closed soft smile. The #30 neutral tile shows a small open smile; that is the `Smile` preset here.
3. **Eye openings:** they are a little less round than #30. The lower lid edge is flatter and the sclera shows less at the sides.
4. **Cheeks:** the reference's cheeks bulge more at 3/4. Cheek fullness is set conservatively (3 mm) because the head silhouette belongs to the body proportions.
5. **3/4 lens reflections:** in the 3/4 view the glasses lenses reflect over the eyes. The lens shader belongs to accessories.

**Generality:** synthetic face B uses the same options with other values. Every difference comes from the override file, with no code paths per character:
- smaller, wide-set, tilted green eyes with one catchlight and long curled lashes;
- thin straight embroidered brows;
- a button nose;
- an open-smile rest with a felt interior and tongue;
- coral blush, fuller cheeks, a longer forehead and chin;
- tan skin, no hair or glasses.

## Budget

- Iteration renders: four girl rounds (b1–b4: brows/blush/mouth, iris fix, two skin-occlusion strengths), plus one low-resolution diagnostic (hair/SSS/bump on/off).
- Final: girl b5, then b6 after the lash fix found by the face test (b6 is the build all evidence comes from), plus synthetic s1/s2.
- Blender 5.3 came from the `bpy==5.3.*` wheel in a Python 3.13 venv with a `blender` wrapper.
