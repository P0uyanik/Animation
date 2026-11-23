# T-215 | Auburn P2: fit existing face controls to the T-204 bands

Character `girl_auburn_bun_glasses` 0.14.0. This is phase P2 of the face plan (fit-and-lock on our own generator).
The output is an override only, [proposal.json](proposal.json). No asset, version or CURRENT pointer changed. The
release is a later phase and needs the owner's sheet review. Score = T-214 measurer with its scoring defaults (visible
opening, visible crown). Views have equal weights (D2). The front smile reference is scored against the matched
`face_SmileOpen` (D4). The 3/4 view is held out: it is checked only, never in the objective. Hair measures are
reported apart and not fitted.

## Result

Pass rule D3 needs every scored T-204 measure within its tolerance, plus the owner's sheet review.
**The proposal has 25 of 34 fitted face measures within tolerance (start: 14).** Full measure of the proposal build
(8 yaws + 3 references, 512 px):

| View (within / scored) | Start (release 0.14.0) | Proposal | Mean abs z |
|---|---|---|---|
| front face | 13 / 27 | **23 / 27** | 1.23 → 0.83 |
| side face | 1 / 7 | **2 / 7** | 2.89 → 2.44 |
| 3/4 face (held out) | 9 / 24 | **13 / 24** | 1.68 → 1.48 |
| front hair (not fitted) | 3 / 7 | 5 / 7 | 1.15 → 1.11 |
| 3/4 hair (not fitted) | 1 / 1 | 1 / 1 | 0.40 → 0.58 |
| side hair (not fitted) | 0 / 2 | 0 / 2 | 6.25 → 6.14 |

The held-out 3/4 view improves without being fitted (+4), so the fit is not over-tuned to front and side. Per measure:
[scores.csv](scores.csv) has start vs proposal with z and result for every reference row. Held-out rows are flagged.

**Regressions (outside before and after):** front `jaw_width` z −1.37 → −1.83 and `cheek_width` −1.87 → −2.12.
The search narrowed `lower_face.jaw_x`, which helps the profile cheek but narrows the front jaw. `outline_exponent`
would widen the jaw at about +0.43 z per step without that trade, but it was dropped as coupled with `jaw_x` (below).
A short follow-up search with `outline_exponent` in place of `jaw_x` is cheap (about 12 builds) if wanted.
Nothing that was within the band at the start fell outside.

**Proposal edits** (start → proposal, in finite-difference steps). The largest moves:
- `layout.mouth_below_eye_m` 0.055 → 0.0468 (−2.0 steps): the mouth sits higher.
- `eyes.lids.upper_edge_deg` 34.5 → 42.2 (+1.9): the opening is taller.
- MouthWide `lo_drop_m` 0.014 → 0.0101 (−1.3): a smaller open-smile drop. This touches every expression that uses MouthWide.
- `ears.radii_m.2` +1.2: taller ears. `ears.below_eye_m` +0.9: the ears sit lower.
- `eyes.scale.0` −1.1: narrower eyes. `eyes.yaw_deg` 0 → 4.2.
- `lower_face.jaw_x` −0.9.
- The other 10 controls move under one step each.

The edit penalty at the best trial is 0.084 of a cost of 0.640.

[sheet.jpg](sheet.jpg) shows all 8 yaws in Cycles with the current release look. The rows are reference, before
(0.14.0) and after (proposal build). Settings are T-202 `face_views.py`: 16 spp + OIDN, `character_neutral/1`, 70 mm,
neutral face, 448 px tiles shown at 240 px. +45 and +135 have no reference, so the −45 and −135 references are
mirrored there and labelled. The sheet is for the owner review; it is not part of the score.

**Face close-up and difference overlay** (Supervisor request). At the sheet scale above, the face is about 80 px:
- [sheet_face.jpg](sheet_face.jpg) has the same render settings with a head-filling frame (target z 0.765, frame
  0.34 m) at −90, −45, 0, +45 and +90. Rows are reference, before and after. Reference tiles are cropped from the
  sheet30 annotations (eye and chin landmarks) to the render's eye height and eye-to-chin span. ±45 and −90 use
  mirrored tiles, labelled. Command: `sheet.py ... --face --px 512`, 6 min 35 s.
- [diff_front.jpg](diff_front.jpg) shows before (cyan) and after (magenta) on the neutral front and on the scored
  open-smile front: Workbench class outlines (head silhouette, eyes, mouth, brows, ears, glasses) plus the T-204
  points (iris span, mouth and ear boxes, chin). From the `measurer.py measure` arrays: `diff.py <before dir>
  <after dir> <out>`. It shows the higher mouth, the taller and lower ears, the taller and narrower eye openings
  and the slightly narrower jaw. The head silhouette above the jaw is unchanged.

**face_parity (T-213) on the proposal build, report only:** PASS (Blender 5.3.0+02f0899d78e3).
- Knob-free: PASS.
- Core expressions: neutral 0, half-blink 0.00006 mm, smile+blink 0.00009 mm, all within the bound.
- Sweep: 9 failing, max 7.80 mm, from the same known chain gaps as the release (Laugh, Sadness, Squint). The release
  had 9 failing, max 8.77 mm.
- Summary: [face_parity.json](face_parity.json).

## Stuck list (input for P3)

These fitted-view measures are still outside the band. [stuck.json](stuck.json) lists, per measure, the three
controls with the largest helpful response in z per step:

| Measure | z now | Why existing controls do not reach it | P3 lever |
|---|---|---|---|
| front, side `eye_to_chin` / `eye_y` | ∓2.41 front, ∓1.97 side | `layout.chin_below_eye_m` moves the face shape, not the outline chin (0.2 z per 6 mm); the best lever, `eyes.offset_z_m`, gives 0.21 z per step | head outline chin (`body.params.head.outline.chin_t`, lower half height) / `face_generic/4` outline points |
| front `cheek_width` | −2.12 | best is `cheek_pad_m` at +0.34 z per step, near its bound | front outline control points at the cheek band |
| front `jaw_width` | −1.83 | `outline_exponent` +0.43 z per step (see the follow-up above); otherwise the outline | front outline points below the mouth |
| side `cheek_advance` | +2.25 | eye scale and lids move it at most 0.35 z per step | profile outline at eye level |
| side `eye_width`, `opening_h_w` | −1.75, +8.32 | the profile opening is about 13 px wide behind the rim. `opening_h_w` jumps ±2.4 z with unrelated controls, so it is kept in the objective but marked noisy for control selection | eye-opening superellipse and lid droop (`face_generic/4`) |
| hair: front `forehead_covered`, `fringe_eye`; side `exposed_cheek`, `profile_depth` | −2.34, +1.80, −6.73, −5.55 | hair is held fixed (not fitted); `profile_depth` also carries the T-214 H caveat | hair release (T-207), separate fit |

## Method

1. **Controls.** [controls.json](controls.json) holds 30 existing `face.*` scalars, each with bounds and a
   finite-difference step: layout, eyes, lids, brows, ears, mouth and MouthWide, and the cheek/jaw shape controls.
   Head-outline scalars (`body.params.head.*`) were left out because they also move the groom frame, and the hair
   must stay fixed.
2. **Sensitivity matrix.** 31 full builds (start + one forward step per control, backward where the step would
   leave the bounds), each measured on the reference views plus neutral yaw 0, which anchors the profile chin as
   in the default measure run. The start build reproduces the release measures exactly (207/207). Columns are in
   [sensitivity.json](sensitivity.json).
3. **Selection** (`core.select_controls`). 18 kept, 12 dropped:
   - No reach (largest |dz| under 0.25 per step): `ears.radii_m.1`, `eyes.scale.1`, `mouth.jaw_open_deg`,
     `mouth.lip_height_m`, `shape.cheek_fullness_m`, `shape.face_width_m`, `shape.face_width_below_eye_m`.
   - Redundant (cosine over 0.95): MouthWide `widen` ≡ `mouth.half_width_m` (cos 1.00).
   - Cheek vs jaw on the front and profile traces (`cheek_width`, `jaw_width`, `chin_width`, `cheek_advance`,
     `cheek_bulge`, cosine over 0.85, tested only where both controls move that family by at least 0.25):
     `jaw_round_m` (0.87) and `outline_exponent` (0.85) are coupled with `jaw_x`; `cheek_forward` with
     `eyes.offset_z_m` (0.88); `lids.lower_edge_deg` with `eyes.scale.2` (−0.98).
   - `cheek_x` and `cheek_pad_m` (cheek) stay separable from `jaw_x` (jaw).
4. **Search** (`core.cmaes`). Seeded separable CMA-ES: seed 215, population 6, σ 0.12 of the bounds, 30 builds.
   - It starts at the optimum of the same CMA-ES run on the linear finite-difference model (no builds).
   - Cost = mean over views of the mean band loss, plus 0.005 × Σ(edit / step)².
   - Band loss = 0.5 for being outside the band, plus 0.5 per tolerance beyond it (capped at 4), plus a weak pull
     to the band centre. A measure that turns unscored costs the maximum.
   - A first run with a squared hinge was stopped after 6 builds: one profile outlier (`opening_h_w`, z 7.3)
     outweighed the front count, and the front fell from 13 to 9 within. The loss was then made count-oriented.
   - Trials are in [search.json](search.json). The best is trial 15.

## Timings (4-core container, CPU, 2 trials in parallel)

| Step | Builds | Wall |
|---|---|---|
| Sensitivity matrix | 31 | 33 min |
| Search (+ 6 discarded in the first run) | 30 | 32 min |
| Per trial: build / measure (median) | — | 112 s / 13 s; about 64 s effective in parallel |
| Proposal: full 8-yaw measure | 1 | 24 s |
| Cycles sheet (16 views) | — | 3 min 44 s |
| face_parity (with sweep) | — | 2 min 17 s |

Details are in [timings.json](timings.json). Ledger: 68 builds (1 timing + 31 + 6 discarded + 30), 1 proposal
build, 26 Cycles review frames (16 sheet + 10 close-up), 0 CI, no asset or version changes.

## Replay (repository root)

```sh
SPEC=assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.14.0.spec.json
python tools/fit/run.py t204-sens --character auburn --spec $SPEC \
  --controls docs/evaluation/characters/T-215/controls.json --out build/t215/sens --jobs 2
python tools/fit/run.py t204-search --character auburn --spec $SPEC --sens build/t215/sens --out build/t215/search \
  --budget 30 --popsize 6 --sigma 0.12 --seed 215 --jobs 2 --noisy side/opening_h_w \
  --coupled front/cheek_width,front/jaw_width,front/chin_width,side/cheek_advance,side/cheek_bulge
# proposal build, full measure, sheet, parity
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec $SPEC \
  --override docs/evaluation/characters/T-215/proposal.json --out build/t215/pb --no-glb --no-compare
python tools/fit/measurer.py measure --character auburn --out build/t215/pm \
  --blend build/t215/pb/girl_auburn_bun_glasses_master.blend --spec build/t215/pb/spec.resolved.json
python docs/evaluation/characters/T-215/sheet.py \
  assets/characters/girl_auburn_bun_glasses/versions/0.14.0/girl_auburn_bun_glasses_master.blend \
  build/t215/pb/girl_auburn_bun_glasses_master.blend build/t215/sheet docs/evaluation/characters/T-215/sheet.jpg
python tools/bpy_blender.py -b --factory-startup -P pipeline/charsys/face_parity.py -- \
  --blend build/t215/pb/girl_auburn_bun_glasses_master.blend --out build/t215/parity.json
```
