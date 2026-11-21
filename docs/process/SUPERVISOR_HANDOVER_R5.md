# Supervisor handover, round 4 → round 5 (2026-11-21 ~16:30Z)

Round-4 Supervisor: session_01NPjxeNjJghYQMGjDycpnsC (idle after takeover). Owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU
(owner decisions only via the liaison or typed by the owner in a session). Pointers only; sources: OWNER_DECISIONS.md,
TASK_LOG.md, OWNERSHIP.md, STATUS.md, docs/process/SUPERVISOR_HANDOVER_R4.md (standing rules unchanged).

## Standing rules added in round 4 (all in OWNER_DECISIONS 2026-11-21)
- P2 visual-round budget: fresh session over ~250k context; ROUND.md per visual task; sheets as ≤1024 px crops; effort high.
- Docs-only fast path (T-177): pushes touching only `docs/process/**` + `docs/tasks/**` run a ~1 min job, which also runs
  `integrate.py claims --check-all`. ALWAYS run `python3 tools/integrate.py claims --check-all` before a ledger push (a failed
  one went to main once: 36086ec). Docs pushes still move main: push them only when no integration branch is waiting.
- One owner per file (T-181/T-181b): globs only, no "(… only)" qualifiers, read overlaps are warnings, write overlaps fail.
- Release rule (T-178): opt-in features in published specs only if listed in `pipeline/charsys/release_manifest.json`
  (guarded); new opt-in keys need a detector in `pipeline/charsys/release_rule.py` + a SAMPLES entry in test_release_rule.py.
- Test registry (T-182): tests are registered in per-directory `TESTS` manifests; new test files and append-only manifest
  lines need no trailer; changing/renaming/deleting an existing test does. C++ tests still go in tests/CMakeLists.txt.
- Relayed owner approvals for test/guard changes: verify with list_events that the owner typed it in that session
  (client_platform desktop_app/web); use a subagent for paging (results are large).
- Priority (owner ~11:10Z): animation production; no further workflow optimisation unless needed.

## State
main = staging = 83b8c37 (green). Merge recipe unchanged (integration branch, --no-ff, trailer commit, full gate, ff promote
`git push origin <sha>:refs/heads/staging <sha>:refs/heads/main`). Gate wait: poll the Actions API with curl in a background
Bash (gh CLI is for search only here). Session cap 7.

## Implementer sessions (all Fable, effort high)
| Task | Session | Branch | State / next |
|---|---|---|---|
| T-175 r2 locomotion | session_01NPjxeMaW53s2xejp6nafPF (537k: next round → fresh session) | t-175-claude-locomotion@c384f1d | READY; waits for owner acceptance (CHECKPOINT relayed ~15:55Z). At merge register tests/test_foot_lock.cpp in tests/CMakeLists.txt and pipeline/clips/tests/test_import_bvh.py in pipeline/clips/tests/TESTS. |
| T-171 r3 hands | session_01NPjxeMcHygukqBoJYvRScz | t-171-claude-hands-r2 | working → CHECKPOINT. Also asked to look at planArmLift popping (from T-175). Everything stays opt-in until the owner sees the clip. |
| T-183 hair contact | session_01NPjxePoErf7PULMnNXPwQk | t-183-claude-hair-contact | design approved, implementing → CHECKPOINT. At merge: trailers for tests/test_secondary.cpp, test_hair_contact.py, release_rule.py, test_release_rule.py; TESTS line for test_hair_contact.py. |
| T-184 seated garments | session_01NPjxeP4GwcYbk72YAg7t9m | t-184-claude-seated-garments | design approved (opt-in "seated" key), implementing. Hands over as text: release_rule detector, TESTS line, GENERATOR_PINS row → apply at merge (after T-183, which owns release_rule.py / GENERATOR_PINS.md). Trailer for test_garments_seated.py. |
Archived today: T-155, T-171 r2, T-172, T-175 r1, T-177, T-178, T-179, T-180, T-181, T-182.

## Waiting for the owner (via the liaison)
1. T-175 r2 acceptance → merge as opt-in.
2. Global floor offset: both released packages rest 27–30 mm below the character origin (feet sink in every shot); a global
   fix changes every bake and golden → owner yes/no (T-175 compensates per shot meanwhile).
3. Ear look (T-183): keep-out only (current) vs hair fully tucked behind the ear.
4. P13: adopt a narrow LIGHT clone rule (code/docs tasks that never run the full suite) — the full suite needs the full
   checkout (docs/process/CLONE_PROFILES.md).
Deferred follow-ups: hair vs static masses/hand and hair vs environment (T-183); boy ankle hem vs hidden foot skin (T-184);
test_recipe needs commit ab9fd4c, unreachable at depth 1 (T-180); stack_specs.py docstring names the old allowlist (T-178).
