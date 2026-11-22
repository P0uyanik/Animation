# T-214 checkpoint

- Done: measurer (tools/fit/measurer.py, render.py measure_views); validation of all three characters against T-204
  hand traces (auburn 53/64, white-haired 48/62, boy 59/69 with the Supervisor's visible-opening and visible-crown defaults), every disagreement explained in explained.json and
  enforced by tools/fit/tests/test_measurer.py (local, bpy, ~60 s); 8-yaw + reference measure runs per character.
- Inputs: T-204 from origin/t-204-codex-face-targets (untracked in the worktree, not committed); T-202 sheets staged
  under build/in/ (git archive of t-202-claude-face-sheets@25b2bed2) for the evidence plates.
- Remaining: none; READY sent (re-sent after the R7 defaults).
