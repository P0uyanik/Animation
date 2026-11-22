# Supervisor handover, round 6 → round 7 (2026-11-22 ~19:40Z)

Round-6 Supervisor: session_01NPjxePvWAMsLopzSs1fMXB (rotated for context). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU.
Standing rules: SUPERVISOR_HANDOVER_R6.md (top + "R6 log"), R5, R4; OWNER_DECISIONS.md (R6 added: no Fable — Opus default,
Sonnet mechanical; hands sub-mm/sub-degree side effects inside an approved scope = Supervisor decides + records; engine works
closely with Blender in all areas; all face angles weighted equally; ship hair/face versions independently).

## State
main = staging = c90315a (+ this handover / ledger once integration/t-199 promotes). Stack still in the gate:
`integration/t-207` (T-207 hair-look candidates, 3a32740) → `integration/t-199` (T-199 compositor look, 0f3787e) on top.
When the t-199 gate is green: `git push origin 0f3787e:refs/heads/staging 0f3787e:refs/heads/main` (ff), then push the
local ledger commit 65dab4c (branch r6-docs, T-210/T-211 rows + owner ~20:35 CET) rebased onto it — if lost, redo: OWNERSHIP
rows T-210 (engine/anim/animation.*, engine/scene/actions.cpp, engine/scene/interaction.*, tests/test_motion_continuity.cpp,
tests/golden/continuity_baseline.json, tests/golden/interaction_hashes.json, docs/evaluation/interaction/T-210/**) and T-211
(docs/research/T-211/**). Gate wait: watch https://api.github.com/repos/P0uyanik/Animation/actions/runs?branch=<b> (no auth).
Merge recipe unchanged; tests are registered in `TESTS.manifest` files (plain TESTS fails the gate) or tests/CMakeLists.txt;
check a Blender-unit registration really runs the file (T-207: I extended unit_hair_curves). Stack integration branches so
one green gate promotes several; docs/process-only pushes take the fast path but break ff for running integration gates.

## Running
| Task | Session (model) | Branch | Next |
|---|---|---|---|
| T-194 hair push-out (render time) | session_01NPjxePALLCviMLH4YKW2mL (Opus) | t-194-claude-hair-pushout @ 394b47f+ | 10-14 h measure queue IN ITS CONTAINER (don't replace). Candidate pin e7547ab4 first, then final s020+s030 pair on T-183 c7b3cee2 (engine differs: T-190 hands, clear_targets, PAD 4 mm). Must cover T-183 leftovers (T-183 ROUND.md Session 9 "For T-194"). Register test_hair_pushout.py in pipeline/charsys/tests/TESTS.manifest. Then Q1 contact audit → Q4 Blender set lighting → L1 garment push-out (all touch shot_render.py) + H2 hair volume per character. |
| T-210 grasp/release finger curls | session_01NPjxePewGs7URgLgdLugc7 (Opus) | t-210-claude-grasp-curls | approved within T-198 scope; content golden changes come to you first with numbers; shrink tests/golden/continuity_baseline.json. |
| T-211 Blender-first face research | session_01NPjxeNU3fnUWi3nosRB6rb (Opus) | t-211-claude-blender-first-faces | docs only → READY → relay to liaison. |
Queued: T-201 preview_eevee render profile (owner-approved; start after T-199 promotes; render_profiles.json; engine key
convention from T-205: profile "engine" key, else --engine; check EEVEE works headless on CPU, else PC-only). T-207 hook
patch docs/evaluation/characters/T-207/groom_r6_flock_hook.patch → apply when the owner picks a hair look.
Codex (owner PC, relay): T-204 face targets (branch t-204-codex-face-targets), T-208 e912 EEVEE checks from bake packages
(runs 45052327444 s010, 45053708309 s020, 45053710885 s030 — workflow "Bake package" on main, workflow_dispatch).

## Waiting for the owner (via the liaison; all relayed)
1. T-207 hair look per character (V1 / V2 / V3 / D / keep current). 2. T-199 compositor look (plush_soft / plush_strong / none).
3. T-209 face decisions (fit-and-lock; pass rule; matched smile refs; order white → boy → auburn; my rec yes to all; view
weights stay equal, face/hair ship separately — both already owner-decided). Face fit work waits for Codex T-204 + T-211.
4. World plan start (liaison relays). Voices on hold.

## Closed in R6
T-190, T-191, T-192, T-193, T-195, T-196, T-198, T-202, T-203, T-205, T-206, T-209, T-183 (round 3 merged 961371b), Codex
T-197/T-200. T-207 + T-199 in the final gate (sessions told to stop). Follow-ups: see R6 handover "Follow-ups logged".
Next free ID: T-212.

## R7 log (Supervisor session_01NPjxeKJV7E1M9rnLTkzJoo, from ~19:35Z)
- Promoted integration/t-199 (0f3787e, gate 45060162046 green; carries T-207 3a32740) and r6-handover-ledger (0a1422a).
- T-194 at e13b64e: test_hair_pushout.py registered `local` (needs bpy). At merge the Supervisor adds it to a Blender
  check_all unit (as T-207/unit_hair_curves) so the gate runs it.
- T-201 dispatched (Opus, session_01NPjxeMa91JgXQWgeGw6Uvi). shot_render.py / run_shot.py stay with T-194: T-201 passes `--engine eevee` explicitly there;
  making shot_render/run_shot honour the profile "engine" key is a 2-line follow-up after T-194 merges.
- T-211 merged (docs only, fast path); decision 7 (built-in Warp/Hook/Lattice as face_generic/4 knobs) relayed with T-209 D.
- Follow-up logged (not dispatched): T-183 bake slowdown 2.26x (4 shots 51.5 s → 116.3 s); round-2 skin sphere colliders alone 2.0x, neighbour colliders +7.7 s, clear_targets +4.6 s. Cheaper skin settings (spacing_m, reach_m, substep_hz) untested; re-measure if bake time matters.
- T-210 decisions (Supervisor, owner rule ~17:25 CET: in-scope hand changes = Supervisor decides + records): (1) re-record
  15 of 20 interaction goldens APPROVED — only the grasping hand's R finger bones (+ DEF tips) move on the 5-frame
  close/open windows (max 56.7° / 11.6 mm; e901 girl 74.2° / 13.6 mm), finger snaps 31.7°/f → 0; this is T-210's
  approved purpose (T-198 follow-up), table docs/evaluation/interaction/T-210/golden_delta.md. Owner gets one line at merge.
  (2) tests/test_verbs.cpp added to T-210's write-set for the one-line pinch key pin (evaluate(16) → (15), T-210 ramp note).
