# T-144 round 2 — option (b), REPORT STEP ONLY

Input `origin/main@d42ad70`, merged into `t-144-claude-retire-versions` (round-1 plan `8a34069`, `PLAN.md`).
Nothing is removed, retired or changed: no code, test, threshold, golden, spec or asset is touched. Write-set
`docs/evaluation/T-144/**` only. Task branches were read with `git show` / `git archive`, never merged.

Data files (this folder): `regen.json` (step 1), `deps.json` + `deps.py` (step 2), `retire_sim.json` + `sim/` (step 3).

**Summary.** (1) REGEN_SUMMARY
(2) Pinned or imported by current / candidate / override builds: body_generic/2, face_generic/3, groom/3, groom/4,
groom/5 (T-167 only), garment/2, garment/3, accessories/1, rigify_human/1, presets/3, export/4 — plus export/5 (the
exporter default) and groom/2 (pinned by the third character's T-126a base spec), which are kept as well.
(3) Registry-only retire candidates: body_v6/1 (5 features), body_generic/1, face_generic/1, face_generic/2,
hair_clumps/1, groom/1, garment/1, albedo/1, presets/1, presets/2. **No generator module can be removed**: every
module of a candidate is still imported by a kept version or unconditionally by `build_character.py`. A plain registry
retirement would break 8 python-tier gate tests, 6 Blender-tier gate units and the export / regenerate of the 5 legacy
published versions (simulated, §3). The only equal-strength route is the round-1 option (a) archival allowance.

## 1. Published versions: stored built files vs a fresh build on current main

Method: `pipeline/charsys/asset_store.py regenerate --version <v> --blender blender --out <scratch>` for every
published version (T-158 deterministic build environment `determinism.subprocess_env()`, `-t 1`). It verifies the
stored manifest, rebuilds from the stored `spec.json` with the current code (`--no-glb --no-compare`), compares the
spec hash and the fingerprint_v2 geometry fingerprints at 0.1 mm and 0.01 mm, and checks the stored master is
untouched. The store is only read; output went to the session scratch folder. Blender 5.3.0 (same as every stored
`build_report.json`). Both stores also pass `asset_store.py verify` (9 versions, `problems: []`).

REGEN_TABLE

## 2. Dependency list (pinned or imported; none of these may be retired)

Resolved with each ref's own `spec.load` + `versions.REGISTRY` (`deps.py`, no Blender). Bases: the approved current
versions (boy 2.2.0, girl 0.13.0, stored `spec.json`) and the T-155 candidates (boy 2.3.0, girl 0.14.0, third 0.1.0,
`versions/<v>/spec.resolved.json` from `t-155-claude-candidates-r2@2774c13`; overlaid on refs that predate T-155).
Every override file a branch adds was applied to each base of its character, one at a time and all together.
84 resolutions, 0 errors.

| ref | sha | override files resolved | pins found |
|---|---|---|---|
| origin/main | d42ad70 | — | body_generic/2, face_generic/3, groom/3, garment/2, accessories/1 \| none, rigify_human/1, presets/3, export/4 |
| t-155-claude-candidates-r2 | 2774c13 | — (candidates) | the above + groom/4, garment/3 (boy 2.3.0, girl 0.14.0, third 0.1.0) |
| t-156-claude-eye-targets | 1a53bc8 | 2 eyes overrides (auburn, third) | no new pin (code change only in face_v3/lids.py, socket.py = face_generic/3) |
| t-159-claude-ears | aca5de6 | 6 (ears ×3, temple ×2, glasses) | no new pin (code in face_generic.py, face_features.py, face_generic_v3.py, accessories.py) |
| t-167-claude-hair-r7 | 3a43adc | 7 (T-160 hair_r6 ×3, T-167 hair_r7/r7b ×4) | **groom/5** (registered on this branch: `groom_r6`) |
| t-168-claude-boy-face | 49b3f56 | 10 (T-137 f1a/f1b/f2, T-159 ears/temple, T-168) | no new pin (code in face_features.py, face_generic.py, face_v3/*) |

Module closure of the kept pins (static imports inside `pipeline/charsys`, transitive; `deps.json` per ref):
`body_generic`, `face_generic_v3` → `face_generic`, `face`, `face_features`, `face_v3.*`; `groom_r4`/`groom_r5`/
`groom_r6` → `groom_hybrid`, `groom`, `groom_felt`, `hair`; `garments_v2`/`garments_v3` → `garments` (garment/1);
`materials.builder`, `geom`, `accessories`, `export_engine`, `versions`. `build_character.py` additionally imports
`body_v6`, `body_helpers`, `face`, `hair`, `geom` unconditionally; `body_v6.py` is a frozen file (`tools/frozen_manifest.txt`).

Kept although no spec pin names them in a current/candidate build:
- **export/5** — `export_engine.EXPORTER_DEFAULT = "5"`: every master without an embedded spec (test data, the toy
  fixture of the gate's export-determinism unit) exports as export/5. It is in use, not a candidate.
- **groom/2** — the third character's base spec `spec/candidates/T-126a/girl_white_hair_blue_dress.0.1.0.spec.json`
  pins groom/2 (T-155 composes it with the T-126 hair override → groom/4); `test_determinism.py` CURRENT
  `third_0.1.0` builds that base spec directly. Part of a candidate's composition chain, so kept.
- **groom/5** — exists only on `t-167-claude-hair-r7`; pinned by all its overrides. Must stay when it lands.

## 3. Retire candidates, the checks that would change, equal-strength replacements

### 3.1 Candidates (pinned by nothing current, candidate or override)

| pin | module | published versions that pin it | any module removable? |
|---|---|---|---|
| body_v6/1 (body, face, garment, accessories, materials) | body_v6 (frozen) | boy 1.0.0 (reference pointer), 1.1.0 | no: imported by build_character, build_mannequin, hair_generic_test, garment_generic_test; frozen |
| body_generic/1 | body_generic | girl 0.10.0 | no: same module as body_generic/2 |
| face_generic/1 | face_generic | girl 0.10.0 | no: imported by face_generic_v3 (face/3) |
| face_generic/2 | face_generic | boy 2.0.0, girl 0.11.0 | no: same |
| hair_clumps/1 | hair | boy 1.0.0, 1.1.0 | no: imported by groom → groom/3, /4, /5; and build_character |
| groom/1 | groom | girl 0.10.0 | no: library of groom/2–5 |
| garment/1 | garments | boy 2.0.0, girl 0.10.0, 0.11.0 | no: library of garment/2, /3 |
| albedo/1 | geom | none | no: geom used by every build |
| presets/1, presets/2 | materials.builder | boy 2.0.0, girl 0.10.0, 0.11.0 | no: same module as presets/3 |

Already retired: hair_clumps/2, export/1–3. So under option (b) "retire and remove only generator code no current or
candidate version pins", **the removable code is empty**; retirement can only be a registry status change.

### 3.2 What a registry retirement would change (simulated)

`retire_sim.json`, `sim/`: two scratch trees from `git archive` of the input; one appends `sim/retire_patch.py.txt`
(all §3.1 pins retired) to its `versions.py`. The repository was not changed. Results:

Python tier (`check_all.py` list + store tests): fail only when retired —
`test_versions.py` (120 PASS → stops after 30: its fixtures use hair_clumps/1 and the 2.0.0-dev spec),
`test_version_switch.py` (presets/1 fixture), `test_materials_r2.py`, `test_face_v3.py`, `test_face_v3b.py`
(face_generic/2 specs boy 2.0.0 / girl 0.11.0), `test_boy2_face.py` (2.0.0-dev), `test_material_presets.py`,
`test_asset_store_guard.py` (girl unversioned spec). Unaffected: the other 28 (6 fail identically in both scratch
trees because the copy has no `.git`/`renders/` or needs `--blender`; not caused by retirement).

Blender tier (entry point = `spec.load`, which `build_character.py` runs first; or `versions.record` in export):

| gate unit | builds / reads | under retirement |
|---|---|---|
| charsys (verify_charsys, boy v6 fingerprint) + face | `boy_yellow_hoodie.spec.json` (body_v6/1 ×5, hair_clumps/1) | fails |
| determinism (default boy) | same v6 spec | fails |
| boy2 (2.0.0-dev → test_boy2_face, test_hoodie) | body_generic/1, face_generic/1, hair_clumps/1, garment/1, presets/1 | fails |
| garments-v2-quick | boy 2.0.0, girl 0.11.0 specs | fails |
| material-presets | girl unversioned spec | fails |
| export-engine (step 4: exports published boy 1.0.0 master) | embedded spec → body_v6/1 | fails |
| hair, groom, groom-dynamics, garment, materials-r2-graphs | call the modules directly, not via the registry | unchanged |
| build-determinism-girl, deform, shot-eyes, emotions, fidelity-regression, hair-curves, render-engine | current versions | unchanged |

Also outside the gate: `asset_store regenerate` and engine export of boy 1.0.0, 1.1.0, 2.0.0 and girl 0.10.0, 0.11.0
(`versions.record` of the stored spec raises), i.e. the §1 comparison itself; episodes e000, e901–e906 with legacy casts.
`restore` and `verify` copy/hash files and are unaffected.

### 3.3 Equal-strength replacement per changed check

A stored-file comparison proves the published file is retrievable; it does not prove the code still produces it. Since
no module can be removed (§3.1), the code stays and so the only replacement that keeps every check at full strength is
to keep running the same builds:

| check | equal-strength replacement | file-comparison alternative (weaker — not recommended) |
|---|---|---|
| charsys / verify_charsys + boy fingerprint + face tests | archival allowance for `boy_yellow_hoodie.spec.json`: identical command and thresholds | sha1 of 1.0.0 master in frozen_manifest + stored fingerprint; loses the "frozen v6 code reproduces it" proof |
| determinism (boy v6 twice) | allowance, unchanged | none equal: a determinism test needs two fresh builds |
| boy2 → test_boy2_face, test_hoodie | allowance for the 2.0.0-dev spec, unchanged | run the two tests on a stored master — none matches 2.0.0-dev (body_generic/1 vs /2), so not equal |
| garments-v2-quick; test_face_v3, test_face_v3b, test_materials_r2 | allowance for the boy 2.0.0 / girl 0.11.0 specs, unchanged | — |
| material-presets; test_asset_store_guard | allowance for the girl unversioned spec, unchanged | — |
| test_versions, test_version_switch | allowance covers their fixtures, unchanged; plus one new test that an unlisted spec pinning a retired version is refused | swapping fixtures to released pins would change the tests: not allowed |
| export-engine step 4 (boy 1.0.0 export) | export of a published master records but does not refuse retired pins (allowance for stored version specs) | — |
| asset_store regenerate (5 legacy versions) | allowance for stored version specs | stored sha256 (manifest) + frozen_manifest sha1: retrievability only |

The allowance is the round-1 option (a) (`PLAN.md` §6): `REGISTRY.retire` the §3.1 pins so new or changed specs,
`version_switch` and `publish` refuse them, while `build_character` / `export_engine` still build or export a retired
pin for an explicit list (the legacy spec files above and stored published version specs), as in T-154. No test,
golden, threshold or module changes. Write-set then: `pipeline/charsys/versions.py`, `spec.py`, `build_character.py`,
`export_engine.py` (record path only), one new test, `docs/CHARACTER_SYSTEM_VERSIONS.md`. One revertible commit, FULL
gate green before merge.

## 4. For the owner (numbered choices)

1. Accept that option (b) removes no code (§3.1) and choose: (a) registry-only retirement with the archival allowance
   (§3.3; protects against new pins, all checks unchanged), or (c) no change, document §3.1 as "legacy, do not pin".
2. If (a): include boy 1.0.0 (the `reference` pointer) under the allowance for export and regenerate? Recommended yes.
3. Keep export/5 and groom/2 out of retirement (§2). Recommended yes.
4. Re-scan with `deps.py` at implementation time (T-167 groom/5 and any new T-155 / override pins).
