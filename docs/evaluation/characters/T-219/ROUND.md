# T-219 round file (hair release: V1 flock + H2 volume + cap border)

Branch `t-219-claude-hair-release`, input origin/main `39717ee`. Supervisor `session_01NPjxeNFfmkruSmnvcb3uSH`.
Owner decision: OWNER_DECISIONS.md 2026-11-23 ~06:58 CET (V1 for both girls, boy unchanged, fix the stair-step with H2).

## Targets
- Candidates (never CURRENT): girl_auburn_bun_glasses **0.15.0** (parent 0.14.0), girl_white_hair_blue_dress
  **0.2.0** (parent 0.1.0). Face untouched (D6): specs = the CURRENT published spec + hair layers only.
- Specs: `assets/characters/<id>/spec/candidates/T-219/<id>.<ver>.spec.json`, composed by `make_specs.py` from
  `h2/<id>.json` + `../T-207/options/V1.json`.

## Current overrides (h2/<id>.json)
- both: `hair.cap_contour` {structure cap, corner_round_m 0.008} (stair-step fix), `hair.flock` = V1.
- auburn: crown height [0.022, 0.036, 0.03] (was 0.05 mid), bun el 62 (was 82), curtain rest_radii [0.15, 0.145],
  ringlets_back(_b) rest_radii [0.17, 0.165], ringlets_side/outer hang_radii x 0.176.
- white: buns az +-84 el 60 (was +-56 / 54), back_mass / back_under / back_locks / outer_locks / side_locks radii
  reduced ~5-9 %, back/outer lock lift reduced.

## Silhouette (hair_silhouette.py: head zone above the shoulder line, body-scaled, 4 views equal weight)
| | IoU head | area ratio | width ratio | top ratio |
|---|---|---|---|---|
| auburn 0.14.0 (current) | 0.819 | 1.025 | 0.948 | 1.045 |
| auburn r1 | 0.843 | 1.026 | 0.956 | 1.045 |
| white 0.1.0 (current) | 0.805 | 1.102 | 1.096 | 0.983 |
| white r1 | 0.838 | 1.029 | 1.021 | 0.974 |

## Open defects / next
- r2 build + measure running (bun back, auburn back fullness).
- Step 6 push-out: s030 copies in `shots/` (current cast running; candidate cast after H2 is final).
- Publish blocked on the decision ref (OWNER_DECISIONS.md must mention 0.15.0 / 0.2.0; asked the Supervisor).

## Sheets
- (pending) preview, then one strict sheet per character + 100 % crops.
