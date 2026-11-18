# animcheck: animation-principle metrics (T-061)

Measures slow-in / slow-out, arcs and spacing per gesture on an engine shot bake (`plush.shot_bake/1`). Part of
the quality gate (`tools/check_all.py`, the "C++ tests" line, sub-check `animcheck`). It needs no Blender: the gate
bakes the regression shots with `plush-render --bake` in about a second.

```
python3 tools/animcheck/animcheck.py --bake bake.json [--scene shot.scene.json] [--json report.json] [--check]
python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render [--out build/check-all/animcheck]
python3 tools/animcheck/make_shots.py        # rewrites shots/*.scene.json from the T-045 evidence shot
python3 tools/animcheck/tests/test_animcheck.py
python3 tools/animcheck/personality.py --bake bake.json --scene shot.scene.json [--json report.json]   # T-053
```

## Regression shots (`shots/`)

Engine test packages (`tests/data/imported`: boy 1.0.0, girl m3), body mechanics on, life off, 24 fps.

| Shot | Gestures |
| --- | --- |
| `wave_touch` | the T-045 evidence shot: idle → touch (IK pointing gesture) → `wave` clip at speed 1.5 with a 4-frame blend in, both characters |
| `clip_gestures` | library clips at their default blends and three speeds: `point` ×1, `wave` mirrored ×1.5, `gest_shrug` ×0.8 |
| `personality` | T-053: both packages with their personality profiles, life and body mechanics on: 4.8 s idle watching the task object, then the boy's one-hand reach into the task (touch, planned 16 f, hold 72 f) and the girl's `point` clip and brisk touch (planned 13 f) |

## Metrics

Per gesture (clip actions that are not base clips; `touch`; `reach` without a prop), on the wrist pivot of the
gesture's hand (`hand.<side>`, world space, per frame) and the arm bones' rotations. The window starts 12 frames
before the gesture and ends 24 frames after its nominal end (never into the character's previous or next gesture).

- **entry / exit segment**: the first movement out of the starting pose (the lift) and the last movement back. A
  segment starts where the wrist speed exceeds 10 % of the window's peak, extended back over its slow tail (while
  the speed falls and stays above 2 % of the peak), and ends at the first local speed minimum below 35 % of the
  segment's peak (the exit mirrors this from the end).
- **ease ratio** (`ease_in`, `ease_out`): mean speed over the first / last 20 % of the segment's frames ÷ its peak.
- **onset / stop step**: the speed of the entry's first moving frame (`onset_step`) and of the exit's last moving
  frame (`stop_step`) ÷ the segment's peak.
- **jerk**: the largest frame-to-frame change of speed inside a segment ÷ its peak.
- **arc**: largest distance of the wrist path from the chord between the segment's ends ÷ the chord, in 3D (`arc`) and
  projected through the shot camera (`arc_screen`, what the viewer sees).
- **max step**: largest wrist displacement per frame (mm) and largest per-frame rotation of upperArm / forearm / hand
  (degrees) in the window.
- **overshoot / settle** (reported only): how far the wrist passes the entry's end along the chord in the next 12
  frames (% of the chord); frames from the entry's peak speed until the speed stays below 10 %.

## Thresholds (`thresholds.json`, guarded, never loosened)

Ease, jerk, step and arc checks apply to segments whose chord is at least `min_chord_mm` (100 mm): shorter moves are
too small for these ratios to mean anything at 24 fps.

| Key | Value | Why |
| --- | --- | --- |
| `max_ease_ratio` | 0.55 | Standard eases give 0.15 (quintic) to 0.35 (cubic smoothstep) and a constant-speed move 1.0. Above ~0.5 the move leaves or arrives at more than half its peak spacing: it reads as a start or stop without cushion. Before T-061 the `point` exit measured 0.61. |
| `max_first_step` | 0.18 | The first frame out of rest (and the last into rest) must cover less than ~1/5 of the peak spacing. A quintic blend of the shortest length (0.35 s) gives ≈ 0.02; a 4-frame cubic blend that starts while the clip already moves gives 0.2–0.3 (measured before T-061: wave lift 0.23, touch 0.19 / 0.22, point 0.28, shrug 0.31). |
| `max_jerk` | 0.45 | A speed change of almost half the peak within one frame is a velocity pop (the burst-and-dip of a short blend into a moving clip measured 0.46–0.53 before T-061). The fastest legitimate motion in the shots (the wave lift at ×1.5) measures ≤ 0.38. |
| `min_arc` | 0.10 | 0.10 is the sagitta ratio of a wrist swinging ~45° about a fixed pivot: a gesture path flatter than that is "near-linear". Before T-061: `point` entry 0.088, shrug 0.073 / 0.076. |
| `min_arc_screen` | 0.10 | The same as seen through the shot camera; the critique's "near-linear hand path" was the T-045 touch: 0.048 on screen (0.21 in 3D: it curved in depth only). |
| `max_step_mm` | 130 | 3.1 m/s at 24 fps; beyond this a wrist strobes. After T-061 the fastest frame (wave lift ×1.5) is 119 mm. |
| `max_rot_step_deg` | 45 | 1/8 turn per frame: beyond it a limb rotation strobes. After T-061: 41°. |

Measured values for both shots before / after T-061: `docs/evaluation/animation/T-061/README.md`.

## Personality check (T-053, `personality.py`)

For shots whose characters carry a `"personality"` profile, `run_gate.py` also measures the bake against the
profile's `limits` (`content/personality/<id>.json`, `content/personality/SCHEMA.md`); report `<out>/personality.json`.

| Measure | How | Limit |
| --- | --- | --- |
| blink duration | runs of the blink morph above 0.1 that reach 0.5 (cut-off runs at the shot ends skipped) | every blink in `blink_duration_frames` ± 1 f |
| blink interval | start-to-start of rhythm events (a blink within 10 f of the previous one is its double blink) | mean in `blink_interval_frames` |
| reach | touch / reach entry segment (as above) | `reach_frames` ± 1 f |
| hold | longest run after the entry within 10 % of the entry chord, ending by the exit's fastest frame | `hold_frames` ± 1 f |
| idle motion | median head speed outside every gesture window, in head widths (H) per frame | `idle_motion_max_H_per_frame` |

Reported only: clip gestures' entry / hold / peak speed, each entry's peak wrist speed (H/f), the idle head amplitude
(H) next to the profile's `energy.idle_motion_amplitude`. H = x extent of the package's head / skin vertices above
the head bone. Frame values at 24 fps. Unit tests: `tests/test_animcheck.py` (class `PersonalityCheck`).

