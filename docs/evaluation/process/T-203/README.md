# T-203: `TESTS` manifests renamed to `TESTS.manifest`

**Problem.** The T-182 per-directory manifests were files named `TESTS`. In three directories (`pipeline/clips`,
`tools/cleanup`, `tools/motion_checks`) a sibling folder `tests/` exists, so on a case-insensitive Windows checkout
`TESTS` and `tests/` collide and git shows the manifests as deleted.

**Change (only this).**

- All 19 manifests moved with `git mv` to `<same dir>/TESTS.manifest`. Content is byte for byte unchanged
  (`git diff -M --cached --summary`: 19 renames, all 100%).
- `tools/check_all.py`: `TEST_MANIFEST_NAME = "TESTS.manifest"`; everything that derives from it (registry scan,
  `is_addable_test`, the "a manifest edit is free only if it appends" guard) follows. `tools/ready.py`,
  `tools/tests/test_task_kit.py`, `tools/tests/test_test_registry.py`, `docs/process/GATE.md` §1.2 updated.
- **No silent fallback.** A plain `TESTS` file anywhere makes the registry check (the "Python tests" step) FAIL:
  `<path>: a plain 'TESTS' file is not a manifest ... rename it to <path>.manifest (use TESTS.manifest)`.
- **Case-collision check.** The same step fails if two tracked paths (files, or a file vs. a folder of another
  spelling) differ only by letter case, listing each pair (`a/README.md <-> a/Readme.md`, `TESTS <-> tests`).
  It runs inside the registry check, so the 10-line gate summary is unchanged.
- Tests (`tools/tests/test_test_registry.py`, `test_legacy_name_and_case`): plain `TESTS` fails and names
  `TESTS.manifest`; a `TESTS` file beside a `tests/` folder fails both rules; case pairs listed; two test files
  differing only by case fail; distinct names pass.

**Registry before/after** (`check_all.test_registry()`, every entry compared by manifest, line, kind, path, args):

| | entries | run | blender | via | local | problems |
| --- | --- | --- | --- | --- | --- | --- |
| before (`TESTS`) | 87 | 38 | 22 | 10 | 17 | 0 |
| after (`TESTS.manifest`) | 87 | 38 | 22 | 10 | 17 | 0 |

The entry lists are identical (manifest names normalised).

**Not touched (outside the write-set).** `tools/guarded_paths.txt` line 18 is a comment that still says "TESTS
manifest"; no pattern there names the file. Historical docs (TASK_LOG, handovers, T-182/T-184 evaluation READMEs)
keep the old name on purpose.

**Guarded paths for the READY trailers:** all 19 `*/TESTS.manifest` paths (new names), the 19 old `*/TESTS` paths
(deleted), `tools/check_all.py`, `tools/ready.py`.
