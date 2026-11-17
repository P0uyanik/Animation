# Delivery plan: managing tasks, merges and plans (rev. 2, 2026-11-17)

Status: **approved by the owner 2026-11-17** (overall approach), revision 2 with the owner's four improvements:
parallel tasks inside a lane (§3), full regression for shared/visual changes (§5.1), version safety for existing
characters (§5.2), durable backups and tested branch cleanup (§8). It replaces the per-task part of `WORKFLOW.md`.
Goal: every finished, verified task reaches `main` quickly, without a pile-up of open merge requests and without merge conflicts, and the task status is always current.

---

## 1. Principles

1. **No waiting merge requests.** A task is either *in progress*, *ready* (waiting at most one Supervisor cycle), or *merged*. Nothing sits "open" for days.
2. **Conflicts are prevented, not resolved.** Parallel tasks never write the same files (file claims, §3). Every task finishes on top of the latest `staging`.
3. **Small tasks.** Target: one lane, ≤ 1 day of work, ≤ ~20 changed files. Larger work is split into a chain of tasks.
4. **One source of truth.** `docs/process/TASK_LOG.md` (status) and `docs/tasks/T-NNN.md` (scope). Only the Supervisor edits them.
5. **Quality first.** No merge without the full gate; no weakened tests; visual changes need the owner's eyes.

## 2. Branches

| Branch | Purpose | Who writes |
| --- | --- | --- |
| `main` | Owner-approved state. Always green. | Supervisor only (fast-forward from `staging`) |
| `staging` | Integration branch: `main` + verified tasks. Always green. | Supervisor only (`tools/integrate.py stage`) |
| `t-NNN-<agent>-<slug>` | One task. Branched from `origin/staging`. | Its Implementer only |
| `relay-channel` | `RELAY_LOG.md` status lines (wakes the Supervisor) | Implementers append, Supervisor reads |
| `archive/*` | Preserved unmerged work (e.g. `archive/t-041-codex-local`) | Supervisor |

There is **no GitHub pull request per task**. The "merge request" is the Implementer's `READY` line in `RELAY_LOG.md` plus its report in `docs/evaluation/.../T-NNN/README.md`. This removes the PR backlog entirely; GitHub only runs the checks.

## 3. Lanes and file claims: how conflicts are avoided

Lanes group the code into areas so planning is easy. **Conflicts are decided per file, not per lane:** several tasks
may run in the same lane at the same time when their files and dependencies do not overlap.

| Lane | Owns (write-set) | Typical tasks |
| --- | --- | --- |
| **A: Tools / CI / process** | `tools/`, `.github/`, `docs/process/` (except TASK_LOG/ROADMAP) | gate, integrate.py, regression, cleanup workflow |
| **B: Character system** | `pipeline/charsys/`, character specs, `body_generic` | T-043 spec parts, Boy 2.0 body |
| **C: Engine / animation** | `engine/`, `content/clips`, `content/emotions` | T-046 facial animation, T-045 body mechanics, T-040 clearance |
| **D: Look / assets** | `face_generic`, `groom`, `garment`, materials, `render_calibration.json` | T-044 hair v3, hoodie, girl look round |

Rules:
- Every task file declares a **write-set**: the exact files (or narrow folders) it may change, plus the files it only
  reads and depends on. Running tasks' write-sets are registered in `docs/process/OWNERSHIP.md` ("claims").
- **Parallel start is allowed when** (checked by `tools/integrate.py claims --check T-NNN`, not by memory):
  1. its write-set does not overlap any running task's write-set (file level, glob-aware);
  2. it does not depend on a file another running task is changing in a way it relies on
     (e.g. it calls a function another task is redesigning); such a dependency means it waits or is sequenced;
  3. it does not bump a version number another running task bumps.
  Otherwise the task waits and the next non-conflicting task starts; the lane itself never blocks.
- **Enforced at merge:** the gate fails if a task's diff touches files outside its declared write-set. Widening
  the write-set mid-task needs a Supervisor update of the claim (only if no running task holds those files).
- A task that must touch another lane's files simply declares them; the claim check decides. If they are held, the
  cross-lane part becomes a small prerequisite task, merged first.
- Two tasks in the same lane that finish close together are merged one after the other; the second re-runs the
  trial merge and gate against the updated `staging` (cheap, because their files don't overlap).
- **Hot shared files** have one owner and a fixed edit pattern:
  - `TASK_LOG.md`, `ROADMAP.md`, `OWNER_DECISIONS.md`: Supervisor only.
  - Generator/exporter versions: per-feature version numbers (T-043), so two tasks never bump the same number.
  - Character specs: a new spec version is a new file; existing versions are never edited.
- Before reporting READY, the Implementer runs `git merge origin/staging` and the gate on the result. If `staging` moved during the task, conflicts are found and fixed by the Implementer who knows the code, not at merge time.

## 4. Task lifecycle

```
queued → assigned → in progress → READY → verified → staged → in main → closed
                         ↘ blocked (Supervisor resolves)   ↘ rework (back to in progress)
```

| State | Entry condition | Owner |
| --- | --- | --- |
| queued | Task file `docs/tasks/T-NNN.md` exists: goal, acceptance criteria, write-set, lane, path A/B, dependencies, render/token budget | Supervisor |
| assigned | Lane is free, dependencies are in `staging`; fresh Implementer session started with the full prompt | Supervisor |
| in progress | Implementer commits and pushes at least every hour (no unpushed work) | Implementer |
| READY | All acceptance criteria met, `origin/staging` merged in, gate green, report written, `RELAY_LOG` line pushed | Implementer |
| verified | Supervisor reviewed diff + report, re-ran gate (trial merge), checked visuals against references | Supervisor |
| staged | Merged into `staging` | Supervisor |
| in main | Path A: fast-forwarded right away. Path B: after owner visual approval | Supervisor / owner |
| closed | Session archived, branch deleted by the cleanup workflow after backup | Supervisor |

**TASK_LOG is updated at every state change**, in the same Supervisor commit as the action (assign, stage, promote). A one-line status table at the top shows: running per lane, waiting for owner, next in queue.

## 5. Merge procedure (Supervisor, per READY task)

Target: **merged within one Supervisor cycle** of the READY signal.

1. Read the report and the diff; confirm the diff stays inside the declared write-set (lint enforces shared-systems rules).
2. `tools/integrate.py stage t-NNN --dry-run`: trial merge into `staging`, must be conflict-free.
3. Gate on the trial merge. The gate picks the tier from the changed paths (§5.1); the Supervisor can raise the tier but never lower it.
4. Visual check: renders vs reference images for every affected character.
5. Pass → `integrate.py stage` (merge `--no-ff`, push `staging`), update TASK_LOG, archive the session.
6. Promote:
   - **Path A (technical, no visual change):** fast-forward `main` to `staging` immediately (standing approval).
   - **Path B (visual change):** send the owner a compact review sheet (before/after vs reference). On approval, promote.
7. Fail → task goes to *rework* with a precise list; a fresh session continues from the pushed branch. After 2 failed rounds the Supervisor re-designs the task instead of iterating (lesson from T-040).

### 5.1 Full regression for shared systems and visuals

| Change touches | Required checks |
| --- | --- |
| docs, tools only, isolated tests | fast tier: frozen assets, guarded paths, lint, build, CTest, plush_tests, Python tests, links |
| **any shared system** (`pipeline/charsys` generators: face, groom, garment, body; materials and presets; `render_calibration.json`; exporter; engine animation, emotion and interaction code; shot render) **or any visual file or spec** | **full regression:** fast tier + Blender tier + for **every** character in `assets/characters` (not only the one being worked on): build, geometry/material/rig fingerprint vs `main`, engine export vs `main`, fixed-camera regression renders (turnaround + face close-up) image-diffed against approved baselines, fidelity score (drop > 2 points = FAIL), and the animation regression shots (idle, walk, wave, hand-over: clearance and gaze checks) |

- The path classification lives in one guarded file in `tools/`, so a new shared module is added there once and is
  then always covered. **Unknown paths default to full regression.**
- Efficiency: per-character builds and renders run as parallel CI jobs; unchanged inputs are cached by content hash;
  regression renders are low-sample, denoised and fixed-seed, so a full run stays within the gate time budget.

### 5.2 Version safety: existing characters cannot change by accident
1. A character's spec pins every generator, preset and exporter version it uses. Released versions are immutable:
   their behaviour may not change; improvements ship as a new version (per-feature version numbers, T-043).
2. **Unchanged-character guard (CI):** for every character whose spec is not changed by the task, its build
   fingerprint, export and regression renders must be **identical** to `main` (fingerprints byte-equal; renders
   within the noise threshold measured between two identical builds). Any difference = FAIL, even if it looks better.
3. A character changes only through an explicit **pin-bump task** for that character (path B, owner approval),
   whose diff is limited to that character's spec and assets; the guard then checks that all *other* characters stay identical.
4. Golden fingerprints and regression renders are stored per character version and frozen once approved.
5. Precondition: builds are bit-deterministic (T-038b fixes the boy's last non-deterministic part). A flaky check is
   a bug to fix, never a reason to skip the guard.

### 5.3 Keeping path B from blocking path A
Because of 5.2, visual work ships as a new version that no approved character uses yet, so it is staged and promoted
like technical work. The owner's approval is then a tiny pin-bump change ("girl spec pins hair v3"). `staging` never
holds unapproved visible changes, and `main` can always be promoted.

## 6. Planning cadence

- **Roadmap** (`docs/ROADMAP.md`): phases and order, changed only with owner approval.
- **Queue**: the next 2–3 tasks per lane are written as task files in advance, so a free lane is filled immediately and Implementers never idle.
- **Parallelism**: up to 4–5 Implementers within the Max 5x budget, placed wherever file claims allow (several in one lane is fine). A task whose files are claimed waits; the next non-conflicting task starts instead, so nobody idles.
- **Dependencies**: a task is assigned only when its prerequisites are in `staging`, not "almost done".
- **Owner touch points**, batched to save your time:
  - one visual review sheet per batch of path-B tasks,
  - a short report after every merge batch (what merged, what is running, what needs you),
  - decisions recorded in `OWNER_DECISIONS.md`.

## 7. Keeping Implementers moving

- Every task starts as a **fresh session** with the complete prompt (scope, write-set, acceptance criteria, budget, foreground-only rule, no `send_message`).
- Builds and tests run in the foreground; no ending a turn while waiting on background jobs.
- Supervisor checks running sessions on every wake-up: idle or stuck for more than 30 minutes → interrupt, archive, and continue in a fresh session from the pushed branch (no work lost).
- Routine blockers are solved by the Supervisor; only real decisions go to the owner.

## 8. Safety: durable backups and tested branch cleanup

### 8.1 Durable backups (not only in a temporary container)
Container files disappear when a session ends, so a backup kept only there is not durable. Three layers:
1. **Backup tags on GitHub** (instant, before every promote and every cleanup): `backup/<date>-<time>/<branch>`
   for `main`, `staging` and every branch about to be deleted. Tags keep every commit reachable on the remote.
   No tool ever deletes tags under `backup/`.
2. **Full bundle by GitHub Actions** (`backup.yml`): on every push to `main` and nightly, `git bundle create --all`,
   `git bundle verify`, SHA-256 checksum, uploaded as a workflow artifact (90-day retention) and attached to a
   weekly `backup-<date>` release (last 8 weekly and every monthly kept permanently).
3. **Off-site copy (owner's choice):** a mirror push to a second private repository, or regular download of the
   release bundle to your PC or cloud drive. Needs one setup step by the owner.

**Restore test:** every backup run clones the bundle into an empty repository, checks that `main`, `staging` and
all branch tips match the remote SHAs, and runs the fast test tier. A failed restore test fails the workflow and
blocks the next cleanup. A restore drill from the release bundle is done monthly and recorded in TASK_LOG.

### 8.2 Automatic branch cleanup (tested before it deletes anything)
The cleanup workflow deletes a branch only if **all** of these hold:
- its tip is an ancestor of `origin/main` (fully merged) and nothing was pushed to it after the merge;
- it is not protected: `main`, `staging`, `relay-channel`, `supervisor-state`, `decisions-tools`, `archive/*`,
  `backup/*`, `codex/*`, or the branch of any task still open in TASK_LOG;
- the latest backup run (8.1) passed its restore test, and a `backup/` tag for that branch tip exists;
- it is named in the cleanup request written by the Supervisor (no wildcard deletion).

Every run first prints a dry-run list. Each deletion records branch name and SHA in `docs/process/CLEANUP_LOG.md`,
so any branch can be restored with `git push origin <sha>:refs/heads/<name>`.

**Testing before it is enabled:**
1. Unit tests of the selection logic on a scratch repository built by the test: merged, unmerged, merged then new
   commit, protected names, `archive/*`, open-task branch, missing backup tag, failed backup run; only the correct
   branches may be selected.
2. End-to-end test on throwaway `cleanup-test/*` branches: create, merge, run cleanup, verify deletion, restore from
   the log and verify the SHA.
3. The first real runs are dry runs reviewed by the Supervisor; real deletion is switched on only after a clean dry run.
These tests run in the gate whenever the cleanup or backup workflow changes.

### 8.3 Always
- No force-push, rebase or history rewrite on shared branches; frozen assets and baselines are never modified;
  tests and thresholds are never weakened. Unmerged work is never deleted (moved to `archive/*` if needed).

## 9. First batch under this plan (after the consolidation)

| Lane | Task | Path | Depends on |
| --- | --- | --- | --- |
| A | T-041 + T-042: integrate.py (incl. `claims --check`), OWNERSHIP.md claims, write-set enforcement, path classification, full all-character regression and unchanged-character guard (§5), durable backups with restore test (§8.1) | A | consolidation in `main` |
| A | T-048: cleanup workflow with its unit and end-to-end tests (§8.2); write-set disjoint from T-041/42 (`.github/workflows/cleanup.yml`, `tools/cleanup/`) | A | backup tags from T-041/42 |
| D | T-038b: boy `hair_mass` bit-determinism (running; needed for §5.2) | A | — |
| B | T-043: spec parts, per-feature generator versions, helpers out of `body_v6` | A | consolidation |
| C | T-040 finish (arm clearance, mesh-fitted capsules), then T-046 facial animation | A, then B | — |
| D | (free until T-043 lands) then T-044 hair v3 | B | T-043 |

Next: T-045 body mechanics (C), T-047 collisions (C), Boy 2.0 look and hoodie (D), girl look round (D), then a short two-character demo scene.

## 10. What the owner needs to do

1. ~~Approve this plan~~ (approved 2026-11-17).
2. In GitHub settings: protect `main` and `staging` (no direct pushes except the Supervisor's fast-forward, required checks green), and protect tags matching `backup/*` from deletion.
3. Choose the off-site backup copy (§8.1 layer 3): a second private repository, or regular download to your drive.
3. Review visual sheets when sent; everything else is handled without you.
