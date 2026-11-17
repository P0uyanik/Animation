# Branch cleanup (T-048, DELIVERY_PLAN §8.2)

Cloud sessions cannot delete branches (the proxy refuses). `.github/workflows/cleanup.yml` deletes merged branches
with `GITHUB_TOKEN`, but only the branches a request lists and only when every safety condition holds. Unmerged
work, protected branches and anything without a backup are never deleted.

## How to request a cleanup (Supervisor)

1. Create the branch `cleanup-request` from `main` the first time. Later, fetch it and merge `main` into it
   (`git merge origin/main`; no rebase, no force-push). The workflow file on `cleanup-request` must be identical
   to the one on `main`, otherwise the run stops at its guard step.
2. Write `cleanup/REQUEST.json` on that branch:

   ```json
   {"mode": "dry-run",
    "branches": ["t-001-studio-shot-pipeline", "t-002-clip-foundation"],
    "requested_by": "Supervisor",
    "reason": "merged first-batch branches"}
   ```

   - `mode`: `dry-run` or `delete`. No other fields are accepted.
   - `branches`: exact branch names (no `refs/`, no `origin/`, no wildcards, no duplicates, at most 200).
3. Commit and push `cleanup-request`. A push that changes `cleanup/REQUEST.json` starts the workflow. You can
   also start it with **Run workflow** (`workflow_dispatch`, from `main` or `cleanup-request`). It always reads the
   request from `cleanup-request`. There is no schedule.
4. Read the decision table in the run's job summary. The workflow also commits its logs to `cleanup-request`, so
   fetch before you write the next request.
5. To delete, change only `"mode"` to `"delete"`, keeping `branches`, `requested_by` and `reason` exactly as they
   were, then push. The request hash covers everything except `mode`, so the delete matches the dry run you
   reviewed. Any other change needs a new dry run.

## How it decides

The tools and tests always come from `main`. Both checkouts of `main` are made without push credentials. The job
first runs `python3 tools/cleanup/run_tests.py`, which uses scratch repositories only. If those tests fail, nothing
else runs. All decision logic is in `tools/cleanup/select.py` as pure functions. A listed branch is deleted only if
**all** of these hold. Otherwise it is skipped, and the job summary gives the reason.

| Rule | Detail |
| --- | --- |
| Valid request | JSON schema above. An invalid request means no branch is considered at all. |
| Valid, existing name | Uses git ref-name rules, rejects wildcards (`* ? [`), and the branch must exist on the remote. Otherwise the reason is "unknown branch". |
| Not protected | The fixed names are `main`, `master`, `staging`, `relay-channel`, `supervisor-state`, `decisions-tools` and `cleanup-request`. The protected patterns are `archive/**`, `backup/**` and `codex/**`. A branch is also protected when it appears as a whole token in an **open** row of `docs/process/TASK_LOG.md`. The workflow reads `TASK_LOG.md` on both `main` and `staging`, and a row open in either counts. A row is closed only if its State/Status cell says result accepted, merged, in main, closed, done, rejected, cancelled, superseded or abandoned, and does not say "not merged". Rows without a state column count as open. |
| Fully merged | The tip must be an ancestor of `origin/main`. A commit pushed after the merge makes it unmerged. |
| Backup exists | The tip must be reachable from a `backup/*` tag or an `archive/backup-*` branch. A later backup tag of `main` that contains the merge also counts. |
| Backup workflow healthy | The latest **completed** `backup.yml` run on `main` must have concluded `success`. A failed, cancelled or never-run `backup.yml`, or a failed lookup, refuses every deletion ("no backup = no delete"). |
| Dry run first (`delete` only) | An earlier dry run with the same request hash must exist in `cleanup/DRY_RUN_LOG.jsonl`. GitHub must confirm that dry run's run ID as a **successful** `cleanup.yml` run. The dry run must have marked this branch `would-delete` at **the same tip SHA**. |

### Steps for each deletion

For each deletion, the workflow:

1. pushes a fresh pin tag `backup/<UTC yyyymmddTHHMMSSZ>/<branch>` at the tip, and keeps the branch if that push
   fails;
2. deletes the branch with `--force-with-lease=refs/heads/<branch>:<sha>`, so a branch that moved after the check
   is kept;
3. checks that the branch is gone;
4. appends `date | branch | sha | request hash` to `docs/process/CLEANUP_LOG.md`.

Both logs are committed to `cleanup-request` only, never to `main`. A dry run deletes nothing. It appends one
record (hash, run ID, would-delete branch → SHA) to `cleanup/DRY_RUN_LOG.jsonl`. The decision JSON is also
uploaded as a run artifact for 90 days.

No tool deletes tags under `backup/`, so every deleted tip stays reachable on GitHub.

## How to restore

Each line in `docs/process/CLEANUP_LOG.md` (on `cleanup-request`) has the branch name and SHA. To restore a branch,
run:

```sh
git push origin <sha>:refs/heads/<name>
```

You can also use the helper, which refuses to overwrite an existing branch and checks the SHA afterwards:

```sh
python3 tools/cleanup/cleanup.py restore --repo . --cleanup-log docs/process/CLEANUP_LOG.md --branch <name>
```

The helper needs a session that can push. Cloud sessions can push branches, so restoring works from them.

## Tests

`python3 tools/cleanup/run_tests.py` runs four test files, all on scratch repositories:

| File | What it covers |
| --- | --- |
| `test_select.py` | Unit and scratch-repository tests. |
| `test_end_to_end.py` | Runs the CLI against a local bare remote on `cleanup-test/*` branches, including restore. |
| `test_workflow.py` | Static checks of the workflow. |
| `test_workflow_rehearsal.py` | Runs the workflow's real shell steps against a scratch remote, with a fake `gh`. |

None of them touches the real repository. The full test matrix is in `docs/evaluation/process/T-048/README.md`.
