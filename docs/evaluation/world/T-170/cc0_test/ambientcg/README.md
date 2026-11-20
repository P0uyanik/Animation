# T-170d · ambientCG rug + fabric swatch test, and the trimmed world plan (RESEARCH/TEST ONLY)

Input SHA `8079458`. Nothing outside this folder was changed; no pipeline, asset, spec or test change. Downloads are
**not in git** (scratch folder); only two sheets, four 384 px swatches, tables and throwaway scripts are committed.
Blender: bpy 5.3.0 via `/usr/local/bin/blender` → `tools/bpy_blender.py`, Cycles CPU, 384 px, 64 spp, ~8 s per swatch.

| File | Content |
|---|---|
| `01_candidates_vs_reference.jpg` | rug and fabric: reference crop + measured patch · 3 candidates, each **raw** and **tweaked**; chip = median display colour of the lit top face; `*` = pick |
| `02_picks.jpg` | rug pick + runner-up and the fabric pick in sage and coral, under their reference crops |
| `swatches/*.png` | those four swatches |
| `sources.json` | every file of the six tested sets: URL, resolved URL, zip member, CC0, SHA-256, bytes; all raw/tweak measurements |
| `scripts/` | `fetch_acg.py`, `candidates.json`, `render_acg.py` (T-170c `render_cc0.py` with ambientCG folders), `make_sheets.py` |

Method: as T-170c (same rig, HDRI `lebombo` at 0.45, same SHA-256 as in T-170c, gain fitted in 3 passes), except the
slab is 20 cm instead of 40 cm so the pile is resolved. 15 ambientCG sets were downloaded and their colour maps
previewed; 3 rug + 3 fabric candidates were rendered. Targets: `rug_sage` `#A49069`, `bin_sage` `#A19558`,
`bin_coral` `#C7755C` (T-170 `measurements.json`).

Limits: gains are rig-relative (as T-170c). The rug fit did not fully converge: tweaked rugs land ~15 display levels
too light and slightly pink (`#B7A489` vs `#A49069`); re-fit under shot lighting. Only `Carpet016` has a real tile
size in the API (1.7 m); the other five sizes are **estimated** from thread/loop size. Thumbnails
(`acg-media.struffelproductions.com`) and `docs.ambientcg.com/license` are still refused by the proxy, so candidates
were chosen from tags + downloaded maps, and the licence was read from the ambientcg.com front page and the asset
page of `Carpet016` ("All assets are released under the Creative Commons CC0 license … free to use without
attribution - even in commercial circumstances"), not from the licence page itself.

## 1. Result

| Material (reference patch) | Candidate | Raw → tweaked (target) | Tweaks | Verdict |
|---|---|---|---|---|
| Rug, sage field (`#A49069`) | **`Carpet016`** (wool loop carpet, 1.7 m tile) | `#DDD6CA` → `#B7A489` | scale ×0.5, contrast ×0.5, normal ×3, sheen 0.15, roughness +0.2, tint gain (0.27, 0.20, 0.06) | **Good. Best match.** Short irregular loops with a slight row direction, like the reference rug. Solves what `dirty_carpet` (T-170c) did not. |
| | `Fabric045` (bouclé loop rows) | `#DFDDD9` → `#B9A790` | scale ×2 (est. 0.3 m tile), contrast ×0.7, normal ×3 | usable runner-up; rows more regular and holes darker than the reference |
| | `Carpet014` (basket weave) | `#D9D5D0` → `#B3A289` | scale ×1.2, normal ×2 | **rejected**: reads as a woven mat, not pile |
| Fabric / canvas bin (`#A19558`, `#C7755C`) | **`Fabric030`** (plain canvas) | `#A6A29F` → `#A19469`; coral → `#C37D6C` | scale ×1.5 (est. 0.15 m tile), contrast ×0.6, normal ×2, sheen 0.1, tint | **Good, but not needed.** Even weave, takes both colours. The bins are small and always out of focus; the existing `woven cotton` preset already fits (T-170 §2). |
| | `Fabric032`, `Fabric036` | → `#AFA075`, `#AB9D6E` | same | `Fabric032` shows light streaks after tinting; `Fabric036` reads as flat colour |

Rug tweaks to keep: normal strength 2–3 (pile height comes only from the normal map), contrast ≤ 0.5, sheen ≤ 0.15,
colour by tint gain on the near-white scan. Colour fields = the same material with a different tint per patch.

Files of the picks (CC0, ambientCG, downloaded 2026-11-20; `https://ambientcg.com/get?file=<id>_1K-JPG.zip`, which
redirects to `acg-download.struffelproductions.com`). The zip also holds AO, displacement, DX normal, `.blend`,
`.mtlx`, `.tres`, `.usdc` and a preview; only three maps are used.

| Asset | File | Bytes | SHA-256 |
|---|---|---|---|
| `Carpet016` | zip | 9371762 | `b9e67b5d42cb47cead082dedae3767ae228175c857b6b3af6fe7bd4e69237b81` |
| | `_Color.jpg` | 1207660 | `c6fca66d1d570d27a921d7cb35b1963e83844e2b8ceec70f0193db5e99e04123` |
| | `_NormalGL.jpg` | 2179963 | `2820cad2593d1e1b58ce1fa38cb53e24be05bf935b40393c379be828a35755ea` |
| | `_Roughness.jpg` | 686755 | `307c7984100374da53261c51dee33665049e3fc5e0e90143da1f58b040298268` |
| `Fabric030` (optional) | zip | 11064340 | `82d4d00ccf901cf4707c5489005945ab8574933fc60437e26c6737f0436699e0` |
| | `_Color.jpg` | 1681447 | `6388762708722de48cdbdfb4878b9ae6d8012de5948d564006067b629f0b84ef` |
| | `_NormalGL.jpg` | 2682952 | `c9a8f4ff15527af0b226b8a8840405f944c45a32c2e4462864d3b0136827e6e2` |
| | `_Roughness.jpg` | 866950 | `221bf708cb614b01ae83b856376fa79fff22dc249d8a397ab0f89dd3b7fe6da6` |

`Carpet016` three maps = 4.07 MB (`Fabric030` 5.23 MB). The other four tested sets are in `sources.json`.

**Recommendation:** add `Carpet016` as the rug; the rug no longer needs a procedural loop shader. Do not add a
fabric image set; keep the existing `woven cotton` preset for bins.

## 2. Trimmed T-170 plan (owner scope guidance 2026-11-20)

Guidance applied: no need for every object of the videos nor an exact match; any table; simple, allowed,
easy-to-make objects first; objects of a scene must feel related; little time on props.

What changes against the T-170c plan (10.5–13.5 task-days):

| Topic | T-170c plan | Trimmed |
|---|---|---|
| Wood | two woods (worn plank + satin oak) | **one wood for all furniture**: `oak_veneer_01`. `wood_table` dropped (T-170 question 1 no longer needed) |
| Image sets | 3 woods/floor + HDRI, rug procedural | `oak_veneer_01`, `laminate_floor_02`, `Carpet016`, HDRI `lebombo` = **9.3 MB** |
| Other materials | 12 hard presets, calibrated one by one | 5 plain Principled presets: plaster, plastic, paint, paper, matte cup. Fabric = existing `woven cotton` / felt |
| Props | restyle 13 T-163 props with part lists + 3 new | **keep the 16 existing assets and their shapes**; only add a bevel and a preset per asset (one table of 16 rows). No new prop. Verb tests untouched |
| Builder | `parts` list with box, cylinder, shell, sheet, later screw/curve | `parts` list with **box and cylinder only**, one rounding rule (`soft`) |
| Furniture / room | table, chair, shelf, bins, window wall, floor, rug, wall art | one table (top + 4 legs), one stool, one open shelf with 3 bins (boxes), floor, 2 plain walls, rug = 1–3 tinted boxes. Window = HDRI + area light, not modelled. No wall art |
| Water | ring bump + reflections, one container (2–3 d) | **not in v1** (owner may add later; a still, flat water surface in the tray would be ~0.5–1 d) |
| Dressing | hand-placed lists, light/DoF presets per shot type, fibre size rule | ≤ 10 T-163 props placed by hand on table and shelf, one light/DoF preset |

How the objects stay related with so little work: one wood, one rounding rule, one pastel palette (sage, coral,
powder blue, cream from T-170 `03_palette_measured.png`) used for bins, rug fields and painted props alike.

| Phase | Content | T-170c | Trimmed |
|---|---|---|---|
| W1 | preset file, 3 image sets + HDRI, one swatch sheet under shot lighting | 1–1.5 | 1 |
| W2 | `parts` (box, cylinder) + bevel in `prop_mesh`, v1 fallback, determinism test | 1 | 0.5–1 |
| W3 | preset + bevel for the 16 existing assets, one contact sheet | 1.5–2 | 0.5 |
| W4 | water | 2–3 | 0 (deferred) |
| W5 | table, stool, shelf + bins, floor, walls, rug as `parts` data | 2–2.5 | 1–1.5 |
| W6 | hand-placed dressing, one light/DoF preset | 2 | 0.5–1 |
| W7 | integration in `run_shot.py`, one shot re-rendered, docs | 1–1.5 | 1 |
| **Total** | | **10.5–13.5** | **4.5–6** (≈ −55 %) |

Desk-only first slice (W1–W3, the table from W5, W7): **3–3.5 task-days** (was 5.5–7.5). These are estimates; none
of the phases was built or timed here.

What the owner gives up: the worn paperboat table, water, wall art, a modelled window, and prop shapes closer to the
videos (pencil stays a cylinder, book a box, tray an open box).

### 2.1 Amendment: ready-made materials only (owner ~20:10Z, 21:10 CET)

The owner said: "my goal is not to create new materials. Use whatever ready-made materials are already available and simply combine
materials that look good together. Creating materials is time-consuming and costly; not considering that now."

- Allowed sources: the CC0 sets already picked (`oak_veneer_01`, `laminate_floor_02`, `Carpet016`, HDRI `lebombo`),
  the existing project presets (`pipeline/charsys/materials/presets*.json`, e.g. woven cotton, felt) and Blender
  built-in shaders at their default settings.
- The only allowed adjustments are tint, texture scale and mapping. There is no new material authoring, no
  tuning or calibration round, and no procedural material work.
- The "5 plain Principled presets" in the table above become built-in Principled BSDF settings with only a tint
  from the pastel palette. There are no per-preset measurements and no swatch calibration. W1 is just the preset
  file listing these combinations plus one look-check sheet.
- The plan stays on hold, and the estimate stays at most 4.5–6 task-days.

## 3. Open points for the Supervisor

1. Water is the only large item removed; confirm it is deferred, or add 0.5–1 d for still water.
2. Tints (rug and fabric) must be re-fitted under the calibrated shot lighting in W1.
3. Rug tile sizes other than `Carpet016` are estimates; not relevant if `Carpet016` is adopted.

## Reproduce

```
S=<scratch outside the repo>; cd docs/evaluation/world/T-170/cc0_test/ambientcg/scripts
python3 fetch_acg.py --out $S/dl --hdri lebombo --acg Carpet016,Carpet014,Fabric045,Fabric030,Fabric032,Fabric036
blender -b --factory-startup -P render_acg.py -- --tex $S/dl --out $S/renders --mode raw --px 384
blender -b --factory-startup -P render_acg.py -- --tex $S/dl --out $S/renders --mode tweak --px 384
python3 make_sheets.py --renders $S/renders --tex $S/dl
```
Not tested: no ctest or pipeline run (nothing outside this folder changed); no 2K maps; no displacement/AO maps; no
shot-calibrated lighting; no multi-colour rug mask; the nine sets that were only previewed (list in `sources.json`).
