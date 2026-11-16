# Fidelity report: boy_yellow_hoodie

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json` -> `<out>/build/boy_yellow_hoodie_compare.blend` + `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json` (variant: compare)
- Views: val27_front, val27_threequarter_right, val27_side_right, val27_back, val27_back_threequarter
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 64.5 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.25) | 71 | figure IoU 0.855 |
| regions (weight 0.15) | 70 | mean region IoU 0.696 |
| landmarks (weight 0.20) | 77 | mean error 0.070 head heights |
| proportions (weight 0.15) | 46 | mean relative error 16.2% |
| colour (weight 0.15) | 53 | mean dE00 9.5 |
| texture (weight 0.10) | 62 | mean abs log2 ratio 0.57 |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.846 | 0.058 | [sheet](sheets/val27_front.png) |
| val27_threequarter_right | 0.859 | 0.076 | [sheet](sheets/val27_threequarter_right.png) |
| val27_side_right | 0.857 | 0.077 | [sheet](sheets/val27_side_right.png) |
| val27_back | 0.855 | 0.071 | [sheet](sheets/val27_back.png) |
| val27_back_threequarter | 0.859 | 0.070 | [sheet](sheets/val27_back_threequarter.png) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 36% too short relative to height  _(severity 7.1, proportion)_
2. hair width at the temples (eye level) -71%  _(severity 7.1, proportion)_
3. eyes silhouette overlap 0.02; render area -39%  _(severity 6.5, region)_
4. skin_limbs silhouette overlap 0.13; render area -67%  _(severity 5.8, region)_
5. backpack silhouette overlap 0.18; render area -37%  _(severity 5.5, region)_
6. skin face colour dE00 21.5 (render darker by 23 L*, more saturated by 12 C*); luma-matched dE00 5.6  _(severity 5.4, colour)_
7. eyes 24% too small (width relative to head height)  _(severity 4.7, proportion)_
8. eye area 41% too small relative to head height squared  _(severity 4.1, proportion)_
9. arms 20% too short relative to height  _(severity 4.1, proportion)_
10. skin_face silhouette overlap 0.43; render area +2%  _(severity 3.8, region)_
11. hoodie colour dE00 14.5 (render darker by 16 L*, more saturated by 7 C*); luma-matched dE00 3.5  _(severity 3.6, colour)_
12. trousers fuzz / fibre texture -68% vs reference  _(severity 3.3, texture)_
13. hoodie fuzz / fibre texture -67% vs reference  _(severity 3.2, texture)_
14. backpack fuzz / fibre texture -66% vs reference  _(severity 3.1, texture)_
15. ear tops (ear_top_R) hidden in the render but visible in the reference (4 of 5 views)  _(severity 3.0, visibility)_

## Suggested spec corrections (suggestions only, never applied)

- `proportions.eye_radius_m`: 0.037 -> **0.05127** (eye_width_to_head render/reference 0.76 (median over views))
- `proportions.eye_x_m`: 0.064 -> **0.07281** (eye_spacing_to_head render/reference 0.87 (median over views))
- `materials.albedo_srgb.hoodie`: [173, 118, 16] -> **[211, 162, 74]** (garment:hoodie dE00 14.5 (luma-matched 3.5); mean Lab shift [15.7, -4.8, -5.7] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.albedo_srgb.trousers`: [8, 7, 7] -> **[21, 17, 18]** (garment:trousers dE00 3.1 (luma-matched 2.7); mean Lab shift [3.4, 2.0, -0.4] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.albedo_srgb.hair`: [14, 7, 7] -> **[27, 20, 21]** (hair dE00 3.8 (luma-matched 1.7); mean Lab shift [4.8, 1.3, 0.0] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.albedo_srgb.skin`: [181, 107, 70] -> **[218, 154, 125]** (skin_face dE00 21.5 (luma-matched 5.6); skin_limbs dE00 6.3 (luma-matched 4.2); mean Lab shift [16.4, -5.8, -8.3] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
