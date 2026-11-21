# T-181: `claims --check-all`

`python tools/integrate.py claims --check-all` checks the whole OWNERSHIP table (exit 1 on any failure):
- write-set overlap between any two rows (`globs_overlap`); depends-on stays a warning as in `--check`;
- any write-set cell with text outside back-ticked globs and separators (`,` `;` whitespace), e.g. `(walk/sit/stand only)`.

Also: one step in the docs-only fast-path job (`.github/workflows/checks.yml`); test `test_claims_check_all` in
`tools/regression/tests/test_gate_tools.py` (disjoint passes, overlap fails, qualifier fails, live table: overlap only).

Live OWNERSHIP.md at input b9c0d4e: 0 overlaps; qualifier text in T-175 ("(walk/sit/stand only)",
"(one plush_anim source line)"), T-171 ("(final list in its first STATUS)"), T-178 ("(test registration only)").
`--check-all` exits 1 on the live file until the Supervisor cleans these rows.

T-181b: a depends-on (read) overlap with another task's write-set is a WARN naming that task and both globs, not a conflict (`--check`, `--check-all`); write-set overlaps and shared version bumps still fail.
