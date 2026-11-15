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

The task history is in `TASK_LOG.md`.
