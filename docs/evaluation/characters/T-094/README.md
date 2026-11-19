# T-094: boy 2.1.0 and girl 0.12.0, published but not current

Input SHA `4874ef7` (`integration/t-094`), claim widened by the Supervisor at `575d9b0` (store `index.json`, candidate
entries and history only). Branch `t-094-claude-versions`. Blender: the **bpy 5.3.0 module** (Python 3.13) behind
`tools/bpy_blender.py` (no Blender binary in the cloud container). Owner authority: `docs/process/OWNER_DECISIONS.md`
2026-11-18 (T-092 ~19:20Z; T-089 + T-093 ~22:35Z; Phase D ~22:50Z; standing approval ~23:10Z: "build and publish
boy 2.1.0 and girl 0.12.0 … leave the current pointers on boy 2.0.0 / girl 0.11.0 until the owner has seen the result").

**Status: both versions published as `candidate`. Nothing is approved; the current pointers stay on boy 2.0.0 and
girl 0.11.0; `fidelity_baseline.json` and the golden baselines are unchanged.** The owner decides on the sheets below.

## Owner evidence
| | boy 2.0.0 → 2.1.0 | girl 0.11.0 → 0.12.0 |
|---|---|---|
| T-087 strict sheet (Cycles 16 spp, 360 px; reference \| current \| new \| AI target) | [boy_sheet/boy_2.0.0_vs_2.1.0_strict.jpg](boy_sheet/boy_2.0.0_vs_2.1.0_strict.jpg) | [girl_sheet/girl_0.11.0_vs_0.12.0_strict.jpg](girl_sheet/girl_0.11.0_vs_0.12.0_strict.jpg) |
| cheap preview (Cycles 2 spp, 120 px; not for approval) | [boy_sheet/…_preview.jpg](boy_sheet/boy_2.0.0_vs_2.1.0_preview.jpg) | [girl_sheet/…_preview.jpg](girl_sheet/girl_0.11.0_vs_0.12.0_preview.jpg) |
| recipe | [boy_2.0.0_vs_2.1.0.recipe.json](boy_2.0.0_vs_2.1.0.recipe.json) | [girl_0.11.0_vs_0.12.0.recipe.json](girl_0.11.0_vs_0.12.0.recipe.json) |
| fidelity (`tools/fidelity`, baseline render settings 640 px / 32 spp) | **67.7245** (2.0.0: 67.6344) | **65.0136** (0.11.0: 62.2949) |
| e907 exchange re-render | see [exchange/](exchange/) | same shot |

The sheets' candidate column is built from the version spec at `1c3ba1e` by the recipe tool. The published versions were
built from the same spec file (unchanged since), deterministic build environment; the manifests' `spec_sha256` are
`d70f55c6…` (boy) and `7977c736…` (girl).

## What the versions contain (`make_specs.py`, reproducible; `--check` compares)
Both are complete monolithic specs derived from the current approved spec plus the approved candidates:

| | boy 2.1.0 (from 2.0.0) | girl 0.12.0 (from 0.11.0) |
|---|---|---|
| face | T-089b `boy_face3b` (face_generic/3, sleepy heavy lids at the T-089 eye size) | T-089b `girl_face3b` (rounder, fuller face, wider eyes, socket corner relax) |
| hair | T-091 `hair_r4` (groom/3) | T-091 `hair_r4` (groom/3) + T-093's single pink flower |
| garments + materials | T-093 `T-093+T-092.combined` (garment/2: B06 flap backpack, felt drawstrings, sneakers; presets/3 hoodie fleece/3, trouser pile/3, skin-felt/3) | T-093b `T-093b+T-092.combined` (garment/2 + leg split; presets/3 vest felt/3, brushed cotton/3, cuff fleece/3, skin-felt/3) |
| pins | face_generic/3, groom/3, garment/2, **materials presets/3** (T-092 README: T-094 sets it) | same |

Decisions made in the merge:
- **Directional fibres: off.** The T-091 strict sheets were rendered without them ("Left off in the main candidates").
- **Boy garments: T-093, not T-093b.** T-093b dropped the T-090b trousers/shoes variant; the boy keeps T-093.
- **Girl hair accessories:** the girl's T-093b combined override also changes two hair structures. `flowers` (one
  pink felt flower) is taken from it: owner design point 2026-11-18, "blue-grey scrunchie with one pink felt
  flower". Its `band` (the retuned old tie) is **not** taken, because T-091's gathered scrunchie replaces the tie
  under the same `band` name and `hair_band` slot. `hair.components` (description text) is taken from T-093.
- Identity (`identity`, `proportions`) unchanged. Face, hair, clothing and materials change (approved systems), so
  the publish carries `--identity-change-approved-by` citing the decisions above.

## Visual review (strict sheets against the original references)
**Boy 2.1.0: clearly closer.**
- Fringe comes down to the brows as clumps; heavy sleepy lids at the larger eye size read like hero24/val27 (face rows).
- Navy flap backpack (B06), plain felt drawstrings with dark tips, warmer skin, more even hoodie fleece.
- Remaining gaps: the crown is less tall and less irregular than val27. The hair outline is a little wider at the
  temples. The fringe clumps are less separated than the reference's.

**Girl 0.12.0: closer, with open deviations.**
- Rounder face and wider, rounder eyes (face rows nearer ref_30). Centre part with swept sections. Narrower
  silhouette. Ringlets grow out of the back sections (back row nearer sheet30_back). Bloomer leg split visible.
  Cream fleece boot cuffs (G08, owner-accepted).
- **Deviation: forehead.** The face-front crop shows a bare forehead below the centre part. ref_30 has hair sweeping
  over its sides. This was open since T-091 and is not fixed here; it is a hair-round item, not a T-094 merge issue.
- **Deviation: flower.** The single flower sits at the side/back of the bun, so the front view shows none. sheet30
  front shows the flowers at the upper right of the bun. The placement comes from T-093 (`around_deg` 55).
- The gathered scrunchie reads slightly beaded from the back. The reference band is smoother.

## Tool change: `tools/version_switch.py`
- `preset_family()` now asks `materials.builder.preset_family()`, so presets/1, presets/2 (skin) and presets/3
  (T-092) ids resolve exactly as the build resolves them. A presets/3 id needs `generators.materials = presets/3`.
- `--publish-only`: validate, build, publish (status `candidate`), fidelity score →
  `docs/evaluation/characters/<task>/fidelity/<id>/` (with the current score next to it), checks, trailers. No
  approve, no `fidelity_baseline.json` change, no golden baseline. The before/after snapshot covers the whole
  baseline file, the store pointers and existing version entries, and the whole golden root. Documented in
  `docs/process/ASSET_STORE.md`.
- Existing behaviour unchanged (the 52 original tests pass unchanged).

## Checks
| check | result |
|---|---|
| `python3 tools/tests/test_version_switch.py` | 75/75 PASS (52 existing + 23 new: presets/3, publish-only) |
| `version_switch.py --publish-only` boy / girl, built-in checks | publish, score OK; checks 7/11 and 9/10, failures below |
| `python3 tools/check_cast.py --base origin/main` | PASS (8 shots; T-094 exchange copy pins via `legacy_reason`, see below) |
| `python3 tools/check_assets.py` | PASS (2 stores) |
| `asset_store.py verify` 2.1.0 / 0.12.0 | ok / ok |
| `index.json` diff | additions only (new version entry + publish history); pointers unchanged |
| `fidelity_baseline.json`, goldens | byte-identical (sha256 before/after; no new golden folder) |

After merging `origin/main` (659b6a9: the T-097-boy/girl acting profiles and the Supervisor's fix of the
`test_hair_r4` guard), these plain checks were rerun on the branch: `test_hair_r4` 37/37, `test_version_switch`
75/75, `test_run_shot_current`, `test_versions` 105/105, `test_skin_presets` 24/24, `test_asset_store_guard` 33/33,
`test_gate_tools`, `test_materials_r2` 104/104, `check_cast` and `check_assets`: all PASS.

Failures during the publish runs (before that merge):
- `pipeline/charsys/tests/test_hair_r4.py` 36/37: its guard "no published spec or override outside candidates/
  pins groom/3" saw the two new version specs. The test is outside the T-094 write-set, so I reported it. The
  Supervisor narrowed it on main to the approved spec (37/37 after the merge).
- `pipeline/charsys/tests/test_store.py`: needs an untracked local render `renders/charsys/ref_1.0.0`; unrelated to
  T-094 (environment).
- In the boy run only: `check_cast.py` and `test_run_shot_current.py` failed on my first exchange copy, which pinned
  the not-current version without a reason and was then missing the girl version. Fixed with `legacy_reason`; both
  pass in the girl run and afterwards.

Not run: the Blender tests that name the characters (listed by version_switch; they test systems already merged
and gated), the full `tools/check_all.py` gate, and C++ ctest (no C++ change).

## Exchange
See `exchange/README.md`.
