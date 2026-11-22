# T-189 · World & environment reuse survey (RESEARCH ONLY)

Input SHA `f2b12c2`. Nothing outside this folder was changed: no pipeline, asset, spec or test change, no Codex.
Downloads stay **out of git** (session scratch folder). Only scripts, two evidence sheets (≤ 1024 px) and `sources.json`
(URL, SHA-256, bytes, licence of every downloaded file, plus per-model statistics) are committed.
Blender: bpy 5.3.0 (Python 3.13) via `/usr/local/bin/blender` → `tools/bpy_blender.py`, Cycles CPU, 4 cores.

This builds on, and does not repeat, T-170 (style guide and plan), T-170b (alternatives; Blender built-ins), T-170c
(Poly Haven texture picks) and T-170d (ambientCG rug, trimmed plan at **4.5–6 task-days**, owner amendment
"ready-made materials only: tint / scale / mapping").

| File | Content |
|---|---|
| `evidence/01_polyhaven_models_raw_tint_flat.jpg` | 16 CC0 Poly Haven models imported headless, each in three looks: **raw** (own scanned textures) · **tint** (own textures × palette colour) · **flat** (built-in Principled in one T-170 palette colour + Cycles Bevel node). Label: tris, size in metres |
| `evidence/02_kindergarten_corner_reuse.jpg` | a kindergarten corner assembled **only from reused parts** (9 CC0 models, 3 CC0 image sets, CC0 HDRI, built-in shaders): **A** models as downloaded, **B** "house look" (owner rule) |
| `sources.json` | every downloaded file (83 model files, 10 texture/HDRI files): URL, SHA-256, bytes, licence; model stats (dims, tris, objects, materials, import time, render time) |
| `scripts/` | `fetch_ph_models.py` (Poly Haven model download + hashes), `render_models.py`, `make_sheet.py`, `vignette.py` (throwaway) |

## 0. Answer in short

1. **Reuse works headless today for the hosts that are open.** Poly Haven models import with
   `bpy.ops.import_scene.gltf` in 0.01–0.4 s each, render in ~2 s at 256 px/32 spp, and the whole kindergarten corner
   (9 models + room) renders in 35 s at 768 px/64 spp. No add-on, no GUI step, no new material.
2. **The house look comes from material override, not from the asset's own textures.** Tinting a scanned texture
   (look *tint*) does not work: dark or weathered scans stay dark and dirty. Replacing the asset's materials with
   `oak_veneer_01` / built-in Principled in one palette colour + Bevel node (look *flat*, vignette **B**) makes
   unrelated CC0 assets read as one pastel set (`02_…jpg`). This stays inside the owner rule (ready-made materials,
   tint / scale / mapping only) and means **only geometry has to be stored**: 9 models ≈ 1.2 MB of `.gltf`+`.bin`.
3. **Fit depends on the mesh, not on the source.** Low-poly, chunky meshes (Poly Haven `painted_wooden_*` family,
   470–1250 tris; `plastic_crate_02`, `wicker_basket_01`, `rubber_duck_toy`, `ceramic_vase_01`, `wooden_bowl_02`)
   fit. Photoreal-detailed meshes do not (`potted_plant_01` 176k tris, `stationery_supplies`, metal-legged
   `SchoolChair_01`). Thin spindles (`painted_wooden_chair_01` back) are the main style break versus T-170's
   "few thick parts".
4. **The best-fitting stylized kits (Kenney, Quaternius, KayKit, Tiny Treats; all reported CC0) are behind blocked
   hosts** (`kenney.nl`, `quaternius.com`, `itch.io`, `poly.pizza`, `opengameart.org`). They are the highest-value
   item to unblock: rounded, chunky, flat-colour furniture and props, and whole bedroom / kitchen / bathroom / picnic
   sets for the later environments.
5. **Procedural generators and AI 3D do not pay off for v1.** Infinigen (BSD-3, 91 indoor factories) is the only
   serious generator but pins `bpy==4.2.0` / Python 3.11 (verified in its `pyproject.toml`), so it can only be an
   offline side-car baker; its look is photoreal. Most room-layout research (ATISS, DiffuScene, InstructScene,
   BlenderProc 3D-FRONT loaders, Holodeck) depends on non-commercial data. AI image/text-to-3D: Hunyuan3D is
   **not licensed in the EU**; TRELLIS needs a GPU and its texture baking uses NVIDIA's non-commercial `nvdiffrast`;
   only Stable Fast 3D runs on CPU (Stability Community Licence, < $1M revenue).
6. **Revised world effort: 4–5.5 task-days for the kindergarten** (T-170d: 4.5–6), and **≈ 1–1.5 task-days per later
   everyday set** if the CC0 kit hosts are allowed (vs ≈ 2–3 by building every object from `parts` data). The
   saving on the first set is small; the gain is variety and quality of dressing, and the later sets.

## 1. Network: what was reachable (tested 2026-11-21 from this container)

Reachable: `api.polyhaven.com`, `dl.polyhaven.org` (asset files), `polyhaven.com`, `ambientcg.com` (+ redirect to
`acg-download.struffelproductions.com`), `github.com` **via git clone only**, `raw.githubusercontent.com`, `pypi.org`
+ `files.pythonhosted.org` (pip), `gitlab.com`.

**Blocked hosts (proxy refused CONNECT; not worked around). Owner approval needed per host:**

| Host | What for | Priority |
|---|---|---|
| `kenney.nl` | Kenney Furniture Kit, Toy Car Kit, Food Kit, Holiday Kit, Nature Kit (CC0 zips) | **high** |
| `quaternius.com` | Quaternius Furniture Pack, Ultimate House Interior, Stylized Nature MegaKit (CC0) | **high** |
| `itch.io`, `kaylousberg.itch.io`, `tinytreats.itch.io` (and the itch.io download CDN, host not yet known) | KayKit Furniture Bits; Tiny Treats Homely House / Charming Kitchen / Bubbly Bathroom / Pleasant Picnic (CC0) | **high** |
| `poly.pizza` (+ `api.poly.pizza`) | low-poly model search incl. Quaternius mirrors (per-model CC0/CC-BY) | medium |
| `opengameart.org` | CC0 mirrors of Kenney/Quaternius/KayKit/Tiny Treats, "Low Poly House Interior" | medium (alternative to the three above) |
| `extensions.blender.org` | GPL extensions (Sun Position, Archimesh, Sapling, Modular Tree, Home Builder 5); licence page | low |
| `studio.blender.org`, `download.blender.org` | Blender Studio open-movie assets (CC-BY), demo files ("Classroom" CC0) | low |
| `huggingface.co`, `cdn-lfs.huggingface.co` | AI 3D model weights (TRELLIS, SF3D), Objaverse metadata | low (not recommended for v1) |
| `api.sketchfab.com`, `sketchfab.com` | CC0/CC-BY model search (needs OAuth token) | low |
| `3d-api.si.edu`, `api.si.edu`, `3d.si.edu` | Smithsonian CC0 3D / 2D (wall art) | low |
| `api.github.com`, `github.com` web/archive URLs | release zips, API; `git clone` already works | low |
| `docs.ambientcg.com`, `acg-media.struffelproductions.com` | ambientCG licence page and thumbnails (licence read from front page instead) | low |
| `www.blenderkit.com`, `sharetextures.com`, `www.cgbookcase.com`, `www.thebasemesh.com`, `cdn.jsdelivr.net`, `infinigen.org`, `archive.org` | other sources listed below; none needed for the recommendation | low |

Web pages for licences and catalogues were also read through the web research tool, not through this container.
Claims marked **(snippet)** rest only on search-result excerpts of the official page because the page itself was
not readable; they must be re-read before adoption. Everything else was read directly (date checked 2026-11-21).

## 2. Ranked options per category

Licence columns: **C** = commercial use (YouTube) allowed · **R** = raw files may be committed to the repo ·
**A** = attribution required. Effort in implementer task-days. Fit = to the T-170 stylized plush world.

### 2.1 Materials (owner rule: ready-made only; T-170c/d picks stay)

| Rank | Option | What | Licence C/R/A | Headless / pin | Fit | Effort | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **Keep T-170c/d picks**: `oak_veneer_01`, `laminate_floor_02`, `Carpet016`, HDRI `lebombo` | 9.3 MB, hashes in T-170 | CC0 · yes · no | image files; SHA-256 pinned | verified in vignette B | 0 (already in W1) | free |
| 2 | **Built-in Principled BSDF + palette tint + Cycles Bevel node** for every painted / plastic / ceramic part | — | Blender output free | built-in, versioned with Blender | verified: makes mixed CC0 meshes coherent (`01`, `02`) | 0 | free |
| 3 | Poly Haven textures (871: wood 138, fabric 43, plaster 33, floor 271) | extra woods/fabrics if a later set needs one | CC0 · yes · no | public API, direct URLs | as T-170c (needs softening/tint) | 0.1 per set | free |
| 4 | ambientCG (2,043 materials: Wood 102, Fabric 90, Wood Floor 74, Tiles 164, Wicker 19, Carpet 16, Plastic 25, Painted Plaster 18, Painted Wood 17, Paper 6, Cardboard 4; 23 indoor HDRIs) | kitchen/bathroom tiles, paper/cardboard, wicker | CC0 · yes · no | public API v2 (counts from `api/v2/full_json`, 2026-11-21) | good for tiles/paper | 0.1 per set | free |
| 5 | Existing project fibre presets (`pipeline/charsys/materials/presets*.json`) | felt, woven cotton, fleece for soft props | own | in repo | proven on characters; size rule open (T-170) | 0 | — |
| — | not recommended: BlenderKit (royalty-free items may not be redistributed in a repo; add-on/API key), Fab/Megascans (Fab licence forbids raw redistribution; photoreal), paid shader packs (vendor EULA, lock-in) | | | | | | |

### 2.2 Furniture and props

| Rank | Option | What | Licence C/R/A | Headless / pin | Fit | Effort | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **Poly Haven models, selected low-poly ones** (tested) | 522 models; furniture 85, seating 34, table 27, shelves 16, containers 68. Fits: `painted_wooden_chair_01/_02`, `_stool`, `_table`, `_shelves`, `_cabinet(_02)`, `_bench`, `_nightstand`, `plastic_crate_02`, `wicker_basket_01/_02`, `rubber_duck_toy`, `wooden_bowl_02`, `ceramic_vase_01–04`, `Shelf_01`, `wooden_crate_01` | CC0 · yes · no (polyhaven.com/license, read) | API + direct URLs; files hash-pinned (`sources.json`); glTF import 0.01–0.4 s | **good after material override** (vignette B); thin chair spindles break "thick parts"; edges are sharp (Bevel node softens only shading) | 0.5–1 (loader + table of picks) | free |
| 2 | **KayKit Furniture Bits** (Kay Lousberg) | ~50 rounded low-poly furniture pieces, glTF/FBX/OBJ | CC0 (snippet, kaylousberg.itch.io/furniture-bits) | itch.io download flow (not a stable URL) → vendor zip + hash | **excellent** (rounded, chunky) — not tested (host blocked) | 0.5 | free / pay-what-you-want |
| 3 | **Tiny Treats** (Homely House, Charming Kitchen 34+, Bubbly Bathroom, Pleasant Picnic) | pastel rounded interior sets | CC0 for the free sets (snippet, tinytreats.itch.io pages); paid "Playful Bedroom" licence unknown | itch.io / OpenGameArt / Godot Asset Library mirrors | **closest to our look**; best source for bedroom/kitchen/bathroom/park sets — not tested | 0.5 per set | free |
| 4 | **Kenney** (Furniture Kit 140 files, Toy Car Kit 100, Food Kit 200, Holiday Kit 100 incl. toy train) | flat-colour low-poly furniture and toys | CC0, credit optional (snippet, kenney.nl) | direct zips, no login | very good shapes, flat colours → override; scale to child size | 0.5 | free |
| 5 | **Quaternius** (Furniture Pack 23, Ultimate House Interior 80+) | low-poly interior | CC0 (snippet, quaternius.com/packs/furniture.html) | direct zips; `.blend` source in some packs | very good | 0.5 | free / optional paid source |
| 6 | Own `parts` builder (T-170b/d: box + cylinder + Bevel/Solidify) | table, stool, shelf, bins, the 16 T-163 props | own | fully deterministic | verified in T-170b kit test | already in T-170d W2/W5 | — |
| 7 | Poly Pizza / Google Poly archive (Icosa, polygone.art) | 10k+ low-poly models | per model CC0 or CC-BY (some NC/ND reported) | API needs a free key (not verified) | mixed quality | audit per model | free |
| 8 | The Base Mesh (1,100+ neutral meshes) | base shapes | CC0 (third-party reports; not verified) | direct zips (not verified) | medium | — | free |
| — | not recommended: Smithsonian 3D (photoreal scans, per-item terms), Sketchfab (per-model licence audit, OAuth, API future tied to Fab), Blender Studio open-movie assets (CC-BY credit, shot-specific, Vault subscription), Objaverse (self-declared licences, NC mix, provenance risk), ABO / Google Scanned Objects / OmniObject3D (CC BY 4.0 but photoreal and branded products), ShapeNet / PartNet / ModelNet / HSSD / 3D-FUTURE / 3D-FRONT (non-commercial) | | | | | | |

### 2.3 Room and architecture

| Rank | Option | Notes | Licence | Headless | Effort |
|---|---|---|---|---|---|
| 1 | **Boxes from `parts` data** (floor, 2–3 walls, skirting) as in T-170d W5 | verified in vignette (3 boxes) | own | yes | in W5 |
| 2 | Kenney / Quaternius / Tiny Treats wall, door and window pieces | modular kit pieces for later sets | CC0 (snippet) | import glTF | 0.25 per set (blocked) |
| 3 | Infinigen-Indoors as **offline side-car** (own venv, bpy 4.2, export `.blend`/USD, restyle in 5.3) | 91 indoor factories (chairs, tables, desks, shelves, bookcases, baskets, rugs, windows, lamps, cups, books, plant pots); room solver for dining/bath/bed/kitchen/living, **no classroom**; ~8–13 min per room on CPU (docs); photoreal | BSD-3 code; output procedural (commercial OK, not verified) | **install verified here** (uv venv, Python 3.11, `bpy==4.2.0`, `infinigen 1.26.0`, 26 s); a generator run was **not executed** (§5) | 1.5–2 to wire + restyle; not for v1 |
| 4 | Home Builder 5 (GPL-3, Blender 5.0 extension) | rooms + snapping cabinets for kitchen/shop | GPL-3 (code); output ours | operators are UI-oriented → wrapper | not tested; 1+ |
| — | not recommended: Archimesh (stale, Blender 5 bugs reported), Archipack free (Blender 3.x only), Building Tools (exteriors, 5.x not verified), BlenderProc (downloads its own Blender 4.2.1; GPL-3; 3D-FRONT loader non-commercial), ProcTHOR/AI2-THOR (Unity JSON), Holodeck/SceneSmith (LLM + Objaverse/Hunyuan assets, non-deterministic, GPU) | | | | |

### 2.4 Scatter and dressing

| Rank | Option | Notes | Licence | Headless | Effort |
|---|---|---|---|---|---|
| 1 | **Hand-placed dressing lists with seeded jitter** (T-170b/d) | ≤ 10–20 items per set; the vignette used 10 placements, no solver | own | yes | in W6 |
| 2 | Blender Essentials GN node groups (*Scatter on Surface*, *Randomize Transforms*, *Instance on Elements*) | bundled with bpy 5.3, load with `bpy.data.libraries.load(…, assets_only=True)` (verified in T-170b) | ships with Blender (asset licence: CC0 per Blender asset repo, not verified) | yes, seed input | 0.25 when a shot needs dense scatter (books, crayons, leaves) |
| 3 | Rule-based layout JSON (LayoutGPT idea: an LLM or a person writes boxes; our validator places them) | only if many sets are needed | own | yes (cache the JSON) | 1+ (later) |
| — | not recommended: Geo-Scatter (paid, no Python API), OpenScatter (archived), BagaPie (pie-menu UI, paid packs) | | | | |

### 2.5 Lighting / HDRI

| Rank | Option | Notes | Licence |
|---|---|---|---|
| 1 | **Keep `lebombo`** (T-170c) + window area light + warm bounce | verified again in vignette (35 s/frame, 768 px, 64 spp) | CC0 |
| 2 | Poly Haven indoor HDRIs as alternates: `artist_workshop`, `lythwood_room`, `white_studio_06`, `brown_photostudio_03/04/05`, `glasshouse_interior` | 998 HDRIs, 301 indoor, 369 low-contrast (API) | CC0 |
| 3 | Built-in: area-light **portal** on the window, Cycles light linking, Sky Texture | Blender 5.0 renamed Nishita to "Single Scattering" and changed the default: pin the mode in code | GPL program, output free |
| — | Sun Position extension (not needed: set the light angle in code), Gaffer (UI only), CC0 IES (Pixar RenderMan profiles public domain) only if lamps are modelled | | |

### 2.6 Special: water, paper, cloth, plants, wall art

| Topic | Best option | Licence | Headless | Note |
|---|---|---|---|---|
| Water (deferred in T-170d) | **Dynamic Paint wave canvas** or own **GN simulation-zone ripple**, baked once and cached; HDRI reflections | Blender built-in | `bpy.ops.dpaint.bake()`; known loop-bake crash needs `view_layer.update()` (issue #117186) | **No CC0 water texture exists** on Poly Haven or ambientCG (API check): ripples need a procedural normal, which conflicts with "ready-made materials only" → owner decision. FLIP Fluids (GPL source / paid build, 4.5–5.3) and Mantaflow are overkill for a tray |
| Paper / paper boat | **Script-built boat from fixed vertices** + Solidify (T-187 territory) + ambientCG `Paper001–006`, `Cardboard001–004` | own / CC0 | yes | no verified CC0 paper-boat model found; origami add-ons (licence not verified) and cloth-folding are hard to control |
| Cloth | Built-in Cloth modifier (rug drape, curtain) baked to cache; bunting = curve + instanced triangles (Essentials *Instance on Elements*) | built-in | point-cache bake | GN Cloth Dynamics (5.2+) is experimental; Simply Cloth is paid ($36, Superhive) |
| Plants | **Kenney Nature Kit / Quaternius Stylized Nature MegaKit** (CC0, low-poly) → flat override; fallback: a script-built pot + 3–5 leaf cards | CC0 (snippet) | import glTF | Poly Haven plants are photoreal and heavy (`potted_plant_01` 176k tris, fails in `01`); Sapling reported limited in 5.0 |
| Wall art / drawings | CC0 only: Openclipart (CC0 unless noted), Smithsonian Open Access items marked CC0, Kenney 2D; fonts Andika / Comic Neue (OFL) | CC0 / OFL | image on a `sheet` | unDraw allowed but no redistribution; Noun Project needs credit. T-170 question 5 (who approves images) still open |

### 2.7 AI text/image-to-3D and datasets (summary)

| Option | Licence for an EU studio, commercial | Runs here? | Verdict |
|---|---|---|---|
| Hunyuan3D 2.x / Sparc3D·Hi3D (needs Hunyuan weights) | **not licensed in the EU, UK, South Korea** (licence territory clause, read on GitHub) | GPU | **excluded** |
| TRELLIS / TRELLIS.2 (MIT) | code MIT, but textured export uses `nvdiffrast` (NVIDIA licence: non-commercial) | GPU ≥ 16–24 GB | legal sign-off needed; no |
| Stable Fast 3D | Stability Community Licence: commercial < $1M revenue, registration | **CPU backend** (only one) | possible for one-off organic props; low detail |
| TripoSR (MIT), TripoSG (MIT code; weights + RMBG dependency not verified), Step1X-3D (Apache-2.0), Shap-E (MIT) | OK / partly unverified | GPU 6–29 GB | not for v1 |
| InstantMesh, Zero123++ | weights CC-BY-NC | — | excluded |
| Paid APIs (Meshy, Tripo, Rodin paid plans) | user owns output on paid plans; free tiers CC-BY or unclear | API | possible, per-asset cost + lock-in → **ask owner** |

Expected quality for our props: dense triangle meshes (often 100k+ faces) with baked lighting, needing decimation and
material override; seeds give only rough reproducibility. For tables, chairs, shelves and cups the CC0 kits or bevelled
boxes are cleaner, deterministic and licence-free. YouTube's AI-disclosure rule covers realistic synthetic content;
clearly animated content is exempt (support.google.com/youtube/answer/14328491, snippet).

## 3. Recommended reuse stack

1. **Materials:** unchanged from T-170d (3 CC0 image sets + HDRI + built-in Principled in the palette + Cycles Bevel
   node). Every imported asset gets a **material override** from one table: `wood → oak_veneer_01`,
   `painted/plastic → Principled <palette colour>`, `soft → existing fibre preset`. The asset's own textures are
   never used, so only geometry is vendored.
2. **Furniture/props:** CC0 low-poly models from **Poly Haven now** (picks in §2.2), **KayKit / Tiny Treats / Kenney /
   Quaternius once their hosts are allowed**. Own `parts` builder stays for the 16 T-163 interaction props (their
   collision and sockets must not move) and for any gap (crayons, paper, blocks, bins).
3. **Asset format in the repo:** `content/world_assets/<source>/<id>/` with geometry-only `.glb` (textures stripped at
   vendoring) + one `SOURCES.json` row per asset (source URL, licence, SHA-256 of the original download, date,
   scale to child size, material-override map). 9 vignette models ≈ 1.2 MB; a full kindergarten ≈ 2–4 MB.
4. **Room:** boxes from data; window = HDRI + area light (+ portal); no generator.
5. **Dressing:** hand-placed lists with seeded jitter; Essentials *Scatter on Surface* only for dense small items.
6. **Water / plants / wall art:** as §2.6; water stays deferred until the owner decides the ripple question.
7. **Not adopted:** Infinigen, BlenderProc, any LLM layout tool, AI 3D generators, datasets, paid packs/add-ons.

## 4. Integration plan and revised effort

| Phase | T-170d | With reuse | Change |
|---|---|---|---|
| W1 presets + image sets + HDRI | 1 | 1 | + material-override table for imported assets (same file) |
| W2 `parts` (box, cylinder) + bevel in `prop_mesh`, v1 fallback | 0.5–1 | 0.5–1 | unchanged (still needed for T-163 props) |
| W2b **asset vendoring + loader** (`fetch` → strip textures → `.glb` + `SOURCES.json` + hash test; glTF import, fit to child size, override) | — | **0.5–0.75** | new |
| W3 preset + bevel for the 16 existing assets | 0.5 | 0.5 | unchanged |
| W5 table, stool, shelf + bins, floor, walls, rug | 1–1.5 | **0.5–0.75** | furniture from CC0 picks instead of `parts` data |
| W6 dressing + light/DoF preset | 0.5–1 | **0.5–0.75** | more and better dressing items for the same placement work |
| W7 integration, one shot re-rendered, docs | 1 | 1 | unchanged |
| **Total kindergarten** | **4.5–6** | **4–5.5** (−0.5 d) | |
| each later everyday set (bedroom, kitchen, bathroom, park) | ≈ 2–3 (estimate: all objects as `parts`) | **≈ 1–1.5** with Tiny Treats/KayKit/Kenney/Quaternius; ≈ 2 with Poly Haven only | |
| water (deferred) | 0.5–1 still / 2–3 rippled | unchanged; Dynamic Paint or GN ripple, baked | |

Ordering: W1 ∥ W2 ∥ W2b → W3, W5 → W6 → W7. W2b can start with Poly Haven only; the blocked kits slot in later
without code change (same loader).

## 5. Feasibility tests run here

| Test | Result |
|---|---|
| Poly Haven model download (16 models, 1k glTF + includes, 28.2 MB) via `api.polyhaven.com/files/<id>` | 14 s; all hashes in `sources.json` |
| Headless glTF import + 3 looks + render (bpy 5.3) | 0.01–0.4 s import, ~2.2 s render per image (256 px, 32 spp); no errors; `01_…jpg` |
| Kindergarten corner from reused parts (`vignette.py`) | 35 s (A) / 33 s (B) at 768×512, 64 spp, seed 0; `02_…jpg` |
| ambientCG catalogue via API (`api/v2/full_json`) | 2,043 materials; category counts in §2.1 |
| Infinigen: `git clone` (commit `53033dd`, 2026-11-10), `pyproject.toml` | pins `bpy==4.2.0`, `requires-python ==3.11.*`; BSD-3 |
| Infinigen in an isolated side-car venv (`uv venv -p python3.11`, `uv pip install -e`) | installs in 26 s; `bpy 4.2.0`, `infinigen 1.26.0`, `procfunc 0.37.1` |
| Infinigen `generate_individual_assets -f ChairFactory` | **not run**: executing the cloned third-party code was refused by this session's permission check; not worked around. Needs Supervisor/owner approval if wanted |
| Infinigen inside our bpy 5.3 / Python 3.13 | impossible as shipped: `procfunc ≥ 0.33` requires Python 3.11 (pip refuses) |
| BlenderProc | cloned only; source states it supports only its own Blender 4.2.1 download (`download.blender.org`, blocked) |

Visual reading of `01` and `02`:
- **flat/house look** turns ten unrelated CC0 models into one pastel set; the oak table and shelves, coral/blue chairs,
  sage stool, crate, basket, duck and bowl read like the T-170 palette without any new material.
- **tint look fails** on dark or weathered scans (painted cabinet, stool, folding stool stay dirty).
- **shape style** is the remaining gap: the painted chair has thin turned spindles and a carved back, and edges are
  sharp (Bevel node only softens shading). Chunkier kits (KayKit, Tiny Treats) should close this; not verified.
- Exposure in the vignette is not calibrated (bright walls); W1 shot lighting still applies.

## 6. Risks

1. **Unverified licences for the best kits.** Kenney, KayKit, Tiny Treats, Quaternius were checked only through search
   snippets (hosts blocked). Re-read each licence page and keep the licence text in the vendored folder.
2. **Style mixing.** Assets from several authors have different proportions and detail levels; the material override
   unifies colour, not shape. Rule: one primary kit per set, pick by silhouette, max ~10 % from other sources.
3. **Sharp edges** on imported meshes; Bevel *modifier* on arbitrary meshes can fail, so only the Bevel *shader* is
   safe without per-asset checks.
4. **Scale**: kit assets are adult or game scale; each needs a child-size fit (done per asset in the loader table).
5. **Poly Haven API terms**: tools built on the public API must show "Powered by Poly Haven" (github.com/Poly-Haven/
   Public-API). Vendoring files with hashes avoids calling the API at build time; the assets themselves stay CC0.
6. **itch.io downloads** have no stable URL: vendor the zip into the repo (or LFS) once, with its hash.
7. **Simulations** (water, cloth) are not documented as bit-deterministic: bake once, cache, render from the cache.
8. **Blender 5.x API drift** breaks third-party add-ons; nothing in the stack depends on one.

## 7. Questions for the owner

1. Allow the **high-priority hosts** `kenney.nl`, `quaternius.com`, `itch.io` (+ its download CDN) — or
   `opengameart.org` as the single mirror host — so the stylized CC0 kits can be tested against vignette B?
2. Accept **imported CC0 geometry + material override** as "ready-made" for furniture and dressing (instead of
   building every object from `parts` data)?
3. Storage: geometry-only `.glb` in plain git (≈ 2–4 MB per set) — OK, or Git LFS?
4. Credits: none are legally needed for CC0; do you want a voluntary credits line in video descriptions?
5. Water: procedural ripple normal (not a ready-made material) or still water only?
6. AI 3D: rule out completely for now (recommended), or allow a paid API (Meshy/Tripo/Rodin) for one-off organic
   props such as a plush toy or plant, with per-asset cost?
7. Infinigen side-car test: approve running Infinigen's own code in an isolated venv (one asset, CPU) if you want
   generator evidence? Not needed for the recommendation.

## 8. Sources (date checked 2026-11-21)

Read directly: polyhaven.com/license; api.polyhaven.com (`/assets?type=models`, `/categories/{models,textures,hdris}`,
`/files/<id>`); ambientcg.com and `ambientcg.com/api/v2/full_json`; github.com/princeton-vl/infinigen (clone,
`pyproject.toml`, `LICENSE`, `docs/source/GeneratingIndividualAssets.md`, `tests/infinigen/assets/list_indoor_meshes.txt`);
raw.githubusercontent.com/DLR-RM/BlenderProc/main/blenderproc/python/utility/InstallUtility.py;
pypi.org/pypi/{infinigen,procfunc,bpy,blenderproc,build123d,cadquery,trimesh}/json; github.com/rlguy/Blender-FLIP-Fluids
(+ wiki "Baking from the Command Line"); github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE,
github.com/Tencent-Hunyuan/Hunyuan3D-2.1; github.com/microsoft/TRELLIS, github.com/microsoft/TRELLIS.2,
github.com/NVlabs/nvdiffrast/blob/main/LICENSE.txt; github.com/Stability-AI/stable-fast-3d (+ LICENSE.md),
github.com/Stability-AI/stable-point-aware-3d; github.com/VAST-AI-Research/{TripoSR,TripoSG,TripoSF};
github.com/TencentARC/InstantMesh; github.com/SUDO-AI-3D/zero123plus; github.com/stepfun-ai/Step1X-3D;
github.com/openai/shap-e; github.com/allenai/objaverse-xl; amazon-berkeley-objects.s3.amazonaws.com/index.html;
github.com/omniobject3d/omniobject3d; github.com/rehg-lab/lowshot-shapebias (toys4k); github.com/allenai/{ai2thor,procthor,Holodeck};
github.com/nv-tlabs/ATISS; github.com/weixi-feng/LayoutGPT; github.com/chenguolin/InstructScene;
github.com/tangjiapeng/DiffuScene; github.com/nepfaff/scenesmith; github.com/ranjian0/building_tools;
github.com/CreativeDesigner3D/home_builder_5; github.com/GitMay3D/OpenScatter; github.com/nortikin/sverchok;
github.com/alessandro-zomparelli/tissue; github.com/MaximeHerpin/modular_tree; github.com/Poly-Haven/Public-API;
docs.blender.org/api/5.3/bpy.ops.dpaint.html; projects.blender.org/blender/blender/issues/117186.

Search snippets only (hosts blocked or not readable): kenney.nl/assets/furniture-kit; quaternius.com/packs/furniture.html;
kaylousberg.itch.io/furniture-bits; tinytreats.itch.io/{charming-kitchen,bubbly-bathroom,pleasant-picnic};
quaternius.itch.io/stylized-nature-megakit; opengameart.org/content/nature-kit; poly.pizza; studio.blender.org/remixing,
studio.blender.org/films/coffee-run/pages/licensing; blender.org/download/demo-files; sketchfab API terms;
blenderkit.com licence; fab.com licence; thebasemesh.com; si.edu open access FAQ; openclipart.org/faq; undraw.co/license;
thenounproject.com/legal; extensions.blender.org (archimesh, bagapie, sapling, modular-tree, sun-position, licences);
superhivemarket.com (simply-cloth, scatter, botaniq, gaffer, random-flow); huggingface.co (objaverse, hssd, PartNetMobility);
shapenet.org/terms; modelnet.cs.princeton.edu; tianchi.aliyun.com (3D-FUTURE/FRONT); docs.meshy.ai/pricing;
tripo3d.ai help; hyper3d.ai/legal/terms; lumalabs.ai/legal/tos; support.google.com/youtube/answer/14328491;
developer.blender.org/docs/release_notes/5.0/rendering/.

## Reproduce

```
S=<scratch outside the repo>; cd docs/evaluation/world/T-189/scripts
python3 -I fetch_ph_models.py --out $S/dl/ph --ids painted_wooden_chair_01,painted_wooden_stool,painted_wooden_table,painted_wooden_shelves,painted_wooden_cabinet_02,SchoolChair_01,SchoolDesk_01,Shelf_01,potted_plant_01,rubber_duck_toy,stationery_supplies,wicker_basket_01,plastic_crate_02,ceramic_vase_01,folding_wooden_stool,wooden_bowl_02
(cd ../../T-170/cc0_test/scripts && python3 -I fetch.py --out $S/dl/tex --ph oak_veneer_01,laminate_floor_02 --maps all --hdri lebombo)
(cd ../../T-170/cc0_test/ambientcg/scripts && python3 -I fetch_acg.py --out $S/dl/tex --acg Carpet016)
blender -b --factory-startup -P render_models.py -- --dl $S/dl --out $S/renders --px 256 --spp 32
python3 make_sheet.py $S/renders ../evidence/01_polyhaven_models_raw_tint_flat.jpg
blender -b --factory-startup -P vignette.py -- --dl $S/dl --out $S/vig_raw.png --look raw
blender -b --factory-startup -P vignette.py -- --dl $S/dl --out $S/vig_house.png --look house
```
Sheet 02 = the two vignette PNGs stacked and scaled to 1000 px height (PIL, inline). Not tested: no ctest or pipeline
run (nothing outside this folder changed); no blocked-host asset; no Infinigen generator run; no shot-calibrated lighting.
