# Reach measurements: bake.json

bake `<t134 run>/e1c/bake.json`, frames 1–192, 24 fps, 7 wrist moves (chord ≥ 60 mm).

| char | side | frames | kind | chord mm | dev mm (ratio) | arc | peak m/s @ | ease in/out | acc/dec mm/f² | stall / dec2 | onset/stop step | lead sh/sh-shift/torso/hip/hip-shift | overlap pk torso/neck/head/hair | settle torso/neck/head/hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 21–73 | extend | 251 | 90 (0.36) | 1.94 | 0.71 @ 0.88 | 0.81/0.08 | 6.1/9.3 | 0.21 / 17.6 | 0.17/0.11 | –/-36/-25/–/– | -3/-16/-8/-19 | +31/+0/+0/+15 |
| boy | R | 81–97 | extend | 130 | 16 (0.12) | 1.04 | 0.29 @ 0.53 | 0.12/0.12 | 2.9/3.0 | 0.00 / 5.3 | 0.13/0.13 | –/–/–/–/– | -8/+38/–/+38 | +7/+32/+0/+36 |
| boy | R | 100–110 | retract | 74 | 9 (0.12) | 1.04 | 0.26 @ 0.45 | 0.10/0.10 | 3.7/3.8 | 0.00 / 6.4 | 0.21/0.21 | –/+21/–/–/– | -4/+23/–/+23 | +36/+36/+0/+36 |
| boy | R | 137–161 | retract | 207 | 51 (0.25) | 1.33 | 0.53 @ 0.40 | 0.12/0.42 | 5.2/6.9 | 0.23 / 12.3 | 0.14/0.21 | –/–/-6/–/– | +45/+37/+21/+32 | +31/+23/+26/+31 |
| girl | L | 106–113 | extend | 145 | 40 (0.28) | 1.25 | 1.26 @ 0.36 | 0.14/0.43 | 22.1/19.1 | 0.00 / 29.6 | 0.28/0.12 | –/+3/+14/–/– | +40/+18/+40/+33 | +36/+29/+36/+36 |
| girl | R | 6–13 | extend | 247 | 78 (0.31) | 1.26 | 1.69 @ 0.50 | 0.14/0.14 | 24.2/22.1 | 0.00 / 40.3 | 0.23/0.28 | –/+4/+4/–/– | –/+24/–/+24 | +0/+22/+0/+32 |
| girl | R | 34–47 | retract | 244 | 74 (0.30) | 1.23 | 0.99 @ 0.50 | 0.23/0.23 | 8.1/8.7 | 0.00 / 16.7 | 0.12/0.14 | –/–/–/–/– | +26/-7/–/+20 | +23/+14/+0/+30 |

Summary (medians): moves 7, extend 4, velocity.stall 0.00, velocity.dec2 16.65, path.max_dev_mm 51.31, path.dev_ratio 0.28, path.arc_ratio 1.25, velocity.frames 13.00, velocity.peak_m_s 0.71, velocity.peak_at 0.50, velocity.ease_in 0.14, velocity.ease_out 0.14, velocity.peak_acc 6.08, velocity.peak_dec 8.71, velocity.onset_step 0.17, velocity.stop_step 0.14, lead.shoulder.median –, lead.shoulder.share_leading 0.00, lead.shoulder_shift.median 3.50, lead.shoulder_shift.share_leading 0.43, lead.torso.median -1.00, lead.torso.share_leading 0.29, lead.hip.median –, lead.hip.share_leading 0.00, lead.hip_shift.median –, lead.hip_shift.share_leading 0.00, overlap.torso.peak_offset 11.50, overlap.torso.settle 31.00, overlap.neck.peak_offset 23.00, overlap.neck.settle 23.00, overlap.head.peak_offset 21.00, overlap.head.settle 0.00, overlap.hair.peak_offset 24.00, overlap.hair.settle 32.00

## Against baseline `<t134 run>/s010/bake.json`

| char | side | start | base start | Δ velocity.stall | Δ velocity.dec2 | Δ path.max_dev_mm | Δ path.dev_ratio | Δ path.arc_ratio | Δ velocity.frames | Δ velocity.peak_m_s | Δ velocity.peak_at | Δ velocity.ease_in | Δ velocity.ease_out | Δ velocity.peak_acc | Δ velocity.peak_dec | Δ velocity.onset_step | Δ velocity.stop_step | Δ lead.shoulder | Δ lead.shoulder_shift | Δ lead.torso | Δ lead.hip | Δ lead.hip_shift | Δ settle.torso | Δ settle.neck | Δ settle.head | Δ settle.hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 21 | 21 | -0.03 | -1.82 | 11.11 | 0.04 | -0.20 | -3 | -0.01 | 0.07 | 0.06 | -0.05 | -0.18 | -2.41 | 0.00 | -0.01 | – | -55 | -44 | – | – | +3 | +0 | +0 | +15 |
| boy | R | 81 | 81 | 0.00 | 0.38 | 15.63 | 0.12 | 0.04 | +0 | 0.00 | 0.06 | 0.00 | 0.00 | 0.25 | 0.28 | 0.01 | 0.01 | – | – | – | – | – | +0 | +0 | +0 | +0 |
| boy | R | 100 | 100 | 0.00 | 0.19 | 8.81 | 0.12 | 0.04 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.21 | 0.25 | 0.02 | 0.02 | – | +13 | – | – | – | +0 | +0 | +0 | +0 |
| boy | R | 137 | 137 | 0.01 | 0.07 | 0.03 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.13 | 0.14 | 0.00 | -0.00 | – | – | +0 | – | – | +0 | +0 | +0 | +0 |
| girl | L | 106 | 105 | -0.11 | -10.54 | -11.38 | -0.07 | -0.13 | -2 | 0.01 | -0.03 | -0.08 | -0.13 | -4.47 | -11.89 | 0.17 | -0.01 | – | – | – | – | – | +0 | +1 | +0 | +0 |
| girl | R | 6 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | – | +0 | +0 | – | – | +0 | +0 | +0 | +0 |
| girl | R | 34 | 34 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | – | – | – | – | – | +0 | +0 | +0 | +0 |
