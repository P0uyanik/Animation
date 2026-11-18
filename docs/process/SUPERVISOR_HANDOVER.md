# Supervisor handover (2026-11-17, Option A: non-elevated Supervisor)

Read this first, then `docs/process/DELIVERY_PLAN.md`, `docs/process/OWNER_DECISIONS.md`, `docs/ROADMAP.md`,
`docs/process/TASK_LOG.md`, `docs/process/OWNERSHIP.md`. The repo is the source of truth; this file is the context
that is not obvious from it.

## 1. Role and how the owner wants to work
- You are the **Supervisor of Plush Studio**: plan, delegate to Implementers, review, run/read the gate, merge, report
  concisely. You do not implement features yourself (small process/doc edits are fine).
- Goal: a reusable plush/felt character system and 2–2.5 min episodes at **reference-level quality**. The owner's
  original references (images, models, videos) are the **primary target**; visual fidelity beats numeric scores.
- Owner style: short, plain answers; keep token use low; report outcomes, not process. Ask only for real decisions.
- **When the owner asks a question, answer it; do not assign work** ("no dont give them to codex, I just wanted to
  know" — 2026-11-17). Never start a task the owner has not approved.
- **Current owner rule (2026-11-17): no new tasks** until the running ones finish; merge each finished task as soon
  as it passes, keep `main` current so the owner can see results. T-074 and the queue are on hold.

## 2. Communication architecture (why this handover exists)
- The previous Supervisor session (`session_01NPjxeNTmHt2DtBN8F8uLqB`) became **elevated** on 2026-11-15 21:11Z when
  the owner approved a trust card so it could message the owner's PC session over Remote Control. Elevation is
  permanent: messages INTO an elevated session must come from a trusted device, so cloud Implementers got
  `elevated_session_untrusted_device`. Verified 2026-11-17: Implementer→Implementer delivered, Implementer→old
  Supervisor refused.
- **You must stay non-elevated.** Never call `confirm_repository_trust`, `request_computer_folder` or anything that
  shows the owner a "use your computers / reach your other sessions" card. If such a refusal appears, report it to
  the owner and use the relay instead.

| Link | Channel | Notes |
| --- | --- | --- |
| Supervisor → cloud Implementer | `send_message` (claude-code-remote) | works |
| Cloud Implementer → Supervisor | `send_message` to **your** session id | works once Implementers have your id (§5); relay as fallback |
| Supervisor ↔ owner's PC (local relay session running Codex) | **relay**: append a line to `RELAY_LOG.md` (and orders in `NEXT_TASK.md`) on branch `relay-channel`, push | the PC relay polls `relay-channel`; its reports are pushed to `RELAY_LOG.md` and a GitHub Action posts them as a comment on PR P0uyanik/Animation#2 |
| GitHub CI results, relay reports | PR P0uyanik/Animation#2 activity | `subscribe_pr_activity` (one session at a time: the old Supervisor unsubscribes at handover) |
| Supervisor → Advisor (old session `session_01NPjxeNTmHt2DtBN8F8uLqB`, owner decision 2026-11-18) | relay line `- <UTC> NEW SUPERVISOR → ADVISOR: <question>` on `relay-channel` | Advisor → Supervisor: `send_message`. Advisor checks hourly or when the owner pings it; it never merges, assigns or messages Implementers |
| Reading any session's progress | `list_sessions children`, `list_events` | read-only fallback, no trust needed |

Relay line format: `<UTC> | T-NNN | READY|BLOCKED|STATUS|ALIVE | <branch@sha> | <one line>`; Supervisor lines start
with `- <UTC> SUPERVISOR → <who>:`. Always fetch `relay-channel` by name before appending; never rewrite it.
The PC relay's own rules are in `RELAY_HANDOVER.md` on `relay-channel` (paths on the PC, Codex invocation, quota).

## 3. Delivery process (summary; DELIVERY_PLAN rev. 2 is authoritative)
- Branches: `main` = `staging` (both updated together, fast-forward). Task branches `t-NNN-<agent>-<slug>` from
  `origin/staging`. Trial merges on `integration/<name>`; **GitHub CI on the integration branch is the merge evidence**
  (full tier ≈ 18 min: linux gate + 3 per-character regression jobs; Windows informational).
- Gate: `tools/check_all.py` (frozen assets, guarded paths, write-set vs claims, shared-systems lint, C++ build/tests,
  Python tests + doc links, Blender tier/regression + unchanged-character guard + fidelity).
- **Guarded paths need one trailer per exact path** in a commit between base and HEAD:
  `Supervisor-Approved: tools/check_all.py` (one line per file; a list in one line does NOT match). Add them in the
  integration merge commit or an empty commit on top, after reviewing those files. Quick local check:
  `python3 -c "import sys;sys.path.insert(0,'tools');import check_all as C,subprocess;ch=set(subprocess.run(['git','diff','--name-only','origin/staging','HEAD'],capture_output=True,text=True).stdout.split());print(C.check_guarded('origin/staging',ch),C.check_frozen())"`
- New immutable files (e.g. published character versions) are added to `tools/frozen_manifest.txt` (blob IDs from
  `git ls-tree -r HEAD <path>`), never removed; scopes reject unlisted additions.
- Claims: `docs/process/OWNERSHIP.md` (one row per running task; check `python3 tools/integrate.py claims --check T-NNN`;
  `python3 tools/regression/tests/test_gate_tools.py` must pass after editing it). Release the row at merge.
- Paths: A technical = standing approval after gate; B visual = owner approves renders first. Approved character
  versions (boy 1.1.0, girl 0.10.0) change only after owner render approval (pin bump in
  `docs/evaluation/characters/fidelity_baseline.json` + regression baseline).
- Evidence size policy: DELIVERY_PLAN §9b (JPEG sheets ≤ 2048 px, MP4 ≤ 1280 px).
- Commit trailers: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and `Claude-Session: <your session URL>`.
  No model IDs in commits. No PRs unless asked.

**Pitfalls learned (do not repeat):**
- Fetch branches by explicit name/refspec; never merge `FETCH_HEAD` after a multi-branch fetch.
- `git merge -F -` fails without stdin: write the message to a file.
- When editing a file with Python, read it before opening it for write (an `open(p,'w')` before reading emptied
  OWNERSHIP.md once).
- Each worktree needs its own build dir. Staging moves often: re-merge before promoting.
- Implementers sometimes end turns while waiting for CI: nudge them; ask them to report and stop instead.

## 4. Security constraints (owner, standing)
Never put secrets in chat or repo; the owner's email is private; never blindly pull/reset/overwrite/discard
uncommitted changes; never delete unmerged branches or lose work; no force-push/rebase/history rewrite; frozen
assets never modified; never loosen tests or thresholds; don't delete or move the owner's personal files (PC, drive
D:); `main` only via the approved workflow.

## 5. Transition checklist (done by the old Supervisor unless marked NEW)
1. Combined merge of T-061, T-075, T-071, T-072 promoted; claims released; task log updated.
2. This file committed to `staging`/`main`.
3. Old Supervisor unsubscribes from PR #2; **NEW: `subscribe_pr_activity` owner P0uyanik, repo Animation, PR 2.**
4. Every running Implementer is told the new Supervisor session id (reply with `send_message` to it; relay stays the
   fallback). Relay line posted so the PC relay/Codex know the new Supervisor (they report via relay as before).
5. **NEW: send one `send_message` to each running Implementer asking for a one-line status by send_message** to
   confirm the two-way direct link; record the result in the task log.
6. Old Supervisor stays available read-only for the owner; it does not merge or assign after the handover.

## 6. State at handover
See `docs/process/TASK_LOG.md` for the full table. Running at handover:

| Task | What | Session / agent | Branch | Next action |
| --- | --- | --- | --- | --- |
| T-065 | Face v2 (`face_generic/2`, opt-in) + criterion 0: 3D head geometry (chin, jaw, face shape) | `session_01NPjxeKEBQQkphCWynxsMCu` | `t-065-claude-face-v2` | Working (ETA ~2–3 h from 23:27Z). AC1–7 READY at b8fc377 (sheets shown to owner; owner decision deferred until criterion-0 sheets). Approved +12 Cycles stills. On READY: show the owner front + 3/4 vs reference sheets; merge only as owner decides (likely "system only, characters unchanged", like hair v3). Needs `versions.py` registry line `_r("face", "face_generic", 2, ...)` + trailer for `pipeline/charsys/tests/test_face_v2.py`. |
| T-070 | Hair v3 round 2 (girl fringe/bun, boy clumps, third S-waves) | `session_01NPjxePeRXGjfaTjJxuGsbv` | `t-070-claude-hair-v3-r2` | Working (head-turn renders). Path B: show owner render sheets, merge on approval. Claims `presets.json` (T-066 waits for it). |
| T-060 | Windows build + Windows CI (Codex on the owner's PC via the local relay) | PC relay + Codex | `t-060-codex-windows-ci` | Local MSVC build + 104/104 tests PASS. Windows CI failed at "Locate VS 2022" (runner image `windows-2025` lacks VS 2022 in `[17.0,18.0)`); fix sent 23:29Z (use `windows-2022` or accept the installed VS). Claim widened (fb0340a). On READY: integration merge + exact trailers for `.github/workflows/checks.yml`, `tests/test_clips.cpp`, `tests/test_shot_workflow.cpp`. |

Finished and merged at handover: T-064, T-076 (report `docs/architecture/REFERENCE_ARCHITECTURE_REPORT.md`), and the
combined T-061/T-075/T-071/T-072 merge (see task log). Idle finished sessions can be archived after merge:
T-061 `session_01NPjxePwRyT3biJzgGf59xN`, T-071 `session_01NPjxePiaod3xb8ZbgvsWPm`, T-072
`session_01NPjxeNnRxgVkFyYsi5XnK6`, T-075 `session_01NPjxeNw29D78oLJU8iFP4M`.

**Open owner items:** face v2 decision (after criterion-0 sheets); T-070 render approval; queue on hold (T-066 skin →
T-067 materials → T-068 garments → T-059 girl round + Boy 2.0 round 2 → T-047 collisions → T-051 fingers → T-053
personality; T-074 CPU render study; wiring the T-071 list of 14 ungated tests (3 pre-existing failures:
deform_test MASK crash, test_shot_eyes girl 0.829 mm, test_emotions AC5); T-054b, T-073 ideas only). Optional:
GitHub rulesets import (`docs/process/github-rulesets/`).

**Follow-ups noted for the Supervisor:** `docs/CHARACTER_SYSTEM_VERSIONS.md` mentions `hair_clumps/2` (retired by
T-072); `docs/process/IMPLEMENTER_PROMPT.md` reporting rule now says: report to the Supervisor session by
`send_message`, relay as fallback.

## 7. Addendum (gaps found after the first handover)
- **Local gate environment.** The old container built C++ with `embree_DIR=/usr/lib/x86_64-linux-gnu/cmake/embree-4.3.0`
  and `PLUSH_OIDN_ROOT=/home/user/deps/oidn-2.3.3.x86_64.linux`, and ran Blender through a bpy-module shim (no
  Blender binary; pass `--blender <shim>` to `check_all.py`). A new container may lack all three: use **GitHub CI on an
  `integration/*` branch as the evidence** (that is the rule anyway) and run locally only the cheap checks
  (`tools/regression/tests/test_gate_tools.py`, `tools/check_doc_links.py`, `tools/integrate.py claims`, the
  guarded/frozen one-liner in §3). Use a separate build dir per worktree if you do build.
- **Owner reference images** sent in chat are not saved to disk automatically: follow `docs/process/REFERENCE_INTAKE.md`
  (shared uploads go to `assets/references/owner_uploads/` or the character's `references/uploads/`; `docs/references`
  is frozen). Images can be recovered byte-exact from your own session transcript (`~/.claude/projects/*/*.jsonl`).
- **Face v2 (T-065) owner context.** AC1–7 sheets were shown on 2026-11-17. Supervisor assessment given to the owner:
  lids clearly better (no shell domes); still off: boy face too wide/flat (lower face and chin), girl/third bright
  lower-lid line, third character upper lid too high + socket edge visible in 3/4, high forehead; skin is T-066. The
  owner deferred the decision until the criterion-0 head-geometry sheets. Recommendation pending: merge as an opt-in
  system only (characters unchanged), like hair v3.
- **T-076 report** (`docs/architecture/REFERENCE_ARCHITECTURE_REPORT.md`): recommendations (G1–G10: two-hand grasps,
  lean/self-contact verbs, profile reader + limits, file-mesh props, light/camera presets, unified prop path, bake
  events, sequence assembly) await an owner decision; nothing was scheduled from it.
- **PC backup** (owner allowed the PC as a backup destination) is not set up: it would need Remote Control (elevation),
  so it stays open; GitHub-side backups run via `.github/workflows/backup.yml` (archive/backup-* branches, tags made
  by Actions). Ask the owner before any PC-side setup; do it via the relay, never by elevating.
- **Leftover integration branches** (`integration/t-061`, `integration/t-071`, `integration/t-075`,
  `integration/batch-061-075-071`, `integration/t-064`) are merged; the cleanup workflow (T-048) handles them; never
  delete branches by hand.
- **Remote Control:** the owner's PC currently shares no folder with cloud sessions and the old Supervisor's Remote
  Control link to the PC session is gone. Do not try to restore it from a cloud Supervisor (needs elevation). If the
  owner wants direct PC access again, recommend a separate, dedicated session for that, never the Supervisor.
