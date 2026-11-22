# T-214 | Render-side T-204 face measurer (phase P1)

`tools/fit/measurer.py` measures a character blend with **T-204's own definitions**. It derives T-204's trace points
from flat Workbench object-ID masks, depth, and projected landmarks, then calls `values()` from
[T-204 measure.py](../T-204/measure.py), so the definitions cannot drift. It is validated against T-204's hand
traces of the same T-202 renders. Auburn agrees on **51 of 64** measures, white-haired on **46 of 62** and the boy
on **59 of 69**. Every disagreement is explained below. `test_measurer.py` fails on any disagreement that is not
explained.

```sh
python tools/fit/measurer.py validate --character auburn --out build/t214/val     # T-202 cameras, neutral, 1024 px
python tools/fit/measurer.py measure  --character auburn --out build/t214/m [--blend B --spec S --px 512]
python tools/fit/tests/test_measurer.py                                           # ~60 s, needs bpy + the masters
```

Blender runs through `tools/bpy_blender.py` (the bpy module) unless `BLENDER=<exe>` is set. The output directory must
be empty and outside `assets/`. Nothing is saved to any blend.

## How it measures

- **Head-only build, three passes per view.** The master is loaded and its garments, rig widgets, lights and cameras
  are removed in memory. Each view gets three flat Workbench object-colour passes, each with a depth channel
  (`tools/fit/render.py measure_views`). **full** is what the camera sees, with the transparent lens omitted as in
  `tools/fit`. **face** has no hair, bun, hair accessories or glasses. **hair** keeps the main hair only.
  The classes are skin, lid, lash, eye L/R, brow, ear, mouth, cavity, glasses, hair, bun and hair accessory.
  Strand fibres take their mesh's class and are decoded from the R/G ratio, because Workbench varies their brightness.
- **Cameras** are T-202's `face_views.py` (70 mm, 36 mm vertical sensor, square frame) with each character's target,
  frame height and elevation ([views.json](views.json)). `measure` renders the 8 yaws (0, ±45, ±90, ±135, 180)
  neutral, plus each reference view at its T-204 yaw with its matched expression.
- **Landmarks.** `LM_*` empties are projected. Each iris is the analytic edge ring of the eye shader: the unit
  sphere of the texture space, at radius − 0.35 × limbal width, where the dark ring meets the sclera ramp. Felt
  `round_iris` is honoured. The predicted front iris spans 28.6 units against 28.5 measured on the T-202 tile. The
  nominal radius would give 30.2. Surface landmarks are the nose apex (the skin vertex near `LM_nose` farthest out
  from the ear axis) and the chin (BVH-nearest skin to `LM_chin`). Their visibility comes from `scene.ray_cast`.
  A hidden nose tip is omitted (null).

| T-204 field | Render derivation |
|---|---|
| crown / crest | Top of the hair-only pass, behind the bun where it hides it (E when not visible) / top of hair+bun; null when clipped |
| chin | Lowest point where the face surface steps ≥ 8 mm over the neck (front, turns). In profile, the occluding-edge pixel nearest the front view's 3D chin |
| left / right | Face-pass head region, flood-filled without crossing an 8 mm depth step, with the neck cut under the jaw edge. One row per 400-unit step, from between the opening top and the iris centre down to the chin |
| eye / iris / far | Connected eyeball pixels of the face pass at the near iris (inside lid and lash) / horizontal extremes of the iris disc the lids leave visible, at the ring's centre height (E when a lid covers part of it) / far iris centre |
| brow | Lowest brow pixel above the near pupil (face pass) |
| nose | Skin connected to `LM_nose` standing above a quadratic face fit by > 25 % of peak relief. The fit ring lies 1.1–1.6 × the projected `face.nose.size_m` |
| mouth / ear | Bounding box of visible lips + cavity / visible near-ear pixels (front: image-left). On turns: `ear_turn` rim to cheek contour at ear mid-height |
| cap, hair_at_cheek, bun_span | Hair+bun extremes above eye level / on the eye–mouth midline / bun extremes, after a 3×3 opening that drops stray fibres |
| fringe, skull, midbrow | On the nose column: lowest hair above the brows / top of the hairless head region / mean brow height |
| profile, exposed, profile_span, eye_y | Side views: anterior skin at eye level, 50 % and 85 % of the fall / skin window on the 50 % line in the full pass / full silhouette at eye height without glasses / opening centre |

The **M/E mark** follows T-204: E when a dependency is hidden in the full pass. **Groups:** `hair` covers hair_width,
hair_height, forehead_covered, fringe_eye, crown_above_skull, hair_cheek_width, bun_width, exposed_cheek and
profile_depth, and P2 fits it separately from `face` (T-212). Every H-normalised measure still depends on the hair
crown through H, so the face fit must hold the hair fixed. **Not measured:** the Lab colour rows need Cycles; the
masks carry no colour. Back views (±135, 180) record crown, chin and hair silhouette points only, because T-204 has
no back measures.

## Validation (auburn 0.14.0)

The measurer rendered the three T-202 cameras at 1024 px with the neutral face. It is compared with every
non-colour measure that T-204 traced on the same renders.
[Table](auburn/validation.csv) · [Evidence: T-202 tile, cyan hand, yellow measurer](auburn/validation_evidence.jpg) ·
[Full report](auburn/validation.json)

| View | Compared | Agree within T-204 tolerance | Agree with hand crown/chin |
|---|---|---|---|
| front | 33 | 30 | 30 |
| three quarter | 25 | 19 | 18 |
| side | 6 | 2 | 5 |
| **all** | **64** | **51** | **53** |

Disagreements are listed below, with T-204's mark on the hand value. In the reasons, H means the hand estimated the
crown or chin; the measure agrees when the hand crown and chin are substituted. TRACE means the hand trace differs
from the render pixels. SHADE means Cycles shading moves an edge that the masks cannot see. RIM means the hand
stopped at the glasses rim. HIDDEN means the feature is under hair or lens and the hand value is an estimate. The
test fails on any disagreement that [explained.json](explained.json) does not list.

| View/measure | Hand | Measurer | Gap | Tol. | Measurer with hand H | Reason |
|---|---|---|---|---|---|---|
| front/chin_width | 0.406 E | 0.498 | +0.092 | 0.075 | 0.496 | TRACE. The tile's skin row at 93 % (y 307) spans 160–242 units, 0.47 F |
| front/eye_height | 0.132 E | 0.151 | +0.019 | 0.015 | 0.153 | SHADE. The lid overhang and felt lid line darken the top 3 units of the eyeball |
| front/opening_h_w | 0.767 M | 0.893 | +0.127 | 0.073 | 0.893 | SHADE. Same opening top |
| three_quarter/brow_gap | 0.157 E | 0.125 | −0.032 | 0.022 | 0.135 | H + RIM |
| three_quarter/chin_width | 0.297 E | 0.403 | +0.107 | 0.075 | 0.389 | HIDDEN. A long lock crosses the near jaw |
| three_quarter/head_roundness | 0.706 E | 0.658 | −0.048 | 0.045 | 0.710 | H. Hand crown at the bun/hair junction (y 91); main hair rises to 73 behind the bun |
| three_quarter/iris_d_spacing | 0.365 M | 0.391 | +0.026 | 0.015 | 0.391 | PREC. The tolerance is 0.75 units of iris width here: 19.5 vs 18.9 units |
| three_quarter/iris_d_w | 0.636 M | 0.575 | −0.062 | 0.035 | 0.575 | RIM. The opening continues 7 units past the rim |
| three_quarter/jaw_width | 0.589 E | 0.657 | +0.068 | 0.065 | 0.649 | H |
| side/cheek_advance | 0.024 E | 0.050 | +0.026 | 0.020 | 0.054 | HIDDEN. Eye-level skin is behind the lens and rim |
| side/eye_to_chin | 0.255 E | 0.223 | −0.031 | 0.025 | 0.260 | H. Crown and chin are under hair |
| side/eye_y | 0.745 E | 0.777 | +0.031 | 0.025 | 0.740 | H |
| side/profile_depth | 0.865 E | 0.776 | −0.090 | 0.045 | 0.838 | H |

**What P2 must know.** (1) H differs from the hand crown on turns. The main-hair top is geometric and the same at
every yaw (73 units here). The hand crowns at 76, 91 and 99 follow the visible bun junction, and that junction moves
with the view. The reference crowns are hand-traced too, so fit H-normalised measures within tolerance bands, not
exactly. (2) The geometric eye opening reads about 0.02 H taller than a shaded render, because of shade under the
lid. Opening heights and opening_h_w therefore carry that bias against hand-traced references. The Supervisor
decides whether P2 subtracts it or widens the band. (3) The 3/4 opening includes the part outside the glasses rim.

## Validation (white-haired 0.1.0, boy 2.3.0)

The two other characters were run with the same method, on the T-202 cameras. Their full tables are in
[white-haired](white_haired/validation.csv) and [boy](boy/validation.csv), with evidence plates for
[white-haired](white_haired/validation_evidence.jpg) and [boy](boy/validation_evidence.jpg).

| Character | Compared | Agree | Agree with hand crown/chin |
|---|---|---|---|
| auburn 0.14.0 | 64 | 51 | 53 |
| white-haired 0.1.0 | 62 | 46 | 46 |
| boy 2.3.0 | 69 | 59 | 59 |

**White-haired.** Locks cover the front cheeks, and T-204 marks both contours E. At ear level the skin outline meets
the ears at x 106 and 294; the hand contour runs at 118 and 283. F is therefore 188 against 165 units, and every
/F ratio shifts by about 14 %. The underlying spans agree in units: cap, cheek hair, mouth and iris centres. The other
disagreements are the shaded opening (SHADE), soft nose boxes, and one lock edge on the profile cheek window.

| View/measure | Hand | Measurer | Gap | Tol. | Measurer with hand H | Reason |
|---|---|---|---|---|---|---|
| front/chin_width | 0.378 E | 0.511 | +0.133 | 0.075 | 0.492 | TRACE: hand E 0.378 F; the measurer's skin edge over the neck at 93 % gives 0.511 (0.492 with the hand H); hand contour E under hair. |
| front/eye_spacing | 0.564 E | 0.490 | -0.073 | 0.03 | 0.490 | HIDDEN/F: the cheeks are under hair locks (T-204 marks left/right E). At ear level the skin outline runs to x 106/294 against the ears, the hand contour to 118/283: F 188 vs 165 units, so every /F measure differs by about 14 %. |
| front/eye_x | -0.285 E | -0.245 | +0.040 | 0.025 | -0.245 | HIDDEN/F: as eye_spacing. |
| front/hair_cheek_width | 1.941 E | 1.717 | -0.224 | 0.12 | 1.717 | HIDDEN/F: hair span agrees (41-366 vs 40-360 units); the ratio differs through F. |
| front/hair_width | 2.080 E | 1.851 | -0.229 | 0.08 | 1.851 | HIDDEN/F: cap agrees (27-377 vs 29-372 units); the ratio differs through F. |
| front/head_roundness | 0.670 E | 0.760 | +0.090 | 0.045 | 0.769 | HIDDEN/F: as eye_spacing. |
| front/iris_d_w | 0.662 M | 0.714 | +0.052 | 0.049 | 0.714 | SHADE: iris agrees (137.1-170.3 vs 136.6-169.7); the geometric opening is wider than the shaded one by 2 units. |
| front/mouth_width | 0.189 E | 0.157 | -0.032 | 0.025 | 0.157 | HIDDEN/F: mouth box agrees (185.2-214.8 vs 184.6-215.7 units); the ratio differs through F. |
| front/nose_height | 0.058 E | 0.039 | -0.018 | 0.018 | 0.040 | TRACE: hand E box 275-290 includes the shaded underside; the relief box is 273-283. Agrees with the hand H. |
| front/opening_h_w | 0.689 M | 0.883 | +0.193 | 0.075 | 0.883 | SHADE: opening 237.5-278.5 vs hand 241.0-275.4: shade under the upper lid and on the lower lid. |
| three_quarter/eye_height | 0.143 E | 0.163 | +0.021 | 0.01788 | 0.170 | SHADE: as front opening. |
| three_quarter/iris_d_w | 0.563 M | 0.641 | +0.078 | 0.05 | 0.641 | SHADE: geometric opening narrower in the hand trace. |
| three_quarter/nose_width | 0.079 E | 0.109 | +0.030 | 0.025 | 0.109 | TRACE: hand E 236.6-251.5; relief box 230.5-251.2 includes the bump's far flank. Nose boxes are soft (T-204 E). |
| three_quarter/nose_y | 0.830 E | 0.802 | -0.028 | 0.025 | 0.817 | H: agrees with the hand H. |
| three_quarter/opening_h_w | 0.733 M | 0.915 | +0.182 | 0.06 | 0.915 | SHADE: as front opening. |
| side/exposed_cheek | 0.244 E | 0.204 | -0.040 | 0.035 | 0.202 | HIDDEN: the window between locks runs 214-264 units vs hand 203-263; a thin lock edge at 203-214 is hair in the masks. |

**Boy.** The hand contour starts 17 units higher than the measurer's. The temple is wider there, so F is 220 against
205 units (START). The hand skull is E at y 68 under the spikes, but the hairless head ends at 128. The drooping lid
hides most of the near iris on the turn. The measurer takes the visible iris disc, which gives the boy's front iris
within 1 unit of the hand trace.

| View/measure | Hand | Measurer | Gap | Tol. | Measurer with hand H | Reason |
|---|---|---|---|---|---|---|
| front/chin_width | 0.192 E | 0.393 | +0.201 | 0.075 | 0.399 | TRACE: hand E 0.192 F; the skin edge over the hood collar is 0.393 F at 93 %. |
| front/crown_above_skull | 0.133 E | 0.313 | +0.180 | 0.1 | 0.309 | TRACE: hand skull E at y 68 under the spikes; the hairless head (face pass) tops out at y 128. |
| front/eye_spacing | 0.495 E | 0.528 | +0.032 | 0.03 | 0.528 | START: 0.528 vs 0.495 through F; iris centres agree within 2 units. |
| front/hair_width | 1.657 M | 1.792 | +0.135 | 0.08 | 1.792 | START: cap agrees (16.8-383.6 vs 18-383 units); F 205 vs 220 units because the hand contour starts 17 units higher where the temple is wider. |
| front/head_roundness | 0.650 M | 0.600 | -0.050 | 0.045 | 0.604 | START: as hair_width. |
| front/jaw_width | 0.529 E | 0.605 | +0.077 | 0.065 | 0.607 | START: as hair_width (agrees in units: the hand jaw contour E). |
| three_quarter/cheek_width | 0.698 E | 0.817 | +0.119 | 0.055 | 0.831 | HIDDEN: near cheek under the fringe lock; hand contour E. |
| three_quarter/iris_d_spacing | 0.296 E | 0.349 | +0.053 | 0.035 | 0.349 | HIDDEN: drooping lid; the visible iris disc spans 195.3-224.2 vs hand E 196.8-222.4. |
| three_quarter/iris_d_w | 0.481 E | 0.565 | +0.084 | 0.05 | 0.565 | HIDDEN: as iris_d_spacing. |
| three_quarter/jaw_width | 0.371 E | 0.448 | +0.078 | 0.065 | 0.494 | HIDDEN: as cheek_width. |

## Scoring a release (`measure`)

`measures.json` and `measures.csv` hold every view's points, marks and T-204 values. On reference views they also hold
the target, tolerance, gap, z = gap/tolerance and the result. `summary` gives scored/within/mean |z| per view and
group. Views have **equal weight** (D2). The **matched smile** (D4) is `face_SmileOpen = 1` for auburn's
open-smiling sheet30 front and `face_Smile = 1` for white-haired id01. The other reference views are neutral. The
**held-out view** for checks only is the three-quarter view for each character (`views.json`). Auburn 0.14.0 at
512 px: [all 11 views](auburn/measures_8yaws.csv) · [overlays](auburn/measure_overlays.png).

| Auburn 0.14.0 | Face within / scored | Hair within / scored |
|---|---|---|
| front (open smile) | 16 / 27 | 3 / 7 |
| three quarter (held out) | 10 / 24 | 1 / 1 |
| side | 1 / 7 | 0 / 2 |

The other releases score as follows: [white-haired views](white_haired/measures_8yaws.csv) ·
[boy views](boy/measures_8yaws.csv).

| Release | Front face | Front hair | 3/4 face (held out) | Side face | Side hair |
|---|---|---|---|---|---|
| white-haired 0.1.0 (front smile) | 16 / 27 | 6 / 7 | 16 / 24 | 1 / 7 | 0 / 2 |
| boy 2.3.0 | 13 / 27 | 5 / 7 | 9 / 24 | 3 / 7 | 2 / 2 |

## Timings (4-core container, CPU)

| Run | Views | Wall |
|---|---|---|
| validate auburn / white-haired / boy, 1024 px | 3 | 13.0 / 32.3 / 16.5 s |
| measure auburn / white-haired / boy, 512 px | 11 | 30.6 / 95.9 / 41.4 s |
| test_measurer.py (all three validations + unit tests) | — | 62 s |

Per-view time is mostly fixed pass overhead with strand fibres. Strand fibres take most of that time, and white-haired has the heaviest groom. A P2 loop over the three
reference views costs about 10 s per try for auburn and 25 s for white-haired.

Ledger | builds 0 · Workbench renders only · CI 0 · no asset or version changes.
