# T-132: candidate versions boy 2.3.0 / girl 0.14.0

Input `main @ 592d3b5`; branch `t-132-claude-versions`. Blender: bpy 5.3.0 via `/usr/local/bin/blender` (the
environment's shim; `tools/bpy_blender.py` is mode 644, so the regression tool cannot execute it).

**Published as CANDIDATES only** (`tools/version_switch.py --publish-only`). Approved pointers stay boy **2.2.0** /
girl **0.13.0** (`tools/check_assets.py`: PASS, base origin/main). `fidelity_baseline.json` and golden baselines are
untouched, and `--approve-published` was not run. `--identity-change-approved-by` cites OWNER_DECISIONS 2026-11-19
~15:10Z (hair and garment sections change).

## Specs (`make_specs.py`)
- `boy_yellow_hoodie.2.3.0.spec.json` = 2.2.0 + T-118 `hair_r5` (groom/4) + T-119 garments r3 (garment/3
  ankle_close; limb skin `skin-felt-limbs/3`, base 226/178/162 = the reference-hand match as accepted, not the 5 L*
  limb-region median) + T-121 `hands_r2/1`.
- `girl_auburn_bun_glasses.0.14.0.spec.json` = 0.13.0 + T-118 `hair_r5` + T-119 garments r3 (collar_seat,
  cuff_gather) + T-121 `hands_r2/1`. T-118 attachment rule: the flower stays seated on the bun (so it follows the
  bun's chain) and is turned towards the front quarter with `turn`.
- The overrides are deep-merged in that order (spec.deep_merge). Their own metadata is dropped. 2.2.0 / 0.13.0
  carry the same hair, clothing and materials as 2.1.0 / 0.12.0, the base the overrides were made on.
- All three ingredients are kept: no visible regression (see below). For the two guard tests that fail by
  construction, see Checks.

## Evidence
| | boy | girl |
|---|---|---|
| cheap preview (Cycles 2 spp) | [preview](boy_sheet/boy_preview.jpg) | [preview](girl_sheet/girl_preview.jpg) |
| strict sheet (T-087, Cycles 16 spp): reference, current, candidate, AI target | [boy_strict.jpg](boy_sheet/boy_strict.jpg) | [girl_strict.jpg](girl_sheet/girl_strict.jpg) |
| expressions (T-113 tooling, Cycles 12 spp): emotion set + lid rows | [boy_expressions_strict.jpg](boy_expressions_strict.jpg) | [girl_expressions_strict.jpg](girl_expressions_strict.jpg) |
| 100% crops (`crops.py`, Cycles 16 spp, 400 px tiles, unscaled), current \| candidate | [boy_crops_100.jpg](boy_crops_100.jpg): crown/whorl back-top, crown 3/4, ankle notch rest / toes up 25 / toes down 30, hand | [girl_crops_100.jpg](girl_crops_100.jpg): sweeps, curl ends, flower, collar rest / half / full reach, bloomer cuffs front / 3/4 back, hand |
| fidelity (publish-only) | [report](fidelity/boy_yellow_hoodie/report.md) | [report](fidelity/girl_auburn_bun_glasses/report.md) |

The strict sheets use the T-118 recipes (`*.recipe.json`) with baseline = current, candidate = the published
version. The girl recipe renders the master variant, as in T-118. The fidelity `sheets/` sit next to each
`report.md`, so its links resolve.

## Visual read (fidelity to the references over scores)
- **Boy 2.3.0: closer.**
  - Crown: taller and uneven, with staggered petals. The back shows tiered locks with dark channels from the whorl,
    as in val27 back / B05.
  - Ankle: the notch is closed at rest and through flexion (trouser cuff fabric inside the ragged hem, no skin).
  - Hands: separated fingers with rounded tips, and a pinker tone that sits better next to the cheek.
  - Face and expressions are unchanged against 2.2.0.
- **Girl 0.14.0: closer.**
  - Collar: seated on the neckline at rest, half reach and full reach (0.13.0 tears and flips at reach).
  - Bloomers: the cuffs are gathered bands.
  - Hair: the sweeps come lower over the forehead, the curl ends are staggered, and the flower is turned towards the
    front quarter.
  - Hands: separated fingers.
  - Expressions are unchanged against 0.13.0.
  - Watch point: at face height, the hair on the girl's left reads a little narrower in the expression camera.
- **Scores:** boy 69.53 (2.2.0: 67.25), girl 63.90 (0.13.0: 64.13). The girl's small drop is in the
  silhouette/mask terms; the visible gains (collar, cuffs, fingers, curl ends) are not scored.

## Checks (version_switch step 6)
- boy 12/14, girl 12/13 passed in the run.
- `pipeline/charsys/tests/test_hair_r5.py` FAIL on "no file under assets/characters pins groom/4". On the
  version_switch run, `test_hands_r2.py` 48/49 FAIL on "no character spec or candidate in assets/ sets body.hands".
  **Expected by construction.** These are the T-118 / T-121 opt-in isolation guards: any published version that adopts
  groom/4 or hands_r2 fails them. Supervisor decision (A): keep all three ingredients, tests unedited. The Supervisor
  narrows both guards at merge to exempt exactly these two owner-approved specs, as with the T-094 groom/3 guard.
- `pipeline/charsys/tests/test_store.py` (boy run) needs `renders/charsys/ref_1.0.0/build_report.json`, a git-ignored
  local reference build this checkout does not have (as in T-122). It needs a re-run where that build exists.
- "files outside this switch changed": only because the boy and girl switches ran in parallel, so each run saw the
  other's store files. Each listed file belongs to the other publish. The baseline file, the pointers and the golden
  root were unchanged in both runs.
- Blender test files are listed by version_switch and not run here (`test_garments_r3.py`, `test_face_v*`,
  determinism etc.); they need a Blender test session.
- Crops: the girl hand shot uses the master A-pose. With the arms-down pose, the girl's hand bounding box did not
  give a usable target, and the sleeve and vest covered the hand.

No test or threshold was changed. Nothing outside the T-132 write-set was written.
