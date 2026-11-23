# T-221 round 1: set light rigs (T-196 Q4)

Branch `t-221-claude-set-lighting`, input `6029c6e` (merged main `440cdbb` for the bake_package write-set).
Blender: bpy 5.3.0 Python module (tools/bpy_blender.py wrapper), Cycles CPU, 4 vCPU container.

## Target
A set names a Blender light rig (`blender_light_rig`), a shot can pick another by name (`x_light_rig`, or
`shot_render --light-rig`); the engine lights stay for engine previews. Opt-in, no-rig renders unchanged.
Starting rig `water_table_corner_window` = today's translated look. Format: docs/PRODUCTION_PIPELINE.md
"Lighting: set light rigs".

## Results
| check | result |
|---|---|
| no-rig identity, e912 s020 f100, main vs branch | pixel-identical (pixel sha 5ff9b35d4b406b96 both); Blender light/world/camera fingerprint identical; `identity.json` |
| preview e907 s010 + water_table_corner f48, 640x360 16 spp, final720_look | engine 97.2 % px identical to rig, max 1/255, PSNR 68.3 dB; `t221_preview_f48_engine_vs_rig.jpg` |
| strict same frame, 1280x720 128 spp, final720_look | 96.9 % px identical, max 5/255, PSNR 67.8 dB; render 327 s (engine) vs 332 s (rig); `t221_strict_f48_engine_vs_rig.jpg` |

Note: the preview ran with the first dump of the rig (6 decimals); the strict run with the committed file (6 significant
digits). Both renders are visually identical (sheet read as two 1024 px crops).

## How it was run
```
python3 pipeline/production/sets.py apply --set content/sets/water_table_corner.set.json \
    --shot episodes/e907_exchange/shots/s010/shot.scene.json --out content/sets/build/e907_s010_rig/shot.scene.json
# engine variant: the same file plus top-level "x_light_rig": "engine" in content/sets/build/e907_s010_engine/
python3 pipeline/production/run_shot.py --shot content/sets/build/e907_s010_<engine|rig>/shot.scene.json --blender blender \
    --frames 48-48 --run-dir preview                                   # preview
    --frames 48-48 --resolution 1280 720 --samples 128 --run-dir strict  # strict
python3 tools/review/shot_sheet.py docs/evaluation/rendering/T-221/<preview|strict>_sheet.json
# rig generation: set_lights_blender.py dump --blend <engine run>/render/shot.blend --id water_table_corner_window
```
`content/sets/build/` is git-ignored (not committed).

## Open
- No HDRI rig in the repo yet (format, build, dump and packaging are tested with a synthetic .hdr only).
- Rigs are JSON, not saved .blend collections; `dump` is the bridge from a Blender-lit scene.
- No light linking / per-object visibility (T-098L finding 4) in the format yet.
