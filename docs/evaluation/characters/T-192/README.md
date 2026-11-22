# T-192 · Boy blink sync: per-frame left/right weights (before = after: no code change yet)

Source: `plush-render` bake of e912 s010/s020/s030 on `integration/t-187` (44f9fb3), boy_yellow_hoodie 2.3.0, girl_auburn_bun_glasses 0.14.0, girl_white_hair_blue_dress 0.1.0.

## Boy, s020 blink frames (morph weights in the bake)

| scene frame | Blink | Blink.L | Blink.R | LeftEyeClosed | RightEyeClosed |
|---|---|---|---|---|---|
| 42 | 0.012 | 0.000 | 0.000 | 0.000 | 0.000 |
| 43 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 44 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 45 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 46 | 0.680 | 0.000 | 0.000 | 0.000 | 0.000 |
| 122 | 0.688 | 0.000 | 0.000 | 0.000 | 0.000 |
| 123 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 124 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 125 | 0.979 | 0.000 | 0.000 | 0.000 | 0.000 |
| 126 | 0.154 | 0.000 | 0.000 | 0.000 | 0.000 |
| 132 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 133 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 134 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 135 | 0.741 | 0.000 | 0.000 | 0.000 | 0.000 |
| 151 | 0.095 | 0.000 | 0.000 | 0.000 | 0.000 |
| 152 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 153 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 154 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 155 | 0.560 | 0.000 | 0.000 | 0.000 | 0.000 |
| 177 | 0.662 | 0.000 | 0.000 | 0.000 | 0.000 |
| 178 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 179 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 180 | 0.985 | 0.000 | 0.000 | 0.000 | 0.000 |
| 181 | 0.168 | 0.000 | 0.000 | 0.000 | 0.000 |

## Asymmetry scan (max |L-R| over every frame, every .L/.R morph pair plus LeftEyeClosed/RightEyeClosed)

| scene | white | auburn | boy |
|---|---|---|---|
| s010 | 0.0000 | 0.0000 | 0.0000 |
| s020 | 0.0000 | 0.0000 | 0.0000 |
| s030 | 0.0000 | 0.0000 | 0.0000 |

## Blender side (master 2.3.0)

- Drivers: `face_Blink` drives Blink / Blink@25/50/75 on lash.L, lash.R, lid_upper.L, lid_upper.R with the same expression; `face_Blink.L/.R`, `face_LeftEyeClosed/RightEyeClosed` drive the per-side keys.
- Shape-key geometry: Blink on lash.L = lash.R (max 0.04458 m, 232 vertices); lid_upper.L = lid_upper.R (max 0.04357 m, 1330 vertices).
- Evaluated meshes with `face_Blink` = 0 / .25 / .5 / .75 / .9 / 1: lid_upper and lash L/R z-extent and centroid equal to 1e-5 m at every value.

## Render crop

`boy_s020_f121_122_125_126_crop.png` (Blink 0, 0.69, 0.98, 0.15): head turned and pitched down, the far eye is covered by the fringe; the near eye closes and opens.
