# T-043: spec parts, per-feature generator versions, shared helpers out of body_v6

Lane B · path A (refactor, zero visual change) · branch `t-043-claude-spec-versions`.
Design and how-to: [docs/CHARACTER_SYSTEM_VERSIONS.md](../../../CHARACTER_SYSTEM_VERSIONS.md).

## 1. Objective
Versioned shared character systems: specs pin every generator / preset / exporter version, released versions are
immutable, unknown/retired versions fail loudly, spec parts, shared helpers out of the frozen `body_v6.py`, with zero
change to any character.

## 2. Result
**Complete.** All six acceptance criteria implemented; zero change proven for every character/configuration (see §6).
Gate: see §5.

## 3. Files changed
Code (all inside the task write-set):
- `pipeline/charsys/versions.py` (new): registry (`Registry`, `REGISTRY`), pin parsing, legacy defaults, `resolve_pins`,
  `record`, `load` (imports the module of a pinned version and checks its `GENERATOR_VERSIONS` declaration).
- `pipeline/charsys/spec.py`: spec parts (`compose`, `split`, `PART_SECTIONS`, `PART_SCHEMA`); `validate` checks
  pins; `load` composes parts and returns `info["versions"]`.
- `pipeline/charsys/build_character.py`: build path chosen by the body pin (`body_generic/1` → generic,
  `body_v6/1` → legacy, anything else fails); generic path loads body/face/groom/garment modules through the pins;
  shared helpers from `body_helpers`. CLI unchanged (same arguments, outputs).
- `pipeline/charsys/body_helpers.py` (new): `face_y`, `bind_to_nearest_bone`, `cleanup_weights`, copied verbatim
  (AST extraction) from `body_v6.py`, which is not edited.
- `pipeline/charsys/export_engine.py`: `GENERATOR_VERSIONS = ("export/4",)`; checks the master's embedded spec pins
  this exporter (fails before any work otherwise); manifest gains a `versions` block. `EXPORTER_VERSION = "4"`
  literal kept (run_shot.py's cache key regex).
- `pipeline/charsys/body_generic.py`, `face_generic.py`, `groom.py`, `garments/__init__.py`: one
  `GENERATOR_VERSIONS` declaration line each (+ a docstring line in `body_generic.rig_generic`).
- `pipeline/charsys/tests/test_versions.py` (new): 66 checks (commit trailer `Supervisor-Approved:` for this
  guarded new test file, as it is in the task's write-set).

Documentation / evidence:
- `docs/CHARACTER_SYSTEM_VERSIONS.md` (new): pins, registry, defaults, parts, adding a version, pin bumps.
- `docs/evaluation/characters/T-043/README.md` (this report), `compare_exports.py` (package comparison tool),
  `evidence/*.json` (comparison outputs).

## 4. Implementation and decisions
- **Features and names as found in code:** `body` (body_v6/1, body_generic/1), `face` (body_v6/1,
  face_generic/1), `groom` (hair_clumps/1, hair_clumps/2, groom/1), `garment` (body_v6/1, garment/1),
  `accessories` (body_v6/1, accessories/1), `rig` (rigify_human/1), `materials` (body_v6/1, albedo/1, presets/1),
  `exporter` (export/1-3 retired, export/4). The task's example `face_generic/2` does not exist in code; the girl
  builds with `face_generic/1`. `accessories` and `rig` were added because the spec pins "every generator".
  The legacy builder's bare `body_v6` is version `body_v6/1`; `hair_clumps/2` is registered because the boy's hair
  experiments use it.
- **Pins were not added to the existing spec files** (the write-set allowed it, "pins only"). Any added key changes
  the spec sha256, which is stamped into the master (`ps_spec_sha256`), the engine package (`source.spec_sha256`)
  and checked by the asset store against the boy's published 1.0.0, i.e. it would change both characters' outputs and
  break AC4. The boy's `1.1.0.override.json` is frozen anyway. Instead, missing pins resolve to frozen legacy
  defaults derived only from each spec's own generator fields (no character names in shared code) and are
  **recorded explicitly** in `build_report.json` and `character.json` (`versions.generators`, `defaulted`).
- **Registration:** central, one immutable line per version in `versions.py` (pure Python, so specs validate without
  Blender); each editable generator module *declares* the versions it implements (`GENERATOR_VERSIONS`) and
  `load()` verifies the declaration. Frozen or other-owned modules (`body_v6`, `hair`, `accessories`, `materials`)
  are registered with `declared=False`.
- **EXPORTER_VERSION:** replaced as the version concept by the per-feature registry (`export/4`), but the literal line
  stays because `pipeline/production/run_shot.py` (not in the write-set) reads it from the source for its package
  cache key; changing it would invalidate every cached package.
- **Manifest record:** the engine package gains one additive key, `versions`. Everything else in `character.json`
  is unchanged (see §6). This is the AC2 requirement; the engine reader ignores unknown keys.
- **Pin vs field conflict:** an explicit pin of the same generator family with another number than the spec's
  generator field is an error (prevents a half-done pin bump).
- **Parts:** `identity` (identity, proportions, metadata), `body` (body, rig, fur, animation, components), `face`,
  `hair`, `outfit` (clothing, accessories), `materials`; `generators` stays in the root. Composition is
  order-independent; duplicate / misplaced sections fail.

## 5. Tests executed
Blender: bpy 5.3.0 module (Python 3.13 venv) through `tools/bpy_blender.py` as the `blender` wrapper.
- `python3 pipeline/charsys/tests/test_versions.py` → **ALL PASS (66/66)**: registry (unknown / retired /
  malformed fail, re-registration refused, retire), module declarations, exporter line, pins (respected, defaults,
  retired/unknown rejected by `spec.validate`, contradiction rejected, spec hash unchanged), two versions of one
  generator interleaved in one session (separate modules and state, specs unchanged, private registry),
  built-in characters resolved interleaved, spec parts (both characters split into 6 parts compose to the same spec
  and hash; overrides; duplicate / wrong part / unknown part / wrong schema rejected).
- `python3 pipeline/charsys/tests/test_material_presets.py` → ALL PASS (54/54) (imports `spec`).
- CLI loud failures: `build_character.py` with an override pinning `body_generic/9` → `ValueError ... contradicts`;
  pinning `export/3` → `ValueError ... exporter version 'export/3' is retired`; both exit code 1 before building.
- Full gate `python3 tools/check_all.py --base origin/main --blender <bpy wrapper>` after `git merge origin/staging`:
  GATE_RESULT_PLACEHOLDER

## 6. Zero change (AC4)
Baseline: worktree of `origin/staging` @ 598b432; branch @ 7b1be40 (the later staging merge dcd07e0 only adds a task
file and claims, no code). Each configuration built with `build_character.py --no-compare`, fingerprinted with
`fingerprint_v2.py` (strict default grid 0.01 mm) and exported with `export_engine.py`
(`rig_profiles/humanoid_rigify.json`).

| Configuration | fingerprint_v2 (sha256 of the JSON) | export: manifest | export: geometry (matched) |
| --- | --- | --- | --- |
| boy spec | **byte-identical** (c6aca097…) | identical except the new `versions` key* | identical |
| boy + 1.1.0 override | **byte-identical** (ef65afb8…) | identical except `versions`* | identical |
| girl spec | **byte-identical** (e609ec37…) | identical except `versions`* | identical |
| girl + dynamics override | **byte-identical** (e609ec37…) | identical except `versions`* | identical |

\* plus `source.blend_sha256` and `files.geometry.bin.sha256`, which hash bytes that are not reproducible even
between two builds of the same staging commit (below).

**The engine export is not byte-reproducible on origin/staging itself:** two builds of the boy at the same staging
commit give `geometry.bin` files that differ in 126 800 bytes (`evidence/export_noise_staging_boy_x2.json`): vertex
and triangle order of some meshes (ears, eyes, lids, buckles, hood_back, undershirt) and float noise of evaluated
normals (≤ 4e-5). Byte equality of the export vs staging is therefore impossible to show for any change, including
none. `compare_exports.py` instead compares every mesh order-independently: each vertex of A is matched to the
vertex of B at the same position (≤ 1 µm), then normals (≤ 1e-3), joints (equal), weights (≤ 1e-5), every morph
delta (≤ 1e-6 m) and the triangle set (winding kept) must agree. Staging-vs-staging passes this; **branch-vs-staging
passes it for all four configurations** (`evidence/export_compare_*.json`, `matched_equal: true`), and all manifest
keys other than those above are equal (skeleton, roles, morphs, expressions, retarget, dynamics, materials, mesh
layout, exporter_version "4", spec_sha256 …). The non-determinism is pre-existing (delivery plan §5.2 item 5, T-038b) and
not introduced or changed here; a follow-up to make the export order-stable would allow a byte-level guard.

## 7. Visual results
None needed: geometry fingerprints are byte-identical, so no renders were made.

## 8. Problems, limitations, open questions
- Export byte non-determinism on staging (above): the unchanged-character guard for exports needs either an
  order-stable exporter or an order-independent comparison like `compare_exports.py`.
- Docs that mention `EXPORTER_VERSION` (`docs/PRODUCTION_PIPELINE.md`, `docs/ANIMATION_CLIPS.md`,
  `docs/SECONDARY_MOTION.md`, `docs/ENGINE_CHARACTER_PACKAGE.md` for the new `versions` key) are outside the
  write-set and were not updated.
- `pipeline/clips/build_mannequin.py` still passes `body_v6` to `rig_generic` (outside the write-set; identical
  helpers, so no behaviour difference).
- `test_versions.py` is not wired into `tools/check_all.py` (T-041's file); suggest adding it to its Python tests.
- Existing specs remain unpinned by design (§4); new spec versions should carry explicit pins.

## 9. Commits
Branch `t-043-claude-spec-versions`: 7b1be40 (code + tests), ba6fb4a (merge origin/staging), 07f8358 (versions
doc), and the report commit.

## 10. Resource use
Token usage not available. Builds: 5 staging builds (4 configurations + 1 noise repeat) and 4 branch builds, plus
the gate.
