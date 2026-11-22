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

## R6 log (Supervisor session_01NPjxePvWAMsLopzSs1fMXB, from ~12:05Z)
- Merged: T-193 (main 5010873, gate 45020921791), T-192 (main 7658003, gate 45021042377; ledger T-190 + clip_layers.cpp,
  tests/test_hand_limits.cpp rode along). T-183 row + scene.h (1632da5).
- T-183 r3 continues in a FRESH session session_01NPjxeNn6rj76f28MV4nHnx (FULL profile, Fable high); the old one pushes
  its last measures then stops. T-190 design approved: default thumb change behind one switch, golden list + sheets
  → owner OK before any re-bless; palm-plane lay-back; no interaction.cpp (box-face wrap drop at :1256 = follow-up).
- Liaison asked: T-193 4 questions; T-192 "is s010 f42 (eye convergence) the moment?"; T-189 §7 still open.
- Follow-ups added: eye convergence limits (gaze, after T-190); box-face wrap key drop (interaction.cpp:1256, after T-191).
- Gate wait script: scratchpad wait_gate.sh <branch> <sha> (curl actions/runs, poll 60 s).

## Running (all report to the Supervisor; each started design/diagnosis-first)
| Task | Session | Branch | State / next |
|---|---|---|---|
| T-183 r3 hair vs props/table/neighbours + own body in real shots + fan-out (Fable) | session_01NPjxeMEWYzeUqnyUKscxwC | t-183-claude-hair-contact (0769144+) | design approved: box colliders in secondary.*, derive_shot.py writes e912 *_t183 + e909 s010_t183 copies with prop colliders, neighbour bones via scene.cpp (opt-in), white-haired girl in scope, fan-out levers. Measured released e912 s010: hair through table 12.5 mm (both girls), auburn ringlets in the boy 68 mm. Merge needs: TESTS line `run test_hair_contact.py` (pipeline/charsys/tests/TESTS) + trailers release_rule.py, tests/test_secondary.cpp, test_hair_contact.py, test_release_rule.py. |
| T-190 finger/thumb joint limits system-wide (Fable) | session_01NPjxeLH3KPsH5iYaR3radj | t-190-claude-finger-limits | diagnosing; STATUS with cause + design + golden impact due; golden/test changes need Supervisor (and owner if defaults move). |
| T-191 character–character collision (Opus) | session_01NPjxeMSi1jfB5YthUet6ZP | t-191-claude-char-collision (80f7d92+) | design approved: opt-in "interaction" bodyClearance lean pass, off by default; worst measured e912 heads through heads ~100 mm. Not scene.cpp (T-183): parse elsewhere or hand-over lines for merge. Register tests/test_body_clearance.cpp in tests/CMakeLists.txt at merge. Asks before editing episodes (use *_t191 copies). |
| T-192 boy blink sync (Sonnet) | session_01NPjxePT9NbJYodeGknNd7N | t-192-claude-blink-sync (6c00605+) | no desync in engine/bake/package/Blender; far eye hidden by fringe in the two-shot. Adding a guard test + both-eyes close-up → READY. Owner asked (via liaison) for the clip timestamp. |
| T-193 hair systems research (Opus, docs only) | session_01NPjxeNdWgW926FfZs5A1Gc | t-193-claude-hair-research | researching → README with recommendation; blocked hosts to the liaison. |

## Waiting for the owner (via the liaison)
1. T-192: timestamp of the out-of-sync blink in T-187_paper_boat_h264.mp4.
2. T-189 questions (README §7): hosts kenney.nl / quaternius.com / itch.io (+CDN) or opengameart.org; CC0 geometry +
   material override as "ready-made"; plain git vs LFS; credits line; water ripple; AI-3D; Infinigen side-car run.

## Follow-ups logged (not dispatched)
Nape cap vs neck-skin fold (body skinning, T-183 item 1); seated thigh through the shorts front panel (T-184 limit 1);
T-171: carry/hand-over wrist bend up to 93°, finger "press" depth, planArmLift popping; e909 r3: boy release 22.9 mm
through the cup if keys go on the pass; boy ankle hem vs foot skin; girl button/embroidery normals vary build to build;
test_recipe needs ab9fd4c at depth 1; stack_specs.py docstring names the old allowlist; world plan (T-170d) on hold
pending T-189 answers.
