# Supervisor handover, round 7 → round 8 (2026-11-23 ~04:45Z)

Round-7 Supervisor: session_01NPjxeKJV7E1M9rnLTkzJoo (rotated for context). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU.
Standing rules: SUPERVISOR_HANDOVER_R7.md ("R7 log"), R6, R5, R4; OWNER_DECISIONS.md (R7 added: face plan approved
2026-11-22 ~22:40 CET — T-212 changes, auburn pilot first, D2 equal views, D4 matched smile, D6 face/hair ship apart).
No Fable (Opus default, Sonnet mechanical); P2 visual budget; one owner per file; T-178 release rule; T-182 test
registration; P13 clone profiles (dispatch FULL, depth 1, for character/render/test work). Next free task ID: **T-221**
.

## State
main = staging = integration/t-217 1c09458f (T-217 + R7 ledger) once its gate is green (the eaabda6e run hung queued with
no jobs; superseded) + branch r7-final on top (owner ~06:58 CET picks, T-219/T-220 rows). If R7 rotated before promoting:
`git push origin 1c09458f:refs/heads/staging 1c09458f:refs/heads/main`, then ff-push origin/r7-final the same way. Gate wait: scratchpad-style loop on
`https://api.github.com/repos/P0uyanik/Animation/actions/runs?branch=<b>` (no auth); gate verdict lines:
`gh run view <id> --log | grep "Combine reports" | grep -E "PASS|FAIL"`.

## Merge lessons from R7 (add to the recipe)
- Shared code may not name a character (Shared-systems lint) → ids come in as arguments.
- New `docs/evaluation/**/shot.scene.json` copies must cast CURRENT versions (T-178); the white girl has none → reference
  the episode file instead of copying it.
- A new module imported by shot_render.py must be added to bake_package.py RENDER_CODE (test_bake_package).
- Blender-needing tests: implementer registers nothing; Supervisor adds a `blender <file> <unit>` line + a unit in
  tools/check_all.py BLENDER_UNITS + tools/ci/blender_shards.json (shard + "added_after_t127"); run
  tools/ci/tests/test_t127_shards.py and `check_all.test_registry(unit_ids=check_all.BLENDER_UNIT_IDS)`. Units added in R7:
  face-parity (5), face-measurer (2), hair-pushout (3).
- OWNERSHIP rows must stay inside the table (no blank line before them); run `claims --check-all` + test_gate_tools.py.
- Docs pushes to main break ff for a running integration gate: batch them on a local branch and merge on top after promotion.
- A staging gate success counts when the main run of the same sha is cancelled ("Already verified?").

## Running
| Task | Session (model) | Branch | Next |
|---|---|---|---|
| T-217 profile engine key | session_01NPjxeLxepAyFoUf6uzmqgm (Sonnet) | t-217-claude-profile-engine | in gate as integration/t-217 1c09458f → promote, tell it to stop. |
| T-220 plush_soft default final profile | session_01NPjxeNJNF6qq6ebqoT9or2 (Sonnet) | t-220-claude-default-look | READY → integration gate → promote; tell the liaison finals now use plush_soft. |
| T-216 auburn face P3 (owner GO) | session_01NPjxeNkz9QaQntYYhFp3SF (Opus) | t-216-claude-auburn-p3 | STATUS after knob design, then READY with combined sheet → liaison (owner review before any release). |
| T-218 Q1 contact audit tool | session_01NPjxeNefPKq6DNksLkwLjk (Opus) | t-218-claude-contact-audit | STATUS after e912 validation, then READY; register its test (Blender unit if bpy). |

## Waiting for the owner (via the liaison; all relayed)
(Owner ~06:55 CET 23 Nov: T-194 static_move_fade ON stays default, rate-limit follow-up NOT started; P3 GO → T-216 running.)
1. (Owner ~06:58 CET: hair V1 for auburn + white, boy unchanged → T-219 queued; plush_soft default final → T-220 running.)
2. T-216 P3 on auburn (running): Warp/Hook/Lattice for the T-215 stuck list (docs/evaluation/characters/T-215/stuck.json:
   eye-to-chin, front cheek/jaw width, side cheek, eye opening), baked on neutral skin before rig/masks; acceptance =
   T-214 measurer within T-204 tolerance + held-out 3/4 + T-213 face_parity (incl. `--strict` sweep: fix the in-between
   chain gap via chain-matched drivers or stop keys) + knob-free; then a combined sheet. Supervisor rec: yes.
3. World plan start. Voices on hold.

## Queued (owner-approved, dispatch in order, one owner per file)
- Q4 lighting setups in Blender set files (touches shot_render.py → after T-217).
- L1 garment–body collision + cloth-sim evaluation for loose pieces (after T-218; use its audit).
- H2 hair volume per character (after T-194, now free). L2 correctives after the next character release.
- **T-219 hair release (dispatch first):** apply docs/evaluation/characters/T-207/groom_r6_flock_hook.patch, V1 for auburn +
  white-haired (boy unchanged), H2 volume + forehead/ear stair-step fix, new versions (T-178 release rule, release_rule.py),
  one sheet per character → liaison → owner approval before CURRENT. Must not collide with T-216 (T-216 writes no assets;
  coordinate if T-216's release follows: hair and face ship independently, D6).

## Closed in R7
T-199, T-207, T-201, T-210, T-211, T-213, T-214, T-215, T-194; Codex T-204, T-208, T-212 (docs, fast path).
Follow-ups logged: T-183 bake slowdown 2.26x (skin colliders 2.0x; cheaper settings untested); auburn stepped hair edge
at ±90° in front of the ear (released 0.14.0 too); T-215 outline_exponent jaw follow-up folded into P3.
