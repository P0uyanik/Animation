# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `girl_auburn_bun_glasses_master.blend` -> `girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 65.0 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 63 | figure IoU 0.813 |
| regions (weight 0.10) | 47 | mean region IoU 0.471 |
| landmarks (weight 0.15) | 70 | mean error 0.089 head heights |
| proportions (weight 0.10) | 64 | mean relative error 10.8% |
| colour (weight 0.10) | 66 | mean dE00 6.9 |
| texture (weight 0.05) | 69 | mean abs log2 ratio 0.46 |
| hair (weight 0.15) | 62 | shape 63, volume 86, face_cover 37, outline 43, strand 94, relief 51 |
| skin (weight 0.10) | 73 | skin_face dE00 11.4, shade chroma -4.4, blush a* P90 -3.6; skin_limbs dE00 3.9, shade chroma -0.1, blush a* P90 -3.5 |
| face (weight 0.05) | 83 | lid_dL +5.1, lid_dC +0.0, blush_da +0.2 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.838 | 0.044 | [sheet](sheets/sheet30_front.png) |
| sheet30_front_left | 0.826 | 0.068 | [sheet](sheets/sheet30_front_left.png) |
| sheet30_left | 0.754 | 0.068 | [sheet](sheets/sheet30_left.png) |
| sheet30_back_right | 0.782 | 0.149 | [sheet](sheets/sheet30_back_right.png) |
| sheet30_back | 0.862 | 0.115 | [sheet](sheets/sheet30_back.png) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 39% too long relative to height  _(severity 7.8, proportion)_
2. hair_accessory silhouette overlap 0.07; render area +81%  _(severity 6.2, region)_
3. hair accessory colour dE00 23.6 (render darker by 4 L*, less saturated by 20 C*, hue shifted 156 deg towards yellow/green); luma-matched dE00 22.2  _(severity 5.9, colour)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. blouse silhouette overlap 0.30; render area -14%  _(severity 4.6, region)_
6. eyes silhouette overlap 0.34; render area -1%  _(severity 4.4, region)_
7. overall silhouette 22% too narrow relative to height  _(severity 4.3, proportion)_
8. skin_limbs silhouette overlap 0.37; render area -48%  _(severity 4.2, region)_
9. vest silhouette overlap 0.37; render area -28%  _(severity 4.2, region)_
10. glasses silhouette overlap 0.38; render area -7%  _(severity 4.1, region)_
11. hair covers 19% of the face that the reference shows uncovered  _(severity 3.8, hair)_
12. hands off by 0.18 head heights  _(severity 3.7, landmark)_
13. shorts silhouette overlap 0.55; render area -18%  _(severity 3.0, region)_
14. skin face colour dE00 11.4 (render hue shifted 9 deg towards yellow/green); luma-matched dE00 3.2  _(severity 2.9, colour)_
15. skin_face silhouette overlap 0.58; render area +22%  _(severity 2.8, region)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
