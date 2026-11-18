# T-093 round 2 — garment/2 refinement (owner feedback 2026-11-18)

Candidate overrides: `assets/characters/{boy_yellow_hoodie,girl_auburn_bun_glasses}/spec/candidates/T-093/*.T-093.override.json`
(written by `make_overrides.py`); combined with T-092 presets/3: `*.T-093+T-092.combined.override.json` (`make_combined.py`,
T-092 material keys read from `candidates/T-092`, unchanged). Nothing is published or made current; published versions and
`*.spec.json` are untouched. Round 1 evidence is in `round1/` (its recipes name sha b83a37a, which was amended before
push; the round-1 commit is 2abc65f).

## Evidence
| what | file |
|---|---|
| boy 2.0.0 vs T-093, strict sheet (AI: B09 front, B07 side, B06 back, B01/B02 face) | `boy_2.0.0_vs_T-093/boy_2.0.0_vs_T-093_strict.jpg` |
| girl 0.11.0 vs T-093, strict sheet (AI: G08 front, G07 3/4, G04 face 3/4, ref_41 side/back crops) | `girl_0.11.0_vs_T-093/girl_0.11.0_vs_T-093_strict.jpg` |
| same, candidate on top of T-092 presets/3 (combined look) | `*_T-092/*_strict.jpg` |
| vest in reach, 0.11.0 / T-093 keys muted / T-093 | `reach/reach_before_after.jpg`, `reach/reach.json` |
| cheap first frames | `preview/` |
| full test run (71/71) | `test_garments_v2.log` |

## Owner points
a. **Backpack (B06/B07)**: zips removed; boxier body (roundness 5.5, depth .068); rounded flap wrapping the sides with a piped
   lower edge; centre tab with a ring buckle; front pocket with its own piped flap; top grab loop; navy felt (44,48,74).
   Flap/tab/buckle/pipings carry no surface fibres so the edges read crisp. The fabric fuzz still softens the silhouette slightly.
b. **Girl collar and vest edges**: rounded blouse collar (`collar.tip_round`), laid over the vest by `collar_clear`
   (two-sheet collar ray-cast onto the vest/blouse, lift smoothed, constant thickness); no fibres on the collar or the vest
   edge/pocket-edge pieces (`clean_fibres`). Test: collar fibres 0, edge fibres 0.
c. **Vest in reach** (FK upper arms −75° about X):

   | | flare max / p99 | vertices in blouse | p95 depth | max depth |
   |---|---|---|---|---|
   | 0.11.0 | 9.9 / 8.4 cm | 1127 | 2.35 cm | 3.0 cm |
   | T-093 keys muted (arm-weight cap only) | 5.4 / 4.9 cm | 1104 | 1.79 cm | 2.5 cm |
   | T-093 (cap + layer-order reach keys) | 5.5 / 4.9 cm | 495 | 0.40 cm | 1.9 cm |

   Rest: 110 vertices, p95 0.9 mm (no new penetration). Keys are 0 at rest and arms-down, 1 at reach.
d. **Details**: blouse sleeves to the wrist with a gathered cuff, shoulder skin closed (sleeve_start 0); split bloomer legs
   (hem gap 13 mm) with gathered (pleated) cuffs; sneakers with cream soles and two white side stripes on both walls;
   hoodie drawstrings plain cream felt with dark tips; boots with a rolled fleece cuff; one flower on the bun.

## Limitations
- The backpack's colour change is the one `material` change on the boy; in the combined render the girl's boot cuff takes
  T-092's band material instead of T-093's cream cuff.
- In the reach pose the lifted collar tips show as stiff flaps near the shoulder (side view); residual vest penetration is
  up to 1.9 cm at a few vertices near the armhole.
- The engine does not drive garment shape keys yet, and `garment_pose_eval` only knows garment/1; the reach keys are
  evaluated here with Blender drivers.
- Scrunchie as a smooth band needs groom code (T-091, out of this write-set).

## Tests
`python3 pipeline/charsys/tests/test_garments_v2.py --blender <blender> --boy-master ... --boy-base-master ...
--girl-master ... --girl-base-master ...` → 71/71 (`--quick`: pin + validation only). Round 2 change to the test: the flap's
front-edge height is measured on its piping (`flap_edge`), because the flap now wraps down the bag's sides and its own
bounding-box bottom is a side corner; thresholds unchanged.
