# T-183 round file: hair contact

Branch `t-183-claude-hair-contact`. Round 1 input `7135087`; round 2 input `2664f7e`.

## Round 2 (in progress): hair against the whole body and the garments

Owner verdict on round 1 (2026-11-21 ~19:20 CET): not accepted, "the hair still intersects with the body and other
areas; it goes inside the body". Round 2 goal: no hair inside head, neck, shoulders, back, arms, hands or garments
through e909 s010; target 0 frames deeper than 1 mm. Ear look stays keep-out. Everything opt-in.
Design approved by the Supervisor 2026-11-21 20:07Z with four conditions: (1) fix and unit-test the resting-contact
tip noise before building on it; (2) one cheap preview frame of the curtain chains before any long render, report at
once if it shears; (3) a 3-8 mm rest gap above cloth is acceptable, state it in the README; (4) `measure_body.py`
result for released and candidate, per surface, at CHECKPOINT. Merge `origin/main` again before READY (T-184 lands
there: `release_rule.py`, `test_release_rule.py` SAMPLES, a GENERATOR_PINS row; keep both entries).

### Measure (`tools/measure_body.py`, all 286 frames, 160,986 hair vertices, girl)

Depth = exit distance of a hair vertex out of the figure (skin, ears, hands, every garment; cloth shells and the space
under the cloth count). Vertices embedded at rest (scalp side of cap and crown, lock roots) count only by what they
are deeper than at rest. `python3 tools/measure_body.py <bake.json> [--out=] [--step=N]`, about 1 minute per bake.

| Bake | Frames deeper than 1 mm | Max depth | Most vertices in one frame |
|---|---|---|---|
| Released 0.14.0 (`s010`, run `rel`) | 286 of 286 | 65.4 mm | 7,164 |
| Round 1 candidate (`s010_t183`, run `r1c`) | 286 of 286 | 63.1 mm | 3,889 |
| Round 2 prototype `p6` (every 3rd frame; package block edited by `tools/proto_contact.py`, no groom build yet) | 96 of 96 | 48.4 mm | 459 |

These two full-shot rows were measured before the measure took the second shortest way out of its fixed directions
(one stray opening of the hollow torso no longer counts as outside); re-measure both at CHECKPOINT.

Prototype `p6` by surface (frames of 96, max): blouse 0; hands 0; cuffs 0; vest 1-3 single vertices in 1-3 frames
(19-44 mm, creases at the vest edges); ears 28-37 frames, 5-7 mm (side_b locks, static temples); skin 55 frames,
48 mm, 402 vertices = the static curtain (not started), cap 12 mm / 127 vertices, temples 2-4 mm.

### Why round 1 missed (measured)

1. Body colliders unchanged (head sphere, torso capsule r 82 mm, two shoulder spheres): sleeves (x to +-221 mm), vest,
   collar not covered. The girl has no arm skin: the blouse is the arm surface (round 1 fitted its 25th percentile).
2. Chain collision radius 14 mm; a ringlet's vertices lie 24-26 mm (median), 43-54 mm (95 %) from the chain line.
3. Non-solid colliders allow the depth of the kinematic target; locks are modelled up to 42.6 mm inside the blouse.
4. Static hair (curtain, cap, temples) has no collision; the head is tilted 28 deg (mean), 37.6 deg (max) against the
   chest all shot and sits directly on the shoulders (head bottom y 0.689, shoulders 0.635, collar 0.633-0.687).

### Done in round 2 (committed)

- Engine `engine/anim/secondary.{h,cpp}`, chain `contact` block, new optional keys (absent = previous path; the 12
  existing secondary tests pass): `radii` (one collision radius per joint, tapered segments), `rest` (resting
  contact: every collider at full radius; a pushed joint takes the collider's velocity along the normal and loses
  sliding speed by `friction`, default 40 1/s; the segment middle is tested with a fixed lever instead of the closest
  point; colliders far from the chain are skipped per step), `max_swing` (default 12 rad/s: a segment turns at most
  this much faster than its kinematic direction, so a lock squeezed between two colliders moves steadily).
- `pipeline/charsys/groom_contact.py`, pure functions (not yet called by the bind): `skin_spheres` (spheres that
  follow a surface from inside, each rides on the bone that carries its vertex; orientation by what is visible, not
  by the stored normal: vest trims and cuffs are modelled inside out), `chain_radii`, `fit_cover`, `capsule_distance`,
  `cover_report`.
- Tools: `tools/measure_body.py`, `tools/proto_contact.py <name> [key=value]` (edits the candidate package's dynamics
  block, bakes into `s010_t183/build/exp/<name>/`, prints cover, tip noise and the measure; needs
  `s010_t183/build/packages/girl_*`: run `run_shot.py --stages prepare,bake` on `s010_t183` first),
  `tools/tip_noise.py`, `tools/trace_chain.py`.

Prototype settings that gave `p6` (`proto_contact.py p6 radius_pct=100`): spheres head 150 (reach 0.10 m), ears 102
(spacing 10 mm, radius <= 20 mm), torso 299 (spacing 24 mm, radius 45 mm, reach 0.12 m of the chains), arms 156
(spacing 22 mm), hands 97 (spacing 12 mm, radius <= 20 mm), pad 2.5 mm; old `head`, `torso`, `shoulder_*` kept as
core; chain radii = 100th percentile of the lock's vertices per joint, root 0, each capped by the joint's rest
clearance to the head-bone colliders; `rest`, `segments`, `anchored_gravity`, friction 40, max_swing 12.
Surface left outside the spheres: head 2.6 mm, ears 1.3 mm, torso 8.9 mm (p99 0.1), arms 18.2 mm (p99 7.8: cuffs
and sleeve openings, no measured penetration there), hands 3.9 mm.

### Session 2 (2026-11-21, to `52dd7e5` and the commit after it): condition (1) and the unit tests

- `origin/main` (159e059) merged; `release_rule.py`, `test_release_rule.py` SAMPLES, `GENERATOR_PINS.md` keep both the
  T-184 `seated` entries and the T-183 ones. Merge `origin/main` once more before READY.
- `tests/test_secondary.cpp`: 7 new cases, 18 secondary cases pass (`./build/tests/plush_tests -tc="secondary*"`):
  parsing, round trip and errors of `radii`, `rest`, `friction`, `max_swing`; per-joint radii and tapered segments;
  resting contact (outside, tip step 0.002 mm per frame once settled); a moving collider carries the chain (no
  reversal); `max_swing` bounds the turn per frame; a collider holds a joint beyond the angular limit.
- Engine fixes (rest chains only unless noted): the angular limit yields to contact (a joint that a collider pushed in
  this or the last step is not clamped; once free its limit shrinks from the angle it had at `kLimitReturn` = 12 1/s;
  `State::hit`); non-rest path with `radii`: a tapered segment is tested where its surface is nearest, and at its
  middle when its thick end is the first joint.
- Cause of the calm-frame noise (traced per step with temporary prints, `ringlets_back_b_00` f50-51): the forearm
  pushed the tip past the 30 degree limit; clamp and push alternated and the tip slid round the limit cone to its far
  side in 2 frames (25 mm per frame).

Tip noise, same bakes, `tools/tip_noise.py <bake> <static bake>` (mm; "double" = two reversals in a row = jitter; a
single reversal is also a tip pushed out and coming back):

| Bake | Calm frames: worst single reversal | Chain-frames over 0.5 mm (calm) | Worst double reversal, locks | Chain-frames double over 0.5 mm (with the bun's 9) |
|---|---|---|---|---|
| Round 1 candidate | 4.8 | 21 | 4.3 | 30 |
| Prototype `p6` (before the fix) | 18.2 | 25 | 4.0 | 32 |
| Prototype `p7` (after the fix) | 7.3 | 17 | 4.6 | 28 |

`p7`'s 7.3 mm (f51) is one out-and-back of a tip that the passing forearm pushes (traced: smooth). Noise is at the
round-1 level, not below it. Friction 0 / 8 / 40 gives the same picture (not the lever). `p7` measure (every 3rd
frame): as `p6` (curtain 48.4 mm / 402 vertices, cap 12.4 mm, vest edges 1-4 vertices 36-46 mm, ears 5-7 mm).

Seen in preview frames (`tools/preview.sh`, view `arm`, f22-75; reported to the Supervisor 21:06Z, no answer yet):
f24-28 her right arm reaches forward for the cup, the puffy sleeve rises under `ringlets_side_r00`. Released and
round 1: the lock sinks into the sleeve. `p7`: it stays out, is lifted with the sleeve (tip up to 26 cm off its
hanging place), touches the cheek near the glasses at about f26-28, then lies draped on the forearm (f32-75). Kept
as is; show it in the arm-raised close-up. Possible trade if asked: thinner chain radii against the arm colliders.

### Facts for the groom port (candidate master inspected in Blender)

- Every figure mesh is a child of the rig with an Armature modifier and vertex groups (deform bone names). Use the
  evaluated meshes (`ob.evaluated_get(deps).to_mesh()`, groups survive): `body_skin` has a Mask modifier (skin under
  the garments is hidden), garments have three Shrinkwrap modifiers. Leave out of the figure: hair objects,
  `garment.collider.*` (`ps_collision_proxy`), `WGT-*`, and the face parts `eye* brow* lash* lid* mouth* glasses*`
  (`glasses_lens` is bone-parented, no groups). Ears: `ear.L`, `ear.R`, one group each.
- `build_character.py:331` calls `GROOM.bind(rig, groom, head_bone, chest_bone, binding)` after the garments exist.
  Hair objects carry `ps_contact` (the stored contact spec); chain objects carry `ps_dyn`; the rig's `ps_dynamics`
  holds chains (`bones`, `tip`, Blender world coordinates) and colliders.
- The prototype (`tools/proto_contact.py`) is the reference for the port: its five sphere sets (head without ears,
  ears, torso = everything but head, arms, hands, legs; arms; hands), `skin_spheres` arguments, sphere bone = the
  vertex's dominant group, chain radii = `chain_radii(vertices with >= 0.5 chain weight, joints, percentile 100,
  floor 6 mm)`, root radius 0, each radius capped by the joint's rest clearance to the colliders on the head bone;
  lock chains: `contact = {solid: [], segments, anchored_gravity, radii, rest, friction 40, max_swing 12}`, no
  `colliders` key (= all); bun chains keep `head, torso, shoulder_l, shoulder_r`.

### Next steps (in this order)

1. Port into `groom_contact.py` (`bind_contact`, validation, `test_hair_contact.py`, `docs/SECONDARY_MOTION.md`:
   also document `radii`, `rest`, `friction`, `max_swing` and the limit rule there): collider `"fit": "skin"` with
   `groups` and/or `objects`, `exclude_groups`, `spacing_m`, `radius_m`, `pad_m`, `reach_m`, `min_radius_m` (no
   `bone`); `"radii": {"percentile", "floor_m"}`; `"rest": true | {"friction", "max_swing"}`; `"figure":
   {"exclude": [...]}`. Update the candidate override; build (`run_shot.py --stages prepare`), bake, measure all 286
   frames; compare with `p7`.
2. Static hair that hugs the head but carries chest weight through `binding.blend_z` (cap lower edge 12 mm, temples
   2-6 mm against skin and ears: they shear when the head tilts): a contact key that binds named structures to the
   head only (e.g. `"head_bound": ["cap", "temple_*", "crown", "fringe"]`), then measure.
3. Curtain chains (B3; `hair_curtain` 36,000 vertices, `hair_back_sections` 7,184; the largest measured item). In
   `bind_contact`, after `G1.bind`: K chains spread over the azimuth of the vertices below where the hair leaves the
   scalp (the head centre must be stored with the contact spec at build: `frame["centre"]` in `groom_r6.build`), each
   along the sheet's centre line of its sector, bones `DYN-<structure>.<k>.<n>` parented to the head bone; a vertex
   is weighted to the two neighbouring chains by azimuth and along the chain by `groom._chain_weights`, blended in
   from the static weights over the first bone; chains get `anchor` weights from `blend_z` like locks, radii from
   the sheet thickness, the same `contact` block. ONE cheap preview frame (`tools/preview.sh`, views `back` and
   `shoulder`, a frame with the head tilted, e.g. f28 and f241) before any long render; if the curtain shears
   between chains, report at once (condition 2).
4. Lock root vertices (static part of back_05, back_b_02: 1-3 vertices, 43-47 mm) and the vest-edge single vertices.
5. Close-up clips (side, back, over-shoulder, arm-raised: `tools/closeup.py` views `side`, `back`, `shoulder`,
   `arm`), strict sheet, README (state the 3-8 mm rest gap and the lifted lock), CHECKPOINT with `measure_body.py`
   for released (`s010/build/runs/<id>/bake.json`) and candidate, per surface, all frames; `tools/ready.py`.

## Round 1 (not accepted): hand / ear / follow

Owner defects (2026-11-21 ~12:30Z): the girl's hand goes into her hair and her hair into her hand; hair goes into
her ear; hair moves independently of the body.

| Target | Released 0.14.0 | Round 1 candidate | State |
|---|---|---|---|
| Hand vertices inside hair | 28 frames, worst 6.7 mm | 0 frames | met |
| Static hair inside the ear (cap, temples) | every frame, 4.4-7.1 mm | 0 | met |
| Moving ringlets inside the ear | side_b to 10.5 mm (188-216 fr), outer to 9.3 mm (123 fr) | side_b to 7.6 mm (111-169 fr), outer to 5.2 mm (113 fr) | open, reduced |
| Back / outer ringlet tips vs body-anchored pose | 42-47 mm max, 25-26 mm rms | 5-28 mm max, 1.6-5.8 mm rms | met |
| Bun vs head | 35.5 mm max, 15.3 mm rms | 17.8 mm max, 6.8 mm rms | improved |

## Current overrides

- `candidates/girl_auburn_bun_glasses.hair_contact.override.json` on girl 0.14.0 (round 1 keys; not a version, not
  published; round 2 keys not added yet).
- Shot: `episodes/e909_two_char_acting/shots/s010_t183/shot.scene.json` (s010 with that cast entry only).

## Sheets and clip (round 1)

- Clip: `T-183_s010_f060-228_before_after.mp4` (side by side), `T-183_s010_f060-228_girl_zoom_half_speed.mp4`.
- Strict sheet: `T-183_strict_sheet.jpg` (frames 26, 63, 103, 115); tiles in `sheet/before/`, `sheet/after/`.
- Read sheets as crops of at most 1024 px (the tiles are 768 px). Notes per frame: `README.md`.

## Environment notes for a fresh session

Engine: `cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build build -j4` (8 min). Blender: the bpy
module; `tools/bpy_blender.py` is not executable, so pass `--blender` a small wrapper script outside the repository
(`exec python3 /home/user/Animation/tools/bpy_blender.py "$@"`). Run ids are never reused (`--run-dir <new id>`).

- Prepare (builds both packages and the girl's master, 3.5 min per shot):
  `python3 pipeline/production/run_shot.py --shot episodes/e909_two_char_acting/shots/s010_t183/shot.scene.json
  --blender <wrapper> --stages prepare --run-dir <id>` (the same for `shots/s010/` = released). `--shot` is the
  scene file, not the folder.
- Bake (14 s; about 60 s with the sphere colliders): the same with `--stages bake --bake-engine
  build/apps/render-cli/plush-render`; the bake is `build/runs/<id>/bake.json`.
- Prototype: `python3 docs/evaluation/characters/T-183/tools/proto_contact.py <name> radius_pct=100 [step=3]
  [nomeasure=1] [friction=..]` (1.5 min with `step=3`); output in `s010_t183/build/exp/<name>/`.
- Trace: `tools/trace_chain.py <exp dir> <chain> A-B`, `tools/near_colliders.py <exp dir> <chain> <joint> A-B`.
- Preview frame (47 s at 640x360, 8 samples): `tools/preview.sh <wrapper> <out dir> <name> <bake> <cast.json> <view>
  8 <frames...>`; a prototype bake renders with the candidate's master (`s010_t183/build/cast.json`) as long as the
  bones are the same (not for new curtain bones: those need the groom build).
- Do not print object lists of a master (`WGT-*` widgets: hundreds of lines); filter by name.
