# Character system versions (T-043)

Owner decision 2026-11-17: shared character systems are **versioned**. A character spec pins the version of every
generator, preset library and the exporter it uses; released versions are immutable; new behaviour is a new version.
This is what keeps existing characters from changing by accident (delivery plan §5.2).

Code: `pipeline/charsys/versions.py` (registry, plain Python), `pipeline/charsys/spec.py` (pins, spec parts),
`pipeline/charsys/build_character.py` (dispatch by pin), `pipeline/charsys/export_engine.py` (exporter pin, manifest
record). Tests: `pipeline/charsys/tests/test_versions.py`.

## Pins in a spec

```json
"generators": {"body": "body_generic/1", "face": "face_generic/1", "groom": "groom/1", "garment": "garment/1",
               "accessories": "accessories/1", "rig": "rigify_human/1", "materials": "presets/1",
               "exporter": "export/4"}
```

* Features: `body`, `face`, `groom` (hair), `garment`, `accessories`, `rig`, `materials`, `exporter`.
* A pin is `<name>/<number>`; `none` = the character does not use the feature.
* Building (and `spec.validate`) **fails loudly** on an unknown, retired or malformed pin. It never falls back.
* A pin may not contradict the spec's own generator field of the same family (`hair.generator: "groom/1"` with
  `generators.groom: "groom/2"` is an error; a pin bump changes both, see below).
* **Missing pins** default to the versions the spec built with before T-043 (frozen rules in `versions.py`,
  `LEGACY_FIELDS`): each feature's pin is its spec field's value (`body.generator`, `face.generator`,
  `hair.generator`, `clothing.generator`, `accessories.generator`, `rig.generator`), the legacy builder's bare
  `body_v6` means `body_v6/1`; materials are `presets/1` with preset assignments, otherwise `body_v6/1` (legacy body)
  or `albedo/1`; the exporter is `export/4`. These rules never change when a version is added, so an unpinned spec
  keeps building the same way.
* The resolved pins are **recorded**, never written into the spec (the spec hash, stamped into every master and
  package, stays the same): `build_report.json` → `versions`, and the engine package `character.json` → `versions`
  (`generators`, `pinned_in_spec`, `defaulted`).

Current characters (both unpinned, defaults recorded explicitly in their build reports):

| Feature | boy_yellow_hoodie | girl_auburn_bun_glasses |
| --- | --- | --- |
| body | body_v6/1 | body_generic/1 |
| face | body_v6/1 | face_generic/1 |
| groom | hair_clumps/1 | groom/1 |
| garment | body_v6/1 | garment/1 |
| accessories | body_v6/1 | accessories/1 |
| rig | rigify_human/1 | rigify_human/1 |
| materials | body_v6/1 | presets/1 |
| exporter | export/4 | export/4 |

Pins were deliberately **not** added to the existing spec files: adding a key changes the spec hash, which is stamped
into the master and the engine package (and the boy's published 1.0.0 identity lock), i.e. it would change those
characters' outputs. New specs (and new spec versions) should carry explicit pins.

## Registered versions

| Feature | Versions (status) | Implemented by |
| --- | --- | --- |
| body | body_v6/1, body_generic/1 | `body_v6.py` (frozen), `body_generic.py` |
| face | body_v6/1, face_generic/1, face_generic/2 (T-065, opt-in), face_generic/3 (T-089, planned) | `body_v6.py` + `face.py`, `face_generic.py`, `face_generic_v3.py` |
| groom | hair_clumps/1, hair_clumps/2 (retired by T-072; its experiments are archived, incl. the frozen H28 candidate), groom/1 | `hair.py`, `groom.py` |
| garment | body_v6/1, garment/1, garment/2 (T-093, opt-in) | `body_v6.py`, `garments/`, `garments_v2/` |
| accessories | body_v6/1, accessories/1 | `body_v6.py`, `accessories.py` |
| rig | rigify_human/1 | `body_v6.rig_character` / `body_generic.rig_generic` |
| materials | body_v6/1, albedo/1, presets/1, presets/2 (T-066), presets/3 (T-092, planned) | `body_v6.make_materials`, `geom.material`, `materials/builder.py` + `presets.json` |
| exporter | export/1-3 (retired), export/4, export/5 (T-056) | `export_engine.py` |

Exporter: `export/4` is the legacy default of every unpinned spec (`LEGACY_EXPORTER`; both current characters) and
`run_shot`'s package cache key (`EXPORTER_VERSION = "4"`). `export/5` (T-056) is export/4 with order-stable,
byte-reproducible output; it is used by specs that pin it and by masters without an embedded spec (test data,
`EXPORTER_DEFAULT = "5"`). Evidence: [T-056](evaluation/characters/T-056/README.md).

Spec sub-generators (`face.mouth.generator` `lips_jaw/*`, `face.blink.generator` `lid_seam/1`) stay spec data of
their face version.

## Spec parts

A spec may keep sections in part files, composed by `spec.py`:

```json
{"schema": "plush-studio.character-spec/1", "generators": {...},
 "parts": {"identity": "x.identity.json", "body": "x.body.json", "face": "x.face.json",
           "hair": "x.hair.json", "outfit": "x.outfit.json", "materials": "x.materials.json"}}
```

Part file: `{"schema": "plush-studio.character-spec-part/1", "part": "face", "sections": {"face": {...}}}`.

| Part | Sections |
| --- | --- |
| identity | identity, proportions, metadata |
| body | body, rig, fur, animation, components |
| face | face |
| hair | hair |
| outfit | clothing, accessories |
| materials | materials |

A section is defined once (root or one part); a section in the wrong part, an unknown part or a wrong schema is an
error. The composed spec has no `parts` key, so a split spec has **the same hash** as the same spec in one file.
Overrides apply after composition. `spec.split()` produces the parts of an existing spec. Existing single-file specs
load unchanged.

## How to add a version (path A: no character changes)

1. Never edit a released version's behaviour. Put the new behaviour in a new module (e.g. `groom_v2.py`) or a code
   path selected only by the new pin; shared helpers that a released version uses (e.g. `body_helpers.py`) are not
   edited either: add a new function.
2. Declare it in the module: `GENERATOR_VERSIONS = ("groom/2",)` (`versions.load` checks the declaration).
3. Register it with one appended line in `versions.py` (`_r("groom", "groom", 2, "groom_v2")`). Never edit or delete
   an existing line; retiring is a status change (`RETIRED`), done only when no character pins the version.
4. If the build path dispatches on the feature (body), add the new pin to `build_character.py`'s path table.
5. A new exporter version is a new `EXPORTER_VERSION` together with its registry line; the literal
   `EXPORTER_VERSION = "<n>"` stays in `export_engine.py` because `run_shot.py` keys its package cache on it.
6. Test the new version on a test/fixture spec. Existing characters do not use it, so the unchanged-character guard
   (fingerprints, exports, regression renders identical to `main`) must still pass.

## How a pin bump works (path B: owner approval)

A character only moves to a new version through an explicit pin-bump task for that character:

1. A **new spec version file** for that character with the new pin (and its matching generator field); existing
   spec versions are never edited.
2. The diff is limited to that character's spec and assets; the guard checks that every *other* character stays
   identical.
3. Renders and fingerprints of the bumped character are evaluated against the references and the owner approves
   before anything is published or promoted.

## Evidence

T-043 zero-change proof: `docs/evaluation/characters/T-043/README.md`.
