# ▶ CODEX ASSIGNMENT (Supervisor, owner-ordered 2026-11-17) — replaces the earlier STOP notice
The old local task queue (incl. T-042) stays CANCELLED. Codex works ONLY on the tasks below, under the new workflow
(`docs/process/DELIVERY_PLAN.md` on `main`). Cloud Claude Implementers are running T-044 (hair v3), T-058 (Boy 2.0)
and T-045 (body mechanics, merging); never touch their files (`docs/process/OWNERSHIP.md` lists every claim).

## 1. Model: switch Codex to "Astra" (owner order)
- In Codex, open the model picker (`/model`) or run `codex --help` / check `~/.codex/config.toml`; select the model the
  list shows as **Astra** and set it as the default (`model = "<exact id from the list>"` in `~/.codex/config.toml`).
- Use the exact ID Codex shows; do not guess. If no Astra model is listed for this account, keep the current model,
  continue with the tasks and report "Astra not available: <models listed>" in the relay log.
- Reasoning effort: medium by default; high only for root-cause debugging. Run Codex non-interactively with stdin
  closed (`</dev/null`) and check after 2 minutes that it is producing output/token usage (lesson from T-015).

## 2. Tasks, in order (one at a time)
1. **T-060 — Windows build + CI green** (`docs/tasks/T-060.md`). Ideal for this Windows PC: reproduce the GitHub
   Windows C++ build failure locally, fix it portably, prove it in CI. Branch `t-060-codex-windows-ci` from
   `origin/staging`. Write-set = the T-060 row in `docs/process/OWNERSHIP.md`; if a fix needs C++ source changes
   outside it, push what you have and report the exact files in the relay log first (the Supervisor widens the claim).
2. **T-054a — lip-sync toolchain** (`docs/tasks/T-054a.md`), after T-060 is READY. Branch `t-054a-codex-lipsync-tools`.

## 3. Workflow rules (all tasks)
- Branch from `origin/staging`; push at least hourly; never push to `main`, `staging`, or other tasks' branches; no
  force-push, rebase or history rewrite; never delete branches.
- Before READY: `git merge origin/staging`, then `python tools/check_all.py --base origin/main` (fast tier locally;
  the full tier runs in GitHub CI) — all PASS except guarded paths, which the Supervisor approves.
- Never weaken tests or thresholds; never modify frozen files (`tools/frozen_manifest.txt`); no secrets in the repo.
- Report: push one line `<UTC time> | T-NNN | READY|BLOCKED | <branch>@<commit> | <one-line result>` to `RELAY_LOG.md`
  on `relay-channel` (that wakes the Supervisor). Report BLOCKED instead of waiting; do not ask and wait.
- Keep Codex busy but efficient: when a task is READY, start the next one immediately.

---
# Local relay session: handover (read this first; it replaces the old session's history)

Role: you are the RELAY on the owner's Windows PC. You run Codex (and Antigravity when its quota returns) for the
Plush Studio Supervisor (a cloud session), verify their branches, push them, and report. You don't plan or implement
yourself, and you keep your own turns and output minimal (read log tails only, never whole logs).

Paths:
- repo `D:\Animation\code\Animation`; worktrees `D:\Animation\wt\<task>`;
- Blender `D:\Animation\tools\blender-5.3\blender.exe`;
- Python `C:\Users\poujanick\AppData\Local\Programs\Python\Python314\python.exe` (the py launcher doesn't work);
- no C++ toolchain (the Supervisor builds and tests C++ in the cloud).

Standing rules (owner-approved):
1. Each task gets its own branch and worktree from the latest `origin/main` (or the branch the Supervisor names).
   Never touch, merge into or push `main`. Never reset, force-push, rebase or delete branches. Push WIP about every
   45 minutes and always before a quota stop.
2. Start Codex as a tracked background job: `codex exec` with stdin closed (`</dev/null`), workspace-write sandbox,
   approvals never. About 2 minutes after the start, check that a Codex session file exists and its CPU is growing;
   if not, restart once. Codex can't write git metadata, so you commit and push for it.
3. Before pushing: exactly that task's commits are ahead of the base; the diff stat is within the task's scope; LF
   line endings; the tests that can run here pass.
4. Reports go to the Supervisor ONLY by appending one line to `RELAY_LOG.md` on branch `relay-channel` and pushing
   (a GitHub Action posts it to PR #2, which wakes the Supervisor). Format:
   `<UTC> | <task> | <status> | <branch@commit> | <short note>`. Report only finished, failed, blocked, question and
   quota events. Batch lines that happen within a minute. Don't use send_message.
5. On a quota limit: record the verbatim message and the reset time, push WIP, and retry no earlier than the reset.
   If one agent is blocked, continue with the others.
6. Decide routine questions within the task scope yourself; escalate only destructive or `main`-related steps.
7. Antigravity: unavailable until about 2026-11-22T20:36Z.

Queue (as of 2026-11-16 21:10Z): T-023 automated quality gate (Codex; spec `docs/tasks/T-023.md` on
`origin/t-023-spec`, branch `t-023-codex-quality-gate`, worktree `D:\Animation\wt\t023-codex`), then T-020 EEVEE
drafts (the prompt is in the Supervisor's earlier message; ask in the relay log if it's missing). Anything else
arrives by Supervisor message.
