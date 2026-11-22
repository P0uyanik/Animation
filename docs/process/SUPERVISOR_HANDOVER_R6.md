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

## Running (R6, as of ~18:55Z; main = staging = 8c69815+)
| Task | Session (model) | Branch | State / next |
|---|---|---|---|
| T-183 r3 hair engine colliders | session_01NPjxeNkwAEozJp2WgBvgGi (Opus) | t-183-claude-hair-contact @ c6842d5a+ | B fixed (clear_targets), C leftovers listed for T-194 (ROUND.md Session 9), r9 final runs on merged main. READY must break down the 2.2x bake slowdown per opt-in feature. Merge: register new tests in pipeline/charsys/tests/TESTS.manifest, trailers as for c775d69, then give T-194 the final pin; apply T-207's groom_r6 hook patch after. |
| T-194 hair push-out | session_01NPjxePALLCviMLH4YKW2mL (Opus, ~200k) | t-194-claude-hair-pushout @ 394b47f | measure queue 10-14 h IN THAT CONTAINER (do not replace the session; outputs are local). Candidate pair s020 first → 3-line STATUS. Lock-volume + back-face rules OFF. Register test_hair_pushout.py. Q1/Q4/L1 wait for it (shot_render.py). |
| T-198 motion continuity r2 | session_01NPjxeNqDsz21bSwmqjn6zA (Opus) | t-198-claude-motion-continuity | content goldens bit-identical; s020 0 snaps; approved: re-record test_interaction/visibleGrip/boy; speed-limit test as ratchet baseline; follow-up T-209 = grasp/release finger-curl timing. Register tests/test_motion_continuity.cpp in tests/CMakeLists.txt. |
| T-199 compositor look | session_01NPjxeLdrDJrSXXNtaCUK5V (Sonnet) | t-199-claude-compositor-look @ b4d8705+ | final720 side-by-side (soft + strong) → owner approves before use. Then T-201 preview_eevee (engine key convention from T-205). |
| T-207 hair look (velvet/flock) | session_01NPjxeMc65LUidkdd4NUwfb (Opus) | t-207-claude-hair-flock @ 0184fd2+ | V1/V2/V3/D sheets rendering → owner picks. groom_r6 hook = patch in its folder (apply after T-183). test_hair_flock.py to register. H2 volume = later task after T-183/T-194. |

Codex (owner PC, relay): T-204 face targets; T-208 e912 EEVEE checks from bake packages (runs 45052327444 s010, 45053708309 s020, 45053710885 s030). Next Supervisor ID: T-209 (reserved: grasp/release curls), then T-210.
Closed in R6: T-190, T-191, T-192, T-193, T-195, T-196, T-197 (Codex), T-200 (Codex), T-202, T-203, T-205, T-206 (sessions archived by the liaison).
Owner standing rules added in R6: no Fable; hands sub-mm/sub-degree side effects in scope = Supervisor decides + records; engine works closely with Blender in all areas.
Merge tips: TESTS files are now TESTS.manifest (plain TESTS fails the gate); stack integration branches on the previous one to promote several with one green gate; docs/process-only pushes take the fast path; gate wait = scratchpad wait_gate.sh, workflow runs = wait_run.sh.

## Waiting for the owner (via the liaison)
1. T-199 compositor look approval (after its side-by-side). 2. T-207 hair look pick (after its sheets).
3. World plan start (liaison relays). 4. Voices on hold. 5. Faces: fit after Codex T-204 (owner answers ~19:10 CET recorded).

## Follow-ups logged (not dispatched)
R6: interaction.cpp box-face fingerClose.wrap drop; clip retarget (wave/point back-flex, authored thumb curl); 30° knuckle spread vs T-138 band fit; e909 boy tile camera; paper_white material preset missing; eye convergence limits (low); T-209 grasp/release curls; H2 hair volume per character (after T-183/T-194); L2 correctives after next release.
Nape cap vs neck-skin fold (body skinning, T-183 item 1); seated thigh through the shorts front panel (T-184 limit 1);
T-171: carry/hand-over wrist bend up to 93°, finger "press" depth, planArmLift popping; e909 r3: boy release 22.9 mm
through the cup if keys go on the pass; boy ankle hem vs foot skin; girl button/embroidery normals vary build to build;
test_recipe needs ab9fd4c at depth 1; stack_specs.py docstring names the old allowlist; world plan (T-170d) on hold
pending T-189 answers.
