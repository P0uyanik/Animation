# M1: reference package for `girl_auburn_bun_glasses` (2026-11-14, complete)

The existing intake (commit `849b072`) was verified and reused (17 images, hashes, analysis). Only the missing items
were added.

| Item | File | Result |
| --- | --- | --- |
| Canonical id | folder `assets/characters/girl_auburn_bun_glasses/` (renamed from the intake folder) | decisions recorded in the index and spec |
| Camera-matchable views | `references/views/sheet30_*.png` + `_mask.png` | 6 views from #30, all 456 px tall (one consistent scale) |
| View extraction tool (**reusable**) | `pipeline/charsys/tools/extract_reference_views.py` | any sheet with figures on a uniform background: crops and silhouettes in the format of the existing harness and metrics; numpy and Pillow only |
| Reference index | `references/reference_index.json` | same schema as the boy's; yaw per view measured from the bun offset, not from the labels |
| Face landmarks | `references/landmarks.json` | eyes, ears, nose, mouth, chin, glasses rims (front view, ±2 px) |
| Measured proportions | `references/measurements.json` | see below |
| Colour targets | `references/color_targets.json` | 12 targets (#42 swatches, #41 garments, #39 accessories, #30 frame) |
| Spec skeleton | `spec/girl_auburn_bun_glasses.spec.json` | valid schema; data only (not buildable until M2) |

## Findings
- **Scale validated on the references (#31 line-up, same image):** her sole-to-bun-top height is 356 px; the boy's
  sole-to-hair-top is 351–353 px. Her bun top is level with his hair top (+1%), so her total height is 1.10 m.
  - The bun-to-head junction is at 0.118 of her height (#30 front 0.123, side 0.116, #31 0.118).
  - Her crown is therefore at 0.97 m, i.e. her body is "slightly shorter", now measured.
- **Eye line from the feet:** 0.706 (the boy: 0.707). The two characters share an eye height.
- **Face ratios (front):** eye spacing / ear width 0.365 (the boy: about 0.38–0.39). The glasses rim radius is
  0.156 × the ear width.
- **Reference flaw:** #30 "Left" and "Right" are near-duplicates (mask IoU 0.989), so no true profile of her right
  side exists. "Right" is kept for visual review only. Symmetry is assumed except for the fringe part and the flower
  placement, which the front and back views show.
- **Missing data** (recorded in the index): her right profile; a closed-mouth neutral in a full-body view; the top of
  the bun from above; boot soles from below.

## Proposed M2: generic body and rig fitting (awaiting your go-ahead)
**Scope**
1. **Joint fitting from data (G1).**
   - A new generic `fit_metarig_from_joints(meta, joints)`, with joints given in `spec.rig.joints` as fractions of
     the height and half-width.
   - The boy keeps the existing `fit_metarig` path when his spec has no `rig.joints`, so his build stays
     byte-for-byte on the v6 path.
2. **Generic body generator** (`body_generic/1`, new module).
   - Parts: head with neck, torso, arms, five-finger hands with three joints per finger, legs.
   - All dimensions come from `spec.proportions` and `spec.body`.
   - Garments are not part of M2; M5 wraps garments around this body.
3. **Component map and weight rules from the spec.**
   - `spec.components` and `spec.rig.weight_rules`, defined per component, not per object name.
   - The boy's current tables become his defaults.
4. **The girl's M2 build:** her body from measured fractions (masks and landmarks), rigged with the unchanged Rigify
   profile.
   - Exported with `export_engine.py`.
   - Tested with the existing engine behaviour tests (reach, look-at, expressions, blink, grasp, walk, idle).

**Reusable improvements**
- Any humanoid proportions can be built and rigged from data.
- The rig builder no longer depends on the boy's height table.
- Component and weight rules become configuration.

**Validation criteria**
| Check | Criterion |
| --- | --- |
| Boy unchanged | `verify_charsys` PASS: build equals v6 geometry, store and reuse tests pass on 1.0.0. `ctest` unchanged |
| Girl proportions | Built crown height 0.97 m ±2%; eye line 0.706 ±0.01; head width and limb lengths within ±5% of the masks (body only, so no silhouette IoU until hair and clothes exist) |
| Girl rig | 0 unweighted vertices; elbow, knee, shoulder and finger deformation renders without tearing; reopen and reuse tests on a temporary store |
| Engine | Girl package exports through `humanoid_rigify`; the behaviour test table runs on three packages (boy, fixture, girl) with no engine change |
| Generic test | `body_generic/1` builds and rigs a synthetic proportions configuration (test only) |

**Not in M2:** face detail (M3), hair (M4), garments and materials (M5).

Status: nothing built; no asset published; the boy's assets untouched.
