# Contact audit: rel_on/shot.blend

Frames 1-208 step 2 (104 measured, 3 characters: boy_yellow_hoodie, girl_auburn_bun_glasses, girl_white_hair_blue_dress); limit 1.0 mm, pops > 5.0 mm; snap frames []; 4882.0 s; sha256 14fd04c2fb85fee5.

| class | entries > limit (all) | calm | max mm | worst | depth pops |
|---|---|---|---|---|---|
| hair | 212 / 312 | 212 / 312 | 88.16 | f23 girl_auburn_bun_glasses hair_own hair_ringlets_side_00 > own:body:body_skin.001 | 0 (max 0.0) |
| hair_own | 208 / 312 | 208 / 312 | 88.16 | f23 girl_auburn_bun_glasses hair_ringlets_side_00 > own:body:body_skin.001 | 1740 (max 83.63) |
| hair_other | 64 / 312 | 64 / 312 | 53.64 | f157 girl_auburn_bun_glasses hair_ringlets_side_00 > boy_yellow_hoodie:garment:garment.hoodie.main | 121 (max 49.58) |
| hair_prop | 30 / 312 | 30 / 312 | 59.77 | f75 girl_auburn_bun_glasses hair_ringlets_side_00 > prop::prop.boat | 40 (max 59.77) |
| hair_set | 4 / 312 | 4 / 312 | 46.07 | f33 girl_auburn_bun_glasses hair_ringlets_side_00 > set::prop.table_top | 15 (max 46.07) |
| garment_body | 311 / 312 | 311 / 312 | 40.91 | f51 girl_auburn_bun_glasses garment.blouse.main > own:body:garment.collider.body_skin.001 | 92 (max 32.86) |
| body_body | 38 / 312 | 38 / 312 | 58.03 | f17 boy_yellow_hoodie hand.R.002 > girl_auburn_bun_glasses:body:garment.collider.body_skin.001 | 52 (max 58.03) |
| hand_prop | 66 / 312 | 66 / 312 | 20.41 | f57 girl_auburn_bun_glasses hand.L.001 > prop::prop.boat | 13 (max 19.04) |
| body_set | 312 / 312 | 312 / 312 | 62.57 | f9 boy_yellow_hoodie garment.trousers.main > set::prop.stool_boy | 133 (max 14.4) |
| glasses | 104 / 312 | 104 / 312 | 1.32 | f7 girl_auburn_bun_glasses hair_ringlets_side_00 > own:glasses:glasses_lens | 0 (max 0.0) |
| known:rigid hair in own head (T-191) | 44 / 312 | 44 / 312 | 52.29 | f207 boy_yellow_hoodie hair_cap.002 > own:body:body_skin.002 | 12 (max 42.23) |
| staging_hair | 32 / 312 | 32 / 312 | 77.55 | f79 girl_auburn_bun_glasses hair_fringe.001 > boy_yellow_hoodie:body:body_skin.002 | 52 (max 73.03) |

`hair` = the worst of hair_own / hair_other / hair_prop / hair_set per frame and character (T-194 headline); staging_hair, glasses and known:* are apart.
