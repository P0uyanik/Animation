# Delivery plan: managing tasks, merges and plans (proposal, 2026-11-17)

Status: **draft for owner approval**. Once approved it replaces the per-task part of `WORKFLOW.md`.
Goal: every finished, verified task reaches `main` quickly, without a pile-up of open merge requests and without merge conflicts, and the task status is always current.

---

## 1. Principles

1. **No waiting merge requests.** A task is either *in progress*, *ready* (waiting at most one Supervisor cycle), or *merged*. Nothing sits "open" for days.
2. **Conflicts are prevented, not resolved.** Parallel tasks never write the same files (lanes, §3). Every task finishes on top of the latest `staging`.
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

## 3. Lanes: how conflicts are avoided

Every task belongs to exactly one lane. **At most one running task per lane**, so two Implementers never edit the same files.

| Lane | Owns (write-set) | Typical tasks |
| --- | --- | --- |
| **A: Tools / CI / process** | `tools/`, `.github/`, `docs/process/` (except TASK_LOG/ROADMAP) | gate, integrate.py, regression, cleanup workflow |
| **B: Character system** | `pipeline/charsys/`, character specs, `body_generic` | T-043 spec parts, Boy 2.0 body |
| **C: Engine / animation** | `engine/`, `content/clips`, `content/emotions` | T-046 facial animation, T-045 body mechanics, T-040 clearance |
| **D: Look / assets** | `face_generic`, `groom`, `garment`, materials, `render_calibration.json` | T-044 hair v3, hoodie, girl look round |

Rules:
- The task file lists its **write-set** (folders/files). The Supervisor checks it against running tasks before assigning (`docs/process/OWNERSHIP.md`).
- A task that must touch another lane's files is split: the cross-lane part becomes a small prerequisite task in that lane, merged first.
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
3. Gate on the trial merge: fast tier always; Blender tier + all-character regression + fidelity whenever `pipeline/`, specs, materials or look files changed. Fidelity drop > 2 points on **any** character = FAIL.
4. Visual check: renders vs reference images for every affected character.
5. Pass → `integrate.py stage` (merge `--no-ff`, push `staging`), update TASK_LOG, archive the session.
6. Promote:
   - **Path A (technical, no visual change):** fast-forward `main` to `staging` immediately (standing approval).
   - **Path B (visual change):** send the owner a compact review sheet (before/after vs reference). On approval, promote.
7. Fail → task goes to *rework* with a precise list; a fresh session continues from the pushed branch. After 2 failed rounds the Supervisor re-designs the task instead of iterating (lesson from T-040).

### Keeping path B from blocking path A
Visual changes are **opt-in by version**: a new look ships as a new generator/spec version that no approved character uses yet. That makes it safe to stage and promote as technical work. The owner's approval is then a tiny follow-up change: "girl spec pins hair v3". So `staging` never holds unapproved visible changes, and `main` can always be promoted.

## 6. Planning cadence

- **Roadmap** (`docs/ROADMAP.md`): phases and order, changed only with owner approval.
- **Queue**: the next 2–3 tasks per lane are written as task files in advance, so a free lane is filled immediately and Implementers never idle.
- **Parallelism**: up to 4 Implementers (one per lane), within the Max 5x budget. A lane with nothing ready stays empty rather than starting a task that would conflict.
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

## 8. Safety

- Before every promote to `main` and before any branch cleanup: a `git bundle` backup, verified with `git bundle verify`.
- Merged branches are deleted only by the cleanup workflow, only after the merge is in `main` and checks pass. Unmerged work is never deleted (moved to `archive/*` if needed).
- No force-push, rebase or history rewrite on shared branches; frozen assets and baselines are never modified; tests and thresholds are never weakened.

## 9. First batch under this plan (after the consolidation)

| Lane | Task | Path | Depends on |
| --- | --- | --- | --- |
| A | T-041 + T-042: integrate.py, OWNERSHIP.md, gate polish, all-character visual regression in CI, cleanup workflow | A | consolidation in `main` |
| B | T-043: spec parts, per-feature generator versions, helpers out of `body_v6` | A | consolidation |
| C | T-040 finish (arm clearance, mesh-fitted capsules), then T-046 facial animation | A, then B | — |
| D | (free until T-043 lands) then T-044 hair v3 | B | T-043 |

Next: T-045 body mechanics (C), T-047 collisions (C), Boy 2.0 look and hoodie (D), girl look round (D), then a short two-character demo scene.

## 10. What the owner needs to do

1. Approve this plan (or tell me what to change).
2. In GitHub settings: protect `main` and `staging` (no direct pushes except the Supervisor's fast-forward, required checks green).
3. Review visual sheets when sent; everything else is handled without you.
