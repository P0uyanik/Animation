# T-170b · World style: reuse alternatives to the T-170 plan (RESEARCH ONLY)

Input SHA `b265c49`. Nothing outside this folder was changed. Question: can the T-170 plan (19–25 task-days) be cut
by reusing existing material libraries, Blender built-ins, add-ons and asset packs?

Evidence in this folder:

| File | Content |
|---|---|
| `scripts/kit_test.py` | throwaway: a desk vignette built from data with **stock Blender primitives + Bevel/Solidify/Weighted Normal modifiers only**, T-170 materials (imported read-only); also geometric vs shader rounding |
| `evidence/kit_desk_vignette.png` | its output, 640×400, 64 spp, 15 s on 4 cores; scene build 0.02 s, 16 objects |
| `evidence/kit_vs_reference.jpg` | same next to `video_paperboat.mp4` t=4 s |

Blender used: bpy module 5.3.0 (Python 3.13) via `/usr/local/bin/blender` → `tools/bpy_blender.py`.

**Limit of this study:** the network proxy refused `api.polyhaven.com`, `dl.polyhaven.org`, `ambientcg.com`,
`extensions.blender.org` and `cdn.jsdelivr.net` (CONNECT 403). No external texture, HDRI or add-on could be
downloaded, so **no CC0 image texture was swatch-tested**. Licence and size statements for external sources below
are from the providers' published terms as known, **not re-verified in this session**.

## 1. Findings from the tests

1. **Construction needs no custom mesh code.** Box, open shell (tray), open cylinder (cup), sheet (paper) and
   cylinder (crayon) come out right from `bmesh` stock primitives plus three stock modifiers and the T-170 rounding
   classes; the whole builder is ~30 lines (`part()` + `rounding()` in `kit_test.py`). `shot_render.prop_mesh()`
   already builds box / sphere / cylinder with `open_top` + `wall`, so the extension point exists. The eight-primitive
   `worldsys/primitives.py` library of T-170 §3.2 is not needed: `lathe` = Screw modifier, `tube_path` = curve bevel
   or Essentials *Curve to Tube*, `soft_blob` = existing `geom.py`; add each only when a prop needs it.
2. **Shader rounding is a usable shortcut for small/far objects.** The two red blocks: left = Bevel modifier, right =
   sharp cube + Cycles *Bevel* shader node (r 4 mm). At this size they read alike; the shader version has a hard
   silhouette. Use geometry for hero/contact parts, shader bevel for background dressing.
3. **Wood is the visible gap, not shape.** Next to the paperboat table the procedural wood looks like painted
   noise: no plank joints, no long open grain, no scratches. T-170 already found grain "too faint". This is exactly
   what scanned CC0 wood textures provide (worn planks, oak veneer), and it is the one material where an image set
   is clearly better than tuning procedural noise. Plastic, paper, ceramic, wall, crayon read acceptably as plain
   Principled presets (T-170 §5 agrees).
4. **Blender's bundled assets do not cover the world.** `datafiles/assets` in bpy 5.3 has node groups only: GN
   Essentials (*Scatter on Surface*, *Array*, *Curve to Tube*, *Randomize Transforms*, *Instance on Elements*,
   *Smooth by Angle*, …), compositing (*Bloom*, *Film Grain*, *Vignette*, …), hair and dynamics. **No materials,
   no furniture, no bevel/rounded-box asset.** They load headless with `bpy.data.libraries.load(path,
   assets_only=True)` (verified), pinned by the Blender version.

## 2. Comparison

Effort = implementer task-days for the world scope of T-170 (W1–W7). Quality = expected match to the reference
videos; ✔ tested here, ○ not tested (network).

| Option | Visual quality vs videos | Headless / deterministic / pinned | Licence (repo redistribution · commercial · attribution) | Repo size | Effort vs T-170 | Cost |
|---|---|---|---|---|---|---|
| **A. Poly Haven textures + HDRIs** | ○ best available for worn and satin wood, plaster, rug, floor; indoor HDRI gives water/window reflections | yes: plain image files + Image Texture node (Box projection, no UVs); pin by file + SHA-256 | CC0 · yes · none | 1K JPG set (diff/rough/nor) ≈ 2–4 MB; 6 sets ≈ 15–25 MB (est.) | W1 −1 d, W5 −0.5 d | free |
| **B. ambientCG textures** | ○ same class as A, more stylisable surfaces (plastic, fabric, plaster) | same as A; has a public API | CC0 · yes · none | same as A | interchangeable with A | free |
| C. ShareTextures / cgbookcase | ○ as A, smaller catalogues | same as A | CC0 · yes · none | same | fallback only | free |
| **D. Blender built-ins (stock primitives, Bevel/Solidify/Screw modifiers, Cycles Bevel node, GN Essentials)** | ✔ shape language and rounding match (§1.1–1.2) | yes, versioned with Blender, fully scriptable | GPL program; output and node assets free to use | 0 | W2 −2…−3 d | free |
| E. Blender asset-library .blend for the world (author assets once, `libraries.load` them) | as authored | loads headless, but assets are binary .blend edited in the GUI: breaks "object = code + JSON", diffs unreadable | own | MB per file, grows per version | saves nothing vs D, adds GUI steps | free |
| F. Kenney / Quaternius furniture kits | low-poly, flat colour, wrong proportions; far layer at best | glTF import headless OK | CC0 · yes · none | small | W5 −0.5 d at most, restyle needed | free |
| G. Poly Haven models (furniture, props) | photoreal scans, wrong scale/style for child furniture; a few items usable in the far layer | glTF/blend, headless OK | CC0 · yes · none | 5–50 MB per model | little; child furniture is 5–15 boxes anyway | free |
| H. BlenderKit (free + paid) | good stylised material/model choice | needs add-on + account/API key at fetch time; versions not pinnable by us | royalty-free licence: use in renders yes, **raw redistribution in a repo no** | n/a | not compatible | free tier / subscription |
| I. Fab (Quixel Megascans) | photoreal, too realistic for this look | download via Fab account, no headless fetch | Fab standard licence: no raw redistribution; free tier no longer general | large | not compatible | paid |
| J. Paid procedural shader packs / GN kits (Superhive/Gumroad) | variable; mostly realism-oriented; GN furniture generators are GUI-parameter driven | node groups load headless, but parameters are made for the GUI; updates break pins | per-vendor EULA, typically **no redistribution** of the .blend in a repo | small | ≤ 0.5 d saved, adds vendor lock | paid (one-off) |
| K. Sketchfab models | variable | glTF import OK | per-model (CC-BY needs credits, many NC) — case by case | variable | not worth the audit for simple furniture | free/paid |

Plan simplifications evaluated:

| Simplification | Keep? | Saving |
|---|---|---|
| No `worldsys/primitives.py`; extend `prop_mesh` to a `parts` list using stock primitives + modifiers (D) | yes | 2–3 d |
| Hard-surface presets as one more JSON file in the existing `charsys/materials/builder.py` resolver (it already layers 5 preset files the same way) instead of `materials_hard.py` | yes | 0.5 d |
| Image textures (A/B) for wood ×2, floor, rug, plaster; plain Principled for plastic, paper, ceramic, wax, wire | yes | 1 d (no grain/scuff/pile tuning) |
| Furniture and room as data in the same `parts` format (no separate furniture kit, no imported models) | yes | 1.5–2 d |
| Hand-placed dressing lists with seeded jitter; no density-budget scatter system (GN *Scatter on Surface* only if a shot needs it) | yes | 1–1.5 d |
| Indoor CC0 HDRI for window light + water/glass reflections instead of a modelled exterior | yes | 0.5 d |
| Water as procedural ring bump (T-170 swatch) + HDRI reflections; no contact-event ripple system in v1 | yes | 1 d |
| Drop water entirely | owner's call | further 2–3 d |
| Wall art from AI/drawn images (T-170 Q5) | owner's call | — |

## 3. Recommendation

**Build the world from Blender built-ins + a small set of CC0 Poly Haven/ambientCG image textures, all driven by the
existing JSON + resolver code. Do not buy or adopt any add-on, paid pack or model kit.**

Concretely:
- Geometry: `plush.asset` v2 `parts` list (box, cylinder, open shell/cup, sheet; later screw/curve when needed),
  each with a T-170 rounding class → stock Bevel / Solidify / Weighted Normal modifiers. Cycles Bevel node for
  background dressing. Same format for furniture and room shells.
- Materials: one new preset file in the existing resolver. Image-backed presets (Box projection, scale in metres,
  per-object random offset) for worn wood, satin oak, floor, rug, plaster; Principled-only presets for the rest.
- Textures committed in the repo as 1K JPG (2K only for the hero table top), with a `SOURCES.json` (URL, licence
  CC0, SHA-256, date). One indoor CC0 HDRI (1K–2K) for window light and reflections.

Revised plan:

| Phase | Content | T-170 | Revised |
|---|---|---|---|
| W1 | presets file + 5–6 CC0 image sets + HDRI, swatches under shot lighting | 2–3 | 1.5–2 |
| W2 | `parts` builder on stock primitives/modifiers, v1 fallback, determinism test | 3–4 | 1 |
| W3 | restyle 13 props, verb tests unchanged | 2–3 | 1.5–2 |
| W4 | water: ring bump + HDRI reflections, one container variant | 3–4 | 2–3 |
| W5 | furniture + room as `parts` data, `plush.set` v2 | 4–5 | 2–2.5 |
| W6 | hand-placed dressing, light/DoF presets, fibre size rule | 3–4 | 2 |
| W7 | integration in `run_shot.py`, docs | 2 | 1–1.5 |
| **Total** | | **19–25** | **11–14** (≈ −45 %) |

A desk-only first slice (W1–W3 + table/chair + W7, no water, no room) is **6–8 task-days**.

Trade-offs:
- + Largest saving is code not written (custom primitives, procedural wood/rug tuning, scatter system).
- + Scanned wood should close the biggest visible gap (§1.3); CC0 means no attribution or redistribution risk.
- − ~20–30 MB of binary textures in git (repo `.git` is 537 MB today); they are immutable and hash-pinned, but each
  later resolution bump adds size. Git LFS is an option the owner may prefer.
- − Photo textures tile and are "real": they need scale rules, random offsets and slight desaturation/softening to
  sit in the stylised look; a wrong pick looks like a stock-photo table. Not verified here (network).
- − Water stays the highest-risk phase; reuse only removes ~1 day of it.
- − Image presets are fixed in look: per-object variation is limited to tint, roughness and wear masks.

## 4. Open points for the Supervisor

1. **Network:** allow `api.polyhaven.com`, `dl.polyhaven.org` (and/or `ambientcg.com`) for W1, or have the owner
   supply the files. A 0.5-day swatch check of 2–3 CC0 woods against the paperboat/watertable tables should run
   before W1 is approved; finding §1.3 is the reason for the recommendation and is not yet confirmed with a texture.
2. Repo storage for textures: plain git (recommended, ~20–30 MB) or Git LFS.
3. T-170 owner questions 1, 2, 5 and 6 still apply; question 2 (water container) decides whether W4 is 2 or 3 days.

## Reproduce

```
blender -b --factory-startup -P docs/evaluation/world/T-170/alternatives/scripts/kit_test.py -- --px 640 --spp 64
```
Not tested: no ctest or pipeline run (nothing outside this folder changed); no external textures (network).
