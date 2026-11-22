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

## Close-ups (s010 front wide, 8 spp, 640x360 source)

`boy_s010_f42_f44_f46_eyes.png`: scene frames 42 (Blink 0.01, open), 44 (1.0), 46 (0.68). Both lids close and open together
(f44 both shut, f46 both arcs part-open). `s010_f42_f44_s030_f80_f82_overview.png`: the same frames plus s030 f80 / f82 (side-on).

## Side finding (not a blink): the eyes are not parallel on near targets

At f42 the left eye shows its iris and the right eye reads as all white. The baked eye bones (`eye.L` vs `eye.R`, skin rotations)
differ by 13-16 degrees in yaw on every visible frame of s010 (look at the sheet / the girl): the eyes converge on a near
point. This is gaze, not blink, and not in this task's write-set (engine/anim/animation.* is T-190, gaze limits live elsewhere);
reported to the supervisor as the other candidate for "the eyes look out of sync".

## Guard test

`tests/test_blink_schedule.cpp`: "blink symmetry: automatic blinks close both eyes together (T-192)" (every frame of a 60 s run,
schedule off and on: Blink.L == Blink.R, LeftEyeClosed == RightEyeClosed, EyeSquint.L == EyeSquint.R, and the automatic blink
leaves Blink.L / Blink.R at 0) and "a deliberate wink is still possible" (an explicit `who/expr.Blink.R` track gives R = 1, L = 0).
