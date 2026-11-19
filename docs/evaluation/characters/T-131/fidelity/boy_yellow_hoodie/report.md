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

## Fidelity score: 67.3 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 67 | figure IoU 0.834 |
| regions (weight 0.10) | 60 | mean region IoU 0.603 |
| landmarks (weight 0.15) | 84 | mean error 0.049 head heights |
| proportions (weight 0.10) | 68 | mean relative error 9.5% |
| colour (weight 0.10) | 69 | mean dE00 6.3 |
| texture (weight 0.05) | 59 | mean abs log2 ratio 0.62 |
| hair (weight 0.15) | 65 | shape 70, volume 54, face_cover 84, outline 46, strand 79, relief 58 |
| skin (weight 0.10) | 52 | skin_face dE00 6.1, shade chroma -7.4, blush a* P90 -7.6; skin_limbs dE00 18.2, shade chroma -8.3, blush a* P90 -9.8 |
| face (weight 0.05) | 73 | lid_dL +5.5, lid_dC +1.8, blush_da +2.6 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.855 | 0.039 | [sheet](sheets/val27_front.jpg) |
| val27_threequarter_right | 0.851 | 0.051 | [sheet](sheets/val27_threequarter_right.jpg) |
| val27_side_right | 0.803 | 0.072 | [sheet](sheets/val27_side_right.jpg) |
| val27_back | 0.822 | 0.029 | [sheet](sheets/val27_back.jpg) |
| val27_back_threequarter | 0.840 | 0.055 | [sheet](sheets/val27_back_threequarter.jpg) |

## Largest differences (ranked)

1. backpack silhouette overlap 0.14; render area -41%  _(severity 5.7, region)_
2. hair width at the temples (eye level) -55%  _(severity 5.5, proportion)_
3. eyes 27% too small (width relative to head height)  _(severity 5.5, proportion)_
4. overall silhouette 27% too wide relative to height  _(severity 5.5, proportion)_
5. eyes silhouette overlap 0.19; render area -18%  _(severity 5.4, region)_
6. skin limbs colour dE00 18.2 (render lighter by 18 L*, less saturated by 4 C*, hue shifted 13 deg towards yellow/green); luma-matched dE00 5.0  _(severity 4.5, colour)_
7. skin_limbs silhouette overlap 0.33; render area -29%  _(severity 4.5, region)_
8. trousers fuzz / fibre texture -71% vs reference  _(severity 3.6, texture)_
9. skin face colour dE00 13.8 (render hue shifted 10 deg towards yellow/green); luma-matched dE00 3.4  _(severity 3.4, colour)_
10. skin limbs fuzz / fibre texture -67% vs reference  _(severity 3.2, texture)_
11. skin_face silhouette overlap 0.57; render area +18%  _(severity 2.9, region)_
12. hoodie silhouette overlap 0.58; render area +11%  _(severity 2.8, region)_
13. skin limbs warmth / blush (a* P90) -9.8 (weaker)  _(severity 2.5, skin)_
14. backpack fuzz / fibre texture -57% vs reference  _(severity 2.4, texture)_
15. backpack colour dE00 9.2 (render lighter by 4 L*, more saturated by 3 C*, hue shifted 47 deg towards red/magenta); luma-matched dE00 6.8  _(severity 2.3, colour)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
