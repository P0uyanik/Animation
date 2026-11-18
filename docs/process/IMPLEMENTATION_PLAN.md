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

## 1. Running now (Phases B and C, started 2026-11-18 16:33Z on the owner's OK; Phase A merged)
| Task | What | Implementer |
| --- | --- | --- |
| T-089 | Face and eyes round 3 (felt-eye mode) | cloud `session_01NPjxeKcdki5txX1RmMHzfK` |
| T-090 | Reference-fit optimiser | Codex (owner's PC, `NEXT_TASK.md`) |
| T-092 | Materials round 2 | cloud `session_01NPjxeMpD6F8ufQRUAj7USK` |
| T-093 | Garments and accessories | cloud `session_01NPjxeKE4CbSHUrHeuTF8mL` |
| T-095 | Two-person exchange | cloud `session_01NPjxeLCrJJXDARJ14smDu3` |
| T-096 | Clearance and visible grip | cloud `session_01NPjxeKWVBHRxiSkeK5hvaE` |

## 2. Next
1. Phase A merged: T-085, T-086, T-087, T-088. Follow-up noted: `.github/scripts/select_base.sh` compares staging with origin/main (fallback full run on staging can drop to fast when main is pushed first).
2. Phase A exit: T-085..T-088 merged, all workflows on `main` green.
3. T-098L after T-095's blocking pass. Before T-094: extend `tools/version_switch.py` `preset_family()` for presets/3; flip `face_generic/3` and `garment/2` to declared=True when their modules merge.
4. Phase D (T-091, T-097, T-094): only after the owner approves Phase B's visual quality.

## 3. Out of scope (until the owner reopens it)
T-100 third character, T-051 fingers, T-101 old failing tests, T-102 hygiene, T-103 perceptual metric, full T-098
environment, T-099 prop hand-off, T-074 full render budget study. Older queue items (T-054b, T-073) are ideas only.
