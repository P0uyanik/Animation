# T-034 Real fabric look for clothing: cloth rest shape, thickness and edges, surface detail

Status: **implemented, all required checks pass; pending owner visual review.** Nothing was published or approved.

Branch `t-034-claude-garment-cloth`, from `t-028b-claude-material-fixes` (39b5b93).

**Honest summary.** The shared systems are in place and work on every body and outfit:
- a deterministic build-time cloth settle, spec-controlled per item and part;
- rounded solidified rims, plus rolled or piped edges on any shell;
- a hand-made surface-detail layer that OIDN keeps.

On the girl at 640 px the difference is **real but modest**:
- softer folds in the blouse sleeves;
- the vest hangs with weight and a slightly uneven hem;
- small gathers above the bloomer cuffs;
- rounded collar and boot edges;
- gentle lumps in the felt and cotton.

The larger differences from her reference are not drape: the vest cut and length, the shoulder gap, the boot shape and
the bloomer cuffs. They are listed under "What still differs" with causes and proposals.

## What was built (all shared, no character names)

### 1. Cloth rest shape (`garment/1` `drape`), `pipeline/charsys/garments/drape.py`

- **Optional per item:** `drape: {enabled, fabric, overrides, pin, gather, gravity, frames, quality, seed, ...}`,
  plus `parts.<main|bodice>` overrides. Fabric presets: `cotton`, `knit`, `felt`, `denim`, each with mass,
  tension/compression/shear, bending, air damping, collision thickness and friction.
- **How it runs:** Blender cloth runs once at build time on the generated shell, in a private scene (nothing else is
  evaluated), with a fixed frame count, no self-collision and a seeded symmetry-breaking jitter.
- **Collider:** the rest-pose body, cropped to the faces near the shell and inflated to the item's ease. A thin
  collision shell is used. A thick collision distance first made the vest take 264 s; it now takes 16 s.
- **Pins:** `edges` holds open edges at their band. `volume` keeps the plain-ease areas fitted. `top` lets the item
  hang from its top band, as a vest does from the shoulders.
- **Gathers:** `gather` grows the free cloth in proportion to the designed fullness. It buckles against the pinned
  bands into folds.
- **After the settle:**
  - the settled shape is the rest shape;
  - the inner solidified layer is rebuilt along the settled normals, so thickness stays even;
  - bands, buttons, pockets, edge rolls and embroidery follow the panel (nearest-face displacement), and so do the
    button and embroidery report positions and the weight anchors;
  - skinning, T-025 masks, post-skinning collision and the rest clearance projection then run **unchanged**, so the
    clearance guarantees hold (see Checks).
- **Deterministic:** the same item built twice gives the same SHA-256 of the rest shape on both synthetic bodies
  (check `drape_deterministic`). Two girl builds give identical garment reports, apart from the timing fields.

### 2. Thickness and edges

- **`edge_finish: "rounded"`** rounds the solidified rim of any shell, so hems, cuffs, the collar and the boot tops
  read as cloth with thickness rather than a cut sheet. The rim gets a 2-segment bevel of half the thickness.
- **`bands.edge_roll_m` now works on every shell type,** not only tops: waist and leg openings, and boot tops.
  A new `bands.edge_style` chooses `rolled` (as in T-025) or `piped` (a cord on the rim, material part `piping`).
  The test outfit A shorts use piping.

### 3. Hand-made surface detail (`surface_detail`, `materials/builder.py`, `presets.json`)

- **What it adds:**
  - domain-warped lumps (felt lumpiness, uneven stuffing);
  - fibre-direction streaks (coordinates stretched by `fibre_direction`);
  - `irregularity` (a warp of both).
- **Where:** it is enabled on felt, woven cotton, cotton knit, denim, fleece and boot fleece. Skin-felt has a tuned
  block that is off; a character opts in with `overrides`. It drives the shading normal and a few percent of the
  albedo, the two guide passes OIDN preserves.
- **OIDN survival** (`surface_detail_oidn.json`, `measure_surface_detail_oidn.py`): the layer's own signal is the std
  of the on-minus-off luminance (0..255) on a curved panel, noise-free 512 spp against 32 spp + OIDN.

| Preset | Signal, noise-free | Signal after OIDN | Correlation |
| --- | ---: | ---: | ---: |
| woven cotton | 1.62 | 1.61 | 0.96 |
| boot fleece | 2.14 | 2.04 | 0.96 |
| skin-felt (opt-in) | 0.81 | 0.77 | 0.81 |
| felt | 1.55 | 1.02 | 0.40 |

  - Cotton, fleece and skin keep the detail.
  - Felt keeps two-thirds of it, but with a different pattern (correlation 0.40). Felt's existing nap and micro
    layers add noise at 32 spp that OIDN smooths together with the lumps.
  - The first strengths I tried gave a signal under 1 grey level, which is invisible, so I raised them about 3×.
    Presets are still "subtle" (albedo ±3–10 %).

### 4. Girl (garments section only)

- **Blouse:** drape cotton, gather 0.30, gravity 0.4, bending 4, smooth 3.
- **Vest:** felt hanging from the shoulders, gravity 0.6, bending 15.
- **Bloomers:** felt, gather 0.35, gravity 0.5.
- **Every item:** `edge_finish: rounded`.
- **Boots:** a slimmer cuff (`cuff_radius_m` 0.014 → 0.009).
- `spec_version` is unchanged. A T-034 note is added to `clothing.provenance`.

## Visual comparison with the reference (judged first)

- `girl_turnaround_before_after.png` shows reference | before (T-028b head) on top and reference | after (T-034) at
  the bottom. It has 4 views at 640 px, 32 spp + OIDN, with the shared `character_neutral/1` calibration
  (`groom_turnaround.py`).
- `closeups_vs_reference.png` shows a reference crop | before | after for the sleeve, collar, vest, bloomers and boots.

| Area | What improved | What still differs and why |
| --- | --- | --- |
| **Blouse sleeves** | The sleeves read as cloth, not a rigid balloon: soft lengthwise folds and a slight downward weight | The reference sleeve is a long, smooth, very full puff with a few large folds; ours are similar in size, with finer and fewer folds. Cause: the puff is still a body offset shell, and the cloth only relaxes it. Gravity above 0.5 collapsed the puff (iteration 1) |
| **Shoulders** | — | Skin still shows at the top of the shoulder between the vest strap and the sleeve, with a stair-stepped shell edge. This predates T-034: `_top` starts the sleeve at t = 0.10 and cuts the torso armhole, so a sleeved top has no set-in shoulder cap. **Proposal:** a `sleeve_start`/set-in cap option for sleeved tops, validated by the pose clearance test |
| **Collar** | Rounded, thick edges; it reads as a felt collar | The reference collar is wider, with pointed shirt tips over the vest. Ours is the T-024 round collar under the vest strap. That is a collar-shape parameter question, not cloth |
| **Vest** | Hangs from the shoulders with weight, a slightly uneven hem, and rounded edges | The reference vest is boxier, ends lower (mid-bloomers) and stands away at the hem; ours is shorter and closer. Cause: the cut (`hem_z_m`, `ease_m`) and felt that is stiff in the reference. Gravity draws ours in a little. **Proposal:** lengthen `hem_z_m` and add hem flare (a vest `flare_m`) in a spec/geometry follow-up. That changes the outfit silhouette, so it needs the owner |
| **Bloomers** | Small gathers above the leg cuffs and a softer shape | The reference has a distinct turned-back cuff and a horizontal balloon. Ours is more barrel-shaped, with subtle folds. The folds are small because, at the girl's mesh resolution (4–8 mm edges), the solver forms few, wide buckles. **Proposal:** a local subdivision of free regions before the settle, at a cost in build time |
| **Boots** | Rounded rims and a slimmer cuff ring | The reference boots are tall, straight fleece cylinders with a soft rolled cuff. Ours have two bulbous toe lobes and a wide flat top ring seen from above. Cause: `toe_volume_m` and `shaft_width_m` in `_footwear` add volume along the normals of a foot-shaped shell, and the cuff band is a torus. **Proposal:** a footwear shaft profile (cylindrical shaft, capped toe) in `garment/1`. Draping does not help with this, so boots are not draped |
| **Surface** | Gentle lumps and grain on the felt and cotton, visible after OIDN | They are subtle at 640 px by design. The vest still reads a little "towel-like" from the T-028 fibres (unchanged here) |

## Synthetic bodies (both) in both outfits, with drape on

The `synthetic_{reference,extreme}_outfit_{a,b}_turnaround.png` and `synthetic_*_worst_pose.png` images come from
`tests/garment_generic_test.py --evidence-dir`.
- **Outfit A:** the fitted shirt and denim shorts hang from top and edges; the vest is felt.
- **Outfit B:** the knit puff top and bloomers gather; the embroidered vest is felt.
- Every item has rounded rims. The shorts have piping.

## Build time, simulation on vs off

| Build | Wall time |
| --- | ---: |
| Girl, drape off (`--override` with `enabled: false`), this branch | 50.9 s |
| Girl, drape on, run 1 | 106.4 s |
| Girl, drape on, run 2 | 81.7 s |
| T-028b head, reference (before) | 69.5 s |

Simulation share, from the build report: blouse 8.7 s, vest 15.8 s, bloomers 6.2 s, about 31 s in total. The rest of
the spread is host variance; the machine was shared with renders.

Synthetic puff top alone: 10.9 s on against 1.5 s off (reference body), and 10.9 s against 1.8 s (extreme body).

## Checks

| Command | Result |
| --- | --- |
| `python3 tests/garment_generic_test.py --blender <blender> --out <dir> --evidence-dir <dir>` | **PASS** (rc 0), both bodies, all 23 poses. Worst pose clearance 0.0005 m (reference) and 0.000501 m (extreme). New gating checks: `drape_deterministic`, `drape_applied`, `bottoms_edge_finish`. On the extreme body, `sleeve_puff`/`bloomers_puff` stay informational, as in T-025 |
| `python3 pipeline/charsys/tests/test_material_presets.py` | PASS 54/54 |
| `python3 pipeline/charsys/verify_charsys.py --blender <blender> --out <dir>` | PASS: geometry fingerprint ok (boy byte-identical) |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>` | PASS 8/8 |

- **No threshold changed.** The first full test run failed `sleeve_puff` on the reference body: just above the cuff
  the sleeve was 8.2 mm wider than the plain sleeve, against an 8 mm limit (T-025 had 7.8 mm). I fixed it in the
  system and the test spec, not the limit:
  - the gather now scales with the designed fullness;
  - the test's puff items use a 30 mm cuff zone and gravity 0.3, giving 7.8 mm.
- **Frozen paths:** `git diff 39b5b93 -- assets/characters/boy_yellow_hoodie tests/data docs/references` is empty.
  The `targets` blocks in `presets.json` are unchanged. Groom, face, engine and clips are untouched.
- **Not measured:** the swatch-sheet metrics (`render_swatches`/`measure_swatches`) were not re-run, because of the
  render budget. The surface detail changes the cloth swatches slightly.

## Iterations (5-render budget)

| Iteration | Changes | Result |
| --- | --- | --- |
| 1 | gather 0.18, full gravity | Sleeves collapsed; bloomers looked like a skirt |
| 2 | gravity 0.35, stiffer bending | Barely visible; the vest solve took 264 s (thick collider) |
| 3 | Inflated thin collider (build 6m15 → 1m54); wider free zones | Paper-like crinkles on the sleeves |
| 4 | Bending 4, Laplacian smooth 3, vest bending 15 | Kept |

The final renders, plus single close-up re-renders of the sleeve and collar to fix the framing, are not iterations.

## Reproduce

Blender: a Python 3.13 venv with `bpy==5.3.0` behind a `blender` wrapper (`-b --factory-startup -P <script> -- <args>`).

```bash
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir> --no-glb --no-compare
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend \
  assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> \
  --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 \
  --closeup "sleeve:0:5:-0.19,-0.02,0.55:0.22" --closeup "collar:0:10:0,-0.05,0.615:0.16" \
  --closeup "vest:0:5:0,-0.1,0.55:0.36" --closeup "bloomers:20:5:0,-0.05,0.38:0.32" --closeup "boots:0:10:0,-0.05,0.12:0.40"
python3 pipeline/charsys/tools/turnaround_sheet.py assets/characters/girl_auburn_bun_glasses/references/views <renders> <sheet.png> \
  --views sheet30_front:front,sheet30_front_left:front-left,sheet30_left:left,sheet30_back:back --height 640 --tag "after (T-034)"
python3 docs/evaluation/characters/T-034/make_closeups.py assets/characters/girl_auburn_bun_glasses/references/views <before> <after> <out.png>
blender -b --factory-startup -P docs/evaluation/characters/T-034/measure_surface_detail_oidn.py -- <out.json> <png dir>
```

## Remaining, with proposals

1. **Shoulder cap gap** on sleeved tops (pre-existing): add a set-in sleeve cap option to `_top`.
2. **Boot shape**: add a shaft profile (cylindrical shaft, capped toe) to `_footwear`.
3. **Vest cut**: longer and flared. This changes the outfit, so it needs the owner's approval.
4. **Finer gathers**: adaptive subdivision of the free cloth before the settle, if the owner wants more folds at the
   cost of build time.
5. **Felt detail under OIDN**: calm the felt nap/micro noise, or raise the turnaround samples, so the lumps keep
   their pattern after denoising.
