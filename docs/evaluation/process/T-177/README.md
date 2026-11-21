# T-177: docs-only fast path for ledger pushes

Input `b531ab5`. Rule and promotion behaviour: `docs/process/GATE.md` §5.6.

## Rule
Push to `main`/`staging`; changed paths = `<previous tip>..HEAD` (`git diff --no-renames`, both rename/delete sides).
`tools/regression/tiers.py docs_only()`: non-empty and every path starts with `docs/process/` or `docs/tasks/`.
- true → plan mode `docs`: only job `docs-only fast path` (doc links, `integrate.py claims --list`,
  `test_gate_tools.py`); linux/regression/Blender shards skipped; Gate verdict `PASS Docs-only fast path: …`.
  The "already verified" wait (up to 150 min) is skipped too.
- false (mix, empty, unknown/zero `before`, `workflow_dispatch`) → unchanged full gate.
- `ci_status.py verified --docs-only-vs origin/main`: a commit with no run of its own is verified by the run of a
  green `origin/main` commit (newest 50, full gate incl. regression jobs) when the diff vs it is docs-only; cites that run.
- Task/integration/PR tiers, Blender shards, Windows gate: untouched. `ci-status.yml` needed no change.

## Tests (`tools/regression/tests/test_gate_tools.py`, no new file)
- `test_docs_only`: docs-only → fast; docs + other → full; `docs/processX/`, `docs/tasks.md`, `docs/evaluation/**`,
  `docs/process` (no slash), `..` escape → full; rename/delete sides; empty → full; tier rules unchanged.
- `test_docs_equivalent`: temp git repo + fake API: docs-only diff vs green commit → verified, cites run 7; code commit
  in between / none green → full gate.
- Result: `python3 tools/regression/tests/test_gate_tools.py` → `PASS gate tools: 0 failure(s)`.

## Example runs
Real CI runs of the fast path exist only on `main`/`staging` pushes (the plan step is limited to them; not exercised: no
push rights there from this task). Real classifier output (`tiers.py --base <input>` in a scratch worktree of the branch
commit, scratch commits not pushed):
- edit `docs/process/TASK_LOG.md` + `docs/tasks/T-177.md` → `docs_only: true`
- same + `tools/ci_status.py` → `docs_only: false` (full gate)
First real main/staging docs-only push after merge is the live check; the Supervisor should look for
`Tier: docs-only fast path` in its Gate verdict.
