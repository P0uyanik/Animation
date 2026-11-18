# Implementation plan and queue (Supervisor working plan, round 2, 2026-11-18)

The approved plan is `docs/process/ROUND2_PLAN.md` (phases A → B/C → D). Decisions: `docs/process/OWNER_DECISIONS.md`.
Status per task: `docs/process/TASK_LOG.md`. Claims: `docs/process/OWNERSHIP.md`. This file only records what runs
now and what starts next; it does not restate the plan.

## 0. Rules
- Start only tasks in the approved plan. At most 6 in parallel, disjoint file claims (`OWNERSHIP.md`).
- Path B (visual): the owner approves T-087 strict sheets before merge; approved versions change only by owner
  approval (via the T-088 version-switch script once merged).
- Codex (owner's PC): assignments only at the top of `NEXT_TASK.md` on `relay-channel`. Currently none; planned as
  independent reviewer at the end of Phases B and C.
- Task files use `docs/tasks/_TEMPLATE.md`: the write-set lists every file a solution may touch.

## 1. Running now (Phase A)
| Task | What | Implementer | Merges after |
| --- | --- | --- | --- |
| T-085 | Renderer optional in the build | cloud `session_01NPjxePZB1du3ZStJN4c7EC` | READY + full CI on `integration/t-085` |
| T-087 | Review recipe lock + fidelity fixes | cloud `session_01NPjxeLy8LE79Ttrgoxqp6S` | READY + full CI |
| T-088 | Version-switch script | cloud `session_01NPjxeLdCn1De2R4uRrMMYo` | READY + full CI |

## 2. Next
1. T-086 CI efficiency: starts when T-085 is merged (shared `checks.yml`).
2. Phase A exit: T-085..T-088 merged, all workflows on `main` green.
3. Phases B and C (max 6 parallel): T-089, T-092, T-093, T-095, T-096, T-098L; T-090 as the 7th slot frees up or
   after T-089's first face fit is reviewed. Task files written from `ROUND2_PLAN.md` before start.
4. Phase D (T-091, T-097, T-094): only after the owner approves Phase B's visual quality.

## 3. Out of scope (until the owner reopens it)
T-100 third character, T-051 fingers, T-101 old failing tests, T-102 hygiene, T-103 perceptual metric, full T-098
environment, T-099 prop hand-off, T-074 full render budget study. Older queue items (T-054b, T-073) are ideas only.
