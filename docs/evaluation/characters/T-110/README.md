# T-110: felt surface, one shared fibre halo for every felt surface (round 3)

Branch `t-110-claude-felt-surface`, input `f550cbd` (`integration/round3`), merged `integration/t-094b` (`ea02ce1`,
claim widened by the Supervisor). Blender: the **bpy 5.3.0 module** (Python 3.13) behind `tools/bpy_blender.py` (no
Blender binary in the cloud container). Base versions: **boy 2.1.0 and girl 0.12.0** (T-094, about to become current).

**Status: candidate evidence only. Nothing is published or approved.** The owner decides on the strict sheets.

## Owner evidence
| | boy 2.1.0 → T-110 | girl 0.12.0 → T-110 |
|---|---|---|
| T-087 strict sheet (Cycles 16 spp, 360 px; reference \| 2.1.0/0.12.0 \| T-110 \| AI target) | [boy_sheet/…_strict.jpg](boy_sheet/boy_2.1.0_vs_T-110_strict.jpg) | [girl_sheet/…_strict.jpg](girl_sheet/girl_0.12.0_vs_T-110_strict.jpg) |
| cheap preview (Cycles 2 spp, 120 px; not for approval) | [boy_sheet/…_preview.jpg](boy_sheet/boy_2.1.0_vs_T-110_preview.jpg) | [girl_sheet/…_preview.jpg](girl_sheet/girl_0.12.0_vs_T-110_preview.jpg) |
| recipe | [boy_2.1.0_vs_T-110.recipe.json](boy_2.1.0_vs_T-110.recipe.json) | [girl_0.12.0_vs_T-110.recipe.json](girl_0.12.0_vs_T-110.recipe.json) |
| material patches (macro + shot size, before/after, neutral + warm rig, Cycles 16 spp) | [patches/patch_sheet.jpg](patches/patch_sheet.jpg), metrics [patch_metrics.json](patches/patch_metrics.json) | same sheet |

The candidate column is built by the recipe tool from the base spec plus
`assets/characters/<id>/spec/candidates/T-110/<id>.felt_surface.override.json` at `e542661`. That build includes the
halo call, so the skin halo is part of the normal build. The patch sheet's footer says "T-092 material patches"
because the T-092 composer (`compose_patches_r2.py`, used unchanged) has that caption. The plan
([patches.plan.json](patches.plan.json)) is T-110's.

## What was built
- **One shared halo:** the Geometry Nodes group `PS Felt Halo/1` (`pipeline/charsys/materials/felt_halo.py`).
  - It grows short, tapered, randomly tilted curve fibres over a surface, optionally only on one material's faces.
  - Each fibre stores its root normal and a tone.
  - The halo shader is a Principled Hair strand. Its opacity is `opacity × (floor + (1 − floor)·(1 − |N·I|)^power) × tip fade`, so the halo shows at silhouettes and is only a faint felt fuzz face-on. It needs no camera input, so it is stable under animation.
- **Opt-in through `presets/4`:**
  - `presets_felt.json` (`plush-studio.material-presets/4`, registered in `versions.py` as `materials presets/4`, `declared=False` until merge).
  - Each `/4` id `extends` a presets/1..3 id and adds an optional `patch` and a `halo` section.
  - Halo fields: density per cm², length (mm), spread, opacity, facing floor, silhouette power, tip transparency, colour value and saturation factors on the base colour, radius fraction, wide-LOD factor.
  - Ids: `felt skin/4`, `hoodie fleece/4`, `trouser pile/4`, `felt/4`, `felt hair/4`, `vest felt/4`, `brushed cotton/4`, `cuff fleece/4`, `boot fleece/4`.
  - The skin id is `felt skin/4`, not `skin-felt/4`: the existing T-092 test uses `skin-felt/4` as its example of an unknown id, and tests are not loosened.
- **Where the halo is attached:**
  - Hair and garments: the existing surface-fibre path (`builder.add_fibres_geometry`). The halo is a second modifier and material on the same fibre object, added once per surface even when the groom adds several fibre layers.
  - Skin: never routed through that path, so `build_character.main_generic` calls `felt_halo.add_missing_halos` once after `organise()` (Supervisor-approved).
  - The skin pass skips garment pieces, which keep or deliberately skip their own halo.
  - `garments/generator._library_preset` now uses `is_known_preset` (Supervisor-approved), so garments accept `/4` ids.
- **Less plastic skin (`felt skin/4`, extends `skin-felt/3`):**
  - roughness 0.76 → 0.88, specular 0.22 → 0.10
  - subsurface weight 0.5 → 0.3 and scale 0.05 → 0.032 (less waxy glow on thin hands and ears)
  - broader dye-tinted sheen (0.4 → 0.55, tint 0.65)
  - stronger felt micro-relief and flock
  - a 0.9 mm skin halo; every fabric halo is longer
  - crease, warmth and the non-emissive rule are kept.
- **Candidates:** `make_candidates.py` swaps every felt-surface preset id of 2.1.0 / 0.12.0 to its `/4` id (17 boy, 13 girl) and pins `generators.materials = presets/4`. Colours, reference sizes, overrides and every non-material key are unchanged.

## Visual review against the original references
- **Skin (both):** more matte. The broad sheen on forehead, cheeks and hands that read as plastic is gone; the
  references (01 closeups, hero24, ref_30) show a matte flocked felt. Colour is unchanged: boy forehead median
  230/181/153 → 233/180/152 (face-front render). ΔE00 to the skin target is slightly lower (boy 9.0 → 8.7, girl
  7.3 → 7.19, neutral rig). Skin fuzz stays below the 3/255 skin target (shot 0.42 → 0.47). At sheet size the skin
  halo is a subtle edge softening of cheeks, ears and hands.
- **Garments:** at shot size the hoodie fleece reads more even and less mottled (shot fuzz 3.55 → 1.75), nearer the
  B08 / 01 "uniform bright fibre halo"; the silhouettes of hoodie, joggers, vest and boots are softer. Hoodie ΔE00
  3.51 → 3.95 (the lighter halo lifts the median a little). Trousers 3.88 → 3.30.
- **Hair edges:** a lighter, wispy halo on the boy's charcoal hair and the girl's curls (girl hair ΔE00 5.58 → 4.23).
- **Unchanged:** proportions, face, hair shapes, garment shapes and colours. No identity change.
- **Limitation:** at the strict-sheet scale (360 px) the halo is mostly sub-pixel. It shows as softer silhouettes,
  not as visible fibres. The macro patches show the fibres themselves. The reference hoodie's backlit glow (01) needs
  a backlight; the review rig character_neutral/1 has only a moderate rim light.

## Render-time cost (Cycles, same settings, same run)
| | base | T-110 | change |
|---|---|---|---|
| boy strict sheet, 6 views at 16 spp / 360 px (`render_result.json` column seconds) | 351.2 s | 434.6 s | +24 % |
| girl strict sheet, 6 views | 461.4 s | 558.5 s | +21 % |
| patches, 32 macro tiles at 16 spp (`patches_render.json`) | 82.2 s | 97.0 s | +18 % |
| patches, 32 shot tiles | 5.8 s | 6.7 s | +17 % |

The first sheet run (blends built before the skin preset was renamed, same settings) measured +26 % and +20 %.

## Default output byte-identical
- `pipeline/charsys/materials/felt_frozen_graphs.json`: node-graph digests of all 18 presets/1..3 ids, written from
  the input SHA's builder. `test_felt_surface_graphs.py` rebuilds them and compares node for node: unchanged.
- The build's halo call on a scene built only from presets/1..3 ids adds nothing and changes no datablock (test 1b).
- Real default build ([default_build_noop.json](default_build_noop.json)): girl 0.12.0 rebuilt with the T-110 code,
  compared with a clean control build at `ea02ce1` (same command, deterministic environment).
  - `components.json`, `animation_compat.json` and `spec.resolved.json` are identical.
  - `build_report.json` differs only in three timing fields.
  - The `.blend` content is the same (objects, materials, node graphs, properties, vertex sets), and there are no halo objects.
  - The `.blend` bytes differ by the vertex order of the ear and lid meshes. The clean control build differs from the
    published 0.12.0 master in the same way, so this is **pre-existing build non-determinism, not T-110**. Reported
    for the Supervisor.

## Tests
| command | result |
|---|---|
| `python3 pipeline/charsys/tests/test_felt_surface.py` | 116/116 PASS |
| `blender -b --factory-startup -P pipeline/charsys/tests/test_felt_surface_graphs.py` | 88/88 PASS |
| `python3 pipeline/charsys/tests/test_materials_r2.py` | 104/104 PASS |
| `blender … test_materials_r2_graphs.py` | 52/52 PASS |
| `python3 … test_material_presets.py` / `test_skin_presets.py` / `test_versions.py` | 54/54, 24/24, 96/96 PASS |
| `blender … test_skin_material.py` | 10/10 PASS |

Not run: ctest and the engine image regressions (no engine or renderer change), `verify_charsys.py` and export
tests (the exporter is untouched; the default build checks above cover the build path), and the fidelity score (not
required by the task).
