# T-094: e907 exchange re-rendered with boy 2.1.0 and girl 0.12.0

| file | what |
|---|---|
| [t094_exchange_strip.jpg](t094_exchange_strip.jpg) | T-095 beats f18, f36, **f48** (accepted frame: both hands share the cup), f53. Top: current boy 2.0.0 / girl 0.11.0 (frames from T-095's own movie). Bottom: boy 2.1.0 / girl 0.12.0. Same shot, shot camera, Cycles 10 spp, 640×360 |
| [t094_exchange_shot_camera.mp4](t094_exchange_shot_camera.mp4) | the whole shot f1–f66 with the new versions, 24 fps, Cycles 10 spp, 640×360 (same settings as T-095's movie) |
| [shot.scene.json](shot.scene.json) | evaluation copy of `episodes/e907_exchange/shots/s010/shot.scene.json`; **only `production.cast` changed**: explicit `version_dir` of 2.1.0 / 0.12.0, with a `legacy_reason` that states why (the not-current versions, for the owner's review) |
| [make_strip.py](make_strip.py) | builds the strip from the run_shot frames and T-095's movie |

The committed e907 cast is unchanged (`"version": "current"`, still boy 2.0.0 / girl 0.11.0).

Command: `python3 pipeline/production/run_shot.py --shot docs/evaluation/characters/T-094/exchange/shot.scene.json
--blender <bpy 5.3 wrapper> --samples 10 --video` (output in the ignored `exchange/build/`): prepare (published
masters, engine packages), bake with no engine warnings, render 66 frames, encode. Times: export 10 s per
character, bake 2.3 s, Blender 1501 s (setup 322 s, render 1178 s, about 18 s per frame on 4 CPU cores).

## Acting profiles (T-097-boy, T-097-girl)
Both merged into main at 01:56Z. This branch merged `origin/main` (659b6a9) and the engine was rebuilt before the
final render, so the profiles are in. **They do not change this shot.** The bake is identical to a first render made
without them: all 528 frame-data arrays are equal. The reason: the acting work plays reactions from scene `events`
(T-097D), and e907 s010 has none. Its beats are the T-095 timed actions. The frames differ only by render noise.
Driving the exchange from events would be a shot change outside T-094 (the e907 shot is read-only here).

## What the strip shows (new versions vs current)
- **Readability is kept**, at the T-095 accepted frame f48 and the other beats: both faces, his eyes under the
  fringe (now with the heavy sleepy lids), both lenses of her glasses, the cup between the hands. No new
  interpenetration is visible.
- **Boy:** a fuller, wider hair outline with the fringe at the brows; navy backpack straps; felt drawstrings.
- **Girl:** gathered blue-grey scrunchie; centre-parted swept sections; rounder face. Her single flower sits at the
  back of the bun, so it is not visible from this camera. The current version shows a flower there.
- **Not measured:** head-to-head clearance with the wider boy hair. The T-095 measurement tool uses the package
  meshes, and I did not rerun it. In the frames, the heads and hair stay visibly apart.
