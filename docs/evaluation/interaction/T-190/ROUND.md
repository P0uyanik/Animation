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
