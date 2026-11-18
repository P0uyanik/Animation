# T-086: CI efficiency (Phase A, round 2) — report

Branch `t-086-claude-ci-efficiency`, input `589fb3d`. Rules documented in [GATE.md §5](../../../process/GATE.md).

## What changed

| File | Change |
| --- | --- |
| `.github/workflows/checks.yml` | plan: task-branch tier rule (`t-*` fast unless `[full]`; `[full]` raises any branch), "already verified" lookup on `staging`/`main` pushes; linux/renderer/regression jobs skipped when the commit already passed; verdict reports the verifying run; Windows job removed |
| `.github/workflows/windows.yml` (new) | the Windows gate job, unchanged steps, nightly 03:43 UTC + `workflow_dispatch`, binding (job fails on a gate FAIL); vcpkg cache saved from `main` only (key has no branch/commit → shared by every branch) |
| `.github/workflows/ci-status.yml` (new) | after every completed `main` run of the other workflows, daily and on demand: latest result of every workflow on `main`, red while any is red |
| `tools/ci_status.py` (new) | `status` (monitoring table) and `verified` (successful gate run for an exact SHA on given branches, with required jobs and optional wait) |
| `docs/process/GATE.md` | §1 Blender-tier note, §5 rewritten (5.1 promotion rule, 5.2 Windows, 5.3 monitoring) |

Not changed: `combine_check_reports.py`, `trial_merge.sh`, `select_base.sh` (its `windows` output is now unused),
`backup.yml`, `cleanup.yml`, the renderer job's build settings (it only gained the same `if: mode == 'run'` as the
other gate jobs), `tools/check_all.py`, tier rules.

## The promotion rule (criterion 1)

`integration/<x>` runs the full gate. `staging` and `main` are then pushed to the same SHA. On each push the plan job
asks `tools/ci_status.py verified` whether a Quality gate run **for exactly this SHA** succeeded on `integration/*`
(`main`: also `staging`) with plan, linux gate, linux renderer and Gate verdict green — and, when the promoted range
`<previous tip>..SHA` contains a full path, every `regression <character>` job green. If so, all gate jobs are
skipped and **Gate verdict** passes with a link to that run. `main` waits (≤ 150 min) for a still-running run of the
SHA; a failed run for the SHA fails the verdict; no run at all → the full gate runs as before. Backups unchanged.

Checked against recorded runs (`gh api`, same function the plan job calls):

```
verified --sha 589fb3d… --branches 'integration/*,staging' --require-full-for '[3 characters]'
  → mode=verified, run 44336710501 on integration/t-085 passed
verified --sha 740e817… (integration/t-081, before T-085)
  → mode=run: "passed but does not cover the gate: job linux renderer missing"
verified --sha b03dc93… with --require-full-for (integration/round2-a5 was a fast-tier run)
  → mode=run: "… job regression boy_yellow_hoodie missing, …"
```

## Effect: one promotion, before vs after (criterion 5)

Measured from recorded runs on 2026-11-18 (job wall-clock minutes from the Actions API; "billed" rounds each job up).
Before = the workflow at `589fb3d` (T-085: renderer job added to every run).

| Run | Before | After |
| --- | --- | --- |
| Quality gate `integration/<x>` (full) | 56.5 min (run 44336710501: linux 22.8, regressions 12.3 + 11.1 + 1.0, renderer 8.6) | same, 56.5 min |
| Quality gate `staging` | plan 0.3 + linux 3.8 + renderer 8.6 + **windows ≥ 61** (never finished: cancelled at 61.3 / 28.6 min, runs 44317730791, 44335726882) ≈ **74** | plan + verdict ≈ **1** |
| Quality gate `main` | full range: plan 0.3 + linux 22.9 + regressions 29.7 + renderer 8.6 + **windows ≥ 61** (run 44335726799, 81.5 min before the renderer existed) ≈ **123**; fast range ≈ 80 (run 44317730095) | plan + verdict ≈ **1** (+ the wait, on one small runner, only if `main` is pushed before the integration run finished) |
| Backup `staging` (tag) / `main` (tag + bundle + restore test) | 0.3 / 6.4–13.5 | unchanged |
| CI status (main) | — | 2 × ≈ 0.3 (after the `main` gate and backup runs) |
| **Runs per promotion** | 5 (3 gate, 2 backup) | 7 (3 gate, 2 backup, 2 status) |
| **Full gate runs per promotion** | 2–3 (integration + `main`, `staging` too when main had not moved yet) | **1** |
| **Runner-minutes per promotion** | ≈ **200–270** (≈ 122 of them Windows that never completed) | ≈ **66–73** |

Windows moves to one nightly run (≈ 30–70 min depending on the vcpkg cache) instead of two per promotion; on
2026-11-18 alone `main` received 33 pushes (66 Windows jobs started, none completed). Since 2026-11-16, 92 of 93
`main` and 70 of 71 `staging` gate runs were cancelled — `main` effectively never had a finished Gate verdict.

## Criterion checklist

1. One full gate run per promotion — `checks.yml` plan "Already verified?" + verdict step; GATE.md §5.1.
2. Task branches fast tier, full with `[full]`; integration branches decided by paths (full when any full path
   changes, as defined in §2; `[full]` raises it). On a capped task branch the "Blender tier" line states that it
   runs on the `integration/*` gate (`--blender-on-other-runner`), never silently.
3. Windows: nightly + dispatch, binding, removed from all pushes; vcpkg cache key shared by all branches.
4. Monitoring: `tools/ci_status.py status` + `ci-status.yml`; GATE.md §5.3. Real output (2026-11-18 16:04 UTC):
   ```
   WARN Branch cleanup: decisive failure (push, 3321e9d, 20 h ago, run 44157541086); … workflow-file error at
        3321e9d is stale: .github/workflows/cleanup.yml changed on main since (2026-11-17T19:26:03Z)
   WARN Quality gate: decisive -; newest in_progress (push, 589fb3d, …); no decisive result in the last 30 runs on
        main (all cancelled/skipped/running)
   PASS Verified repository backup: decisive success (push, 589fb3d, 8 min ago, run 44341274335)
   WARN relay-notify: decisive -; newest -; no run on main; last run on relay-channel: success (…)
   ```
   A workflow-file error (a run with no jobs, named after the file) counts as stale (WARN, not FAIL) once the file
   changed on `main` after it; otherwise a workflow that never runs on `main` again (cleanup) would stay red forever.
5. Before/after above.
6. No check removed or loosened: every job and check of a full gate still runs once per promotion, on the exact
   commit that reaches `main`; Windows runs the same `check_all.py` steps and now fails its workflow instead of being
   "informational".

## Tested / not tested

- Tested: `actionlint` 1.7.7 on all workflows (clean); `tools/regression/tests/test_gate_tools.py` (PASS);
  `ci_status.py verified` and `status` against the real repository (above); the tier rule shell logic for
  t-*/[full]/integration/staging cases.
- Not tested before merge: the `staging`/`main` "already verified" path and `windows.yml`/`ci-status.yml` on
  GitHub — they only run on `staging`/`main` pushes, on schedule, or by `workflow_dispatch`, which needs the
  workflow file on the default branch. First promotion after merge exercises §5.1.

## Open points for the Supervisor

- Pre-existing: `select_base.sh` compares `staging` against `origin/main`; when `main` is pushed first the `staging`
  run sees no changes (fast tier). With T-086 the verification requirement uses the branch's previous tip instead,
  but a fallback full run on `staging` keeps that weakness (fix needs `select_base.sh`, outside the write-set).
- `Branch cleanup` has a stale workflow-file error on `main` (run 44157541086, 2026-11-17; the file was fixed six
  minutes later) and, the same day, on old task branches; listed as WARN.
- Rulesets: unchanged (required check stays **Gate verdict**).
