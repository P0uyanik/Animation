# Contact audit: rel_off/shot.blend

Frames 1-208 step 2 (104 measured, 3 characters: boy_yellow_hoodie, girl_auburn_bun_glasses, girl_white_hair_blue_dress); limit 1.0 mm, pops > 5.0 mm; snap frames []; 5090.6 s; sha256 b16c160c59e86ada.

| class | entries > limit (all) | calm | max mm | worst | depth pops |
|---|---|---|---|---|---|
| hair | 208 / 312 | 208 / 312 | 109.53 | f25 girl_auburn_bun_glasses hair_own hair_ringlets_side_00 > own:body:body_skin.001 | 0 (max 0.0) |
| hair_own | 208 / 312 | 208 / 312 | 109.53 | f25 girl_auburn_bun_glasses hair_ringlets_side_00 > own:body:body_skin.001 | 1705 (max 93.19) |
| hair_other | 66 / 312 | 66 / 312 | 91.35 | f29 girl_auburn_bun_glasses hair_ringlets_outer_00 > boy_yellow_hoodie:garment:garment.hoodie.main | 147 (max 74.28) |
| hair_prop | 38 / 312 | 38 / 312 | 73.39 | f79 girl_auburn_bun_glasses hair_ringlets_side_00 > prop::prop.boat | 36 (max 73.39) |
| hair_set | 112 / 312 | 112 / 312 | 58.39 | f25 girl_auburn_bun_glasses hair_ringlets_back_06 > set::prop.table_top | 43 (max 58.39) |
| garment_body | 311 / 312 | 311 / 312 | 40.91 | f51 girl_auburn_bun_glasses garment.blouse.main > own:body:garment.collider.body_skin.001 | 92 (max 32.86) |
| body_body | 38 / 312 | 38 / 312 | 58.03 | f17 boy_yellow_hoodie hand.R.002 > girl_auburn_bun_glasses:body:garment.collider.body_skin.001 | 52 (max 58.03) |
| hand_prop | 66 / 312 | 66 / 312 | 20.41 | f57 girl_auburn_bun_glasses hand.L.001 > prop::prop.boat | 13 (max 19.04) |
| body_set | 312 / 312 | 312 / 312 | 62.57 | f9 boy_yellow_hoodie garment.trousers.main > set::prop.stool_boy | 133 (max 14.4) |
| glasses | 104 / 312 | 104 / 312 | 1.32 | f7 girl_auburn_bun_glasses hair_ringlets_side_00 > own:glasses:glasses_lens | 0 (max 0.0) |
| known:rigid hair in own head (T-191) | 45 / 312 | 45 / 312 | 52.29 | f207 boy_yellow_hoodie hair_cap.002 > own:body:body_skin.002 | 12 (max 42.23) |
| staging_hair | 62 / 312 | 62 / 312 | 77.55 | f79 girl_auburn_bun_glasses hair_fringe.001 > boy_yellow_hoodie:body:body_skin.002 | 87 (max 73.03) |

`hair` = the worst of hair_own / hair_other / hair_prop / hair_set per frame and character (T-194 headline); staging_hair, glasses and known:* are apart.
