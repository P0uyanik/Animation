# T-139 (E5): animcheck gesture attribution

Input: integration/t-133 @ 68da3e8. Change: `tools/animcheck/animcheck.py` only. Thresholds, goldens and engine are unchanged.

## 1. Change
A clip gesture is measured on the arm the clip drives. That arm is the one whose `upperArm` / `forearm` / `hand` roles
are in the clip's `mask` (or its tracks when there is no mask), swapped when the action sets `mirror`. The old rule
took the wrist that travels furthest in the window; it is now used only when a clip drives both arms (e.g.
`gest_shrug`) or neither, or when the clip file is missing. Touch and reach still use the action's `hand`. `acting.py`
reads the side from the animcheck report, so the amplitude warning now follows the same arm. Its code is unchanged.

## 2. Evidence: before (68da3e8) vs after ([measure.py](measure.py), [measure_t139.json](measure_t139.json))
These are experiment scenes: e910 s010 (T-117 §3) plus the mirrored `boy_reluctant_shrug` on his left arm. They are
temporary and not production.

| scene | before: side, result | after: side, result |
|---|---|---|
| shrug @f1 (overlaps his pick-up) | R; acting WARN amplitude 0.58 (105°) | **L**; pass, 0 warnings |
| shrug @f126 (overlaps release) | R; FAIL entry onset_step 0.201 | **L**; pass |
| shrug @f144 | R; FAIL entry onset_step 0.198 | **L**; FAIL exit ease_out 0.793, stop_step 1.0 |

At f144 the 96 f clip is cut by the shot end (f192), so the left arm stops mid-motion. This is a real failure on the
gesture's own arm, and it is still caught. e910 s010 as shipped and e909 s010 report the same before and after (0
failures, 0 warnings). The current e909 s010 has no scene clip gesture, so the T-114 §3 window cannot be re-measured
there. The T-114 case (a one-arm shrug overlapping the other arm's reach) is the same as the f1 / f126 rows.

## 3. Old failures still caught
- `run_gate.py` on the regression shots (clip_gestures, personality, wave_touch) gives the same output before and after:
  13 gestures, 0 failures, 0 warnings.
- Existing unit tests: 18/18 pass. The new `AttributionTest` adds 5 tests, so the total is 23/23:
  - a constant-speed move on the clip's arm still fails ease and onset;
  - it still fails while the other arm moves further;
  - an eased one-arm gesture passes while the other arm carries;
  - a two-arm clip keeps the furthest-wrist rule.
- On the 68da3e8 code, 3 of the new tests fail. They are the ones that cover the bug.
- `tests/acting`: 33 passed, 15 skipped (the skips need bakes).

## 4. Open
- `tools/animcheck/README.md` still describes the furthest-wrist rule. It is outside the T-139 write-set; the docstring
  in animcheck.py is updated.
- Verbs (pick_up, pass, carry) are still not animcheck gestures. This task did not change that.
