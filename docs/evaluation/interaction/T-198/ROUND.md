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

## Next (in order)

1. Golden delta: build `0cb0053` engine in a second build dir (`git worktree add ../anim-base 0cb0053`, `cmake
   --preset fast-dev` there), write `golden_delta_t198.cpp` (as T-190's golden_delta.cpp: per scene, per frame, per
   bone the world turn deg / travel mm between the two builds, using the test packages like test_bake_golden's
   contentScene) and find which fix moves them (likely the look arc: those scenes have looks between characters, or
   the ikRamps loop). Send the Supervisor per golden: frames, max deg / mm, bones, cause. Wait.
2. Orient flip (s020 hands): plan the blend at compile time (interaction.cpp, where the orient keys are written):
   for frames start .. weight-full, key the orient track per frame with the blended world orientation, the
   quaternion hemisphere kept from the previous frame (sticky), weight 1 from the ramp start (no shortest-path choice
   at evaluation). Only where the clip hand and the planned orientation are > ~150 deg apart in the ramp (else keys
   as before). Then re-check with continuity_t198.
3. `tests/test_motion_continuity.cpp`: unit tests (touch end < contact + 10 not inverted; ramp lengthened under the
   limit; look arc keys present for a swing across the head and absent otherwise; laggedLookTarget identity for r >=
   0.75; assist identical on a converging case; exemptions: camera step = cut, `"fast"` action range) + the per-frame
   speed-limit test over every content scene / golden test scene with the test packages: 0 unexempt snaps.
4. `tools/motion_checks/continuity.py`: written, NOT yet run on a bake (bake e912 s010/s020/s030 with
   `plush-render <resolved> --bake bake.json`, compare with continuity_t198); add a test under tools/motion_checks/tests.
5. README before/after table (bakes), sheet frames if the Supervisor wants pictures, `tools/ready.py`, READY.

## Environment notes

- `cmake --preset fast-dev && cmake --build build/fast-dev -j4`; e912 resolved scenes: `python3
  pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/<s>/shot.scene.json --blender
  /usr/local/bin/blender --stages prepare` -> `<shot>/build/shot.resolved.scene.json` (ignored build dirs).
- Evidence tools (build lines in their headers): `trace_t198 <scene> <who> <from> <to> [track suffixes]`,
  `continuity_t198 <scene>` (s020 ~40 s, s010 ~11 s).
- Before numbers: README "Before / after".
