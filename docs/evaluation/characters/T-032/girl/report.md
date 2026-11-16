# Fidelity report: girl_auburn_bun_glasses

**The score and the numbers support, but never replace, visual judgement.** Review the side-by-side sheets (`sheets/`) before acting on any number.

- Build: `assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json` -> `<out>/build/girl_auburn_bun_glasses_master.blend` (variant: master)
- Views: sheet30_front, sheet30_front_left, sheet30_left, sheet30_back_right, sheet30_back
- Render: groom_turnaround.py, character_neutral/1, 640 px, 32 samples

## Fidelity score: 63.0 / 100

| part | sub-score | measure |
|---|---|---|
| silhouette (weight 0.25) | 59 | figure IoU 0.794 |
| regions (weight 0.15) | 57 | mean region IoU 0.566 |
| landmarks (weight 0.20) | 73 | mean error 0.081 head heights |
| proportions (weight 0.15) | 64 | mean relative error 10.9% |
| colour (weight 0.15) | 51 | mean dE00 9.8 |
| texture (weight 0.10) | 80 | mean abs log2 ratio 0.30 |

## Per view

| view | figure IoU | landmark error (head heights) | sheet |
|---|---|---|---|
| sheet30_front | 0.824 | 0.039 | [sheet](sheets/sheet30_front.png) |
| sheet30_front_left | 0.809 | 0.070 | [sheet](sheets/sheet30_front_left.png) |
| sheet30_left | 0.739 | 0.070 | [sheet](sheets/sheet30_left.png) |
| sheet30_back_right | 0.745 | 0.133 | [sheet](sheets/sheet30_back_right.png) |
| sheet30_back | 0.856 | 0.092 | [sheet](sheets/sheet30_back.png) |

## Largest differences (ranked)

1. hair_accessory silhouette overlap 0.16; render area -17%  _(severity 5.6, region)_
2. arms 26% too short relative to height  _(severity 5.1, proportion)_
3. skin face colour dE00 19.8 (render darker by 23 L*, less saturated by 8 C*); luma-matched dE00 5.4  _(severity 5.0, colour)_
4. hair accessory colour dE00 19.2 (render darker by 3 L*, less saturated by 5 C*, hue shifted 54 deg towards yellow/green); luma-matched dE00 7.2  _(severity 4.8, colour)_
5. glasses silhouette overlap 0.34; render area -7%  _(severity 4.4, region)_
6. skin_limbs silhouette overlap 0.37; render area -21%  _(severity 4.2, region)_
7. overall silhouette 21% too narrow relative to height  _(severity 4.2, proportion)_
8. skin_face silhouette overlap 0.37; render area -8%  _(severity 4.2, region)_
9. eyes 20% too small (width relative to head height)  _(severity 4.1, proportion)_
10. blouse silhouette overlap 0.40; render area +29%  _(severity 4.0, region)_
11. eyes silhouette overlap 0.44; render area -26%  _(severity 3.8, region)_
12. vest silhouette overlap 0.48; render area +1%  _(severity 3.4, region)_
13. blouse fuzz / fibre texture +223% vs reference  _(severity 3.4, texture)_
14. hands off by 0.16 head heights  _(severity 3.2, landmark)_
15. shorts silhouette overlap 0.55; render area -27%  _(severity 3.0, region)_

## Suggested spec corrections (suggestions only, never applied)

- `face.eyes.radius_m`: 0.036 -> **0.04498** (eye_width_to_head render/reference 0.80 (median over views))
- `body.params.eyes.x`: 0.05979 -> **0.06615** (eye_spacing_to_head render/reference 0.90 (median over views))
- `body.params.arm.upper_len`: 0.09794 -> **0.13977** (arm_length render/reference 0.74 (median over views))
- `body.params.arm.fore_len`: 0.08763 -> **0.12506** (arm_length render/reference 0.74 (median over views))
- `body.params.shoulder.joint_x`: 0.10103 -> **0.11388** (shoulder_width render/reference 0.88 (median over views))
- `clothing.garments[0].material.base_color_srgb`: [214, 210, 210] -> **[224, 221, 221]** (garment:blouse dE00 7.5 (luma-matched 1.0); mean Lab shift [3.8, -0.1, -0.4] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[3].material.base_color_srgb`: [104, 58, 34] -> **[111, 57, 26]** (garment:boots dE00 4.2 (luma-matched 3.9); mean Lab shift [0.8, 3.4, 6.0] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[2].material.base_color_srgb`: [110, 114, 103] -> **[102, 107, 97]** (garment:shorts dE00 3.4 (luma-matched 1.1); mean Lab shift [-2.8, -0.7, -0.3] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `clothing.garments[1].material.base_color_srgb`: [150, 94, 96] -> **[142, 82, 86]** (garment:vest dE00 4.2 (luma-matched 1.9); mean Lab shift [-4.2, 2.3, -0.2] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.assignments.hair.base_color_srgb`: [86, 54, 44] -> **[83, 31, 19]** (hair dE00 10.5 (luma-matched 8.9); mean Lab shift [-6.7, 10.2, 8.0] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))
- `materials.assignments.skin.base_color_srgb`: [202, 176, 169] -> **[255, 222, 209]** (skin_face dE00 19.8 (luma-matched 5.4); skin_limbs dE00 9.5 (luma-matched 1.4); mean Lab shift [17.2, 2.8, 3.7] (first-order; a large lightness share points at lighting/exposure as much as at the base colour; re-measure))

Method and definitions: docs/CHARACTER_FIDELITY.md. Every number: fidelity.json.
