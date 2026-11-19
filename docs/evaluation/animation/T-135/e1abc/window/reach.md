# Reach measurements: bake.json

bake `<t134 run>/e1c/bake.json`, frames 1–192, 24 fps, 2 wrist moves (chord ≥ 60 mm).

| char | side | frames | kind | chord mm | dev mm (ratio) | arc | peak m/s @ | ease in/out | acc/dec mm/f² | stall / dec2 | onset/stop step | lead sh/sh-shift/torso/hip/hip-shift | overlap pk torso/neck/head/hair | settle torso/neck/head/hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 57–76 | extend | 136 | 47 (0.34) | 1.61 | 0.71 @ 0.50 | 0.32/0.37 | 7.7/9.3 | 0.05 / 17.6 | 0.26/0.01 | –/+0/+11/–/– | -3/-6/-8/-5 | +28/+0/+0/+12 |
| girl | L | 104–114 | extend | 147 | 39 (0.26) | 1.31 | 1.26 @ 0.45 | 0.30/0.40 | 22.1/19.1 | 0.00 / 29.6 | 0.08/0.07 | –/+1/+12/–/– | +40/+18/+41/+33 | +36/+28/+36/+36 |

Summary (medians): moves 2, extend 2, velocity.stall 0.03, velocity.dec2 23.61, path.max_dev_mm 42.75, path.dev_ratio 0.30, path.arc_ratio 1.46, velocity.frames 14.50, velocity.peak_m_s 0.99, velocity.peak_at 0.47, velocity.ease_in 0.31, velocity.ease_out 0.38, velocity.peak_acc 14.87, velocity.peak_dec 14.22, velocity.onset_step 0.17, velocity.stop_step 0.04, lead.shoulder.median –, lead.shoulder.share_leading 0.00, lead.shoulder_shift.median 0.50, lead.shoulder_shift.share_leading 0.50, lead.torso.median 11.50, lead.torso.share_leading 1.00, lead.hip.median –, lead.hip.share_leading 0.00, lead.hip_shift.median –, lead.hip_shift.share_leading 0.00, overlap.torso.peak_offset 18.50, overlap.torso.settle 32.00, overlap.neck.peak_offset 6.00, overlap.neck.settle 14.00, overlap.head.peak_offset 16.50, overlap.head.settle 18.00, overlap.hair.peak_offset 14.00, overlap.hair.settle 24.00

## Against baseline `<t134 run>/s010/bake.json`

| char | side | start | base start | Δ velocity.stall | Δ velocity.dec2 | Δ path.max_dev_mm | Δ path.dev_ratio | Δ path.arc_ratio | Δ velocity.frames | Δ velocity.peak_m_s | Δ velocity.peak_at | Δ velocity.ease_in | Δ velocity.ease_out | Δ velocity.peak_acc | Δ velocity.peak_dec | Δ velocity.onset_step | Δ velocity.stop_step | Δ lead.shoulder | Δ lead.shoulder_shift | Δ lead.torso | Δ lead.hip | Δ lead.hip_shift | Δ settle.torso | Δ settle.neck | Δ settle.head | Δ settle.hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 57 | 57 | -0.19 | -1.82 | 1.18 | 0.03 | -0.20 | +0 | -0.01 | 0.05 | 0.05 | 0.00 | 0.58 | -2.41 | 0.02 | -0.11 | – | – | – | – | – | +0 | +0 | +0 | +12 |
| girl | L | 104 | 104 | -0.11 | -10.54 | -12.82 | -0.09 | -0.10 | +0 | 0.01 | 0.00 | 0.00 | -0.10 | -4.47 | -11.89 | 0.02 | -0.06 | – | – | – | – | – | +0 | +0 | +0 | +0 |
