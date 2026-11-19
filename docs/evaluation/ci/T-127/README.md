# T-127 evidence: CI speed without loss of quality

Input `integration/t-127-prep @ 6016b1b`, branch `t-127-claude-ci-speed`. Items 1-5 approved; item 6 (reusing built
characters between tests) not approved and not done: every unit builds its own characters.

## (a) Before/after inventory — `inventory.json`

`python tools/ci/blender_inventory.py --out docs/evaluation/ci/T-127/inventory.json` (dry run, no Blender: every
command recorded with normalised paths; also run in CI by `tools/ci/tests/test_t127_shards.py`).

| tier | commands before (6016b1b, one runner) | after (5 shards) | same set + arguments | unsharded fallback identical incl. order |
| --- | ---: | ---: | --- | --- |
| full | 20 | 20 | yes | yes |
| fast | 20 | 20 | yes | yes |

The other checks (frozen, guarded, write-set, lint, C++ build, CTest, plush_tests, animcheck, Python tests, links,
renderer, per-character regression) are unchanged code and still run in the same jobs; the Python test list gains one
entry (`tools/ci/tests/test_t127_shards.py`), none removed. Thresholds, goldens and required checks are untouched.

## (b) Probe commits (throwaway `probe/t-127-*` branches, never merged; production code broken, no test touched)

Each probe adds the `probe/t-127-*` push trigger on its own branch only. "Guarded paths" is red on every probe (T-127's
own guarded files); the table lists the line the probe itself turns red.

| probe | run | red line from the probe |
| --- | --- | --- |
| `probe/t-127-blender` 0e2b49a: `verify_charsys` exits 1 | 44543943625 | FAIL Blender tier, shard 1/5: verify_charsys, boy fingerprint, face tests |
| `probe/t-127-cpp` 0acc571: `sqr()` returns x*x+1 | 44543950834 | FAIL C++ tests (renderer-ON ctest) |
| `probe/t-127-python` f8762e8: fidelity `compare_score` flag inverted | 44543956710 | FAIL Python tests: test_ci.py |
| `probe/t-127-regression2-sharded` b0c6d4c: `geom.uv_sphere` radius x1.001 | 44548402872 | FAIL regression boy + auburn girl (fingerprint/export/renders vs origin/main); FAIL Blender tier shard 1 (boy fingerprint) |
| `probe/t-127-regression2-unsharded` d2a4f1e: same, `[unsharded]` (old path) | 44548408522 | identical FAIL lines: the new path catches exactly what the old path catches |

Findings: `probe/t-127-regression` feed43b (default `segments` 48 -> 40) stayed green because every caller of
`geom.uv_sphere` passes explicit segments, so it changed no geometry (a no-op probe, not a detection gap). The C++
probe is caught only by the renderer-ON ctest; the renderer-OFF `plush_tests` in the linux gate do not cover `sqr()`.
That coverage gap predates T-127 (no C++ job changed) and is reported as a follow-up.

## (c) Two consecutive runs on the same commit

Run 44544365213 on 9b5f905, attempt 1 and attempt 2 (re-run): every test check PASS both times (Blender tier in all
5 shards, regression for all 3 characters, Frozen, Write-set, lint, C++ build, C++ tests, Python tests and links).
Red only: Guarded paths (T-127 edits guarded files; Supervisor approval trailer at merge) and Merge status (derived).

## (d) Wall clock and runner minutes (job start to end, from the Actions API; billable minutes report 0)

| | baseline 44508054856 (integration/t-113, pre-T-127) | 9b5f905 attempt 2 |
| --- | ---: | ---: |
| wall clock | 45.3 min | 17.0 min |
| runner minutes (sum of jobs) | 82.2 (7 jobs) | 81.0 (12 jobs) |
| linux gate job | 44.5 (install 5.1, Gate 38.7) | 7.7 (install 0.7, Gate 6.5) |
| longest job now | linux gate 44.5 | blender shard 4: 16.2 (garment_generic_test alone 15.6, one command) |
| regression boy / auburn | 13.4 / 14.2 | 14.1 / 14.5 |

Same-load comparison (both probe runs started 14:52 under the same runner contention): sharded 28 min, old path
44 min. Runner minutes stay about equal: the shards add 5 job set-ups and installs, the apt cache removes about
4.5 min of mirror install per C++ job. The new critical path is garment_generic_test (shard 4) and the per-character
regression jobs (about 14 min each, unchanged by T-127).

Caches: apt cache hit on the primary key `apt-cpp-<image>-<hash>` (install 0.3-0.7 min instead of 5.1, no mirror
contact). ccache per run (after `ccache -z`, T-128 §2c): attempt 2 of 9b5f905 reports 52/52 hits (100 %); that is a
re-run of the same commit restoring its own cache. A first push of a new commit restores the newest older cache of
the branch and is not measured here (follow-up: record it on the next task-branch push).

## Follow-ups (not in T-127)

- C++: no renderer-OFF test covers `engine/core/math.h` `sqr()` (caught only by the renderer-ON job).
- ccache: measure the hit rate on the first run of a new commit with the per-run statistics.
- Probe trigger: probes need the `probe/t-127-*` trigger on their own branch; a permanent `probe/**` trigger was not added.
