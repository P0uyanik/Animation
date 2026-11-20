# T-170c · CC0 texture swatch test against the reference videos (RESEARCH/TEST ONLY)

Input SHA `62cef51`. Nothing outside this folder was changed; no pipeline, asset, spec or test change. Downloads are
**not in git** (scratch folder); only sheets, five 320 px swatches, tables and throwaway scripts are committed.
Blender: bpy 5.3.0 via `/usr/local/bin/blender` → `tools/bpy_blender.py`, Cycles CPU, 320 px, 64 spp, ~7 s per swatch.

| File | Content |
|---|---|
| `01_candidates_vs_reference.jpg` | per material: reference crop + measured patch (T-170 `measurements.json`) · 3 candidates, each **raw** and **tweaked**; chip = median display colour of the lit top face; `*` = pick |
| `02_recommended_set.jpg` | the five picks (tweaked) under their reference crops, the HDRI, two reference frames |
| `swatches/*.png` | the five picked swatches |
| `sources.json` | every downloaded file: URL, CC0, SHA-256, bytes; plus all raw/tweak measurements and fitted gains |
| `scripts/` | `fetch.py` (download + hash), `candidates.json` (scale/tweaks), `render_cc0.py`, `make_sheets.py` |

Method. 36 Poly Haven diffuse maps were previewed, 15 sets (3 per material) downloaded in full (diff / rough / nor_gl,
1K JPG) plus 4 indoor HDRIs (1 kept). Rig = the T-170 swatch rig (window key screen-left, warm bounce, AgX, 70 mm,
DoF) with the HDRI as world at 0.45. **raw** = maps as downloaded at real-world size. **tweak** = hand-set scale,
contrast, normal strength, coat/sheen, then a linear RGB gain fitted (3 passes) so the lit top face lands on the
reference patch colour.

Limits: the gain is relative to this rig, not to the calibrated shot lighting, so the tint numbers are directions,
not final values. Reference crops are 854×480 / 828×1108 video. Walls and floor were tested on the same lying slab.
**ambientCG could not be tested**: its API answers, but downloads redirect to `acg-download.struffelproductions.com`,
which the proxy refuses. All candidates are therefore Poly Haven.

## 1. Best match per material

| Material (reference patch) | Pick | Raw → tweaked display colour (target) | Tweaks needed | Verdict |
|---|---|---|---|---|
| Worn plank, paperboat table (`#946C4C`) | **`wood_table`** | `#B17C5B` → `#946C4B` | contrast ×0.6, saturation ×0.85, normal ×0.7, gain (0.59, 0.58, 0.40) = slightly darker and less red-orange; real scale | **Good.** Long streaky grain, scratches and thin board lines like f96. Raw is too contrasty and orange ("stock-photo table"); the tweak fixes it. Board lines are denser than in the reference: use scale 1.3–1.6 on the hero table top. |
| | `brown_planks_09` | `#CBB9A7` → `#9A735A` | needs a heavy gain (0.26, 0.14, 0.05) from grey-weathered | usable second choice, cleaner boards |
| | `wood_planks` | `#C19D81` → `#987159` | — | **rejected**: deep open gaps and end joints read as separate blocks |
| Light satin oak/beech (`#C0A382`) | **`oak_veneer_01`** | `#D5BAA1` → `#C5A585` | scale ×0.6 (finer grain for child-size parts), contrast ×0.7, normal ×0.5, coat 0.2, gain (0.61, 0.59, 0.42) = deeper and warmer | **Good.** Clear straight grain, the thing the T-170 procedural wood lacked. |
| | `oak_veneer_05`, `white_oak_veneer` | → `#C6A688`, `#C4A689` | same tweaks | fainter grain; reads close to a flat colour after softening |
| Floor, light wood (`#D3BC9E`) | **`laminate_floor_02`** | `#CFB7A2` → `#D2BB9F` | contrast ×0.8, normal ×0.7, gain ≈ 1 (1.09, 1.11, 0.87) | **Good, nearly as scanned.** `wood_floor` and `oak_wood_planks` need more correction (too dark / too pink). |
| Rug, sage field (`#A49069`) | `dirty_carpet` (weak) | `#877C6F` → `#A19079` | scale ×1.5, contrast ×0.35, normal ×1.5, sheen 0.15, tint to the field colour | **Partial.** Gives a nubby pile, but not the reference's rows of loops, and colour fields still need a mask. `poly_wool_herringbone` at ×5 reads as woven canvas (better for the storage bins than for the rug). |
| Wall, painted plaster (`#E4D4C0`) | `beige_wall_001` (optional) | `#D2C5B9` → `#DECFC0` | gain (1.49, 1.40, 1.15) | **No gain over a plain preset.** The reference wall is featureless and always out of focus; all three sets render as a flat cream. |
| HDRI | **`lebombo`** 1k | — | rotate so the window sits screen-left; strength 0.45 as fill/reflection, area light stays the key | warm cream room with one large window; the other three were grey, dark or cluttered |

General tweaks for image-backed presets (W1 input):
- **Scale** in metres from the provider's tile size, with a per-preset factor (0.6 for furniture oak, 1.0–1.6 planks).
- **Softening**: diffuse contrast ×0.6–0.8 and normal strength ×0.5–0.7 on every wood; raw scans are too busy for the look.
- **Colour**: woods need a tint gain, not desaturation: display saturation rose from 0.24 to 0.32 (oak) to reach the
  reference. Only `wood_table` needs slight desaturation (×0.85).
- Sheen above ~0.2 washes fabric colour out (rug fit failed at 0.5).
- Tangent normal maps need UVs: the test generates box UVs in metres at build time instead of Box projection.

## 2. Files of the recommended set (CC0, Poly Haven, downloaded 2026-11-20)

Licence re-checked this session on `polyhaven.com/license`: all assets CC0 (commercial use, redistribution, no
attribution). URL pattern `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/<id>/<id>_<map>_1k.jpg`; exact URLs
and the other 30 files are in `sources.json`.

| Asset | Map | Bytes | SHA-256 |
|---|---|---|---|
| `wood_table` | diff | 987969 | `f81642ae141958feac6c5acac03e2aeb6cfe049dff301d0627e3c17f2dc5c7a5` |
| | nor_gl | 625535 | `88ecc8e54c30314f4662696ddf8c05b031976e3cbc68e399daa5ebddfb4cec71` |
| | rough | 618983 | `5b98d4d6b22960c781050ba622cebe67d8710c7a7ba0060b24cb6752d50fde32` |
| `oak_veneer_01` | diff | 641756 | `c14681f72f59f17bff568cae7a837641443b607b899f0c279cd64a5638f877a7` |
| | nor_gl | 484844 | `1297acf7b4476d5ccd83cc8b27be96aa6110f7a9c3a40be0bd767bf81b17db01` |
| | rough | 865194 | `ca2af5649b628ef05f196793d68cdca874c12ceb6e9ae566976546d9dd5a2604` |
| `laminate_floor_02` | diff | 721641 | `c112a8fb107d8600a2974af2f9fa9b595c491a33a59982e22706e9650990bf8f` |
| | nor_gl | 515725 | `ec501e1c76269cabc1648ab0e3f38db1b062ffef7ff4ce037fdc369383afd005` |
| | rough | 560815 | `1d48d21a8497d83d4148e4378bf6891e052c98b58cdce1f79003bcc24a3aff8f` |
| `dirty_carpet` (optional) | diff | 978020 | `b0ef2b248cb7dfa1d33f1b2215fb3b83e815527d4091a2c3a423bdcd63bef60a` |
| | nor_gl | 1089297 | `ba96f6f098ac64456f4cc310469200ff702596a9070d2553f990da8f7b86d29f` |
| | rough | 434062 | `a2e13692bd7e5af9875150130ce9904c11879e693e70753d417b93121cf65be4` |
| `lebombo` | 1k .hdr | 1476953 | `a02c9615adeba91a753c3e4737c3ce7a719273df822eeaa85d24982bd43c9ecb` |

Sizes: three woods 6.02 MB + HDRI 1.48 MB = **7.5 MB**; with the carpet 10.0 MB. (T-170b estimated 15–25 MB.)

## 3. Recommendation and revised effort

**Adopt 3 image sets + 1 HDRI, not 6:** `wood_table` (worn), `oak_veneer_01` (satin oak), `laminate_floor_02`
(floor), `lebombo` (HDRI). Keep **plaster as a plain Principled preset** (no image). **Rug is not solved by a ready
CC0 set from Poly Haven**: keep it procedural (loop rows + colour-field mask), optionally with `dirty_carpet` as the
pile detail, or test ambientCG `Carpet0xx` once its download host is allowed.

The T-170b claim "scanned wood closes the visible gap" is **confirmed for both woods and the floor**, with the
softening and tint above. It is not confirmed for rug and not needed for plaster.

| Phase | T-170b | Now | Why |
|---|---|---|---|
| W1 presets + image sets + HDRI | 1.5–2 | 1–1.5 | sets chosen, hashes and starting tweaks known; plaster needs no image |
| W5 furniture + room | 2–2.5 | 2–2.5 | rug stays procedural (no saving) |
| others | 7.5–9.5 | 7.5–9.5 | unchanged |
| **Total** | **11–14** | **10.5–13.5** | desk-only first slice 6–8 → 5.5–7.5 |

## 4. Open points for the Supervisor

1. ambientCG: allow `acg-download.struffelproductions.com` if a rug/carpet (or second-source) test is wanted.
2. T-170 patch `floor_wood` (watertable f0, box 430,654–495,689) lies on the table-frame corner, not on the floor
   (visible in sheet 01, row 3). The floor target colour is therefore a light-oak value; a real floor patch should
   be re-measured in W1.
3. Final tint values must be re-fitted under the calibrated shot lighting (W1); the gains here are rig-relative.
4. Wood condition (T-170 question 1) still decides whether `wood_table` is needed at all.

## Reproduce

```
S=<scratch outside the repo>; cd docs/evaluation/world/T-170/cc0_test/scripts
python3 fetch.py --out $S/dl --maps all --ph wood_planks,wood_table,brown_planks_09,oak_veneer_01,oak_veneer_05,white_oak_veneer,laminate_floor_02,wood_floor,oak_wood_planks,poly_wool_herringbone,knitted_fleece,dirty_carpet,plastered_wall,painted_plaster_wall,beige_wall_001 --hdri lebombo
blender -b --factory-startup -P render_cc0.py -- --tex $S/dl --out $S/renders --mode raw
blender -b --factory-startup -P render_cc0.py -- --tex $S/dl --out $S/renders --mode tweak
python3 make_sheets.py --renders $S/renders --tex $S/dl
```
Not tested: no ctest or pipeline run (nothing outside this folder changed); no 2K maps; no shot-calibrated lighting;
no ambientCG asset.
