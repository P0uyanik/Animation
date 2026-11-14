# Character Production Pipeline (`charsys`)

_2026-11-14. Status: implemented and tested in the cloud with Blender 5.3.0 (Python module). Not yet run with your
own Blender. The v6 pilot (`pipeline/blender/boy_pilot/`) and its frozen baseline are unchanged and remain the
reference implementation. The C++ engine is unchanged; iteration 5 has not been started._

## 1. What it is
The automated `boy_yellow_hoodie` pilot is now a reusable, versioned pipeline:

1. A character is described once, in a **spec** (JSON).
2. `charsys` **builds** it headless in Blender from that spec.
3. The result is **published** once into an immutable, hashed **version** in the asset store.
4. Episodes **link** that version. They never copy or rebuild it.

```
spec.json ──► build_character.py ──► build folder ──► asset_store.py publish ──► versions/<x.y.z>/  (read-only, hashed)
 (+ override)   (body_v6, hair, rig,     (master,                                 │
                 face controls)           glb, compare)                            ├─► episode.py: link + override ──► shot .blend
                                                                                  └─► .glb ──► other tools / engine import
```

**Proven by test:** charsys rebuilds v6 exactly. All 55 objects have the same vertex, face, vertex-group, shape-key
and material counts. Bounding box, centroid and spread differ by **0.0 m**. One object's exact coordinate hash
differs through float rounding, the same informational difference the v6 reproduction kit shows.

## 2. Asset architecture
Each concern is separated in four places: the spec, the code, the master file and the published version.

| Concern | Spec section | Code | In the master `.blend` | In the published version |
| --- | --- | --- | --- | --- |
| Identity and proportions | `identity`, `proportions` | `body_v6.configure()` | root collection `boy_yellow_hoodie`, properties `ps_character_id`, `ps_spec_sha256` | `spec.json`, `manifest.json` |
| Body mesh | `body` | `body_v6` (head, neck, hands) | `boy_yellow_hoodie.body` | master, glb |
| Face and facial controls | `face` | `body_v6` (eyes, lids, lashes, brows, mouth, ears, shape keys); `build_character.add_face_controls` | `boy_yellow_hoodie.face`; rig properties `face_Blink`, `face_BrowDown`, `face_Smile`, `face_JawOpen` drive the shape keys | master; glb morph targets |
| Hair geometry and settings | `hair` (generator, seed, params), `fur[hair]` | `hair.py` (`hair_clumps/1`) | `boy_yellow_hoodie.hair` | master |
| Clothing | `clothing` | `body_v6` (hoodie, trousers, socks, shoes) | `boy_yellow_hoodie.clothing` | master, glb |
| Accessories | `accessories` | `body_v6` (backpack, charcoal-plum) | `boy_yellow_hoodie.accessories` | master, glb |
| Rig and skin weights | `rig` | `body_v6.rig_character` (Rigify, heat weights + cleanup) | `boy_yellow_hoodie.rig` (410 bones, 73 deforming); weights on each mesh | master, glb skin |
| Materials and textures | `materials` (calibrated albedos, target colours), `fur` | `body_v6.make_materials` (procedural; no image textures) | material datablocks in the same file | master |
| Animation compatibility | `animation` | `build_character.animation_compat` | — | `animation_compat.json`: deform and control bone names, shape keys, facial controls, rest pose |
| Metadata and version | `metadata` | `spec.py`, `asset_store.py` | root collection properties; embedded text `ps_character_spec.json`; asset-marked collection | `manifest.json` (hashes, parent, notes, identity changes), `index.json` (pointers, history) |
| Landmarks (evaluation) | — | `body_v6.add_landmarks` | `boy_yellow_hoodie.landmarks` | master |
| Fur fibres (evaluation) | `fur` | `geom.add_fur` | only in `<id>_compare.blend` (`.fur`) | not published |

The rig, facial controls and materials stay together because they are in **one master `.blend`**. The master
also embeds its own spec, so it can be traced and rebuilt.

## 3. Scripts and exact locations
| File | Purpose |
| --- | --- |
| `pipeline/charsys/spec.py` | Spec load, override merge, validation, canonical sha256, identity-change detection (plain Python) |
| `pipeline/charsys/body_v6.py` | Isolated copy of the v6 part generators. Verbatim copy; the source sha256 is recorded in its header. Only the module-level `main()` call is removed, and `configure(spec)` is added |
| `pipeline/charsys/geom.py` | Copy of the v6 geometry helpers |
| `pipeline/charsys/hair.py` | Parametric felted-hair generator. Empty params reproduce v6 exactly. Each experimental control has its own random generator, so the v6 draws never shift |
| `pipeline/charsys/build_character.py` | Builds from spec (+ overrides). Writes the master (component collections, metadata, embedded spec, facial controls), glb, compare file, `components.json`, `animation_compat.json`. Refuses to write into `assets/` |
| `pipeline/charsys/asset_store.py` | `publish`, `approve`, `verify`, `restore`, `list` |
| `pipeline/charsys/episode.py` | Links a published version into a shot file as a library override, then poses the rig and facial controls |
| `pipeline/charsys/hair_experiments.py` | Runs hair variants. Each variant gets build → 16-view harness → sheet → regions → metrics, then a summary and a multi-view sheet |
| `pipeline/charsys/verify_charsys.py` | One-command check with any Blender: build → v6 equivalence → store tests → reuse test |
| `pipeline/charsys/tests/test_store.py` | Asset-store tests on a temporary store |
| `pipeline/charsys/tests/reuse_test.py` | Reopen and reuse test on a published version |
| `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json` | The character spec (v6 values) |
| `assets/characters/boy_yellow_hoodie/experiments/hair/H0*.json` | Hair experiment overrides (8 variants) |
| `assets/characters/boy_yellow_hoodie/versions/` | Asset store: `index.json` and `1.0.0/` |

## 4. Permanent asset preservation (method)
| Need | Method | Tested |
| --- | --- | --- |
| Saving master `.blend` files | `build_character.py` writes `<id>_master.blend` with components, metadata and embedded spec. `asset_store.py publish` copies it into `versions/<x.y.z>/` | yes |
| Exporting reusable assets | The same publish stores `<id>.glb` (meshes, 73-joint skin, weights, 4 morph targets) and `animation_compat.json` | glb imports and deforms (T6) |
| Keeping rig, facial controls and materials together | One master file holds all of them. Facial controls are rig properties driving the shape keys | T1 |
| Versioning | A version is a semantic folder `x.y.z`. Published versions are immutable: re-publishing is refused and files are read-only. The manifest holds the sha256 of every file, the spec hash, the parent and notes. `index.json` keeps pointers (`reference`, `approved`) and the history | store tests |
| Identity lock | Publishing a build whose identity sections (identity, proportions, face, hair, clothing, accessories, materials) differ from the parent is refused unless `--identity-change-approved-by "<who, when>"` is given. The approval is recorded in the manifest | store tests |
| Restoring approved versions | `restore --version approved --to <dir>` verifies hashes, copies the version out and re-verifies the copy. It never writes into the store. Any version can also be rebuilt from its `spec.json` | store tests |
| Episode edits cannot modify the master | Shots **link** the master (relative path) and create a library override. Only the rig (pose, `face_*`) is editable. Meshes and materials stay linked; edits to them are neither saved nor written back. `episode.py` checks the master's hash against the manifest before linking | T3–T5, T7 |
| Tamper and corruption detection | `verify` re-hashes every file. `approve` and `restore` refuse a version that fails | store tests |
| Backup | The published versions are tracked in git, so the git bundle carries them | — |

Commands:
```bash
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json --out out/build_x
```
```bash
python3 pipeline/charsys/asset_store.py publish --build out/build_x --version 1.0.1 --notes "what changed"
```
```bash
python3 pipeline/charsys/asset_store.py approve --version 1.0.1 --by "owner, date"
```
```bash
python3 pipeline/charsys/asset_store.py restore --version approved --to out/restored
```
```bash
blender -b --factory-startup -P pipeline/charsys/episode.py -- --version-dir assets/characters/boy_yellow_hoodie/versions/1.0.0 --out episodes/ep01/shots/shot_010.blend --face '{"face_Smile": 0.6}'
```

**Current store:** `1.0.0`, status `reference`. It is pilot v6 rebuilt from the spec, plus the facial controls. The
`approved` pointer is **empty**: approving is your decision (your visual approval of face and hair is still pending).

## 5. Tests that prove reuse (run on the stored files, after reopening them)
Run: `renders/charsys/verify/CHARSYS_VERIFICATION.md` (cloud, Blender 5.3.0). Verdict **PASS**. Evidence:
`docs/evaluation/charsys/`.

| Test | What was done | Result |
| --- | --- | --- |
| T1 reopen master | Opened `versions/1.0.0/boy_yellow_hoodie_master.blend`. Checked component collections, metadata, embedded spec hash, asset mark, objects per component, rig (410/73), weights, shape keys and facial controls; drove `face_Blink` and `face_Smile` | PASS. 0 unweighted vertices. Blink moves the lids by up to 44 mm, Smile moves the mouth by up to 8 mm |
| T2 pose master | FK arm rotation on the reopened rig (not saved) | PASS. Sleeve moves 18.5 cm |
| T3 episode shot | Empty file: link and override, pose arms and head, Smile 1.0 and JawOpen 0.6, save, then **reopen fresh** | PASS. Links the store master (relative path), no geometry copied, pose, FK switch and expression persisted, sleeve and mouth deformed, renders |
| T4 second episode | Another shot with another pose (leg up, Blink) from the same version | PASS. Independent of shot A |
| T5 isolation | Inside the shots, moved a linked vertex and recoloured a linked material, then saved | PASS. Not saved in the shot; the master is unchanged |
| T6 glTF reuse | Imported `boy_yellow_hoodie.glb` into an empty scene and posed it | PASS. 73 bones, 54 skinned meshes, 4 morph targets; skin deforms 18.5 cm |
| T7 master unchanged | sha256 of the master before and after everything | PASS. Byte-identical |
| Store | Publish, immutability, version format, identity lock, spec-after-build tamper, approve (needs `--by`), restore (approved pointer, identical bytes, refuses store or non-empty targets), tamper detection | PASS, 19/19 |

## 6. Genuinely reusable vs. experimental
**Reusable (tested by reopening and reusing):**
- The published `boy_yellow_hoodie` version `1.0.0`: master, glb and metadata. It can be used in any number of shots
  and episodes without rebuilding.
- The asset store: publish, verify, approve, restore, identity lock.
- The episode linking method (`episode.py`): link, override, pose and facial controls.
- The spec format and spec tools (`spec.py`).
- The spec-driven build for this character (equal to v6).
- The rig, weights and facial-control layer as generated for this body.

**Reusable in code, but not yet proven on a second character:**
- The proportion and colour parameters (`configure`).
- The hair generator.
- Component organisation, metadata and `animation_compat`.
- The rigging, weighting and fur steps.

These are generic, but no other character has been built (deliberately: not requested yet).

**Character-specific (boy only):**
- The part generators in `body_v6.py` (hoodie, backpack, shoes, the face construction).
- They read the spec's proportions, but their shapes are written for this outfit.
- A second character needs its own garment modules or parameterised versions of these.

**Experimental:**
- All hair variants (section 7). None is published or approved.

**Not covered:**
- Fur fibres are not in the master or glb (evaluation only; glTF cannot carry curves).
- No USD or Alembic export yet.
- Files are not byte-reproducible across rebuilds (vertex order after modifiers), so equality is checked numerically.
- `episode.py` covers posing; animation actions on the override and multi-character scenes are not tested yet.
- **Your Blender has not run any of this.**

## 7. Hair experiments
Full results: `docs/evaluation/hair_experiments/HAIR_EXPERIMENTS.md`.

There were 13 variants: a control plus 12 changes covering length, direction, irregularity and asymmetry, gaps,
projecting tufts, layering, felting and combinations. Each was measured on 6 views and shown from 8 angles.

| Finding | Evidence |
| --- | --- |
| The control reproduces v6 | 0.841 / 3.40% |
| Bigger hair is always worse | Longer, up/out and layered variants: hair contour 4.0–4.8% |
| Removing clumps at the outline helps | 3.13–3.14% |
| Exposing the scalp is a hidden failure | Three variants scored well but showed bald patches; caught only visually |
| Best clean variant: **H12** (drop 15% of clumps over the dark base, no inset) | IoU 0.844, hair contour 3.14% |
| **Target not reached** | Hair contour target is ≤ 3.0%. The next lever is the clump layout itself (`hair_clumps/2`), not more parameters |

Nothing was adopted: a hair change is an identity change and needs your approval.

## 8. Next concrete milestone
See `NEXT_STEPS.md`. In short:
1. Run `verify_charsys.py` on your Blender 5.2, next to the v6 reproduction you are running.
2. Then build `hair_clumps/2`, measured with the same runner. Target: hair contour ≤ 3.0% with a clean visual. If
   it gets there, it is proposed to you as candidate version 1.1.0.
