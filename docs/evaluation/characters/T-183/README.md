# T-183: hair contact (hair inside the body, the garments, the hands and the ears)

Owner 2026-11-21: round 1 not accepted, "the hair still intersects with the body and other areas; it goes inside the
body". Round 2 goal: no hair inside head, neck, shoulders, back, arms, hands or garments through `e909 s010`
(286 frames); round 3: the real shots e912 s010 / s020 / s030 and e909 s010, both girls, props and the
neighbour. Everything is opt-in: the released packages, bakes and goldens are unchanged. Round file: `ROUND.md`.

## Round 3 result (final runs r9 on main merged at c6842d5a, session 9, 2026-11-22)

Four real shots on the merged main (incl. T-190 hand limits), every frame, both girls (`T-183_r9_tables.json`;
summaries in `T-183_r3_measures.json`, keys `*_r9_*`). Limit 1 mm. **Calm** = every frame that is not a source-body snap frame
+-1 (`tools/snaps.py`: a body bone of the measured character, or of the character whose surface it is, turns > 45
degrees or travels > 100 mm within one frame). **Snap** = the snap frames +-1, reported apart and excluded from the
criterion (Supervisor rule). `fringe`, `crown`, `flowers` > `boy:body_skin` in e912 s020 are the rigid parts inside
the boy's head skin (T-191 staging, parked), listed apart.

Fixed in round 3 (all opt-in; released packages, bakes and goldens unchanged):

- **Props and the table**: world boxes, box props (the sheet), cylinder props (e909 cup: 23.9 mm / 143 frames -> 0).
- **The neighbour**: spheres on the other characters' bones (scene.cpp callback); e912 s010 hoodie 2.2 mm -> 0
  (fit padding 2.5 -> 4 mm).
- **contact.carry**: the e912 s010 one-frame pops of the side locks into the blouse.
- **contact.clear_targets** (session 9): e912 s030 f1-10, the head turned 54 degrees against the chest anchor put
  the side lock's target inside the upper arm and the max_swing bound held the lock there: blouse 7.7 mm / 10 frames
  -> 0. The spring targets are taken out of the colliders, the preroll starts there, and the bound yields when the
  uncapped direction is at least 1 mm less deep (docs/SECONDARY_MOTION.md).
- Gone since r5 besides: e912 s020 table top 11.8 mm, boy's body / hoodie / ear and the other girl (snap frames),
  e912 s030 blouse 18.9 mm and both girls' snap-frame pairs (one frame each).

**Not met: <= 1 mm on every calm frame.** What is left (below) is rigid groom parts (cap, curtain, back sections,
temples, the white girl's back mass) inside the own skin while the head / neck pose moves the skin under them, a
few vertices of the chain locks beside the ear and the cheek that the sphere fits of the skin do not cover, and the
T-191 parts. Chain dynamics cannot move the rigid parts; these go to T-194 (render-time push-out on the real
meshes), list in `ROUND.md` "Session 9".

| shot, character | hair part > surface | calm frames: worst mm / frames / vertices | snap frames +-1 only: worst mm / frames | r5 calm (before this session) |
|---|---|---|---|---|
| e912_s010_auburn | hair_curtain>body_skin | 9.8 / 148 / 208 | 9.8 / 36 | 9.8 / 148 |
| e912_s010_auburn | hair_ringlets_outer_00>body_skin | 8.8 / 140 / 8 | 8.8 / 36 | 8.8 / 148 |
| e912_s010_auburn | hair_cap>body_skin | 5.9 / 148 / 37 | 6.2 / 36 | 5.9 / 148 |
| e912_s010_auburn | hair_ringlets_side_b>ear.L | 2.0 / 60 / 3 | 2.0 / 11 | 3.0 / 105 |
| e912_s010_white | hair_back_mass>ear.L | 10.3 / 184 / 202 | - | 10.3 / 184 |
| e912_s010_white | hair_back_under_06>ear.R | 10.1 / 178 / 9 | - | 10.2 / 178 |
| e912_s010_white | hair_back_under_00>ear.L | 5.4 / 177 / 6 | - | 5.4 / 184 |
| e912_s020_auburn | hair_fringe>boy:body_skin | 49.9 / 39 / 443 | 49.9 / 3 | 49.9 / 39 |
| e912_s020_auburn | hair_flowers_petals>boy:body_skin | 45.5 / 3 / 154 | - | 45.5 / 3 |
| e912_s020_auburn | hair_crown>boy:body_skin | 29.8 / 4 / 444 | - | 29.8 / 4 |
| e912_s020_auburn | hair_cap>body_skin | 25.5 / 193 / 364 | 25.5 / 13 | 25.5 / 193 |
| e912_s020_auburn | hair_curtain>body_skin | 20.9 / 189 / 905 | 20.9 / 13 | 20.9 / 189 |
| e912_s020_auburn | hair_flowers_centres>boy:body_skin | 11.7 / 1 / 31 | - | 11.7 / 1 |
| e912_s020_auburn | hair_ringlets_side_00>boy:body_skin | 8.3 / 3 / 34 | 8.3 / 2 | 8.3 / 3 |
| e912_s020_auburn | hair_temple_l>body_skin | 7.9 / 8 / 8 | - | 7.9 / 8 |
| e912_s020_auburn | hair_back_sections>body_skin | 5.7 / 29 / 23 | 5.7 / 1 | 5.7 / 29 |
| e912_s020_auburn | hair_ringlets_outer_00>body_skin | 3.8 / 44 / 4 | 12.4 / 8 | 2.9 / 48 |
| e912_s020_auburn | hair_ringlets_side_b>ear.L | 1.9 / 50 / 2 | 1.9 / 4 | 6.0 / 103 |
| e912_s020_auburn | hair_curtain>garment.blouse.collar | 1.6 / 144 / 19 | 1.6 / 5 | 1.6 / 144 |
| e912_s020_auburn | hair_flowers_petals>white:body_skin | 0 | 4.9 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_fringe>white:body_skin | 0 | 23.9 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_ringlets_side_b>body_skin | 0 | 6.4 / 3 | 2.9 / 3 |
| e912_s020_auburn | hair_ringlets_side_b>ear.R | 0 | 1.6 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_temple_r>body_skin | 0 | 5.8 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_cap>garment.blouse.collar | 0 | 12.2 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_curtain>garment.blouse.main | 0 | 18.0 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_curtain>garment.vest.edge.2 | 0 | 1.8 / 1 | 0.0 / 0 |
| e912_s020_auburn | hair_curtain>garment.vest.main | 0 | 3.3 / 1 | 0.0 / 0 |
| e912_s020_white | hair_back_mass>ear.L | 10.2 / 208 / 267 | - | 10.2 / 208 |
| e912_s020_white | hair_back_under_06>ear.R | 9.8 / 167 / 11 | - | 9.4 / 169 |
| e912_s020_white | hair_back_under_00>ear.L | 5.3 / 192 / 6 | - | 5.3 / 208 |
| e912_s020_white | hair_cap>body_skin | 5.2 / 28 / 124 | - | 5.2 / 28 |
| e912_s030_auburn | hair_cap>body_skin | 22.0 / 145 / 389 | 22.0 / 1 | 22.0 / 145 |
| e912_s030_auburn | hair_curtain>body_skin | 6.9 / 26 / 219 | 7.5 / 1 | 6.9 / 26 |
| e912_s030_auburn | hair_back_sections>body_skin | 4.1 / 21 / 7 | - | 4.1 / 21 |
| e912_s030_auburn | hair_curtain>garment.vest.main | 3.5 / 6 / 7 | - | 3.5 / 6 |
| e912_s030_auburn | hair_curtain>garment.vest.edge.2 | 2.3 / 10 / 5 | - | 2.3 / 10 |
| e912_s030_auburn | hair_ringlets_outer_00>body_skin | 2.3 / 6 / 3 | - | 2.6 / 8 |
| e912_s030_auburn | hair_curtain>garment.blouse.collar | 1.8 / 54 / 13 | 1.8 / 1 | 1.8 / 54 |
| e912_s030_auburn | hair_ringlets_back_01>ear.L | 0 | 9.2 / 1 | 0.0 / 0 |
| e912_s030_auburn | hair_ringlets_outer_b>body_skin | 0 | 4.6 / 1 | 0.0 / 0 |
| e912_s030_auburn | hair_ringlets_outer_b>ear.R | 0 | 10.0 / 1 | 0.0 / 0 |
| e912_s030_auburn | hair_ringlets_side_b>ear.R | 0 | 10.3 / 1 | 0.0 / 0 |
| e912_s030_white | hair_back_mass>ear.L | 11.3 / 163 / 271 | 11.3 / 3 | 11.3 / 163 |
| e912_s030_white | hair_back_under_06>ear.R | 9.7 / 87 / 12 | 9.7 / 2 | 9.7 / 88 |
| e912_s030_white | hair_cap>body_skin | 8.8 / 79 / 222 | 8.8 / 1 | 8.8 / 79 |
| e912_s030_white | hair_back_under_00>ear.L | 7.9 / 135 / 6 | - | 7.9 / 147 |
| e909_s010_girl | hair_cap>body_skin | 13.1 / 268 / 126 | - | 13.1 / 268 |
| e909_s010_girl | hair_curtain>body_skin | 11.1 / 165 / 404 | - | 11.1 / 165 |

Bake time (plush-render alone, median of 3, quiet 4-core machine, merged main; released shot -> T-183 candidate copy
with every round-3 collider): e912 s010 6.4 -> 24.8 s (3.9x), s020 29.8 -> 51.2 s (1.7x), s030 3.2 -> 17.3 s (5.5x),
e909 s010 12.2 -> 23.1 s (1.9x); **all four 51.5 -> 116.3 s = 2.3x**. clear_targets itself costs nothing measurable
(bakes before / after the key within 1 s).

Sheet `T-183_r3_sheet.jpg` (642x1024; spec and full frames `sheet_r3/`, built by `tools/sheet_r3.py`): released
shot | candidate copy, same camera, crops of 1280x720 renders. e912 s030 f5 (the side lock over the turned-away upper
arm), e912 s010 f120 (released: the ringlets go through the table top; candidate: they lie on it), e912 s020 f100
(beside the boy), e909 s010 f76 (released: the side lock in the cup; candidate: beside it; the wider back ringlets of
the lean are the fan-out of round 2, unchanged).

## Round 2: result in plain numbers (girl, e909 s010, all 286 frames, 160,986 hair vertices)

How many frames have hair deeper than 1 mm inside a surface, how deep at worst, and how many hair vertices at once.
Released = girl 0.14.0 as published. Candidate = the same girl with `candidates/girl_auburn_bun_glasses.hair_contact.override.json`.

| Surface | Released: frames, worst depth, most vertices | Candidate: frames, worst depth, most vertices |
|---|---|---|
| Vest | 282 of 286, 65.9 mm, 2,079 | 0 |
| Blouse | 286, 61.9 mm, 5,396 | 0 |
| Blouse cuffs | 115, 31.2 mm, 37 | 0 |
| Hands | 95, 48.4 mm, 240 | 0 |
| Shorts | 74, 31.0 mm, 463 | 0 |
| Ears | 195, 11.8 mm, 212 | 0 |
| Skin (head, neck, arms) | 268, 25.7 mm, 470 | 268, 13.1 mm, 436 (two hidden places, below) |
| All surfaces together | 286, 65.9 mm, 8,496 | 268, 13.1 mm, 436 |

Tool: `tools/measure_body.py` (every hair vertex against every body and garment surface, every frame), table by
`tools/measure_table.py`. Runs: released `rel4b`, candidate `s4fb`; the candidate was rebuilt from scratch in a fresh
container in session 5 (run `s5f`): the same numbers on every surface.

## What is left, and whether it can be seen from outside

Both leftovers are on skin, under other hair. Neither can be seen in the four close-up views (the nape and the
neck base are covered by the curtain's outer face and the ringlets in every rendered frame).

1. **Scalp cap at the nape**: about 130 vertices, 268 frames, true depth 2-6 mm (the measure reports up to 13.1 mm).
   When the head tilts, the body's own neck skin folds over the hairline: two skin layers end up 0-3 mm apart and
   the hair cap, which is fixed to the head, is counted as inside the outer one. This is the body's skinning, not
   the hair, and it is outside this task; the Supervisor has logged it as a follow-up. It lies under the back
   curtain and the ringlets. Not visible.
2. **Lower edge of the back curtain against the base of the neck**: up to 404 vertices, 165 frames, up to 11.1 mm.
   The curtain is a 2 cm thick sheet that follows the head; when the head turns, the inner face of its lower edge
   (height 0.69-0.72 m) turns into the neck base. It is the face that lies against the neck, under the ringlets.
   Not visible.

Tried once for item 2 and dropped: letting the curtain's lower edge follow the chest earlier (curtain blend
0.66-0.78 m instead of 0.60-0.72 m). It cut item 2 to 6.7 mm and 188 vertices, but the curtain then lagged behind
the head beside the left ear and went 10.2 mm into the ear in 210 frames. An ear is visible, so the change is not in
the candidate.

## What you will see (read from the close-up frames; this is a change of look, please judge it)

- **Upright (frames 10-18, 148): close to the released look.** The locks lie on the blouse and vest instead of
  sinking into them. They rest 3-8 mm above the cloth (the colliders are spheres just under the surface plus a
  small margin, and each lock has a thickness).
- **Leaning forward to the cup (about frames 24-132): the hair is wider and less tidy than released.** Released,
  the back ringlets keep their neat hanging shape because they pass through her back, shoulder and sleeve.
  Candidate, they cannot pass through, so they pile up on the bent back and shoulder, fan out and stand off the
  body: the silhouette behind her head is clearly bigger (arm view f24-58, side view f54-96), ringlets lie across
  each other (back view f62-106), and in the over-shoulder view one ringlet is kinked with a tuft of fibres
  sticking up (f116-132). When she straightens the hair settles again (over-shoulder view f148).
  Three changes against this were tried in session 5 and none helped (next section).
- **The right side lock is lifted by the sleeve (frames 26-28).** When her right arm reaches forward, the puffy
  sleeve rises under the lock in front of her right ear (`ringlets_side_r00`). Released: the lock sinks into the
  sleeve. Candidate: the lock stays out, is carried up by the sleeve (tip up to 26 cm from where it hangs), curls
  up against the cheek near the glasses at frames 26-28, then lies draped over the forearm (frames 32-75). It is
  captioned in the arm-raised clip. If it is not wanted, the possible trade is thinner locks against the arm
  (not tried).
- The ears stay clear (0 frames; released: 195 frames).

## The wide hair in the lean: three changes tried, none kept (session 5)

The candidate is unchanged. Each of the three changes session 4 named was built, baked and measured once over all
286 frames, with preview frames at f60, f100 and f124 from behind and from her right side. None makes the hair
visibly narrower or tidier, and each one puts hair back into a visible surface.

The values in the task ("friction 40", "spheres 45 mm, pad 2.5 mm") are what the candidate already has, so the
trials went below them.

| Run | Hair beyond the body's outline, from behind / from the side (cm2, mean of f24-132) | Lock pairs crossing (mean / most) | Sharpest fold of a lock (mean / worst) | Cloth, hands, ears (frames over 1 mm) |
|---|---|---|---|---|
| Released | 843 / 891 | 16 / 23 | 56 / 80 degrees | see the table at the top |
| Candidate (kept) | 999 / 1,088 | 27 / 32 | 115 / 164 degrees | 0 |
| Friction 40 -> 10 | 1,000 / 1,087 | 26 / 29 | 115 / 160 degrees | ears: 32 frames, 1.9 mm, 2 vertices |
| Torso spheres 45 -> 30 mm (pad 2 mm, 18 mm apart, 529 instead of 298) | 975 / 1,079 | 28 / 35 | 99 / 164 degrees | vest: 2 frames, 2.7 mm, 1 vertex |
| Lock radii percentile 100 -> 85 (largest 41 instead of 53 mm) | 967 / 1,063 | 28 / 34 | 132 / 174 degrees | blouse 95 frames, 3.3 mm; vest 24, 3.8 mm; hands 1, 5.7 mm; cuffs 1, 1.5 mm |

Skin is the same in all four (268 frames, 13.1 mm, 436 vertices: the two hidden places).

- Tool: `tools/fan_out.py` (new): the hair's silhouette seen straight from behind and from her right side, the part
  of it that lies beyond the body's outline, how many pairs of lock centre lines cross seen from behind, and the
  sharpest fold between two neighbouring segments of a lock (more than at rest). Every 4th frame of f24-132; all
  rows in `T-183_r2_fan_out.json`.
- The numbers say what the frames show: the candidate has 18 % (from behind) and 22 % (from the side) more hair
  beyond the body's outline than released; the best trial takes back 3 of those 18 and 2 of those 22 points. The
  whole silhouette is not bigger (2,339 against 2,358 cm2 from behind): the hair that released hides inside the
  body now lies beside and behind it.
- Frames: `T-183_r2_fanout_levers_back.jpg` and `T-183_r2_fanout_levers_side.jpg` (960x980; one row per run:
  released, candidate, the three trials; columns f60, f100, f124). The lock that stands out to the side at the
  upper right of the hair (f100, f124 from behind) is there in the candidate and in all three trials.
- No combination was built: no single change reduced the fan-out, and each alone already breaks a zero.

Why these three do not reach it (measured on the candidate bake):

- The locks collide as thick tubes. A ringlet is a wide spiral; its collision radius is the farthest fibre from
  the chain's centre line, up to 53 mm per joint (median 36 mm). For the three ringlets below: released, the
  centre lines run 3-34 mm from skin and cloth and the curls pass through; candidate, 41-79 mm (f24, f96). The
  whole lock sits 2-6 cm farther out. Thinner radii (percentile 85: median 28 mm, largest 41 mm) move the locks
  in by a few mm, and the outermost curls then dip 1.5-5.7 mm into blouse, vest and a hand.
- The kinked ringlet is a squeeze at the first joint. Three ringlets at her right back (`ringlets_back_05`,
  `_06`, `_b_02`) fold by more than 80 degrees at their first joint (worst 125, 112 and 88 degrees; released
  never over 49) in f22-56, f75-146 and again in f199-241. When her head tips back and to her right in the lean,
  the place where that joint hangs is 8-22 mm from the neck and shoulder. A joint with a collision radius of
  23-44 mm does not fit between head and shoulder; it is pushed out sideways and up (`ringlets_back_05`: 14-15 cm
  from where the released joint hangs, 5 cm above its own root), and the rest of the lock hangs from there. The
  first segment is one stiff piece of 6-9 cm. With smaller torso spheres or thinner radii `ringlets_back_05`
  still folds by 101-114 degrees at f24 and f96.
- Friction decides how fast a pushed lock slides back, not where it has room: with friction 10 the picture is the
  same, and `ringlets_side_b` slides 1.9 mm into the left ear.

What would address it (not tried; outside the bounded trials): more and shorter segments at the top of the back
ringlets so that a lock can bend around the shoulder instead of folding at one joint; a lock that may be squeezed
thinner near its root where it lies under other hair; and the locks do not collide with each other, which is why
they cross.

## Clips and sheet

Close-ups of the girl, released on the left, candidate on the right, shot frame number burnt in. Fixed cameras
(`tools/closeup.py`), 640x360 per side, 8 samples, every second frame of the shot (12 pictures per second), H.264.

| File | View | Shot frames | Look at |
|---|---|---|---|
| `clips/T-183_r2_arm_f010-058.mp4` | arm raised: front three-quarter on her right | 10-58 | the bow to the cup; the lifted right side lock at f26-28 (captioned); the hair piled on the bent back |
| `clips/T-183_r2_side_f050-098.mp4` | her right side | 50-98 | released: ringlets inside the sleeve and back; candidate: on top of them, fanned out |
| `clips/T-183_r2_back_f060-108.mp4` | straight from behind | 60-108 | the ringlets across the back; candidate wider, shifted to her right, ringlets crossing |
| `clips/T-183_r2_shoulder_f100-148.mp4` | over her right shoulder, from behind and above | 100-148 | the back from above; the kinked ringlet (f116-132); settling at f148 |
| `T-183_r2_strict_sheet.jpg` | strict sheet, 840x1024 px: one row per view, released / candidate | 28 (arm), 76 (back), 78 (side), 116 (shoulder) | tiles at full size in `sheet_r2/before/`, `sheet_r2/after/` (640x360) |

The clips and the sheet show the candidate that is kept (session 5 changed nothing in it). They were not rendered
again: the four sheet frames, rendered from the session 5 rebuild, match the committed candidate tiles at 42-44 dB
(JPEG noise; against the released tiles 20-21 dB).

Each clip plays its frames once at real speed and once at half speed. Not rendered: frames 149-286 in close-up
and her left side (the boy's side); those are covered by the measure only.

## Tip noise (condition 1)

`tools/tip_noise.py` on the final candidate (the root radius of the locks changed since it was last checked): in
calm frames the worst single out-and-back of a lock tip is 7.3 mm (frame 51, the forearm passing a lock), 17
chain-frames over 0.5 mm; the worst two-reversals-in-a-row (jitter) of a lock is 3.3 mm; 30 chain-frames over
0.5 mm, 9 of them the bun. Round 1 candidate: 4.8 mm, 21, 4.3 mm, 30. Same level: no new jitter.

## What was built (all opt-in; a spec without the keys builds exactly as before)

- Engine `engine/anim/secondary.{h,cpp}`: chain key `contact` with `segments`, `anchored_gravity`, `radii` (one
  collision radius per joint), `rest` (resting contact with `friction`, `max_swing`). Format:
  `docs/SECONDARY_MOTION.md`. Tests: `tests/test_secondary.cpp` (18 cases).
- Groom `pipeline/charsys/groom_contact.py` (called from `groom_r6.py`, groom/5): `hair.ear_keepout` (hair surface
  moved out of the ear meshes at build time) and `hair.dynamics.contact`: colliders fitted from the figure's own
  meshes at bind time. `"fit": "skin"` gives spheres that follow the surface from inside, each riding on the bone
  that carries it; `radii` gives each lock its thickness per joint; `rest` lets a lock lie on a surface. Tests:
  `pipeline/charsys/tests/test_hair_contact.py` (73 checks).
- Candidate: five sphere sets (head 150, ears 102, torso with the garments 298, arms 157, hands 97), `radii`
  (percentile 100, floor 6 mm), `rest` (friction 40, max_swing 12), ear keep-out 3 mm, locks damping 7 -> 14, bun
  stiffer (400 / 320, damping 34, limit 6 degrees). Shot: `episodes/e909_two_char_acting/shots/s010_t183/`.
- Release rule: feature `hair_contact` (`pipeline/charsys/release_rule.py`, one sample in `test_release_rule.py`,
  two rows in `docs/process/GENERATOR_PINS.md`).

Tried and removed:

- `sheets` (spring chains for the static back curtain): the chains are independent, so where colliders pushed
  neighbours apart the curtain sheared (mesh edges up to 3.8 times their rest length, against 1.8 without chains)
  and the curtain's own count hardly moved (9.6 mm against 11.1 mm). Key and code are gone.
- The curtain blend above (one build, one full measure). Key and code are gone.
- Binding the scalp cap to the skin under it: 130 instead of 131 vertices at the nape. Code gone.

## The measure, and the old rules beside it

`tools/measure_body.py` counts a hair vertex as inside by its exit distance: how far it has to move, in the best
direction, until nothing of the figure lies beyond it. Three rules were corrected in round 2 (accepted by the
Supervisor); released and candidate are always measured with the same rules:

1. Rest match: a vertex that is inside the figure as modelled and still sits at its modelled distance from the same
   part does not count (hair tucked behind the ear counted 3-6 mm whenever a raised shoulder closed one way out).
2. Open borders: the skin mesh is cut away under the garments; a hair tip hanging in the air below that border
   counted as 48 mm "inside the skin" (4 curtain vertices).
3. Enclosure: a vertex "behind" a face with nothing beyond it counts only when it is really enclosed (a lock in the
   open air behind a vest trim that is modelled inside out counted 35-46 mm).

With the old rules (`--legacy`), same bakes:

| Surface | Released: frames, worst depth, most vertices | Candidate: frames, worst depth, most vertices |
|---|---|---|
| Vest | 286, 65.9 mm, 2,089 | 64, 37.4 mm, 6 (2-6 single vertices in the open air beside the vest's borders and inside-out trims) |
| Blouse | 286, 61.9 mm, 5,413 | 1, 9.9 mm, 1 |
| Blouse cuffs | 115, 31.2 mm, 37 | 0 |
| Hands | 95, 48.4 mm, 240 | 0 |
| Shorts | 74, 31.0 mm, 463 | 0 |
| Ears | 286, 11.8 mm, 216 | 286, 5.8 mm, 18 (temples tucked behind the ear, as modelled) |
| Skin | 286, 50.0 mm, 475 | 286, 49.8 mm, 444 (the 4 curtain tips below the skin border; items 1 and 2) |
| All | 286, 65.9 mm, 8,529 | 286, 49.8 mm, 452 |

## Round 1 (not accepted; kept for the record)

Owner defects 2026-11-21 ~12:30Z: hand in hair, hair in ear, hair moves independently of the body. Causes: the
chain solver had only head, torso and shoulder colliders and tested joints only; no ear keep-out; gravity used the
head's tilt for joints anchored to the chest; low damping. Round 1 added the `contact` chain key, capsule colliders
for hands, arms and ears, the ear keep-out and the follow tuning.

| Measure (`tools/measure_contact.py`, `tools/follow.py`) | Released | Round 1 candidate |
|---|---|---|
| Hand vertices inside hair | 28 frames, worst 6.7 mm | 0 frames |
| Cap / temples inside the ear | 286 frames, 4.4-7.1 mm | 0 frames |
| `ringlets_side_b` inside the ear (L / R) | to 10.2 / 10.5 mm, 216 / 188 frames | to 7.6 / 5.1 mm, 169 / 111 frames |
| Back ringlet tips off the body-anchored pose (max / rms) | 42-47 / 25-26 mm | 5-24 / 1.6-3.6 mm |
| Bun | 35.5 / 15.3 mm | 17.8 / 6.8 mm |

Round 1 files: `T-183_s010_f060-228_before_after.mp4`, `T-183_s010_f060-228_girl_zoom_half_speed.mp4`,
`T-183_s010_f060-228_after_hevc10.mp4`, `T-183_strict_sheet.jpg` (tiles in `sheet/`).

## Reproduce

Blender is the bpy 5.3.0 module (`tools/bpy_blender.py` behind a small wrapper script). Per shot
(`shots/s010/` = released, `shots/s010_t183/` = candidate): `python3 pipeline/production/run_shot.py --shot
<shot.scene.json> --blender <wrapper> --stages prepare --run-dir <id>`, then the same with `--stages bake
--bake-engine build/apps/render-cli/plush-render --run-dir <new id>`; `python3 tools/measure_body.py
<build/runs/<id>/bake.json> --out=<measure.json> [--legacy]`; close-ups: `tools/closeup.py <bake> <copy> <view>
--frames=A-B --step=2`, then `pipeline/charsys/shot_render.py --bake <copy> --cast <build/cast.json> --out <dir>
--resolution 640 360 --samples 8`; fan-out: `python3 tools/fan_out.py released=<bake.json> candidate=<bake.json>`.
More in `ROUND.md` ("Environment notes").
