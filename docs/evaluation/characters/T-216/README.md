# T-216 | Auburn P3: face_generic/4 knobs (Warp / Hook / Lattice), chain gap fix, knob fit

Character `girl_auburn_bun_glasses` 0.14.0. Phase P3 of the face plan (owner GO 2026-11-23 ~06:55 CET). The output is a
spec override plus a new, opt-in generator version: [candidate.override.json](candidate.override.json) (T-215's P2
proposal + `generators.face = face_generic/4` + `face.knobs`). No asset, character version or CURRENT pointer changed.
`face_generic/3` and every released character build exactly as before (their pins never reach the new code). Release
is a later step and needs the owner's sheet approval.

## Result

| View / group (within / scored, mean abs z) | 0.14.0 | P2 (T-215) | **P3 candidate** | P3-chin* (not acceptable) |
|---|---|---|---|---|
| front face | 13 / 27 (1.23) | 23 / 27 (0.83) | **23 / 27 (0.84)** | 20 / 27 (0.92) |
| side face | 1 / 7 (2.89) | 2 / 7 (2.44) | **3 / 7 (2.20)** | 5 / 7 (2.14) |
| 3/4 face, held out | 9 / 24 (1.68) | 13 / 24 (1.48) | **13 / 24 (1.48)** | 8 / 24 (1.87) |
| front hair (not fitted) | 3 / 7 (1.15) | 5 / 7 (1.11) | 5 / 7 (1.11) | 5 / 7 (1.00) |
| side hair (not fitted) | 0 / 2 (6.25) | 0 / 2 (6.14) | 0 / 2 (6.14) | 0 / 2 (6.35) |
| fit objective (T-215 cost, fitted views, lower is better) | – | 0.556 | **0.475** | 0.386 |
| face_parity `--strict` (sweep) | 9 failing, 8.77 mm | 9 failing, 7.80 mm | **PASS, 56/56, 0.000119 mm** | **FAIL**, 12 failing, 16.6 mm (blouse collar) |

The T-215 stuck list, z per stage (start → P2 → P3 → P3-chin*), full rows in [scores.csv](scores.csv):

| Measure | 0.14.0 | P2 | P3 | P3-chin* |
|---|---|---|---|---|
| side `cheek_advance` | +2.23 | +2.25 | **+0.12 (within)** | +0.61 (within) |
| front `eye_to_chin` / `eye_y` | ∓2.63 | ∓2.41 | ∓2.41 | **∓0.78 (within)** |
| side `eye_to_chin` / `eye_y` | ∓2.67 | ∓1.97 | ∓1.97 | **∓0.96 (within)** |
| front `cheek_width` | −1.87 | −2.12 | −2.12 | −2.24 |
| front `jaw_width` | −1.37 | −1.83 | −1.83 | −3.28 |
| front `chin_width` (within at P2) | +0.11 | −0.71 | −0.71 | −2.58 (out) |
| side `eye_width`, `opening_h_w` (out of P3 scope) | −2.30, +7.26 | −1.75, +8.32 | −1.75, +8.32 | −2.01, +9.37 |

**The P3 candidate** is one knob: a Warp on the profile at eye level (the nose bridge, 30 mm smooth falloff) moved
3 mm forward. It brings side `cheek_advance` into the band, and nothing that was within at P2 leaves it. It is
neutral on the front and on the held-out 3/4 view, because the knob moves no skin outside its 30 mm radius. D3 (every
scored measure within) is still not met.

**Why not the chin (P3-chin\*).** The knob fit found the chin lever the stuck list asked for. A chin Warp (15.8 mm down)
plus a lower-face Lattice (5×3×5, its mid-plane on the face front; chin row 13.3 mm down, jaw points 8 mm out)
bring front and side `eye_to_chin` into the band and give the best fit objective (0.386, trial 6 of 30,
[search.json](search.json)). Three things rule it out as the candidate:
1. **Garment clearance.** The chin ends about 29 mm lower, below the blouse collar's front top (z 0.659 m). The collar
   and vest carry live Shrinkwrap modifiers onto the body collider, which shares the skin's face keys. With the chin
   over the collar, 1 to 3 collar vertices flip their nearest surface between chin and neck under small face-key
   motion in Blender, while the engine keeps them static. `face_parity --strict` fails on 12 sweep expressions (and
   on smile+blink in the core set), max 16.6 mm. It also fails with the neck held still (`floor_m`, below), so the
   chin position itself is the cause. Variants: a 6 mm smaller lattice chin drop still fails 3; the chin Warp alone
   (15.8 mm, variant B) passes, but then the front lower-face widths drop to 19 / 27 and side `cheek_advance` returns
   (+2.37), so it is worse than P2 on the fitted cost (0.594).
2. **The held-out 3/4 view gets worse** (13 → 8 within). The longer face narrows the measured lower outline: front
   `jaw_width` −1.83 → −3.28, `chin_width` leaves the band. The fitted cost improves only through the side view.
3. **The measured front outline below the mouth is the jaw's occluding edge** over the side of the head (about
   ±0.10 m at y ≈ −0.10 m), not the head silhouette (±0.128 m). Widening it needs large moves: the lattice x-points
   gave about 0.1 z per 6 mm. The reference's broad lower face is a head-outline change (`body.params.head`, groom
   frame) rather than a regional knob.

So the chin and lower-face widths need an owner decision: (a) lower the blouse collar / vest neckline (garment
change, then re-run this fit with the chin bounds opened), or (b) a head-outline round, or (c) accept P3 as is.
The P3-chin\* row is on the sheets for that decision only.

## Sheets (owner review)

- [sheet.jpg](sheet.jpg): 8 yaws, rows reference / release 0.14.0 / P2 / P3 / P3-chin\*. Cycles 16 spp + OIDN,
  `character_neutral/1`, 70 mm, neutral face (T-202 `face_views.py` settings; T-215 layout). +45 and +135 use
  mirrored references, labelled.
- [sheet_face.jpg](sheet_face.jpg): face close-up at −90, −45, 0, +45, +90 (frame 0.34 m), same rows.
- [expressions.jpg](expressions.jpg): front close-up, rows P2 / P3 / P3-chin\*, columns neutral / Smile / Blink 0.5 /
  Blink / Smile+Blink / SmileOpen (face controls set on the rig; Blender evaluation).

## face_generic/4 (what was built)

[`face_generic_v4.py`](../../../../pipeline/charsys/face_generic_v4.py) = face_generic/3's build (copied; v3 unchanged)
plus two parts. It is registered in [`versions.py`](../../../../pipeline/charsys/versions.py) as `face_generic/4`.

1. **`face.knobs`** ([`face_v4/knobs.py`](../../../../pipeline/charsys/face_v4/knobs.py)). A list of built-in Blender deform
   modifiers: `WARP` and `HOOK` (radius falloff, move and scale of the target about the anchor) and `LATTICE` (a box
   of n×m×k points with linear interpolation; border points stay fixed; offsets per point index, mirrored).
   - Anchors: `chin`, `mouth`, `eye`, `{"front": t}`, `{"cheek": t}`, `{"profile": t}`. `t` runs from the eye line (0)
     to the spec chin (1). `front` is the occluding front-view outline of the row (walk outward until the surface
     behind jumps by more than `jump_m`), which is what the T-214 measurer sees. `cheek` is the most forward skin
     point of the row on one side.
   - `mirror` makes a per-side knob on both sides, or makes a midline lattice symmetric. `floor_m` (any type) keeps
     skin below the anchor minus `floor_m` still, with a smooth fade.
   - Applied right after the head shape options, on the **neutral skin, before** the eyes, lids, socket, brows, ears,
     mouth, glasses, groom, rig and masks are built. Each knob is applied with `modifier_apply_as_shapekey` and folded
     into Basis: every key block moves by its delta, so existing keys stay relative and unchanged, and keys are baked
     from Basis alone (other key values are zeroed during the bake).
   - Every helper (modifier, empty, lattice, vertex group) is removed, so the master is knob-free.
   - The build report lists every knob instance: anchor, moved vertices, max mm, the maximum motion **outside its
     falloff radius / lattice box** (0.000 mm on every auburn build) and below its floor, and the body motion more
     than 4 cm below the chin.
   - Because the lids, lid keys, socket and blink are generated after the knobs, the **lid keys are rebuilt on the
     fitted rest face**. The **glasses** (accessories/1) are built after the face on the fitted skin and stay rigid:
     `ARMATURE` only, no Surface Deform; skin clearance 1.525 mm and eye clearance 7.84 mm, unchanged from P2
     ([glasses_check.py](glasses_check.py)).
2. **In-between chain gap** ([`face_v4/chains.py`](../../../../pipeline/charsys/face_v4/chains.py); T-213 finding, option b).
   A mesh that carries a chained base key but none of its stop keys gets linear stop keys
   (`<X>@NN = Basis + NN/100 × (<X> − Basis)`), once per Key datablock. `face_generic.add_inbetween_drivers` then
   gives them the hat drivers. Blender and the engine's `expandInbetweens` now agree at every partial weight. On
   auburn this completes Laugh and Squint (body_skin, lower lids, mouth, cavity) and Sadness (brows, mouth, cavity).
   `build_character.py` calls it only when the face module has it (face_generic/4+).

## Acceptance

| Check | Result |
|---|---|
| T-204 measures, start → P2 → P3 (front, side, held-out 3/4) | table above; D3 not met (front 4, side 4 out; side 2 of them out of scope) |
| face_parity (Blender 5.3.0+02f0899d78e3) | **PASS**: knob-free PASS (12 face objects), rest 0.000032 mm, neutral 0, half-blink 0.000007 mm, smile+blink 0.000091 mm; [face_parity.json](face_parity.json) |
| face_parity `--strict` sweep | **PASS** 56 / 56, max 0.000119 mm (P2: 9 failing, 7.80 mm). P3-chin\*: FAIL, [face_parity_chin_variant.json](face_parity_chin_variant.json) |
| knob-free | PASS (no knob modifier, empty, lattice or vertex group left; keys relative to Basis) |
| export determinism | see [determinism.json](determinism.json): DETERMINISM_RESULT |
| glasses | rigid, clearances unchanged (above) |
| off-region knob motion | 0.000 mm outside every falloff / box on every build |

## Method and ledger

1. Knob design d0 (hand, [design0.override.json](design0.override.json)): chin Warp, cheek and jaw Hooks, midface Warp.
   It showed the chin lever and the chain fix (strict PASS); the Hooks were anchored on the head silhouette, which
   the measurer does not see. Anchors were then changed to the occluding outline (`front`) and the cheek (`cheek`).
2. Sensitivity rounds with `tools/fit/run.py t204-sens` (unchanged tool; controls are `face.knobs.*` scalars):
   9 + 8 + 7 + 7 controls. The last design ([knobs_start.override.json](knobs_start.override.json),
   [controls.json](controls.json), [sensitivity.json](sensitivity.json)) kept 6 controls.
3. Search: `t204-search`, seeded separable CMA-ES (seed 216, population 6, σ 0.12, 30 builds), T-215's objective
   (equal views, matched smile, 3/4 held out, edit penalty 0.005). Best: trial 6 (P3-chin\*).
4. Garment-clearance check of the best trial, then four variants (A, B, C, D) built and checked. C (bridge Warp
   only) is the candidate.

Ledger: about 34 sensitivity builds + 30 search builds + 9 single builds, about 60 Cycles review frames (4 build rows ×
13 + 18 expression tiles), 0 CI, no asset or version change. Timings: build about 90 s, measure about 30 s, parity
about 90 s on the 4-core container.

## Replay (repository root)

```sh
SPEC=assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.14.0.spec.json
D=docs/evaluation/characters/T-216
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec $SPEC \
  --override $D/candidate.override.json --out build/t216/p3 --no-glb --no-compare
python tools/fit/measurer.py measure --character auburn --out build/t216/p3m \
  --blend build/t216/p3/girl_auburn_bun_glasses_master.blend --spec build/t216/p3/spec.resolved.json
python tools/bpy_blender.py -b --factory-startup -P pipeline/charsys/face_parity.py -- \
  --blend $PWD/build/t216/p3/girl_auburn_bun_glasses_master.blend --strict --out build/t216/parity.json
python $D/determinism.py build/t216/det --spec $SPEC --override $D/candidate.override.json --runs 2
# fit (knob sensitivity + search), from T-215's proposal
python tools/fit/run.py t204-sens --character auburn --spec $SPEC --override docs/evaluation/characters/T-215/proposal.json \
  --override $D/knobs_start.override.json --controls $D/controls.json --out build/t216/sens --jobs 2
python tools/fit/run.py t204-search --character auburn --spec $SPEC --override docs/evaluation/characters/T-215/proposal.json \
  --override $D/knobs_start.override.json --sens build/t216/sens --out build/t216/search --budget 30 --popsize 6 \
  --sigma 0.12 --seed 216 --jobs 2 --noisy side/opening_h_w \
  --coupled front/cheek_width,front/jaw_width,front/chin_width,side/cheek_advance,side/cheek_bulge
python $D/sheet.py build/t216/sheet $D/sheet.jpg 0.14.0=<release master> P2=<p2 master> P3=<p3 master> 'P3-chin*'=<chin master>
python $D/sheet.py build/t216/sheet $D/sheet_face.jpg <same rows> --face --px 512
python $D/sheet.py build/t216/expr $D/expressions.jpg P2=<p2> P3=<p3> 'P3-chin*'=<chin> --expr
python $D/tables.py $D/scores.csv 0.14.0=<measures.json> P2=<...> P3=<...> 'P3-chin*'=<...>
python3 pipeline/charsys/tests/test_face_generic_v4.py --blender blender
```
