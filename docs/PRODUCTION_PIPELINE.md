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

## Workflow contract (T-001, 2026-11-15): one contract for the command line and Plush Studio
`run_shot.py` is the only production entry point. The extensions are additive: without `--run-dir` and `--stages`,
the command behaves and writes exactly as in M3.2.

**Stages** (`--stages prepare,bake,render,encode`, default: all):
- **prepare** resolves the cast (masters, packages, `shot.resolved.scene.json`, `cast.json`) and writes
  `prepare.json`, which reports per cast member whether its master and package were cached or built.
  - It is idempotent: an unchanged repeat writes nothing to masters, packages, `assets/` or published versions.
  - The resolved scene and `cast.json` are rewritten only when their content changes.
- **bake:** the engine (`plush-render --bake`).
- **render:** Blender (`shot_render.py`).
- **encode:** mp4. Without `--stages`, encode runs only with `--video`, as before.

**Run folders** (`--run-dir <id>` gives `<shot>/build/runs/<id>/`):
- Each run folder holds that run's `bake.json`, `render/` (frames, `shot.blend`, `shot_render.json`), `shot.mp4`,
  `prepare.json`, `run_shot.json`, `logs/` and `status.json`.
- The shared cache (masters, packages, resolved scene, `cast.json`) stays in `<shot>/build/`.
- `runs/latest` (a text file holding the run id) is replaced only after a run succeeds.
- An existing run folder is never reused.

**`status.json`** (`plush.run_status/1`):
- Rewritten atomically per stage and per finished frame.
- Fields: `state` (running / done / failed / cancelled), `stage`, `stages`, `stages_done`, `frames`, `frames_done`,
  `frames_total`, `resolution`, `samples`, `light_scale`, `exposure_ev`, `error`.

**Cancel:**
- SIGTERM or SIGINT stops the current step, removes a partly written frame (a PNG without its IEND chunk), marks the
  run cancelled, and never touches earlier runs or `latest`.
- `--mark-cancelled --run-dir <id>` finalises a run whose process was killed forcibly.

**Frame numbers:** rendered files carry the shot's own frame numbers (`frame_0005.png` is frame 5).

**Tests:**
- `pipeline/production/tests/test_run_shot_workflow.py`: idempotent prepare; the status contract; cancel and
  partial frames; failure; default command-line behaviour.
- `pipeline/production/tests/compare_runs.py`: equivalence of two runs.

## Clip actions (T-002)
Shots can play shared body animation clips from `content/clips/` with the action
`{"type": "clip", "character", "clip", "start", "end", "speed", "weight", "blendIn", "blendOut", "loop", "mirror", "base"}`.
Format, retargeting and layering are described in `docs/ANIMATION_CLIPS.md`.
- **One file per clip:** the same file plays on every humanoid.
- **Retarget data:** each character's generated retarget data comes from its engine package (`retarget` block,
  `export_engine.py` `EXPORTER_VERSION` 2).
- **Package cache:** packages are cached by the master hash and the exporter version, so they are re-exported when
  the exporter changes.
- **Render path:** clip motion reaches Blender only through the existing bake (`shot_bake` / `shot_render` unchanged).
- **Shots without clip actions:** they bake exactly as before (s010 bake byte-identical with `main` for the same
  packages).
- **Test shot:** `episodes/e901_clip_test/shots/s010`.

## Plush Studio drives the workflow (T-001)
Studio orchestrates and displays. It contains no animation, bake, retargeting or rendering logic.

**Opening shots:**
- `plush-studio --shot <shot.scene.json> [--blender <exe>]`, or the shot browser in the Production panel.
- The browser lists every `episodes/*/shots/*/shot.scene.json`; there is no per-shot code.
- A prepared shot opens its resolved scene in the engine evaluator. Timeline scrubbing and playback evaluate the
  shot's actions, so the preview equals the bake (R2).

**Production panel:**
- the cast, with its source (published version or unpublished build) and package status from `prepare.json`;
- Prepare / Render / Cancel;
- frame range, resolution and samples (defaults from `production.render`);
- stage and frame progress, and the log tail;
- the run list;
- a result viewer. It shows the selected run's image for the timeline frame only inside that run's range, and
  "not rendered in this run" otherwise, together with the run's settings from its `status.json`.

**Jobs:**
- Each job runs `run_shot.py --run-dir <id>` in its own process group (`apps/studio/shot_workflow.{h,cpp}`, no UI).
- Cancel sends SIGTERM to the group, then SIGKILL after 8 s. Studio is the subreaper, so no orphans remain.
- Blender comes from `--blender`, then `PLUSH_BLENDER`, then the settings file
  (`$PLUSH_STUDIO_SETTINGS` or `~/.config/plush-studio/settings.json`, `{"blender": "..."}`).

**Saving a shot** merges the edits into the source file:
- Only these may change: the camera, animation tracks and keys, actions, render settings, frame range, and each
  character's position, yaw and life.
- Everything else is kept as written, at every depth: the production block, asset placeholders and unknown keys.
- An unedited save leaves the file untouched.
- Prepare and Render save first, because the pipeline works on the saved shot.

**Shot-specific limits:**
- A shot's character packages are pipeline outputs: "Save character" is refused inside a shot.
- The engine animation render renders a copy of the resolved scene.

**Evidence:** `docs/evaluation/production/T-001/`. The equivalence of a Studio run with the command line covers bake,
bones, Blender camera, frames, settings and pixels, all identical.

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
- **Plush Studio** drives the pipeline (T-001), but it has no episode/sequence view, and the cast is edited at its sources, not in Studio.
- **Arms:** imported characters stand in the engine's default A-pose arms (no relaxed idle pose for them).
