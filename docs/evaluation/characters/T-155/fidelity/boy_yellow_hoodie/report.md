# Fidelity report: boy_yellow_hoodie

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `boy_yellow_hoodie_master.blend` -> `boy_yellow_hoodie_compare.blend` (variant: compare)
- Hide prefixes that matched no object (val27_back): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_back_threequarter): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_front): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_side_right): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_threequarter_right): backpack_body, backpack_pocket, backpack_handle
- Views: val27_front, val27_threequarter_right, val27_side_right, val27_back, val27_back_threequarter
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 69.7 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 65 | figure IoU 0.826 |
| regions (weight 0.10) | 61 | mean region IoU 0.606 |
| landmarks (weight 0.15) | 85 | mean error 0.046 head heights |
| proportions (weight 0.10) | 78 | mean relative error 6.6% |
| colour (weight 0.10) | 69 | mean dE00 6.2 |
| texture (weight 0.05) | 61 | mean abs log2 ratio 0.59 |
| hair (weight 0.15) | 65 | shape 69, volume 23, face_cover 96, outline 56, strand 90, relief 58 |
| skin (weight 0.10) | 66 | skin_face dE00 6.5, shade chroma -5.2, blush a* P90 -3.6; skin_limbs dE00 15.5, shade chroma -7.6, blush a* P90 -5.8 |
| face (weight 0.05) | 74 | lid_dL +5.9, lid_dC +1.0, blush_da +2.3 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.849 | 0.040 | [sheet](sheets/val27_front.jpg) |
| val27_threequarter_right | 0.859 | 0.048 | [sheet](sheets/val27_threequarter_right.jpg) |
| val27_side_right | 0.784 | 0.055 | [sheet](sheets/val27_side_right.jpg) |
| val27_back | 0.812 | 0.028 | [sheet](sheets/val27_back.jpg) |
| val27_back_threequarter | 0.826 | 0.058 | [sheet](sheets/val27_back_threequarter.jpg) |

## Largest differences (ranked)

1. hair width at the temples (eye level) -90%  _(severity 9.0, proportion)_
2. backpack silhouette overlap 0.14; render area -39%  _(severity 5.7, region)_
3. eyes silhouette overlap 0.19; render area -17%  _(severity 5.4, region)_
4. skin_limbs silhouette overlap 0.32; render area -21%  _(severity 4.6, region)_
5. eyes 19% too small (width relative to head height)  _(severity 3.9, proportion)_
6. skin limbs colour dE00 15.5 (render lighter by 16 L*); luma-matched dE00 1.5  _(severity 3.9, colour)_
7. trousers fuzz / fibre texture -74% vs reference  _(severity 3.8, texture)_
8. overall silhouette 18% too wide relative to height  _(severity 3.6, proportion)_
9. skin_face silhouette overlap 0.54; render area +30%  _(severity 3.0, region)_
10. hoodie silhouette overlap 0.59; render area +15%  _(severity 2.8, region)_
11. backpack fuzz / fibre texture -60% vs reference  _(severity 2.6, texture)_
12. skin face colour dE00 9.2 (render hue shifted 9 deg towards yellow/green); luma-matched dE00 3.3  _(severity 2.3, colour)_
13. backpack colour dE00 9.2 (render lighter by 4 L*, more saturated by 3 C*, hue shifted 47 deg towards red/magenta); luma-matched dE00 6.7  _(severity 2.3, colour)_
14. hoodie fuzz / fibre texture -55% vs reference  _(severity 2.3, texture)_
15. shoes colour dE00 8.9 (render darker by 7 L*, more saturated by 16 C*); luma-matched dE00 6.7  _(severity 2.2, colour)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
