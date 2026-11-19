# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `girl_auburn_bun_glasses_master.blend` -> `girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 64.1 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 63 | figure IoU 0.813 |
| regions (weight 0.10) | 47 | mean region IoU 0.473 |
| landmarks (weight 0.15) | 71 | mean error 0.086 head heights |
| proportions (weight 0.10) | 61 | mean relative error 11.7% |
| colour (weight 0.10) | 65 | mean dE00 6.9 |
| texture (weight 0.05) | 69 | mean abs log2 ratio 0.46 |
| hair (weight 0.15) | 63 | shape 63, volume 87, face_cover 41, outline 42, strand 94, relief 51 |
| skin (weight 0.10) | 71 | skin_face dE00 9.4, shade chroma -6.6, blush a* P90 -5.1; skin_limbs dE00 3.9, shade chroma -0.4, blush a* P90 -3.5 |
| face (weight 0.05) | 71 | lid_dL +3.3, lid_dC +0.0, blush_da +5.3 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.838 | 0.047 | [sheet](sheets/sheet30_front.jpg) |
| sheet30_front_left | 0.826 | 0.066 | [sheet](sheets/sheet30_front_left.jpg) |
| sheet30_left | 0.757 | 0.054 | [sheet](sheets/sheet30_left.jpg) |
| sheet30_back_right | 0.782 | 0.150 | [sheet](sheets/sheet30_back_right.jpg) |
| sheet30_back | 0.862 | 0.115 | [sheet](sheets/sheet30_back.jpg) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 39% too long relative to height  _(severity 7.8, proportion)_
2. hair_accessory silhouette overlap 0.08; render area +69%  _(severity 6.2, region)_
3. hair accessory colour dE00 23.6 (render darker by 4 L*, less saturated by 20 C*, hue shifted 156 deg towards yellow/green); luma-matched dE00 22.2  _(severity 5.9, colour)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. blouse silhouette overlap 0.30; render area -15%  _(severity 4.7, region)_
6. eyes silhouette overlap 0.34; render area -15%  _(severity 4.4, region)_
7. overall silhouette 22% too narrow relative to height  _(severity 4.3, proportion)_
8. skin_limbs silhouette overlap 0.36; render area -47%  _(severity 4.3, region)_
9. vest silhouette overlap 0.36; render area -28%  _(severity 4.2, region)_
10. glasses silhouette overlap 0.39; render area -6%  _(severity 4.1, region)_
11. hands off by 0.18 head heights  _(severity 3.6, landmark)_
12. hair covers 18% of the face that the reference shows uncovered  _(severity 3.6, hair)_
13. shorts silhouette overlap 0.55; render area -18%  _(severity 3.0, region)_
14. shorts fuzz / fibre texture -63% vs reference  _(severity 2.9, texture)_
15. eye spacing 14% too narrow relative to head height  _(severity 2.8, proportion)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
