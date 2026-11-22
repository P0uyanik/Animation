# T-202: face close-ups of the current releases next to the reference faces

Sheets only, no analysis. Three sheets, one per character, one row per (view, reference), each row "reference | current":

| Sheet | Character, version | Rows (reference tile -> view) |
|---|---|---|
| `sheets/boy_faces.jpg` | boy_yellow_hoodie 2.3.0 | front: `val27_front`, `hero24_front`, `canon29_front`; 3/4 (yaw -35): `val27_threequarter_right`, `canon29_threequarter_left` (mirrored); side (yaw -90): `val27_side_right`, `canon29_side_left` (mirrored) |
| `sheets/girl_faces.jpg` | girl_auburn_bun_glasses 0.14.0 | front `sheet30_front`; 3/4 (yaw -45) `sheet30_front_left`; side (yaw +90) `sheet30_left`. All three are crops of upload `ref_30`. |
| `sheets/third_faces.jpg` | girl_white_hair_blue_dress 0.1.0 | front: `id01_full` (upload 01 `01_identity_front`), `f14_head_front` (upload 14), `s02_front` (upload 02 `02_character_sheet`); 3/4 (yaw -30): `f14_head_3q`, `s02_front_left`; side (yaw -90): `f14_head_side`, `s02_left` (mirrored) |

Sheets are 2000 px wide (two 1000 px tiles). Tile labels name the reference file and the character, version, view and yaw.
Versions are the `approved` pointers in `assets/characters/<id>/versions/index.json` (boy 2.3.0, girl 0.14.0, third 0.1.0).

Files: `renders/<character>_<version>_<yaw>.png` are the current-release crops at 1024 x 1024 (100 %, unscaled);
`crops/<char>_<view>_<reference>.png` are the reference tiles as used (square head crops, mirrored where labelled; the sheet scales both to 1000 px).

## Render settings

- Masters: `assets/characters/<id>/versions/<version>/<id>_master.blend` (A-pose, no pose applied; head unaffected).
- Neutral expression: every `face_*` rig property set to 0 (the master's rest face). No expression shape keys.
- Cycles, CPU, **16 samples**, OpenImageDenoise (lowered from the 64 normally used: 9 views on 4 cores; no view skipped), seed 0,
  threads AUTO (determinism pins 1 thread; this is a review render, not a build).
- Camera as T-155 `crops.py`: 70 mm lens, 36 mm vertical sensor, light `character_neutral/1` (`render_calibration`), light oriented to the
  camera, square 1024 px. The reference index gives 70 mm for the references (`focal_mm_estimate`), elevation 5-6 deg; renders use
  elevation 6 deg (boy) / 5 deg (girl, third).
- Yaw convention as the reference index: 0 = camera in front, +90 = camera on the character's left.
- Head framing (target z, frame height): boy (0, 0, 0.91) 0.58 m; girl (0, 0, 0.84) 0.66 m; third (0, 0, 0.79) 0.56 m. Chosen so hair top and
  collar fit as in the reference tiles.

## Reference tiles

Head crops of `assets/characters/<id>/references/views/<file>` (boxes in `compose.py`), padded to a square with the crop border colour.
The sources are small (99 to 590 px wide), so the reference tiles are upscaled and soft; `hero24_front` keeps its label text.
Left-facing references are mirrored (labelled) so every row faces the same way as the render. `sheet30_front`, `id01_full`,
`f14_head_front` and `s02_front` show a smile or open mouth; the renders are the neutral face.

## Commands (repository root)

    docs/evaluation/characters/T-202/render_all.sh        # 9 renders into renders/ (face_views.py, derived from T-155 crops.py)
    python3 docs/evaluation/characters/T-202/compose.py   # sheets/ and crops/
