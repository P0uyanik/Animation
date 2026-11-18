# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `girl_auburn_bun_glasses_master.blend` -> `girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 62.3 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 59 | figure IoU 0.796 |
| regions (weight 0.10) | 44 | mean region IoU 0.437 |
| landmarks (weight 0.15) | 71 | mean error 0.087 head heights |
| proportions (weight 0.10) | 59 | mean relative error 12.3% |
| colour (weight 0.10) | 71 | mean dE00 5.8 |
| texture (weight 0.05) | 68 | mean abs log2 ratio 0.48 |
| hair (weight 0.15) | 60 | shape 60, volume 76, face_cover 15, outline 57, strand 93, relief 60 |
| skin (weight 0.10) | 66 | skin_face dE00 11.1, shade chroma -7.4, blush a* P90 -7.3; skin_limbs dE00 4.3, shade chroma -1.4, blush a* P90 -3.6 |
| face (weight 0.05) | 69 | lid_dL +6.1, lid_dC -2.0, blush_da -0.1 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.810 | 0.042 | [sheet](sheets/sheet30_front.png) |
| sheet30_front_left | 0.796 | 0.076 | [sheet](sheets/sheet30_front_left.png) |
| sheet30_left | 0.743 | 0.059 | [sheet](sheets/sheet30_left.png) |
| sheet30_back_right | 0.778 | 0.146 | [sheet](sheets/sheet30_back_right.png) |
| sheet30_back | 0.852 | 0.113 | [sheet](sheets/sheet30_back.png) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 33% too long relative to height  _(severity 6.5, proportion)_
2. hair_accessory silhouette overlap 0.10; render area +110%  _(severity 6.0, region)_
3. blouse silhouette overlap 0.19; render area -45%  _(severity 5.4, region)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. hair covers 25% of the face that the reference shows uncovered  _(severity 5.1, hair)_
6. eyes silhouette overlap 0.24; render area -32%  _(severity 5.1, region)_
7. vest silhouette overlap 0.32; render area -34%  _(severity 4.6, region)_
8. skin_limbs silhouette overlap 0.36; render area -41%  _(severity 4.3, region)_
9. hair accessory colour dE00 16.4 (render darker by 5 L*, less saturated by 6 C*, hue shifted 117 deg towards yellow/green); luma-matched dE00 8.6  _(severity 4.1, colour)_
10. glasses silhouette overlap 0.40; render area -8%  _(severity 4.0, region)_
11. eyes 19% too small (width relative to head height)  _(severity 3.7, proportion)_
12. hands off by 0.18 head heights, render higher by 0.09  _(severity 3.7, landmark)_
13. blouse fuzz / fibre texture +190% vs reference  _(severity 3.1, texture)_
14. skin_face silhouette overlap 0.54; render area +20%  _(severity 3.0, region)_
15. eye area 30% too small relative to head height squared  _(severity 3.0, proportion)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
