# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `girl_auburn_bun_glasses_master.blend` -> `girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 62.8 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 60 | figure IoU 0.800 |
| regions (weight 0.10) | 44 | mean region IoU 0.445 |
| landmarks (weight 0.15) | 71 | mean error 0.086 head heights |
| proportions (weight 0.10) | 58 | mean relative error 12.6% |
| colour (weight 0.10) | 72 | mean dE00 5.6 |
| texture (weight 0.05) | 71 | mean abs log2 ratio 0.44 |
| hair (weight 0.15) | 59 | shape 62, volume 74, face_cover 10, outline 56, strand 91, relief 64 |
| skin (weight 0.10) | 67 | skin_face dE00 11.3, shade chroma -7.6, blush a* P90 -6.9; skin_limbs dE00 4.2, shade chroma -1.2, blush a* P90 -3.5 |
| face (weight 0.05) | 70 | lid_dL +6.6, lid_dC -1.7, blush_da +0.2 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.813 | 0.044 | [sheet](sheets/sheet30_front.png) |
| sheet30_front_left | 0.798 | 0.066 | [sheet](sheets/sheet30_front_left.png) |
| sheet30_left | 0.754 | 0.051 | [sheet](sheets/sheet30_left.png) |
| sheet30_back_right | 0.782 | 0.150 | [sheet](sheets/sheet30_back_right.png) |
| sheet30_back | 0.851 | 0.117 | [sheet](sheets/sheet30_back.png) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 33% too long relative to height  _(severity 6.6, proportion)_
2. hair_accessory silhouette overlap 0.06; render area +123%  _(severity 6.2, region)_
3. hair covers 27% of the face that the reference shows uncovered  _(severity 5.4, hair)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. blouse silhouette overlap 0.23; render area -37%  _(severity 5.1, region)_
6. vest silhouette overlap 0.33; render area -31%  _(severity 4.5, region)_
7. skin_limbs silhouette overlap 0.36; render area -28%  _(severity 4.2, region)_
8. eyes silhouette overlap 0.37; render area -29%  _(severity 4.2, region)_
9. hair accessory colour dE00 16.1 (render darker by 5 L*, less saturated by 6 C*, hue shifted 116 deg towards yellow/green); luma-matched dE00 8.6  _(severity 4.0, colour)_
10. eyes 18% too small (width relative to head height)  _(severity 3.5, proportion)_
11. glasses silhouette overlap 0.47; render area -4%  _(severity 3.5, region)_
12. hands off by 0.17 head heights  _(severity 3.3, landmark)_
13. skin_face silhouette overlap 0.51; render area +23%  _(severity 3.3, region)_
14. shorts silhouette overlap 0.55; render area -27%  _(severity 3.0, region)_
15. skin face colour dE00 11.3 (render darker by 4 L*); luma-matched dE00 3.1  _(severity 2.8, colour)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
