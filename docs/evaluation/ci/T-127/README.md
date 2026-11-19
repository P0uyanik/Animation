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

## (b) Probe commits, (c) two green runs, (d) wall-clock and runner minutes

See the sections below (filled from the CI runs).
