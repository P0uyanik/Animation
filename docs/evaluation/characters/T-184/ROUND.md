# T-184 round file (garment under skin when seated / in the walk)

Keep this current each round so a fresh session can take over. Details and numbers: [`README.md`](README.md).
Branch `t-184-claude-seated-garments`, input `origin/main@7135087`. Opt-in only: the `garment/3` item field
`seated` (`pipeline/charsys/garments_v3/seated.py`); no spec under `assets/` uses it.

## Round 1 (2026-11-21): design approved ~16:02Z, CHECKPOINT
### Targets
| # | Target | State |
| --- | --- | --- |
| 1 | Reproduce on T-175's seated clip, find the cause | done: two faults, weights and collision weights (README "Cause") |
| 2 | Girl's shorts under the skin when seated | as rendered: 149 → 0 vertices under visible skin; engine check −57.9 → −26.9 mm. The thighs still leave the shorts through the front panel (limit 1) |
| 3 | Walk case (Supervisor 15:51Z) | girl: same cause, engine check −28.3 → −13.8 mm, the leg tube now follows the thigh (sheet). Boy: ankle hem, not the hip, out of scope |
| 4 | Opt-in, released versions / packages / goldens unchanged | done: default builds compared (README "Opt-in evidence") |
| 5 | Before / after sheet, both characters, numbers | done: three sheets ≤ 1024 px, `numbers.json` |

### Current settings (defaults of `seated`, used by both overrides as `"seated": true`)
| Key | Value |
| --- | --- |
| `leg_weights.centre_m` | 0.012 (0.006 tried: same worst value, fewer flagged vertices; kept at the default) |
| `collision.hip_deg` | 45, 90, 110 |
| `collision.radius_m`, `falloff_m` | 0.03, 0.03 |
| `leg_bone`, `fk_bone` | `DEF-thigh.{side}`, `thigh_fk.{side}` |

Tried and dropped: blending by distance along the cloth from the centre seam instead of by distance from the centre
plane. The leg split leaves long edges across the centre at the hem, so most leg-tube vertices counted as "on the
seam" and the engine check went back to −56 mm.

### Evidence inputs
- Motion: `t-175-claude-locomotion@c384f1d` review shot, read only; frames 24 and 150 in `bake_excerpt.json`.
- Before: published boy 2.3.0 / girl 0.14.0. After: the same specs + `overrides/*.T-184.override.json`, built here.

### Open
- Limits 1–5 in the README (accepted for this round by the Supervisor 16:02Z).
- Supervisor applies at merge: release-rule detector, `TESTS` line, `GENERATOR_PINS.md` row, guarded-path trailer for
  the new test (texts in the README).
- The claim also lists `assets/characters/*/spec/candidates/T-184/**`; it is not used (an override under `assets/`
  would trip the release rule's `characters` scope), the overrides are in this folder instead.
- Follow-ups: boy ankle hem; a seated corrective for short leg tubes; button / embroidery normal variation on `main`.
