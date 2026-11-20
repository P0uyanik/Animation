# T-168: boy face contour (side/3/4 bulge) and nose

Status: **diagnosis only, on HOLD** (owner hold 2026-11-20 ~10:05 CET). No generator code or spec changed. Input main 3c698c7;
branch from integration/t-141 2a02532; boy built from the T-155 2.3.0 candidate spec (origin/t-155-claude-candidates-r2 b0d4f8f).

## Cause of the bulge (criterion 1)
Method: 2.3.0 master plus four ablation builds (one `face.shape` option off each, `diagnosis/ov_*.json`); bald head on
Workbench at yaw -35 / -60 / -90 (`diagnosis/diag.py`); silhouette extent of the head skin per 1 cm slice
(`diagnosis/sections_*.json`, metres, screen-x at each yaw).

| contour, far side (m) | yaw -35: z .76 -> .75 | yaw -60: z .76 -> .75 | side: forward at z .74 |
|---|---|---|---|
| 2.3.0 | 0.1543 -> 0.1585 | 0.1541 -> 0.1655 | 0.1454 |
| cheek_pad_m = 0 | 0.1542 -> 0.1516 | 0.1502 -> 0.1512 | 0.1422 |
| cheek_fullness_m = 0 | 0.1544 -> 0.1578 | 0.1521 -> 0.1605 | 0.1422 |
| jaw_round_m = 0 | 0.1543 -> 0.1583 | 0.1538 -> 0.1652 | 0.1445 |
| outline_roundness = 0 | 0.1540 -> 0.1570 | 0.1524 -> 0.1642 | 0.1445 |

- **3/4 bulge = `face.shape.lower_face.cheek_pad`** (16 mm radial, centre at 1.3 x eye x, cut off 15 mm under the eye with
  a fixed 15 mm fade in `face_v3/lower_face.py`): an 11 mm step in the contour within 1 cm of height at yaw -60, 4 mm at
  -35. Pad off: smooth. `cheek_fullness_m` adds about 5 mm on top; jaw_round and outline_roundness do not matter.
- **Side view**: a flat, forward lower face (as far forward as the eye line down to z 0.73) with an abrupt chin undercut
  remains with the pad off. It comes from the head data `body.params.head` (`profile_levels` / `outline.side`), not from
  the face generator. The references (val27_side_right, canon29_side_left) recede below the nose to a soft round chin.
- Nose: `small_round` 9 mm / 1.6 mm high is nearly invisible in profile; the references show a small upturned tip.

Images: `diagnosis/ablation_yaw-35_-60_-90.jpg` (columns: 2.3.0, no pad, no jaw, no cheek fullness, no outline
roundness; rows: yaw -35, -60, -90), `diagnosis/boy_2.3.0_bald_head.jpg`, `diagnosis/refs_head.jpg`.

## Plan if released (Supervisor answers 2026-11-20 ~09:06Z)
- Merge origin/t-155-claude-candidates-r2; candidate = T-168 override on the 2.3.0 spec (opt-in, nothing current changes).
- Generator edits, opt-in, default byte-identical: `pipeline/charsys/face_v3/lower_face.py` (pad top fade / falloff),
  `pipeline/charsys/face_features.py` `build_nose` (new nose type), `spec.py` only if nose types are validated there, one test.
- Spec data in the override: smaller/softer cheek pad, lower-head profile rows (chin / lower-face side profile), nose.

## Not done
Criteria 2-3 (nose, strict sheet), tests. Blender 5.3.0 (/usr/local/bin/blender). Previews are Workbench, not approval evidence.
