# Supervisor handover, round 3 → round 4 (2026-11-21 ~01:40Z)

Owner decision 2026-11-21 ~00:25Z: rotate the Supervisor after the R3 release. This file points to the sources and does not copy them.
Round-3 Supervisor: session_01NPjxeL81bNYoFDm9Ypv5Ck (goes idle after takeover; implementers still report to it until you
message them). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU. Owner-facing reports, READY and decision requests go there.
The original Supervisor session_01NPjxeNTmHt2DtBN8F8uLqB is unreachable (trusted-device error).

## Standing rules (sources: OWNER_DECISIONS.md, brief in the R3 handover)
- Reserved for the owner: making a version CURRENT, deleting anything under A3, GPU rental, and new scope beyond the approved plan.
- Never weaken, skip or remove tests, thresholds or goldens. Never modify frozen or published assets. No force-push or history rewrite, no branch
  deletion, no PRs, no model identifiers in commits. Respect permission-classifier denials: report them, no workaround.
- Environment `env_01MTWJVTWBHG13yZcRS4DzCz`. Session cap is **temporarily 7** (owner ~20:30Z, until the bundle merges or the owner
  says otherwise). Models: Fable 5.2 for visual work, Opus 5.5 by default, Sonnet 5.5 for mechanical work.
- Rework rule: an implementer above ~250k context with narrow feedback gets a fresh session with a pointer brief (T-176 found this
  was not followed for visual rounds). Send one consolidated feedback message per round.

## State
- main = staging = `ea4e440` = R3 release (boy 2.3.0 / girl 0.14.0 / third 0.1.0 CURRENT, full gate 44849547856 green); docs on top up to this file (main moves only by docs since).
- Merge recipe: integration branch from main; merge with `--no-ff`. Compute guarded paths with
  `check_all.guarded_patterns()`/`matches()` over `git diff --name-only origin/main...HEAD`, review them, then make one empty commit
  with `Supervisor-Approved: <path>` lines (implementers must NOT write these). Push, run `gh run watch <id>`, then promote:
  `git push origin <sha>:refs/heads/staging <sha>:refs/heads/main` (fast-forward only).
- Claims: `tools/integrate.py claims --check T-NNN`. After any OWNERSHIP edit, run
  `python3 tools/regression/tests/test_gate_tools.py`. A row whose write-set cell has no back-ticked paths breaks the gate (this
  kept main red 15:41–21:30Z on 11-20).
- **Batch docs pushes to main.** Every main move forces integration branches to re-merge and re-gate (T-176 finding 2).

## Implementer sessions
| Task | Session | Branch | State / next |
|---|---|---|---|
| T-171 hands round 2 (Fable) | session_01NPjxeLU2sMH4otka5fuSE1 | t-171-claude-hands-r2 | started after R3; brief `docs/tasks/T-171.md` (ownership vs T-175 in it). |
| T-172 test video (Sonnet) | session_01NPjxePMjSGJzaMrqPDNdb2 | t-172-claude-test-video | started after R3; brief `docs/tasks/T-172.md`; READY → send paths to the liaison. |
| T-175 locomotion (Opus) | session_01NPjxePthX6LUTzxubPhcNj | t-175-claude-locomotion@53cf255 | CHECKPOINT sent to the owner (01:18Z): style review pending. Defects listed (black hands at stand-up, popping check flags footfalls, 90° turn + step, garment under skin seated). Not merged. Registration lines needed at merge: `tests/CMakeLists.txt` add test_foot_lock.cpp to plush_tests; `tools/check_all.py` python tests add `pipeline/clips/tests/test_import_bvh.py`. Also `docs/ANIMATION_CLIPS.md` §8/9 is outdated (not in its claim). |
| T-155 release (Opus) | session_01NPjxeNhRLKn2GCC7oqttgu | integration/r3-faces | merged; it was told to stop its local check and report only a failure. Archive it if quiet. |
Archived after the R3 merge: T-156, T-159, T-167 (branches kept). Earlier: T-144, T-166, T-168, T-174, T-176.

## Codex (relay-channel, NEXT_TASK.md top)
T-173 local GPU render benchmark on the owner's PC (measurement only, `docs/evaluation/rendering/T-173/**`; relay-channel@722c00e9).
T-161 reference targets (Codex limited until 2026-11-23 ~21:43Z).

## Waiting for the owner
1. T-175 style review (questions at the top of `docs/evaluation/animation/T-175/README.md`).
2. T-176 proposals (`docs/audit/T-176/REPORT.md`, 14 items). Nothing is applied without approval.
3. T-174 code vs no-code (owner still deciding; plan beyond T-175 on hold).
4. Later items logged by the owner: T-156 limits; T-168 chin/jaw/cheek line; T-159 ears slightly wide; boy hair improvement (r6 kept,
   flicker limit 0.056); T-168 side effect on boy shoes/trousers ≤3.6 mm (garment fit reacting to the head change).

## On hold
T-170 world plan (trimmed 4.5–6 d, ready-made materials only). T-144 removals (option c: legacy documented instead). Run/turn/idle
mocap and walk-on-clips (T-174 step 4). New Codex tasks.

## Known issues
- Implementer permission layers refuse relayed owner approvals for releases, guard changes and scope changes. Ask the
  liaison to have the owner type the exact words in that session, and verify them with `list_events` (kinds user) before recording
  (this happened ~6 times on 11-20).
- `create_trigger`/`send_later` were denied by the classifier, so there is no hourly self-check. Long background waits: use `gh run watch`.
- Implementer sessions can go idle while waiting on their own background jobs (T-156 at 19:47Z). Check `list_events` when one is quiet.
- Some sessions' model/effort was changed outside the Supervisor (T-176 ran on Fable at max effort with ultracode); check
  `get_session` if cost matters.
