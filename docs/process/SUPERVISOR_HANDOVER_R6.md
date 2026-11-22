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

## Running (R6, as of ~13:35Z; main = staging = ec56331)
| Task | Session | Branch | State / next |
|---|---|---|---|
| T-183 r3b hair engine colliders (Fable) | session_01NPjxeNn6rj76f28MV4nHnx | t-183-claude-hair-contact | candidate c775d69 merged; building neighbour/prop colliders (golden-identical off, ~1.05x) + contact.carry. Body-snap frames (±1) and rigid-part-in-boy listed apart, not in its criterion. Merge needs TESTS/trailers like c775d69. |
| T-194 hybrid hair push-out (Fable) | session_01NPjxeL5HtXkGWdiap3R8or | t-194-claude-hair-pushout | design approved (stage A ray re-key of DYN chains, stage B GN clamp; opt-in --hair-pushout; nape pushed out; hair-vs-hair out). run_shot.py granted. Register test_hair_pushout.py in pipeline/charsys/tests/TESTS at merge. |
| T-190 finger limits (Fable) | stopped at ~300k (session_01NPjxeLH3KPsH5iYaR3radj) | t-190-claude-finger-limits@250ad00 | READY; owner: default ON/OFF + 33 vs 45 box-face lay-back (my rec: ON + 45 box only). Next round = FRESH session from ROUND.md; add tests/test_grasp_contact.cpp + tests/test_verbs.cpp to its row; register tests/test_hand_limits.cpp; 6 goldens re-record only after owner OK. |
| T-195 sound (Opus) | session_01NPjxePtiFXPhYUXTLBiWzx (idle) | merged | owner: record child gasps/laughs? (or freesound key). |

Closed in R6: T-191, T-192, T-193, T-196 (sessions told to stop).

## Waiting for the owner (via the liaison)
1. T-190 default on/off + lay-back (above).
2. Motion-continuity task (body snaps in T-187: s010 hand jumps, s020 head 95-115 deg/frame, s030 cut at f93, keyed touch
   shape 28-36 deg/frame) — proposed for after T-190 (same animation.* file).
3. T-195 voices: owner recordings or freesound key.
4. T-196 Q1-Q4 (contact audit standard line; compositor side-by-side; L2 timing; Kenney manual download).
5. World plan start (all questions answered; liaison relays).

## Follow-ups logged (not dispatched)
Nape cap vs neck-skin fold (body skinning, T-183 item 1); seated thigh through the shorts front panel (T-184 limit 1);
T-171: carry/hand-over wrist bend up to 93°, finger "press" depth, planArmLift popping; e909 r3: boy release 22.9 mm
through the cup if keys go on the pass; boy ankle hem vs foot skin; girl button/embroidery normals vary build to build;
test_recipe needs ab9fd4c at depth 1; stack_specs.py docstring names the old allowlist; world plan (T-170d) on hold
pending T-189 answers.
