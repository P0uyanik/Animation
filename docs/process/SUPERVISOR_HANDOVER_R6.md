# Supervisor handover, round 5 → round 6 (2026-11-22 ~00:45Z)

Round-5 Supervisor: session_01NPjxeLwrBZTHQcvtcEtsUk. Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU (owner decisions only
via the liaison or typed by the owner in a session). Standing rules: SUPERVISOR_HANDOVER_R5.md + R4 (unchanged), plus
OWNER_DECISIONS 2026-11-21 ~19:20 / ~22:45 / ~23:10 CET. P13: LIGHT clone only per CLONE_PROFILES.md §3.

## State (updated 2026-11-22 ~12:10Z)
main = staging = da41d26 (T-187 merged at 44f9fb3, gate 45018717142 green; ledger on top). Merged in R5: T-175 r2, T-184,
T-171 r3, T-185, T-186, T-188, T-189, T-187. Merge recipe unchanged. Gate wait: background Bash polling
`https://api.github.com/repos/P0uyanik/Animation/actions/runs?branch=<b>` (no auth), then ff promote
`git push origin <sha>:refs/heads/staging <sha>:refs/heads/main`. `git reset --hard` is refused by the auto-mode classifier:
use `git checkout -q -B <branch> origin/main`. Guarded paths: `check_all.guarded_patterns()` is a list → `any(check_all.matches(f, p) for p in pats)`.
OWNERSHIP rows must sit inside the table (above the "Supervisor-only files" footer); `claims --list` shows what is parsed.
Pre-existing reds (informational): "CI status (main)" summary job; Windows gate (b9c0d4e, 11-21); Branch cleanup (since 11-17).
Owner decisions ~04:20 CET 22 Nov: T-187 accepted, NO revised video until the system fixes below land.

**Model rule (owner ~15:20 CET 22 Nov): no Fable. Opus by default, Sonnet for mechanical work; running Fable sessions
continue in a fresh Opus session after their next checkpoint.**

## R6 log (Supervisor session_01NPjxePvWAMsLopzSs1fMXB, from ~12:05Z)
- Merged: T-193 (main 5010873, gate 45020921791), T-192 (main 7658003, gate 45021042377; ledger T-190 + clip_layers.cpp,
  tests/test_hand_limits.cpp rode along). T-183 row + scene.h (1632da5).
- T-183 r3 continues in a FRESH session session_01NPjxeNn6rj76f28MV4nHnx (FULL profile, Fable high); the old one pushes
  its last measures then stops. T-190 design approved: default thumb change behind one switch, golden list + sheets
  → owner OK before any re-bless; palm-plane lay-back; no interaction.cpp (box-face wrap drop at :1256 = follow-up).
- Liaison asked: T-193 4 questions; T-192 "is s010 f42 (eye convergence) the moment?"; T-189 §7 still open.
- Follow-ups added: eye convergence limits (gaze, after T-190); box-face wrap key drop (interaction.cpp:1256, after T-191).
- Gate wait script: scratchpad wait_gate.sh <branch> <sha> (curl actions/runs, poll 60 s).

## Running (R6, as of ~17:30Z; main = staging after this push)
| Task | Session (model) | Branch | State / next |
|---|---|---|---|
| T-183 r3 hair engine colliders | session_01NPjxeNkwAEozJp2WgBvgGi (Opus) | t-183-claude-hair-contact | A cup + B fixed (clear_targets); D final runs, then E README/READY. Merge: register new tests, trailers as for c775d69; give T-194 the final pin. |
| T-194 hair push-out | session_01NPjxePALLCviMLH4YKW2mL (Opus) | t-194-claude-hair-pushout | stages A+B built, f110-112 fixed, measuring real shots against T-183 pin e7547ab4. Register test_hair_pushout.py. Q1/Q4/L1 wait for it (shot_render.py). |
| T-198 motion continuity | session_01NPjxeKFhB6MjQW9AoXXVst (Opus) | t-198-claude-motion-continuity | design approved (source fixes in actions.cpp ikRamps, assistGazeWithNeck convergence, receiver orient ramp; detector + speed-limit test; no limiter). Goldens: numbers to me first; owner if visible/outside scope. Register tests/test_motion_continuity.cpp. |
| T-199 compositor look | session_01NPjxeLdrDJrSXXNtaCUK5V (Sonnet) | t-199-claude-compositor-look | code + tests done (b4d8705); final720 side-by-side renders (soft + strong) → owner approves before use. Then T-201 preview_eevee. |
| T-203 TESTS → TESTS.manifest | session_01NPjxeNmio6xu7vC4pXDwgt (Sonnet) | t-203-claude-tests-manifest-rename | Windows case collision; same test set before/after; + case-collision check. Trailers for all manifests + check_all/ready. Re-check other branches' new TESTS lines at their merges. |
| T-205 bake package + PC render | session_01NPjxeLneYX48vFFGroyvGf (Opus) | t-205-claude-bake-package | cloud/CI zip, no engine exe; tools/pc one command. |
| T-206 face + wool research | session_01NPjxePp9vJdYxLR6AyFiB9 (Opus) | t-206-claude-face-hair-research | docs only; uses Codex T-204 targets. |

Closed in R6: T-190, T-191, T-192, T-193, T-195, T-196, T-202; Codex T-197, T-200 merged. Codex T-204 running on the owner PC (relay).
Owner standing rules added in R6: no Fable (Opus default, Sonnet mechanical); hands sub-mm/sub-degree side effects in scope = Supervisor decides + records.

## Waiting for the owner (via the liaison)
1. T-199 compositor look approval (after the side-by-side).
2. World plan start (liaison relays). 3. Voices on hold. 4. Faces: after T-206 + Codex T-204.

## Follow-ups logged (not dispatched)
Nape cap vs neck-skin fold (body skinning, T-183 item 1); seated thigh through the shorts front panel (T-184 limit 1);
T-171: carry/hand-over wrist bend up to 93°, finger "press" depth, planArmLift popping; e909 r3: boy release 22.9 mm
through the cup if keys go on the pass; boy ankle hem vs foot skin; girl button/embroidery normals vary build to build;
test_recipe needs ab9fd4c at depth 1; stack_specs.py docstring names the old allowlist; world plan (T-170d) on hold
pending T-189 answers.
