# motion_checks/reach: reach measurements (T-135)

A report over a baked shot (`plush.shot_bake/1`, read with `tools/motion_checks/shot.py`). **Not a gate**: nothing in
`tools/check_all.py` runs it, and it has no thresholds. Results: `docs/evaluation/animation/T-135/README.md`.

```
python3 tools/motion_checks/reach/run.py --bake <run>/bake.json --label e910 --out <dir> [--baseline <old>/reach.json]
python3 tools/motion_checks/reach/tests/test_reach.py
```

Writes `reach.json` (`plush.reach_measures/1`) and `reach.md`. With `--baseline`, each move is matched to the
baseline move of the same character and side with the nearest start (within `--match` frames, default 12) and the
deltas are added. `--window boy.R:57-76` (repeatable) measures given spans instead of the segmented moves.

**Moves.** Each wrist (`hand.L/R` pivot, world space, mm) is cut into moves: frames with speed > 1.5 mm/f, gaps
≤ 3 frames merged, start / end where the speed falls below 10 % of the move's peak, chord ≥ 60 mm. `kind` is
`extend` if the wrist ends further from the hips pivot than it started, else `retract`. A move is a wrist excursion,
not an authored action: a slow drift merged with a reach, or a reach during a walk, is measured as it is.

| group | field | meaning |
| --- | --- | --- |
| path | `max_dev_mm`, `dev_ratio`, `dev_at` | largest distance of the wrist from the start→end chord, its share of the chord, where along the move (0–1) |
| | `arc_ratio`, `bulge_up` | path length / chord; vertical component of the bulge direction (+1 = arcs upward) |
| velocity | `frames`, `peak_m_s`, `peak_at` | duration, peak speed, peak time as a share of the move |
| | `ease_in`, `ease_out` | share of the move before the speed first reaches / after it last leaves half the peak |
| | `peak_acc`, `peak_dec` | largest frame-to-frame rise / fall of speed (mm/f²), from and to rest at the edges |
| | `stall`, `stall_at`, `dec2` | deepest dip between two speed humps as a share of the peak (0 = one hump) and where; largest speed fall over 2 frames after the peak (mm/f) |
| | `onset_step`, `stop_step` | first / last frame's speed as a share of the peak (1 = starts or stops in one frame) |
| anticipation | `onset_lead`, `peak_lead` | frames by which a joint starts / peaks before the wrist (+ = joint first), searched from 24 f before the start to the end; `busy` = already moving when that window opens (onset not measured) |
| overlap | `peak_offset`, `settle` | joint peak after the wrist peak (frames), and frames after the wrist stops until the joint stays below 10 % of its peak (cap 36, `settle_capped`); `after_ratio` = peak after the stop / peak during |

Joint signals: `shoulder` = `DEF-shoulder` local rotation (°/f), `shoulder_shift` = `upperArm` pivot speed (mm/f),
`torso` = `chest` world rotation, `hip` = `hips` world rotation, `hip_shift` = `hips` pivot speed; overlap uses
`neck` / `head` local rotation and `hair` = the fastest spring-chain bone (`DYN-*`) local rotation. A joint quieter
than 0.25 °/f (0.5 mm/f) over the window reports `–`. Head and neck also move for looks and reactions: an overlap or
settle number near a look is the look, not follow-through; read it with the shot's actions.
