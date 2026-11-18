# Fidelity report: boy_yellow_hoodie

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `boy_yellow_hoodie_master.blend` -> `boy_yellow_hoodie_compare.blend` (variant: compare)
- Views: val27_front, val27_threequarter_right, val27_side_right, val27_back, val27_back_threequarter
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 67.6 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 69 | figure IoU 0.843 |
| regions (weight 0.10) | 60 | mean region IoU 0.602 |
| landmarks (weight 0.15) | 82 | mean error 0.055 head heights |
| proportions (weight 0.10) | 60 | mean relative error 12.0% |
| colour (weight 0.10) | 75 | mean dE00 5.0 |
| texture (weight 0.05) | 73 | mean abs log2 ratio 0.41 |
| hair (weight 0.15) | 68 | shape 73, volume 71, face_cover 72, outline 43, strand 84, relief 65 |
| skin (weight 0.10) | 48 | skin_face dE00 7.3, shade chroma -8.8, blush a* P90 -8.3; skin_limbs dE00 19.3, shade chroma -9.2, blush a* P90 -10.8 |
| face (weight 0.05) | 70 | lid_dL +3.7, lid_dC +0.7, blush_da +5.5 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.868 | 0.054 | [sheet](sheets/val27_front.jpg) |
| val27_threequarter_right | 0.875 | 0.061 | [sheet](sheets/val27_threequarter_right.jpg) |
| val27_side_right | 0.806 | 0.062 | [sheet](sheets/val27_side_right.jpg) |
| val27_back | 0.829 | 0.043 | [sheet](sheets/val27_back.jpg) |
| val27_back_threequarter | 0.838 | 0.057 | [sheet](sheets/val27_back_threequarter.jpg) |

## Largest differences (ranked)

1. backpack silhouette overlap 0.00; missing in render  _(severity 6.7, region)_
2. visible gap between the legs (crotch to sole) 31% too short relative to height  _(severity 6.2, proportion)_
3. eyes 30% too small (width relative to head height)  _(severity 6.0, proportion)_
4. eyes silhouette overlap 0.15; render area -40%  _(severity 5.7, region)_
5. skin limbs colour dE00 19.3 (render lighter by 20 L*, less saturated by 5 C*, hue shifted 14 deg towards yellow/green); luma-matched dE00 5.2  _(severity 4.8, colour)_
6. skin_limbs silhouette overlap 0.35; render area -28%  _(severity 4.3, region)_
7. eye area 40% too small relative to head height squared  _(severity 4.0, proportion)_
8. skin face colour dE00 13.8 (render darker by 4 L*, hue shifted 10 deg towards yellow/green); luma-matched dE00 3.5  _(severity 3.5, colour)_
9. skin limbs fuzz / fibre texture -67% vs reference  _(severity 3.2, texture)_
10. skin_face silhouette overlap 0.55; render area +21%  _(severity 3.0, region)_
11. skin limbs warmth / blush (a* P90) -10.8 (weaker)  _(severity 2.7, skin)_
12. hoodie silhouette overlap 0.60; render area +12%  _(severity 2.6, region)_
13. shoes silhouette overlap 0.62; render area +39%  _(severity 2.5, region)_
14. ear tops (ear_top_L) hidden in the render but visible in the reference (3 of 5 views)  _(severity 2.5, visibility)_
15. skin limbs chroma in shade -9.2 C* (grey cast)  _(severity 2.3, skin)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
