# T-091: hair round 4 (`groom/3`): few large, overlapping felt masses

Date: 2026-11-18. Blender: bpy module 5.3.0 (Linux, CPU) through `tools/bpy_blender.py`; Workbench (Mesa llvmpipe)
for geometry previews, Cycles for the recipe previews and the strict sheets.
Status: **candidate for owner review (path B).** Nothing is published, approved or promoted; no character spec,
published version, frozen file or existing groom module changed. `groom/3` is opt-in: only the T-091 candidate
overrides pin it. Supervisor: `groom/3` is registered `declared=False`; `groom_r4.GENERATOR_VERSIONS = ("groom/3",)`,
so it can be flipped to `declared=True` at merge.

## What groom/3 adds (`pipeline/charsys/groom_r4.py`)
groom/2 (`groom_hybrid.py`) is used read-only as a library; every groom/2 structure type builds through groom/3 with
vertex-identical output (tested). New, all spec data, no character names:

- **`masses`**: few large felt masses with a round, deep section (depth = thickness/width, 0.4–0.65 in the
  candidates; groom/2 clumps were flat, ~0.45 at 30–40 % of the width), a root sunk into the base, a held full width
  over `hold` of the length, then a pointed taper; `layer` stacks later masses over earlier ones so they overlap like
  petals and meet in deep channels. Explicit `items` (root/tip on the head) and/or `rows` (count, azimuth spread,
  flow from a whorl pole). Lift as an arch `[root, peak, tip]` or a rising curve `[root, tip]` + `lift_power`
  (standing crown petals); `sweep` bows a mass sideways (swept fringe sections). The section frame follows the actual
  path (width across the path along the scalp, depth along the normal), so steep petals do not twist and clamped
  masses do not turn their width into the face.
- **Face keep-out**: a mass that reaches the keep-out window **ends there** (shortened, re-tapered) instead of being
  dragged along the brow line; the build reports `keepout_clamped` and the vertex check (`violations`) as groom/2.
- **`scrunchie`**: a gathered fabric band round a bun (gathers, gather depth, ruffle; slot `hair_band`), following
  the bun's chain like a tie.
- **Directional-fibre experiment** (one flag, default off): `hair.fibres.directional {"enabled", "strength"}`. Each
  mass stores its centre-line direction as the `ps_comb` point attribute; a small GN modifier after the shared
  fibre group bends each fibre along it. Only masses are combed.
- Dynamics: one spring chain per mass (as groom/2 clumps); structure names kept, so the specs' chain settings apply.

## Candidates (`assets/characters/<id>/spec/candidates/T-091/`, written by `tools/make_candidates.py`)
On the current approved specs (boy 2.0.0, girl 0.11.0); the hair structures are replaced as a whole, fibres,
materials and dynamics are kept. `*.hair_r4_dirfibres.override.json` = the same candidate with the experiment on.

**Boy** (B04/B05 + val27/hero24): 62 groom/2 clumps → **33 masses** (mean row width 0.086 m vs 0.066 m), depth
0.5–0.62. Long petals from the top whorl over crown, sides and back (9), a nape row (6), side masses over the ears
with outward-flicking tips (4), fringe masses hanging to the brow line (4 + 1 centre), and **crown petals that rise
from the crown and stand up at the top of the silhouette** (6 + 3 at the whorl), with channels between them. Felt
base slightly lower (0.016–0.03 m).

**Girl** (G01/G02/G04–G06 + ref_30, owner design points 2026-11-18):
- **centre parting** (crown part az 0, was −18) with **two swept fringe sections per side** (mirrored masses from
  the parting down to the temples), replacing the felt fringe, the part fringe and the 7 sweep strands;
- **soft back transition**: 10 broad back sections from the crown run down over the ringlet roots (staggered lengths)
  so the curls grow out of the sections, no horizontal band/ridge (G05 used only for bun, scrunchie and ringlets);
- **narrower silhouette**: curtain rest radii 0.17/0.145 → 0.15/0.13, ringlet hang radii 0.20/0.18 → 0.17/0.155,
  rest radii −30/−20 mm, flare 0.05 → 0.02;
- **ringlet taper**: end scale 0.55 and a smaller, tighter coil over the last 30 % (tip radius × 0.8, pitch × 0.75);
- **gathered scrunchie** (11 gathers) replaces the tube band; the pink felt flowers stay.

## Evidence
- Cheap first frames (Cycles 2 spp, recipe preview, STATUS): `boy_preview/`, `girl_preview/`.
- **Strict sheets** (T-087 recipe, Cycles, reference | current approved | candidate | AI target): `boy_sheet/`,
  `girl_sheet/` (`*_strict.jpg`, `recipe.resolved.json`, `sheet.json`, `log.txt`).
- Head-turn check (head control ±35°, Workbench, geometry only): `media/head_turn.jpg`.
- Directional fibres on/off (Cycles 16 spp crops): `media/directional_fibres_off_on.jpg`.

## Directional-fibre experiment (measured)
Boy candidate, two Cycles crops (16 spp, 360 px, 3/4 + back), same machine, run one after the other:
off 85 s, **on 87 s (+2 %)**; fibre points identical (6,985,266; the modifier only moves them). Build cost: one GN
modifier per mass fibre layer. Look: fibres lie along each mass (slightly streakier felt, the lock direction reads a
little better at close range); at sheet distance the difference is small. Left **off** in the main candidates;
recommendation: keep it as an opt-in for close-ups.

## Checks
| check | result |
|---|---|
| `python3 pipeline/charsys/tests/test_hair_r4.py` (new, plain) | 37/37 PASS |
| `blender … -P pipeline/charsys/tests/test_hair_r4_build.py` (new, Blender, synthetic head) | 13/13 PASS |
| `test_hair_v3.py`, `test_hair_v3_r2.py`, `test_hair_v3_r3.py` (plain) | 30/30, 20/20, 25/25 PASS |
| `test_hair_v3_r3_weights.py`, `groom_generic_test.py`, `groom_dynamics_test.py` (Blender) | PASS |
| face keep-out on the candidates (build report) | boy 0, girl 0 violations |
| `export_engine.py` on both candidate masters (humanoid_rigify) | boy 122 bones / 78 meshes, girl 184 / 76: OK |
| groom/1, groom/2, versions.py, build_character.py, published versions, frozen files | unchanged (`git diff a682abb`) |

The new Blender test found one real defect during development (a mass aimed into the face kept its width inside the
keep-out after clamping: 138 vertices); fixed by the end-at-keep-out rule and the path-following frame.

## Limitations / open points
- Fidelity score (`tools/fidelity`) not run in this task; the sheets are the deliverable.
- Boy: the nape row is still slightly shorter than val27 back; the whorl centre shows one small knot at the top.
- Girl: swept sections are smooth felt (G04 shows coarser fibre texture), fringe colour/texture via the existing
  hair preset only; the scrunchie colour is the existing `hair_band` slot.
- Head-turn check is geometric (Workbench); dynamics in motion were not simulated here.
