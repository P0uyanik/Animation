# ▶ (Supervisor 2026-11-19 10:05Z) T-115 and T-116 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks for both. Codex stays idle until a new block appears at the top of this file (standing duty: nightly Windows
result).

---
# ▶ T-116 — NEW CODEX ASSIGNMENT, queued behind T-115 (Supervisor 2026-11-19 09:10Z, owner decision ~09:20Z)
**Do not interrupt T-115.** When T-115 is READY, do **T-116: independent review of the current state** (like T-107,
but on what is on main now: boy 2.1.0 / girl 0.12.0 and every round-3 improvement). Task file:
`git show origin/integration/t-116-prep:docs/tasks/T-116.md` (reaches main shortly).

1. Branch `t-116-codex-current-review` from the latest `origin/main` in a new worktree on C: (never write on D:).
   Write only `docs/audit/current_review/**`. Evaluation only.
2. For each of T-107's 5 gaps: fixed / improved / still open, with evidence pairs (reference → ours); new regressions;
   a ranked remaining-gap list with procedural next steps; say which gaps no task covers yet.
3. Fresh stills of the current masters are allowed; state exactly what you rendered and how.
4. Post `| T-116 | STARTED |` when you begin; when done push and post
   `<UTC> | T-116 | READY | t-116-codex-current-review@<sha> | input <sha> | <headline>` + the ledger line.
5. Model: as for T-107.

---
# ▶ (Supervisor 2026-11-19 09:00Z) T-107 ACCEPTED and merging — NEXT: T-115 (block below)
Thanks for T-107. Now do **T-115** as described in the next block. Current versions are boy 2.1.0 / girl 0.12.0
(on main); T-109 is merged, so its parameter names and tried ranges are in
`docs/evaluation/characters/T-109/fit_parameters.json` on main. Branch `t-115-codex-face-fit` from `origin/main`.

---
# ▶ T-115 — NEW CODEX ASSIGNMENT, queued behind T-107 (Supervisor 2026-11-19 03:05Z, owner-approved round 3)
When Codex is back (~09:00 owner time): **first finish T-107** (block below), then do **T-115: fit search on the
face-round-4 parameters**. Task file: `git show origin/integration/t-094b:docs/tasks/T-115.md` (reaches main shortly).

1. Branch `t-115-codex-face-fit` from `origin/main` in a new worktree on C: (never write on D:). Write only
   `docs/evaluation/characters/T-115/**`. Proposals only: no spec, candidate, code or test changes.
2. `tools/fit` with a larger budget than T-090b on the **current** versions (boy 2.1.0, girl 0.12.0 once T-094 makes
   them current; check `docs/evaluation/characters/fidelity_baseline.json`): lower-face fullness (cheek/jaw), eye
   opening, lid profile; use the parameter names on the `t-109-claude-face-r4` branch if it has added them.
3. Post `| T-115 | STARTED |` when you begin; when done push and post
   `<UTC> | T-115 | READY | t-115-codex-face-fit@<sha> | input <sha> | <headline>` + the ledger line.
4. Model: as for T-090.

---
# ▶ T-107 — NEW CODEX ASSIGNMENT (Supervisor 2026-11-18 23:00Z, owner standing approval for tonight)
Codex does **T-107: independent review of round 2 Phases B and C** (like T-083/T-084). Task file:
`git show origin/integration/t-106:docs/tasks/T-107.md` (reaches main shortly).

1. Branch `t-107-codex-bc-review` from `origin/main` in a new worktree on C: (never write on D:). Write only
   `docs/audit/round2_bc_review/**`. Evaluation only: no code, asset, test or workflow changes.
2. Review the Phase B and C evidence named in the task file against the owner's original references; be independent
   and critical; rank what is still off and give concrete procedural next steps; list the 5 most important gaps.
3. Post `| T-107 | STARTED |` now; when done push and post
   `<UTC> | T-107 | READY | t-107-codex-bc-review@<sha> | input <sha> | <headline>` + the ledger line.
4. Model: as for T-084.

---
# ▶ (Supervisor 2026-11-18 22:58Z) T-106 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks. Codex stays idle until a new block appears at the top of this file (standing duty: nightly Windows result).

---
# ▶ T-106 — NEW CODEX ASSIGNMENT (owner-approved 2026-11-18 ~22:50Z, Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **T-106: reference performance extraction**. Task file:
`git show origin/integration/phase-d:docs/tasks/T-106.md` (reaches main shortly).

1. Branch `t-106-codex-perf-extract` from `origin/main` in a new worktree on C: (never write on D:, never touch the
   owner's personal files). Write only `tools/perf_extract/**` and `docs/evaluation/animation/T-106/**`.
2. Offline MediaPipe analysis (Apache-2.0; install dependencies locally to the tool, e.g. a venv under the worktree)
   of `docs/references/video_paperboat.mp4` and `docs/references/video_watertable.mp4`: per character (boy, girl,
   white-haired girl where visible) expression changes, gaze/glance timing, blink rate, head motion, beat durations.
3. Output: a data table (JSON + CSV) and small evidence contact sheets (JPEG <= 2048 px), as calibration targets for
   T-097B/G (acting) and T-104 (timing). No changes to characters, engine or tests outside the write-set.
4. Post `| T-106 | STARTED |` to `RELAY_LOG.md` now. When done, push and post
   `<UTC> | T-106 | READY | t-106-codex-perf-extract@<sha> | input <sha> | <headline>`, ending with
   `ledger: build N · render N · tests N · ci N · wait N (min)`. BLOCKED with the question if stuck.
5. Model: as for T-090.

---
# ▶ (Supervisor 2026-11-18 22:15Z) T-090b ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
Thanks. Codex stays idle until a new block appears at the top of this file (standing duty: nightly Windows result).

---
# ▶ T-090b — NEW CODEX ASSIGNMENT (owner order 2026-11-18 ~20:10Z, Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **T-090b: fit proposals** with the merged T-090 tool. Task file:
`git show origin/integration/t-090b:docs/tasks/T-090b.md` (reaches main shortly).

1. Branch `t-090b-codex-fit-proposals` from `origin/main` in a new worktree on C: (never write on D:, never touch the
   owner's personal files). Write only `docs/evaluation/characters/T-090b/**`. Never edit specs, tools or tests.
2. Run `tools/fit` (Workbench fit renders) and produce **proposals**:
   a. girl face: eye opening, lid profile, cheek profile (input for T-089);
   b. garment outlines: boy inseam / trouser break and shoe volume; girl sleeve reach and shorts (input for T-093).
   Per proposal: override JSON + score table + recipe preview first, then one T-087 strict sheet in Cycles (final only).
3. Post `| T-090b | STARTED |` to `RELAY_LOG.md` now. When done, push and post
   `<UTC> | T-090b | READY | t-090b-codex-fit-proposals@<sha> | input <sha> | <headline>`, ending with
   `ledger: build N · render N · tests N · ci N · wait N (min)`. BLOCKED with the question if stuck.
4. Model: as for T-090.
5. Not for Codex: the time-ledger and preview rules are already done by the Supervisor (docs; `recipe.py preview`
   exists). Standing duty: check the nightly Windows workflow result on main; if it fails, report BLOCKED/STATUS
   with the cause before fixing anything outside an assignment.

---
# ▶ (Supervisor 2026-11-18 19:25Z) T-090 ACCEPTED and merging — NO CODEX ASSIGNMENT NOW
T-090 READY at e0ebdad reviewed and merged (integration/t-090). Thanks. Codex stays idle until a new block appears at
the top of this file. Planned next for Codex: independent reviewer at the end of round 2 Phases B and C.

---
# ▶ T-090 FOLLOW-UP (Supervisor 2026-11-18 16:55Z): strict sheets in Cycles, then READY again
T-090 READY at ccb09b8 reviewed: tool and Workbench evidence accepted. Before merge, add the T-087 strict sheets:
1. On `t-090-codex-fit-optimiser`, run `tools/review/recipe.py sheet` for boy and girl with **Cycles at the recipe
   defaults (16 spp, as in docs/evaluation/process/T-087/)**, columns: reference | 2.0.0 / 0.11.0 approved | fit
   candidate (the proposal overrides). Cheap first frame (`recipe.py preview`) first, as the recipe requires.
2. Check the face rows show the head from hair top to chin (T-087 "fit": "head"); in your Workbench sheet the face
   rows stop at the eyes. If recipe.py crops wrongly, say so in the READY line (do not edit tools/review/).
3. Commit the JPEG sheets (≤ 2048 px) to `docs/evaluation/characters/T-090/{boy,girl}/`, push, then post
   `<UTC> | T-090 | READY | t-090-codex-fit-optimiser@<sha> | input 12559bb | strict sheets added`.

---
# ▶ T-090 — NEW CODEX ASSIGNMENT (owner-ordered 2026-11-18 ~16:20Z, round 2 Supervisor session_01NPjxeNGwvGuevzV1aTjiEo)
Codex does **only T-090: reference-fit optimiser** (round 2 Phase B, B2).

1. `git fetch origin` and read the task file: `git show origin/integration/round2-bc:docs/tasks/T-090.md`
   (it reaches main shortly; the round 2 plan is `docs/process/ROUND2_PLAN.md`, review procedure
   `docs/process/REVIEW_RECIPE.md`).
2. Create branch `t-090-codex-fit-optimiser` from `origin/main` (12559bb or newer) in a new worktree on C:
   (e.g. `C:/AnimationWT/t090-codex`). Never write on D:, never touch the owner's personal files.
3. Write only `tools/fit/**` (incl. `tools/fit/tests/**`) and `docs/evaluation/characters/T-090/**`. Never change
   character specs, published versions, frozen files or tests outside `tools/fit/`. Cheap Workbench renders only
   (Blender 5.3 on the PC); evidence JPEG ≤ 2048 px.
4. Use the model you used for T-084 (Astra).
5. Post `<UTC> | T-090 | STARTED | t-090-codex-fit-optimiser | input <sha> | started` to `RELAY_LOG.md` now. When
   done: push the branch, then `<UTC> | T-090 | READY | t-090-codex-fit-optimiser@<sha> | input <sha> | <headline>`
   (BLOCKED with the question if stuck). Only READY/BLOCKED/STATUS lines reach the Supervisor.

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
