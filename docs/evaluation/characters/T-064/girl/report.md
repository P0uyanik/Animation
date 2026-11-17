# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json` -> `<out>/build/girl_auburn_bun_glasses_master.blend` + `assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.10.0.override.json` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 64.4 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 65 | figure IoU 0.825 |
| regions (weight 0.10) | 50 | mean region IoU 0.497 |
| landmarks (weight 0.15) | 73 | mean error 0.080 head heights |
| proportions (weight 0.10) | 62 | mean relative error 11.4% |
| colour (weight 0.10) | 71 | mean dE00 5.7 |
| texture (weight 0.05) | 74 | mean abs log2 ratio 0.39 |
| hair (weight 0.15) | 58 | shape 70, volume 90, face_cover 0, outline 45, strand 87, relief 55 |
| skin (weight 0.10) | 78 | skin_face dE00 4.3, shade chroma -7.7, blush a* P90 -5.9; skin_limbs dE00 2.7, shade chroma -1.2, blush a* P90 -1.6 |
| face (weight 0.05) | 38 | lid_dL +19.0, lid_dC +3.1, blush_da -2.1 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.847 | 0.049 | [sheet](sheets/sheet30_front.png) |
| sheet30_front_left | 0.842 | 0.065 | [sheet](sheets/sheet30_front_left.png) |
| sheet30_left | 0.778 | 0.055 | [sheet](sheets/sheet30_left.png) |
| sheet30_back_right | 0.791 | 0.134 | [sheet](sheets/sheet30_back_right.png) |
| sheet30_back | 0.868 | 0.096 | [sheet](sheets/sheet30_back.png) |

## Largest differences (ranked)

1. hair covers 46% of the face that the reference shows uncovered  _(severity 9.3, hair)_
2. visible gap between the legs (crotch to sole) 37% too long relative to height  _(severity 7.4, proportion)_
3. hair_accessory silhouette overlap 0.14; render area +17%  _(severity 5.8, region)_
4. arms 26% too short relative to height  _(severity 5.3, proportion)_
5. hair accessory colour dE00 20.6 (render darker by 4 L*, hue shifted 12 deg towards yellow/green); luma-matched dE00 11.5  _(severity 5.1, colour)_
6. eyes silhouette overlap 0.28; render area -12%  _(severity 4.8, region)_
7. lids vs face skin, lightness +19.0 L* vs the reference (paler lids (shell domes))  _(severity 4.7, face)_
8. skin_limbs silhouette overlap 0.38; render area -34%  _(severity 4.1, region)_
9. blouse silhouette overlap 0.41; render area +2%  _(severity 3.9, region)_
10. skin_face silhouette overlap 0.42; render area -16%  _(severity 3.9, region)_
11. glasses silhouette overlap 0.42; render area -7%  _(severity 3.8, region)_
12. eyes 18% too small (width relative to head height)  _(severity 3.7, proportion)_
13. vest silhouette overlap 0.48; render area -5%  _(severity 3.5, region)_
14. overall silhouette 17% too narrow relative to height  _(severity 3.3, proportion)_
15. hands off by 0.16 head heights  _(severity 3.2, landmark)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
