# Contact audit: cand_on/shot.blend

Frames 1-208 step 2 (104 measured, 3 characters: boy_yellow_hoodie, girl_auburn_bun_glasses, girl_white_hair_blue_dress); limit 1.0 mm, pops > 5.0 mm; snap frames []; 3976.0 s; sha256 75450e682a1357bc.

| class | entries > limit (all) | calm | max mm | worst | depth pops |
|---|---|---|---|---|---|
| hair | 158 / 312 | 158 / 312 | 33.81 | f115 girl_auburn_bun_glasses hair_own hair_cap.001 > own:body:body_skin.001 | 0 (max 0.0) |
| hair_own | 154 / 312 | 154 / 312 | 33.81 | f115 girl_auburn_bun_glasses hair_cap.001 > own:body:body_skin.001 | 30 (max 29.2) |
| hair_other | 10 / 312 | 10 / 312 | 3.82 | f133 girl_auburn_bun_glasses hair_ringlets_back_00 > boy_yellow_hoodie:garment:garment.hoodie.main | 0 (max 0.0) |
| hair_prop | 0 / 312 | 0 / 312 | 0.0 |  | 0 (max 0.0) |
| hair_set | 0 / 312 | 0 / 312 | 0.0 |  | 0 (max 0.0) |
| garment_body | 311 / 312 | 311 / 312 | 40.91 | f51 girl_auburn_bun_glasses garment.blouse.main > own:body:garment.collider.body_skin.001 | 92 (max 32.86) |
| body_body | 38 / 312 | 38 / 312 | 58.03 | f17 boy_yellow_hoodie hand.R.002 > girl_auburn_bun_glasses:body:garment.collider.body_skin.001 | 52 (max 58.03) |
| hand_prop | 66 / 312 | 66 / 312 | 20.41 | f57 girl_auburn_bun_glasses hand.L.001 > prop::prop.boat | 13 (max 19.04) |
| body_set | 312 / 312 | 312 / 312 | 62.57 | f9 boy_yellow_hoodie garment.trousers.main > set::prop.stool_boy | 133 (max 14.4) |
| glasses | 104 / 312 | 104 / 312 | 1.3 | f15 girl_auburn_bun_glasses hair_cap.001 > own:glasses:glasses | 0 (max 0.0) |
| known:rigid hair in own head (T-191) | 44 / 312 | 44 / 312 | 52.29 | f207 boy_yellow_hoodie hair_cap.002 > own:body:body_skin.002 | 12 (max 42.23) |
| staging_hair | 31 / 312 | 31 / 312 | 77.55 | f79 girl_auburn_bun_glasses hair_fringe.001 > boy_yellow_hoodie:body:body_skin.002 | 45 (max 73.03) |

`hair` = the worst of hair_own / hair_other / hair_prop / hair_set per frame and character (T-194 headline); staging_hair, glasses and known:* are apart.
