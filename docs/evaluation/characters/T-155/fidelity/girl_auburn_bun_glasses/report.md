# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/girl_auburn_bun_glasses/versions/0.14.0/girl_auburn_bun_glasses_master.blend` -> `assets/characters/girl_auburn_bun_glasses/versions/0.14.0/girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 63.1 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 62 | figure IoU 0.810 |
| regions (weight 0.10) | 49 | mean region IoU 0.489 |
| landmarks (weight 0.15) | 71 | mean error 0.087 head heights |
| proportions (weight 0.10) | 51 | mean relative error 14.6% |
| colour (weight 0.10) | 68 | mean dE00 6.4 |
| texture (weight 0.05) | 76 | mean abs log2 ratio 0.36 |
| hair (weight 0.15) | 60 | shape 65, volume 88, face_cover 29, outline 35, strand 92, relief 50 |
| skin (weight 0.10) | 71 | skin_face dE00 11.8, shade chroma -6.1, blush a* P90 -2.4; skin_limbs dE00 5.6, shade chroma +0.9, blush a* P90 -2.9 |
| face (weight 0.05) | 67 | lid_dL +0.5, lid_dC +0.0, blush_da +7.5 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.835 | 0.042 | [sheet](sheets/sheet30_front.jpg) |
| sheet30_front_left | 0.822 | 0.069 | [sheet](sheets/sheet30_front_left.jpg) |
| sheet30_left | 0.759 | 0.063 | [sheet](sheets/sheet30_left.jpg) |
| sheet30_back_right | 0.771 | 0.157 | [sheet](sheets/sheet30_back_right.jpg) |
| sheet30_back | 0.861 | 0.106 | [sheet](sheets/sheet30_back.jpg) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 44% too long relative to height  _(severity 8.9, proportion)_
2. hair_accessory silhouette overlap 0.08; render area +98%  _(severity 6.1, region)_
3. hair accessory colour dE00 23.7 (render darker by 5 L*, less saturated by 20 C*, hue shifted 156 deg towards yellow/green); luma-matched dE00 22.3  _(severity 5.9, colour)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. eyes silhouette overlap 0.29; render area -35%  _(severity 4.8, region)_
6. blouse silhouette overlap 0.34; render area -8%  _(severity 4.4, region)_
7. hair covers 21% of the face that the reference shows uncovered  _(severity 4.3, hair)_
8. overall silhouette 21% too narrow relative to height  _(severity 4.1, proportion)_
9. skin_limbs silhouette overlap 0.38; render area -43%  _(severity 4.1, region)_
10. glasses silhouette overlap 0.40; render area -7%  _(severity 4.0, region)_
11. vest silhouette overlap 0.42; render area -11%  _(severity 3.9, region)_
12. hands off by 0.18 head heights  _(severity 3.6, landmark)_
13. shorts silhouette overlap 0.53; render area -31%  _(severity 3.1, region)_
14. skin face colour dE00 11.8 (render darker by 7 L*, hue shifted 9 deg towards yellow/green); luma-matched dE00 3.1  _(severity 2.9, colour)_
15. skin face fuzz / fibre texture +163% vs reference  _(severity 2.8, texture)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
