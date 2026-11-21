# T-183 round file: hair contact

Branch `t-183-claude-hair-contact`. Round 1 input `7135087`; round 2 input `2664f7e`.

## Round 2 (in progress): hair against the whole body and the garments

Session 4 state: see "Session 4" below first (final candidate measured; `sheets` and the curtain blend are gone).

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

### Session 3 (2026-11-21/22, `4ebed76` and the commit after it): groom port, measure corrected, curtain chains tried

**Read this section first; it replaces the numbers and the next steps above.**

- Groom port (`pipeline/charsys/groom_contact.py` `bind_contact`, called by `groom_r6.bind` with the binding): keys
  `"fit": "skin"` colliders, `figure`, `radii`, `rest` (module docstring, `docs/SECONDARY_MOTION.md`; `sheets` was
  removed in session 4).
  The candidate override uses five skin sets (head 150 spheres, ears 102, torso 298, arms 157, hands 97 = prototype
  `p7`), `radii` (percentile 100, floor 6 mm), `rest` (friction 40, max_swing 12). `test_hair_contact.py` 73 checks (86 with the sheet checks, removed in session 4)
  (the skin sphere checks need the bpy module).
- Root radius (new, measured): the root joint takes the next joint's radius, capped by its own rest clearance to the
  head-bone colliders (was 0). With 0 the first segment was a thin cone; the two short `side_b` locks start beside
  the ears (joint 1 has clearance 0) and turned 5-7 mm into them in 82-113 frames. With the rule: ears 0 frames
  (tried first as a package edit, `exp/rootr`). A tighter `limit_deg` (12, 6) for those locks changed nothing: the
  turn comes from the chest anchor, not from the swing.
- Curtain chains (B3) built as `sheets` (13 chains x 4 bones, run `s3c`), ONE preview frame f28 (back, shoulder): the
  curtain is hidden under the ringlets in both views. Numerically it shears (`tools/sheet_stretch.py`): mesh edges up
  to 3.82 x rest length (released, static: 1.84 x), neighbouring chain tips 0.3-3.7 x their rest spacing; and the
  curtain's count hardly moved (9.6 mm / 130 frames against 11.1 mm / 165 frames). Reported to the Supervisor
  (condition 2). **The candidate does not use `sheets`**; the key and its code were removed in session 4.
- Tried and removed: binding the scalp cap to the skin under it (weights of the nearest skin vertex): 130 instead of
  131 vertices, so the code is gone. `head_bound` (cap to the head only) likewise.
- `tools/measure_body.py` corrected (three rules, `--legacy` gives the old measure; released and candidate are always
  measured with the same rules):
  1. Rest match: a vertex inside the figure at rest that sits at its rest distance (0.5 mm) from the same part does
     not count (temples tucked behind the ear are rigid with the ear; they counted 3-6 mm whenever a raised shoulder
     closed one of their ways out).
  2. Open borders: "behind the nearest face" counts only under the face (within 45 degrees of its normal), not beside
     its border. The skin mesh is cut away under the garments: 4 tip vertices of the curtain hanging in the air below
     that border were the "curtain 48 mm".
  3. Enclosure: behind a face with nothing beyond it counts only when fewer than two of the 26 directions are free
     (a lock vertex in the open air "behind" an inside-out vest trim was the 35-46 mm single vertices).

#### Measure, all 286 frames, corrected rules (`tools/measure_table.py <label>=<measure.json> ...`)

| Surface | Released 0.14.0 (run `rel3`): frames, max mm, most vertices | Candidate (run `s3f`): frames, max mm, most vertices |
|---|---|---|
| All | 286 of 286, 65.9, 8,496 | 268 of 286, 13.1, 436 |
| Vest | 282, 65.9, 2,079 | 0 |
| Blouse | 286, 61.9, 5,396 | 0 |
| Hands | 95, 48.4, 240 | 0 |
| Blouse cuffs | 115, 31.2, 37 | 0 |
| Shorts | 74, 31.0, 463 | 0 |
| Ears | 195, 11.8, 212 | 0 |
| Skin | 268, 25.7, 470 | 268, 13.1, 436 (cap at the nape 126 vertices / 268 frames / 13.1 mm; curtain lower edge 404 vertices / 165 frames / 11.1 mm) |

With the old rules (`--legacy`): released 286 of 286 frames, 65.9 mm, 8,529 vertices; candidate 286 of 286 frames, 48.5 mm,
452 vertices (the 4 curtain tip vertices below the skin border and the pockets behind the ears count again).
Curtain mesh of the candidate (static, as released): 107994 edges; longest 1.84 x rest (f29), shortest 0.68 x (f285); over the frames: 99.9 % of edges under 1.81 x, 99 % under 1.74 x, 1 % under 0.74 x.

What is left in the candidate, by cause:

1. Scalp cap at the nape, about 130 vertices, 268 frames, true depth 2-6 mm (the measure reports up to 13: second
   shortest of the fixed directions). The body's own neck skin folds over the hairline when the head tilts (two skin
   layers 0-3 mm apart; debug: nearest face `behind`, `body_skin` again 0-3 mm beyond). Not a hair problem: body
   skinning, outside the T-183 write-set. It lies under the curtain and the ringlets.
2. Curtain lower edge against the neck base, up to 404 vertices, 165 frames, 11 mm: head-dominant vertices of the
   2 cm thick sheet at height 0.69-0.72 turn into the neck base with the head. Inner face, not visible from outside.
   Not tried: a per-structure `blend_z` for the curtain (lower edge follows the chest earlier; risk: the head then
   turns into the band), 5 min per build.

### Session 4 (2026-11-21/22): Supervisor decisions, final candidate

Supervisor decisions on session 3's questions: (a) the three measure corrections are accepted, `--legacy` stays and
both rule sets are reported; (b) the per-structure curtain blend is tried once; item 1 (nape cap against the neck
skin fold, body skinning) is accepted and logged as a follow-up outside T-183; (c) the unused `sheets` key and code
are removed.

- `sheets` removed (`groom_contact.py`, its tests, `docs/SECONDARY_MOTION.md`); `bind_contact` takes no binding again.
- Curtain blend, ONE build and ONE full measure (run `s4bzb`, contact key `blend_z {"curtain": [0.66, 0.78]}`, the
  curtain's 36,000 static vertices re-weighted; the spec's binding is [0.60, 0.72]): curtain against the neck base
  6.7 mm / 167 frames / 188 vertices (final candidate: 11.1 mm / 165 / 404), but the curtain then lags the head
  beside the left ear: `hair_curtain > ear.L` 10.2 mm, 210 frames, 305 vertices (final candidate: 0), and the
  longest curtain edge 1.99 x rest (1.84 x). The ear is visible, so the blend is **dropped**: key, code, tests and
  the override entry are gone (commit `curtain blend_z tried once and dropped`). Item 2 stays as the hidden inner
  face of the curtain.
- Final candidate = the override as at `42d0aee` (five skin sets, `radii`, `rest`), rebuilt with the code without
  `sheets`: run `s4f` (prepare) / `s4fb` (bake). Corrected rules: the same numbers as `s3f` on every surface (table
  above: 268 of 286 frames, 13.1 mm, 436 vertices; skin only). `--legacy`: released 286 of 286 frames, 65.9 mm,
  8,529 vertices; candidate 286 of 286, 49.8 mm, 452 vertices (session 3 wrote 48.5 mm for the same single curtain
  tip in the air below the skin border; this session measured 49.8). Released re-measured as `rel4b`: as `rel3`.
- Tip noise on the final candidate (`tools/tip_noise.py`, static bake = `build/shot.resolved.scene.json` with
  `"dynamics": false` on the girl, written beside it so the package paths resolve): calm frames worst single
  reversal 7.3 mm (f51, the forearm passing), 17 chain-frames over 0.5 mm; worst double reversal of a lock 3.3 mm;
  30 chain-frames double over 0.5 mm with the bun's 9. Level of `p7` and of round 1 (table in "Session 2"):
  condition (1) holds with the new root radius.
- `origin/main` (55b5f51) merged; `release_rule.py`, `test_release_rule.py`, `GENERATOR_PINS.md` keep both the
  T-184 and the T-183 entries. Main changed no code since the last merge.
- Close-up clips (`clips/T-183_r2_<view>_f<A>-<B>.mp4`: arm 10-58, side 50-98, back 60-108, shoulder 100-148; every
  second frame, released | candidate, once at real and once at half speed) and the strict sheet
  (`T-183_r2_strict_sheet.jpg`, 840x1024, tiles `sheet_r2/`): `README.md` ("Clips and sheet"). `tools/closeup.py
  --step=N` keeps every Nth frame and renumbers (the renderer has no frame step). A close-up frame costs 40 s at
  640x360, 8 samples (two renders side by side on 4 cores: 200 frames in 65 min).
- **Seen in the close-ups (new, reported in the CHECKPOINT):** upright (f10-18, f148) the candidate looks like the
  released hair lying on the cloth. While she leans to the cup (about f24-132) the back ringlets cannot pass through
  the back, shoulder and sleeve any more: they pile up on the bent back, fan out and stand off the body (bigger
  silhouette behind the head, ringlets across each other, one kinked ringlet with a fibre tuft at f116-132 from
  above). The measure is 0 on cloth, hands and ears, but the look is wider and less tidy than released. The lifted
  right side lock (f26-28) is captioned in the arm clip.

### Next steps

1. Supervisor / owner verdict on the CHECKPOINT (README table, clips, sheet).
2. Follow-up outside T-183 (logged by the Supervisor): the neck skin folds over the hairline when the head tilts
   (body skinning; item 1 above).
3. If the lifted right side lock (f26-28, `ringlets_side_r00` on the sleeve, at the cheek) is not wanted: thinner
   chain radii against the arm colliders (not tried).
4. If the fanned hair in the lean is not wanted: levers not tried are thinner chain radii (percentile below 100),
   smaller torso spheres (radius 45 mm, pad 2.5 mm), and less resting friction (40) so that locks slide off the
   back instead of staying where they were pushed. Each is one build (5 min) + bake + measure (2.5 min) + a few
   close-up frames (`tools/preview.sh`).

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

- `candidates/girl_auburn_bun_glasses.hair_contact.override.json` on girl 0.14.0 (not a version, not published):
  ear keep-out, follow tuning, and the round 2 contact block (five skin collider sets, `radii`, `rest`).
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
- Session 3 runs: released `s010/build/runs/rel3`, candidate `s010_t183/build/runs/s3f` (build logs with the
  bind report: `runs/<id>/logs/build_girl.log`, line `groom contact:`). Try chain keys without a rebuild:
  `tools/tweak_chains.py <name> '<chain pattern>:<key>=<number>'` (bake in `build/exp/<name>/`). Full measure: 2.5 min
  per bake on 4 cores. The build cache does not see a change of generator code (`groom_contact.py`): the same
  override gives "cached"; delete `build/masters/<id>` and `build/packages/<id>` named in `build/cast.json` (girl) to
  rebuild. A scratch script must not be named like a standard module (`inspect.py` breaks the bpy import).
- Do not print object lists of a master (`WGT-*` widgets: hundreds of lines); filter by name.
