# T-198 Motion Continuity Guard: round state

Supervisor: `session_01NPjxePvWAMsLopzSs1fMXB` (STATUS / CHECKPOINT / READY only there). Branch
`t-198-claude-motion-continuity` from `0cb0053`. Write-set: `engine/anim/animation.h/.cpp`,
`engine/scene/interaction.h/.cpp`, `engine/scene/actions.cpp` (granted R6), `tests/test_motion_continuity.cpp` (new;
registration is the Supervisor's), `tools/motion_checks/continuity.py` (new), `docs/evaluation/interaction/T-198/**`.
NOT ours: `engine/scene/scene.*`, `engine/anim/secondary.*` (T-183), episodes, goldens (re-record only after approval
with numbers).

Design approved (R6, ~17:26Z): (A) source fixes on by default, each touching only frames over the limit; (B) detector +
per-frame speed-limit test, intent exemptions by data only (cut = camera / character step key; `"fast": true` on an
action). No inertialization limiter, no scene.cpp hook. Goldens: per golden the frames + max angle / mm to the
Supervisor BEFORE re-recording. Hand-only sub-mm / sub-degree side effects: decide and record here.

## Session 1 (2026-11-22): done, uncommitted parts committed at the checkpoint

- Causes (measured, `trace_t198.cpp`; see README "Causes"): s010 touch ramps (ikRamps lag squeeze + inverted out
  ramp + 2-frame finger curl); s020 head = look target switch boy -> white passing THROUGH auburn's head (all three in
  a row at z = 0) + the lag average of positions collapsing onto the head + assistGazeWithNeck passes oscillating for
  that near target; s020 hands (auburn f45-46 pick-up, boy f137-138 receive) = orient weight 0 -> 1 in 4 frames AND a
  shortest-path slerp flip (clip hand vs planned grip ~180 deg apart) in `applyOrientConstraints`; s030 f93 = cut.
- Engine: `MotionLimits`, `motionBoneClass`, `motionStepRatio`, `motionStepPeak`, `motionJumps` (animation.h);
  `continuityExemptions`, `continuityReport` (interaction.h).
- Fixes in: ikRamps (inverted out ramp rebuilt; measured per-frame loop lengthens in / out ramps over the limit,
  lag first); touch finger curl measured (closes later, at most contact - 4); look transitions keyed on an arc round
  the looker's head when the straight path passes within 0.6 x the nearer end's distance (actions.cpp look);
  `laggedLookTarget` (animation.cpp: mean direction blended in when the lagged mean point collapses toward the head,
  r < 0.75; above it the mean point bit for bit) in the life head follow and the assist; assistGazeWithNeck: when the
  excess rises between passes, the result is replaced by a grid search (5 / 1 / 0.25 deg) for the smallest neck turn
  with the least excess (converging passes unchanged).
- Tried and dropped: halving / secant backtracking in the assist (stuck or landed on other branches); lengthening the
  orient weight ramp (made the slerp flip worse: 129 / 156 deg) -> reverted.
- After (continuity_t198 on the resolved scenes): s010 17 snap frames -> 0; s020 9 -> 4 (only the two orient-flip
  hands left: auburn f45-46 hand.L 48 / 79 deg, boy f137-138 hand.R 55 / 56 deg); s030 0 (f93 cut, 3 characters).
- Full suite: 284 / 285 pass; the failure is `test_bake_golden`: 3 interaction goldens change hash (clip + bake):
  `content/scenes/eval/exchange`, `e907_exchange/s010`, `e907_exchange/s010_calibrated`. NOT re-recorded.

## Session 2 (2026-11-22)

- Merged origin/main (no engine changes there). Golden delta measured (README "Goldens"): the 3 round-1 deltas were
  the look arc + lag direction firing on a shift under the limit -> both gated by the measured head-chain peak (arc
  keys + `<who>/continuity.lookArc` marker only when over; the lag direction only on marked frames). All 6 content
  goldens bit-identical.
- Orient blend pass (interaction.cpp, last block of finishInteractions; scene.h not touched): s020 4 -> 0. It changes
  `test_interaction/visibleGrip/boy` (a 147 deg flip at f11 -> peak 25 deg / f): numbers sent, NOT re-recorded.
- Bug caught by the new test: the marker track held 1 before its first key (fixed: a 0 key at start - 1).
- tests/test_motion_continuity.cpp (5 cases, pass; built locally: `g++ ... tests/test_main.cpp
  tests/test_motion_continuity.cpp`), tools/motion_checks/tests/test_continuity.py (registered `run` in
  tools/motion_checks/TESTS), continuity.py on bakes: before 17 / 9 / 0, after 0 / 0 / 0.
- Asked the Supervisor: (1) re-record visibleGrip/boy? (2) the shipped-scene per-frame test: content goldens still
  have grasp / release finger curls 25-32 deg / f (limit 25) and e901 boy f223 hand.R 81 mm at 30 fps (1.01 x):
  (a) fix the curls (golden change) or (b) recorded baseline rows. Recommended (b).

- Supervisor (~18:45Z): (1) re-record visibleGrip/boy: done (`PLUSH_GOLDEN_WRITE=1 plush_tests -tc="golden*"`, only
  that entry changed); per-frame table in golden_delta.md. (2) option (b) as a ratchet: done
  (continuity_baseline.json, 125 rows with causes; test case "shipped content scenes ... ratchet"; checked that a
  grown value and a new row fail). Option (a) = follow-up T-210 (rows in README).

## Next (in order)

1. Full suite, tools/ready.py, READY.

## Environment notes

- `cmake --preset fast-dev && cmake --build build/fast-dev -j4`; e912 resolved scenes: `python3
  pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/<s>/shot.scene.json --blender
  /usr/local/bin/blender --stages prepare` -> `<shot>/build/shot.resolved.scene.json` (ignored build dirs).
- Evidence tools (build lines in their headers): `trace_t198 <scene> <who> <from> <to> [track suffixes]`,
  `continuity_t198 <scene>` (s020 ~40 s, s010 ~11 s).
- Before numbers: README "Before / after".
