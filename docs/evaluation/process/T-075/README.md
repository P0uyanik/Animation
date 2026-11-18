# T-075: preserve approved character assets (report)

Branch `t-075-claude-approved-assets` (from `origin/staging` 7c32158). Lane A, path A. Implementer: Claude (cloud).
Blender that ran: the pinned **bpy 5.3.0** wheel (sha256 `5850cd39…c6a0`, `.github/ci-dependencies.json`), Python
3.13, through `tools/bpy_blender.py`.

## Result
Complete, with two follow-ups that need files outside the write-set (see "Open items").

## What was done
| Criterion | Result |
| --- | --- |
| 1. Publish boy 1.1.0 and girl 0.10.0 | Built from the fidelity-baseline inputs (spec + override) with `determinism.subprocess_env()` and `-t 1`, published, `approved` pointers set. Notes record the owner's wording: boy "current approved"; girl "approved as an intermediate version, not final visual approval". Boy 1.1.0 has parent 1.0.0; its identity change (`face`: lid tracking) is recorded with the owner decision as approval. |
| 2. Generator guard | `publish` refuses an existing folder, any version number in the index history, a build folder inside a store; staged copy + rename. `refuse_store_target` used by `episode.py`, `run_shot.py` (build folder, `--run-dir`), `restore`. `build_character.py` already refuses `assets/` (tested against all three real versions: refused, files byte-identical). |
| 3. Integrity check | `tools/check_assets.py` (hashes vs manifest, file list, pointers, sizes, diff vs `origin/staging`, append-only index). PASS on the branch. |
| 4. Reuse | Already in `run_shot.py` (T-062): cast `"current"` uses the published version when its manifest exists. Verified: `run_shot --stages prepare` on `content/scenes/eval/wave` resolves boy → stored 1.1.0 master, girl → stored 0.10.0 master, "published (read only)" (`reuse_prepare_wave.json`). New `asset_store.py regenerate` is the determinism check: both versions rebuild with **identical fingerprints at 0.1 mm and 0.01 mm**, same spec hash, stored master unchanged (`regenerate_*.json`). Rule in `docs/process/ASSET_STORE.md`. |
| 5. Size | boy 1.1.0: 7.0 MB (master 6,974,841 B); girl 0.10.0: 19.3 MB (master 19,192,252 B); boy 1.0.0 unchanged 19.9 MB. Largest file 19.2 MB (< 95 MB). `.glb` not stored: reuse links the master and packages are exported from it (`not_stored` in the manifests). |
| 6. Gate | `tools/check_all.py --base origin/staging --task T-075 --full` (local, bpy 5.3.0): PASS write-set, shared-systems lint, Python tests and links, Blender tests (determinism, export engine, face, garment, groom, hair, verify_charsys incl. reuse); regression girl 0.10.0 PASS (fidelity 65.38), third character PASS, boy fingerprint byte-equal and renders identical (fidelity 64.07, drop 0.42). Expected FAILs: frozen assets, guarded paths. Environment FAILs: C++ build/tests (no embree 4 in this container; no C++ touched). Pre-existing FAIL: boy `engine export: differs: character.json` vs the stored golden; unmodified `origin/staging` gives the same FAIL on this machine (`tools/regression/run.py --character boy_yellow_hoodie`), so it is not caused by T-075. |

Decision made: builds on the `body_generic` path write `spec.resolved.json` after fitting (eye positions, generated
control list), so it never matched the stamped input hash and the girl could not be published before. For those
builds `publish` recomposes the input spec from the paths in `build_report.json`, requires its hash to equal the
stamped hash, stores it as `spec.json` and keeps the fitted file as `spec.resolved.json`. Legacy builds keep the
strict check (existing tamper test unchanged).

## Tests
- `python3 pipeline/charsys/tests/test_asset_store_guard.py --blender <bpy wrapper>`: 36/36 PASS
  (`test_asset_store_guard.json`).
- `python3 pipeline/production/tests/test_run_shot_current.py`: PASS (0 failed).
- `python3 tools/check_assets.py --base origin/staging`: PASS.
- `asset_store.py verify` for both characters: ok.
- Not run: `pipeline/charsys/tests/test_store.py` needs a `renders/charsys/ref_1.0.0` build (verify_charsys); the
  gate's Blender tier covers it if it runs it.

## Open items for the Supervisor
1. `tools/frozen_manifest.txt` already has `# scope: assets/characters/boy_yellow_hoodie/versions/1.1.0/*`, so the
   new 1.1.0 files fail the frozen check until their blob IDs are added (file outside this write-set):
   ```
   b0e41220b301735b81459260fdec37e4576667fc  assets/characters/boy_yellow_hoodie/versions/1.1.0/animation_compat.json
   69f498661131a627aed751ad9f9041f153816011  assets/characters/boy_yellow_hoodie/versions/1.1.0/boy_yellow_hoodie_master.blend
   431a68b9d998f3dff2ca1b5d0123cba30877e533  assets/characters/boy_yellow_hoodie/versions/1.1.0/build_report.json
   6fd18859acdd04b5a7ad7cf0c49e80ecd60ca07b  assets/characters/boy_yellow_hoodie/versions/1.1.0/components.json
   a6dc58d56a30f7c323c23df456d2750400d3b865  assets/characters/boy_yellow_hoodie/versions/1.1.0/manifest.json
   0e0354c553e1284e9097e8902d95b3ee1df29e9a  assets/characters/boy_yellow_hoodie/versions/1.1.0/spec.json
   ```
2. Wiring into `tools/check_all.py` after T-061 releases it (exact diff):
   ```diff
   @@ def check_python_tests(logs: Path) -> Result:
            [sys.executable, str(ROOT / "pipeline/production/tests/test_run_shot_current.py")],  # T-062 cast check
   +        [sys.executable, str(ROOT / "pipeline/charsys/tests/test_asset_store_guard.py")],  # T-075 store guard
   +        [sys.executable, str(ROOT / "tools/check_assets.py")],  # T-075 published-version integrity
        ]
   ```
3. `assets/characters/*/versions/` commits need the approval trailer at merge (guarded path), as expected.
