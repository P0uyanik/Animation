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
- `pipeline/charsys/face_features.py` `build_nose`: nose type `upturned` (tip with a soft bridge above and a short
  underside; `size_m, height_m, bridge_m, under_m, tip_up_m, bridge_narrow, tip_power`).
- `pipeline/charsys/tests/test_face_t168.py` (new; **not registered** in tools/check_all.py, outside my write-set).

Candidate data `boy_yellow_hoodie.T-168.override.json` (on the 2.3.0 spec):
- cheek pad 16 -> 10 mm, radius 70 -> 60 mm, centre 35 -> 45 mm below the eye, top fade 15 -> 45 mm;
  cheek_fullness 6 -> 4 mm; `lower_face_recede_m` 8 mm from 25 mm below the eye (existing face.shape option; the
  head profile rows did not need to change).
- nose `small_round` 9 / 1.6 mm -> `upturned` 13 mm half width, 5.5 mm high.

## 3. Evidence
- Strict sheet: `boy_2.3.0_vs_T-168_strict.jpg` (recipe `boy_2.3.0_vs_T-168.recipe.json`, preview passed, Cycles 16 spp).
- Side / oblique / 3/4 close-ups, same rig and settings: `boy_closeups_2.3.0_vs_T-168.jpg`
  (rows: 3/4 -35, oblique -60, side -90; columns: reference, 2.3.0, T-168).
- Front: face layout, eyes, mouth, hair unchanged; cheeks slightly slimmer low down; the nose is now visible.

## 4. Tests
- `python3 pipeline/charsys/tests/test_face_t168.py --blender blender`: 11/11.
- Default unchanged: 2.3.0 rebuilt with the edited code vs a build from the unedited T-155 branch,
  `mesh_hash_strict.py`: 222 of 223 objects identical (head/body_skin included); `lid_upper.R` differs, which is the
  known run-to-run lid drift (T-158; the T-155 branch build does not have the deterministic-build fix), not this code
  (the new branches are not reached without the new keys).
- test_face_r5 9/9, test_guard_allowlist 25/25. test_face_v4 15/17: the two failures ("candidate is on the current
  version", 2.2.0 vs 2.3.0) are already there at the merge commit 7fdc278, before any T-168 edit.

## 5. Not done / limits
- Fidelity score, full ctest and CI not run. No golden, threshold or test loosened.
- Nose shape is a first candidate (tip a little pointed from the front); it is spec data and easy to tune.
- Eyes/lids (T-156) and head/ears/temple (T-159) untouched.
- Close-ups, honest reading: the ledge under the eye is gone at -35 and -60 and the side shelf is gone; in the side
  view the lower face now recedes a little more than val27_side_right (the reference keeps a rounder mouth/cheek
  line just behind the nose tip) and the nose tip is sharper than the reference's soft nub. Both are override values.
