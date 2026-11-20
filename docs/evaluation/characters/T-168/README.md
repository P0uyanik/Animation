# T-168: boy face contour (side/3/4 bulge) and nose

Candidate only (opt-in): nothing current changes. Input main 3c698c7; branch from integration/t-141 2a02532 + merge of
origin/t-155-claude-candidates-r2 (boy 2.3.0 spec, current on that branch). Blender: bpy 5.3.0 (`blender` wrapper).

## 1. Cause of the bulge
Method: 2.3.0 master plus four ablation builds (one `face.shape` option off each, `diagnosis/ov_*.json`); bald head on
Workbench at yaw -35 / -60 / -90 (`diagnosis/diag.py`); silhouette extent of the head skin per 1 cm slice
(`diagnosis/sections_*.json`, metres).

| contour, far side (m) | yaw -35: z .76 -> .75 | yaw -60: z .76 -> .75 | side: forward at z .74 |
|---|---|---|---|
| 2.3.0 | 0.1543 -> 0.1585 | 0.1541 -> 0.1655 | 0.1454 |
| cheek_pad_m = 0 | 0.1542 -> 0.1516 | 0.1502 -> 0.1512 | 0.1422 |
| cheek_fullness_m = 0 | 0.1544 -> 0.1578 | 0.1521 -> 0.1605 | 0.1422 |
| jaw_round_m = 0 | 0.1543 -> 0.1583 | 0.1538 -> 0.1652 | 0.1445 |
| outline_roundness = 0 | 0.1540 -> 0.1570 | 0.1524 -> 0.1642 | 0.1445 |
| **T-168 candidate** | 0.1542 -> 0.1519 | 0.1503 -> 0.1522 | 0.1435 |

- **3/4 bulge = `face.shape.lower_face.cheek_pad`**: 16 mm radial, centre at 1.3 x eye x, cut off 15 mm under the eye
  with a fixed 15 mm fade. It made an 11 mm step in the contour within 1 cm of height at yaw -60 (4 mm at -35), a ledge
  under the eye. `cheek_fullness_m` added about 5 mm on top; jaw_round and outline_roundness do not matter.
- **Side view**: the lower face stayed as far forward as the eye line down to z 0.73 and then cut under to the chin
  (the head's fitted side profile only starts receding below mid-face). The references recede from below the nose.
- Images: `diagnosis/ablation_yaw-35_-60_-90.jpg` (columns: 2.3.0, no pad, no jaw, no cheek fullness, no outline
  roundness), `diagnosis/boy_2.3.0_bald_head.jpg`, `diagnosis/refs_head.jpg`.

## 2. Change
Generator (opt-in, defaults unchanged):
- `pipeline/charsys/face_v3/lower_face.py`: `cheek_pad_top_fade_m` (default 0.015 = the previous constant).
- `pipeline/charsys/face_features.py` `build_nose` only: nose type `upturned` (tip with a soft bridge above and a short
  underside; `size_m, height_m, bridge_m, under_m, tip_up_m, bridge_narrow, tip_power`).
- `pipeline/charsys/tests/test_face_t168.py` (new), registered in `tools/check_all.py` (approved ~15:30 CET).

Candidate data `boy_yellow_hoodie.T-168.override.json` (on the 2.3.0 spec), r2 after the owner review ~15:30 CET:
- cheek pad 16 -> 10 mm, radius 70 -> 60 mm, centre 35 -> 45 mm below the eye, top fade 15 -> 45 mm;
  cheek_fullness 6 -> 4 mm; `lower_face_recede_m` 3 mm from 30 mm below the eye (r1: 8 mm from 25 mm; existing
  face.shape option, data only; the head profile rows did not need to change).
- nose `small_round` 9 / 1.6 mm -> `upturned` as a soft nub: 10 mm half width, 3.5 mm high, round dome
  (r1: 13 / 5.5 mm, read as a cone at 3/4).

r3 (owner ~17:05 CET, option 2): `body.params.head.outline.side` below mid-face set further back in the override
(t .37/.44/.51/.57/.60: 0.013/-0.027/-0.08/-0.16/-0.27 -> -0.015/-0.09/-0.20/-0.33/-0.46 eye-spacing units; side
profile at z 0.70: 0.117 -> about 0.100 m forward, 0.71: 0.130 -> 0.120); nose height 3.5 -> 2.5 mm.

r4 (owner ~18:20 CET, "the face form has to be softer"), override data only:
- `head.outline.front` (chin outline, half widths in eye-spacing units at t .23/.37/.47/.54/.585):
  0.93/0.86/0.76/0.65/0.30 -> 0.94/0.83/0.70/0.52/0.35 (an ellipse: narrower, rounder chin; front half width at
  z 0.70/0.71/0.72: 0.081/0.113/0.127 -> 0.073/0.100/0.117 m).
- `head.profile_levels` rows 2-4 (jaw underside) narrower and shallower so the head closes more gradually to the chin.
- `head.outline.side` chin set-back moderate (between 2.3.0 and r3): -0.06/-0.14/-0.25/-0.38 at t .44/.51/.57/.60.
- face.shape: `outline_exponent` 2.4 -> 2.0 (no squared outline), `jaw_round_m` 6 -> 3 mm with `jaw_down` 0.5.

## 3. Evidence (r4)
- 100 % close-ups, ref | 2.3.0 | candidate, front / 3/4 / side: `boy_closeups_2.3.0_vs_T-168.jpg` (Cycles 16 spp,
  480 px renders pasted unscaled; reference enlarged from a 210-240 px source).
- Skin-only clay (Workbench, hair and clothes hidden), 2.3.0 vs candidate: `boy_clay_2.3.0_vs_T-168.jpg`.
- Strict sheet: `boy_2.3.0_vs_T-168_strict.jpg` (recipe `boy_2.3.0_vs_T-168.recipe.json`, preview passed).
- Reading: clay: 2.3.0 has a ledge under the eyes, a step at the jaw and a shelf in profile; the candidate is one
  smooth rounded form from cheek to chin. Cycles: front jaw line is a round U, narrower at the chin; 3/4 has no ledge;
  side runs from a small nose tip round into the chin. Nose barely visible from the front.
- Remaining differences to val27: little chin shows below the mouth from the front (the chin tucks under); the head
  is still deeper front to back and the jaw underside flatter than the reference; ears are 2.3.0 defaults (T-159).
- The table in section 1 was measured on the r1 shape.

## 4. Tests
- `test_face_t168.py --blender blender`: 11/11. After merging origin/t-159-claude-ears (3c306ea): test_ears_shape 8/8,
  test_face_front_fade 14/14, test_face_r5 15/15, test_guard_allowlist 25/25, blender_inventory + T-127 shard tests pass.
- Merge does not change the candidate: r2 candidate built before and after the T-159 merge, `mesh_hash_strict.py`:
  223/223 objects identical.
- Default unchanged: 2.3.0 rebuilt with the edited code vs a build from the unedited T-155 branch: 222 of 223 objects
  identical (head/body_skin included); `lid_upper.R` differs = the known run-to-run lid drift of the T-155 branch
  build (no deterministic-build fix there), not confirmed by a same-code rebuild.
- test_face_v4 15/17: the two failures ("candidate is on the current version", 2.2.0 vs 2.3.0) are already there at
  the T-155 merge commit 7fdc278, before any T-168 edit.

## 5. Not done / limits
- Fidelity score, full ctest and CI not run. No golden, threshold or test loosened.
- r3 sheet and close-ups are rendered after the T-159 merge; the 2.3.0 close-up column is the r2 run (same job settings).
- Not touched: shape_face_v2, build_ears and the ears (T-159), face_v3/lids.py (T-156).
