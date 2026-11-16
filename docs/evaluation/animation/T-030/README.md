# T-030 evidence: eyes in their sockets, hands out of the body (e905_props_test/s010)

Branch `t-030-claude-eyes-hand-fix` (from `t-022-claude-hand-props`). The owner rejected the T-022 render for two
defects. Both are fixed in the shared system (exporter, render path, interaction/IK). Nothing is specific to one
character or to this shot.

## 1. Eyes floating in front of the face

**Cause.** The exporter (`pipeline/charsys/export_engine.py`) gave every deform bone its nearest *deform* ancestor as
its engine parent. Rigify hangs `DEF-eye.L` under `ORG-eye.L` → `ORG-spine.006` → … (all non-deform), so the eyes
had **no parent**: they were engine roots and stayed in character space while the head turned, nodded and swayed.
The bake carried that faithfully: in e905 the eyes were up to **61 mm (boy) / 48.5 mm (girl)** from where the head
holds them. `shot_render.py` reproduced the bake exactly (0.0008 mm bone error), so the fault was not in the Blender
apply step, not a rest/local-space mismatch, and not a double transform. The face rig itself was unaffected, which
matches the T-024 note. `DEF-shoulder.*`, `DEF-upper_arm.*`, `DEF-thigh.*` and `DEF-pelvis.*` had the same orphan
problem: the shoulder girdle did not follow the chest (up to 8.5 mm off).

A second, smaller cause: the boy's `DEF-eye` bone head sits **5.2 mm in front of** his eyeball's centre (a 37 mm
sphere). Gaze turned the ball about that point, so it slid up to 3.4 mm in the socket.

**Fix (shared, exporter version 3).**
- A deform bone without a deform ancestor gets the deform twin (`DEF-x` of `ORG-x`/`MCH-x`) of its nearest such
  ancestor. That is the bone Blender carries it with: eyes → head, shoulders → chest, upper arms → shoulders,
  thighs/pelvis → hips.
- Eye roles (`eye.*`) pivot at the centre of the spherical eyeball bound only to them (sphere fit; recorded in the
  package's `eye_pivots`). Skin matrices are world transforms of the geometry, so the render stays exact.
- Docs: `docs/ENGINE_CHARACTER_PACKAGE.md`.

**Proof.** `shot_render.py` now measures every frame, as Blender evaluates the applied bake. It compares each eye's
centre (sphere fit of the evaluated eyeball) with its socket (the rest centre carried by the head bone). See
`e905_shot_render.json`.

| | before (T-022 packages) | after (this render, 72 frames) |
|---|---|---|
| boy eye centre → socket | 61.2 mm | **0.10 mm** (worst f17; the lid shell's fit, the eyeball itself is ~0) |
| girl eye centre → socket | 48.5 mm | **0.002 mm** |

Tests:
- `pipeline/charsys/tests/test_shot_eyes.py` (new): bake + Blender apply of e905; both characters ≤ 0.5 mm on all
  frames. 9/9.
- `test_export_engine.py` (+5 checks on the published boy 1.0.0 master, read-only): only `hips` is a root, eyes are
  children of the head, eyes pivot at the ball centre, and the master is byte-identical. 13/13.

## 2. Hand and forearm inside the body during reach / hold / hand-over

**Causes (measured).**
- **No body awareness.** The two-bone IK had no pole and kept whatever bend plane the clip arm had, and nothing
  kept the wrist path, the hold targets or the hand-over point out of the body.
- **Hand-over point.** The hand-over point (between the two right shoulders) was 2.5 cm in front of the boy's belly,
  so his right forearm crossed his chest: **−69 mm** inside on the T-022 bake (`clearance_before_t022_bake.json`).
- **Grip socket at the belly.** The T-022 staging put the grip socket 0.5 arm lengths in front of the shoulder, which
  is at the belly surface (11.6 cm vs. ~12 cm body radius). The grasp contact itself required the forearm in the body.
- **Asset issue, not fixed here (not my area).** The boy's hoodie sleeves are skinned to `DEF-hand`, `DEF-shoulder`
  and `DEF-spine.003` only (0 weight on the upper arm, 4 % on the forearm). When the hand comes in front, the sleeve
  stretches along the shoulder→hand chord, which cuts the chest whatever the elbow does. The clearance below therefore
  works on the arm's *skinned surface*, not on bone capsules, so it sees and avoids this.

**Fix (shared: `engine/scene/interaction.{h,cpp}`, `scene.cpp`, `actions.cpp`; docs `docs/ACTIONS_AND_DIRECTOR.md`).**
- **Body model** from the shared roles (hips, spine, chest, neck) and the skinned rest meshes, garments included:
  7 elliptical capsule sections (2 pelvis, 3 lower torso, 2 upper torso). Each is fitted to the 99th percentile of its
  own height slab (front half: a backpack or hair behind is not body to a hand).
- **Arm** = ~600 sampled vertices of the arm's own surface (sleeve, cuff, hand) with their real skin weights.
- **Required:** the hand and the wrist half of the forearm. The upper arm and the elbow half rest against the side and
  are reported only. A point that already rests against the body at rest counts from that depth.
- **Elbow pole** (`pole.<hand>` tracks, weight = IK weight): the arm swings about the shoulder→wrist axis so the elbow
  points out/down/back. The wrist stays and the hand keeps its rotation.
- **Wrist target:**
  - pushed per frame along the gap gradient to a 5 mm margin;
  - coherent in time (each frame starts from the previous push and is shrunk to the smallest push that clears, with
    capped steps), then eased over ±5 frames, so there are no pops;
  - while the IK fades in or out, the arm is never deeper than the clip arm alone;
  - contacts, the giver's still hold and the legacy `reach`/`touch` contacts keep exact targets.
- **Hand-over meeting point:** grid search (3 cm, then 1 cm) around the requested point for the closest point where
  both arms are clear and within reach. The receiver's reach is planned there.
- **Warnings:** an arm still inside at full IK, or a hand-over with no clear point, is a scene warning. A contact the
  body is in the way of cannot be moved (the prop is where the author put it).
- **Staging (shot data, same rule as the test fixtures).** `make_t022_shot.py` now derives the cup 0.85 arm forward /
  0.45 down (was 0.5 / 0.66, at the belly). The hand-over `at` is unchanged; the engine moved it to a clear point.

**Measurements, this render** (`e905_measurements.json`, from `measure_e905.cpp`). Gap = forearm/hand surface to the
body sections; ≥ 0 is outside; margin 5 mm.

| | boy right arm | girl right arm |
|---|---|---|
| min gap at full IK weight (all reach/hold/hand-over frames) | **+7.3 mm** (f51) | **+5.8 mm** (f54) |
| IK fade frames, deeper than the clip arm alone | 0.29 mm max | 0.0 mm |
| T-022 bake, same model | −68.7 mm (f55) | +15.4 mm |
| upper arm / elbow half (reported only) | −79 mm (sleeve chord near the shoulder, see asset issue) | −30 mm |
| clip-only (idle) arms resting against the sides (no IK, not this task) | −9 mm | −32 mm |
| scene warnings | none | none |

Contacts and props are unchanged from T-022:
- boy palm → grip at grasp: 0.00007 mm;
- girl palm → grip_b at hand-over: 0.00007 mm;
- prop jump at the parent switches: 0.0001 / 0.0002 mm;
- palm → socket while held: ≤ 0.0001 mm;
- cup stays upright (cos 1.0); max cup speed 18 mm/frame.

**Doctests** (`tests/test_interaction.cpp`, 4 new cases):
- model fit (7 sections, >100 arm points, rest pose clear, a hand pushed into the belly reads −60…−95 mm with an
  outward push);
- the pole moves only the elbow (wrist < 0.01 mm, hand rotation unchanged);
- a hold pulled across and into the body stays outside (≥ 0 at full IK), with an exact contact, no wrist spike
  (< 0.0005 mm) and a continuous prop;
- the hand-over meeting point keeps both arms outside, both pairings.

Changed fixtures, with no assertion loosened: the T-022 interaction tests placed the cup at the belly the same way
e905 did. The cup now stands 0.85 arm forward. Two hold vectors that pulled the cup toward or across the body now
move it away, because the clearance rightly resists the old ones. Every existing threshold is unchanged.

## 3. Render
- `e905_s010.mp4`: 72 frames, 3.0 s, 640×360, Cycles 16 samples + OIDN 2.3.3; bpy 5.3.0 venv behind a `blender`
  wrapper. 49.6 s setup + 432 s render (6.0 s/frame), 8 min wall clock.
- `e905_contact_sheet.png` (`contact_sheet.py`): beats f1/17/30/46/51/72; under each, the boy's eyes, the girl's eyes
  and the working forearm with its measured gap.
- Visual notes:
  - The boy looks down at the cup with his lids lowered (f1–30) and opens them at the hand-over.
  - From this camera the girl's eyes are mostly behind her hair. Her alignment is proven by the measurement, not the
    picture.
  - The boy's sleeve still stretches straight from shoulder to wrist (asset weights, above).

## Checks
| check | result |
|---|---|
| `ctest` | 4/4 |
| `build/tests/plush_tests` | 77/77 cases, 21530 assertions |
| `test_export_engine.py` | 13/13 |
| `test_shot_eyes.py` (new) | 9/9 |
| `verify_charsys.py` | PASS, 68 checks; boy 1.0.0 master byte-identical; v6 geometry worst difference 0.0 m |
| `face_test.py` (boy 1.0.0, read-only) / `face_system_test.py --no-render` (girl) | exit 0 |
| frozen data (boy 1.0.0/1.1.0/v6, tests/data, baselines) | untouched (`git status` clean there) |

## Open
- Boy hoodie sleeves need upper-arm/forearm weights (garment/character build, not in T-030's file area).
- Clip idle arms rest against the sides (−9 / −32 mm against the conservative 99th-percentile envelope); clips are
  not in T-030's file area.
- The meeting-point search costs about 1 s per hand-over at load.

## Commands
```bash
python3 pipeline/clips/make_t022_shot.py --boy-package <build>/packages/boy_* --girl-package <build>/packages/girl_*
python3 pipeline/production/run_shot.py --shot episodes/e905_props_test/shots/s010/shot.scene.json --blender <blender> \
    --run-dir t030_final --video
g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-030/measure_e905.cpp -Lbuild/engine -lplush_scene \
    -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o m && ./m <build>/shot.resolved.scene.json
python3 docs/evaluation/animation/T-030/contact_sheet.py --frames <run>/render --bake <run>/bake.json \
    --cast <build>/cast.json --measurements docs/evaluation/animation/T-030/e905_measurements.json --out docs/evaluation/animation/T-030
python3 pipeline/charsys/tests/test_shot_eyes.py --blender <blender>
```
