# T-183 round file: hair contact

Branch `t-183-claude-hair-contact`. Round 1 input `7135087`; round 2 input `2664f7e`.

## Round 3 (in progress): scene props, real shots, the fan-out

Owner verdict on round 2 (2026-11-22 ~04:20 CET, on the T-187 paper-boat test `episodes/e912_paper_boat`): not final,
the girl's hair goes through the table and still into her own body. Round 3 goal: zero penetration in real shots
(e912 s010 / s020 / s030, e909 s010), per frame per surface (body, garments, props), real shots must use the
candidate, and the fan-out of the back ringlets in the lean visibly better. Design approved by the Supervisor
2026-11-22 ~11:48Z: write-set + `episodes/e912_paper_boat/shots/s0{1,2,3}0_t183/**`; the white-haired girl is in
scope; lock-against-lock opt-in and deterministic. **`engine/scene/scene.cpp` and `engine/scene/scene.h` are granted**
(R5 ~11:53Z, R6 ~12:07Z; OWNERSHIP row on main `1632da5`): hair against the neighbour character IS part of zero
penetration; neighbour + carried-prop colliders through a callback, opt-in, bit-identical when absent (prove it with
an existing-golden check), report the bake slowdown factor in READY, main merged before READY.
**Supervisor from round 6 on: `session_01NPjxePvWAMsLopzSs1fMXB`** (the R5 session confirmed the rotation). Other tasks own `engine/anim/hand_shape.*`, `animation.*`
(T-190), `engine/scene/collision.*` (T-191), `engine/scene/face_layer.*` (T-192): not touched.

### Session 6 (2026-11-22): state at `415a594` and the commit after it

Checked: T-187 rendered the released hair (e912 casts `auburn: version current` = 0.14.0, no override).
`origin/integration/t-187` (main `2869eae` + the T-187 merge, `44f9fb3`) is merged into the branch (`43022be`) and
pushed; main then landed as `44f9fb3` and `origin/main` `5010873` is merged too (ledger, T-193 docs). Merge main once
more before READY. T-184 and T-183 entries
are both in `release_rule.py` / `test_release_rule.py`; `GENERATOR_PINS.md` has the T-184 row.

Built (all opt-in, absent keys = the previous path; 270 engine tests pass):

- `engine/anim/secondary.{h,cpp}`: collider type `box` (world space, `min` / `max`, `radius` = edge rounding) and
  the scene override key `dynamics.colliders` (docs/SECONDARY_MOTION.md "Scene colliders"). The solver's shape
  queries go through `nearestOn` / `nearestSeg`; a sphere or capsule takes the same calls as before.
- Chain key `contact.locks` (number in [0, 1], 0 = off): lock against lock, joints only, fixed chain order, half the
  overlap per step. Unit-tested; **not yet tried on the hair** (no groom key yet: try it with `tweak_package.py`).
- `tools/derive_shot.py <shot.scene.json> ...`: writes `<shot>_t183/shot.scene.json` = the source shot + the
  candidates in `production.cast` + the scene's box objects as `scene.<name>` colliders of those characters.
  `--check` compares. e909 `s010_t183` is re-derived from the new s010 (T-188); e912 `s010_t183`, `s020_t183`,
  `s030_t183` are new.
- `candidates/girl_white_hair_blue_dress.hair_contact.override.json` (on her 0.1.0 `versions/0.1.0/spec.json`): the
  auburn girl's keys and values, `buns` instead of `bun`. Builds (47 chains).
- `tools/measure_props.py <bake> --character=<name> [--others]`: hair against scene boxes (exact), props (primitive
  shapes at the baked transforms) and the other characters' figures. `tools/tweak_package.py`: any chain key on a
  built shot without a rebuild. `tools/r3_run.sh`: prepare + bake + both measures for one shot.

Measured (limit 1 mm; `props` every frame, own body every 2nd frame for the candidate, every 4th for released;
"rel" = shots `sNNN`, runs `rel6` / `rel6b`; "cand" = shots `sNNN_t183`, runs `r3b` / `r3bb`):

| Shot, hair of | Surface | Released | Candidate |
|---|---|---|---|
| e912 s010 auburn | table_top | 12.5 mm, 164 fr, 616 v | 0 |
| | the boy (hoodie / skin / hand.R) | 68.1 / 59.6 / 34.4 mm, 166 / 33 / 29 fr | 53.9 / 53.1 / 0 mm, 36 / 3 / 0 fr, all in f1-36 (walk-in, before the rendered range f41+) |
| | own blouse | 86.2 mm, every frame, to 22,376 v | 20.4 mm in f101, 9.1 mm in f161 (`ringlets_side_r00`), 8.9 mm in f79 (`ringlets_side_00`): one frame each |
| | own skin (curtain inner face, nape cap; round 2 items) | - | curtain 9.8 mm, cap 6.2 mm, `ringlets_outer_00` 8.8 mm (7 v), every frame |
| | ear.L (`ringlets_side_b`) | - | 3.0 mm, 59 of 92 fr, 1-4 v |
| e912 s010 white | table_top | 12.5 mm, 162 fr, 465 v | 0 |
| | auburn (blouse / hand.R / cuff) | 48.9 / 7.1 / 7.2 mm, 23 / 1 / 6 fr | 40.7 / 11.6 / 8.9 mm, 19 / 2 / 6 fr, all in f11-33 |
| | own bodice / skin | 42.8 mm / 22.1 mm | 0 |
| | own ears (static `back_mass`, `back_under_06`, `_00`) | (10.1 mm in s020) | 10.3 / 9.9 / 5.4 mm, every frame: the ear keep-out does not reach `back_mass` (not looked at yet) |
| e912 s020 auburn | table_top | 12.5 mm, 57 fr | 0 |
| | the boy (hoodie / strap / skin / hand.R) | 74.1 / 70.0 / 62.0 / 31.2 mm, 123 / 8 / 65 / 33 fr | 71.7 / 75.2 / 49.9 / 52.0 mm, 118 / 8 / 50 / 4 fr |
| | boat, boat_end_a (in her hand) | 13.0 / 14.8 mm, 55 / 41 fr | 12.8 / 15.0 mm, 37 / 48 fr |
| | white-haired girl's skin | 23.9 mm, 1 fr | 23.9 mm, 1 fr |
| | own skin (cap / curtain / `ringlets_outer_00`) | - | 25.5 / 20.9 / 26.6 mm, 103 / 101 / 18 of 104 fr, to 362 / 756 / 55 v: the head tilts further than in e909 (round 2 item 1, the neck skin; bigger here) |
| | own blouse | 88.4 mm, every frame | curtain 18.0 mm f135, collar 12.2 mm f135, `ringlets_back_00` 10.9 mm f133: one measured frame each |
| e912 s020 white | table_top | 12.5 mm, 162 fr | 0 |
| | auburn (hand.R / blouse / cuff) | blouse 8.8 mm, 9 fr | 26.7 / 22.0 / 20.6 mm, 2 / 9 / 2 fr (f34) |
| | own bodice / skin | 32.1 / 17.0 mm | bodice 0; cap > skin 5.2 mm, 14 fr |
| | own ears (static) | 11.5 / 10.1 mm | 10.2 / 9.4 / 5.2 mm, every frame |
| e912 s030 auburn | the boy (skin / hoodie / hand.R) | 47.8 / 42.8 / 33.7 mm, 15 / 46 / 17 fr | 47.6 / 34.8 / 20.7 mm, 24 / 32 / 11 fr |
| | boat_end_a, boat (in her hand) | 14.8 / 12.9 mm, 11 / 9 fr | 13.4 / 9.0 mm, 10 / 6 fr |
| | own blouse / vest | 72.3 mm, most frames | f93 only: `ringlets_back_00` 22.0, `outer_b` 19.1, `side_r00` 14.5 mm, vest 8.4 mm (the stand-up) |
| | own skin (cap) | - | 22.0 mm, 73 of 83 fr, to 389 v |
| e912 s030 white | table_top | 12.5 mm, 9 fr | 0 |
| | auburn's blouse | - | 18.7 mm, 8 fr (f31) |
| | own bodice | 47.0 mm, 33 of 42 fr | f93 only: `outer_locks_00` 23.0, `back_locks_00` 13.8 mm |
| | own ears (static) / cap > skin | - | 11.2 / 9.2 / 7.3 mm every frame; 8.8 mm, 39 fr |
| e909 s010 girl | own body (every 2nd frame) | round 2: 286 of 286 fr, 65.9 mm | skin only: cap 12.4 mm (134 of 143 fr), curtain 11.0 mm (82 fr); cloth, hands, ears 0 (as round 2) |
| | **cup (prop, never measured before)** | not measured (no released run in session 6) | 23.9 mm, 157 of 286 fr, to 186 v (worst f75) |
| | the boy's hand.R | not measured | 11.8 mm, 18 fr (f139) |
| | table_top, table_leg | not measured | 0 |

All summaries: `T-183_r3_measures.json` (`tools/r3_summary.py <log dir> <out>`; `rel` = released, `r3b` = candidate).

Read: the table is solved for both girls by the static boxes. What is left needs shapes that move: the neighbour
(the boy beside her, 0.40 m seats) and the boat in her own hand.

### Session 7 (2026-11-22, continuation session): neighbour / prop colliders, the pops, `contact.carry`

Built and committed (`b792ed1`, the commit after it):

- **Scene colliders that move** (open item 1): collider keys `"character"` (+ `bone` of that other character) and
  `"prop"` (oriented box / sphere / capsule in the prop's frame) in the scene override; the solver takes their frames
  per step from a callback (`SpringChainSolver::External`), `scene.cpp` resolves the carriers at load and passes
  kinematic poses (a memo shared by the characters) and a kinematic `propWorlds`. A scene without such a collider
  calls the solver as before: `tests/test_bake_golden.cpp` unchanged and passing, e912 `s020_t183` without the new
  colliders bakes to the same SHA-256 with the binary before and after (`80e99129...`). Docs: SECONDARY_MOTION.md
  "Scene colliders". Tools: `tools/neighbours.py` (the `skin_spheres` fit on the neighbours' package meshes, where the
  hair comes within 0.1 m of them in a bake; prop boxes from the assets), `derive_shot.py --props
  --neighbours-from=<bake>` (recorded in `x_t183.options` / `.neighbours`; `--check` keeps the fitted spheres),
  `tools/r4_run.sh` (derive without neighbours, bake, derive with them, bake, both measures).
- **The one-frame pops are body snaps of the source animation** (open item 2), measured on the kinematic bones in
  the bakes (`snaps` numbers: bone turn in degrees / pivot travel in mm within ONE frame):
  e912 s010 auburn: hands 109-281 mm, forearms 31-147 deg at f79, 98, 101, 116, 120, 131, 135, 146, 150, 161, 165,
  180 (the fold cycle); s020 auburn: head 95 deg at f109 (36 / 52 at f110-111), 41 / 115 / 41 / 52 deg at f133-136,
  chest 35 deg at f133; s030: every character moves 1.1-1.6 m at f93 (a cut inside the shot). The traced pops (s010
  f79 / f101 / f161, s020 f133-135) are exactly these frames. Not in the T-183 write-set (T-187 shots, gaze chain,
  clips): logged for the animation side, reported to the Supervisor.
- **`contact.carry`** (chain key, opt-in, with `rest` + `max_swing`; `groom_contact.py` `rest.carry`; both candidate
  overrides now carry it): the `max_swing` bound yields to the speed of the collider that pushes the joint, so a
  forearm that crosses the chest within a frame takes the lock along. e912 s010 auburn f76-182 every frame: blouse
  30.7 mm / 5 fr and 8.9 mm / 2 fr -> nothing over 1 mm against garments. Off = bit-identical.
- First numbers with the scene colliders, before `carry` (e912 `s020_t183`, run `r4nb`, every frame, auburn):
  boy hoodie 71.7 mm / 118 fr -> 40.2 mm in f110 only; strap 75.2 -> 0; hand.R 52.0 -> 0; boat 12.8 mm / 37 fr and
  boat_end_a 15.0 mm / 48 fr -> boat 6.0 mm in f110 only; white-haired girl against auburn -> 0 (all surfaces).
  **Not chains:** boy skin 49.9 mm / 43 fr is `hair_fringe` / `hair_crown` / `hair_flowers` (rigid with her head):
  her head overlaps the boy in the source animation. Bake 52-54 s without, 56 s with the 520 colliders.

**Later in session 7** (commits up to the one that adds this paragraph; main `99f1da6d` is merged, the engine was
NOT rebuilt after the merge: build first, run the golden check and all tests again):

- Supervisor decisions (R6, 13:05-13:12Z): body snaps are not fixed here; the table gets a column "frames where the
  source body snaps" and ONLY those frames (+-1) are outside the zero-penetration criterion; rigid hair parts inside
  the boy (her head overlaps his: T-191 staging, parked) are listed apart; `contact.carry` approved; the golden proof
  goes into READY; do not change e912 shot files (the `_t183` copies are fine); T-194 builds a render-time push-out
  (`shot_render.py`, `hair_pushout.py`: not ours; ordering questions go through the Supervisor). **New targets:** e909
  `s010_t183` hair inside the CUP 23.9 mm / 157 fr and in the boy's hand.R 11.8 mm / 18 fr; e912 s030 f93.
- Candidates rebuilt with `rest.carry` (e912 packages `auburn_ec423c7c2fcfbcf1`, `white_7ded3d4107990fd4`); all four
  shot copies derived with `--props` and neighbours (`tools/r4_run.sh`, runs `r5a` without / `r5b` with neighbours),
  every frame measured. Numbers per pair, all frames and calm frames: **`T-183_r5_tables.json`** (`tools/r5_table.py`,
  snap frames from `tools/snaps.py`: > 45 deg or > 100 mm in one frame; none in e909). Read of the calm frames:
  - e912 s010 auburn: table 0, blouse 0, boy 0 except `ringlets_back_00` > hoodie 2.2 mm, 2 vertices, f12-16
    (walk-in, before the rendered f41+); own skin as before (curtain 9.8, cap 6.2, `ringlets_outer_00` 8.8 mm / 8 v,
    `ringlets_side_b` > ear.L 3.0 mm / 4 v). White: only the static ears.
  - e912 s020 auburn: boy hoodie / strap / hand, boat, table, own blouse and vest all 0 in calm frames (all their
    events are on f109-111 and f133-136). Left: rigid `hair_fringe` / `crown` / `flowers` in the boy's HEAD skin
    (49.9 mm, f1-160: the heads overlap) and with them `ringlets_side_00` > boy skin 8.3 mm f78-80; own skin: cap
    25.5, curtain 20.9, `ringlets_outer_00` 2.9 mm / 48 fr, `ringlets_side_b` > ear.L 6.0 mm / 103 fr, curtain >
    collar 1.6 mm, `back_sections` 5.7 mm. White: 0 against everything but her own ears and cap (5.2 mm).
  - e912 s030 auburn: f93 is the cut (all three characters move 1.1-1.6 m in one frame); calm frames:
    **`ringlets_side_00` > blouse 7.7 mm in f1-10 (80 v): not looked at yet** (the start pose: probably squeezed
    between arm and chest during the preroll), curtain > vest 3.5 mm f64-73, collar 1.8 mm. White: f93 only + ears.
  - e909 girl (all 286 frames, no snap frames; bake 29.1 s without / 30.1 s with the neighbours): own body cap 13.1
    mm / 268 fr and curtain 11.1 mm / 165 fr only (as round 2), garments 0, boy's hand.R 0; **cup 23.9 mm / 143 fr: the cup
    is a cylinder primitive and `neighbours.prop_boxes` writes boxes only**.
  - Bake seconds without / with the neighbour spheres (same run, 4 cores shared with other jobs, so only a first
    reading): s020 59.1 / 56.1, s010 23.6 / 29.6, s030 20.6 / 21.1. Take the factor again on a quiet machine,
    three bakes each, also against the binary before the change.
- Fan-out levers (open item 3), e909, `tools/tweak_package.py` + `tools/fan_out.py`, f24-132 every 4th
  (`T-183_r5_tables.json` `fan_out_e909_s010`): out back / side cm2, crossings, fold mean / max: released 851 / 891,
  16.2, 56 / 80; candidate 1008 / 1101, 27.6, 128 / 171; joint 1 of the back ringlets 12 mm: 981 / 1093, 27.8,
  108 / 171 (own body: cap and curtain only, collar 1.0 mm in one frame); joints 0 and 1: 973 / 1093, 26.3,
  104 / 171; `locks` 0.5: 1024 / 1108, 23.8, 128 / 171; `locks` 1.0: 1139 / 1220, 24.8, 121 / 171; joint 1 + locks
  0.25: 981 / 1094, 26.7, 108 / 171. **None is clearly better; nothing kept, `locks` stays off.** (Locks push the
  locks apart, so the outline grows; a thinner joint 1 changes the outline by 3 %.)

Environment additions: a second shot of the same cast needs no package build when `build/masters` and
`build/packages` are copied from a prepared shot of that cast (cache hit, prepare 0 s). `near_colliders.py` takes
`--character=`. The golden check: `build/tests/plush_tests -tc="golden*"` (24 s).

### Session 8 (2026-11-22, continuation session, stopped at a checkpoint on the Supervisor's request)

State per item (A done, B traced and not fixed, C-E not started):

- **A. Cylinder prop collider: DONE.** Collider type `"cylinder"` (prop only; `a`, `b` = centres of the end faces,
  `radius`, `round` = rim rounding, default 0.003) as a third core shape in `secondary.cpp` (`Shape.cyl` / `rc`,
  `nearestOn`, `nearestSeg` by the box's ternary search), `DynamicsCollider::Kind::Cylinder` + `round` in
  `secondary.h`, unit test "a cylinder on a prop (a cup) ..." in `tests/test_secondary.cpp` (parse / round trip /
  errors, standing and lying cup 0.01-0.02 mm inside, out of reach = bit-identical), `neighbours.prop_boxes` writes
  cylinders for cylinder assets, docs "Scene colliders". **e909 `s010_t183`, run `r6u`, all 286 frames: cup 23.9 mm /
  143 fr -> 0; no object, prop or the boy over 1 mm; own body cap 13.1 mm / 268 fr and curtain 11.1 mm / 165 fr as
  before.** Bake 30.1 s without / 31.1 s with the neighbours. The committed e909 copy now carries `prop.cup`.
- **Engine on the merged main: built; `plush_tests` 287 / 287 passed (golden included), `plush_prop_tests` passed**,
  both with the cylinder change in. Trap met: editing `secondary.h` while a build runs leaves objects compiled
  against the old header (the bake aborted with `std::length_error` in the `DynamicsSpec` copy): `touch
  engine/anim/secondary.h` and build again.
- **B. e912 s030 `ringlets_side_00` > blouse 7.7 mm f1-10: traced, NOT fixed.** Reproduced on the merged engine
  (run `b1` of the committed copy: 7.5-7.7 mm f1-4, 5.1-6.1 mm f5-10, 65-80 vertices, gone from f11). Cause: in
  f1-10 her head is turned 54 degrees to her left against the chest (chest yaw 0, head 53.5). The chain
  `ringlets_side_00.00` (radii 36 mm at joints 2-4) hangs from the head, so its root goes behind the left shoulder
  (z -77), while `anchored_gravity` (anchor chest, weights 0 / 0 / 0.43 / 0.97 / 1) puts the targets of joints 3-4 in
  front of the arm (z +79 / +82). The lock is laid over the top of the upper arm (joint 3 at 185 / 654 / -21 mm, tip
  181 / 618 / 31) and the tip is pulled through the arm towards its target: tip 29.7 mm inside the contact distance
  of 44 arm spheres (upperArm.L / DEF-upper_arm.L.001 / forearm.L), the middle of segment 3-4 22.9 mm inside 35; no
  other collider holds it there, so it is the spring towards the anchored target against the projection, a steady
  state of the preroll (a bake with `preroll_s` 0 reaches the same place by f3). It leaves when the body moves
  (f11+). This is inside the T-183 system (anchored target + contact). Not tried yet: (1) why the projection does not
  win in the static pose (pass count against 44 spheres + the segment-middle test with lever 2 + the length
  constraint); (2) limiting the anchor pull for a joint that a collider holds (the spring target taken to the
  nearest point outside the collider); (3) otherwise list it for T-194. Tools: the scratch dump of session 8 is not
  committed; `near_colliders.py <run dir> ringlets_side_00.00 <joint> 1-12 3 --character=auburn` gives the same.
- **C.** Not started. **D.** Engine + tests done (above); the FINAL measure runs `r6` of the four shots, the released
  "before" bakes and the slowdown factor are not done (e909 `r6u` is a valid final run for e909 unless B / C change
  the packages). **E.** Not started.
- Environment: package ids after the merge of main are `auburn_ef9dd0b340ba8d3a`, `white_c4e0a846770cd63f`,
  `boy_3e04c84ed8656b55` (session 7 had `auburn_ec423c7c2fcfbcf1`, `white_7ded3d4107990fd4`): the candidates
  rebuild on the merged generator; compare the final numbers with `T-183_r5_tables.json` before trusting either.
  e912 prepare of `s010_t183` builds all three packages; copy `build/masters` and `build/packages` to the other two
  copies (prepare then 0 s).

### Open (in this order)

**State of this list after session 8: A is done, B is traced (see session 8); what is left is B's fix or hand-over, C, D (final runs), E.**

- A. **Cylinder prop collider** for the cup of e909 (23.9 mm / 143 fr). Plan: collider type `"cylinder"` (`a`, `b`
  = axis ends, `radius`, `"round"` = edge rounding 0.003) as a third core shape in secondary.cpp: `Shape` gets a
  cylinder core (axis a'..b' shrunk by the rounding, core radius R - rounding), `nearestOn` clamps along the axis
  and radially, `nearestSeg` takes the ternary search of the box branch (the core is convex); on a prop like the
  box (frame from the scene). `neighbours.prop_boxes` -> also cylinders (asset `mesh.primitive == "cylinder"`:
  standing on its base, axis y, `radius`, `height`, times the asset scale; as `measure_props.prop_shape` reads it).
  Unit test beside "a prop box at the identity frame"; docs "Scene colliders".
- B. e912 s030 `ringlets_side_00` > blouse 7.7 mm f1-10: trace with `near_colliders.py --character=auburn`.
- C. Optional, small: neighbour sphere `PAD` 0.0025 -> 0.004 in `neighbours.py` for the 2.2 mm / 2 vertices of
  s010 f12-16; own-body leftovers `ringlets_outer_00` > skin and `ringlets_side_b` > ear.L (few vertices, every
  shot; from round 2, not looked at in round 3).
- D. Build the merged engine, golden + all tests, then **the final runs on the merged engine** (`STEP=1 sh
  tools/r4_run.sh <wrapper> <logs> r6 <source shot dir> <characters>` for e912 s010 / s020 / s030 (auburn white)
  and e909 s010 (girl); 12-15 min per shot), `r5_table.py` per shot and character, released bakes for the "before"
  column (`shots/sNNN`, prepare + bake, no build), the slowdown factor on a quiet machine.
- E. Deliverables (old item 5): table with the snap-frame column in README (round 3 section) and here,
  `T-183_r3_measures.json` (`r3_summary.py`) + the tables JSON, before / after close-ups (e912 s010 table contact,
  e912 s020 beside the boy, e909 lean) and the strict sheet <= 1024 px (`tools/review/strict_sheet.py`, spec like
  `sheet_r2/strict_sheet.json`), `derive_shot.py --check` on the four copies, `tools/ready.py`, READY with: golden
  unchanged, bit-identity SHA, slowdown factor, guarded paths (release_rule.py, tests/test_secondary.cpp,
  test_hair_contact.py, test_release_rule.py; nothing else guarded touched so far).

The original list, for reference:

1. **Neighbour and carried prop** (`engine/scene/scene.cpp` + `scene.h` granted; nothing written yet). Plan: a collider may name `"character": "<scene name>"` (bone of that
   character) or `"prop": "<name>"` (box in prop space); the solver asks a callback for those transforms per step;
   scene.cpp resolves the names at solver creation and passes the other characters' `kinematicGlobals` and the
   props' worlds; `propWorlds` needs a kinematic variant (it calls `characterGlobals` of the carrier, which would
   re-enter the solver; the boat is in the hair owner's hand). The neighbour's shapes are fitted at derive time from
   its package meshes (the fit of `groom_contact.py`'s skin sets) and written into the `_t183` copy by
   `derive_shot.py`. Each girl needs the other girl and the boy; the boy has no candidate (his package stays).
   Solver code to extend: `Shape` / `nearestOn` / `nearestSeg` in secondary.cpp (a prop box needs an oriented box:
   transform the point into the prop's frame); scene.cpp: the dynamics block of `compile` (~line 736) and
   `characterGlobals` (~845); `propWorlds` (~974) calls `characterGlobals` at four places.
2. **One-frame pops of the side locks into the blouse** (e912 s010 f79, f101, f161; her hands go to the sheet every
   15 frames). Traced in the bake: joint 3 of `ringlets_side_r00` travels 66 mm from f100 to f101 and 52 mm on to
   f102 (115 mm net, no way back), so the lock is swept across the chest and is inside the blouse at the frame in
   between; f79 and f161 the same with 44 / 50 mm. Reading (not confirmed with `near_colliders.py`): her forearm
   pushes the lock into the torso spheres and the last push wins. Not fixed.
3. **Fan-out levers** (session 5's untried three), each: build or tweak + bake + `fan_out.py` + `measure_body.py` +
   preview f60 / f100 / f124 on e909 `s010_t183`: (b) thinner joint 1 of the back ringlets:
   `tweak_package.py episodes/e909_two_char_acting/shots/s010_t183 j1 girl 'ringlets_back*:contact.radii[1]=0.012'`;
   (c) `'ringlets_*:contact.locks=0.5'` the same way; (a) shorter top segments needs the groom (`groom_r6.py`
   dynamics `bone_length` per structure / a first-segment key) and a rebuild. Keep one only with cloth / hands /
   ears / props at 0 and the fan-out numbers and picture better; a kept `locks` needs the key in
   `groom_contact.py` (CONTACT_KEYS, the chain block) and its test.
4. White-haired girl: static `back_mass` in ear.L (ear keep-out), see the table.
5. Deliverables: before / after close-ups incl. the table contact (e912 s010, f101-184 medium shot) and the lean
   (e909), strict sheet <= 1024 px, per-surface numbers in the README (add the round 3 section), a committed
   `T-183_r3_measures.json` (the summaries of the measure JSONs; they are in the scratch folder only),
   `tools/ready.py` (the "tests" stop for `test_hair_contact.py` is expected), CHECKPOINT to the Supervisor.

## Round 2 (not accepted by the owner, see round 3): hair against the whole body and the garments

Round 2's last state: see "Session 5" below (three levers against the fan-out tried, none kept; the candidate is
the one of `65e3b9c`). Before it: "Session 4" (final candidate measured; `sheets` and the curtain blend are gone).

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

### Session 5 (2026-11-21/22): the fan-out in the lean, three levers, none kept

Bounded job from the Supervisor: try the three levers of next step 4 once each (build + bake + full measure +
preview frames f60, f100, f124, back and side), accept only with cloth / hands / ears at 0 and the fan-out visibly
reduced. The values named in the job (friction 40, spheres 45 mm, pad 2.5 mm) are the candidate's own, so the trials
went below them. Fresh container: engine built, candidate rebuilt as `s5f` / `s5fb`: 268 of 286 frames, 13.1 mm,
436 vertices, skin only (as `s4fb`). Released baked as `rel5b` (its prepare takes no build: published packages).

- New tool `tools/fan_out.py <label>=<bake> ...` (8 s per bake after loading): hair silhouette from behind and from
  the side (parallel projection, 3 mm cells), the part beyond the body's outline, crossing pairs of lock centre
  lines (back view), sharpest fold between neighbouring chain segments over rest. Every 4th frame of f24-132.
- Trials (override = the candidate with one key changed; trial scene = `s010_t183` scene with that override; runs
  `<name>p` / `<name>b` in `s010_t183/build/runs/`):

  | Run | Change | out back / side cm2 (mean) | crossings | fold deg (mean / max) | Measure beside skin |
  |---|---|---|---|---|---|
  | `rel5b` | released | 843 / 891 | 16.2 | 56 / 80 | (released) |
  | `s5fb` | candidate | 999 / 1,088 | 26.9 | 115 / 164 | 0 |
  | `fr10b` | `rest.friction` 40 -> 10 | 1,000 / 1,087 | 25.5 | 115 / 160 | `ringlets_side_b > ear.L` 32 frames, 1.9 mm, 2 vertices |
  | `ts30b` | `skin_torso` `radius_m` 0.030, `pad_m` 0.002, `spacing_m` 0.018 (529 spheres) | 975 / 1,079 | 28.2 | 99 / 164 | vest 2 frames, 2.7 mm, 1 vertex |
  | `pc85b` | `radii.percentile` 85 (median 28, max 41 mm; candidate 36, 53) | 967 / 1,063 | 27.7 | 132 / 174 | blouse 95 / 3.3 mm / 10; vest 24 / 3.8 / 3; hands 1 / 5.7 / 9; cuffs 1 / 1.5 / 1 |

  Skin identical in all (268 / 13.1 / 436). Preview sheets: `T-183_r2_fanout_levers_back.jpg`, `_side.jpg`; rows:
  `T-183_r2_fan_out.json`. Read at full size, candidate against `pc85b` (the largest numeric change): the same
  picture, the lock that stands out at the upper right of the hair is in both. **None accepted, no combination
  built; the candidate is unchanged.**
- Cause, measured on `s5fb`: (a) chain radii are the farthest fibre from the chain line (up to 53 mm, median 36);
  released the joints of `ringlets_back_05/06/b_02` run 3-34 mm from skin and cloth, candidate 41-79 mm.
  (b) The kink: joint 1 of `ringlets_back_05`, `_06`, `_b_02` folds by more than 80 degrees over rest (max 125, 112,
  88; released at most 49) in f22-56, f75-146, f199-241. The released joint 1 is 8-22 mm from `body_skin` there
  (head tipped onto the neck and right shoulder); with radius 23-44 mm it has no place, goes sideways and up
  (`back_05` f96: (-449, 839, 8) mm against (-383, 708, -20) released, root at y 786) and the lock hangs from there.
  Rest clearance of joint 1 of these three to the whole figure is 41-52 mm, so capping the radius by rest clearance to all
  colliders (instead of the head's only) changes nothing: the squeeze exists only in the pose.
- Clips and sheet not rendered again (candidate unchanged): the four sheet frames rendered from `s5fb` match the
  committed `sheet_r2/after` tiles at 41.7-43.8 dB (JPEG noise; against `before` 19.9-21.0 dB).

### Next steps

1. Supervisor / owner verdict on the CHECKPOINT (README table, clips, sheet).
2. Follow-up outside T-183 (logged by the Supervisor): the neck skin folds over the hairline when the head tilts
   (body skinning; item 1 above).
3. If the lifted right side lock (f26-28, `ringlets_side_r00` on the sleeve, at the cheek) is not wanted: thinner
   chain radii against the arm colliders (not tried).
4. The fanned hair in the lean: friction, torso sphere size and radii percentile are tried (session 5) and do not
   help. Not tried: shorter segments at the top of the back ringlets (two joints in the first 7-9 cm, so the lock
   bends around the shoulder instead of folding at joint 1); a smaller radius for joint 1 only where the lock lies
   under other hair (the nape; it would count against the skin and the collar there); lock-against-lock contact
   (the chains do not see each other, hence the crossings: 27 pairs against 16 released).

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
- Session 5: trial overrides were scratch copies of the candidate override with one key changed, used through a
  scene copy `s010_t183/trial_<name>.scene.json` (not committed) so that the shot's build cache is shared.
- Session 3 runs: released `s010/build/runs/rel3`, candidate `s010_t183/build/runs/s3f` (build logs with the
  bind report: `runs/<id>/logs/build_girl.log`, line `groom contact:`). Try chain keys without a rebuild:
  `tools/tweak_chains.py <name> '<chain pattern>:<key>=<number>'` (bake in `build/exp/<name>/`). Full measure: 2.5 min
  per bake on 4 cores. The build cache does not see a change of generator code (`groom_contact.py`): the same
  override gives "cached"; delete `build/masters/<id>` and `build/packages/<id>` named in `build/cast.json` (girl) to
  rebuild. A scratch script must not be named like a standard module (`inspect.py` breaks the bpy import).
- The branch holds a merge of main (`d366edf4`): a plain `git pull --rebase` replays main through it and stops in a
  conflict (`git rebase --abort` restores the branch). Use `git pull --rebase=merges`, or fetch and check that origin
  is not ahead before pushing.
- Do not print object lists of a master (`WGT-*` widgets: hundreds of lines); filter by name.
