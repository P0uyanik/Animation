# Second production character: reference analysis and platform assessment

_2026-11-14. Status: analysis only. Nothing modelled or implemented. The 17 references are stored unchanged in
`assets/characters/girl_auburn_bun_glasses/references/uploads/` (`intake_index.json`: sha256 and content of each
image). Canonical id confirmed: girl_auburn_bun_glasses._

## 1. Who the character is, and conflicts in the collection
The collection describes **the brown-haired girl with round glasses**. She is the main subject of 15 of the 17
images.

| Conflict | Evidence | Proposed resolution |
| --- | --- | --- |
| Label "Character A" vs "Character B" | #30, #33, #36, #39, #40, #42 say A or character_a; #31, #35, #37 say B or character_b | Use a descriptive permanent id, not a letter (see question 1) |
| #37 outlines a different character | The skeleton blueprint shows the **white-haired girl in a dress** (twin buns, bow, skirt) | Use #37 only for the bone-hierarchy idea; not for her shape |
| #31 and #32 show three characters | The boy, this girl and the white-haired girl together | Use them only for world scale (relative height) and style consistency |
| Hair length | Long curls to the mid-back (#30, #33, #36, #39, #40) vs shoulder length (#31 row 2, #45, #46) | Question 2 |
| Neutral expression | Open happy smile in most full-body views; closed soft smile in #34 "Neutral" and #45 "Neutral" | Question 3 |
| Eye colour | Brown everywhere, except blue in #30 "Surprised", "Angry", "Sad" (those tiles also lack glasses) | Brown; the blue tiles are generator errors (no question needed) |
| Absolute measurements | Numbers like "181.8 cm", "3.2 m", "70 mm" are inconsistent with each other | Ignore all numbers; measure proportions from silhouettes only, as for the boy |

## 2. Character specification
Legend: **R** = directly supported by several references; **U** = uncertain or conflicting; **I** = inferred by me,
needs your confirmation.

| Area | Specification | Evidence |
| --- | --- | --- |
| Silhouette / proportions | Chibi plush doll; large head (about 1/3 of the height including the bun); short limbs; slightly wider stance than the boy; A-pose for modelling (#30, #45 at 10°). **R** | #30 proportion sheet, #45 neutral pose |
| World scale | About the boy's height, slightly shorter without the bun; the bun reaches about the boy's hair top. **U** | #31 bottom row, #32 |
| Head / face | Round face, full cheeks with pink blush, small nose bump, ears visible (rounded, low). **R** | #30, #33 01, #34 |
| Eyes | **Large, round, fully open** (very different from the boy's half-closed sleepy eyes); brown iris, dark pupil, two white highlights; upper lash line with 2–3 outer lashes; lower lash hint. **R** | #30, #34 eye controls, #46 |
| Brows | Thin, soft brown, high above the eyes, partly hidden by the fringe and glasses frame. **R** | #34 |
| Mouth | Small; open smile showing teeth and a pink tongue in "happy"; closed soft smile in some neutrals. **R / U** | #34 mouth & jaw controls, #30 |
| Glasses | Large round thin frames (dark brown / copper), bridge, temples to the ears; clear lenses; low roughness. **R** | all; #42 callout |
| Hair: style | Dark auburn/brown felted wool. Side-swept fringe parted slightly off-centre, covering the forehead to the brows. A **large high bun** on the crown (single, made of interlocking wavy bundles). **Long spiral curls** down the back and sides (length: question 2). **R / U** | #30, #39 01/05/06, #40 |
| Hair: surface | Matte, fuzzy halo, irregular felted matting, fibre stray-aways; no sheen. **R** | #39 04, #42 |
| Hair accessories | 2–3 **pink felt flowers** with yellow centres, plus a soft **blue-grey band (scrunchie)** at the bun base. **R** | #39 06, #42 |
| Shirt | Cream / off-white collared blouse; button front (4–5 small buttons); **puffy long sleeves** gathered at the cuffs; visible fibres. **R** | #41, #42 |
| Vest | Open (unbuttoned) dusty-rose / mauve **bouclé** vest; dark brown **embroidered motifs** (bow / X shapes and small flowers) on both front panels; patch pockets; small wooden buttons; plain back. **R** | #41 A, #42 |
| Shorts | Sage-green felted wool **bloomer shorts**; gathered cuffs above the knee; 3 buttons at the waistband. **R** | #41, #42 |
| Legs | Bare skin legs (no socks visible above the boots). **R** | #30, #41 |
| Boots | Brown **fluffy fleece boots** (rounded, chunky); darker brown soles; plush cuff; stitching. **R** | #41, #42 |
| Hands | 5 fingers (thumb + 4), each finger 3 joints (MCP, PIP, DIP); chubby; **independent thumb opposition**. **R** | #35, #44 |
| Skin material | Soft matte vinyl with subtle subsurface scattering; pale peach. **R** | #42 |
| Skeleton | root → pelvis → spine.01 → spine.02 → chest → neck → head; clavicles; upper arm, forearm, hand, fingers; thigh, shin, foot, **toe**. IK/FK limbs with pole targets. **R** | #36, #37, #38 |
| Expressions | Neutral, smile/happy, laugh, sad, surprise, anger, frown, confusion, squint, wide-open, blink, left/right eye closed, mouth open, brows up/down. **R** | #30, #34, #45 |
| Hair motion | Secondary motion: bun (high inertia), fringe, side-lock chains, back curl chains, collision volumes, spring/damping. **R** | #40 |
| Clothing motion | Cloth layers with collision boundaries; volume preservation at elbows, knees and bloomers. **R** | #36, #41 B, #45 05 |
| Interaction | Precision pinch, power grasp, open-hand support; pick-up sequence; carry a book; sit on a chair; table reach; foot contact. **R** | #35, #44, #46 |
| Actions | Walk, run, jump, land, sit, squat, arms raised, wave. **R** | #36, #45 07, #46 |
| UV / textures | Full UV layout and PBR maps (albedo, roughness, normal, fuzz). **R** (production practice, not identity) | #42, #43 |

**Evaluation views** (reference-to-implementation mapping). They are camera-matched as for the boy, in a new
reference index:
- **Identity authority:** #30, top row (6 views: front, front-left, left, right, back-right, back). It is the cleanest
  turnaround, with neutral lighting and the same A-pose.
- **Secondary checks:** #45 01 (F, ¾, S, B); #41 garment turnaround (body without head); #46 top row.
- **Face:** #34 blendshape matrix (expression targets); #30 face tiles.
- **Hair:** #39 01–06 (construction); #30 back views (curl layout).
- **Materials:** #42 sphere swatches (colour targets for automatic calibration, as for the boy).
- **Hands and interaction:** #35, #44; tested with the engine behaviour tests, not by image comparison.

## 3. Platform assessment (evidence from the current code)
| Requirement | Classification | Evidence / current state |
| --- | --- | --- |
| Spec, versioned store, episode linking, reuse tests | **Already supported** | `spec.py`, `asset_store.py`, `episode.py`, `reuse_test.py` take the character id as data |
| Rigify rig with 3-joint fingers, IK/FK, eye bones | **Already supported** | Rigify human metarig (`body_v6.rig_character`) |
| Engine import and behaviours (reach, look, grasp, walk, idle, morph blink, expression map) | **Already supported** | `export_engine.py` + `humanoid_rigify` profile; TD-38/TD-39; tested on the boy and the fixture |
| Proportions, albedos, colour calibration | **Supported through configuration** | `spec.proportions`, `spec.materials`, `calibrate_colors.py` |
| Fringe, top layer, mouth (`lips_jaw/2`), smile coupling, closed-lid flatten | **Supported through configuration** | `hair.py` fringe block and families; `face.py` |
| **Rig joint fitting** | **Requires a reusable improvement** | `body_v6.fit_metarig` places joints from the boy's `Z` height table, and the weight rules (`allowed_bones`) use the boy's object names |
| **Body and garment generators** | **Requires a reusable improvement** (largest gap) | `body_v6.build_hoodie`, `build_legs`, `build_shoes` and `build_backpack` are the boy's outfit. No shirt, collar, open vest, bloomers or boot generators exist; `build_character.COMPONENTS` maps the boy's object names |
| **Open eyes and eyelids** | **Requires a reusable improvement** | `build_eyes` builds half-closed lid shells for the boy. She needs fully open eyes with lash lines, highlights and different lid rest states; `face_test` assumes `eye.L` / `lid_upper.L` names |
| **Expression library beyond 4 keys** | **Requires a reusable improvement** | `spec.face.expression_shape_keys` = Blink, BrowDown, Smile, JawOpen. Needed: sad, surprise, anger, frown, squint, wide-open, per-eye blink, brows up, laugh |
| **Teeth and tongue for the open smile** | **Requires a reusable improvement** (optional component) | `lips_jaw/2` has a shaded interior only. Her "happy" shows teeth and a tongue: an optional mouth-interior component configured per character |
| **Long curly hair and bun** | **Requires a reusable improvement** | `hair_clumps/2` builds short locks over the scalp (azimuth/elevation, one origin). It has no long hanging locks, spiral curls, bun primitive or accessory attachment |
| **Accessories (glasses, flowers, band)** | **Requires a reusable improvement** | Only the boy's backpack exists (character-specific). Needed: a generic accessory module (rigid parts attached to a bone, placed by landmarks) |
| **Patterned textiles (vest embroidery)** | **Requires a reusable improvement** | Materials are uniform procedural albedos. Needed: per-material decal or texture support |
| Felted fibre surface on hair, shirt, vest, boots | **Partly supported** | Fur curves exist (`spec.fur`), but only in the evaluation file; the shader-only approach was ineffective (H31) |
| Toe bones | **Supported by Rigify, not used** | The engine has no `toe` role; adding an optional role is a profile change |
| Actions sit, run, jump, squat, wave | **Not currently supported** (engine) | Engine actions: look, expression, reach (grip/lift/place/release/lean), touch, walk |
| Precision pinch and power-grasp variants | **Partly supported** | Engine grasp: sphere or cylinder contact, all fingers; there is no pinch (thumb + index only) mode |
| Hair and cloth dynamics, collision | **Not currently supported** | No secondary-motion or cloth system in the pipeline or engine |
| UV unwrapping and PBR texture maps | **Not currently supported** | Procedural materials only |

## 4. Limitations → smallest generic improvements
| # | Limitation (evidence) | Generic or specific? | Smallest generic improvement | Benefit for future characters | Validation on both characters |
| --- | --- | --- | --- | --- | --- |
| G1 | Rig fitting reads the boy's `Z` table | generic gap | Joint positions from spec landmarks or proportions (`spec.rig.joints`), with the boy's values as his spec data | Any humanoid body fits the same rig builder | Boy rebuild equals v6; girl rig from her spec |
| G2 | Garments are the boy's code | generic gap | A garment module library (top/shirt with collar, sleeve type, cuffs; open vest; trousers/shorts with leg shape; boots/shoes), each from spec parameters; the component map from the spec | New outfits by configuration | The boy's hoodie path untouched (v6 equality); girl's outfit from spec |
| G3 | Eyes are half-closed shells | generic gap | Eye module with lid rest openness, lash style and highlights as parameters (the boy = sleepy, the girl = open) | Every eye style by configuration | `face_test` on both (blink covers the eye, gaze) |
| G4 | 4 expressions only | generic gap | Expression library: named, landmark-driven deformation layers (brows up/down, frown, O-mouth, squint, per-eye blink), driven by the existing rig controls and the engine expression map | Shared expressions; characters tune intensities | Expression sheet on both; engine export morph names |
| G5 | No teeth or tongue | generic, optional | Mouth-interior components (teeth row, tongue) as optional spec parts in `lips_jaw/2` | Characters choose | Girl: on; boy: off (unchanged) |
| G6 | Short locks only | generic gap | Hair "strand-lock" family: long locks along a guide curve with spiral curl (radius, pitch, phase), and a "bun" family (wound bundles at a scalp anchor) | Long, curly, bun and ponytail hairstyles by configuration | Synthetic-head test plus the girl; the boy's H28 unchanged |
| G7 | No accessories module | generic gap | Accessory parts (primitive or parametric, e.g. glasses from eye landmarks; flowers and band at a hair anchor) bound rigidly to a bone | Hats, glasses, bows, bags by configuration | Girl glasses; boy backpack later migrated (optional) |
| G8 | Uniform materials | generic gap | Per-material decal or texture slot (image or procedural motif), configured in the spec | Patterned clothes | Girl vest; the boy is unaffected |
| G9 | No toe role, no sit/run/jump | engine scope | Optional `toe` role in the profile; new engine actions are separate later milestones | Shared behaviours | Engine behaviour tests on both packages |

**Character-specific (stays in her spec and assets):** her proportions, colours, eye and lash style, curl layout,
bun shape, flower and band design, embroidery motifs, outfit parameters, and movement-style parameters.

## 5. Proposed milestones (each tested on both characters; nothing published without approval)
1. **M1, reference package:** reference index (camera-matched views from #30 top row and #45), silhouettes and
   landmarks, measured proportions, colour targets from #42, spec skeleton. No geometry.
2. **M2, generic body and rig fitting (G1):** body proportions and joint fitting from the spec. The boy must rebuild
   unchanged. The girl gets a base body with rig, engine export and behaviour tests.
3. **M3, face (G3, G4, G5, G7 glasses):** open eyes, expression library, teeth and tongue option, glasses accessory.
4. **M4, hair (G6, G7 accessories):** fringe, bun, long curls, flowers and band.
5. **M5, garments and materials (G2, G8):** shirt, vest with motifs, bloomers, boots; colour calibration.
6. **M6, integration:** engine package and behaviour tests on three packages; version proposal for your review.

Later and not scheduled: hair and cloth dynamics, sit/run/jump actions, pinch grasp, UV/PBR textures.

## 6. Questions (only what cannot be resolved from the references)
1. **Canonical id:** `girl_brown_glasses`? The engine already has an older SDF character with that name
   (`content/characters/girl_brown_glasses.character.json`, iteration 4); the new asset would get the same id in
   the charsys store.
2. **Hair length:** long curls to the mid-back (#30, #33, #39, #40) or shoulder length (#31, #45, #46)?
3. **Neutral expression:** a closed soft smile (#34, #45), with the open happy smile as the "happy" expression?
4. **Height relative to the boy (1.10 m including hair):** about the same, as in #31 and #32? Proposal: body
   slightly shorter, with the bun top level with his hair top.


## Gap status after M3 (2026-11-14)
- **G3 (open eyes)** and **G4 (expression library):** built as shared systems (`face_generic/1`, `face_library/`).
- **G5 (teeth and tongue):** built as oral layers.
- **G7:** glasses built (`accessories.py`); flowers and band remain for M4.

See `docs/second_character/M3_FACE_SYSTEM.md`.
