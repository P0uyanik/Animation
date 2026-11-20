# Reach measurements: r5

bake `<scratch>/r5.json`, frames 1–192, 24 fps, 2 wrist moves (chord ≥ 60 mm).

| char | side | frames | kind | chord mm | dev mm (ratio) | arc | peak m/s @ | ease in/out | acc/dec mm/f² | stall / dec2 | onset/stop step | lead sh/sh-shift/torso/hip/hip-shift | overlap pk torso/neck/head/hair | settle torso/neck/head/hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 57–76 | extend | 137 | 62 (0.45) | 1.76 | 0.69 @ 0.50 | 0.32/0.37 | 10.0/7.7 | 0.01 / 14.2 | 0.35/0.01 | +1/+3/+11/–/+4 | +14/-6/-9/-5 | +28/+10/+0/+19 |
| girl | L | 104–114 | extend | 137 | 27 (0.20) | 1.28 | 1.14 @ 0.45 | 0.30/0.40 | 19.2/22.1 | 0.05 / 29.3 | 0.13/0.08 | +2/+4/–/+4/+5 | -4/+18/+41/+18 | +36/+28/+36/+36 |

Summary (medians): moves 2, extend 2, velocity.stall 0.03, velocity.dec2 21.74, path.max_dev_mm 44.58, path.dev_ratio 0.32, path.arc_ratio 1.52, velocity.frames 14.50, velocity.peak_m_s 0.92, velocity.peak_at 0.47, velocity.ease_in 0.31, velocity.ease_out 0.38, velocity.peak_acc 14.60, velocity.peak_dec 14.93, velocity.onset_step 0.24, velocity.stop_step 0.04, lead.shoulder.median 1.50, lead.shoulder.share_leading 1.00, lead.shoulder_shift.median 3.50, lead.shoulder_shift.share_leading 1.00, lead.torso.median 11.00, lead.torso.share_leading 0.50, lead.hip.median 4.00, lead.hip.share_leading 0.50, lead.hip_shift.median 4.50, lead.hip_shift.share_leading 1.00, overlap.torso.peak_offset 5.00, overlap.torso.settle 32.00, overlap.neck.peak_offset 6.00, overlap.neck.settle 19.00, overlap.head.peak_offset 16.00, overlap.head.settle 18.00, overlap.hair.peak_offset 6.50, overlap.hair.settle 27.50

## Against baseline `<scratch>/run_base/bake.json`

| char | side | start | base start | Δ velocity.stall | Δ velocity.dec2 | Δ path.max_dev_mm | Δ path.dev_ratio | Δ path.arc_ratio | Δ velocity.frames | Δ velocity.peak_m_s | Δ velocity.peak_at | Δ velocity.ease_in | Δ velocity.ease_out | Δ velocity.peak_acc | Δ velocity.peak_dec | Δ velocity.onset_step | Δ velocity.stop_step | Δ lead.shoulder | Δ lead.shoulder_shift | Δ lead.torso | Δ lead.hip | Δ lead.hip_shift | Δ settle.torso | Δ settle.neck | Δ settle.head | Δ settle.hair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boy | R | 57 | 57 | -0.23 | -5.22 | 16.19 | 0.14 | -0.05 | +0 | -0.03 | 0.05 | 0.05 | 0.00 | 2.89 | -4.04 | 0.11 | -0.11 | – | – | – | – | – | +0 | +10 | +0 | +19 |
| girl | L | 104 | 104 | -0.06 | -10.87 | -24.18 | -0.15 | -0.13 | +0 | -0.12 | 0.00 | 0.00 | -0.10 | -7.32 | -8.84 | 0.07 | -0.06 | – | – | – | – | – | +0 | +0 | +0 | +0 |
