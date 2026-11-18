# T-068: garment detail types (sneakers, backpack, hood fix, gathered skirt, vest details)

1. **Task and objective.** T-068, lane D, path B. Add shared, spec-driven garment detail types: sneakers, backpack,
   hoodie hood volume and underarm fix, gathered skirt with hem rib, and vest details (decals, pockets). Deliver them
   only as candidate overrides; approved character versions stay unchanged.
2. **Result: complete, with the limits listed in §8.** All items are built, tested, and shown on evidence sheets.
   - The gate result is in §5.
   - No new `garment/2` / `accessories/2` pin was registered. That needs `versions.py`, which is outside the write-set.
   - All new behaviour is opt-in under `garment/1`, which is how T-024/T-025/T-034/T-058 extended it. Existing specs
     build identically (§6).

## 3. Files changed

| Path | Purpose |
| --- | --- |
| `pipeline/charsys/garments/sneakers.py` (new) | `sneakers` type: dome upper with ankle opening, sole slab with wrap, toe cap, laces, padded collar with rise, tongue |
| `pipeline/charsys/garments/backpack.py` (new) | `backpack` type: bag on the outer clothing, front pocket, zips and pullers, handle, two straps (over the shoulders, down the chest, under the arms) |
| `pipeline/charsys/garments/shapes.py` (new) | Shared helpers: ribbon strap, superellipsoid, Catmull-Rom/resample, layer-stack projection, mesh BVH, `ps_body_vertex` writer |
| `pipeline/charsys/garments/generator.py` | Registers both types. Adds opt-in `armhole: "closed"`, `sleeve_start`, `pockets.shape: "patch"` (+ `corner`, `top_roll_m`, `inset_m`), embroidery style `cross_stitch` (pattern grid), skirt `gathers` and `bands.hem_rib`, plus their validation |
| `pipeline/charsys/garments/hoodie.py` | Opt-in hood volume: `rim_back_radius_m`, `bag_fullness`, `bag_rise_m`, `bag_taper`, `bag_n`, `bag_gap_m`, `edge_radius_m`, `edge_drop`; validates `armhole` |
| `pipeline/charsys/accessories.py` | Documents and rejects `backpack/1` with a pointer to the garment type. Accessories are rigid to the head bone, so a backpack cannot work there |
| `pipeline/charsys/tests/test_garment_details.py` (new) | Validation and build checks (70 checks) |
| `docs/evaluation/characters/T-068/make_candidates.py`, `candidates/*.override.json` | Writes the three candidate overrides reproducibly |
| `docs/evaluation/characters/T-068/make_sheets.py`, `*.png` | Evidence sheets |

Documentation: `pipeline/charsys/garments/README.md` has a new section "Garment detail types (T-068)" and an updated
type list. This README is the task report.

## 4. What was implemented

Everything is generic: no character names, sizes or coordinates are in code. Sizes come from the spec, with defaults
scaled by the body-fit ratios.

- **Sneakers.** The shoe is built around the foot, not offset from it, because an offset of `body_generic`'s
  ellipsoid foot gives the "blob" shoes seen in T-058.
  - The upper is a dome over a superellipse plan (toe wider than heel, lower toe box). The faces inside an opening
    ellipse at the ankle are removed. `collar.rise_m` raises the upper around the opening into a padded ankle collar.
  - The sole is a lofted slab whose rim wraps up the upper.
  - The toe cap is an offset patch of the upper. Its edge vertices are slid onto the region boundary, so the edge
    is smooth rather than stair-stepped.
  - Laces are bars across the instep; there is a tongue strip and a collar tube along the opening.
  - All pieces are rigid to the foot. The foot inside the shoe is recorded as covered and is masked.
- **Backpack.** It is a garment type, not an accessory, so it follows the torso through the shared weight transfer.
  - The bag is placed after the garments listed before it in the spec. Its body side is flattened onto their outer
    surface (BVH ray casts); its outside stays round (`puff`).
  - Strap control points run under the bag top, over the shoulder, down the chest, under the arm, and into the bag
    side. Each point is projected from the nearest torso skin through the stack of clothing layers lying on it
    (`layer_top`). A gap larger than `layer_gap_m` (for example to a sleeve) is never crossed. The hood is skipped,
    so the straps run under it, as in the reference.
  - The bag, pocket, zips and handle are rigid to the upper back. Each strap vertex copies the weights of the nearest
    chest/back/shoulder-top vertex (`ps_body_vertex`).
- **Hood.** `bag_fullness` replaces the flattened ellipsoid (body side squashed to 15 % of its depth) with a pillow.
  Its body side hugs the hoodie and the neck, it tapers to a U at the bottom, and it rises behind the neck. The rim is
  thicker at the back, and an opening-edge roll lies on the bag.
- **Underarm.** The hole came from the torso panel's armhole cut combined with the dropped-shoulder sleeve. With
  `armhole: "closed"` the panel keeps the armhole faces. The rendered hole is gone (sheet), and the 6-pose check
  passes.
- **Gathered skirt with hem rib.**
  - `gathers` switches the skirt to finer rings (25 × 8·count). Soft outward folds grow from the waist to the hem.
  - `bands.hem_rib` adds a solidified knit band with vertical ridges over the lower edge. The folds are drawn in
    towards the band (`gather`).
  - The same code serves a dress's skirt.
- **Vest details.**
  - `pockets.shape: "patch"` makes flat pockets conformed to the panel by ray casts. They have rounded bottom
    corners, a bulge, a rolled dark top edge, and are kept clear of the open front. A pocket that misses the front
    panel is an error.
  - Embroidery style `cross_stitch` places one X stitch per pattern cell, conformed to the target surface, as decals.
    Cells are `x` (main colour), `o` (accent) or `.` (empty).
- **Candidates** (`candidates/`; written by `make_candidates.py`; values are my estimates, tuned by eye against the
  references):
  - `boy_2.0.0-dev.garment_details.override.json`, applied on the boy 2.0.0-dev spec:
    - hoodie: hood volume and closed armhole;
    - trousers: length 0.985, so they reach the collar;
    - `shoes` becomes the `sneakers` type;
    - a charcoal-plum backpack is added.
  - `girl.vest_details.override.json`, applied on the girl spec + 0.10.0: patch pockets, bow and "mountain"
    cross-stitch decals (#41), and edge buttons moved above the pockets.
  - `girl.gathered_dress.override.json`, applied on the girl spec + 0.10.0: **type demonstration only.** The third
    character has no spec, so her dress (d09/c15) is shown on the girl's body. This is not a proposal for the girl's
    outfit.

## 5. Tests

Blender: bpy 5.3.0 wheel (Python 3.13 venv) via `tools/bpy_blender.py`.

- `python3 pipeline/charsys/tests/test_garment_details.py --blender <bpy wrapper> --boy-master … --vest-master … --dress-master …`:
  **70/70 PASS** on the final candidate masters. It covers:
  - every new option is validated, bad values are rejected, and options are refused on unsupported item types;
  - all sneaker parts exist per foot; the sole is under the upper, the cap is at the front, the collar is around the
    ankle, and the foot is masked;
  - all backpack parts exist; the bag is outside the hoodie; the straps cross the shoulders and show on the front;
  - strap weights are torso-dominant: the largest limb weight is DEF-upper_arm 0.085, which comes from the body's own
    shoulder skin blend; there is no leg, neck or head weight;
  - the hood bag is deeper than 4 cm;
  - no visible (unmasked) skin is left uncovered under the arm;
  - patch pockets are in front of the vest, with edges;
  - the decals are built;
  - the hem rib wraps the skirt edge, and the hem folds are 13.4 mm deep.
- **6-pose deformation check**: `pipeline/charsys/tools/garment_pose_eval.py --poses idle_relaxed:45,wave:52,point:46,gest_shrug:26,sit_down:50,emo_happy:30`.
  Signed garment-to-visible-body clearance:

  | Master | Rest | 6 poses | Vertices inside visible body |
  | --- | --- | --- | --- |
  | boy candidate | PASS (12.7 mm) | **6/6 PASS** (min 2.2 mm, wave) | 0 |
  | boy current 2.0.0-dev, for comparison | PASS | **5/6** (idle_relaxed FAIL, −1.0 mm) | 2 |
  | girl vest candidate | PASS | 6/6 PASS (min 0.52 mm) | 0 |
  | dress demo | PASS | 6/6 PASS (min 1.9 mm) | 0 |

  Not measured by this tool: garment-to-garment intersections, for example strap against hoodie or backpack against
  hood.
- **Full gate**: `python3 tools/check_all.py --base origin/staging --task T-068 --blender <bpy wrapper>`. The full
  tier was selected (shared garment system). The run was on the merge with `origin/staging` 902867b.

  | Check | Result |
  | --- | --- |
  | Frozen assets | PASS |
  | Guarded paths | FAIL, expected: `pipeline/charsys/tests/test_garment_details.py` is a new test file and needs Supervisor approval |
  | Write-set | PASS: 18 paths, all inside the T-068 claim |
  | Shared-systems lint | PASS |
  | C++ build / C++ tests | FAIL, **environment only**: CMake cannot find `embree` in this container. No C++ or engine file is changed; GitHub CI builds with vcpkg |
  | Python tests and links | PASS |
  | Blender tier (full) | girl_auburn_bun_glasses regression **PASS** (fidelity 64.40, unchanged); girl_white_hair_blue_dress **PASS**; garment_generic_test and the other Blender subchecks PASS. boy_yellow_hoodie **FAIL** on one check only: "engine export differs: character.json". Fingerprint byte-equal, renders identical (rmse 0.0000), fidelity 66.41 = baseline |

  The boy's export FAIL is **pre-existing and not caused by T-068**:
  - Only the hash of the export's metadata (`meta_sha256`) differs from the stored baseline; every geometry buffer is
    equal.
  - The same command on a clean `origin/staging` worktree (902867b) fails identically:
    `tools/regression/run.py --character boy_yellow_hoodie --no-fidelity` reports
    "FAIL boy_yellow_hoodie (unchanged): engine export differs: character.json".
  - The boy's approved build is `body_v6` and does not use `garments/` or `accessories.py`.
  - In CI the regression job compares against a fresh build of `main` (`--against origin/main`), so it should not be
    affected by the stored baseline.

## 6. Baselines and unchanged characters

- Unchanged-output guard, run locally: the girl's approved build (spec + 0.10.0 override) and the boy 2.0.0-dev
  spec were each built from `origin/staging` and from this branch, and `pipeline/charsys/fingerprint_v2.py` was run
  on every build. The fingerprints are **byte-identical** for both characters, and the build reports differ only in
  timing fields.
- The boy's approved 1.1.0 build uses `body_v6`, which does not touch `garments/`.
- No file under `assets/`, no spec, no frozen file and no test threshold was changed. Nothing was published or
  approved.
- CI's regression jobs run the per-character guard against `main`.

## 7. Visual results

There are 15 Cycles evidence stills: 24 samples, OIDN, 640 px, shared calibration (`groom_turnaround.py`), with the
reference views' cameras.

| Sheet | What changed vs current | Remaining deviation from the references |
| --- | --- | --- |
| [sneakers.png](sneakers.png) | The blobs on a disc are now low chunky sneakers: cream sole and toe cap, cream laces, padded collar | No side stripes. The toe cap covers more of the front than in val27. A small sliver of ankle shows at the front: the trousers hem has a notch at the instep (it was already in the trousers shell, hidden before by the taller T-058 shoes) |
| [backpack.png](backpack.png) | New: charcoal-plum bag on the upper back, straps over the shoulders, visible down the front of the chest as in canon29/val27, pocket and zips | The pocket and zip read weakly at 640 px (same colour as the bag). The bag sits a little lower and wider than canon29 |
| [hoodie_hood_underarm.png](hoodie_hood_underarm.png) | The hood is now full and rounded, U-shaped on the back, standing behind the neck. The underarm holes visible in current (back, back-3/4) are closed | The hood is still smaller and sits lower than the large hood in val27 back/side, and the rim reads less thick from the side. The fleece look is unchanged (T-067 owns the materials) |
| [vest_details.png](vest_details.png) | Raised flowers become flat cross-stitch decals (dark bows, pale zig-zags). Ellipsoid pockets become flat patch pockets with a dark rolled top | The reference motifs are larger and bolder; mine are smaller and sit lower. The pockets read weakly (same felt colour, no embroidery density). The buttons moved above the pockets |
| [gathered_skirt_hem_rib.png](gathered_skirt_hem_rib.png) | New type, shown on the girl's body (the third character has no spec) | The hem rib reads as a distinct tier, while c15 has a flatter knit band. The folds are soft and subtle. There is no cable-knit pattern (material work) |

## 8. Problems, limitations, open questions

1. **Versions.** No `garment/2` / `accessories/2` was registered, because `versions.py` is outside the write-set.
   - The additions are opt-in under `garment/1`, with identical output for every existing spec (§6).
   - If the Supervisor wants a new pin, it is a one-line registration plus a `GENERATOR_VERSIONS` entry.
2. **The backpack is a garment type, not an accessory.** `build_character.py` attaches accessories rigidly to the
   head bone and passes only face context, and that file is outside the write-set. `accessories.py` now rejects
   `backpack/1` and points to the garment type. Question: should accessories gain a body-attached path later?
3. **Garment-to-garment intersections** (strap through hoodie fibres, bag against hood) are not measured in poses.
   Visually they are clean at rest.
4. The trousers-hem notch at the instep (sneakers row above) is a `trousers` shell artefact. Fixing it would change
   the trousers output, which belongs to another task.
5. **The dress demo uses the girl's body.** A spec for `girl_white_hair_blue_dress` is needed to evaluate the type
   on its intended character.
6. **Guarded paths.** `pipeline/charsys/tests/test_garment_details.py` is a new test file. Every test file is
   guarded, so it needs Supervisor approval.

## 9. Commits

Branch `t-068-claude-garment-details`. The final commit is in the RELAY_LOG READY line. `origin/staging` (T-077,
`902867b`) is merged in.

## 10. Resource use

- Token usage: not available.
- Renders:
  - 15 evidence stills (Cycles, 24 spp, 640 px).
  - 74 iteration previews (Cycles, 8 spp, 360–480 px), all made while tuning the shapes.
  - If the task's ≤ 24 Cycles-still budget also counts iteration previews, it was exceeded.
- Builds: about 20 character builds of about 1 min each.
