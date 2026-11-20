# T-170 · World style system: reference analysis + architecture plan (PLANNING ONLY)

Input SHA `5e91048`. Nothing in the pipeline, assets, specs or tests was changed. Everything below is a proposal for
the owner; no development starts before review.

Evidence in this folder:

| File | Content |
|---|---|
| `01_reference_frames.jpg` | six frames of the two videos used for the analysis |
| `02_reference_vs_swatches.jpg` | per material: reference crop(s) with the measured patch (magenta) and its median colour, next to the T-170 swatch |
| `03_palette_measured.png` | measured palette, grouped |
| `04_bevel_rule.jpg` | edge-radius rule (0 / 3 / 8 / 16 %) against the reference table edges |
| `measurements.json` | 28 patches + 24 frame statistics (`scripts/measure_reference.py`) |
| `swatches/*.png` | 21 Cycles swatches, 320 px, 64 spp (`scripts/render_swatches.py`, throwaway) |

Limits of the evidence: the videos are 854x480 and 828x1108, compressed, and look AI-generated (details change between
shots). Colours are measured display values under the scene's light, not base colours. Texture below about 3 px
(paper fibre, plastic micro-surface, crayon wax) cannot be resolved; those rows are marked ESTIMATE.

## 1. Visual analysis

### 1.1 What the world actually is (verified against crops)

The first impression holds, with four corrections:

1. **Plush is not limited to the characters.** Soft toys in the set (teddy in the foreground, grey animal on the
   shelf) are plush/fur. Rug, storage bins, bunting and hair pom-poms are textiles too. The rule is "soft things
   are fibre, hard things are stylized-real", not "characters felt, world real".
2. **Skin is flocked, not smooth vinyl.** The macro hand shots show a short velvet fuzz on the silhouette. This matches
   the existing `skin-flock/3` direction.
3. **The two videos disagree about the wood.** Paperboat: a worn, darker plank table with open grain, scratches and
   scuffs (`#946C4C`). Watertable: clean light oak/beech with satin varnish (`#C0A382` lit). Shelves and floor are the
   light wood in both. This needs an owner decision (question 1).
4. **The two videos disagree about the water container.** Paperboat: a semi-gloss blue plastic tray with a thick
   rounded rim. Watertable: water directly in the wooden frame over a pale liner, with coloured pebbles (question 2).

### 1.2 Materials identified

| Family | Where | What it is | Evidence |
|---|---|---|---|
| Light wood, satin | watertable table, shelves, chairs, floor, window frame, picture frames | oak/beech, straight fine grain, thin satin varnish, soft broad highlight | `Y99/Y50` 1.08–1.16: no sharp speculars |
| Worn wood | paperboat table | plank top, visible board joints, long grain streaks, pale scratches, matte | texture `hf_rms` 5.4 in focus; scratches visible in `01_reference_frames.jpg` (f96) |
| Painted wood / toy gloss | stacking rings, toy cars, blocks | saturated primaries, glossy lacquer; always small and blurred | `S50` 0.84; the only S > 0.8 areas besides scissors |
| Plastic, semi-gloss | water tray | moulded PP look: thick wall, rounded rim, broad soft highlight band, faint texture | `Y99/Y50` 1.56 across the rim highlight |
| Plastic, gloss | scissor handles | hard, saturated, tight highlights | `S50` 0.66–0.92 |
| Paper | boat, sheets, wall drawings | matte white card, crisp folds, visible thickness at edges, takes the colour of its surroundings (warm on the desk, blue-grey over the tray) | lit `#A4948A` R/B 1.19; over tray `#9D8C83`, `S50` 0.13–0.16 |
| Water | tray / table | clear, shallow; mirror-like at grazing angle (reflects boat and hands), concentric ripples carrying hard window highlights, tint comes from the container | paperboat f168/f192; watertable f0 |
| Wax crayon | desk | waxy cylinders with paper sleeve; about 8 px wide in source | ESTIMATE |
| Matte cup | pencil cup | unglazed ceramic or card tube, matte, thick wall | `Y99/Y50` 1.37 only from form shading |
| Painted plaster | walls | warm cream, near featureless | `#E4D4C0`, `S50` 0.16 |
| Rug | floor | loop/woven pile in pastel colour fields, clear pile direction | `hf_rms` 5–10 at 1108 px height |
| Canvas | storage bins | soft fabric boxes with a cut handle, sage / coral / blue | `#A19558`, `#C7755C` |
| Fibre (existing library) | clothes, hair, skin, soft toys | fleece, wool yarn/roving, felt, flock | covered by T-015/T-126 presets |
| Metal wire | glasses | thin copper-tone wire | ESTIMATE |
| Glass / exterior | window | blown out to near white with soft green bokeh; never a detailed view | `#E6E5D7`, `S50` 0.06 |
| Emissive accent | boat glow, sparkles | warm gold, very small area | already in `VISUAL_TARGET.md` |

### 1.3 Shape language and construction

- Everything is built from **few, thick, simple parts**: boards, square posts, boxes, cylinders, discs. No thin sheet
  material except paper and wire; tray and cup walls are visibly thick.
- **All hard edges are rounded.** Table rails and legs have a radius of roughly 8–15 % of the part's smallest
  dimension (`04_bevel_rule.jpg`: 8 % reads closest for boards, 16 % for the tray rim). No razor edges anywhere.
- Furniture is **joined like real furniture** (mitred frame corners, legs under aprons, board joints in the top) but
  with child-furniture proportions: thick legs, low heights.
- Proportions are toy-like: objects are large relative to hands, with details reduced (scissors have no rivet
  detail, crayons no print).
- Flat graphic content (children's drawings, flower posters, chalkboard) is carried by **texture on paper planes**, not
  geometry.
- The set is a **real room at child scale**: floor, walls, a large window, shelving along the walls, a second table
  group behind.

### 1.4 Light, lens, colour (measured)

- One large soft daylight source (window), warm bounce fill, bright interior. Whole-frame luma: wide shots
  `Y05/Y50/Y95` = 27–35 / 105–131 / 165–232 (desk and wide shots); water inserts 38–73 / 117–134 / 188–215. These fall inside the envelopes
  already in `docs/references/VISUAL_TARGET.md`; no change proposed there.
- Shallow depth of field in every shot. Share of 32 px tiles with less than 15 % of the sharpest tiles' detail
  energy: 39–43 % in the paperboat wides, 50–55 % in watertable, 64–73 % in the macro inserts. (The measure also
  counts flat surfaces, so read it as a ranking, not as blur percent.)
- Saturation: wides `S50` 36–46 %, `S90` 71–76 %; water inserts `S50` 19–27 %. Pixels with S > 0.7 are 11–16 % of a
  wide frame and 0–5 % of an insert. Much of that is the characters' own colours (hoodie, hair).
- Palette (`03_palette_measured.png`): warm cream and honey wood as the base, sage / coral / dusty rose / powder
  blue as textile pastels, blue plastic + water + paper as the cool relief, saturated primaries only as small
  blurred accents.

## 2. Material library

One library for characters, props and environments. The fibre half exists (`pipeline/charsys/materials/presets*.json`);
the proposal adds a **hard-surface half** with the same resolver and JSON conventions. Ranges are starting values
for Principled BSDF in Cycles; the swatch column says what T-170 actually rendered.

| Preset (proposed) | Base colour range | Roughness | Other | Detail layer | Swatch status |
|---|---|---|---|---|---|
| `wood/light-satin` | `#C8A47C`–`#DDC09A`, grain dark `#A8794B` | 0.38–0.50 | coat 0.15–0.30, coat roughness 0.2–0.3 | grain along the part's long axis, period 1–3 mm, contrast 8–15 % luma, bump ≤ 0.4 mm | rendered; grain too faint and too pale vs reference |
| `wood/worn` | `#9A7350`–`#B08560`, dark `#6B4630` | 0.55–0.70 | no coat | as above with contrast 15–25 %, plus scuff mask (5–15 % area, lighter, +0.25 roughness) and 1–3 board joints | rendered; scuffs too blotchy, need to be thinner and grain-aligned |
| `paint/toy-gloss` | saturated primaries, S 0.75–0.90 | 0.20–0.32 | coat 0.5–0.7 | none | rendered |
| `plastic/semi-gloss` | `#5F86AE` family, pastel | 0.25–0.38 | coat 0.2–0.4 | very fine noise bump, optional | rendered |
| `plastic/gloss` | saturated | 0.12–0.20 | — | none | rendered |
| `paper/card` | `#ECE8E0`–`#F4F1EA` | 0.65–0.80 | subsurface 0.1–0.2 at 1–2 mm; thickness 0.2–0.4 mm real geometry | fibre noise, amplitude below 3/255 luma (`VISUAL_TARGET`) | rendered; exposure too high to judge the tooth |
| `water/shallow` | clear, tint from container | 0.0 | IOR 1.333, transparent shadows, depth 10–40 mm | ripple normal: ring wavelength 8–20 mm, amplitude 0.3–1.5 mm, animated | rendered as a prototype only: **not matched** (no readable reflections or ring highlights at this angle) |
| `wax/crayon` | saturated, S 0.6–0.8 | 0.38–0.48 | subsurface 0.2–0.4 at 2–3 mm | fine noise | rendered, ESTIMATE (no usable reference patch) |
| `ceramic/matte` | warm beige | 0.50–0.62 | — | low noise bump | rendered |
| `wall/plaster` | `#E4D4C0`–`#EFE3D0` | 0.85–0.95 | — | large soft bump ≤ 0.6 mm | rendered |
| `metal/wire` | copper `#B4744A` | 0.25–0.35 | metallic 1 | none | rendered, ESTIMATE |
| `textile/rug-loop` | pastel fields | 0.95–1.0 | sheen 0.4–0.7 | loop rows 3–5 mm pitch, bump 1.5–2.5 mm; fibre geometry only for close shots | rendered; reads as coarse canvas, pile height missing |
| `textile/canvas` | sage / coral / blue | existing `woven cotton` | | | existing preset, rendered: fits |
| fibre presets | — | existing `felt`, `fleece`, `wool yarn`, `skin-flock/3`, … | | | existing, rendered: see finding below |

Findings from the swatches:

- The existing fibre presets were calibrated on character-sized surfaces. On 6–9 cm test blocks `felt`, `fleece` and
  `wool yarn` come out too shaggy. Soft props need either a size-relative fibre length or prop-specific overrides.
  This matters for every plush toy in the set.
- The hard-surface prototypes are a plausible family, not a match. The swatch rig is brighter and less saturated than
  the reference frames, so colours cannot be compared one to one. Matching needs the calibrated shot lighting
  (`render_calibration`), which was outside this task.

## 3. Procedural construction system

### 3.1 Principle

An object is **data**: a list of parts, each a shared primitive with dimensions, a rounding class and a material
preset. Code never knows object names (same rule as for characters). Today `content/assets/*.asset.json` has exactly
one `mesh.primitive` per asset and `shot_render.prop_mesh()` builds it; `content/sets/*.set.json` is boxes only.
The proposal generalizes that one step, without replacing either format.

### 3.2 Shared primitives

| Primitive | Parameters | Covers |
|---|---|---|
| `rounded_box` | size, edge radius, optional per-axis taper | boards, legs, blocks, books, bins, shelves |
| `rounded_cylinder` | radius, height, rim radius, optional wall (open top) | cups, crayons, pegs, wheels, bowls |
| `lathe` | profile polyline, segments | stacking rings, vases, knobs, balls, pears |
| `sheet` | outline, thickness, fold lines + angles | paper, card, flags, posters, book pages |
| `tube_path` | path, radius profile | wire glasses, handles, scissor loops, cords |
| `shell_tray` | outer box, wall, rim radius, floor | trays, tubs, drawers, crates |
| `soft_blob` | superellipsoid + fibre preset | plush toys, cushions, pom-poms (reuses `geom.py` lofts) |
| `liquid_surface` | container reference, level, ripple sources | water |

Modifiers applied by rule, not by hand: bevel (from rounding class), weighted normals, optional boolean cut, array /
mirror for repeats (shelf compartments, chair legs), solidify for sheets and shells.

### 3.3 Rounding rules

| Class | Edge radius | Use |
|---|---|---|
| `crisp` | 0.3–0.5 mm fixed | paper, card, metal wire ends |
| `soft` (default) | 6–10 % of the smallest part dimension, clamped to 1.5–12 mm | wood boards, blocks, furniture |
| `chunky` | 14–20 %, clamped to 3–20 mm | moulded plastic, tray rims, toy parts |
| `pillow` | 30–50 % | soft toys, cushions |

Segments scale with on-screen size (3 for background, 6 for hero). No part is built without a class.

### 3.4 Code architecture (proposed, new files only)

```
pipeline/worldsys/
  primitives.py     the eight primitives above -> mesh (pure functions, deterministic)
  rounding.py       rounding classes -> bevel width/segments
  build_object.py   asset JSON (parts list) -> Blender object(s), sockets, material slots
  build_set.py      set JSON -> instances of assets + architecture (walls, floor, window)
  dressing.py       seeded scatter with density budgets (section 4)
  materials_hard.py hard-surface presets -> node graphs (same resolver API as charsys/materials/builder.py)
content/materials/world_presets.json   the table in section 2
content/assets/*.asset.json            plush.asset v2: "parts": [...] replaces the single "mesh"
content/sets/*.set.json                plush.set v2: references assets instead of raw boxes
```

- The material resolver stays single: `resolve_preset(name)` learns one more family (`wood/…`, `plastic/…`), so a part
  can name a fibre or a hard preset the same way.
- `shot_render.py` calls `build_object` where it calls `prop_mesh` today. v1 assets (one primitive) keep working
  unchanged, so existing shots and tests stay valid.
- The engine (frozen renderer, TD-43) keeps using the collision shape and sockets only. Visual parts are
  Blender-side, so no engine change is needed for looks.

### 3.5 How T-163 fits

T-163 gave 13 props with correct **interaction data** (sockets, grasp sites, affordances, collision, verb tests) and
placeholder looks (one felt primitive each). That data is kept as is. Each prop gets a `parts` list and real
material presets: for example `pencil` becomes a rounded cylinder in `wax/crayon` or painted wood, `block` a `soft`
rounded box in `wood/light-satin` or `paint/toy-gloss`, `felt_tray` a `shell_tray` in `plastic/semi-gloss`, `book` a
box plus `sheet` pages. `ball`, `toy`, `apple` may stay fibre. Collision and sockets must not move, so the 593 verb
assertions remain the regression.

## 4. Scene rules

| Topic | Rule |
|---|---|
| Lighting | One window key (large area light or portal, 5000–5800 K) from one side, warm bounce fill, no visible hard sun patches on the subject. Numeric targets stay in `VISUAL_TARGET.md` (fill 1.6–2.5:1, R/B 1.03–1.15 on neutrals). Window itself exposes to near white. |
| Lens | 40–55 mm equivalent for group shots, 65–85 mm for inserts (existing target). |
| Depth of field | Always on. Subject plane sharp; anything more than about one head-depth behind is visibly soft; far shelves and wall art are colour shapes only. Starting apertures to calibrate: f/2.8–4 for wides, f/2–2.8 for inserts at the scene's real scale. |
| Scale | One world scale in metres, as `content/assets` already uses. Furniture is sized to the characters (table top near character hip height, chair seat near knee height). Hand-held objects are 0.6–1.0 hand lengths. Thickness is exaggerated: boards ≥ 8 % of their width, walls of containers ≥ 4 mm. |
| Surface detail | Detail lives at two scales only: form (rounded parts) and one material texture (grain, weave, pile). No decals, labels, screws or print except children's drawings on paper. |
| Wear | Default is clean with soft edges. Wear is a per-object parameter 0–1 (scuff mask + roughness) used on a few hero wood surfaces; never dirt, stains or damage. Level depends on question 1. |
| Palette | 60–70 % of the set area cream + light wood; 20–30 % textile pastels (S 0.3–0.55); cool relief from water, plastic, paper; saturated primaries (S > 0.75) under about 5 % of set area and never in the focus plane unless they are the story object. Set colours must not match a character's garment colour at the same saturation. |
| Background density | Three depth layers. Hero (focus plane): 3–8 objects, each readable. Mid (0.5–1.5 m behind): furniture + 10–20 simple objects. Far (walls): shelving blocks, wall art, window. Detail per object drops with layer: far objects are single primitives with one colour. Leave 30–40 % of the wall and floor area empty. |
| Foreground | An out-of-focus foreground object (teddy, crayon, chair back) at a frame edge is used in most reference shots; allow one per shot. |

## 5. Comparison summary

`02_reference_vs_swatches.jpg` is the comparison. Honest reading:

- Close in character already: semi-gloss and gloss plastic, painted toy, matte cup, wall, canvas, flocked skin.
- Right family, needs calibration: both woods (grain strength, colour depth), paper (exposure), rug (pile).
- Not matched: water. It needs reflections of the surroundings, ring ripples with highlights and a low camera,
  which only a lit scene can show.
- Not verifiable from the videos: crayon wax and glasses wire (too small).
- Existing fibre presets need a size rule before they are used on small props.

## 6. Phased plan

Effort is in implementer task-days (one focused task of the usual size = 1), not calendar time. Each phase ends with
an owner review; none starts without approval.

| Phase | Content | Deliverable | Effort |
|---|---|---|---|
| W0 | Owner decisions on the open questions | decisions recorded | — |
| W1 | Hard-surface material presets (section 2), schema + resolver family, swatch sheet under calibrated shot lighting, per-preset measurements against the reference patches | `world_presets.json`, swatch evidence, tests for the schema | 2–3 |
| W2 | Primitives + rounding rules + `build_object`; `plush.asset` v2 with v1 fallback; determinism test | `pipeline/worldsys/` core, contact sheet of primitives | 3–4 |
| W3 | Restyle the 13 T-163 props (+ paper sheet, cup, tray) with parts and presets; verb tests unchanged | prop contact sheet before/after | 2–3 |
| W4 | Water: surface, ripples from contact events, tray/table variants; one still + one short loop | water evidence vs paperboat f168/f192 | 3–4 |
| W5 | Furniture + room kit (table, chair, shelf, bins, window wall, floor, rug, wall art from textures); `plush.set` v2 | one kindergarten corner set | 4–5 |
| W6 | Dressing with density budgets, lighting/DoF presets per shot type, fibre size rule for soft props | two reference-matched frames (desk wide, water-table wide) with measurements | 3–4 |
| W7 | Integration in `run_shot.py`, render-time budget, documentation | one existing shot re-rendered in the new world | 2 |

Total 19–25 task-days. W1 and W2 are independent and can run in parallel; W3–W5 depend on both; W4 carries the
highest risk (render time and look).

Not included: new character work, engine changes, animation of water physics beyond ripple rings, outdoor sets.

## 7. Open questions for the owner

1. **Wood condition.** Worn plank table (paperboat) or clean light oak (watertable), or both as a per-object wear
   setting? This sets the default wear level for every set.
2. **Water container.** Blue plastic tray inside a wooden table, or water directly in the wooden basin with pebbles?
   The two videos show different objects.
3. **How literal should the room be?** Rebuild this specific kindergarten, or a kit that produces rooms in this style?
   The plan assumes the kit, with this room as its first set.
4. **Soft props.** Should the T-163 props stay felt where plausible (ball, toy, apple), or should all hand props
   become hard materials as in the videos (paper, plastic, wood)?
5. **Wall art and posters.** These need image textures. May they be generated/drawn assets under `assets/`, and who
   approves them? (No such textures exist in the repository today.)
6. **Render budget.** Water, depth of field and a dressed room raise render time per frame. Is there a target time
   per frame that the world must stay within?
7. **Glow/sparkle effect.** Out of scope here; confirm it stays a separate later task.
8. **Reference quality.** The videos are low resolution. If higher-resolution stills of the same scenes exist, W1
   calibration would be considerably more reliable.

## Reproduce

```
python3 docs/evaluation/world/T-170/scripts/measure_reference.py
blender -b --factory-startup -P docs/evaluation/world/T-170/scripts/render_swatches.py -- --px 320 --spp 64
(cd docs/evaluation/world/T-170/scripts && python3 make_sheets.py)
```

Not tested: no ctest or pipeline run (no code outside this folder was touched). Swatch render about 2.5 min on 4 CPU
cores.
