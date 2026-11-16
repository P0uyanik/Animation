# T-016: girl hair through the shared groom system (V3)

Status: **round 2 implemented.** Colour is now within the ΔE00 ≤ 8 tolerance and the curls read as chunky, irregular
ringlets. The deviations that remain are listed under "Round 2: remaining deviations". Nothing is published or approved.
The girl's spec version is **0.6.0** (round 1 was 0.5.0) and is unpublished.

The round-1 report follows first, unchanged. Round 2 starts at "Round 2".

## What was built
- `pipeline/charsys/groom.py` adds `groom/1`, the shared groom system. Hair is a list of spec structures:
  - `scalp_cap` reuses `hair.scalp_cap`;
  - `sweep` is locks on the scalp drawn towards a gather point or bun;
  - `fringe` is locks from a part line to the forehead;
  - `locks` are hanging locks in the style `straight`, `wavy` or `curly`, so long and curly hair are parameters;
  - `bun` is a list of coiled buns, each with its own position, size, wrap direction, turns and rope count;
  - `tie`, `bow` and `flowers` are hair accessories.

  Every lock is a plied yarn rope: the ply count, depth, twist, sections and step are set in `spec.hair.yarn`.

  Binding: by default the hair follows the head bone. The spec can set `spec.hair.binding.blend_z` so that long
  hair blends from the head bone to the chest bone.
- The generator has no character names. The boy's `hair_clumps/1` and `hair_clumps/2` are unchanged.
  `build_character.main_generic` calls `groom/1` only when the spec asks for it.
- Girl spec 0.5.0:
  - groom structures: a cap, one bun, front and back sweeps, a side-swept fringe, side, back and nape spiral curls,
    a band and 3 flowers;
  - material slots: `hair` uses the T-015 `wool yarn` preset in auburn `#56362C`; `hair_band`, `hair_flower` and
    `hair_flower_centre` use `felt`.
- `tools/groom_turnaround.py` renders the cameras from the reference index under the harness lighting. AgX, exposure
  −1.
- `tests/groom_generic_test.py` builds a synthetic egg head with no character data. It uses the structures the girl
  does not use: two buns with opposite wraps, a bow, straight and wavy long locks.

## Evidence
- `turnaround_vs_reference.png`: front, 3/4 (yaw −45), side (yaw 90) and back. Each view is a 640 px render next to
  the matching `sheet30_*` reference view. Cycles, 32 samples, OIDN.
- `yarn_closeup.png`: orthographic close-up, 0.30 m wide at 640 px, of the bun, the sweep and the back curls.
- `render_timings.json`.

## Matches the reference
- **Structure:** one high bun slightly behind the crown, with the top at about 1.09 m (target 1.10 m). A band at the
  bun base, flowers on the bun's front-left, hair swept up into the bun, spiral curls at the sides and back.
- **Length:** the back curls reach z ≈ 0.45–0.54 m, about mid-back, which matches #30 and #39/#40.
- **Yarn as geometry:** the ropes show plied twist ridges, visible in the close-up.
- **Face unaffected:** `face_system_test` gives the same 584 values with and without the groom: no eye occlusion and
  no glasses or eye overlaps.

## Deviates from the reference (open)
1. **Colour.** The hair reads grey-mauve, not auburn. The back-view hair median is sRGB (114, 92, 86); the reference
   is (88, 49, 40). The skin is also desaturated: leg (184, 169, 165) against (204, 160, 144). Likely causes:
   - the harness lighting under AgX;
   - the white sheen of the `wool yarn` preset (0.42).

   This needs lighting/exposure calibration for character renders, or a hair-preset override. I did not override the
   shared T-015 presets.
2. **Curl look.** The curls read as tight, regular "springs" or an accordion curtain. The reference has soft, chunky,
   irregular ringlets. On the back, the curls merge into a horizontal ribbed sheet with a hard lower edge. Also:
   - the twist ridges are too fine and too regular;
   - the material's object-space yarn waves add horizontal stripes everywhere. Ridges that follow each rope need
     UVs or tangents.
3. **Volume.** The side and back curls hang too far from the head: the side view shows a gap. The front view lacks
   the puffy temple volume of the reference.
4. **Fringe.** The fringe barely reads in the front view, and the forehead looks bare. The tips need more coverage
   and more contrast.
5. **Accessories.** The flowers are small and partly hidden. The band is buried inside the bun ropes. In the
   reference, the flowers are larger and pinker and the band is clearly visible.
6. **Pose.** Long hair is rigid to head and chest through a linear blend only. There are no hair dynamics and no
   collision check against arms or garments. The garments do not exist yet.
7. **Task wording.** The task says "buns with a bow". The reference and the approved identity decision show a
   single bun with flowers and a blue-grey band, so the girl uses those. Several buns and a bow are supported and
   tested on the synthetic head.

## Render time (CPU, 4 cores, Blender 5.3 bpy)
| Step | Time |
|---|---|
| Girl build (master + glb), groom part ≈ 2 s | 37.4 s |
| 4 turnaround views at 320×640, 32 samples | 17.0 s (5.0, 4.4, 3.6, 4.1) |
| Yarn close-up at 640×640 | 16.7 s |

The groom has 128,868 vertices in 11 objects. Budget used: 2 low-resolution iteration renders at 200×400 and 16
samples, plus 1 final turnaround and the close-up.

## Commands
```
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir>
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --closeup "yarn_closeup:135:10:0.02,0.06,0.93:0.30"
blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>
```


---

# Round 2

Evidence is in `round2/`. The round-1 files above are left as they were.

## Before / after
- `round2/before_after_turnaround.png`: the round-1 turnaround above the round-2 turnaround, with the same views and
  references.
- `round2/before_after_closeup.png`: the round-1 yarn close-up next to the round-2 one. The camera is the same
  (`yarn_closeup:135:10:0.02,0.06,0.93:0.30`).
- `round2/turnaround_vs_reference.png` and `round2/yarn_closeup.png`: the final round-2 renders, 640 px, Cycles,
  32 samples, OIDN.

## 1. Colour: shared character-render calibration
- **`pipeline/charsys/render_calibration.json` + `render_calibration.py`** hold the shared profile
  `character_neutral/1`. It has no character data, and the lights are placed relative to each camera:
  - **Key:** sun from screen-left, azimuth 35°, elevation 45°, 5800 K, angle 18°.
  - **Fill:** azimuth −50°, elevation 15°, 4800 K.
  - **Rim:** azimuth 160°, elevation 35°; its stop gain over the adjacent hair was not measured this round.
  - **Ambient:** uniform, 6500 K.
  - **Backdrop:** camera rays see the sheet's grey, sRGB (96, 92, 95), through a Light Path mix, so the backdrop does
    not light the subject.
  - **View transform:** `Standard`, exposure 0.

  Targets from `docs/references/VISUAL_TARGET.md`: key azimuth 25–45° and elevation 35–55°; key 5000–5800 K and warm
  bounce; neutral R/B 1.03–1.15 (the profile gives about 1.08); fill ratio 1.6–2.5:1.

  Strengths are tuned so that a flat patch facing the camera displays at its base colour. Round 1 used AgX, exposure −1
  and a grey world that lit everything; together they halved saturation.
- `compare_harness.studio_lighting` is **unchanged**, because silhouette and baseline renders depend on it.
  `groom_turnaround.py` now uses the calibration by default. `--lighting harness` reproduces round 1.
  `render_swatches.py` gained the same `--lighting` option and keeps `harness` as its default.
- **The calibration was checked on the T-015 swatch sheet.** Values are the ΔE00 of each patch median against its base
  colour:

  | preset | harness, AgX (T-015 setup) | `character_neutral/1` |
  |---|---|---|
  | felt | 24.2 | 2.6 |
  | wool yarn | 19.5 | 3.2 (sheen 0.10) |
  | fleece | 18.0 | 4.2 |
  | cotton knit | 16.6 | 3.5 |
  | woven cotton | 14.9 | 2.9 |
  | denim | 23.2 | 3.2 |
  | felt hair | 23.8 | 7.1 |
  | buttons/plastic | 17.0 | 0.8 |
  | skin-felt | 5.8 | 4.0 |

  Every opaque preset is within ≤ 8. The acrylic lens is transparent and is not a colour patch.

  Files: `round2/swatch_sheet_calibrated.png`, `swatch_metrics_calibrated.json`, `swatches.json`.
- **Wool-yarn sheen lowered in the shared preset: 0.42 → 0.10** (`materials/presets.json`).
  - On spheres in the hair colour under the calibration, the sheen is the main cause of the grey lift on dark yarn.
    The ΔE00 against the base colour is 4.8 at sheen 0.20 and 2.4 at sheen 0.10.
  - Specular 0.3 → 0.15 changed less than 1 ΔE, so the specular stays at 0.3.
  - On the light wool swatch, saturation retention rises from 48.0 % (0.42) to 52.4 % (0.20) and 55.1 % (0.10). The
    patch ΔE moves from 2.6 to 3.2 because the patch is slightly darker; it is still within ≤ 8.
  - The two other T-015 swatch metrics fail at every sheen value, so the sheen change makes none of them worse:
    - `fuzz_rms_y255` is about 0.3 against 3–8 (see deviation 4 below);
    - `sheen_p90_p50` is about 1.00.
- **The colour measurement** is in `pipeline/charsys/tools/measure_colour.py`. It runs in plain Python with numpy and
  Pillow.
  - `groom_turnaround.py --ids` writes one material-slot mask per view. It renders in Cycles with emission
    stand-ins, 1 sample and no anti-aliasing, because Workbench needs a GPU context.
  - The reference patches are character data, in `references/colour_checks.json`.
  - The render median uses every pixel of the slot in the same view.

### Hair and skin medians (final, `round2/colour_checks.json`)
| check | round 1 (README medians) | round 2 render | reference | ΔE00 r1 | ΔE00 r2 | ΔE00 r2, luma-matched |
|---|---|---|---|---|---|---|
| hair, back view | (114, 92, 86) | (77, 53, 46) | (93, 53, 43) | **13.7** | **5.8** | 5.2 |
| hair, front view | – | (81, 56, 48) | (107, 68, 55) | – | **7.0** | 2.8 |
| skin, front legs | (184, 169, 165) | (195, 162, 151) | (198, 155, 139) | **10.1** | **3.6** | 3.6 |
| skin, back legs | – | (190, 159, 148) | (215, 185, 172) | – | **7.2** | 2.0 |
| flowers, front | – | (185, 123, 124) | (198, 138, 137) | – | 4.8 | 1.8 |
| band, front | – | (125, 121, 119) | (128, 122, 127) | – | 4.5 | 4.5 |

Notes on the table:
- The round-1 ΔE uses the round-1 README medians against this round's reference boxes. Against the round-1 reference
  numbers, the values are 14.8 and 9.9.
- The round-2 skin median is from the `M_skin_face` slot, the whole body skin.
- Hair saturation is 0.40 against 0.54 in the reference; it was 0.25 in round 1.

## 2. Curl look
- **Ringlets randomised per lock with the seed (shared, `groom/1` `locks.curl`):**
  - `jitter` sets the per-lock radius and pitch;
  - `wobble` and `wobble_wavelength` vary the radius and pitch along each lock, using seeded smooth noise;
  - `sway` makes the centre line wander sideways;
  - the start phase and start offset are random per lock;
  - `hang_jitter` varies the hang radius per lock, which layers the locks in depth.
- **Fewer, thicker plies:** the girl's yarn goes from 3 plies with depth 0.16 at 160 twists/m to 2 plies with depth
  0.24 at 95 twists/m.
- **Per-rope UVs:**
  - Every rope gets a `ps_fibre` UV map: U is metres around the rope, in the frame of the twisting plies (`fibre_lean`),
    and V is metres along the rope.
  - The shared material builder has a new option, `fibre.coordinates: "uv"`. The default stays `"object"`, so other
    materials are unchanged.
  - The girl's `hair` assignment uses `"uv"` with anisotropy [1, 0.35, 1], so the ridges follow each rope. The
    object-space horizontal stripes are gone; see `before_after_closeup.png`.
- **Back curls are separate locks:**
  - 9 back locks and 6 nape locks (round 1: 11 and 8), thicker and irregular;
  - lengths are staggered (z_end 0.42–0.56 m);
  - layered in depth, with no ribbed sheet and no hard lower edge.

## 3. Volume
- **Drape (shared `locks.rest_radii` + `rest_z`):** below the head, the back and nape locks move in to an ellipse
  around the back, rx 0.12 and ry 0.10 m at z 0.66 m. They no longer hang at the skull radius, which closes the gap in
  the side view.
- **Side curls** are closer to the head: hang radii 0.16 / 0.15 m, against 0.175 / 0.16 m in round 1.
- **Temple puffs:** a new spec structure, `temple_puffs`. It has 2 short chunky curls per side at azimuth 48–78°, lifted
  12–30 mm. The front sweep lift goes from 6–20 mm to 8–24 mm.

## 4. Fringe
The fringe has 8 locks instead of 6, each 42–50 mm wide instead of 36–44 mm. The tips are lower and more even, and the
tip gap is 8 mm. Under the calibration, the dark yarn now contrasts with the skin: luma 59 against 170.

The face is unaffected. `face_system_test --no-render` gives the same 604 numeric values on the round-1 and round-2
masters; for example, eye visibility is 76.1 % on both sides at rest.

## 5. Accessories
- **Flowers:**
  - 36, 32 and 28 mm, against 26, 22 and 18 mm in round 1, and set 10–12 mm out from the bun;
  - colour (198, 130, 138), from the sheet30 flower median (195, 134, 132), slightly pinker.
- **Band:** set at 0.20 of the bun height, radius × 1.12, tube 10 mm. It is visible from every view; see the close-up.

## Round 2: remaining deviations
1. **Hair lightness and redness.** The hair is a little darker and browner than the sheet: L* is about 7 lower in the
   front view, and saturation is 0.40 against 0.54. The base colour is unchanged. Self-shadowing inside the chunky curls
   lowers the median; the reference's hair has broader lit tops.
2. **Skin chroma.** The skin is less saturated than the front reference legs: 0.23 against 0.30. Its luma-matched ΔE is
   3.6, within tolerance. The cause is the spec's skin base colour (202, 176, 169), not the lighting. Under the
   calibration, the skin-felt swatch is within ΔE 4.0.
3. **Fringe and temple shape.** The fringe and temples read as yarn locks rather than the reference's soft felted
   fringe. The temple puffs are curls, not a smooth volume.
4. **Fine fibre fuzz.** The ropes show twist and ply relief, but individual fibre fuzz is barely visible at 640 px. The
   bump is weak after denoising.

   The T-015 swatch fuzz metric (`fuzz_rms_y255` ≈ 0.3 against 3–8) and the sheen-ratio metric (≈ 1.00) fail for every
   preset under both lightings. This is a T-015 material/metric issue that I did not change. The saturation-retention
   metric is also low (49–67 %) even where the median ΔE is ≤ 4.

   `measure_swatches` reads the PNG through Blender's linear buffer; this should be checked separately.
5. **Pose** (unchanged from round 1): the hair has no dynamics and no garment collision.
6. **The band** is a smooth felt ring. The reference's band is softer, like a scrunchie.

## Round 2: tests
| command | result |
|---|---|
| `blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>` | PASS 9/9: the 7 earlier checks plus UV map and drape |
| `python3 pipeline/charsys/tests/test_material_presets.py` | ALL PASS (29/29) |
| `python3 pipeline/charsys/verify_charsys.py --blender <blender> --out <dir>` | **PASS** (68 PASS, 0 FAIL; v6 geometry worst numeric difference 0.0 m) |
| boy build at the round-1 commit `811eb9f` vs HEAD, `fingerprint.py` | 55/55 objects; every field identical except `hair_mass.coords_hash` |
| `blender -b --factory-startup -P pipeline/charsys/tests/face_system_test.py -- <master> <dir> --no-render`, round 1 vs round 2 | 604 numeric values identical |

**About `hair_mass.coords_hash`:** the boy's `hair_mass` coordinate hash changes between two builds of the *same*
commit. I measured this on round 1 twice and on HEAD twice, and got 4 different hashes. Its counts, centroid, radius
and bbox are identical, and `verify_charsys` already lists it as an "informational exact-hash difference" against v6.
This non-determinism existed before round 2 and is not caused by it. The boy code paths (`hair_clumps/1`/`2`, legacy
materials) were not modified. The boy's .glb differs between builds for the same reason.

## Round 2: render time and budget (CPU, 4 cores, Blender 5.3 bpy)
| step | time |
|---|---|
| girl build (master + glb); groom part 2.8 s | 46–47 s |
| 4 turnaround views at 320×640, 32 samples | 25.4 s (7.7, 6.3, 5.1, 6.3) |
| yarn close-up at 640×640 | 26.0 s |
| slot-mask pass (4 views, 1 sample each) | inside the total of 55.6 s |

- The groom has 114,700 vertices in 12 objects; round 1 had 128,868 in 11.
- Peak memory was about 1.1 GB.
- Character-render budget used: 2 iteration renders at 200×400 and 16 samples (each 4 views plus masks; the second
  also had the close-up), then the final render.
- Calibration probes outside that budget, all material swatches, none of them a character render:
  - 5 swatch sheets at 640×960 and 64 samples, about 85 s each;
  - 1 hair-colour sphere probe.

## Round 2: commands
```
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir>
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --ids --closeup "yarn_closeup:135:10:0.02,0.06,0.93:0.30"
python3 pipeline/charsys/tools/measure_colour.py assets/characters/girl_auburn_bun_glasses/references/colour_checks.json <renders> <colour.json>
blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- --out <swatch.png> --metadata <swatches.json> --samples 64 --lighting character_neutral/1
blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- --image <swatch.png> --metadata <swatches.json> --out <metrics.json>
```
