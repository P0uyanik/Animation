# Fidelity report: boy_yellow_hoodie

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json` -> `<out>/build/boy_yellow_hoodie_compare.blend` + `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json` (variant: compare)
- Views: val27_front, val27_threequarter_right, val27_side_right, val27_back, val27_back_threequarter
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 66.4 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 67 | figure IoU 0.836 |
| regions (weight 0.10) | 65 | mean region IoU 0.651 |
| landmarks (weight 0.15) | 80 | mean error 0.061 head heights |
| proportions (weight 0.10) | 61 | mean relative error 11.8% |
| colour (weight 0.10) | 60 | mean dE00 8.0 |
| texture (weight 0.05) | 59 | mean abs log2 ratio 0.62 |
| hair (weight 0.15) | 65 | shape 75, volume 38, face_cover 56, outline 91, strand 65, relief 64 |
| skin (weight 0.10) | 56 | skin_face dE00 24.0, shade chroma +2.3, blush a* P90 +5.6; skin_limbs dE00 5.9, shade chroma -0.5, blush a* P90 +1.8 |
| face (weight 0.05) | 83 | lid_dL -1.5, lid_dC -0.1, blush_da +1.1 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.838 | 0.047 | [sheet](sheets/val27_front.png) |
| val27_threequarter_right | 0.847 | 0.067 | [sheet](sheets/val27_threequarter_right.png) |
| val27_side_right | 0.838 | 0.071 | [sheet](sheets/val27_side_right.png) |
| val27_back | 0.814 | 0.056 | [sheet](sheets/val27_back.png) |
| val27_back_threequarter | 0.842 | 0.062 | [sheet](sheets/val27_back_threequarter.png) |

## Largest differences (ranked)

1. hair width at the temples (eye level) -70%  _(severity 7.0, proportion)_
2. visible gap between the legs (crotch to sole) 35% too short relative to height  _(severity 6.9, proportion)_
3. eyes silhouette overlap 0.10; render area -37%  _(severity 6.0, region)_
4. backpack silhouette overlap 0.15; render area -36%  _(severity 5.6, region)_
5. skin_limbs silhouette overlap 0.16; render area -64%  _(severity 5.6, region)_
6. skin face colour dE00 20.7 (render darker by 22 L*, more saturated by 13 C*); luma-matched dE00 5.7  _(severity 5.2, colour)_
7. eyes 19% too small (width relative to head height)  _(severity 3.9, proportion)_
8. eye area 37% too small relative to head height squared  _(severity 3.7, proportion)_
9. arms 19% too short relative to height  _(severity 3.7, proportion)_
10. hoodie fuzz / fibre texture -72% vs reference  _(severity 3.6, texture)_
11. hoodie colour dE00 14.3 (render darker by 15 L*, more saturated by 8 C*); luma-matched dE00 3.5  _(severity 3.6, colour)_
12. trousers fuzz / fibre texture -70% vs reference  _(severity 3.5, texture)_
13. backpack fuzz / fibre texture -68% vs reference  _(severity 3.3, texture)_
14. skin_face silhouette overlap 0.52; render area +7%  _(severity 3.2, region)_
15. ear tops (ear_top_R) hidden in the render but visible in the reference (4 of 5 views)  _(severity 3.0, visibility)_

## Suggested spec corrections (suggestions only, never applied)

- none

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
