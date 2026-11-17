# T-056: order-stable, byte-reproducible engine export

Branch `t-056-claude-export-determinism` (from `origin/staging` d350f1d). Blender: bpy 5.3.0 module (Python 3.13)
through `tools/bpy_blender.py`; C++: Ubuntu 24.04 apt embree 4.3.0 / glm / nlohmann-json, OIDN 2.3.3 (prebuilt
release archive; without it the frozen image regressions miss by RMSE 0.04-0.05 on this machine, see §6).

## 1. Task and result
Make two clean builds + exports of every character produce byte-identical engine packages, with no visible change.
**Result: complete.** New exporter version **export/5** (registered; released export/4 is unchanged byte for byte).
3 consecutive clean build+export runs per character with export/5 are byte-identical (`geometry.bin` and
`character.json`), fingerprints equal staging's, the engine bakes e904 identically.

## 2. Where the variation comes from (evidence: `evidence/source_of_variation.json`)
* Exporting one master twice is byte-identical: the exporter was deterministic. All variation is in the **built
  master**, which `fingerprint_v2` (order-independent) does not see.
* Two clean builds at staging store some meshes with their **polygons in another order** (boy: buckles, eyes, lids,
  hood_back, undershirt; girl: eyes, lids, garment buttons/soles/pockets/embroidery) and the ears and some lids with
  their **vertices in another order** plus **1-2 float32 ulps of noise** (<= 6e-8 m) on a few coordinates. All
  affected meshes are made with applied SUBSURF/SOLIDIFY modifiers (`face_generic.py`, `body_v6.py`,
  `garments/generator.py`); the bpy module ignores `-t 1`, so Blender's threaded modifier code is the likely origin
  (not proven further: the builders are outside this task's write-set and `body_v6.py` is frozen).
* **Skin weights:** the boy's `hood_back` automatic weights (`body_v6.py`, `parent_set(type="ARMATURE_AUTO")`)
  differ by up to 1.8e-7 in 1125 values between builds.
* **Morph deltas:** lid shape keys carry ulp noise (girl: ~58 components per build pair, <= 1.1e-7 m).
* **hair_clumps** (T-041's CI observation): not reproduced. In every build here (2 staging + 8 export/5 builds of the
  boy) all `hair_*` meshes export identically, also with export/4. `hair.py` got T-038b's fix (186f779, canonical
  hair_mass topology) on staging, which matches T-041's observation predating it. Nothing to report against
  `hair.py`.
* `source.blend_sha256` in the manifest hashes `.blend` bytes, which are never reproducible.

The builders are the root cause, and changing them is outside this task. So export/5 removes the dependence on that
order and noise at export time, and keeps everything else the same.

## 3. What export/5 does (`pipeline/charsys/export_engine.py`)
Selected by the pinned exporter version (`generators.exporter`). An unpinned spec still resolves to export/4
(frozen legacy default), and export/4 runs its released code path. Masters without an embedded spec (test data)
export as export/5, the default for new exports.

| Item | export/5 rule | Max change vs export/4 (measured) |
| --- | --- | --- |
| positions | rounded to 2^-15 m (30.5 µm grid) | 15.3 µm |
| morph deltas | rounded to 2^-14 m (61 µm grid). A vertex is listed when its rounded delta is not 0 | 30.5 µm. No vertex with a delta > 31 µm dropped |
| skin weights | multiples of 1/1024, exact integer sum 1; influences ordered by (weight desc, joint); empty slot = joint 0 | 1.4e-3 of an influence |
| vertex order | canonical rank per object: (rounded position, joints, weights, rounded deltas in shape-key order); exact ties split by colour refinement over the polygon graph (no ties left in either character) | none (reorder) |
| triangles | Blender's split kept (quads/n-gons keep the build's start corner); each triangle rotated to its lowest index, list sorted | triangle sets identical |
| normals | Blender's own rule on temporary meshes in canonical order: from the rounded positions where within 2° of the unrounded result (noise-free), else the unrounded result (near-degenerate garment spots, where rounding first would turn normals up to 170°) | ≤ 2.0° (boy: 0 vertices > 2°, 151 > 1°; girl: 0 > 2°, 3666 > 1° of 320 326) |
| eye pivots | sphere fit on the sorted points | identical |
| manifest | `source.blend_sha256` left out; `exporter_version` "5" | all other keys identical |

Why these grids: a value whose build-to-build noise crosses a rounding midpoint still differs. Rounding cannot remove
that risk, only make it unlikely. Over 7 masters per character (`evidence/noise_and_grids.json`), the expected number
of such crossings per pair of builds is ≤ 0.009 (positions), ≤ 0.016 (deltas) and ≤ 0.015 (weights) per character
with the chosen grids. With 2^-17 (the first choice) it was 0.06-0.12, and a real crossing happened: an earlier
3-run proof failed on one byte of a girl lid "Laugh" delta. The grids are powers of two (exact in float32). Every
change is below 0.03 px at 1080p for a ~1 m character. A future geometry can still land a noisy value on a midpoint;
`test_export_determinism.py --characters` detects it.

Also handled: `-0.0` vs `+0.0` after rounding (it cost one byte in a boy Blink delta in an earlier proof run).

Versioning (`docs/CHARACTER_SYSTEM_VERSIONS.md` path A): `versions.py` gains one appended line
(`export/5`). `EXPORTER_VERSION = "4"` stays, because it is run_shot's cache key and the legacy default that
`test_versions` ties to `LEGACY_EXPORTER`. A master pinning export/5 never had an export/4 package, so the cache
cannot serve a stale one. The manifest's `exporter_version` records the version actually written.

## 4. Files changed
* `pipeline/charsys/export_engine.py`: export/5 path (canonical rank, polygons, Blender normals on canonical
  copies, rounding, weights, triangles, manifest), version dispatch, constants.
* `pipeline/charsys/versions.py`: one appended registration line `export/5`.
* `pipeline/charsys/tests/test_export_determinism.py` (new): quick mode (toy fixture: two exports identical; a
  scrambled master with shuffled vertices/polygons, rotated triangle starts and 1-ulp noise on positions, shape keys
  and weights exports to identical bytes; export/5 content rules). Full mode (`--characters boy,girl --runs 3`):
  clean builds pinned to export/5, fingerprints and package bytes compared.
* **Outside the write-set (required by the registration):** `pipeline/charsys/tests/test_versions.py`. The single
  assertion "export/4 is the only released exporter" now expects export/4 and export/5. This updates an expectation
  that registering any new exporter must change; nothing is weakened (67/67 PASS).
* Docs/evidence: `docs/evaluation/characters/T-056/README.md` (this), `compare_v4_v5.py` (export/4 vs export/5
  content comparison tool), `exporter5.override.json` (pins export/5 for proofs; not used by any character),
  `evidence/*`.

## 5. Tests (exact commands; results)
* Quick determinism: `python3 pipeline/charsys/tests/test_export_determinism.py --blender <bpy wrapper>`. **15/15
  PASS.** The same test run against origin/staging's exporter fails 7 of 15, including both scrambled-master checks.
* **3-run proof** (`... --out <dir> --characters boy --runs 3` and `--characters girl --runs 3`): **23/23 PASS each**
  (`evidence/proof_*_3runs.json`):
  * boy: `geometry.bin` d0d568bd5a3d9485…, `character.json` 4d010aeb5ceed5fb…, all 3 runs.
  * girl: `geometry.bin` 18d29adf65958662…, `character.json` 8e23dbd90c71a53b…, all 3 runs.
  * The same hashes come from 5 further masters per character (2 earlier export/5 builds + 3 from an earlier proof
    run) exported with the final code: 8 builds per character, 1 package each.
* Fingerprints (fingerprint_v2, 0.01 mm): boy d407ad84a25176dd and girl 13f4e0a684d1ae6a, identical for the 2
  origin/staging builds and the 3 export/5-pinned builds (the pin changes no geometry).
* export/4 unchanged: origin/staging's exporter vs this branch on 3 masters (staging boy, staging girl, published
  boy 1.0.0). All 6 files byte-identical (`evidence/export4_unchanged.json`).
* export/4 vs export/5 content (`compare_v4_v5.py`): matched per vertex. Numbers in §3; skeleton, eye pivots, morph
  sets, materials, retarget, dynamics and capabilities identical (`evidence/compare_v4_v5_*.json`).
* Engine: e904 s010 (girl + dynamics, frames 1-48) `run_shot.py --stages prepare,bake` with export/4 and export/5
  packages. **bake.json identical** apart from the package path. Engine preview frame 24: export/4 twice
  byte-identical; export/4 vs export/5 RMSE 0.0019 (CTest image-regression limit 0.03), isolated speckles only
  (`evidence/e904_bake_and_preview.json`, `evidence/e904_f24_export4_export5_diffx8.png`).
* `python3 pipeline/charsys/tests/test_versions.py`: 67/67 PASS.
* `python3 pipeline/charsys/tests/test_export_engine.py --blender …`: 13/13 PASS.
* `ctest` (build/, OIDN 2.3.3): 4/4 PASS. `build/tests/plush_tests`: 78/78 test cases PASS.
* Full gate after `git merge origin/staging`: all checks PASS except the Guarded-paths approval (§9).

Not tested: Windows; a real Blender 5.3 binary (only the bpy module); shots other than e904 s010 with export/5
packages; the girl's T-055 spec work (untouched).

## 6. Baselines
No frozen file, character spec, asset, committed package or C++ file is touched. export/4 output (what both
characters and every shot use today) is byte-identical to staging's. CTest image regressions: PASS with OIDN. Without
OIDN, `regression_milestone01` (RMSE 0.046) and `regression_face_neutral` (0.041) fail on this machine with or
without this branch, since no engine code changed.

## 7. Visual results
Not a look change. export/5 output differs from export/4 by at most 15 µm (positions), 31 µm (morphs), 1.4e-3
(weights) and 2° (normals). The engine preview differs by RMSE 0.0019 (sampling speckle from the new vertex and
triangle order), and the bake is identical. Final renders come from the Blender master, which is unchanged.

## 8. Problems, limitations, questions for the Supervisor
1. **Existing characters still export with export/4** (unpinned specs resolve to the frozen default). For a
   byte-level unchanged-character guard (DELIVERY_PLAN §5.2), they need export/5. That is a path-B pin bump per
   character (new spec version with `generators.exporter: export/5`, owner approval), or the guard builds with
   `exporter5.override.json` as this proof does. Decision needed.
2. `docs/CHARACTER_SYSTEM_VERSIONS.md` (outside the write-set) should list export/5 in "Registered versions" (exporter:
   `export/1-3 (retired), export/4, export/5`) and say that new specs should pin `export/5`. Not edited here.
3. `test_versions.py` edited outside the write-set (one assertion, §4). Needs Supervisor acknowledgement.
4. Residual risk: rounding cannot make noisy inputs deterministic, only unlikely to differ (§3). The real fix is in
   the builders (polygon/vertex order and ulp noise after applied SUBSURF/SOLIDIFY, automatic weights in frozen
   `body_v6.py`). Suggested follow-up: canonical topology after modifier application in `face_generic.py` /
   `garments/generator.py` (as T-038b did for hair).
5. export/5 keeps the build's quad/n-gon start corners (they decide Blender's quad split). They were stable in every
   observed build. If a builder ever rotates them, export/5 output changes and the full-mode test reports it.

## 9. Gate
After `git merge origin/staging` (54f003b, clean), `PLUSH_OIDN_ROOT=<oidn 2.3.3> python3 tools/check_all.py --base
origin/main --blender <bpy wrapper>` (foreground wait):

```
PASS Frozen assets
FAIL Guarded paths: REQUIRES SUPERVISOR APPROVAL: pipeline/charsys/tests/test_export_determinism.py,
     pipeline/charsys/tests/test_versions.py
PASS Shared-systems lint
PASS C++ build
PASS CTest
PASS plush_tests
PASS Python tests
PASS Documentation links
PASS Blender tier  (verify_charsys, boy fingerprint, build determinism, test_export_engine, face tests,
                    hair/groom test, groom_generic_test, garment_generic_test, material presets: all PASS)
```

The only FAIL is the approval gate: every test source is guarded (`tools/guarded_paths.txt`: `**/tests/`), so the new
test (in the task's write-set) and the one-line `test_versions.py` update need `Supervisor-Approved: <path>` commit
trailers. The Implementer may not write those. Everything else passes.

## 10. Resource use
Token usage: not available. Repeated work: the 3-run proof ran three times (two runs caught real determinism
defects: a signed zero and a 2^-17 midpoint crossing, both fixed); normal handling went through three designs
(numpy rule → Blender on canonical copy → rounded/unrounded switch) after measurements showed the earlier ones
deviating.
