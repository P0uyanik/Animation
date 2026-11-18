# Approved character assets: store, guard and reuse (T-075)

Owner decision 2026-11-17: approved Blender character assets are preserved and reusable, and the generator never
overwrites them.

## Store
- One immutable folder per version: `assets/characters/<id>/versions/<ver>/` holds `<id>_master.blend`, `spec.json`
  (the input spec; its hash is `spec_sha256`), `components.json`, `animation_compat.json`, `build_report.json`,
  `manifest.json` (sha256 and size of every file), plus `spec.resolved.json` (the fitted spec) for body_generic builds.
  `versions/index.json` lists the versions, the `approved` / `reference` pointers and an append-only history.
- The `.glb` is not stored for new versions (`--without-glb`, recorded under `not_stored` in the manifest): shots link
  the master and `run_shot.py` exports engine packages from it. Boy 1.0.0 keeps its frozen `.glb`.
- Published now: boy 1.0.0 (reference), boy **1.1.0** ("current approved") and girl **0.10.0** (approved as an
  intermediate version, not final visual approval). The owner's wording is in each version's notes.
- Tool: `pipeline/charsys/asset_store.py` (`publish`, `approve`, `verify`, `restore`, `regenerate`, `list`).

## Guard: nothing writes into a published version
- `publish` refuses an existing version folder, any version number the index ever recorded, and a build folder
  inside a store; it copies through a hidden staging folder renamed into place only when complete.
- `build_character.py` refuses any `--out` under `assets/`; `episode.py`, `run_shot.py` (shot build folder and
  `--run-dir`) and `restore` refuse any path inside a store (`asset_store.refuse_store_target`).
- New work goes to a build folder; a new version only through `publish`, approval only through `approve --by` on
  an owner decision.
- `tools/check_assets.py` checks every store (hashes against the manifest, file list, pointers, sizes under 95 MB)
  and fails when a file of a version that exists in the base (`origin/staging`) is changed, removed or added, or
  when `index.json` loses an entry, edits one (other than `status` / `approval_notes`) or rewrites its history.
  `assets/characters/*/versions/` is also a guarded path (Supervisor approval trailer at merge).

## Reuse rule
- Shots and evaluations use cast `{"character_id": "<id>", "version": "current"}`. When the current version
  (`docs/evaluation/characters/fidelity_baseline.json`) is published, `run_shot.py` uses the stored master directly:
  manifest-checked, LINKED read-only with a library override (only the rig is editable; `episode.py` rules), never
  regenerated. Unpublished current versions are still built from spec and overrides in the shot's build folder.
- Regenerate-and-compare stays the determinism check: `asset_store.py regenerate --character <id> --version <ver>
  --blender <exe> --out <new dir>` rebuilds from the stored `spec.json` with the current code and requires identical
  geometry fingerprints (`fingerprint_v2`, 0.1 mm and 0.01 mm) against the stored master. `.blend` bytes are not
  reproducible between builds; the fingerprint is the comparison. The all-character regression keeps building
  from the pinned specs and comparing renders.
