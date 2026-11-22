# T-190 · round notes (hand-off to a fresh session)

Supervisor since 12:05Z 22 Nov: round-6 session `session_01NPjxePvWAMsLopzSs1fMXB` (report there). Branch
`t-190-claude-finger-limits`, input `44f9fb3`, main merged at `8640619`.

## Done
- Diagnosis (README sections 1-2, `measures/before_*`): every wrong-way joint in T-187 is a thumb joint; causes =
  per-finger grasp search (box face / band) has no thumb range and swaps solutions per frame; clip layers' retargeted
  thumbs; no limit anywhere.
- Design APPROVED by the Supervisor 12:11Z with these rulings:
  1. no `engine/scene/scene.cpp` (T-183) and no `engine/scene/interaction.cpp` (T-191); the call after
     `applyClipFingers` goes in `engine/scene/clip_layers.cpp` (added to the T-190 row);
  2. the in-range thumb is the default for non-wrap grasps, behind ONE named switch (track `hand.<s>.limits`, 0 = off);
     no golden re-bless until the owner OKs: READY lists every golden that moves with max joint / vertex delta;
  3. thumb lay-back limit = the palm's plane (keeps T-171 r3);
  4. unit test file `tests/test_hand_limits.cpp` (the Supervisor registers it in `tests/CMakeLists.txt`), with a
     frame-to-frame guard: no digit joint jumps > 25 deg in a held grasp;
  5. sheet: before / after of T-187 s020 auburn thumb + e909 s010 boy thumb.
- Evidence tools: `measure_t190.cpp` + `build_measure.sh`, `summarize.py`, `closeup.py` (hand close-ups from a bake).

## Write-set
`engine/anim/animation.h`, `engine/anim/animation.cpp`, `engine/scene/clip_layers.cpp`, `tests/test_hand_limits.cpp`,
`docs/evaluation/interaction/T-190/**` (`engine/anim/hand_shape.*`, `tests/test_hand_shapes.cpp` unused so far).

## State at READY
Implemented and measured (README sections 3-6). Nothing in tests/golden or existing tests was edited. Open: the
decisions in README section 7 (default on / off, lay-back 33 or 45, re-record 6 golden hashes and rewrite the thumb
assertions listed there), then the Supervisor registers `tests/test_hand_limits.cpp` in `tests/CMakeLists.txt`.

## Local state that is not in the repository (regenerate if the session is new)
Build `cmake --preset fast-dev && cmake --build build/fast-dev -j4` (10 min); prepare per shot with
`pipeline/production/run_shot.py --stages prepare` (1 min each); the before bakes need a binary built at `44f9fb3`
(or the new binary with `hand.<s>.limits` 0 keyed on every hand).

## Next round (Supervisor 13:24Z 22 Nov; for a fresh session, nothing of it started)
Owner is deciding; Supervisor recommends default ON + 45 deg lay-back for box-face grasps only (wrap keeps 33). Do not
re-record goldens or rewrite test criteria in place yet. Prepare two separate commits:
- (a) the 45 deg box-face limit, measured. Where: `applyHandPosePerFinger` passes `lim.thumbBack / 55.0f` to
  `rangeThumb`; for `face` grasps pass 45 / 55 instead, and let the final clamp accept it (e.g. `HandLimits::thumbBackFace`
  = 45 used when the hand's grasp is a box face, or `thumbBack` 45 with the wrap keeping its own `kThumbBack` 0.6).
  Already measured with a global 45: `test_hand_shapes.cpp:221`, `test_verbs.cpp:886`, `:1208` pass (40: 2.5 mm,
  33: 4.6 mm). Re-run those three and the T-187 s020 scan (boy R thumb, section 4 of the README).
- (b) a draft rewrite of the failing thumb criteria (README section 6 table: `test_hand_shapes.cpp:168/170/171/221`,
  `test_grasp_contact.cpp:134/139/140/157/207/216/226`, `test_verbs.cpp:886/1208`) to in-range criteria: thumb opposes
  the fingers as far as its range allows, contact within N mm where reachable in range, no penetration. Separate
  commit the Supervisor can drop. Editing these tests needs the Supervisor's go-ahead for the write-set.
- Optional: a better camera for the e909 boy tile (thumb hidden in `sheet/before_after_boy_clip.jpg` row 2).

## Open items (Supervisor 13:24Z: the variants request above is cancelled; nothing starts until the owner answers)
1. Default on or off (README section 7.1).
2. Thumb lay-back 33 or 45 deg for box-face grasps (wrap keeps 33).
3. Rewrite of the failing thumb criteria and re-record of the 6 golden hashes (README section 6), only after the owner's OK.
4. A better close-up camera for the e909 boy tile.
5. Follow-up outside this task: clip thumb retarget (`pipeline/clips/retarget.py`, `engine/model/clip.h`); `interaction.cpp:1256`
   drops `fingerClose.wrap` on box faces.

## Round 2 state (22 Nov, implementer r2)
- `e189084`: `HandLimits::thumbBackFace` = 45 and `handLimitsFor(HandPose)` (grasp && graspFace && !wrap). The per-finger
  box-face thumb search and the final clamp use it; wrap keeps 33. `test_hand_shapes.cpp:221`, `test_verbs.cpp:886` and
  `:1208` pass unchanged. `golden_delta` now reports thumb and finger joints apart (`measures/golden_delta.md`).
- Goldens at 45: exactly the 6 named hashes change (JSON diff, no other key). **Parked, uncommitted** until the owner
  answers on e901 s010: a finger correction of 0.525 deg, back-flex past 0 on the middle hinge. `wave` clip frame 26,
  f0b (boy R at frames 36/256, girl L at 36); `point` clip frames 26-27, f3b (boy R at 146-147). Fingertips move 0.04-0.07 mm.
- `2b93031` WIP: `thumbJointRotations` (thumb joint coordinates). ThumbFit criteria (old thumb criteria required
  exactly wherever an in-range thumb can meet them; else Pareto-optimal within 2 mm, plus a no-skin-penetration
  criterion). The cup case `test_hand_shapes.cpp:168/170/171` is rewritten and passes.
- Open (asked the Supervisor): `test_grasp_contact` shows the T-138 band fit is inert with the in-range thumb (fingers
  not pulled in; boy/girl). The kSdf thumb misses reachable criteria by 0.03 mm (:226) and 1.08 mm (:216). Proposed fix:
  the band fit spans the fingers only when the thumb cannot reach the band; refine the non-wrap per-finger thumb
  search. Then the same ThumbFit rewrite for :134/139/140/157/207/216/226.
- Local only: `tests/CMakeLists.txt` registers `test_hand_limits.cpp` (the Supervisor's at merge).
