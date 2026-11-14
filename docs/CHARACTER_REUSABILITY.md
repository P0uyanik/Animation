# Character reusability: shared infrastructure vs. character data (assessment, 2026-11-14)

Status levels:
- **verified-generic**: proven with more than one character.
- **parameterised**: driven by data, but proven on one character only.
- **character-specific**: written for the boy.
- **missing**.

Rule: shared logic reads character dimensions from the spec or the built geometry (landmarks, mesh measurements),
never from constants. Generic reuse is only claimed after a second, different character (planned, not started).

| System | Current implementation | Shared or character-specific | Reusability gap | Next action |
| --- | --- | --- | --- | --- |
| Character spec & assembly | `pipeline/charsys/spec.py`, `build_character.py` (component collections, metadata, embedded spec) | parameterised | Part list and object-name → component map are fixed to the boy's parts | Move the component map into the spec when a second character needs it |
| Body, clothing, accessories geometry | `body_v6.py` (head, hoodie, trousers, shoes, backpack) | **character-specific** (reads spec proportions, but garment shapes are the boy's) | No garment library; a girl would need new part builders | Later: garment modules (top, bottoms, shoes, bag) with spec parameters; not before the second-character test |
| Rigging & weights | Rigify human metarig fitted to measured joints; heat weights + allowed-bone filter + nearest-bone fallback + 4-influence limit (`body_v6.fit_metarig`, `rig_character`) | parameterised (Rigify is generic; joint fitting uses the boy's Z table) | Joint positions come from boy-named landmarks; the allowed-bone table uses boy object names | Express joints and weight rules in the spec |
| IK/FK, hands, fingers | Rigify IK/FK limbs, 3-joint fingers; `episode.apply_pose` switches FK | generic (Rigify) | No grasp or pose library on the Blender rig | Bridge to the engine's grasp (below) |
| Facial controls | Rig properties `face_*` driving shape keys (`build_character.add_face_controls`); `face.py` Blink `lid_seam/1` derives the closing angle from the lid meshes | parameterised (control layer generic; Blink measures geometry; Smile still has a boy-tuned frown constant) | `lips_jaw/1` (experimental F02) adds lips, interior and a `DEF-jaw` bone sized from landmarks and spec; cheek/eye coordination for Smile missing; expression set fixed to 4 | Cheek/eye coordination as a reusable expression layer; then test on the second character |
| Eyes | Eyeball + lid shells + lashes (`body_v6.build_eyes`), gaze bones | parameterised (EYE_X, EYE_R from spec) | Lid shapes tied to the boy's half-closed look | Keep; lid opening as a spec parameter later |
| Hair geometry | `hair.py`: `hair_clumps/1` (v6) and `/2` (lock families on the spec's hair ellipsoid, scalp cap derived from the head mesh) | parameterised (families, ellipsoid, hairline are data) | Fringe positions are boy data inside the code; no secondary motion | Move the fringe into the family data; hair dynamics later |
| Fur / surface fibres | `geom.add_fur` driven by `spec.fur` | parameterised | Evaluation only: not in master or glb, does not follow the rig | Later: USD/Alembic or engine-side fur |
| Materials | Procedural, albedos from `spec.materials` (calibrated) | parameterised | No shared "world material" library | World standard materials doc and library (later) |
| Animation & behaviour | **C++ engine** actions + life layer; **imported-character adapter** (`export_engine.py`, rig profiles, `engine/model/imported_character.*`, scene loading) | adapter verified on 2 packages (boy + engineering fixture): reach, look-at, expressions, idle supported; walk supported for the boy, partial for the fixture; grasp and life-layer blink unsupported | Engine assumptions: fixed walk step, fixed hand convention, lid-bone-only blink, hard expression names (`docs/ENGINE_CHARACTER_PACKAGE.md`) | Small generic engine fixes (each with your go-ahead); a real second production character later |
| Physics & interaction | Engine: contact grasp (sphere, cylinder), touch ≤ 6 mm, no skating | verified-generic in the engine | Same bridge gap; no cloth or hair dynamics anywhere | After the bridge |
| Asset management | `asset_store.py` (immutable hashed versions, identity lock, approve, restore), `episode.py` (link + override) | parameterised (character id is an argument; tests use the boy) | Never run on a second character | Second-character test |
| Validation & evaluation | Harness (camera-matched views), silhouette/contour/landmark/ΔE metrics, `face_test.py`, `reuse_test.py`, `verify_charsys.py` | parameterised (reference index per character) | Region IDs and landmark names assume the boy's materials and face | Map regions from the spec |
| World standards | Scale (1.10 m boy), lighting in the harness, plush materials | partly implicit | No written world standard | Write a short world-standards spec when the second character starts |

## Proof of reuse so far
- **Proven:**
  - one character, many episodes (link + override, `reuse_test.py`);
  - versioning and restore (`test_store.py`);
  - spec-driven rebuild equals v6.
- **Not proven:** any shared system working on a second character. Engine actions are proven on several engine
  characters, but not on Blender-built assets.
