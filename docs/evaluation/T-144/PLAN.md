# T-144 PLAN checkpoint — retire generator versions no current or candidate character pins

Input `origin/integration/t-137@c2b4d13` · branch `t-144-claude-retire-versions` · plan only, nothing removed or changed.
Data: `pin_matrix.json` (this folder).

## 1. Pinned set (KEEP)

| source | body | face | groom | garment | materials | exporter |
|---|---|---|---|---|---|---|
| current boy 2.2.0 / girl 0.13.0 | body_generic/2 | face_generic/3 | groom/3 | garment/2 | presets/3 | export/4 |
| T-155 candidates boy 2.3.0 / girl 0.14.0 (T-132 `f28fe2a` spec.resolved) | body_generic/2 | face_generic/3 | groom/4 | garment/3 | presets/3 | export/4 |
| T-155 third 0.1.0 (T-126a spec + T-126 hair/dress overrides, allowlist) | body_generic/2 | face_generic/3 | groom/4 | garment/3 | presets/3 | export/4 |
| T-141 `1a70299` | — post-build tool on masters; registers/pins nothing | | | | | |

Also kept: accessories/1, rigify_human/1, none. Caveat: T-155 is not on any branch yet; pins come from T-132 `f28fe2a`
and `owner_approved_candidates.json`. Re-scan at removal time.

## 2. Retirement candidates (not pinned by any current/candidate spec)

body_v6/1 (body, face, garment, accessories, materials), body_generic/1, face_generic/1, face_generic/2,
hair_clumps/1, groom/1, groom/2, garment/1, albedo/1, presets/1, presets/2, export/5.
Already retired: hair_clumps/2, export/1–3.

## 3. Published versions stay retrievable (proven, no Blender)

- `asset_store.py verify` on both stores: 9 versions, `problems: []`. `tools/check_assets.py`: PASS. `test_versions.py`: 119/119.
- Every published version has its built master in the store (`*_master.blend`, + glb for boy 1.0.0); 1.0.0/1.1.0/0.10.0
  also sha1-locked in `tools/frozen_manifest.txt`. `restore` copies files (no rebuild), so it is unaffected.
- Only `asset_store.py regenerate` (rebuild from stored spec) would fail for boy 1.0.0, 1.1.0, 2.0.0 and girl 0.10.0,
  0.11.0, which pin candidates. Equivalent: the existing byte hashes (store + frozen manifest).

## 4. Finding: no generator module can be archived

| candidate | module | still needed by a pinned version |
|---|---|---|
| groom/1, hair_clumps/1 | groom.py, hair.py | groom_hybrid (groom/2) → groom_r4 (groom/3) → groom_r5 (groom/4) import groom.py; groom.py imports hair.py |
| face_generic/1, /2 | face_generic.py, face.py | face_generic_v3 (face/3) imports both |
| garment/1 | garments/ | garments_v2 and garments_v3 import it |
| body_generic/1 | body_generic.py | same module as body_generic/2 |
| presets/1, /2 | materials/builder.py + libraries | presets/3 extends them |
| export/5 | export_engine.py | same module as export/4 |
| body_v6/1 | body_v6.py | frozen file (frozen_manifest); build_character, build_mannequin |

So "retire" can only be a registry status change (`REGISTRY.retire`), as done for hair_clumps/2. No code is removed.

## 5. Required checks that BUILD a candidate (would fail with `VersionError` once retired)

| check (gate) | builds |
|---|---|
| verify_charsys (boy baseline vs frozen v6 fingerprint) + test_store input build | body_v6/1 ×5, hair_clumps/1 (unpinned v6 spec) |
| boy 2.0.0-dev build → test_boy2_face, test_hoodie | body_generic/1, face_generic/1, hair_clumps/1, garment/1, presets/1 |
| hair_generic_test, groom_generic_test, groom_dynamics_test | groom/1 (unpinned girl spec: body_generic/1, face_generic/1, garment/1, presets/1) |
| garment_generic_test (mannequin) | body_generic/1, garment/1, albedo/1 |
| test_garments_v2 (garment/1 vs /2 on boy 2.0.0) | face_generic/2, groom/2, garment/1, presets/2 |
| test_export_determinism, test_determinism, test_material_presets, test_garment_details, test_asset_store_guard | unpinned boy v6 / girl specs; export/5 |
| test_face_v2/_v3/socket_wall, test_hair_v3*/r4_build, test_materials_r2(+graphs), test_skin_*, test_version_switch | face_generic/1–2, groom/2, presets/1–2 (golden graph digests) |

Not in the gate but pinned to legacy specs: episodes e000, e901–e906 shot casts (gate shot tests switch to `current`).

## 6. Options (decision needed)

- **(a) Recommended: registry-only retirement with a named archival build allowance.** Mark the §2 set RETIRED, so
  `spec.validate`, `version_switch` and publish refuse them for any new or changed spec. `build_character` builds a
  retired pin only for the listed regression specs/tests and `asset_store regenerate` (explicit allowlist, like T-154;
  a test proves an unlisted spec is refused). No test, golden or threshold changes; no module removed. Write-set:
  `pipeline/charsys/versions.py`, `build_character.py`, `spec.py`, one new test, `docs/CHARACTER_SYSTEM_VERSIONS.md`,
  `docs/evaluation/T-144/**`. One revertible commit; FULL gate before merge.
- (b) Replace the §5 builds by stored-file comparisons: removes the proof that code still reproduces them, i.e. weakens
  checks — conflicts with the owner's safety conditions. Not recommended.
- (c) Defer T-144: change nothing; document §2 as "frozen-legacy, do not pin" only.

Hold export/5 out of (a) until T-158 (deterministic builds) decides whether it needs it.

## 7. Open questions

1. (a), (b) or (c)? With (a): is the change to versions.py/build_character.py acceptable (TD-level: new allowance)?
2. Re-scan T-155 pins once it publishes; any new pin there is removed from §2.
