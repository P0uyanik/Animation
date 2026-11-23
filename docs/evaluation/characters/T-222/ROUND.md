# T-222 round file (L1: garment push-out + cloth evaluation)

Keep this current each round so a fresh session can take over. Details and numbers: [`README.md`](README.md).
Branch `t-222-claude-garment-contact`, input `origin/main@625c634`. Opt-in only: `shot_render.py --garment-pushout`
(`pipeline/charsys/garment_pushout.py`); without the flag nothing runs.

## Round 1 (2026-11-23)
### Targets
| # | Target | State |
| --- | --- | --- |
| A1 | Opt-in flag, identity without it (one s020 frame) | in progress |
| A2 | garment_body before / after: e912 s020 (all frames, step 2) and s010 (sit down, f1-80) | in progress |
| A3 | No new pops (garment jump > 5 mm added, T-194 rule): HARD acceptance, per character, full shot at step 1 (Supervisor R8) | in progress |
| B | Cloth evaluation (pieces, cost / frame, determinism, look), STATUS + wait for go | in progress |

### Current settings (`garment_pushout.DEFAULTS`)
| Key | Value |
| --- | --- |
| `margin_m` | 0.0015 |
| `clearance_cap_m` | 0.01 |
| `max_exit_m` | 0.5 |
| `move_fade_m` | 0.05, 0.08 |
| `nearest_cone_deg` | 150 (90 / 120 left shallow cases inside in the synthetic test) |
| `smooth_iterations`, `normal_smooth` | 0, 2 |

### Open defects / questions
- Per-shot key `production.render.garment_pushout`: approved (R8), forwarded by run_shot.py like hair_pushout.

### Sheets
(none yet)
