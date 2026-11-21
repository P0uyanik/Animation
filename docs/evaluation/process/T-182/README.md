# T-182 — test registry from per-directory manifests

Owner decision 2026-11-21 ~11:20Z (T-176 proposal 7); owner approval typed in the T-182 session ~12:19Z. Rule text:
[GATE.md §1.2](../../../process/GATE.md).

## What changed

- `tools/check_all.py`: the 33-command Python test list (32 lines + the conditional `tools/cleanup/run_tests.py`)
  is gone; "Python tests" runs every `run` entry of the `TESTS` manifests, sorted by path. The registry check
  (`test_registry`) fails the step if any `test_*.py` / `*_test.py` outside `docs/` is in no manifest, is listed twice,
  is listed but missing, names an unknown Blender unit or runner, or shares a module name with another test.
- Guard (`check_guarded`): a new test source or `TESTS` file, or an append-only `TESTS` edit whose new entries are
  files the same change adds, needs no trailer if it matches only `TEST_GUARD_PATTERNS`. Everything else is
  unchanged.
- Found and fixed while testing: `changed_paths`, `dirty_paths` and the write-set diff used git's default rename
  detection, so `git mv` of a guarded file listed only the NEW path. The old path escaped the guard and the
  write-set. All three now use `--no-renames`.
- `tools/ready.py`: the new-test check also accepts manifest registration, and still reads the old registries.
- 18 manifests with 83 entries: run 34 (33 pre-T-182 + this task's test), blender 22, via 10, local 17.

## Same tests before and after (acceptance 1)

[commands_before.txt](commands_before.txt) is the list in `check_all.py` at b87fbfd.
[commands_after.txt](commands_after.txt) is the manifest `run` entries before this task's own test was added.
`diff` shows them identical: 33 == 33, no duplicates. `test_repository` in the new test asserts on every run that no
command from `commands_before.txt` is dropped.

The Blender units are unchanged in code: same ids, commands and shard plan. Their files are listed as `blender`
entries.

`local` entries were not run by the gate before T-182, and they still are not:

- 10 need Blender.
- 7 are plain Python: `test_hair_v3*.py` (3), `tools/motion_checks/**` (2), `tools/perf_extract/tests/test_extraction.py`
  and `tools/review/tests/test_readability.py`. These are candidates for `run`; that is left to the Supervisor.

## Negative tests (acceptance 2, 3): `tools/tests/test_test_registry.py`

The guard cases run against scratch git repositories with the real `tools/guarded_paths.txt`.

- **Passes without a trailer:**
  - add a test and append its entry;
  - add a new directory with a new manifest.
- **Needs the trailer:**
  - modify a test;
  - rename a test, even with unchanged content;
  - delete a test plus its line;
  - remove a manifest line only;
  - change a manifest entry;
  - insert a line before existing lines;
  - append an entry for a file the change does not add;
  - add a helper or shadowing module (`json.py`) or test data;
  - add a test under `tools/regression/` or `engine/render/`;
  - leave a new test uncommitted.
- **A modified test with a trailer passes.**
- **Registry:**
  - a test on disk in no manifest fails, including an untracked one;
  - a duplicate entry, a dangling entry, an unknown unit, an unknown runner or a duplicate module name each fail;
  - `..` and absolute paths are rejected.

## Open

- `tools/tests/test_task_kit.py:57-58` asserted its own path appears in `check_all.py`; changed (2 lines, Supervisor
  approved, needs trailer) to check `tools/tests/TESTS`.
- C++ tests stay in `tests/CMakeLists.txt`. Adding one edits that existing file, which needs a trailer.
