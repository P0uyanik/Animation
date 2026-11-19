# T-132: candidate versions boy 2.3.0 / girl 0.14.0 (WORK IN PROGRESS)

Input `main @ 592d3b5`; branch `t-132-claude-versions`. Blender: bpy 5.3.0 via `/usr/local/bin/blender` (the
environment's shim; `tools/bpy_blender.py` is mode 644).

**Status: published as CANDIDATES only; waiting for a Supervisor decision (A/B below).** Approved pointers stay boy
**2.2.0** / girl **0.13.0**. `fidelity_baseline.json` and the goldens are unchanged, and `--approve-published` was not run.

## Specs (`make_specs.py`)
- `boy_yellow_hoodie.2.3.0.spec.json` = 2.2.0 + T-118 `hair_r5` (groom/4) + T-119 garments r3 (ankle_close; limb skin
  `skin-felt-limbs/3`, base 226/178/162 = the reference-hand match as accepted) + T-121 `hands_r2/1`.
- `girl_auburn_bun_glasses.0.14.0.spec.json` = 0.13.0 + T-118 `hair_r5` (the flower stays on the bun, turned with
  `turn`: the T-118 attachment rule) + T-119 garments r3 (collar_seat, cuff_gather) + T-121 `hands_r2/1`.
- The overrides are deep-merged in that order. 2.2.0 / 0.13.0 have the same hair, clothing and materials as
  2.1.0 / 0.12.0 (the T-118 / T-119 base), so the overrides apply unchanged.

## Fidelity (publish-only)
boy 69.53 (2.2.0: 67.25) · girl 63.90 (0.13.0: 64.13). Reports: [boy](fidelity/boy_yellow_hoodie/report.md),
[girl](fidelity/girl_auburn_bun_glasses/report.md).

## Checks (version_switch step 6): open decision
- `test_hair_r5.py` FAIL: "no file under assets/characters pins groom/4". `test_hands_r2.py` FAIL (48/49): "no character
  spec or candidate in assets/ sets body.hands". These are T-118 / T-121 opt-in guards, and any published version that
  adopts these ingredients fails them. Both files are outside the write-set, and test changes are forbidden.
  Read literally, the task rule drops hair r5 and hands_r2 (option B). Option A, recommended: keep all three and have
  the Supervisor update the two guards. Reported to the Supervisor; this README is updated after the decision.
- `test_store.py` (boy) needs the git-ignored `renders/charsys/ref_1.0.0/build_report.json` (as in T-122).
- The "files outside this switch changed" note appears only because the boy and girl switches ran in parallel.

## Evidence (in progress)
Recipes: `boy_2.2.0_vs_2.3.0.recipe.json`, `girl_0.13.0_vs_0.14.0.recipe.json` (previews passed). The strict sheets,
100% crops (`crops.py` / `compose_crops.py`) and expression sheets (T-113 tooling) are rendering.
