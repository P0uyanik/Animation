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
| Animation & behaviour | **C++ engine** actions + life layer; **imported-character adapter** (`export_engine.py`, rig profiles, `engine/model/imported_character.*`, scene loading) | adapter verified on 2 packages (boy + engineering fixture): reach, look-at, expressions, idle supported; all behaviours supported for the boy; fixture all except grasp (no fingers, by design); walk, hands, blink and expressions driven by character data (TD-39) | Humanoid profiles only; grasp tested with a stick across the hand | A real second production character; non-humanoid profiles when needed |
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


## Face and hair after CP-2 (2026-11-14)
| System | Shared logic | Character configuration | Remaining assumptions | Needed for a very different face or hairstyle |
| --- | --- | --- | --- | --- |
| Lips / mouth (`lips_jaw/2`) | seam layout, interior, jaw bone and weights from landmarks | `spec.face.mouth` (size, frown, materials, offsets, colours, jaw angle) | horizontal slit mouth; `face_y` ray cast | mouth types without a slit (beak, muzzle) need another generator |
| Eyes / blink (`lid_seam/1`) | closing angle from lid edges; offset, thickness, flatten | `spec.face.blink` | spherical eye looking along −Y; shell lids | non-spherical eyes need lid geometry from the eye mesh |
| Smile coupling | cheek and corner deformation from landmarks; squint | `spec.face.smile_coupling` | `eye_L/R` and `mouth` landmarks; one symmetric smile | per-side intensities; other expressions (frown, surprise) as coupled layers |
| Hair (`hair_clumps/2`) | lock families, scalp cap, irregularity | `spec.hair.params` | hair-ellipsoid placement; fringe positions inside the generator | surface-projected placement; fringe as family data |

**Before a second production character is a genuine end-to-end reusability test:**
1. Garment builders as parameterised modules (today `body_v6.py` is boy-specific).
2. Component map and weight rules from the spec, not object names.
3. Fringe as family data; surface-projected hair placement.
4. Region mapping for the metrics from the spec.
5. A reference package and landmarks for the new character.


## Face and hair genericity after the CP-2 system step (2026-11-14)
| Category | Face (`face.py`) | Hair (`hair.py`, `hair_clumps/2`) |
| --- | --- | --- |
| Shared implementation | Lips and seam layout; interior with shaded depth; jaw bone, weights and corner-centred ramp; blink with derived closing angle, flatten and lash; smile coupling (cheeks, corner follow, squint) with intensity and asymmetry | Lock families; crown; fringe block; irregularity; lock-shape variation (curve, tips, splits); felt shader; scalp cap with configurable face cut; ellipsoid or real-scalp placement; scalp or ellipsoid base |
| Character configuration | `spec.face.mouth` (size, frown, lips, seam, colours, smile and jaw shaping, jaw band), `spec.face.blink`, `spec.face.smile_coupling` | `spec.hair.params` (families, fringe, irregularity, shape, placement, offsets, hairline, felt), `spec.fur` |
| Inputs | Head mesh (ray-castable face), eye and lid meshes, landmarks `eye_L/R`, `mouth`, `ear_L/R`, `chin`, `Z.mouth` | Head mesh (closed, for surface placement), projection origin (hair ellipsoid centre), hairline heights |
| Assumptions | Spherical eyes looking along −Y; shell lids; slit mouth; `face_y` falls back to a fixed depth (−0.14 m) if a ray misses; one smile shape with left/right scaling | Azimuth/elevation parametrisation around one origin (no long hair or ponytails); face cut is a box; fringe tips placed on the face by `face_y` |
| Verified independence | Synthetic proportions (G01): all criteria hold, derived values adapt | Synthetic egg head: runs with its own configuration; roots on the scalp (0.0 mm); 96.9% coverage |
| Not verified | Other face topology (another head mesh, muzzle or beak mouth); other eye shapes | Other hairstyles on a production character; long hair; hair dynamics |
| Future usability | A new humanoid face needs only its spec values and landmarks; the same tests (`face_test.py`) apply | A new hairstyle is a configuration: families, fringe and hairline. Surface placement removes the ellipsoid dependency; the synthetic test is a template for the next character |


## Body and rig after M2 (2026-11-14)
| System | Status | Evidence |
| --- | --- | --- |
| Body generation (`body_generic/1`) | shared; parameterised; used by the girl and the synthetic G02 | girl meets the M1 measurements; G02 builds at 1.5 m |
| Rig fitting | shared via `rig_profiles/rigify_human_metarig.json` | 410 / 73 bones for both; joints exactly as specified |
| Weight rules | role-based with profile defaults (eye bones only drive eyes) | gaze deforms nothing without eye meshes (C++ test) |
| Component map | from the spec (legacy default for the boy) | — |
| Boy | **legacy path** (`body_v6`, literal joints, name-based rules) | convergence plan in `docs/second_character/M2_GENERIC_BODY_RIG.md` |


## Face after M3 (2026-11-14)
| System | Status | Evidence |
| --- | --- | --- |
| Eyes, lids, lashes, highlights (`face_generic/1`) | shared; parameterised; used by the girl and the synthetic G03 | girl and G03 `face_system_test` |
| Blink (`lid_seam/1` in the eye frame, in-betweens on the arc, per eye) | shared; verified on 2 configurations | Blink 0%, partial blinks monotonic, 0 eyeball/lid intersections |
| Mouth (`lips_jaw/2` + extra shapes + oral layers) | shared; girl with teeth and tongue, G03 without | Smile: teeth 18%, tongue 12% |
| Expression library (13 action units, 14 + 2 presets) | shared data; per-character intensity, scale, overrides | girl 15 presets, G03 13 presets at intensity 0.7 |
| Accessories (`glasses/1`) | shared; round (girl) and rectangular (G03) | 0 intersections in every state and gaze |
| Engine expressions | per-character names merged at export; no engine change | 10 semantic expressions tested in C++ |
| Boy | **legacy face path** (`body_v6.build_eyes`, F09 config) | unchanged (36/36 face_test values) |

**Remaining assumptions:**
- humanoid front-facing face with two eyes;
- horizontal slit mouth;
- spherical eyes for large gaze;
- ellipsoid ears and a bump nose;
- glasses need ear landmarks for the temples.


## Facial engine after M3.1 (2026-11-14)
| Capability | Shared mechanism | Character data | Characters |
| --- | --- | --- | --- |
| Arc-correct blinks and presets in the engine | package `morph_inbetweens` + `expandInbetweens` | the face's in-between keys | girl (G03 builds them too; it has no engine package) |
| Expression-driven bones (jaw) | package `expression_bones` + scene pose step | jaw angle, preset weights | girl; packages without it stay morph-only (boy 1.0.0, fixture) |
| Blink timing | package `blink` + `LifeParams` | `spec.face.blink.timing` | girl custom; boy defaults |
| Oval eyes under gaze | gaze envelope → lid clearance | `eyes.scale`, `eyes.gaze_range_deg` | G03 (oval), girl (sphere: unchanged) |
