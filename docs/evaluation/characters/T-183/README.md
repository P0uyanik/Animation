# T-183: hair contact (hair inside the body, the garments, the hands and the ears)

Owner 2026-11-21: round 1 not accepted, "the hair still intersects with the body and other areas; it goes inside the
body". Round 2 goal: no hair inside head, neck, shoulders, back, arms, hands or garments through `e909 s010`
(286 frames). Everything is opt-in: the released packages, bakes and goldens are unchanged. Round file: `ROUND.md`.

## Result in plain numbers (girl, e909 s010, all 286 frames, 160,986 hair vertices)

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
`tools/measure_table.py`. Runs: released `rel4b`, candidate `s4fb`.

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
- **The right side lock is lifted by the sleeve (frames 26-28).** When her right arm reaches forward, the puffy
  sleeve rises under the lock in front of her right ear (`ringlets_side_r00`). Released: the lock sinks into the
  sleeve. Candidate: the lock stays out, is carried up by the sleeve (tip up to 26 cm from where it hangs), curls
  up against the cheek near the glasses at frames 26-28, then lies draped over the forearm (frames 32-75). It is
  captioned in the arm-raised clip. If it is not wanted, the possible trade is thinner locks against the arm
  (not tried).
- The ears stay clear (0 frames; released: 195 frames).

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
--resolution 640 360 --samples 8`. More in `ROUND.md` ("Environment notes").
