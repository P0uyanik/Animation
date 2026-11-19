# T-126c: dress, tights, boots and a skirt cloth-simulation prototype (candidate input)

Third character `girl_white_hair_blue_dress`. Nothing is published or made current. Input `integration/t-131@3307d82`,
branch `t-126c-claude-dress`. Body: T-126a's base spec `girl_white_hair_blue_dress.0.1.0.spec.json` at
`t-126a-claude-body-face@05c5602` (read from that branch, not copied here; sha256 `4edb998ad508…`); the
T-070 draft `third.base.spec.json` was used until it arrived and is what the build test uses.

## Result against the references (fidelity first)

Sheets: [strict sheet](sheets/dress_strict.jpg) (01 primary, 09 panel 01, 16 W05) ·
[crops: collar, cuffs, hem, boots](sheets/dress_crops.jpg) · [skirt simulation](sheets/skirt_sim.jpg).
16 spp + OIDN, calibrated light; the first check was a 4 spp preview of a plain dress on the draft body.

| part | state | what the sheet shows |
|---|---|---|
| Silhouette: bodice, long full sleeves, raised waist seam, flared skirt to mid-thigh, tights, cuffed boots | **reads as 01 and 09** | waist seam set at 0.467 m and hem at 0.264 m: 01's fractions from `measurements.json` on an assumed 1.00 m sole-to-bun-top height (not measured on the built figure) |
| Peter Pan collar (T-119 `collar_seat`, nothing over it) | **present, too small and flat** | two rounded lobes meeting at the front; in 01 and 16 it is wider and thicker. A wider collar (42 mm) wings out at the shoulders with the current seat, so 36 mm is kept |
| Rib cuffs (T-119 `rib_cuff`, 18 wales) | **present, wales faint** | a close band with a rolled seam ring above it; the wales do not read at figure scale |
| Cable/leaf skirt relief (`skirt_pattern`, new) | **present, weaker than 16** | 12 panels of rope cable and leaf column stand up to 5 mm proud and survive the build; the cables read, the leaves read weakly, and the pattern is less dense and less ordered than 16 |
| Rib hem | **not right** | the `hem_rib` band reads as a second edge under the skirt, not as a rib strip continuous with it; 01's scalloped hem is not reproduced |
| Stockinette (stitches on bodice and sleeves) | **not achieved** | `fibre_uv` gives the pieces a knit direction, but no stitch columns are visible: the `knit` shader draws its rows from a third coordinate a UV map lacks, and its column bump is too fine. Shader work, T-126d / `materials/builder.py` |
| Colour, fuzz | **approximate** | existing `cotton knit` preset with overrides (short halo, nap flecks reduced); the dress is greyer than 01. Her preset file is T-126d's part |
| Tights (`tights` item, new) | **reads as 01** | one skin-following shell, waist to toes; cream, no skin shows at the boot top |
| Boots | **shape approximate** | tan fleece with a turned-down cuff; squatter than 01/16, the sole shows as a plate wider than the upper, the cuff pile is not visibly longer than the shaft's, and the new sole stitches are hidden by the pile |
| Sleeve/bodice junction | **defect** | a dark slit at the armhole when the arms are lowered (3/4 and W05 tiles). `armhole: "cut"` is worse (open gaps showing skin); not solved here |

## What was added (generic, opt-in; `pipeline/charsys/garments_v3/README.md`)
- item type `tights`; fields `skirt_pattern`, `fibre_uv`, `sole_stitch`, `cloth_sim` (a tag only). No character data in
  the code; a `garment/3` block without the new fields builds as before.
- `pipeline/charsys/cloth_sim/`: baked skirt simulation, run per shot on a built master (its README has method,
  settings and limits).
- Her clothes are only in [the override](girl_white_hair_blue_dress.dress.override.json), written by
  [make_override.py](make_override.py) (sizes are my estimates read off 01, 09, 16 and `measurements.json`).

## Skirt cloth simulation (prototype)
Blender cloth on a 3,600-vertex proxy, baked to a PC2 cache, replayed without a solver; the 76,800-vertex skirt and
its hem band follow the proxy. Seed 126. Records: [walk](sim/walk.json), [sit](sim/sit.json), [kneel](sim/kneel.json).

| evidence frame | simulated: vertices inside the body skin / max depth | skinned (the build): inside / max depth | hem rise, simulated |
|---|---|---|---|
| walk, stride L | 128 of 76,800, all in the waist third / 5.2 mm | 0 | 16.8 mm |
| walk, passing | 0 | 0 | 6.3 mm |
| walk, stride R | 110, waist third / 4.8 mm | 0 | 10.2 mm |
| sit, half way | 0 | 0 | -0.6 mm |
| sit | 0 | 775, all in the hem third / 16.6 mm | 0.2 mm |
| kneel | 0 | 0 | -0.6 mm |

- Sit is where the simulation helps: the skinned skirt lets the thighs through its front hem, the simulated one does not.
- In the walk the simulation is slightly worse at the waist (the cloth just under the pinned seam is pressed by the
  moving hip) and the hem rides up 6 to 17 mm without settling between strides. The skinned skirt is rigid with the
  waist and the short legs do not reach it.
- Kneel does not load the skirt on this body (hem above the knee): both are clean.
- Bake time 27 to 34 s per motion (54 to 60 frames, 4 CPU cores).
- Deterministic: two runs of `walk` with seed 126 give the same cache (sha256 `4fe493fd…`); seed 7 gives another.
- Not covered: arms. Lowered arms press into the skirt sides and dragged the hem up by 6 to 10 cm in an earlier run,
  so the test motions keep the A-pose. Sleeves, hands, hair, boots and floor are not colliders. The motions are FK
  probes, not animation; the seat is a collision box and is not rendered.

## Tests and guards
`python3 pipeline/charsys/tests/test_garments_r3.py --blender blender`: see [tests.txt](tests.txt). The T-119 checks
are unchanged; 27 checks were added for T-126 (70 before, 97 now) (override, validation, build). The guard that `garments/`,
`garments_v2/`, their tests and the older preset files are unchanged passes, and the boy's and girl's default builds
match their published masters in every garment piece, hand and material name. Not run: `garment_generic_test.py`,
the full `test_garments_v2.py`, `tools/check_all.py`, CI.

## Reproduce
```
python3 docs/evaluation/characters/T-126/dress/make_override.py
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec <her base spec> --out <dir> --no-glb \
    --no-compare --override docs/evaluation/characters/T-126/dress/girl_white_hair_blue_dress.dress.override.json
blender -b --factory-startup -P docs/evaluation/characters/T-126/dress/shots.py -- <out> preview|sheet|crops <master>
blender -b --factory-startup -P pipeline/charsys/cloth_sim/run.py -- <master> walk|sit|kneel <bakes>
blender -b --factory-startup -P docs/evaluation/characters/T-126/dress/sim_evidence.py -- <master> <bakes> <out>
python3 docs/evaluation/characters/T-126/dress/compose.py strict|crops|sim <dir> <sheet.jpg>
```

Environment setup: none needed (Blender 5.3.0 `bpy` wrapper and Pillow were present).

ledger: build 14 · render 62 · sim 12 · tests 30 · ci 0 · wait 0 (min)
