# Engine character package (Blender → C++ adapter)

_2026-11-14. Status: implemented and tested on two packages:_
- _`boy_yellow_hoodie` 1.0.0, a production character (read-only source);_
- _an **engineering test fixture**, which is not a production character._

_The fixture proves that the exporter and importer do not depend on the boy's bone names, proportions or hierarchy.
It does **not** validate the whole character-production pipeline for other character types: that needs a genuinely
different production character later._

## Purpose
Characters built outside the engine (the charsys Blender pipeline) run the engine's existing behaviours without
character-specific engine code:
- the actions (reach, touch, walk, look);
- the life layer;
- constraints, skinning and morphs.

```
master .blend ──export_engine.py + rig profile──► package (character.json + geometry.bin) ──loadImportedCharacter──►
Skeleton + CharacterRig ──► existing SceneEvaluator / actions / life layer / poseCharacter
```

## Pieces
| Piece | File | Character-independent? |
| --- | --- | --- |
| Exporter (headless Blender, read-only on input) | `pipeline/charsys/export_engine.py` | yes: everything rig-specific comes from the profile |
| Rig profiles (data) | `pipeline/charsys/rig_profiles/*.json` | one per rig family |
| Engine behaviour requirements (data) | `pipeline/charsys/rig_profiles/engine_behaviours.json` | engine facts, no character data |
| Importer | `engine/model/imported_character.h/.cpp` | yes: checks package consistency only |
| Scene integration | `engine/scene/scene.cpp`: a scene character whose `asset` is a package manifest is loaded from it (`CharacterInstance::imported`) | yes |
| Fixture (engineering test) | `pipeline/charsys/tests/fixtures/make_toy_fixture.py` | test only |
| Tests | `tests/test_imported_character.cpp`, `pipeline/charsys/tests/test_export_engine.py` | run on both packages |
| Test packages | `tests/data/imported/boy_yellow_hoodie_1.0.0/` (14 MB), `tests/data/imported/toy_fixture/` (0.1 MB) | exported, committed so C++ tests need no Blender |

## Rig profiles
A profile maps **engine roles** to the rig's bone names and states what this rig family must provide:

| Field | Meaning |
| --- | --- |
| `kind` | `humanoid` now. `quadruped`, `creature` and others are possible later without format or importer changes |
| `required_roles` | **Profile-specific.** Export fails if one is missing (`humanoid_*`: `hips, spine, chest, neck, head`). Other kinds will define their own |
| `roles` | Role → source bone; `mirror` expands `.L` entries to the right side using the rig's own suffixes |
| optional roles | Every other role in `roles` (eyes, limbs, fingers …). Behaviours that need a missing one are reported as missing |
| `rig_specific_bones` | Bones kept under their own names (e.g. `DEF-jaw`, `tail_1/2`). They are deformed and posable by name; no engine behaviour drives them yet |
| `contiguous_chains` | Role chains whose engine algorithm (two-bone IK) needs parent and grandparent to be the chain |
| `discarded` | Rig information that does not survive export, stated explicitly |

Two profiles exist: `humanoid_rigify/1` (production) and `humanoid_toy_fixture/1` (test only). Adding a character
type means writing a profile, plus requirement entries for any new engine behaviour. Importer and format stay the
same.

## Export rules (what is preserved and what is lost)
- **Every deform bone is exported**: role bones, Rigify twist bones (`DEF-*.001`), palm and helper bones, and
  rig-specific bones. Skin weights are not merged.
- Role bones get their engine role name; all other bones keep their source name (`source_name` is recorded for every
  bone).
- Non-deform bones (Rigify `ORG-`, `MCH-`, controls) are not exported. A bone's parent is its nearest deform
  ancestor.
- **Re-parenting (recorded in `reparented`):** in a contiguous chain, a role bone whose deform parent is a helper is
  re-parented to the previous role. For the boy these are `forearm`, `hand`, `shin` and `foot`; their parents were
  the Rigify twist bones. The twist bones stay, as children of their original role bone.
- **Discarded, as listed in each package:**
  - Rigify's constraint-driven twist distribution: twist bones follow their role bone rigidly, because the engine
    evaluates no constraints;
  - non-deform control and mechanism bones;
  - bone roll and rest orientation: engine rest frames are axis-aligned at each pivot. Skinning is unaffected;
    authored rotations are in engine axes.
- Up to 4 influences per vertex, normalised. A vertex without deform weights fails the export.
- Coordinates: Blender (+Z up, faces −Y) → engine (+Y up, faces +Z): (x, y, z) → (x, z, −y), in metres.

## Package format (`character.json`, version 1)
| Key | Content |
| --- | --- |
| `format`, `version` | `plush.imported_character`, `1` |
| `name`, `source` | character id; source file name and sha256, spec hash and version, Blender version |
| `profile` | name, kind, required roles |
| `skeleton` | ordered list (parents first): `name`, `source_name`, `kind` (`role` / `helper` / `rig_specific`), `parent`, `head` (rest pivot, engine coordinates) |
| `reparented`, `roles_present`, `rig_specific_bones`, `discarded` | as above |
| `materials` | engine material JSON (`name`, `baseColor`, `roughness`, `sheen`) |
| `meshes` | per (object, material): `part`, `source_object`, `material`, `vertices`, and arrays `positions` (f32×3), `normals` (f32×3), `indices` (u32), `joints` (u16×4), `weights` (f32×4) |
| `morphs` | `name`, `mesh`, arrays `vertices` (u32) and `dpos` (f32×3) |
| `capabilities` | per engine behaviour: **data** `available` or `missing`, with the missing roles. Not proof of support |
| `files` | `geometry.bin` byte count and sha256 |

Arrays are `{offset, count, dtype}` into `geometry.bin` (little-endian); `count` is the number of scalars. Skinning
convention: rest positions are in rest world space and the skinning matrix is `boneGlobal · translate(−head)`, so the
rest pose reproduces the rest mesh exactly (tested, error < 1e-5 m).

## Behaviour support, as tested (`tests/test_imported_character.cpp`)
| Behaviour | boy_yellow_hoodie 1.0.0 | toy fixture (engineering test) | Reason when not supported |
| --- | --- | --- | --- |
| Rest skinning | **supported** (exact) | **supported** | — |
| Reach / two-bone IK | **supported** (hand error 0.0003 mm, mesh follows) | **supported** (0.0001 mm) | — |
| Look-at (eyes) | **supported** (axis error 0°, eye mesh moves 13 mm) | **supported** (9 mm) | — |
| Expressions (morph weights `expr.<name>`) | **supported** (Blink, BrowDown, Smile, JawOpen) | **supported** (Squint, Puff) | Names are the character's own; the engine's expression presets (smile, frown, surprise) are not mapped to them |
| Blink in the life layer | **unsupported** | **unsupported** | The life layer rotates `lid.L/R` bones by a fixed 86°. Both packages blink with morphs and have no lid bones. A lid bone would reproduce the 62° overshoot problem fixed in F01 |
| Grasp / hand pose | **unsupported** (chains resolve, 5 fingertips, but contact misses by 46 mm) | **unsupported** (no fingers, by design) | The engine hand code assumes its own rest pose: fingers hanging along −y, palm facing −x. An A-pose import has neither. Rigify's third phalanx stays a helper (the engine uses 2 joints) |
| Walk (scene action) | **supported** (3/59 sliding frames, limit 6; 22 mm foot lift) | **partial** (root reaches the target and feet lift, but 8/59 sliding frames) | The walk action uses a fixed 0.11 m step, not scaled by leg length |
| Idle (life layer: breathing, sway, head drift) | **supported**, deterministic | **supported** | — |

Status is pinned in the tests: if an engine fix changes it, the test fails and this table must be updated.

## Engine assumptions found (candidates for small, generic engine fixes; not made here)
1. Walk step length is a constant (0.11 m): it should scale with leg length from the skeleton.
2. The hand convention is fixed: palm and finger axes should come from the hand's own rest geometry, or from the
   profile.
3. Blink is lid-bone only: it should also accept a blink morph, mapped through the profile or package.
4. Expression presets are hard names: a per-character expression map belongs in the package.

## Commands
```bash
blender -b --factory-startup -P pipeline/charsys/export_engine.py -- --blend assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend --profile pipeline/charsys/rig_profiles/humanoid_rigify.json --out out/pkg_boy
```
```bash
python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>
```
```bash
ctest --test-dir build
```
