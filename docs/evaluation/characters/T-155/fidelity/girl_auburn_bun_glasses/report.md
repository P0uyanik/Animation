# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `girl_auburn_bun_glasses_master.blend` -> `girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 63.4 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 60 | figure IoU 0.800 |
| regions (weight 0.10) | 48 | mean region IoU 0.476 |
| landmarks (weight 0.15) | 72 | mean error 0.084 head heights |
| proportions (weight 0.10) | 53 | mean relative error 14.1% |
| colour (weight 0.10) | 64 | mean dE00 7.2 |
| texture (weight 0.05) | 77 | mean abs log2 ratio 0.34 |
| hair (weight 0.15) | 62 | shape 61, volume 77, face_cover 56, outline 35, strand 87, relief 54 |
| skin (weight 0.10) | 72 | skin_face dE00 8.9, shade chroma -6.0, blush a* P90 -2.7; skin_limbs dE00 5.6, shade chroma +1.5, blush a* P90 -3.2 |
| face (weight 0.05) | 76 | lid_dL +0.6, lid_dC -0.6, blush_da +4.8 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.833 | 0.039 | [sheet](sheets/sheet30_front.jpg) |
| sheet30_front_left | 0.808 | 0.065 | [sheet](sheets/sheet30_front_left.jpg) |
| sheet30_left | 0.736 | 0.059 | [sheet](sheets/sheet30_left.jpg) |
| sheet30_back_right | 0.765 | 0.155 | [sheet](sheets/sheet30_back_right.jpg) |
| sheet30_back | 0.857 | 0.104 | [sheet](sheets/sheet30_back.jpg) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 45% too long relative to height  _(severity 8.9, proportion)_
2. hair_accessory silhouette overlap 0.08; render area +24%  _(severity 6.2, region)_
3. hair accessory colour dE00 23.2 (render less saturated by 3 C*, hue shifted 14 deg towards yellow/green); luma-matched dE00 12.1  _(severity 5.8, colour)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. eyes silhouette overlap 0.32; render area -18%  _(severity 4.5, region)_
6. vest silhouette overlap 0.36; render area -24%  _(severity 4.3, region)_
7. blouse silhouette overlap 0.36; render area -7%  _(severity 4.3, region)_
8. overall silhouette 21% too narrow relative to height  _(severity 4.3, proportion)_
9. skin_limbs silhouette overlap 0.38; render area -42%  _(severity 4.1, region)_
10. glasses silhouette overlap 0.41; render area -7%  _(severity 4.0, region)_
11. hands off by 0.18 head heights  _(severity 3.7, landmark)_
12. shorts silhouette overlap 0.51; render area -35%  _(severity 3.3, region)_
13. eye spacing 14% too narrow relative to head height  _(severity 2.7, proportion)_
14. hair covers 13% of the face that the reference shows uncovered  _(severity 2.6, hair)_
15. hair length +26%  _(severity 2.6, proportion)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
