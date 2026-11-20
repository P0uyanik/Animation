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

## Fidelity score: 69.5 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 67 | figure IoU 0.834 |
| regions (weight 0.10) | 61 | mean region IoU 0.608 |
| landmarks (weight 0.15) | 84 | mean error 0.047 head heights |
| proportions (weight 0.10) | 74 | mean relative error 7.9% |
| colour (weight 0.10) | 69 | mean dE00 6.2 |
| texture (weight 0.05) | 61 | mean abs log2 ratio 0.58 |
| hair (weight 0.15) | 67 | shape 70, volume 39, face_cover 91, outline 49, strand 90, relief 65 |
| skin (weight 0.10) | 62 | skin_face dE00 5.4, shade chroma -6.8, blush a* P90 -7.5; skin_limbs dE00 15.0, shade chroma -8.1, blush a* P90 -6.4 |
| face (weight 0.05) | 77 | lid_dL +4.0, lid_dC +1.5, blush_da +2.5 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.852 | 0.041 | [sheet](sheets/val27_front.jpg) |
| val27_threequarter_right | 0.856 | 0.051 | [sheet](sheets/val27_threequarter_right.jpg) |
| val27_side_right | 0.796 | 0.057 | [sheet](sheets/val27_side_right.jpg) |
| val27_back | 0.822 | 0.029 | [sheet](sheets/val27_back.jpg) |
| val27_back_threequarter | 0.843 | 0.055 | [sheet](sheets/val27_back_threequarter.jpg) |

## Largest differences (ranked)

1. hair width at the temples (eye level) -70%  _(severity 7.0, proportion)_
2. backpack silhouette overlap 0.15; render area -38%  _(severity 5.7, region)_
3. eyes silhouette overlap 0.21; render area -22%  _(severity 5.3, region)_
4. skin_limbs silhouette overlap 0.32; render area -21%  _(severity 4.5, region)_
5. eyes 20% too small (width relative to head height)  _(severity 4.0, proportion)_
6. trousers fuzz / fibre texture -74% vs reference  _(severity 3.8, texture)_
7. skin limbs colour dE00 15.0 (render lighter by 15 L*); luma-matched dE00 1.5  _(severity 3.8, colour)_
8. skin face colour dE00 13.6 (render hue shifted 10 deg towards yellow/green); luma-matched dE00 3.4  _(severity 3.4, colour)_
9. overall silhouette 17% too wide relative to height  _(severity 3.3, proportion)_
10. skin_face silhouette overlap 0.57; render area +22%  _(severity 2.9, region)_
11. hoodie silhouette overlap 0.59; render area +13%  _(severity 2.8, region)_
12. backpack fuzz / fibre texture -56% vs reference  _(severity 2.4, texture)_
13. hoodie fuzz / fibre texture -56% vs reference  _(severity 2.3, texture)_
14. backpack colour dE00 9.1 (render lighter by 4 L*, more saturated by 3 C*, hue shifted 47 deg towards red/magenta); luma-matched dE00 6.7  _(severity 2.3, colour)_
15. shoes colour dE00 8.9 (render darker by 7 L*, more saturated by 16 C*); luma-matched dE00 6.7  _(severity 2.2, colour)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
