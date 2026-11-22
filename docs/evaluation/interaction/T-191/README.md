# T-191 · Character-character collision: check and resolution

Owner request ~04:20 CET 22 Nov: bodies pass through each other (T-187 paper boat, elsewhere). Branch
`t-191-claude-char-collision` (from `integration/t-187` 44f9fb3). **Status: READY** (design approved R5; implemented opt-in, no golden moves).

## 1. Measure (done)
**Tool:** `tools/motion_checks/body_contact.cpp` (not in the build or the gate, built like `collision_trace.cpp`; command
line in its header) + `tools/motion_checks/body_contact_report.py` (tables, worst cases). Poses are the engine's own
(`SceneEvaluator::characterGlobals`: clips, IK, constraints, secondary motion), every scene frame.

**What is measured — fitted capsules, cross-checked against the skinned meshes:**
- **capsule** (primary): new *body-part capsules* (`collision.h` `deriveBodyParts`), one per body role (hips, spine,
  chest, neck, head, upperArm / forearm / hand / thigh / shin / foot .L/.R; 23-28 capsules per character), fitted to
  that role's skinned rest vertices, garments and hair included (principal axis, 90th-percentile radius; flat parts
  such as a torso or a hand are two side-by-side capsules). Per frame and pair: the signed gap of the closest capsule
  pair (negative = penetration depth along the closest-point line) and which parts.
- **mesh** (cross-check): every 4th skinned mesh vertex (linear blend skinning of the rest meshes) of one character
  inside the other's capsules: the deepest one. The capsules lie just inside each surface (90 % of a part's vertices
  are within its radius), so a vertex inside one is inside the other body.
- **head shell**: T-096 head + hair shells (`headGap`; negative = overlapping, not a depth), for reference.

Shots: e912 s010 / s020 / s030 (T-187, rendered ranges 41-184 / 41-208 / 45-166), e907 `s010_verbs` (hand-over),
e909 `s010`, e910 `s010`. Full tables: [`before.md`](before.md), data [`before.json`](before.json).

**Worst cases** (capsule depth; runs of frames deeper than 5 mm; hand-hand excluded — none occurred):

| shot | pair | parts | frames | worst frame | capsule mm | mesh mm | what it is |
| --- | --- | --- | --- | --- | --- | --- | --- |
| e912 s020 | white-auburn | head/head | 133-134 | 133 | -103 | -104 | auburn turns to the boy, heads swing through each other |
| e912 s030 | auburn-boy | forearm.L/forearm.R | 45-92 | 75 | -99 | -57 | stand-up: arms cross (seats 0.40 m apart) |
| e912 s020 | auburn-boy | head/head | 69-82 | 80 | -92 | -127 | she shows the boat, leans into his head (contact sheet 7.0-8.0 s) |
| e912 s020 | auburn-boy | head/forearm.R | 84-174 | 128 | -85 | -86 | hand-over: her head/hair over his arm |
| e912 s010 | auburn-boy | hand.L/forearm.R | 41-164 (7 runs) | 114 | -52 | -41 | her touches on the sheet go through his resting forearm |
| e910 s010 | boy-girl | hand.R/forearm.L | 141-144 | 143 | -16 | -10 | hand-over: his hand into her forearm |
| e912 s030 | white-auburn | forearm.L/head | 61-64 | 62 | -13 | -15 | stand-up |

e907 `s010_verbs` and e909 `s010`: no capsule contact (worst +1.3 / +19 mm); e907 mesh -15 mm for 16 frames (her
upper-arm vertices inside his hand capsule at the hand-over, f64). Frames deeper than 5 mm (capsule): e912 s020
auburn-boy 110 of 168, s030 auburn-boy 48 of 122, s010 auburn-boy 45 of 144.

Reading: the T-187 contacts come from the staging (three 0.3 m wide heads on seats 0.40-0.43 m apart) plus actions
that bring a part across the gap (lean to show, hand-over, touches next to a neighbour's arm, the stand-up clip). The
two-character shots are mostly clean.

## 2. Design (approved R5)
**Where:** an interaction pass in `SceneEvaluator::compileActions` (interaction.cpp), after IK / look-at / the T-047 arm
clearance and before the T-096 head tilt, the same pattern as the head tilt: a generated per-character track, planned
per frame on the pose as it plays back, eased with a rate limit. Not staging offsets (a root shift slides a seated
pelvis off its stool and a foot-locked walk's feet) and not verb approach targets (only some contacts come from verbs).

**Resolution = body lean away.** Per pair and frame where the body-part gap (`bodyGap`, hand-hand pairs excluded: a
hand-over's shared hold) is below `bodyClearance` (default 10 mm): both characters lean their upper body away from the
other (`<who>/bodyLean`, a world rotation vector spread over spine 40 % / chest 60 % about the hips; horizontal
direction from the other's closest point), the same angle each, the smallest 0.5 deg step up to `bodyLeanMax`
(default 12 deg) that clears; then the smallest envelope above it with at most 0.6 deg per frame, so they ease away and
back. Applied at the reach-lead point of the pose path (`applyArmPoles`): IK-held wrists stay on their targets
(re-solved, as T-134 reach lead does), clip arms ride with the torso, eyes keep their gaze. `<who>/collision.bodyLean.
<other>` records the angle; a warning names frames still deeper than the clearance after the lean (what the lean cannot
fix, e.g. two pinned hands' forearms, is reported, not hidden).
Not in this task (follow-ups if the after-numbers need them): an arm-vs-other-body elbow swing (touches beside a
neighbour's forearm), walk spacing (speed / start offset is staging).

**Opt-in vs default:** opt-in, per character, on the existing collision action (T-047 / T-082; parsed in
actions.cpp, so `scene.{h,cpp}` — T-183's claim — is not touched): `{"type": "collision", "character": "auburn",
"bodyClearance": true, "bodyClearanceMm": 10, "bodyLeanMaxDeg": 12}`. A pair is resolved when at least one of the two
opted in; only the characters that opted in lean (sharing the angle). Off: no track, no pose change, **no golden moves**. Turning it on by default would move every
multi-character golden bake (`tests/golden` two-character shots and the e907/e909/e910/e912 bakes) — not proposed.
Turning it on for e912 is an `episodes/**` change: I will measure before/after on copies of the resolved scenes in my
evaluation folder and ask before touching the shot files.

**Write-set (exact):**
- `engine/scene/collision.h`, `engine/scene/collision.cpp` — body-part capsules, `bodyGap`, `pointBodyGap`,
  `segmentSegment` (added for step 1; existing functions unchanged)
- `engine/scene/interaction.h`, `engine/scene/interaction.cpp` — `applyBodyLean`, the planning pass, model build
- `engine/scene/actions.cpp` — the collision action's three new keys only (next to `maxElbowSwingDeg`)
- `tests/test_collision.cpp` (append: capsule fit, segment distance, gap sign/direction) and new
  `tests/test_body_clearance.cpp` (the pass: off = bit-identical tracks, on = gap opened, rate limit, hand-hand skip,
  IK wrist kept) — registering the new file in `tests/CMakeLists.txt` is the owner's
- new `tools/motion_checks/body_contact.cpp`, `tools/motion_checks/body_contact_report.py`
- `docs/evaluation/interaction/T-191/**`

## 3. Implementation (as built)
- `collision.{h,cpp}`: `deriveBodyParts`, `bodyGap`, `pointBodyGap`, `segmentSegment`; `CollisionBody` gains
  `parts`, `bodyClearance`, `bodyClearanceGap`, `bodyLeanMax` (all inert unless opted in; never in the package block).
- `actions.cpp`: the collision action's keys `bodyClearance` (bool), `bodyClearanceMm` (0..50, default 10),
  `bodyLeanMaxDeg` (0..30, default 12); checked (bad values fail the load).
- `interaction.cpp` `finishInteractions` (before the T-096 head tilt), per pair with at least one opted-in character:
  1. **lean** `<who>/bodyLean`: direction = horizontal contact direction (from the other's closest point; chest to
     chest when the contact is mostly vertical), smoothed over ±8 frames weighted by depth; smallest 0.5 deg step that
     clears, up to the limit; envelope at <= 0.6 deg/frame. Applied by `applyBodyLean` (spine 40 % / chest 60 %, IK
     wrists re-solved by weight, root riders carried, eyes keep their gaze).
  2. **arm yield** `<who>/armYield.<hand>` (added after the first after-run: forearms at hip height barely move with a
     lean): what the lean leaves on a *free* arm part (IK weight < 0.5, and never within 25 frames of a planned contact
     of that hand: grasp / hand-over / touch keep their exact palm) swings that upper arm about the shoulder away from
     the other body, 1 deg steps up to 25 deg, stopping where the arm would go deeper into its own body (T-047 limb
     clearance); envelope <= 1 deg/frame. Applied by `applyArmYield` right after the lean.
  3. what remains below the clearance is a warning naming the pair, parts and frame.
  `"<who>/collision.bodyLean.<other>"` records the lean (degrees). Pairs run in order and add up.
- Off (no key / `false`): no track, no pose change — tested bit-identical (`test_body_clearance.cpp`).
- Tests: `tests/test_collision.cpp` (+3 cases: segment distance, fit per role, gap sign/depth/direction) and new
  `tests/test_body_clearance.cpp` (6 cases: off = identical, option checks, lean opens a -111 mm contact to +11 mm
  within the limit and rate with hips/legs fixed, only opted-in characters lean, IK wrist kept / clip arm rides,
  arm yield moves only that arm). **Registration of `test_body_clearance.cpp` in `tests/CMakeLists.txt` is the
  owner's** (add it next to `test_collision.cpp` in `plush_tests`). Locally: T-191 + T-047/T-082/T-096/T-134 cases
  18/18 pass; full suite see the READY line.

## 4. Before / after (all characters opted in, default 10 mm / 12 deg; copies of the resolved scenes, no episode edited)
Data: [`after.md`](after.md) / [`after.json`](after.json); the 20 deg variant: [`after_lean20.md`](after_lean20.md).

| shot | pair | worst capsule mm | frames < -5 mm (capsule) | worst mesh mm | frames < -5 mm (mesh) |
| --- | --- | --- | --- | --- | --- |
| e912 s010 | auburn-boy | -51.9 → **+10.0** | 45 → **0** | -41.0 → -9.5 | 92 → 14 |
| e912 s020 | white-auburn | -103.0 → -65.3 | 2 → 1 | -104.1 → -63.7 | 2 → 1 |
| e912 s020 | auburn-boy | -92.2 → -101.7 | 110 → **30** | -126.9 → -101.5 | 145 → 118 |
| e912 s030 | white-auburn | -13.4 → **+1.4** | 4 → **0** | -25.4 → -1.5 | 19 → 0 |
| e912 s030 | auburn-boy | -99.4 → -95.0 | 48 → 35 | -96.0 → -111.2 | 48 → 48 |
| e907 s010_verbs | boy-girl | +1.3 → +10.0 | 0 → 0 | -15.3 → **+4.2** | 16 → **0** |
| e909 s010 | boy-girl | +19.0 → +19.0 | 0 → 0 | +11.5 → +11.5 | 0 → 0 |
| e910 s010 | boy-girl | -16.1 → -11.7 | 4 → 3 | -11.1 → -10.3 | 2 → 2 |

Fixed: s010 her touches through his forearm (his arm yields), s030 white-auburn, e907's hand-over contact, s020
head/head while she shows the boat (f69-82: -92 → -20 mm). **Not fixed — staging, needs the owner:**
- e912 s020 f115-138 (hand-over): her head over his *held* right forearm (-102 mm). His hand is on the boat (no yield
  by design), her lean saturates at 12 deg; the worst frame moved from f128 (-85) to f132 (-102) because her lean away
  from the white-hair girl pushes her towards him (she sits in the middle). Fix: hand-over point lower / nearer him,
  or wider seats.
- e912 s030 f57-91 (stand-up): heads and his boat hand pass through her head and chest (-95 mm); the three stand up
  from seats 0.40-0.43 m apart with 0.3 m heads. Fix: wider seats for the stand-up or staggered timing.
- A 20 deg limit is worse (s020 white-auburn -121 mm): the middle character is pushed into the other neighbour.
- e910 f141-144 (hand-over, both hands held): -12 mm, hand against hand/forearm at the shared hold.
Turning it on in e912 means adding one collision action per character to the shot files (episodes/**): not done,
asking.

**Sheet** [`before_after_sheet.jpg`](before_after_sheet.jpg) (800 x 988, Cycles 16 spp, 640x360 review profile,
engine bakes of the resolved scene and its opted-in copy): left before, right after. The visible change at these
framings is small: in s010 f114 his yielding forearm is out of the shot-2 frame; s020 f80 the lean opens the capsule
gap but her hair (curls outside the 90th-percentile head capsule) still meets his; s020 f132 is the unfixed staging
case; s030 f75 his forearm moves off hers at the table edge.
