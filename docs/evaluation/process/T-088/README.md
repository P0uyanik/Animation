# T-088: version-switch script (Phase A, round 2)

Branch `t-088-claude-version-switch` from `origin/main` at `ab9fd4c`. Task: [docs/tasks/T-088.md](../../../tasks/T-088.md).
Documentation: [ASSET_STORE.md, "Making a version current"](../../../process/ASSET_STORE.md).

## Result
Complete for the write-set; two follow-ups need files outside it (see "Open points").

- `tools/version_switch.py` (new): validate, build + publish, approve, fidelity baseline entry, golden baseline,
  checks, trailer block, in that order; `--dry-run` writes nothing.
- `tools/tests/test_version_switch.py` (new): 52 checks on a fixture repository in a temporary folder, with a fake
  runner standing in for Blender, fidelity and regression. The real repository is only read.
- `docs/process/ASSET_STORE.md`: one section.

## The 2026-11-18 inconsistencies and where they are now caught (step 1, before any write)
| 2026-11-18 problem | Check | Test case(s) |
| --- | --- | --- |
| Version spec refused by `tools/regression/tiers.py` | the would-be baseline entry goes through `tiers.character_config` on a scratch copy of the character's spec folder; its spec_version must equal `--version` | "spec name the gate refuses", "override changes spec_version" |
| `skin-felt/2` without a `presets/2` pin | every assignment's preset family (presets/1 library or the skin library's family) must be covered by the resolved `generators.materials` pin (`spec.validate` does not check this) | "skin-felt/2 without presets/2 pin", "... with presets/1 pin", accepted with the presets/2 pin |
| Missing golden regression baseline | step 5 writes it; step 1 refuses when the target exists, and when `metadata.spec_version` differs from `--version` (the golden folder is named by spec_version) | "golden baseline already there", "spec_version differs from --version" |
| Claim and approval timing | the task's claim (OWNERSHIP.md row or `docs/tasks/<task>.md` write-set, `tools/integrate.py`) must cover every predicted write; the owner decision must be given and its file must mention the version; identity changes need `--identity-change-approved-by` before the build, not at publish | "claim does not cover the writes", "no claim", "decision missing", "decision not recorded", "identity change without approval" |
| 8 to 18 per-file approval trailers | step 7 prints the exact `Supervisor-Approved:` block from `tools/guarded_paths.txt` for the files actually written | "exact trailer block for every guarded path written", dry-run "lists the predicted trailers" |

Also refused early: a published or reused version number, an unresolvable generator pin, inputs from another
character's folder, a wrong `identity.id`, a work folder inside a store, a missing `--blender` outside `--dry-run`.

## Tests run
| Command | Result |
| --- | --- |
| `python3 tools/tests/test_version_switch.py` | **52/52 PASS** ([output](test_version_switch.txt)) |
| `python3 tools/version_switch.py --character girl_auburn_bun_glasses --version 0.11.0 ... --dry-run` (real repo) | exit 1, refused as expected: already published, golden exists, claim does not cover ([output](dryrun_girl_0.11.0_refused.txt)) |
| the same for a hypothetical `0.12.0` (copy of the 0.11.0 spec with spec_version 0.12.0, a decision line and a widened claim) in a scratch git worktree outside the repository | exit 0, every step, command, file and the 16 predicted trailers ([output](dryrun_girl_0.12.0_scratch.txt)); the worktree was removed afterwards |
| `tools/check_cast.py`, `tools/check_assets.py`, `test_run_shot_current.py`, `test_versions.py`, `test_skin_presets.py`, `test_asset_store_guard.py`, `test_gate_tools.py`, `test_material_presets.py` (the step-6 plain-Python set, on this branch) | all exit 0 |
| `tools/check_doc_links.py` | exit 0 |

Not tested: a real (non-dry) switch with Blender. The task forbids publishing or approving a real version, and the
build, fidelity and regression tools are the existing ones, called with the arguments T-080/T-081 used. Blender was
not run.

## Baselines
No file under `assets/`, `docs/evaluation/characters/fidelity_baseline.json` or `docs/evaluation/regression/` changed
(`git diff --stat origin/main` lists only the write-set). The test checks that the real baseline and every store
`index.json` are byte-identical before and after it runs.

## Open points for the Supervisor
1. **Guarded path:** `tools/tests/test_version_switch.py` is a new test (`**/tests/`, `**/test_*.py`) and needs
   `Supervisor-Approved: tools/tests/test_version_switch.py`.
2. **Not run by the gate yet:** the test is not in `tools/check_all.py` `check_python_tests` (outside the write-set;
   guarded). Proposed one line: `[sys.executable, str(ROOT / "tools/tests/test_version_switch.py")],  # T-088`.
3. Step 6 lists tests that name the character but take `--blender` or import bpy (for the girl: `test_determinism`,
   `test_export_determinism`, `test_face_v2`, `test_face_v2_socket_wall`, `test_garment_details`); they are printed
   for a separate run, not run, because their arguments differ per test.
4. A switch that fails after the publish cannot roll back (published versions are immutable by design); the tool
   lists what was written and stops.
