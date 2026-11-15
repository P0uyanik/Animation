# Orchestration state (Supervisor checkpoint; update on every status change)

Integration base: origin/main (after T-003 merge, see git log). Local relay: Claude Code session on owner PC, repository
`D:\Animation\code\Animation`, worktrees `D:\Animation\wt\`. Pushes and merges into main need owner approval.

| Task | Agent | Branch | Worktree | Commit | Status | Depends |
| --- | --- | --- | --- | --- | --- | --- |
| T-003 body emotions | Claude Impl | t-003-body-emotions | cloud | 9f9f1f7 | merged into main e8fd5d5 | - |
| T-004 clip file test | Codex | t-004-codex-clip-check (local only) | wt\t004-codex | 687362b | done; Supervisor review pending | - |
| T-005 doc link checker | agy | t-005-agy-doc-links (local only) | wt\t005-agy | 0c2f178 | done; Supervisor review pending | - |
| T-006 gaze range limit | Codex | t-006-codex-gaze-limit | wt\t006-codex | - | dispatched | (fixes T-003 eye issue) |
| T-007 mocap licences | agy | t-007-agy-mocap-licences | wt\t007-agy | - | dispatched | input for mocap converter |

Queue (not dispatched): ANIMATION_CLIPS.md section-8 formula reconciliation (Codex, after T-006); mocap converter
(after T-007 + reconciliation; owner-approved licence architecture); A2 test video (after T-003 acceptance).
Quota: no provider limit messages so far. Agents: Codex model reported gpt-5.6-sol; agy model not reported.
