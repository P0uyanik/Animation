# Workflow evaluation, end of round 4 (T-130)

Input `integration/t-117 @ 7fb2ffe`, 2026-11-19. Existing data only: TASK_LOG, task READMEs, `gh api` run data (949 runs,
2026-11-18 00:04Z .. 2026-11-19 17:35Z), RELAY_LOG, T-127 and T-128 reports. Raw data and scripts:
`docs/evaluation/workflow/T-130/` (`extract.py`, `summarize.py`, `codex_quota.py`). **M** = measured, **E** = estimate,
**n/a** = the existing data does not answer it (no new logging was added to fill gaps).

Run-level caveat: the API gives run start/end, not billable minutes (T-127 §d: reported 0). Per-run wall clock over all
gate runs is not meaningful: most task-branch runs end red on purpose or are path-skipped (see 2 and 4).

## 1. "Animation" environment setup script (`env_01MTWJVTWBHG13yZcRS4DzCz`)
| | before | after |
|---|---|---|
| ledger "build" min per session | T-089b 45, T-090b 16.4, T-093b 38, T-115 40.3 (n=4, 2026-11-18/19, M) | T-119 58, T-123 12, T-129 0 (n=3, 2026-11-19, M) |
| setup failures | no record | no record |

Not comparable: the ledger has no field for setup time, "build" mixes C++/Blender builds with task content, and the
README ledger lines do not state which sessions ran on the new environment. No cutover time is recorded.
**Recommendation: keep** (no evidence either way; it was a prerequisite for T-127's apt cache). To decide, add one
`env` word to the ledger line in round 5.

## 2. CI speed (T-127 items 1-5)
| | before | after |
|---|---|---|
| gate wall clock, same commit class | 45.3 min (run 44508054856, n=1, M) | 17.0 min (9b5f905 attempt 2, n=1, M); under equal load 44 vs 28 min (n=1 each, M) |
| runner minutes (sum of jobs) | 82.2, 7 jobs | 81.0, 12 jobs (equal, M) |
| superseded runs cancelled | 199 cancelled of 550 gate runs before 15:44Z (M; includes manual) | 1 of 10 after (n small) |
| flaky reruns (attempt > 1) | 3 of 550 | 0 of 10 |
| READY -> merged-on-main latency | n/a (no READY timestamps in a machine-readable place) | n/a |
| test inventory unchanged | baseline 20 full / 20 fast commands | 20 / 20, same args and order (`inventory.json`, M) |
| probes still caught | -- | 5 probe runs red for their own reason; sharded and unsharded identical (M, T-127 §b) |

Open: one probe was a no-op, the C++ `sqr()` probe is caught only by the renderer-ON job (predates T-127).
Only n=1 per side for wall clock: it is a one-off comparison, not a distribution.
**Recommendation: adopt.** Critical path is now the 15.6 min `garment_generic_test` and the two 14 min regression jobs.

## 3. Tooling trial (T-128), session numbers, not CI
| | before | after |
|---|---|---|
| clean C++ build | 114.9 s | 1.6 s warm ccache, new dir; 109.8 s cold (n=1 each, M) |
| mold | 114.9 s | 108.0 s clean, no gain (n=1; 3 incremental runs equal) |
| Python tests (23) | 11.3 / 12.1 / 13.1 s | 7.8 / 8.5 / 8.7 s with `-j4` (n=3) |
| C++ doctest (215) | 202.7 / 198.4 / 202.7 s | 110.8 / 112.7 / 112.2 s `-j4` (n=3) |
| pass/fail | 215/215, 23/23 | identical per case / per script in 6 of 6 runs (M) |

**Recommendation:** ccache preset and parallel helper: adopt as opt-in (pending owner, per TASK_LOG); mold: revert/skip;
OIIO/SSIM/VMAF in the gate: do not adopt (VMAF not measured). Whether sessions actually used the helper: n/a.

## 4. Batch promotions
Gate runs per merged task, round-4 branches (M, `gate_runs_by_branch.json`): T-118 2, T-119 4, T-120 1, T-121 3, T-122 3,
T-114 2, T-127 5, T-128 2. Median 2.5 (n=8 tasks). No pre-T-127 equivalent (no promotion batching existed), so no
before/after delta can be stated. Most task-branch runs are red because of Guarded paths / Merge status, which are red by
design until the Supervisor trailer (T-127 §c), so "failure" is not a quality signal. **Recommendation: keep**; measure
per merged batch in round 5.

## 5. Model choice: Fable 5.2 (T-118, T-119, T-120) vs Opus 5.5 (same round)
| | Fable 5.2 | Opus 5.5 |
|---|---|---|
| tasks merged | T-118, T-119, T-120 (n=3) | T-121, T-122, T-117, T-114, T-113 ... (n=5+, round 4) |
| rework rounds | 0 recorded in TASK_LOG | 0 recorded |
| wall time | T-119 ledger total 140 min (build 58, render 55, tests 27); T-118, T-120: no ledger on main | T-123/T-129 are Codex; Opus README ledgers: none found for round 4 |
| token cost per task | n/a (not recorded) | n/a |
| accepted on first review | T-119 accepted by Supervisor with criterion 2 not met (18.5 -> 14.9 L*); T-118, T-120 merged as scoped | T-122: candidates only, fidelity dipped; T-117 merged with 5 open issues |
Not enough data: n=1 ledger for Fable, none for Opus; scopes differ. **Recommendation: keep both; no conclusion.**
Add a token and rework-round field to the READY line if this comparison is wanted.

## 6. Render optimisation (T-124)
**Pending**: no owner-chosen profile yet (TASK_LOG: running since ~12:30Z). Measure s/frame before/after in round 5.

## 7. Codex availability
| window | hours | basis |
|---|---:|---|
| 2026-11-16: 6 quota stops, stated resets (RELAY_LOG), union of windows | 13.9 (sum 17.0, overlapping) | M (n=6) |
| 2026-11-19 overnight (~03:00Z to ~09:00 owner time) | <= 5 | E (OWNER_DECISIONS, no exact stop time) |
| 2026-11-19 T-123 paused ~11:44-13:50Z (usage limit) | 2.1 | M (given by Supervisor, 126 min) |
| 2026-11-19 all sessions, 5-hour usage limit ~15:45-17:10Z | 1.4 (every session, incl. Claude) | M (given by Supervisor, 85 min) |

agy: quota-out 2026-11-15 22:53Z until ~2026-11-22T20:36Z (stated reset, M). Hours "lost" are availability, not work
lost: cloud work continued (owner rule). **Recommendation: keep** the rule "do not wait for Codex"; keep Codex to
evaluations that stay useful (T-129). The 15:45-17:10Z stop hit everything and cannot be routed around.

## Summary
| item | recommendation |
|---|---|
| 1 setup script | keep (no usable data) |
| 2 CI speed | adopt |
| 3 tooling | adopt ccache + parallel helper as opt-in; revert/skip mold; no OIIO/SSIM in gate |
| 4 batch promotions | keep |
| 5 model choice | keep both; no conclusion |
| 6 render optimisation | pending |
| 7 Codex availability | keep current routing |
