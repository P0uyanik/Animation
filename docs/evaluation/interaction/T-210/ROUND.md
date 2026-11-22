# T-210 round state

Supervisor: `session_01NPjxePvWAMsLopzSs1fMXB` (STATUS / READY / questions only there). Branch `t-210-claude-grasp-curls`
from main `d0528dc`. Write-set: engine/anim/animation.h/.cpp, engine/scene/actions.cpp, engine/scene/interaction.h/.cpp,
tests/test_motion_continuity.cpp, tests/golden/continuity_baseline.json, tests/golden/interaction_hashes.json (only after
the Supervisor's OK), docs/evaluation/interaction/T-210/**.

## Session 1 (2026-11-22)

- Cause measured (README): grasp weight ramps 4 frames (close) / 5 frames (open), ~92 deg of distal finger curl.
- Fix: measured grasp weight ramp pass at the end of finishInteractions (interaction.cpp only). Shipped scenes: 124
  finger rows -> 0; e901 walk-start row = body yaw ramp, left recorded (cause corrected).
- Baseline 125 -> 1 row; new test case; continuity tests 7 / 7 pass; ratchet re-checked (grown value, new row fail).
- Goldens: 15 / 20 change (golden_delta.md). Numbers sent to the Supervisor; NOT re-recorded.

## Next

1. On the Supervisor's OK: `PLUSH_GOLDEN_WRITE=1 build/fast-dev/tests/plush_tests -tc="golden*"`, check only those 15
   entries changed, full suite, tools/ready.py, READY.
