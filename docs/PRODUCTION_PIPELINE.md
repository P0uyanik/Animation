# Production pipeline: from character sources to a rendered shot (M3.2, 2026-11-14)

**Render path (TD-42):**
- **The C++ engine animates:** actions, life layer, IK, expressions, jaw, blink timing.
- **Blender renders:** Cycles by default, or EEVEE for drafts, with the characters' own materials.
- The engine's path tracer stays for previews and the existing image regressions.

```
character sources            engine packages           C++ engine                 Blender
(published version dir   ->  export_engine.py      ->  plush-render --bake    ->  shot_render.py (Cycles/EEVEE)
 or spec, built)             (cached by master sha)    bake.json                  frames, shot.blend, shot.mp4
```

## One command per shot
```bash
python3 pipeline/production/run_shot.py --shot episodes/e000_pilot/shots/s010/shot.scene.json --blender <blender> --video
```

`--engine cycles|eevee` selects the Blender renderer and defaults to `cycles`. EEVEE is a draft approximation with
four-ray soft shadows, Fast GI ambient occlusion and bloom off. `--bake-engine <path>` overrides the separate
`plush-render` executable used by the bake stage. Omitting `--engine` keeps the original Cycles setup and invocation.

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
- **render:** Blender (`shot_render.py`, Cycles by default or EEVEE with `--engine eevee`).
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

## Lighting: set light rigs (T-221, T-196 Q4)
Final renders can light a shot with a **Blender light rig** (lights + optional world colour or HDRI) instead of the
approximate engine-light translation. The engine's lights stay in the shot for engine previews only. Opt-in: a shot
without a rig renders exactly as before (same Blender scene, same pixels).

- **Where rigs live:** `content/sets/rigs/<id>.light_rig.json` (`plush.light_rig/1`, `pipeline/charsys/set_lights.py`).
  Blender world axes (+Z up, metres) and Blender units, so a rig lit in Blender is saved as-is.
- **Who picks the rig** (first that applies): `shot_render.py --light-rig <id | file | engine>`; the scene's top-level
  `"x_light_rig": "<id>"` (`"engine"` = no rig); the set's `"blender_light_rig": "<id>"` (recorded by
  `sets.py apply` as `x_set.light_rig`); none. An unknown id stops the render and lists the available rigs.
- **With a rig:** the rig's lights and world are built (objects `rig.<name>`); the bake's sun/rect/sky lights and
  `light_scale` are not used. Box objects, props, camera, exposure and the render profile are unchanged.
  `shot_render.json` gets a `light_rig` block (id, source, file, lights, world); without a rig it has no such key.
- **File format** (unknown keys are refused):

```json
{"format": "plush.light_rig", "version": 1, "id": "<id = file name>", "description": "...",
 "lights": [
  {"name": "key", "type": "area", "location": [x, y, z], "aim": [x, y, z],
   "shape": "RECTANGLE", "size": [w, h], "energy": 75.0, "color": [1, 0.88, 0.72]},
  {"name": "sun", "type": "sun", "direction": [x, y, z], "strength": 3.6, "angle_deg": 3, "color": [1, 0.9, 0.75]},
  {"name": "bulb", "type": "point", "location": [x, y, z], "radius": 0.1, "energy": 20, "color": [1, 1, 1]},
  {"name": "spot", "type": "spot", "location": [x, y, z], "rotation_deg": [rx, ry, rz], "spot_size_deg": 40,
   "spot_blend": 0.15, "energy": 50, "color": [1, 1, 1], "cast_shadow": false}],
 "world": {"color": [0.96, 0.92, 0.84], "strength": 2.0}}
```
  - Orientation: area and spot take `aim` (a point) or `rotation_deg` (XYZ Euler); sun takes `direction` (where
    the light travels) or `rotation_deg`. Lights emit along their local -Z.
  - Units: `energy` in W (area, point, spot); sun `strength` in W/m². `shape` RECTANGLE/ELLIPSE take `size: [w, h]`,
    SQUARE/DISK take `[s]`. `cast_shadow` is optional (default true).
  - `world` (optional, absent = black): `{"color", "strength"}` or `{"hdri": "<path relative to the rig file>",
    "strength", "rotation_deg"}`.
- **Saving a rig from Blender:** `blender -b --factory-startup -P pipeline/charsys/set_lights_blender.py -- dump
  --blend <file.blend> --id <id> --out content/sets/rigs/<id>.light_rig.json` writes every light of the scene and its
  world (Background colour, or an Environment Texture as `hdri`). A build followed by a dump gives the file back.
- **Starting rig:** `water_table_corner_window` (named by `content/sets/water_table_corner.set.json`) is today's
  translated window key / wool rim / fill / window sun and the window sky, saved with `dump` at `light_scale` 1.0.
  It renders the same frame as the translation (e907 s010 f48, 1280x720, 128 spp, final720_look: 96.9 % of pixels
  identical, max difference 5/255, PSNR 67.8 dB; the residue is the dump's 6-significant-digit rounding).
- **Evidence and tests:** `docs/evaluation/rendering/T-221/`; `pipeline/charsys/tests/test_set_lights.py`,
  `pipeline/charsys/tests/test_set_lights_blender.py`, `pipeline/production/tests/test_sets.py`.

## Verified (pilot shot e000/s010, 120 frames, published boy 1.0.0 + unpublished girl M3.1)
- **Bone reconstruction:** at most 0.0003 mm and 0.0° for both characters.
- **Mapping:** every morph maps to a facial control.
- **Bake round trip** (C++ test): the posed meshes rebuilt from the bake equal the engine's evaluation (0 mm).
- **Timing:**
  - bake 0.2 s;
  - Blender setup and keying about 5 s;
  - Cycles 8.6 s per frame at 640×360 / 32 samples (17.9 s at 960×540).
- **Evidence:** `docs/evaluation/production/M32_s010_*` (contact sheet, mp4, run report).

## Scene events: reactions in playback (T-097D)
A shot can list things that happen in it under the optional scene key `events` (opt-in: without it nothing changes,
and every existing shot bakes byte-identical). Each event is planned for every reacting character by the reaction
planner (`engine/scene/reaction.h`, T-097B: the character's `personality` profile, else the shared defaults) and played
as generated actions:

```json
"events": [
  {"time": 1.0, "kind": "object_appears", "name": "ball appears", "source": "ball"},
  {"time": 2.5, "kind": "partner_acts", "name": "boy waves", "source": "boy", "salience": 0.6, "characters": ["girl"]}
]
```

| Field | Meaning |
| --- | --- |
| `time` | seconds from `frameStart` (required, >= 0) |
| `kind` | `object_appears`, `partner_acts`, `success`, `failure` or `custom` (default `custom`; a custom event needs `name`, which is the key of a profile's `reaction.events` entry) |
| `name` | label (logs, animcheck) |
| `source` | the character or scene object that causes it (`""` = the scene); the actor of `partner_acts` does not react to it |
| `salience` | 0..1 (default 1): how noticeable it is (later, weaker, shorter reaction; 0 = not noticed) |
| `characters` | optional list of the characters that react (default: every scene character) |

These are the fields of `plush::ReactionEvent` (`engine/scene/acting.h`); animcheck's acting rule
(`tools/animcheck/acting.py`, T-097C) reads `time`, `name` and `source` of the same list. Per reacting character, at
`time` + the planned notice delay (frame `frameStart + (time + delay) x fps`):
- **Look** at the source (a character's face or the object), held for the reaction's gaze habit (`gazeShift` x its
  duration, at least 3 frames), then back to the earlier gaze. A character without an earlier look turns in and out
  over 12 frames (`lookAt.weight`), so nothing changes before the reaction. No look for a scene event without a source.
- **Emotion** (the planned one, at the planned intensity) as a blended emotion action (T-097A `blend`), released after
  the planned duration (it replaces the character's other blended emotions, the T-097A default); the profile's intensity scale and gaze shift are its `modulation` (the plan's timing already
  holds the tempo and hold scales). Skipped with a warning if `content/emotions` has no such emotion.
- **Gesture**: the profile's preferred gesture for the event (the first one `content/clips` has), as a clip action at
  the same frame, when the expressed intensity reaches the gesture threshold.

The generated actions are deterministic (events by time, then scene character order) and follow the authored actions
at equal frames. `SceneEvaluator::reactionActions()` returns them in the scene's action format: the scene with them
appended to `actions` is what the acting rule checks. Generated looks use two look options that authored looks may
use too: `"atCharacter": "<name>"` (look at that character's face) and `"back": true` (return to the earlier gaze).
Tests: `tests/test_reaction_playback.cpp`; evidence: `docs/evaluation/animation/T-097D/`.

## Animation timing: the calibrated profile is the default (T-104, T-104d)
The scene key `timing` names a timing profile, `content/timing/<name>.timing.json` (`content/timing/README.md`).
It sets the defaults of interaction frames a scene leaves out, and the notice delay of event reactions. Frames written
in an action always win.

| Scene key | Timing used |
| --- | --- |
| absent (or `null`) | `calibrated`, the default since T-104d (owner decision 2026-11-19) |
| `"timing": "<name>"` | that profile; a load error if `content/timing/<name>.timing.json` is not found above the scene |
| `"timing": "none"` | the shared engine defaults (`engine/scene/interaction.h`), the behaviour before T-104d |

- If a scene has no key and no `content/timing` folder exists above it (a scene outside a content tree), it uses the
  shared defaults without a warning, the same way a missing personality profile is handled.
- The tempo scales of a character's personality (`tempo.beat_scale`, `tempo.hold_scale`) apply to every profile.
- Saving a scene keeps the key as written: an absent key stays absent.
- No existing shot changed when the default was switched: every shot in the repository writes out the interaction
  frames the profile would set. The bakes are byte-identical before and after (`docs/evaluation/animation/T-104d/`).
- `episodes/e907_exchange/make_shot.py` still builds the authored exchange from the shared beats unless it is run with
  `--timing calibrated` (`s010_calibrated`).

## Not covered yet
- **Props:** SDF props, water and paper boats are not baked (listed as `objects_not_baked`).
- **Engine-only characters** (SDF) cannot be rendered in Blender.
- **Lights:** the engine-light translation is approximate, not radiometric. Final renders can use a Blender light
  rig instead (see "Lighting: set light rigs"); shots without a rig still use the translation.
- **No episode layer:** each shot is run on its own; there is no sequence assembly or audio.
- **Plush Studio** drives the pipeline (T-001), but it has no episode/sequence view, and the cast is edited at its sources, not in Studio.
- **Arms:** imported characters stand in the engine's default A-pose arms (no relaxed idle pose for them).
