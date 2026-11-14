# Production pipeline: from character sources to a rendered shot (M3.2, 2026-11-14)

**Render path (TD-42):**
- **The C++ engine animates:** actions, life layer, IK, expressions, jaw, blink timing.
- **Blender renders:** Cycles, with the characters' own materials.
- The engine's path tracer stays for previews and the existing image regressions.

```
character sources            engine packages           C++ engine                 Blender
(published version dir   ->  export_engine.py      ->  plush-render --bake    ->  shot_render.py (Cycles)
 or spec, built)             (cached by master sha)    bake.json                  frames, shot.blend, shot.mp4
```

## One command per shot
```bash
python3 pipeline/production/run_shot.py --shot episodes/e000_pilot/shots/s010/shot.scene.json --blender <blender> --video
```

The shot file is an engine scene (`plush.scene`): characters, actions, tracks, camera, lights and props. It also has
a `production` block naming each cast member's source:
- `version_dir`: a published store version, manifest-checked;
- `spec`: an unpublished build, made in the shot's `build/` folder and never published.

Everything is written to `<shot>/build/` (ignored by git). Masters and packages are cached by content hashes.

## Interchange format `plush.shot_bake/1` (`engine/scene/shot_bake.{h,cpp}`)
- **Static:**
  - fps and frame range;
  - render size and exposure;
  - lights (sun, rect, sky);
  - box props with colour;
  - per character: package path, engine bone names, morph names.
- **Per frame:**
  - camera (position, target, up, focal length, sensor, f-stop, focus distance);
  - per character: skinning matrices (engine axes, column-major) and morph control weights (the animated weight,
    with life-layer blinks applied).
- Characters that are not imported packages (the engine's SDF characters) are listed as `supported: false`.

## Blender side (`pipeline/charsys/shot_render.py`)
- **Linking:** masters are linked through a library override (`episode.link_master`); only the rig is editable, and
  no master is ever modified.
- **Deform bones:** constraints muted in the shot; pose keyed from the skinning matrices. Bones with drivers (e.g. a
  jaw driven by facial controls) are left to their drivers.
- **Facial controls:** `face_<morph>` keyed from the control weights. The master's own drivers then produce every
  shape key, in-between and jaw rotation.
- **Camera, lights and box props** are translated from the bake. The light units are an approximate translation
  (`production.render.light_scale`).
- **Report:** the bone pose reconstruction error at the first, middle and last frame.

## Verified (pilot shot e000/s010, 120 frames, published boy 1.0.0 + unpublished girl M3.1)
- **Bone reconstruction:** at most 0.0003 mm and 0.0° for both characters.
- **Mapping:** every morph maps to a facial control.
- **Bake round trip** (C++ test): the posed meshes rebuilt from the bake equal the engine's evaluation (0 mm).
- **Timing:**
  - bake 0.2 s;
  - Blender setup and keying about 5 s;
  - Cycles 8.6 s per frame at 640×360 / 32 samples (17.9 s at 960×540).
- **Evidence:** `docs/evaluation/production/M32_s010_*` (contact sheet, mp4, run report).

## Not covered yet
- **Props:** SDF props, water and paper boats are not baked (listed as `objects_not_baked`).
- **Engine-only characters** (SDF) cannot be rendered in Blender.
- **Lights** are matched only approximately, not radiometrically.
- **No episode layer:** each shot is run on its own; there is no sequence assembly or audio.
- **Plush Studio** does not call this pipeline yet.
- **Arms:** imported characters stand in the engine's default A-pose arms (no relaxed idle pose for them).
