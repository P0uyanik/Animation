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

## Making a version current: `tools/version_switch.py` (T-088)
One command for what took five serial fixes on 2026-11-18 (boy 2.0.0, girl 0.11.0). Run it on the task branch whose
claim the Supervisor has widened to the version folder, `index.json`, the character's golden baselines,
`fidelity_baseline.json` and `docs/evaluation/characters/<task>/`, after the owner decision is recorded:

```
python3 tools/version_switch.py --character <id> --version <x.y.z> --spec <spec> [--overrides <file> ...] \
    --task T-NNN --decision "<owner wording>" --decision-ref "docs/process/OWNER_DECISIONS.md <date>" \
    --blender <exe> [--identity-change-approved-by "<who, when>"] [--fidelity-json <earlier fidelity.json>] [--dry-run]
```

1. **Validate** (nothing is written until everything passes; all problems are listed at once): version `x.y.z`,
   never used in the store, no golden baseline for it yet; the spec and overrides lie in the character's own
   `spec/` folder, load, carry `identity.id` = the character and `metadata.spec_version` = the version; every
   generator pin resolves; the materials pin covers the preset families used (a `presets/2` id such as
   `skin-felt/2` needs `generators.materials = "presets/2"`, a T-092 `presets/3` id such as `skin-felt/3` needs
   `"presets/3"`, which also covers presets/1 and presets/2 ids); `tools/regression/tiers.py` accepts the build inputs
   and reads the same spec_version; identity changes against the approved parent carry the owner's approval; the
   decision is given and its file mentions the version; the task's claim covers every path the run writes.
2. **Build and publish**: `build_character.py` with the determinism environment (one thread, fixed seed), then
   `asset_store.py publish --without-glb` (refuses an existing or reused version).
3. **Approve**: `asset_store.py approve --by "owner (<decision-ref>)"` with the decision as the note.
4. **Fidelity baseline**: the score (`tools/fidelity/run.py` on the build at the baseline's render settings, or
   `--fidelity-json`) goes to `docs/evaluation/characters/<task>/fidelity/`; only this character's entry changes
   (build, overrides, score, source, `rebaseline` with the previous version, score and source).
5. **Golden baseline**: `tools/regression/run.py --write-baseline` for this character, copied to
   `docs/evaluation/regression/baselines/<id>/<version>/` (never overwritten).
6. **Checks**: `tools/check_cast.py`, `tools/check_assets.py`, the plain-Python tests that read current versions and
   every other plain-Python test naming the character (tests that need Blender are listed for a separate run);
   then every other version, character, golden and baseline entry is compared with its hash from before the run.
7. **Trailers**: prints the exact `Supervisor-Approved: <path>` block for every guarded path written (also in
   `<work>/version_switch.json`); the Supervisor puts it on the approval commit.

### Publish without making current: `--publish-only` (T-094)
For a version the owner reviews before it becomes current. The claim needs the version folder, `index.json` and
`docs/evaluation/characters/<task>/` only:

```
python3 tools/version_switch.py --publish-only --character <id> --version <x.y.z> --spec <spec> --task T-NNN \
    --decision "<owner wording that allows the publish>" --decision-ref "docs/process/OWNER_DECISIONS.md <date>" \
    --blender <exe> [--identity-change-approved-by "<who, when>"] [--dry-run]
```

Runs steps 1, 2, the score of step 4, 6 and 7: the version is published with status `candidate` (parent = the
approved version), and the fidelity score goes to `docs/evaluation/characters/<task>/fidelity/<id>/` with the current
version's score next to it (a drop above the baseline policy is flagged for owner review). It does **not** approve
(no pointer moves), does **not** change `fidelity_baseline.json` and does **not** write a golden baseline; step 6
compares the whole baseline file, the store pointers and the golden root before and after. To make the version
current later, after the owner's decision: `asset_store.py approve`, the baseline entry (reusing the score with
`--fidelity-json`) and the golden baseline, by the Supervisor's approval task.

### Make a published candidate current: `--approve-published` (T-094 step 2)
After the owner's decision, on a version published earlier (for example with `--publish-only`). The claim needs
`index.json`, `fidelity_baseline.json`, the version's golden folder and `docs/evaluation/characters/<task>/`:

```
python3 tools/version_switch.py --approve-published --character <id> --version <x.y.z> --spec <the version's spec> \
    --task T-NNN --decision "<owner wording>" --decision-ref "docs/process/OWNER_DECISIONS.md <date>" --blender <exe> \
    [--fidelity-json <fidelity.json>] [--dry-run]
```

Runs steps 1 and 3 to 7 (no build, no publish). Step 1 also refuses a version that is not published, is already
approved or fails verification, a spec whose hash is not the manifest's `spec_sha256`, and a missing fidelity report
(`docs/evaluation/characters/<task>/fidelity/<id>/fidelity.json` from `--publish-only`, or `--fidelity-json`). The
baseline entry's `source` is that report. Step 6 also checks that the published version folder is byte-identical.

The fidelity evidence (every mode) is copied with the sheets `report.md` links, stored as JPEG with the links
rewritten.

`--dry-run` validates and prints every step, command, file and the predicted trailer block without writing anything.
A failure after step 2 stops the run and lists what was already written; a published version stays published, so
continue by hand from the failed step (or publish a new version number). The tool only calls `asset_store.py`; the
guard, `tools/check_assets.py` and the frozen manifest are unchanged. Tests: `tools/tests/test_version_switch.py`
(fixture repository in a temporary folder, fake Blender tools).

## Release rule for opt-in features (T-178, owner 2026-11-21 ~04:10Z)

- A file under `assets/` that uses an opt-in feature (`pipeline/charsys/release_rule.py` `FEATURES`: groom/2..5,
  face_generic/3, body.hands, lash_curve, closed_fill, t168_face) passes only when its version, read from its path, is
  listed in `pipeline/charsys/release_manifest.json` for that feature with an owner `decision_ref` (a decision file
  that mentions the version). Base specs and unversioned files are never exempt; a malformed manifest exempts nothing.
- `tools/version_switch.py` writes the entry (features its files use, `--decision-ref`, `--decision`, task, date) in
  the same run that publishes or makes the version current; the claim must cover the manifest. Both files are guarded.
- A new opt-in feature registers one detector in `FEATURES`; it adds **no** per-feature "no spec uses X" guard test.
- Checked by `pipeline/charsys/tests/test_release_rule.py` (gate and version_switch step 6). Unchanged: byte-immutable
  versions, `tools/frozen_manifest.txt`, `test_asset_store_guard.py`, goldens, the decision ref for CURRENT.
