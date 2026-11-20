# Development workflow: Supervisor and Implementer (approved by the owner, 2026-11-15)

**Roles:**
- **Owner:** decides direction; approves every task prompt and accepts every result.
- **Supervisor chat:** the owner's only point of contact. Plans, writes and reviews task prompts, and checks the
  Implementer's work against the repository, the architecture and the visual references. Implements nothing.
- **Implementer chat:** executes exactly one approved task at a time, then reports and stops. Its standing
  instructions are in `IMPLEMENTER_PROMPT.md`.

## Per-task workflow
1. The Supervisor identifies the next task.
2. The Supervisor explains its understanding: what, why, which systems, expected outcome, what stays unchanged, and
   how it is tested. The owner confirms.
3. The Supervisor writes the full implementation prompt (`T-<nnn>`).
4. The owner reviews the prompt and gives explicit approval.
5. The owner pastes the approved prompt into the Implementer chat.
6. The owner brings the Implementer's report back. The Supervisor verifies it against the commits (not only the
   report) and requests corrections through a new approved prompt if needed.
7. The Supervisor presents the result (implemented / tested / not tested / incomplete / meets requirements). The
   owner accepts or rejects it.

## States, never mixed
- **discussed:** an idea was talked about. Nothing is approved.
- **prompt approved:** the owner approved the exact prompt text.
- **result accepted:** the owner accepted the delivered work.

A question or a discussion is never an approval.

## Rules carried over
- One agent per chat, no subagents.
- Reuse first; avoid unnecessary scans, tests and renders.
- Shared systems separate from character data.
- Frozen assets untouched; nothing published or approved without the owner.
- The visual references are the target.
- No session subscribes to PR #2 (owner 2026-11-20 ~08:10Z): wait on your own CI run with one background
  `gh run watch <id>` (or `tools/wait_gate.py` once the T-165 kit lands); the gate's checks are unchanged.
- Rework rule (owner ~08:10Z): if an implementer's context is over ~250k tokens and the feedback is narrow, do the
  rework in a fresh session with a pointer brief (task file, review points, branch@sha, README) or after compaction.
  One consolidated feedback message per review round.

## Work areas, conflicts and integration
1. Before dispatch, the Supervisor compares the planned file lists. Parallel tasks never share files. Central files
   (`presets.json`, `build_character.py` and character specs) belong to one active task at a time.
2. For textual and hidden conflicts, the agent that owns the branch merges `main` into its branch (never rebases and
   never force-pushes), runs `python tools/check_all.py` and pushes the result. The CI trial-merge report triggers
   this work. For content conflicts, the Supervisor decides the resolution in one line. Product questions go to the
   owner.
3. Only the Supervisor merges into `main`, only from a CI-green integration commit, and only with owner approval;
   approved changes may be batched. CI never merges or writes to a branch.
4. Work is never lost: do not rebase, force-push or delete work branches. Work in progress is always committed and
   pushed.

`tools/check_all.py` is the common local and CI entry point. A guarded path is accepted only when a commit on the
branch has the exact trailer `Supervisor-Approved: <path>`, added by the Supervisor. The Supervisor applies GitHub
rulesets separately.

The optional Blender tier also runs character fidelity when a character spec or references/annotations change, or
when a shared body, face, groom, garment, material, geometry/build, or render-calibration generator changes. It runs
`tools/fidelity/run.py` for every affected character, puts score and signed main-baseline delta on the Blender line
of the at-most-ten-line summary, and uploads the side-by-side sheets. A score drop greater than 2.0 points fails as
`visual regression, needs owner review`; an increase is informational. The main baseline is
`docs/evaluation/characters/fidelity_baseline.json` and may change only in an explicit commit with the exact trailer
`Supervisor-Approved: docs/evaluation/characters/fidelity_baseline.json`. See `docs/CHARACTER_FIDELITY.md` for the
trigger list, artifacts, and interpretation.

The relay creates its rotating verified local backup with:

```powershell
python tools/backup_repository.py --destination D:\Animation\backups --keep 7 --restore-test
```

The task history is in `TASK_LOG.md`.
