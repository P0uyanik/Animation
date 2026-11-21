# T-NNN: <title> (Phase <X>, round 2)

Implementer: <agent> · lane <L> · path <A technical | B visual> · branch `t-NNN-<agent>-<slug>` from `origin/main`
(input SHA in the task prompt). Round 2 plan: `docs/process/ROUND2_PLAN.md` <row>. Owner-approved <date>.

## Why (evidence)
- <audit finding or owner decision, with file or figure>

## Acceptance criteria
1. <measurable outcome>
2. Visual tasks: one cheap first frame (`tools/review/recipe.py preview`) before any long render, then one T-087
   strict sheet as the single visual deliverable.
3. No test loosened, no frozen or published file changed.

## Kit (T-165; use these, do not write per-task scripts)
`tools/review/shot_sheet.py` (shot before/after grid + crops) · `tools/render_queue.py run -- <render>` ·
`tools/run_logged.py -- <cmd>` · `tools/wait_gate.py <run-id>` · `tools/ready.py` before READY.

## Round file (visual tasks, T-176 P2)
Keep `docs/evaluation/<area>/T-NNN/ROUND.md` up to date each round: targets, current overrides, open defects, sheet
paths. A fresh session must be able to continue from it plus this brief. Read sheets as crops of at most 1024 px.

## Write-set
Every file a solution may touch, as back-ticked repository-relative globs (the gate's write-set check fails on any
other file). Name read-only dependencies separately. Guarded paths in the write-set need a `Supervisor-Approved:`
trailer at merge.

## Reporting
Run `tools/ready.py`, then send its line once to the Supervisor session (relay line as fallback):
`<UTC> | T-NNN | READY|BLOCKED|STATUS | <branch@sha> | input <SHA> | <one line>`.
READY ends with one line `ledger: build N · render N · tests N · ci N · wait N (min)`.
