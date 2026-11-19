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

## Fidelity score: 67.7 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 67 | figure IoU 0.834 |
| regions (weight 0.10) | 60 | mean region IoU 0.603 |
| landmarks (weight 0.15) | 83 | mean error 0.050 head heights |
| proportions (weight 0.10) | 72 | mean relative error 8.4% |
| colour (weight 0.10) | 69 | mean dE00 6.3 |
| texture (weight 0.05) | 59 | mean abs log2 ratio 0.62 |
| hair (weight 0.15) | 65 | shape 70, volume 52, face_cover 84, outline 45, strand 80, relief 58 |
| skin (weight 0.10) | 53 | skin_face dE00 6.5, shade chroma -7.4, blush a* P90 -8.0; skin_limbs dE00 18.3, shade chroma -8.1, blush a* P90 -9.2 |
| face (weight 0.05) | 76 | lid_dL +4.8, lid_dC +0.9, blush_da +2.3 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.854 | 0.039 | [sheet](sheets/val27_front.png) |
| val27_threequarter_right | 0.852 | 0.051 | [sheet](sheets/val27_threequarter_right.png) |
| val27_side_right | 0.804 | 0.073 | [sheet](sheets/val27_side_right.png) |
| val27_back | 0.822 | 0.029 | [sheet](sheets/val27_back.png) |
| val27_back_threequarter | 0.840 | 0.057 | [sheet](sheets/val27_back_threequarter.png) |

## Largest differences (ranked)

1. hair width at the temples (eye level) -58%  _(severity 5.8, proportion)_
2. backpack silhouette overlap 0.14; render area -41%  _(severity 5.7, region)_
3. eyes silhouette overlap 0.17; render area -12%  _(severity 5.5, region)_
4. overall silhouette 27% too wide relative to height  _(severity 5.5, proportion)_
5. skin limbs colour dE00 18.3 (render lighter by 18 L*, less saturated by 4 C*, hue shifted 13 deg towards yellow/green); luma-matched dE00 5.0  _(severity 4.6, colour)_
6. skin_limbs silhouette overlap 0.33; render area -29%  _(severity 4.5, region)_
7. eyes 19% too small (width relative to head height)  _(severity 3.9, proportion)_
8. trousers fuzz / fibre texture -71% vs reference  _(severity 3.6, texture)_
9. skin face colour dE00 14.1 (render darker by 3 L*, hue shifted 10 deg towards yellow/green); luma-matched dE00 3.3  _(severity 3.5, colour)_
10. skin limbs fuzz / fibre texture -67% vs reference  _(severity 3.2, texture)_
11. skin_face silhouette overlap 0.56; render area +18%  _(severity 2.9, region)_
12. hoodie silhouette overlap 0.58; render area +11%  _(severity 2.8, region)_
13. backpack fuzz / fibre texture -58% vs reference  _(severity 2.5, texture)_
14. ear tops (ear_top_L) hidden in the render but visible in the reference (3 of 5 views)  _(severity 2.5, visibility)_
15. backpack colour dE00 9.4 (render lighter by 4 L*, more saturated by 3 C*, hue shifted 47 deg towards red/magenta); luma-matched dE00 6.8  _(severity 2.3, colour)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
