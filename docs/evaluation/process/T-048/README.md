# T-048 report: automatic branch cleanup workflow, fully tested

1. **Task / objective:** build a GitHub Actions workflow that deletes merged branches only under strict, tested
   conditions (DELIVERY_PLAN §8.2).
2. **Result:** complete for AC1–AC4 and AC6. AC5 (first real dry run) is the Supervisor's step after merge
   (instructions below). The tests are not yet in `check_all.py`, because T-041 owns that file; the line to add
   is below.

## 3. Files changed

| Path | Purpose |
| --- | --- |
| `.github/workflows/cleanup.yml` | Trigger on push of `cleanup/REQUEST.json` to `cleanup-request`, or `workflow_dispatch`. Self-test job, guard, gather, decide/delete, log commit to `cleanup-request`. |
| `tools/cleanup/select.py` | All decision logic as pure functions: request schema and hash, name validation, protection, TASK_LOG open rows, backup-run status, dry-run approval, decision table, log format. |
| `tools/cleanup/cleanup.py` | Runner CLI (`run`, `hash`, `runs-to-verify`, `restore`). Gathers git facts, then pins, deletes with a lease and logs. |
| `tools/cleanup/run_tests.py` | Runs all cleanup tests. This is what goes into `check_all.py`. |
| `tools/cleanup/tests/scratch_repo.py` | Scratch bare remote plus work clone, isolated git config. |
| `tools/cleanup/tests/test_select.py` | Unit tests and scratch-repository selection tests. |
| `tools/cleanup/tests/test_end_to_end.py` | CLI end to end on `cleanup-test/*` branches against a local bare remote, including restore. |
| `tools/cleanup/tests/test_workflow.py` | Static safety checks of `cleanup.yml`. |
| `tools/cleanup/tests/test_workflow_rehearsal.py` | Runs the workflow's real shell steps with bash against a scratch remote and a fake `gh`. |

Documentation:
- `docs/process/CLEANUP.md`: how to request, how it decides, how to restore.
- `docs/evaluation/process/T-048/README.md`: this report.
- `docs/evaluation/process/T-048/first_dry_run_REQUEST.json`: draft request for the first real dry run.

## 4. Design and decisions

**Overview**
- **Where the code comes from.** Tools and tests always come from a credential-less checkout of `main`. The
  `cleanup-request` branch supplies only the request and the logs. A guard stops the run if the workflow file on
  `cleanup-request` differs from `main`. (GitHub runs a push-triggered workflow from the pushed branch, so without
  the guard a modified workflow there could run.)
- **Self-test first.** The `self-test` job runs `tools/cleanup/run_tests.py` first, and the cleanup job `needs` it.
  Every real run is therefore preceded by the full test suite.
- **Facts vs decisions.** `cleanup.py` gathers the facts: `git fetch --prune` of heads and `backup/*` tags,
  `rev-parse`, `merge-base --is-ancestor <tip> origin/main`, and `for-each-ref --contains <tip>` over
  `refs/tags/backup/` and `archive/backup-*`. `select.decide()` makes every decision.

**Decisions I made:**
- **Request hash.** sha256 of the canonical JSON of `branches` (order-sensitive), `requested_by` and `reason`. It
  excludes `mode`, so a dry run and its delete share one hash. Any other change needs a new dry run.
- **Stricter than the AC: per-branch SHA.** The delete must match the dry run's would-delete list per branch, at the
  same tip SHA. A branch the dry run did not approve, or whose tip moved since, is skipped.
- **Dry run must be confirmed by GitHub.** A dry-run record counts only if `GET /actions/runs/<id>` confirms it as
  a `cleanup.yml` run that concluded `success`. A hand-written log line therefore approves nothing.
- **"Latest backup.yml run".** This is the latest **completed** run on `main`, so a nightly run in progress does not
  block. It must be `success`. These all refuse every deletion: no run, no completed run, a failed or cancelled
  run, or a failed API lookup.
- **Backup reachability.** The rule is reachability from any `backup/*` tag or `archive/backup-*` branch, as the AC
  says. So a backup of `main` taken after the merge also counts. The tests show this explicitly.
- **Extra pin tag before deleting.** Before each deletion the workflow pushes a fresh tag
  `backup/<UTC yyyymmddTHHMMSSZ>/<branch>`, the T-041 naming format. If that push fails, the branch is kept.
  Deletion then uses `--force-with-lease=refs/heads/<b>:<sha>`: a branch that moved after the check is kept, which
  is tested.
- **Open TASK_LOG rows.** This is conservative.
  - All tables are scanned. A row is closed only when its State/Status cell says one of: accepted, merged, in main,
    closed, done, rejected, cancelled, superseded, abandoned. A negated form ("not merged") keeps it open.
  - A row without a state column is open.
  - The branch name must appear as a whole token anywhere in an open row.
  - The workflow uses the union of `TASK_LOG.md` from `main` and `staging`.
  - Against the real TASK_LOG this protects exactly `t-040-claude-pose-clearance`, `t-041-claude-gate-claims`,
    `t-043-claude-spec-versions`, `t-046-claude-facial-animation` and `t-048-claude-branch-cleanup`.
- **Protected names.** I added `master` to the list in the AC. This is harmless.
- **Rejected requests.** These are rejected as a whole, and nothing is considered: wildcards, `refs/`/`origin/`
  prefixes, duplicates, unknown fields, or more than 200 branches.
- **Logs.**
  - `docs/process/CLEANUP_LOG.md`: `date | branch | sha | request hash`, one line per deletion.
  - `cleanup/DRY_RUN_LOG.jsonl`: one record per dry run.
  - Both are committed only to `cleanup-request`, with merge-and-retry on a push race and no force.
  - The decision table goes to the job summary, and the decision JSON is uploaded as an artifact.
- **`select.py` shadows the stdlib.** The AC fixes the name `tools/cleanup/select.py`, but that name shadows the
  standard-library `select` module, which `subprocess` imports. Every entry point removes its own directory from
  `sys.path` and loads `select.py` by path. A test runs the CLI with `cwd=tools/cleanup` to prove this works.
- **No global "deletion enabled" switch.** A repository variable would need settings access. Real deletion is gated
  per request by the confirmed dry run instead.

## 5. Tests executed

`python3 tools/cleanup/run_tests.py` gives `cleanup tests: 25 run, 0 failures, 0 errors, 0 skipped`. All tests use
scratch repositories in temp directories. No real branch of this repository was touched, and no dry-run request was
pushed.

| Case (AC4) | Where | Result |
| --- | --- | --- |
| merged + backed up → selected | test_select `test_only_correct_branches_selected`, e2e | PASS |
| unmerged → skip | test_select, e2e | PASS |
| merged then new commit → skip | test_select (`t-102`), e2e (`late-commit` after dry run) | PASS |
| each protected name (`main`, `staging`, `relay-channel`, `supervisor-state`, `decisions-tools`, `cleanup-request`) | test_select (real branches in scratch repo + pure) | PASS |
| `archive/**`, `backup/**`, `codex/**` | test_select | PASS |
| open-task branch (incl. "open, redesign", "delivered", "not merged", status tables, rows without state) | test_select `test_task_log_*`, e2e, rehearsal | PASS |
| missing backup → skip; archive/backup-* branch counts; main backup tag counts | test_select `test_facts` | PASS |
| failed / cancelled / never-run / in-progress-only / lookup-failed backup.yml → nothing | test_select `test_backup_run_status`, `test_failed_never_run_*`, e2e `test_failed_backup_run_deletes_nothing` | PASS |
| delete without prior dry run; with unconfirmed / failed / other-workflow run; other request content | test_select `test_dry_run_approval`, `test_delete_without_prior_dry_run`, e2e steps 2–3 | PASS |
| delete only approved branches at unchanged SHA | test_select `test_delete_after_dry_run_only_approved_and_unchanged` | PASS |
| unknown branch name; invalid names / wildcards; invalid request | test_select, e2e `test_invalid_request_considers_nothing` | PASS |
| E2E: create `cleanup-test/*`, merge into scratch main, dry run (no ref changes), delete against local bare remote, pin tag present, log lines, rerun deletes nothing, restore from log + SHA verified, second restore refused, manual restore line | e2e `test_full_cycle` | PASS |
| branch moved between check and delete → kept (lease) | e2e `test_branch_moved_between_check_and_delete_is_kept` | PASS |
| Workflow shell steps rehearsed: dry run → log committed to cleanup-request; delete → CLEANUP_LOG committed; main unchanged; tampered workflow on request branch → guard stops | rehearsal | PASS |
| workflow static: no schedule, triggers, permissions, tools from main, only push target is cleanup-request | test_workflow | PASS |

**Mutation check:** I disabled six safety conditions one at a time in `select.py`: merged, backup ref, backup run,
SHA-unchanged, open task and dry-run approval. Each mutation made at least one suite fail.

**Bug found by the rehearsal:** the log-commit step used `git add a b || true`. That silently staged nothing when
`CLEANUP_LOG.md` did not exist yet, so the dry-run log was never committed. I fixed it to add only existing files.

**Gate:** `git merge origin/staging` was already up to date. Then
`python3 tools/check_all.py --base origin/main --artifacts-dir <scratch>`:

| Check | Result |
| --- | --- |
| Frozen assets | PASS |
| Shared-systems lint | PASS |
| Python tests | PASS |
| Documentation links | PASS |
| Blender tier | PASS |
| Guarded paths | **FAIL by design**: needs Supervisor approval (see below) |
| C++ build / CTest / plush_tests | **FAIL, environmental** |

- **Guarded paths.** The workflow and every test file are guarded paths, and Implementers cannot add the trailer.
  The Supervisor adds these trailers:
  - `Supervisor-Approved: .github/workflows/cleanup.yml`
  - `Supervisor-Approved: tools/cleanup/tests/scratch_repo.py`
  - `Supervisor-Approved: tools/cleanup/tests/test_end_to_end.py`
  - `Supervisor-Approved: tools/cleanup/tests/test_select.py`
  - `Supervisor-Approved: tools/cleanup/tests/test_workflow.py`
  - `Supervisor-Approved: tools/cleanup/tests/test_workflow_rehearsal.py`
- **C++ build.** CMake cannot find `embree` 4 in this container (`cpp-build.log`: "Could not find a package
  configuration file provided by embree"). This task changes no C++ file.

**Not tested:**
- The real GitHub run: the API responses (`gh api`), `GITHUB_TOKEN` push rights for deletions and tags, and
  repository rulesets that might refuse tag creation. Those are simulated. If a ruleset refuses the pin tag, the
  branch is kept.
- Windows: the rehearsal is skipped there, and the other tests are expected to run but were not run on Windows.

## 6. Baselines

No frozen asset, existing test, threshold, `check_all.py`, `integrate.py`, `checks.yml` or `backup.yml` was
touched. The "Frozen assets" check passes.

## 7. Visual results

Not applicable.

## 8. Open points for the Supervisor

**Wire the tests into the gate (one line).** In `tools/check_all.py` `check_python_tests()`, add this to the
`tests` list:

```python
        [sys.executable, str(ROOT / "tools/cleanup/run_tests.py")],
```

**First real dry run (AC5).** Run it after T-048 is merged into `main`:

1. Create `cleanup-request` from `main`:
   `git push origin origin/main:refs/heads/cleanup-request`.
2. On it, copy `docs/evaluation/process/T-048/first_dry_run_REQUEST.json` to `cleanup/REQUEST.json`. The draft has
   `mode: dry-run` and the 51 current `t-*`, `integration/*` and `roadmap-*` branch names from `ls-remote`. Edit the
   list if you like. The open-task branches in it are skipped automatically. Commit and push.
3. Review the job summary. Then fetch `cleanup-request`, which now has the dry-run log commit.
4. Change only `"mode": "delete"` and push again.

Expected in the first dry run:
- There are no `backup/*` tags on GitHub yet; `ls-remote` shows 0. But `archive/backup-20261117-1417-main` exists,
  so every branch merged into `main` before that snapshot counts as backed up.
- Everything is refused until `backup.yml` has at least one successful completed run on `main`.

**Restore.** Use `git push origin <sha>:refs/heads/<name>` with the SHA from `docs/process/CLEANUP_LOG.md` on
`cleanup-request`, or use `cleanup.py restore`.

## 9. Commits

Branch `t-048-claude-branch-cleanup`. The commits are listed in the RELAY_LOG line, and the final commit is the
branch head.

## 10. Resource use

Token usage is not available. No repeated builds. The gate ran once, and the cleanup tests ran a few times while
developing (each run takes about 6 s).
