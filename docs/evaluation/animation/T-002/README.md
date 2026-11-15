# T-002 evidence: clip foundation (2026-11-15)

**Environment:**
- Blender: the bpy 5.3.0 module (Python 3.13).
- Engine: built with the official OIDN 2.3.3 prebuilt (`-DPLUSH_OIDN_ROOT`, installed outside the repository).
- Studio: Mesa llvmpipe under Xvfb.
- Renders: Blender Cycles at 320×180 / 16 samples. They are technical evidence only.

**Characters:**
- the boy, published 1.0.0;
- the girl, an unpublished build from her spec;
- the neutral mannequin, the authoring rig for C3.

Packages are the shot cache's packages (exporter version 2, with the `retarget` block).

## C2, C3 (`clip_measurements.json`)
**Measurement:** per role and every frame of each clip, life layer off.
- **C2:** world direction / twist reference of boy vs girl, over the roles the clip drives (limits 2.0° / 5.0°).
- **C3:** the engine playing the exported clip on the mannequin's package vs the Blender mannequin pose (limits 1.0° / 3.0°).
- **Not measured:** finger roles (C2 uses the limb, torso and head roles of the specification); the hand appears in C3.

| Clip | C2 boy vs girl: max direction / twist (deg) | roles | C3 engine vs Blender: max direction / twist (deg) | frames |
| --- | --- | --- | --- | --- |
| idle_relaxed | 0.0000 / 0.0000 | 13 | 0.0466 / 0.0426 | 90 |
| wave | 0.9548 / 0.9548 | 2 | 0.0197 / 0.0172 | 105 |
| point | 0.9398 / 0.9548 | 2 | 0.0325 / 0.0182 | 93 |
| sit_down | 0.0000 / 0.0000 | 7 | 0.0392 / 0.0392 | 57 |
| stand_up | 0.0000 / 0.0000 | 7 | 0.0341 / 0.0341 | 57 |
| dense_test | 0.0000 / 0.0000 | 13 | 0.0000 / 0.0000 | 60 |

| Character | Boundary | Worst role: change / limit (deg per frame) | Root change / limit (mm per frame) | Result |
| --- | --- | --- | --- | --- |
| boy | wave blend-in (base idle -> wave) | spine: 0.07 / 0.08 | 0.0 / 0.0 | PASS |
| boy | wave blend-out (wave -> base idle) | spine: 0.07 / 0.08 | 0.0 / 0.0 | PASS |
| boy | point (mirrored) blend-in | forearm.R: 0.12 / 0.20 | 0.0 / 0.0 | PASS |
| boy | point (mirrored) blend-out | head: 0.16 / 0.23 | 0.0 / 0.0 | PASS |
| boy | walk start (base idle -> walk) | forearm.R: 5.69 / 7.08 | 3.4 / 11.8 | PASS |
| boy | wave during walk: blend-in | hips: 0.06 / 0.07 | 4.8 / 11.8 | PASS |
| boy | wave during walk: blend-out | neck: 0.09 / 0.11 | 5.9 / 11.8 | PASS |
| boy | walk end (walk -> base idle) | head: 0.18 / 0.23 | 3.4 / 11.8 | PASS |
| boy | sit_down blend-in (base idle -> sit_down) | hips: 0.05 / 0.07 | 2.3 / 9.7 | PASS |
| boy | sit_down -> stand_up hand-over | upperArm.L: 0.15 / 0.23 | 0.0 / 9.7 | PASS |
| boy | stand_up end (stand_up -> base idle) | shin.R: 0.17 / 0.17 | 2.3 / 9.7 | PASS |
| girl | wave blend-in (base idle -> wave) | spine: 0.07 / 0.08 | 0.0 / 0.0 | PASS |
| girl | wave blend-out (wave -> base idle) | spine: 0.07 / 0.08 | 0.0 / 0.0 | PASS |
| girl | point (mirrored) blend-in | forearm.R: 0.12 / 0.20 | 0.0 / 0.0 | PASS |
| girl | point (mirrored) blend-out | head: 0.16 / 0.23 | 0.0 / 0.0 | PASS |
| girl | walk start (base idle -> walk) | forearm.R: 5.69 / 7.08 | 3.0 / 10.5 | PASS |
| girl | wave during walk: blend-in | hips: 0.06 / 0.07 | 4.3 / 10.5 | PASS |
| girl | wave during walk: blend-out | chest: 0.15 / 0.19 | 5.3 / 10.5 | PASS |
| girl | walk end (walk -> base idle) | head: 0.18 / 0.23 | 3.0 / 10.5 | PASS |
| girl | sit_down blend-in (base idle -> sit_down) | hips: 0.05 / 0.07 | 2.0 / 8.7 | PASS |
| girl | sit_down -> stand_up hand-over | forearm.L: 0.15 / 0.23 | 0.0 / 8.7 | PASS |
| girl | stand_up end (stand_up -> base idle) | shin.L: 0.17 / 0.17 | 2.0 / 8.7 | PASS |

- loop seam idle_relaxed (boy): max 0.040 deg per frame = 0.22 x the interior maximum (limit 1.25); root change 0.00 mm
- loop seam idle_relaxed (girl): max 0.040 deg per frame = 0.22 x the interior maximum (limit 1.25); root change 0.00 mm
- entry/exit (weight 0 frames vs the underlying pose): max 0.000002 deg over 16 events

Interior per-frame maxima (deg per frame, boy):
| Source | upperArm.R | forearm.R | thigh.L | shin.L | spine | head | root mm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| idle_relaxed | 0.16 | 0.16 | 0.00 | 0.00 | 0.07 | 0.18 | 0.00 |
| wave | 8.45 | 11.42 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| point | 6.27 | 6.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| sit_down | 0.00 | 0.00 | 3.94 | 0.14 | 2.77 | 0.56 | 7.73 |
| stand_up | 0.00 | 0.00 | 3.94 | 0.14 | 2.77 | 0.56 | 7.73 |
| dense_test | 0.85 | 0.85 | 0.00 | 0.00 | 0.00 | 2.28 | 0.00 |
| walk | 5.67 | 5.67 | 14.51 | 8.34 | 0.00 | 0.00 | 9.40 |


**Reading the C2 numbers:**
- **Whole-body clips** (idle, sit, stand, dense): 0.0000°. Rest pose and proportions drop out.
- **Arm-only clips** (wave, point): 0.95°. The arm is applied relative to each character's own rest chest, which
  differs by about 1° between the two characters (local-space layering).
- **Synthetic skeletons** (`plush_tests`): 0.00003° direction, 0.00002° twist (limit 0.5°).

## C4 (`clip_measurements.json` → `C4`)
**Method:**
- **Scenes:** each character is measured alone. Base `idle_relaxed`, then a wave (blend 8/8), a point mirrored to the
  left arm, a walk with a wave during it, sit_down → stand_up.
- **Reference:** the same scene without clip actions (the underlying pose).
- **Interior maxima** come from the per-clip scenes; for the walk, from the engine walk alone over its whole span.
- **Boundary limits:** min(12°, 1.25 × the larger interior maximum of the sources there). The base idle is under
  every window. The root limit is 1.25 × the largest interior root speed.

All 22 boundary checks (11 per character), both loop-seam checks and all 16 entry/exit checks pass (table above).

## C5: layering (`plush_tests` "clips: scene playback ...")
- **Arm clip during a walk:** the masked arm follows the clip; the other arm keeps the walk swing (difference < 0.001°).
  Hips, legs, spine, chest and root equal the walk without the clip (< 0.001°, < 1 µm).
- **Full-body clip during a walk:** the legs and hips stay the walk's; the arms follow the clip.
- **Reach on the same arm as an arm clip:** the wrist reaches the IK target (< 1 mm) and is 0.0001 mm from the reach
  alone. Clip finger tracks yield to the hand track.
- **Hand keys** win over clips (< 0.01°).
- **Look:** applied after clips (gaze and head follow unchanged).
- **The e901 shot** combines all of these: the boy walks, waves and looks at the camera; the girl's point clip and
  her right-hand reach overlap.

## C6: unchanged without clips
- **(i) Same packages, engine only.** Main's resolved s010 scene (old packages), all 120 frames, baked by the main
  engine and by the branch engine: **byte-identical**, sha256 `aa01af32…6953a` (`c6_i_engine_bake.json`).
- **(ii) Full production run on the branch** (new packages, exporter version 2) vs (i): **2 differing fields**, both
  package paths (`characters[0].package`, `characters[1].package`). Camera, skinning matrices, morph weights and
  static fields are identical (`c6_ii_production_bake_diff.json`).
- **Pixels** (main vs branch, 320×180 / 16 samples; `c6_pixels.json`):
  - **e900:** frames 20–22, 0 differing pixels.
  - **s010:** frames 5–7, 0 differing pixels with the same girl master.
  - **The first comparison** showed up to 54 pixels differing by 1/255. Main's fresh worktree had rebuilt the
    unpublished girl's master from her spec (sha f620… vs the cached b5f2…). A rebuild is not byte-identical; that
    is pre-existing and unrelated to clips.
- **Frozen image regressions:** ctest 4/4 (see `regression_results.txt`).

## C7: production path
- **Shot:** `episodes/e901_clip_test/shots/s010`, 440 frames, both characters (`T002_e901_contact_sheet.jpg`):
  - base idle;
  - wave (the girl's mirrored to her left arm);
  - point;
  - the boy walking, waving and looking at the camera; the girl's point plus her reach for the cup;
  - both sit on boxes and stand up (three-quarter camera; seen from the front, seated thighs point into the lens).
- **Seat boxes:** top = the sit_down seat contact `height_ratio` 0.6173 (clip data) × the leg length (package data):
  boy 0.161 m, girl 0.145 m.
- **Runs:** `run_shot.py` (a full bake and one run per contact-sheet frame) and Studio
  `--script-production --script-frames 360-362`:
  - prepare;
  - preview vs bake, difference 0.0;
  - render with live progress;
  - viewer mapping (`studio_e901_viewer_*.png`, `studio_production_e901.json`).

**Visual check** (technical only; acting quality is out of scope):
- arms down in the idle; no limb through the body;
- the knees and hips of the seated pose are plausible; both characters rest on their boxes;
- the waving forearm and hand stay outside the head.

**Not checked:** fine contact (low resolution).

## C8
- **dense_test:** 60 fps dense samples, played in a 30 fps scene. C2 0.0000°, C3 0.0000° at every second clip frame.
- **Unit tests:** 60 fps dense vs 30 fps sparse play the same motion (< 0.05°); a speed test.
- **Mirror, finger tracks and contact markers:** `point` (fingers), the mirrored wave and point in e901, and the seat
  and foot-plant contacts in sit_down / stand_up.
- **Mocap mapping:** documented in `docs/ANIMATION_CLIPS.md` §8.
