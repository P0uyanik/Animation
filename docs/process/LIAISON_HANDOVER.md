# Owner-liaison handover (2026-11-20 ~08:30Z)

From the old liaison `session_01NPjxeNTmHt2DtBN8F8uLqB` (rotated because its ~760k context made every turn expensive;
T-152/T-162) to the new liaison session. Pointers instead of copies. The authoritative state is in the repo files named
below. Read them on demand, not all at once.

## 1. Roles and how work flows
- **Owner**: one person. Approves visuals, versions and scope. Writes in short English, sometimes with typos. Times
  are given in German time (CET = UTC+1).
- **Liaison (you)**: talk to the owner. Relay decisions to the Supervisor with `send_message`. Show results (sheets
  and clips) to the owner. Do not run implementation work yourself.
  - Exception: short read-only analyses via a subagent, e.g. T-162.
- **Round-3 Supervisor**: `session_01NPjxeL81bNYoFDm9Ypv5Ck` (Opus 5.5, Animation environment). It owns:
  - task files, claims, dispatching implementers (cap **6** sessions), reviews, trial merges, CI, merges and archiving;
  - `docs/process/STATUS.md`, the **single status board**: lanes, running, queued, waiting for owner;
  - `docs/process/OWNER_DECISIONS.md`: it records every decision you relay.
  - Rotate the Supervisor too when its context grows large (>~300k); see SUPERVISOR_HANDOVER_R3.md for the pattern.
- **Implementers**: fresh Claude session per task. Routing:
  - Opus 5.5 by default;
  - Fable 5.2 (`claude-fable-5-2`) for hard visual tasks (hair, faces, garments, motion craft);
  - Sonnet 5.5 for aggregation and mechanical work.
  - Environment `env_01MTWJVTWBHG13yZcRS4DzCz` "Animation" (setup script preinstalls bpy 5.3, C++ deps, `blender`
    shim).
- **Codex** (OpenAI agent on the owner's PC) does evaluations via branch `relay-channel`:
  - assignments go ONLY at the top of `NEXT_TASK.md`; replies are `| T-NNN | STARTED/READY |` lines in
    `RELAY_LOG.md`;
  - it writes only to its own write-set (docs);
  - **it hit its weekly limit and is unavailable until ~2026-11-23 21:43Z**; T-161 is queued for then;
  - the PC may sleep, and the relay resumes by itself. Never block cloud work on Codex.
- Repo `P0uyanik/Animation`; main = staging (fast-forward); gate `tools/check_all.py` plus sharded CI (~17 min).

## 2. Owner's standing rules (binding)
- Visual fidelity to the owner's original references beats scores. Characters stay procedural and code-driven.
- **No character version becomes CURRENT without the owner's explicit OK.** New work ships as opt-in or as candidates
  with strict sheets (reference | current | candidate | target).
- Never weaken, skip or remove tests, thresholds or goldens.
  - Owner-approved exceptions: T-142 legacy-only tests; the T-154 named-candidate allowlist.
- Never modify frozen or published assets. No force-push or history rewrite. Never delete branches. Archive instead of
  delete. Every change must be revertible.
- No secrets in chat or the repo; the owner's email is private. Commit trailers:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` + `Claude-Session: <your session URL>`. No model IDs in
  commits.
- No PRs unless asked. When the owner only asks a question, answer it; don't assign work.
- Destructive or architectural steps (e.g. A1/A3 removals): a plan or report first, then removal.
- **Token rules**:
  - concise messages; one-line READY;
  - pointer-based briefs;
  - no FYI messages; don't wake idle sessions;
  - batch merges per lane;
  - rework in a fresh session when context >~250k (T-162).
- Don't pause unrelated work while waiting for owner feedback. Resolve real blockers first. Use parallel slots, but
  keep the lanes tidy.
- Archive sessions once their work is merged and nothing is pending (never with unmerged work or open questions).
- No GPU rental (evaluations first). Environment development is deferred. Lip sync is out of scope. The 8 s shot
  rebuild (S1a/S1b/S1c) is postponed.

## 3. Current state (see STATUS.md for live detail)
- **Versions**:
  - owner approved ~08:20Z: boy **2.3.0**, girl **0.14.0** become CURRENT. The switch is running in T-155 with a full
    gate; confirm it landed.
  - Third character `girl_white_hair_blue_dress` **0.1.0** is published as her first version.
  - Previous current: 2.2.0 / 0.13.0.
- **Decided today** (all in OWNER_DECISIONS.md, 2026-11-20):
  - T-137 faces approved;
  - guard-test allowlist (option a);
  - T-157 wider contact band stays OPT-IN until hands round 2 is verified;
  - **`final720` is the default final render** (old preset kept by name); **HEVC 10-bit is the default delivery**,
    with H.264 as fallback; the change is being implemented;
  - fidelity score v2 stays experimental (validate on unseen examples later, Codex);
  - T-144 = option B, after T-158;
  - T-162 items 1, 3, 4, 5 adopted (PR #2 comment scope; `tools/ready.py`; rework rule; shared task kit);
  - S1a/b/c postponed; T-141b not approved (to discuss).
- **Running** (lanes):
  - Character look: T-156 lashes first, then eye shape to the T-150 targets (Fable); T-160 hair round 6, base groom,
    all three (Fable); T-158 deterministic builds (Opus).
  - Release: T-155 (switch, see above).
  - Interaction: T-157 done (opt-in).
  - Workflow: T-164 PR #2 comment scope; T-165 task kit + ready.py; final720/HEVC defaults task.
  - Other: T-163 starter prop library (review), T-141 hair-curves experiment (opt-in tool, review).
- **Queued**, auto-start by condition:
  1. ears round T-159 (after T-158);
  2. hands round 2: boy finger separation, pre-shaping during the reach, finger-by-finger close, soft contact (after
     T-155 published);
  3. T-144 option B (after T-158; comparison report to the owner BEFORE any removal);
  4. next versions with lashes, hair round 6 and ears (after the owner approves those results).
- **Later / to discuss** (not approved):
  - T-141b hair curves production-ready (bake binding, cull hidden strands, tone down flyaways, motion test);
  - S1a/b/c shot rebuild;
  - fidelity v2 validation;
  - walking polish;
  - third-character expression set;
  - first 30–60 s story scene (needs the owner's story idea);
  - GPU test (if the owner's PC has an NVIDIA GPU, Codex could benchmark locally; owner not yet answered);
  - T-162 "trim fixed prefix" and "shared before-renders" (the latter only after T-158, and needs approval; the owner
    declined build caching earlier).

## 4. Known issues
- Scheduled triggers: the permission classifier denied `create_trigger` / `send_later` for the Supervisor, so there
  are no autonomous hourly check-ins. The owner said to fix this separately later. If work stalls (5-hour usage
  limit), resume sessions with one-line "continue" messages.
- The old liaison could not receive messages (trusted-device restriction). Check whether the Supervisor can reach
  you; if not, poll STATUS.md and list_sessions when the owner asks.
- Usage windows: shared 5-hour window (all Claude sessions); weekly window resets Sat 00:00Z.

## 5. Key documents
- `docs/process/STATUS.md`, `OWNER_DECISIONS.md`, `TASK_LOG.md`, `SUPERVISOR_HANDOVER_R3.md`,
  `MORNING_SUMMARY_2026-11-20.md`, `IMPLEMENTER_PROMPT.md`.
- Efficiency:
  - `docs/process/WORKFLOW_EFFICIENCY_R5.md` (T-162);
  - `docs/audit/token_efficiency/REPORT.md` (T-152);
  - `docs/process/WORKFLOW_EVAL_R4.md`.
- Targets and evidence:
  - `docs/evaluation/characters/T-150/targets.json` (eyes);
  - T-155 sheets;
  - `docs/evaluation/rendering/T-124/` (render and encoding study).
- Audits: `docs/audit/` (project audits, legacy_engine_deps, current_review, round4_review).

## 6. How-to
- **Show sheets**: `git fetch origin <branch>`, then `git show origin/<branch>:<path> > <scratchpad file>`, view it
  yourself, send it with SendUserFile, and summarise what changed and what's still off.
- **Relay a decision**: one concise `send_message` to the Supervisor. Start with "OWNER DECISION <time>", quote the
  owner where it matters, and list the actions and constraints.
- **Codex task**: prepend a block to `NEXT_TASK.md` on `relay-channel` (fetch first; commit with trailers; push) and
  tell the Supervisor.
- **Status**: read STATUS.md first; then `list_sessions`, recent `git log origin/main`, and the RELAY_LOG tail.
