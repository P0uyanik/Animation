# T-214 checkpoint

- Done: measurer (tools/fit/measurer.py, render.py measure_views); validation of all three characters against T-204
  hand traces (auburn 51/64, white-haired 46/62, boy 59/69), every disagreement explained in explained.json and
  enforced by tools/fit/tests/test_measurer.py (local, bpy, ~60 s); 8-yaw + reference measure runs per character.
- Inputs: T-204 from origin/t-204-codex-face-targets (untracked in the worktree, not committed); T-202 sheets staged
  under build/in/ (git archive of t-202-claude-face-sheets@25b2bed2) for the evidence plates.
- Remaining: merge origin/main, tools/ready.py, READY to the Supervisor.
