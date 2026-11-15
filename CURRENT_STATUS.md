# Current status (2026-11-15)

**Latest: T-001, Plush Studio drives the shot pipeline (implemented and tested; accepted by the owner on 2026-11-15).**
Details: `docs/milestones/2026-11-15_T-001_studio_shot_pipeline.md`, `docs/PRODUCTION_PIPELINE.md`.
- **Implemented:**
  - one workflow contract in `run_shot.py`: stages, `--run-dir` run folders, `status.json`, cancel; additive, so the
    default command is unchanged;
  - a non-UI workflow module `apps/studio/shot_workflow.{h,cpp}`;
  - in Studio: a shot browser, `--shot`, a Production panel (cast, Prepare / Render / Cancel, progress, log, runs,
    result viewer) and merge-save of shots;
  - a second test shot, `episodes/e900_workflow_test/shots/s010`.
- **Tested:**
  - idempotent prepare: 0 of 126 / 119 files changed;
  - preview equals the bake: 0.0 difference;
  - cancel: no orphans, run cancelled, earlier runs untouched;
  - merge-save with unknown fields at every depth;
  - viewer frame mapping;
  - command line vs Studio: bake, bones, camera, frames, settings and pixels identical;
  - `plush_tests` 39/39, exporter 8/8, `verify_charsys` PASS, Studio round trip.
- **Image regressions:** with the official OIDN 2.3.3 prebuilt (a build dependency installed outside the repository, `-DPLUSH_OIDN_ROOT=<path>`), `ctest` is 4/4 on unchanged `main` 1ab1ade and on the branch e6e9246, with identical rmse (m01 0.0164, face_neutral 0.0004, lineup 0.0000). This was independently confirmed in the Supervisor environment (`ctest` 4/4, `plush_tests` 39 test cases / 19631 assertions).
- **Unchanged:** the engine, `pipeline/charsys`, assets and test data.

**Latest: M3.2, first end-to-end production path (TD-42: engine animates, Blender renders).**
- The pilot shot `episodes/e000_pilot/shots/s010` (published boy + unpublished girl, 120 frames) runs from character
  sources through the engine bake to a Cycles render with one command (`pipeline/production/run_shot.py`).
- Bones exact (≤ 0.0003 mm); bake round trip 0 mm; `ctest` 4/4; `verify_charsys` PASS.
- Details: `docs/PRODUCTION_PIPELINE.md`.

**Latest: M3.1 facial engine completion (experimental; technically verified; awaiting review).** Details:
`docs/second_character/M3_FACE_SYSTEM.md` (M3.1 section).
- Engine:
  - arc-correct blink in-betweens (girl lid clearance +0.51 mm, was −10.7 mm);
  - expression-driven jaw (MouthOpen 10°, 14.2 mm chin drop);
  - per-character blink timing.
- Pipeline: the oval-eye gaze envelope; G03 has 0 eyeball/lid intersections (was 606).
- Tests: `ctest` 4/4 (19457 assertions), exporter tests 8/8, `verify_charsys` PASS.
- Boy baseline unchanged.

**Latest: `girl_auburn_bun_glasses` M3 (one reusable facial production system), experimental; technically verified;
awaiting owner review.** Details: `docs/second_character/M3_FACE_SYSTEM.md`.
- Shared:
  - `face_generic.py` (eyes, lids, lashes, brows, ears, nose, blush, action units, preset bake);
  - `face_library/expressions.json` (13 action units, 14 presets from #34, 2 optional);
  - `accessories.py` (`glasses/1`);
  - opt-in extensions of `face.py` and `geom.py`;
  - `face_system_test.py`; `face_test.py` generalised.
- Girl:
  - open eyes with highlights; Blink 0%; per-eye and partial blinks on the true arc;
  - closed soft-smile neutral; Smile/Happy with teeth and tongue;
  - glasses with 0 intersections in all states and gaze cases.
- Engine: no C++ change; her package `girl_auburn_bun_glasses_m3` blinks and plays 10 semantic expressions
  (694 assertions).
- Synthetic G03 face: builds and passes from data only.
- Boy unchanged (F09 face_test 36/36 identical, `verify_charsys` PASS, `ctest` 4/4).
- Open:
  - rounded closed lids;
  - ellipsoid eyes under gaze;
  - engine in-betweens, jaw bone and per-character blink timing (proposed engine changes, not made).

**CP-2 (hair_clumps/2): target reached by an experimental candidate; awaiting owner approval.**

Completed and tested:
- Character production pipeline `pipeline/charsys/` (TD-37); published `boy_yellow_hoodie` 1.0.0 (reference).
  Store tests 19/19 and reuse tests (reopen, pose, episode link/override, glTF, master unchanged) pass.
- `hair_clumps/2` generator with lock families and a scalp cap (`pipeline/charsys/hair.py`).
- Best candidate **H25**: hair contour 2.93% (target ≤ 3.0%, v6 3.40%), IoU 0.8455, head width +4.1% (v6 +5.7%),
  no visible scalp; 8-angle sheet `docs/evaluation/hair_experiments/cp2_hair_clumps_v2_sheet.jpg`.
- Regression: the v1 hair path still rebuilds v6 geometry exactly (0.0 m).

- Facial controls (experimental F01, `pipeline/charsys/face.py`): Blink no longer turns the eyes into skin balls
  (lid 6.0 -> 3.75 mm proud, lash seam visible, computed closing angle 41 deg), Smile corner lift +4.5 -> +7.0 mm.
  Test `pipeline/charsys/tests/face_test.py`; evidence `docs/evaluation/face_controls/`. Regression
  `verify_charsys.py` PASS (67/0).

- Hair H26 (dense rows + fanned crown, spec override): contour 2.99%, IoU 0.8463, head width +2.0%; fixes the
  H25 review points (cap patches, nape, back density, crown). Evidence `docs/evaluation/hair_experiments/H26_*`.
- Face F02 (`lips_jaw/1` + F01 Blink): real mouth opening with dark interior, `DEF-jaw` bone driven by
  `face_JawOpen` (6.7 mm chin drop), closed mouth hides the interior (0%). Temp-store reuse test PASS (411/74 bones,
  glTF, episode link). Evidence `docs/evaluation/face_controls/F02_review_1.0.0_vs_F02.jpg`.
- Reusability assessment `docs/CHARACTER_REUSABILITY.md`. Regression `verify_charsys.py` PASS (67/0).

- **Blender → C++ adapter** (TD-38, `docs/ENGINE_CHARACTER_PACKAGE.md`): exporter + rig profiles + importer +
  scene loading. Tested on the boy 1.0.0 package and an engineering fixture with different names, hierarchy and
  proportions:
  - supported on both: reach/IK, look-at, morph expressions, idle;
  - walk: supported for the boy, partial for the fixture;
  - unsupported: grasp, life-layer blink.
  `ctest` 4/4 (incl. image regressions), exporter tests 8/8, `verify_charsys` 67/0.

- **Engine behaviour generalised** (TD-39): leg-derived walk step + double support; hand frames (derived/explicit,
  any 2+ digits); blink via the character's morph; per-character expression map with warnings. Boy package: reach,
  look-at, expressions, blink, grasp (both hands), walk, idle all supported. Fixture: all except grasp (no fingers,
  by design); missing `smile` reported. ctest 4/4, exporter tests 8/8, verify_charsys PASS.

- **CP-2 face and hair quality** (experimental, not approved):
  - **F06 face:** single thin neutral mouth line; flat closed eyes with a dark lash curve (no dome); Smile with
    cheeks and eye narrowing; shaded open mouth.
  - **H28 hair:** irregular crown with a dominant front tuft; H26 coverage kept; IoU 0.8493, contour 2.92%.
  - Evidence: `docs/evaluation/face_controls/F06_*`, `combined_H28_F06_vs_1.0.0.jpg`, `docs/evaluation/hair_experiments/H28_*`.
  - `verify_charsys` PASS. No engine change.

- **CP-2 generic face and hair system step** (status: experimental; technically verified; visually reviewed by me;
  not approved):
  - **Face F09:** readable smile with intensity and asymmetry, larger JawOpen (25.5 mm) with corner-centred jaw
    weights. Synthetic-proportions check (G01) passes.
  - **Hair:** new generic options (lock shape, felt shader, real-scalp placement, fringe as data); synthetic-head
    test passes. None improves this boy beyond H28, so **H28 remains the hair candidate**.
  - `verify_charsys` PASS; no engine change.

- **`girl_auburn_bun_glasses` M2: generic body and rig fitting** (experimental; technically verified; not approved),
  details in `docs/second_character/M2_GENERIC_BODY_RIG.md`:
  - `body_generic/1` builds and rigs from the spec;
  - the girl meets the M1 measurements;
  - engine behaviours pass on 3 packages;
  - the synthetic G02 configuration builds;
  - the boy is unchanged (`verify_charsys` PASS, `ctest` 4/4).
- **Second production character `girl_auburn_bun_glasses`: M1 reference package complete**
  (`docs/second_character/M1_REFERENCE_PACKAGE.md`):
  - 6 camera-matchable views with masks; landmarks; measured proportions; colour targets; spec skeleton;
  - reusable view-extraction tool;
  - scale validated on #31: bun top level with the boy's hair top, crown at 0.97 m.

Not done / limitations:
- H25/H26 (hair) and F01/F02 (face) not published or approved (identity changes: owner decision); H25 and F01 reviewed and not approved.
- F02: flat interior (no teeth/tongue), skin stretch at mouth corners (3.5x), Smile without cheek/eye coordination; closed lid slightly rounded.
- H26: crown tufts form a regular ring; #7 front 3.63%.
- Smooth cap patch behind the ear; crown tufts thinner than the refs; side/back-¾ views still 3.5–3.7%.
- Your local Blender 5.2 runs (`reproduce_v6.py`, `verify_charsys.py`) not yet reported.
- Adapter limits: humanoid profiles only; grasp tested with a stick across the hand; no cadence/speed limit for very short legs.
- Fur is evaluation-only (not in master/glb); no USD/Alembic.

Protected: v6 + frozen baseline, version 1.0.0, reproduction script, C++ engine. Iteration 5 not started.
