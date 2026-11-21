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

Tip noise (`tip_noise.py`, zigzag = a tip that reverses direction frame to frame, mm): round 1 max 67, 109
chain-frames over 1 mm; `p6` max 25, 165 chain-frames (the bun's 19 mm at f57-62 is the head's own jerk, same in
round 1). In calm frames (181 of 284): round 1 worst 4.8 mm, 21 chain-frames over 0.5 mm; `p6` worst 18 mm, 25.
The first prototype had 259 mm / 753: caused by spheres placed outside the body (inside-out trims) and by the
closest-point segment lever; both fixed. Condition (1) is not closed yet: see next steps 1-2.

### Next steps (in this order)

1. Engine unit tests in `tests/test_secondary.cpp` for `radii`, `rest` (a chain resting on a collider whose kinematic
   target is inside it stays outside and still, tip step under 0.1 mm per frame once settled; a collider that moves
   under it carries it), `max_swing`, parsing and round trip; the calm-frame noise of `p6` (side_00 f75, back_b_00
   f50: hands or forearm near) to be traced with `trace_chain.py` and closed.
2. Port the prototype into `groom_contact.bind_contact` (Blender data: evaluated meshes bound to the rig, vertex
   groups for the dominant bone): spec keys under `hair.dynamics.contact`: collider `"fit": "skin"` with `groups`
   and/or `objects`, `spacing_m`, `radius_m`, `pad_m`, `reach_m`, `min_radius_m`; `"radii": {"percentile", "floor_m"}`;
   `"rest": {"friction", "max_swing"}`; validation, `test_hair_contact.py`, `docs/SECONDARY_MOTION.md`. Update the
   candidate override; build, bake, measure all 286 frames.
3. Static hair (B3): skirt chains for curtain, back sections (and the cap's lower edge) from where the hair leaves the
   scalp; one cheap preview frame first. Temples against the ear: extend the ear keep-out margin or bind check.
4. Lock root vertices (static part of back_05, back_b_02: 1-3 vertices, 43-47 mm at f19) follow the curtain fix.
5. Close-up clips (side, back, over-shoulder, arm-raised) and strict sheet, README (state the 3-8 mm rest gap),
   `tools/ready.py`, merge `origin/main`.

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
(`exec python3 tools/bpy_blender.py "$@"`). Candidate master build 2 min, bake 14 s (about 60 s with the sphere
colliders), run ids are never reused (`--run-dir <new id>`).
