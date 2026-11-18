# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.11.0.spec.json` -> `<out>/build/girl_auburn_bun_glasses_master.blend` + `assets/characters/girl_auburn_bun_glasses/spec/candidates/T-089/girl_face3.override.json` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 62.5 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.20) | 59 | figure IoU 0.795 |
| regions (weight 0.10) | 44 | mean region IoU 0.436 |
| landmarks (weight 0.15) | 71 | mean error 0.087 head heights |
| proportions (weight 0.10) | 63 | mean relative error 11.0% |
| colour (weight 0.10) | 71 | mean dE00 5.8 |
| texture (weight 0.05) | 68 | mean abs log2 ratio 0.48 |
| hair (weight 0.15) | 60 | shape 60, volume 76, face_cover 13, outline 58, strand 93, relief 60 |
| skin (weight 0.10) | 66 | skin_face dE00 11.1, shade chroma -7.5, blush a* P90 -7.4; skin_limbs dE00 4.3, shade chroma -1.2, blush a* P90 -3.5 |
| face (weight 0.05) | 67 | lid_dL +5.9, lid_dC -1.6, blush_da -2.1 (2 views) |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.810 | 0.042 | [sheet](sheets/sheet30_front.png) |
| sheet30_front_left | 0.796 | 0.075 | [sheet](sheets/sheet30_front_left.png) |
| sheet30_left | 0.742 | 0.060 | [sheet](sheets/sheet30_left.png) |
| sheet30_back_right | 0.778 | 0.146 | [sheet](sheets/sheet30_back_right.png) |
| sheet30_back | 0.852 | 0.113 | [sheet](sheets/sheet30_back.png) |

## Largest differences (ranked)

1. visible gap between the legs (crotch to sole) 33% too long relative to height  _(severity 6.5, proportion)_
2. hair_accessory silhouette overlap 0.10; render area +109%  _(severity 6.0, region)_
3. blouse silhouette overlap 0.19; render area -44%  _(severity 5.4, region)_
4. arms 26% too short relative to height  _(severity 5.2, proportion)_
5. hair covers 26% of the face that the reference shows uncovered  _(severity 5.2, hair)_
6. eyes silhouette overlap 0.24; render area -15%  _(severity 5.1, region)_
7. vest silhouette overlap 0.31; render area -34%  _(severity 4.6, region)_
8. skin_limbs silhouette overlap 0.36; render area -42%  _(severity 4.3, region)_
9. hair accessory colour dE00 16.6 (render darker by 5 L*, less saturated by 5 C*, hue shifted 127 deg towards yellow/green); luma-matched dE00 8.9  _(severity 4.1, colour)_
10. glasses silhouette overlap 0.39; render area -8%  _(severity 4.1, region)_
11. hands off by 0.18 head heights, render higher by 0.09  _(severity 3.6, landmark)_
12. blouse fuzz / fibre texture +192% vs reference  _(severity 3.1, texture)_
13. skin_face silhouette overlap 0.55; render area +20%  _(severity 3.0, region)_
14. shorts silhouette overlap 0.55; render area -21%  _(severity 3.0, region)_
15. eye spacing 14% too narrow relative to head height  _(severity 2.8, proportion)_

## Suggested spec corrections (suggestions only, never applied)

- `face.eyes.radius_m`: 0.048 -> **0.05606** (eye_width_to_head render/reference 0.86 (median over views))
- `body.params.eyes.x`: 0.05979 -> **0.06902** (eye_spacing_to_head render/reference 0.86 (median over views))
- `body.params.arm.upper_len`: 0.09794 -> **0.14** (arm_length render/reference 0.74 (median over views))
- `body.params.arm.fore_len`: 0.08763 -> **0.12527** (arm_length render/reference 0.74 (median over views))
- `body.params.shoulder.joint_x`: 0.10103 -> **0.11471** (shoulder_width render/reference 0.88 (median over views))
- `clothing.garments[0].material.base_color_srgb`: [214, 210, 210] -> **[244, 242, 244]** (garment:blouse dE00 7.1 (luma-matched 1.5); mean Lab shift [11.3, -0.7, -1.0] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[1].material.base_color_srgb`: [144, 104, 104] -> **[146, 100, 103]** (garment:vest dE00 3.7 (luma-matched 1.9); mean Lab shift [-0.7, 2.7, -0.5] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.assignments.hair.base_color_srgb`: [100, 64, 47] -> **[99, 54, 40]** (hair dE00 4.6 (luma-matched 3.8); mean Lab shift [-2.7, 4.8, 0.6] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.assignments.skin.base_color_srgb`: [238, 202, 184] -> **[244, 205, 193]** (skin_face dE00 11.1 (luma-matched 3.2); skin_limbs dE00 4.3 (luma-matched 3.6); mean Lab shift [1.6, 1.9, -2.4] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.albedo_srgb.skin`: [238, 202, 184] -> **[244, 205, 193]** (skin_face dE00 11.1 (luma-matched 3.2); skin_limbs dE00 4.3 (luma-matched 3.6); mean Lab shift [1.6, 1.9, -2.4] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
