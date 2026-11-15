# Task report 2026-11-15: T-001, Plush Studio ↔ shot pipeline integration

| Item | Result |
| --- | --- |
| Objective | Studio drives the M3.2 pipeline through one reusable workflow: open any shot, prepare, play the engine animation, render (engine bake, then Blender Cycles), monitor and cancel, view results, save safely |
| Contract | `pipeline/production/run_shot.py`: stages prepare/bake/render/encode (`--stages`), per-run folders (`--run-dir`), `status.json` (`plush.run_status/1`), `runs/latest` written only on success, cancel by SIGTERM and `--mark-cancelled`. Additive: the default command is unchanged |
| Workflow module | `apps/studio/shot_workflow.{h,cpp}` (no UI, no GL): shot discovery, command building, job runner (process group, SIGTERM then SIGKILL, subreaper), status parsing, run list, frame mapping, merge-save, configuration |
| Studio | `--shot`, shot browser, Production panel (cast with source and package status, Prepare / Render / Cancel, range / resolution / samples, stage and frame progress, log tail, runs, result viewer), shot actions (start/end), life toggle; scripted tests `--script-production`, `--script-cancel`, `--script-fail` |
| Test shot | `episodes/e900_workflow_test/shots/s010`: published boy 1.0.0 only, side camera with a moving target, frames 11–70; existing character, no character change |
| Approvals | Nothing published or approved |

## Implemented / tested / not verified
**Implemented and tested:**
- **R1, idempotent prepare:**
  - A second prepare changed 0 of 126 (s010) and 0 of 119 (e900) watched files. Each file was compared by sha256,
    size and mtime: `assets/`, the published version, masters, packages, resolved scene and `cast.json`.
  - Every cast member was reported as cached.
- **R2, preview equals the bake:**
  - Studio's preview evaluator matches the pipeline's bake at 12 frames (s010) and 9 frames (e900): camera, skinning
    matrices and morph weights all differ by 0.0.
  - Motion over time: the girl walks 0.31 m and the e900 boy 0.75 m; Smile and Laugh go 0→1; the camera moves.
  - Timeline playback showed about 30 distinct frames in 3 s.
- **R3, cancel:**
  - Cancel during the Blender render was graceful in 0.05 s.
  - The process group is empty and no process names the run.
  - The run is marked cancelled, and 29 earlier runs and `latest` are unchanged.
  - A partly written frame is removed: shown with a fake Blender, for SIGTERM and for a forced kill plus
    `--mark-cancelled`.
  - The C++ job tests cover graceful and forced cancel of a child-plus-grandchildren tree.
- **R4, merge-save:**
  - Unknown fields were injected at top level, in production, cast, render, camera, characters, actions, track keys,
    an unused track, lights, objects and materials.
  - Only the listed edit paths change, and an unedited save does not touch the file.
  - Key removal and disabling life were also tested.
- **R5, viewer:**
  - Offset ranges 5–7 (s010) and 20–22 (e900): frames inside the range show `frame_####.png`; frames outside show
    "not rendered in this run".
  - The run's settings come from its `status.json`.
- **R6, equivalence** (command line vs Studio, s010 frames 5–7, 320×180, 16 samples), all identical:
  - bake: byte-identical;
  - bone report: equal;
  - Blender camera: max 0.0;
  - frames: 5–7 in both;
  - resolution, samples, exposure, light energies: equal;
  - pixels: 0 differing pixels.
- **R7:** Studio only builds `run_shot.py` command lines and reads its files. There is no shot, character or
  episode name in the code.
- **R8:**
  - `plush_tests` 39/39 (19631 assertions), `test_export_engine` 8/8, `verify_charsys` PASS.
  - Studio `--script-hair-edit` / `--script-verify` round trip passes (`lashes.L` 4 → 5).
  - Path tracing a frame works in legacy and shot mode.
  - The default command line writes the same outputs (bake, resolved scene and `cast.json` byte-identical with
    `main`, pixels identical).

**Not verified:**
- **ctest image regressions:** `regression_milestone01` and `regression_face_neutral` fail in this environment
  because OIDN 2.3.3 is missing. They fail identically on unchanged `main`; the engine and `plush-render` are not
  changed. `ctest` is 2/4 here and must be rerun once OIDN is installed.
- **"Render animation to video" (engine path):** not exercised by a script. Its legacy code path is unchanged apart
  from creating `renders/`.
- **Studio under real Blender 5.3:** only the bpy module ran. With a real Blender binary the same command lines apply.

## Decisions and assumptions
- **Run ids:** run folders are `<shot>/build/runs/<id>`. A bare `--run-dir` value is an id; a path is used as given.
- **`latest`:** replaced by any successful run, including prepare-only runs. The viewer defaults to the newest
  successful run that rendered frames.
- **Status file in default mode:** a run without `--run-dir` also writes `status.json` and `prepare.json` into
  `<shot>/build/`. These are additive files; everything M3.2 wrote is unchanged.
- **Where a shot opens from:** Studio opens a shot from its resolved scene once prepared. The prepared check compares
  the resolved scene with the source (minus production and asset paths) and checks that the packages exist.
  Prepare and Render merge-save first.
- **Character edits in a shot:** inside a shot, characters are packages (a pipeline cache), so "Save character" is
  refused.
- **Engine animation render in a shot:** it renders a copy of the resolved scene
  (`build/studio_engine_preview.scene.json`).
- **Layout:** in a shot, Production, Inspector and Render share the right column as tabs. In a plain scene,
  Production is a tab behind Render, so the existing layout is kept.
- **Working directory:** Studio still writes `imgui.ini` into its working directory (existing behaviour). The
  scripted tests ran from a scratch folder, so the tracked `imgui.ini` is unchanged.

Agents: one primary agent, no subagents. Token counts are not exposed to me and are not estimated.
