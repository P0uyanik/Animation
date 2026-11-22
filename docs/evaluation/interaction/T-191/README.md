# T-191 · Character-character collision: check and resolution

Owner request ~04:20 CET 22 Nov: bodies pass through each other (T-187 paper boat, elsewhere). Branch
`t-191-claude-char-collision` (from `integration/t-187` 44f9fb3). **Status: STATUS — step 1 measured, step 2 design
waiting for the owner's OK.**

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

## 2. Design (proposal — waiting for the owner's OK)
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
