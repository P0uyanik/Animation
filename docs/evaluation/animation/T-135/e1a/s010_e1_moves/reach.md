# Reach measurements: bake.json

bake `<t134 run>/s010_e1/bake.json`, frames 1–192, 24 fps, 7 wrist moves (chord ≥ 60 mm).

| char | side | frames | kind | chord mm | dev mm (ratio) | arc | peak m/s @ | ease in/out | acc/dec mm/f² | stall / dec2 | onset/stop step | lead sh/sh-shift/torso/hip/hip-shift | overlap pk torso/neck/head/hair | settle torso/neck/head/hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 52–73 | extend | 133 | 69 (0.52) | 2.11 | 0.85 @ 0.69 | 0.52/0.24 | 7.4/12.7 | 0.03 / 18.7 | 0.16/0.13 | –/-5/+6/–/– | -4/-6/-9/-5 | +31/+0/+0/+0 |
| boy | R | 81–97 | extend | 130 | 0 (0.00) | 1.00 | 0.29 @ 0.53 | 0.12/0.12 | 2.7/2.7 | 0.00 / 5.0 | 0.12/0.12 | –/–/–/–/– | +11/+38/–/+38 | +7/+32/+0/+36 |
| boy | R | 100–110 | retract | 73 | 0 (0.00) | 1.00 | 0.26 @ 0.45 | 0.10/0.10 | 3.6/3.6 | 0.00 / 6.2 | 0.19/0.18 | –/+22/+8/–/– | -4/+23/–/+23 | +36/+36/+0/+36 |
| boy | R | 137–161 | retract | 207 | 51 (0.25) | 1.33 | 0.54 @ 0.40 | 0.12/0.42 | 4.8/6.7 | 0.22 / 12.2 | 0.14/0.21 | –/–/-6/–/– | +45/+37/+21/+32 | +31/+23/+26/+31 |
| girl | L | 63–114 | extend | 133 | 51 (0.38) | 1.93 | 1.44 @ 0.89 | 0.86/0.08 | 25.2/24.7 | 0.04 / 33.8 | 0.03/0.06 | –/-34/-2/+6/– | -42/+18/+41/+19 | +36/+28/+36/+36 |
| girl | R | 6–13 | extend | 247 | 78 (0.31) | 1.26 | 1.69 @ 0.50 | 0.14/0.14 | 24.2/22.1 | 0.00 / 40.3 | 0.23/0.28 | –/+4/+4/–/– | –/+24/–/+24 | +0/+22/+0/+32 |
| girl | R | 34–47 | retract | 244 | 74 (0.30) | 1.23 | 0.99 @ 0.50 | 0.23/0.23 | 8.1/8.7 | 0.00 / 16.7 | 0.12/0.14 | –/–/–/–/– | +26/-7/–/+20 | +23/+14/+0/+30 |

Summary (medians): moves 7, extend 4, velocity.stall 0.00, velocity.dec2 16.65, path.max_dev_mm 51.36, path.dev_ratio 0.30, path.arc_ratio 1.26, velocity.frames 16.00, velocity.peak_m_s 0.85, velocity.peak_at 0.50, velocity.ease_in 0.14, velocity.ease_out 0.14, velocity.peak_acc 7.39, velocity.peak_dec 8.71, velocity.onset_step 0.14, velocity.stop_step 0.14, lead.shoulder.median –, lead.shoulder.share_leading 0.00, lead.shoulder_shift.median -0.50, lead.shoulder_shift.share_leading 0.29, lead.torso.median 4.00, lead.torso.share_leading 0.43, lead.hip.median 6.00, lead.hip.share_leading 0.14, lead.hip_shift.median –, lead.hip_shift.share_leading 0.00, overlap.torso.peak_offset 3.50, overlap.torso.settle 31.00, overlap.neck.peak_offset 23.00, overlap.neck.settle 23.00, overlap.head.peak_offset 21.00, overlap.head.settle 0.00, overlap.hair.peak_offset 23.00, overlap.hair.settle 32.00

## Against baseline `<t134 run>/s010/bake.json`

| char | side | start | base start | Δ velocity.stall | Δ velocity.dec2 | Δ path.max_dev_mm | Δ path.dev_ratio | Δ path.arc_ratio | Δ velocity.frames | Δ velocity.peak_m_s | Δ velocity.peak_at | Δ velocity.ease_in | Δ velocity.ease_out | Δ velocity.peak_acc | Δ velocity.peak_dec | Δ velocity.onset_step | Δ velocity.stop_step | Δ lead.shoulder | Δ lead.shoulder_shift | Δ lead.torso | Δ lead.hip | Δ lead.hip_shift | Δ settle.torso | Δ settle.neck | Δ settle.head | Δ settle.hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 81 | 81 | 0.00 | 0.06 | 0.04 | 0.00 | 0.00 | +0 | 0.00 | 0.06 | 0.00 | 0.00 | -0.00 | -0.00 | -0.00 | -0.00 | – | – | – | – | – | +0 | +0 | +0 | +0 |
| boy | R | 100 | 100 | 0.00 | -0.00 | 0.03 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 | 0.10 | -0.00 | -0.01 | – | +14 | +0 | – | – | +0 | +0 | +0 | +0 |
| boy | R | 137 | 137 | -0.01 | -0.08 | 0.08 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | -0.18 | -0.08 | -0.00 | -0.00 | – | – | +0 | – | – | +0 | +0 | +0 | +0 |
| girl | R | 6 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | – | +0 | +0 | – | – | +0 | +0 | +0 | +0 |
| girl | R | 34 | 34 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | – | – | – | – | – | +0 | +0 | +0 | +0 |
