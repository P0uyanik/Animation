# T-214 checkpoint

- Done: measurer (tools/fit/measurer.py, render.py measure_views); validation of all three characters against T-204
  hand traces (auburn 53/64, white-haired 48/62, boy 59/69 with the Supervisor's visible-opening and visible-crown defaults), every disagreement explained in explained.json and
  enforced by tools/fit/tests/test_measurer.py (local, bpy, ~60 s); 8-yaw + reference measure runs per character.
- Inputs: T-204 from origin/t-204-codex-face-targets (untracked in the worktree, not committed); T-202 sheets staged
  under build/in/ (git archive of t-202-claude-face-sheets@25b2bed2) for the evidence plates.
- Remaining: none; READY sent (re-sent after the R7 defaults).

## P2 hand-off

- **Call:** `python tools/fit/measurer.py measure --character <auburn|white_haired|boy> --out <empty dir>
  [--blend <built head .blend> --spec <its spec.resolved.json>] [--px 512] [--geometric]`. It renders 8 yaws plus
  the 3 reference views (matched smile on smiling fronts, 3/4 held out per `views.json`). Read `measures.json`:
  each row has `group` (face/hair), `current`, `geometric`, `reference`, `tolerance`, `z`, `result`, plus `summary`.
  Fit only non-held-out views, weight views equally, and fit the `hair` group separately with the hair held fixed
  (every H ratio depends on the hair crown). Cost per call at 512 px: auburn 30 s, white-haired 95 s, boy 40 s. For
  a loop, pass only the reference yaws (edit the views list).
- **SHADE (eye opening):** scoring defaults to the visible opening. The top is lowered by `lid_shadow_h × H`: auburn
  0.018, white-haired 0.026, boy −0.001 (fitted on the T-202 renders). The geometric opening is the `geometric`
  column. Refit the band if a release changes lids or lid-line shading.
- **RIM (auburn):** on the 3/4 view the opening runs about 7 units past the glasses rim, while the hand references
  stop at the rim. Auburn 3/4 opening width, iris_d_w and opening_h_w are therefore biased (3/4 is held out anyway).
- **White-haired hidden cheek F:** F is the skin outline under the locks, 188 against 165 units in the hand trace, so
  every /F ratio reads about 14 % lower than a hand trace of the same render. Use tolerance bands, not exact
  targets, or compare in units.
- **Crown:** scored at the visible main-hair top (the bun junction). The hand crowns on auburn's turns (91 and 99)
  sit lower than the visible hair (74 and 83), so fit H ratios to bands.
- Colour (Lab) rows are not measured. Back views give silhouette points only.
