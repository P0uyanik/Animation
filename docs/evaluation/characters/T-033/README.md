# T-033: hair v2, felted styles (groom/1 felt finish)

Branch `t-033-claude-hair-v2`, from `t-021-claude-secondary-motion`; the T-021 dynamics still work.
Girl spec **0.8.0**, unpublished. Nothing was published or approved. **The final visual approval is the owner's.**

## What was built (shared, character-independent)
- **`pipeline/charsys/groom_felt.py`** (new): felted primitives for groom/1. Every size, groove and lump is spec data.
  - **`felt_volume`** is a new structure type with three shapes:
    - `gather`: a closed felt shell lying on the real scalp, from a hairline (a table over azimuth) towards a gather point (bun, crown or nape). It has a height profile, rounded soft edges, combing grooves (count, depth, sharpness, wander), low-frequency lumps and a part line.
    - `fringe`: a felted fringe sheet built with the yarn fringe's placement keys, with strand grooves and scalloped, rounded strand tips (`tip_scallop`). It is conformed to the head, so it never passes inside the forehead (`clearance`).
    - `mass`: an ellipsoidal felt mass with swirled grooves and lumps, placed on a bun frame or on the scalp. Used for temple volumes and puffs.
  - **`felt_lock`**: the felt finish of hanging locks. It keeps the same centre lines (straight, wavy, curly ringlets) and the same dynamics chain, but the cross-section is soft and slightly irregular: two slow harmonics plus a slow elliptical twist, and no ply lobes.
- **Finish selection per structure**: `hair.finish` takes `"yarn"` (the default, unchanged) or `"felt"`, and each structure can override it with `"finish"`. With felt:
  - a sweep becomes a gather volume;
  - a fringe becomes a fringe sheet;
  - a bun becomes a felt mass on each bun frame, so ties, flowers and the bun chain still attach;
  - locks become felt_locks.
- **Fibre surface**: `hair.fibres {slots, layers[{name, overrides}]}` attaches the shared GN fibre group (materials builder `add_fibres_geometry`, unchanged) to every object of those slots, one fibre object per layer.
  - The girl uses two layers: dense short felt fuzz, and sparse long flyaways on the silhouette.
  - Fibre objects are parented to their surface, so they ride with the skinned mesh. They are curves, so the engine exporter skips them.
  - The hookup is `groom.build(..., fibres=callback)`. The hair material binding in `build_character.py` passes a callback that deep-merges the layer overrides into the slot's material assignment.
- No character names in the code. The boy is untouched: he uses the legacy hair path, and Boy 2.0 can opt in through his spec.

## Girl 0.8.0 (hair section and its material binding only)
- **Kept:**
  - the scalp cap under-layer;
  - the bun frame (az 180, el 74, r 0.074, h 0.135), drawn as a felted mass at 1.25 / 1.2 / 1.2 of its radius and half height;
  - the band and the flowers.
- **New:**
  - `crown`: a 360° gather to the bun, with soft grooves and a part at az −22°;
  - `back_fall`: a short gather down the back of the head under the curls;
  - a `fringe` felt sheet: same roots and tips as before, tips 8 mm lower (to the glasses), scalloped strand ends;
  - `temple_l` / `temple_r` masses.
- **Ringlets:** `temple_puffs`, `side_curls`, `back_curls` and `nape_curls` are felted, with thinner tubes and an open helix. Counts are 3, 6, 12 and 8.
  - Their names are unchanged, so the T-021 dynamics override still applies: 39 chains, exported in the package `dynamics` block.
- **Material:** `hair` → preset `felt hair`, colour = `references/color_targets.json` hair (86, 54, 44).
  - Fibre layers use saturation compensation 1.0, so the fuzz is not orange.
  - Felt layer: 5 fibres/cm², 2.8 mm. Flyaways: 0.06 fibres/cm², 9 mm.
- Build time 46 s (was 40 s).

## Evidence
- `turnaround_vs_reference.png`: front, 3/4, side and back views next to the sheet30 references.
  - 640 px, shared calibration `character_neutral/1` (Standard view, exposure 0), Cycles 32 samples + OIDN.
  - About 4–5 s per view: `render_timings.json`.
- `hair_closeup_vs_reference.png`: orthographic 0.42 m close-ups (front and back of the head) next to crops of #30 (the proportion-sheet head and the hair-construction back view).
- `colour_checks.json`: `measure_colour.py` on the final renders.
- `groom_generic_test.json`: the extended synthetic test.
- `fidelity_hair_summary.json`: the T-032 fidelity tool, before vs after.
- Iteration renders used: 5 (the 5th is the final).

## What matches
- **Felted look, not plied yarn:** smooth felted masses with soft combing grooves on the crown and bun, and a fine fuzzy halo.
  - No ply ridges on the locks. In the synthetic test, the along-length radius variation is 12 % of the yarn rope's.
- **Fringe:** a soft felted sheet covering the forehead down to the glasses, side-swept from a part on her right, with rounded strand tips. Close to the #30 front.
- **Colour:** clearly better.
  - Fidelity tool, hair: dE00 **10.5 → 2.9**, luma-matched 8.9 → 2.6.
  - measure_colour: back dE00 2.1, front 4.8 (render slightly darker than the reference patch).
- **Bun:** size and placement are close in the front and 3/4 views. Band and flowers are kept.
- **Dynamics:** chain bones, skinning and export are unchanged in behaviour (groom_dynamics_test PASS, girl export with 39 chains).

## What does not match (open, for the owner's review)
1. **Hair silhouette is too small, and worse than before.**
   - Fidelity tool: hair area relative to reference **−23 % → −36 %**, hair IoU **0.64 → 0.54**. The score is 63.0 → 62.5, mostly from this.
   - The thinner ringlet tubes cover less. The reference has a much fuller cascade: wide at the shoulders, curls reaching mid-back, volume beside the cheeks.
   - Next step: wider hang radii, more and fuller locks, larger helix radius, longer z_end on the back curls.
2. **Back:** the reference shows long wavy felted locks starting just under the bun gather. Ours shows straight felted strands on the back of the head, then tight horizontal coils. It reads as more regular, more "corkscrew", than the reference's loose waves.
3. **Fuzz texture:** our fuzz reads a little like terry cloth or towelling. The reference felt has longer combed fibres lying along the strands (lengthwise sheen).
   - This needs a lean/direction input in the fibre group, which belongs to the materials owner, or a groom-side tangent attribute.
4. **Bun:** the reference bun is two or three lobed bundles, bigger and higher. Ours is one lumpy felt ball.
5. **Fringe:** the reference fringe is fuller and more curtain-like, partly falling on both sides of the part. Ours sweeps one way.
6. **Hue:** still a little redder and darker than the reference at the front.
7. Not hair, unchanged: skin and face colour (darker), arm length, eye size. These are the fidelity tool's other top differences.

## Checks
| Check | Result |
|---|---|
| `groom_generic_test.py` (extended: 10 felt checks on the synthetic head) | PASS 19/19 |
| `groom_dynamics_test.py` (T-021) | PASS |
| `verify_charsys.py` (boy) | PASS, 68 PASS / 0 FAIL, boy master byte-identical |
| `test_export_engine.py` | ALL PASS 8/8 |
| `test_material_presets.py` | ALL PASS 54/54 (see note) |
| `ctest` (OIDN 2.3.3 prebuilt, embree 4.3.0) | 4/4 passed |
| girl 0.8.0 + dynamics override → `export_engine.py` | 39 chains, 4 colliders in the package |

- **Note on `test_material_presets.py`:** its check "girl hair preset (T-016)" pinned the girl's hair to `wool yarn`. T-033 moves her to `felt hair` by design, so the expected value now says `felt hair` (same strictness). No threshold was changed anywhere.
- The fidelity tool was run read-only from a scratch worktree with `tools/fidelity` and the annotations from `origin/t-032-claude-fidelity`. Nothing from that branch was committed here.

## Reproduce
```
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir> --no-compare --no-glb
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --ids --closeup "head_front:0:5:0,-0.02,0.9:0.42" --closeup "head_back:180:10:0,0.05,0.82:0.42"
python3 pipeline/charsys/tools/turnaround_sheet.py assets/characters/girl_auburn_bun_glasses/references/views <renders> turnaround_vs_reference.png --views sheet30_front:front,sheet30_front_left:3/4,sheet30_left:side,sheet30_back:back --tag T-033
python3 pipeline/charsys/tools/measure_colour.py assets/characters/girl_auburn_bun_glasses/references/colour_checks.json <renders> colour.json
blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>
```
- Blender 5.3 here is `bpy==5.3.*` in a Python 3.13 venv, behind a `blender` wrapper script.
- The close-up sheet crops are `ref_30.webp` (70, 600, 330, 860) and (965, 615, 1155, 805).
