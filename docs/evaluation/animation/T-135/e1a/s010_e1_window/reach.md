# Reach measurements: bake.json

bake `<t134 run>/s010_e1/bake.json`, frames 1–192, 24 fps, 2 wrist moves (chord ≥ 60 mm).

| char | side | frames | kind | chord mm | dev mm (ratio) | arc | peak m/s @ | ease in/out | acc/dec mm/f² | stall / dec2 | onset/stop step | lead sh/sh-shift/torso/hip/hip-shift | overlap pk torso/neck/head/hair | settle torso/neck/head/hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 57–76 | extend | 137 | 54 (0.39) | 1.86 | 0.85 @ 0.50 | 0.32/0.42 | 7.6/12.7 | 0.03 / 18.7 | 0.21/0.07 | –/+0/+11/–/– | -4/-6/-9/-5 | +28/+0/+0/+0 |
| girl | L | 104–114 | extend | 141 | 55 (0.39) | 1.51 | 1.44 @ 0.45 | 0.30/0.40 | 25.2/24.7 | 0.01 / 33.8 | 0.07/0.06 | –/+7/–/–/– | +40/+18/+41/+19 | +36/+28/+36/+36 |

Summary (medians): moves 2, extend 2, velocity.stall 0.02, velocity.dec2 26.25, path.max_dev_mm 54.72, path.dev_ratio 0.39, path.arc_ratio 1.68, velocity.frames 14.50, velocity.peak_m_s 1.14, velocity.peak_at 0.47, velocity.ease_in 0.31, velocity.ease_out 0.41, velocity.peak_acc 16.39, velocity.peak_dec 18.69, velocity.onset_step 0.14, velocity.stop_step 0.07, lead.shoulder.median –, lead.shoulder.share_leading 0.00, lead.shoulder_shift.median 3.50, lead.shoulder_shift.share_leading 0.50, lead.torso.median 11.00, lead.torso.share_leading 0.50, lead.hip.median –, lead.hip.share_leading 0.00, lead.hip_shift.median –, lead.hip_shift.share_leading 0.00, overlap.torso.peak_offset 18.00, overlap.torso.settle 32.00, overlap.neck.peak_offset 6.00, overlap.neck.settle 14.00, overlap.head.peak_offset 16.00, overlap.head.settle 18.00, overlap.hair.peak_offset 7.00, overlap.hair.settle 18.00

## Against baseline `<t134 run>/s010/bake.json`

| char | side | start | base start | Δ velocity.stall | Δ velocity.dec2 | Δ path.max_dev_mm | Δ path.dev_ratio | Δ path.arc_ratio | Δ velocity.frames | Δ velocity.peak_m_s | Δ velocity.peak_at | Δ velocity.ease_in | Δ velocity.ease_out | Δ velocity.peak_acc | Δ velocity.peak_dec | Δ velocity.onset_step | Δ velocity.stop_step | Δ lead.shoulder | Δ lead.shoulder_shift | Δ lead.torso | Δ lead.hip | Δ lead.hip_shift | Δ settle.torso | Δ settle.neck | Δ settle.head | Δ settle.hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 57 | 57 | -0.21 | -0.69 | 8.71 | 0.08 | 0.05 | +0 | 0.12 | 0.05 | 0.05 | 0.05 | 0.47 | 0.93 | -0.02 | -0.05 | – | – | – | – | – | +0 | +0 | +0 | +0 |
| girl | L | 104 | 104 | -0.10 | -6.40 | 3.58 | 0.04 | 0.10 | +0 | 0.18 | 0.00 | 0.00 | -0.10 | -1.32 | -6.28 | 0.00 | -0.07 | – | – | – | – | – | +0 | +0 | +0 | +0 |
