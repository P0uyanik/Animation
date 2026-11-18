# Fidelity report: boy_yellow_hoodie

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0.spec.json` -> `<out>/build/boy_yellow_hoodie_compare.blend` (variant: compare)
- Hide prefixes that matched no object (val27_back): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_back_threequarter): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_front): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_side_right): backpack_body, backpack_pocket, backpack_handle
- Hide prefixes that matched no object (val27_threequarter_right): backpack_body, backpack_pocket, backpack_handle
- Views: val27_front, val27_threequarter_right, val27_side_right, val27_back, val27_back_threequarter
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 67.4 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 69 | figure IoU 0.843 |
| regions (weight 0.10) | 61 | mean region IoU 0.605 |
| landmarks (weight 0.15) | 82 | mean error 0.055 head heights |
| proportions (weight 0.10) | 60 | mean relative error 12.0% |
| colour (weight 0.10) | 73 | mean dE00 5.3 |
| texture (weight 0.05) | 71 | mean abs log2 ratio 0.43 |
| hair (weight 0.15) | 68 | shape 73, volume 71, face_cover 72, outline 43, strand 84, relief 65 |
| skin (weight 0.10) | 48 | skin_face dE00 7.3, shade chroma -8.8, blush a* P90 -8.3; skin_limbs dE00 19.3, shade chroma -9.2, blush a* P90 -10.8 |
| face (weight 0.05) | 70 | lid_dL +3.7, lid_dC +0.7, blush_da +5.5 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| val27_front | 0.868 | 0.054 | [sheet](sheets/val27_front.png) |
| val27_threequarter_right | 0.875 | 0.061 | [sheet](sheets/val27_threequarter_right.png) |
| val27_side_right | 0.806 | 0.062 | [sheet](sheets/val27_side_right.png) |
| val27_back | 0.829 | 0.043 | [sheet](sheets/val27_back.png) |
| val27_back_threequarter | 0.838 | 0.057 | [sheet](sheets/val27_back_threequarter.png) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 31% too short relative to height  _(severity 6.2, proportion)_
2. eyes 30% too small (width relative to head height)  _(severity 6.0, proportion)_
3. backpack silhouette overlap 0.13; render area -42%  _(severity 5.8, region)_
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

- `face.eyes.radius_m`: 0.042 -> **0.07146** (eye_width_to_head render/reference 0.70 (median over views))
- `body.params.eyes.x`: 0.063116 -> **0.06808** (eye_spacing_to_head render/reference 0.92 (median over views))
- `body.params.arm.upper_len`: 0.136 -> **0.14713** (arm_length render/reference 0.92 (median over views))
- `body.params.arm.fore_len`: 0.127 -> **0.1374** (arm_length render/reference 0.92 (median over views))
- `body.params.shoulder.joint_x`: 0.109 -> **0.11685** (shoulder_width render/reference 0.92 (median over views))
- `clothing.garments[3].material.base_color_srgb`: [68, 56, 68] -> **[47, 38, 50]** (accessory:backpack dE00 6.6 (luma-matched 1.6); mean Lab shift [-8.6, -0.7, -0.9] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[0].material.base_color_srgb`: [204, 152, 62] -> **[217, 166, 87]** (garment:hoodie dE00 5.0 (luma-matched 2.3); mean Lab shift [5.2, -0.7, -5.3] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[2].material.base_color_srgb`: [206, 156, 70] -> **[219, 183, 131]** (garment:shoes dE00 8.3 (luma-matched 6.3); mean Lab shift [8.8, -3.6, -19.6] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[1].material.base_color_srgb`: [38, 34, 34] -> **[32, 26, 28]** (garment:trousers dE00 3.6 (luma-matched 2.0); mean Lab shift [-3.5, 1.3, -0.8] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.assignments.skin.base_color_srgb`: [236, 190, 166] -> **[230, 172, 154]** (skin_face dE00 13.8 (luma-matched 3.5); skin_limbs dE00 19.3 (luma-matched 5.2); mean Lab shift [-5.2, 5.7, -0.6] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.albedo_srgb.skin`: [236, 190, 166] -> **[230, 172, 154]** (skin_face dE00 13.8 (luma-matched 3.5); skin_limbs dE00 19.3 (luma-matched 5.2); mean Lab shift [-5.2, 5.7, -0.6] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
