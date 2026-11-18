# ▶ ROUND 2 (2026-11-18, new Supervisor session_01NPjxeNGwvGuevzV1aTjiEo): NO CODEX ASSIGNMENT RIGHT NOW
T-084 is DONE and merged. Codex stays idle until a new block appears at the top of this file. Planned: independent
reviewer at the end of round 2 Phases B and C. Report lines (`| T-NNN | READY/BLOCKED/STATUS |`) still go to
`RELAY_LOG.md`; only READY, BLOCKED and STATUS lines are posted to PR #2 now.

---
# ▶ T-084 — NEW CODEX ASSIGNMENT (owner-ordered 2026-11-18, Supervisor): independent PROJECT AUDIT
Everything above T-060/T-054a below is DONE (T-060 merged). Codex now does **only T-084**:

1. `git fetch origin` and read the task file: `git show origin/supervisor/t-084-task:docs/tasks/T-084.md`
   (raw usage data: `git show origin/supervisor/t-084-task:docs/audit/data/agent_sessions_2026-11-18.md`).
2. Create branch `t-084-codex-project-audit` from `origin/main` (0388efb or newer) in a new worktree on C:
   (e.g. `C:/AnimationWT/t084-codex`). Never write on D:, never touch the owner's personal files.
3. Evaluation only: no code, asset, test or workflow changes. Write only `docs/audit/CODEX_PROJECT_AUDIT.md` and
   `docs/audit/codex/**`. Be independent and critical; do not read any `supervisor/audit*` branch.
4. Use the model you used for T-083 (Astra), reasoning high for this task.
5. When done: push the branch, then append to `RELAY_LOG.md` on `relay-channel`:
   `<UTC> | T-084 | READY | t-084-codex-project-audit@<sha> | <one-line headline>`.
   Post a `| T-084 | STARTED |` line first, now.

---
# ▶ T-060 UNBLOCKED — owner approved option B (2026-11-17, Supervisor)
The owner approves installing the C++ Build Tools on this PC **and accepting their licences** for T-060. Do it now,
then continue T-060; T-054a continues in parallel only if it doesn't slow the install/build.

1. **Install on C: only** (C: has space; never install to or write on D:). Use winget, non-interactive:
   - `winget install --id Microsoft.VisualStudio.2022.BuildTools -e --accept-package-agreements --accept-source-agreements --override "--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`
   - `winget install --id Kitware.CMake -e --accept-package-agreements --accept-source-agreements` (skip if `cmake --version` works)
   - `winget install --id Ninja-build.Ninja -e --accept-package-agreements --accept-source-agreements` (if CI uses Ninja)
   - vcpkg: `git clone https://github.com/microsoft/vcpkg C:\vcpkg` and `C:\vcpkg\bootstrap-vcpkg.bat -disableMetrics`;
     set `VCPKG_ROOT=C:\vcpkg` for the build; put the vcpkg binary cache on C: (`VCPKG_DEFAULT_BINARY_CACHE=C:\vcpkg-cache`).
   - Pinned OIDN as `.github/ci-dependencies.json` / `.github/scripts/install_ci_dependencies.ps1` specify, under C:.
   Match versions to the CI Windows job where they are pinned. If an installer asks for elevation (UAC) or a reboot and
   cannot proceed unattended, report BLOCKED with the exact prompt — that is the only thing to ask the owner.
2. **Do not delete, move or modify any of the owner's personal files** (D:\Users etc.). The owner frees space on D:
   personally. Keep all T-060 work (worktree, build dirs, caches) on C:.
3. Then follow `docs/tasks/T-060.md`: reproduce the Windows build, fix portably, local fast tier on Windows, prove the
   GitHub windows job green, report READY via the relay line. Use `gpt-6.2-astra` as before.

---
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
# Next task

0. **Working structure (2026-11-15):** Supervisor/Implementer workflow in `docs/process/` (owner-approved). Pending: GitHub push access to the project repository, then the Implementer chat setup. No development task is selected yet.
1. **Owner review of M3.2:**
   - `docs/PRODUCTION_PIPELINE.md`;
   - `docs/evaluation/production/M32_s010_contact_sheet.jpg` and `M32_s010_shot.mp4`.
2. **T-001 (Studio ↔ shot pipeline): accepted by the owner on 2026-11-15** (branch `t-001-studio-shot-pipeline`).
   - Report: `docs/milestones/2026-11-15_T-001_studio_shot_pipeline.md`.
   - `ctest` is 4/4 with OIDN 2.3.3 (a build dependency outside the repository, `-DPLUSH_OIDN_ROOT`).
3. **T-002 (clip foundation): delivered on branch `t-002-clip-foundation`; awaiting Supervisor and owner review.**
   - Report: `docs/milestones/2026-11-15_T-002_clip_foundation.md`;
   - format and usage: `docs/ANIMATION_CLIPS.md`;
   - evidence: `docs/evaluation/animation/T-002/` (contact sheet, measurements).
3a. **T-003 (body emotions): delivered on branch `t-003-body-emotions`; awaiting Supervisor and owner review.**
   - Report: `docs/milestones/2026-11-15_T-003_body_emotions.md`; format and library: `docs/EMOTIONS.md`;
   - evidence: `docs/evaluation/animation/T-003/` (contact sheet, face comparisons with #34 / #28, measurements);
   - open question: eyes render closed when the head pitches down (render/master side).
4. **Then:**
   - the girl's hair and garments (M4/M5) on the shared path, judged in final Blender renders;
   - acting-quality clips towards the reference videos (Blender-authored or licensed motion capture through the
     same format); the `idle_relaxed` base clip already replaces the A-pose arms in shots that use it;
   - an episode layer (shot sequence, audio).
5. **Still pending your review:**
   - M3 / M3.1;
   - the boy's F09 / H28 candidates.
