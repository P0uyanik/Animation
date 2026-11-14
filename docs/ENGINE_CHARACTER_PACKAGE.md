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

## Character settings carried by the package (optional keys)
| Key | Meaning | Source |
| --- | --- | --- |
| `expressions` | Engine expression name → this character's morph (e.g. `blink → Blink`, fixture `blink → Squint`). The `expression` action resolves through it; an unknown expression is reported in `SceneEvaluator::warnings()`, not silently dropped | profile `expressions`, extended per character by the generic face (collection property `ps_engine_expressions`: e.g. `happy → Smile`, `sad → Sadness`, `surprised → Surprise`); only morphs that exist are kept; `expressions_missing` lists the rest |
| `walk` | `step_length` (m) or `step_scale` (× leg length); default `0.11 / 0.3451` per metre of leg, which keeps the original chibi characters at exactly 0.11 m | profile `walk` (optional) |
| `hands` | `{"L": {"finger_dir": [...], "palm_normal": [...]}, "R": ...}`. Without it the importer derives each hand frame from its finger geometry | profile `hands` (optional) |

Engine side (generic, for every character):
- **Walk** step = `walkStep(asset)`: explicit length, else scale × leg length (thigh → shin → foot).
  - Foot lift and pelvis motion scale with the step.
  - Each swing now uses about 85% of its interval, so both feet are briefly planted at every hand-over (double
    support). Previously both feet moved at hand-overs; this was visible with short steps.
- **Hands:** `Skeleton::handL/handR` (`HandFrame`) gives curl, spread and thumb axes. A zero frame reproduces the old
  convention exactly (existing characters unchanged).
  - Any subset of at least two digits works.
  - A hand with fewer digits is "no hand": grasp is unsupported and nothing is posed.
- **Blink:** if `expressions.blink` names a morph, the life layer drives that morph (`blinkAmount`) and does not rotate
  lid bones (`LifeParams::blinkLids = false`). Lid-bone characters are unchanged.
- **Expressions:** `resolveExpression(asset, name, morphs)`. A map entry wins, else the morph name itself, else a
  warning.
- SDF character files accept the same optional `expressionMap` and `walk` keys.

## Behaviour support, as tested (`tests/test_imported_character.cpp`)
| Behaviour | boy_yellow_hoodie 1.0.0 | toy fixture (engineering test) | Notes |
| --- | --- | --- | --- |
| Rest skinning | **supported** (exact) | **supported** | — |
| Reach / two-bone IK | **supported** (0.0003 mm) | **supported** (0.0001 mm) | — |
| Look-at | **supported** (0°, eye mesh 13 mm) | **supported** (9 mm) | — |
| Expressions by engine name | **supported** (blink, smile, jawOpen, browDown → own morphs) | **supported** (blink → Squint, surprise → Puff); `smile` **missing**, reported as a warning | — |
| Blink in the life layer | **supported** via morph `Blink` (morph vertices move 48 mm when closed) | **supported** via morph `Squint` (13 mm) | No lid bones used |
| Grasp / hand pose | **supported** both hands: hand frame derived from fingers; all 5 fingertips rest on a stick held between thumb and fingers (worst gap 4.5 mm = finger-tube radius) | **unsupported**: no finger roles, hand frame "none", by design | Hand orientation is verified independently: a rotated skeleton gives exactly Q × the original fingertips (≤ 0.0001 mm); a 3-digit hand grasps |
| Walk | **supported**: step 83 mm from 261 mm legs, 1/59 frames with both feet moving | **supported**: step 54 mm from 170 mm legs, 0/59 | Chibi reference walk: 2/59 (was up to 6) |
| Idle | **supported**, deterministic | **supported** | — |

**Second production character** (`girl_auburn_bun_glasses`, packages `_m2` without face, `_m3` with the generic face):
- `_m3` look-at: 0°, eye meshes move 11 mm.
- `_m3` life-layer blink: via `Blink`.
- `_m3` semantic expressions: happy, sad, surprised, angry, laugh, squint, confused, frown, blink and jawOpen all
  resolve and move the face (2.9–61.6 mm).
- `_m2` reports blink and expressions as unsupported.
- Engine morphs are linear: the face's blink in-between keys are exported as extra morphs but the engine does not
  chain them. The `DEF-jaw` bone is not driven by engine expressions (Blender driver only).

Remaining limitations:
- Only humanoid profiles exist. The finger-role naming (`thumbA/B`, `f0..f3`) is the engine's humanoid hand model;
  other limb types need their own behaviour definitions later.
- Hand-frame derivation assumes index and pinky (or thumb) define the across-hand direction, which is a humanoid hand
  convention. Other hands supply `hands` metadata.
- Grasp is measured with the engine's convention: a stick across the hand. Arbitrary object shapes are not tested.
- Walk timing (frames per step) follows the action's duration. Very short legs over long distances give a fast
  cadence; there is no speed limit.
- The fixture validates the adapter only, not production of a second character.

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
