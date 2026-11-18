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

## Write-set
Every file a solution may touch, as back-ticked repository-relative globs (the gate's write-set check fails on any
other file). Name read-only dependencies separately. Guarded paths in the write-set need a `Supervisor-Approved:`
trailer at merge.

## Reporting
send_message to the Supervisor session (relay line as fallback):
`<UTC> | T-NNN | READY|BLOCKED|STATUS | <branch@sha> | input <SHA> | <one line>`.
