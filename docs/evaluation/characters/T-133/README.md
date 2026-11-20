# T-133 · White-haired girl in the blue knit dress

**Propose the contour trial.** Against the primary identity front it gains **1.05 points**, mostly from the outline and eye spacing. The 02 front also improves. The 02 profile is effectively tied. [Proposal](proposal.json) · [Seven measured builds](scores.csv) · [Visual comparison](evidence.jpg)

| Measure | First version | Proposal | Target |
|---|---:|---:|---:|
| 01 identity fit / 100 | 89.35 | 90.41 | 100 |
| 01 figure IoU | 0.8109 | 0.8250 | 1 |
| 01 visible eye-centre spacing, registered px | 159.9 | 143.2 | 133 |
| 02 A-pose IoU, front / left | 0.8512 / 0.7714 | 0.8557 / 0.7716 | 1 / 1 |
| Hem below bun top, fraction of mesh height | 0.727 | 0.737 | 0.736 on 01 |
| 03 sole-to-bun height, m | 1.0523 | 1.0514 | ≈1.069 |

### What to carry forward

The eye anchor moves inward 6.83 mm per side. The skirt is 11 mm longer with flare 0.079 (from 0.072). Both bun radii fall from 77.45 to 69.5 mm and the outer and side lock end scales fall from 0.58 to 0.43. The simpler eye-and-flare trial has the closer eye spacing (139.9 px) and strongest profile. The contour trial earns the higher primary score and matches the hem level. Chin error changes by less than one annotated pixel.

### First-version review and ranked next steps

1. **Face, 01/04/14.** Blue irises, catchlights and the small closed smile read clearly. The closed neutral follows 14 e1 and 02, while 01 has an open smile. In the neutral close-up a skin wedge cuts across each inner eye and a shelf crosses each cheek. In Blink, the lids close into angular pale patches and the downward dark lash arc in 04 and 14 disappears. Repair the socket surface and add the closed-lash curve in the face generator before further fine spacing adjustments.
2. **Dress and boots, 01/02/16.** The flared skirt, tights and turned cuffs read at figure size. Both hands disappear against the skirt in the lowered pose. Reference 01 shows the fingertips. Check cuff and hand clearance. The collar flattens into two small tabs. Skirt leaves, hem ribs and sole stitches lose definition. The boots look squat even though the built cuff top is at 0.858 of body height from the top (01 target 0.859). Keep that level and work on shaft-to-toe width, cuff pile and the projecting sole. Compare collar seating and knit relief in 16-sized crops. The T-126d garment preset suggestions are metadata outside its active override. The ordered build uses the dress layer’s clothing presets.
3. **Hair and bow, 01/02/17/18.** The first version has twin cream buns, a right-side blue bow and a continuous back mass that divides into S-waves. The rear render shows thick, synchronized bends with hooked tips. In 17 the tips separate into fine wisps. In 18 the padded loops and knot are distinct. At figure size the build’s loops merge. Refine tip taper and stagger, then separate the bow loops from the knot.
4. **Cast scale, 03.** The lineup gives a height ratio of 955/983 to the other girl. At the stated 1.10 m anchor that implies about 1.069 m. The proposal is about 18 mm shorter. Check both built characters on a shared floor before changing rig scale. Registered image scores remove absolute scale.

### Build and scoring

Input `683794f`. Use the T-126a candidate `girl_white_hair_blue_dress.0.1.0.spec.json`. Apply T-126’s `body_face/hands_r2.override.json`, `hair/candidates/girl_white_hair_blue_dress.hair.override.json`, `dress/girl_white_hair_blue_dress.dress.override.json`, then `materials/girl_white_hair_blue_dress.T-126d.override.json` against that candidate. Apply the proposal last. Its arrays preserve all sibling entries. All blends and temporary annotations are under `build/t133/`.

T-090/T-115 Workbench search, seed 4, 320 × 640, assumed 70 mm lens, indexed yaw and elevation. Five A-pose builds include the start and sample eye x [0.058, 0.065], head half-width [0.137, 0.148] and boot height parameter [0.46, 0.56]. Two additional builds target the measured eye-spacing and contour errors. The CSV records each trial. Reapplying each override to the four-layer start reproduces its build-report SHA-256. All seven fit-tool tests passed. Final selection uses the highest pose-matched 01 score. Each master was rendered with a 35° upper-arm rotation for 01 and its native A-pose for 02.

01 uses the upload alpha (>127) and crop-relative iris centres, nose, mouth and chin. The score equally weights silhouette IoU and mean landmark agreement normalized by reference head height. Visible eye-opening centres approximate the marked irises. The score has no eye-shape or material term. 02 uses separately registered front and left outlines segmented from the indexed crops with GrabCut. Padding of 96 px on 01 and 24 px on 02 counts candidate spill outside each crop. Cycles review frames use 4 samples; fibre and stitch detail at that resolution is qualitative.

2026-11-19T20:09:43Z | T-133 | READY | t-133-codex-third-fit@683794f | input 683794f | Local proposal gains 1.05 points on 01.

Ledger splits overlapping timed worker intervals equally among active categories.

ledger: build 13.76 · render 8.71 · tests 0.01 · ci 0 · wait 0 (min)
