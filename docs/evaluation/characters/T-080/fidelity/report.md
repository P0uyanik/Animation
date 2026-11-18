# Fidelity report: boy_yellow_hoodie

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `boy_yellow_hoodie_master.blend` -> `boy_yellow_hoodie_compare.blend` (variant: compare)
- Views: val27_front, val27_threequarter_right, val27_side_right, val27_back, val27_back_threequarter
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 67.5 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 67 | figure IoU 0.835 |
| regions (weight 0.10) | 60 | mean region IoU 0.604 |
| landmarks (weight 0.15) | 82 | mean error 0.053 head heights |
| proportions (weight 0.10) | 60 | mean relative error 12.1% |
| colour (weight 0.10) | 75 | mean dE00 5.0 |
| texture (weight 0.05) | 74 | mean abs log2 ratio 0.38 |
| hair (weight 0.15) | 68 | shape 71, volume 59, face_cover 81, outline 46, strand 82, relief 68 |
| skin (weight 0.10) | 48 | skin_face dE00 7.3, shade chroma -8.8, blush a* P90 -8.4; skin_limbs dE00 19.4, shade chroma -9.2, blush a* P90 -10.9 |
| face (weight 0.05) | 72 | lid_dL +3.0, lid_dC +0.5, blush_da +5.3 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.858 | 0.056 | [sheet](sheets/val27_front.png) |
| val27_threequarter_right | 0.860 | 0.062 | [sheet](sheets/val27_threequarter_right.png) |
| val27_side_right | 0.794 | 0.056 | [sheet](sheets/val27_side_right.png) |
| val27_back | 0.829 | 0.034 | [sheet](sheets/val27_back.png) |
| val27_back_threequarter | 0.833 | 0.057 | [sheet](sheets/val27_back_threequarter.png) |

## Largest differences (ranked)

1. eyes 35% too small (width relative to head height)  _(severity 7.1, proportion)_
2. backpack silhouette overlap 0.00; missing in render  _(severity 6.7, region)_
3. visible gap between the legs (crotch to sole) 31% too short relative to height  _(severity 6.2, proportion)_
4. eyes silhouette overlap 0.15; render area -44%  _(severity 5.7, region)_
5. skin limbs colour dE00 19.4 (render lighter by 20 L*, less saturated by 5 C*, hue shifted 13 deg towards yellow/green); luma-matched dE00 5.1  _(severity 4.9, colour)_
6. skin_limbs silhouette overlap 0.36; render area -27%  _(severity 4.3, region)_
7. skin face colour dE00 15.1 (render darker by 4 L*, hue shifted 10 deg towards yellow/green); luma-matched dE00 3.4  _(severity 3.8, colour)_
8. hair width at the temples (eye level) +36%  _(severity 3.6, proportion)_
9. skin limbs fuzz / fibre texture -66% vs reference  _(severity 3.2, texture)_
10. eye area 31% too small relative to head height squared  _(severity 3.1, proportion)_
11. skin_face silhouette overlap 0.57; render area +22%  _(severity 2.8, region)_
12. skin limbs warmth / blush (a* P90) -10.9 (weaker)  _(severity 2.7, skin)_
13. hoodie silhouette overlap 0.60; render area +13%  _(severity 2.7, region)_
14. overall silhouette 13% too wide relative to height  _(severity 2.6, proportion)_
15. shoes silhouette overlap 0.62; render area +40%  _(severity 2.6, region)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
