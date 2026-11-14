# Hair experiments on `boy_yellow_hoodie` (charsys `hair_clumps/1`)

_2026-11-14. Cloud, Blender 5.3.0. Every variant is a separate spec override in
`assets/characters/boy_yellow_hoodie/experiments/hair/`, built and measured in its own folder
`renders/experiments/hair/<variant>/` (not tracked; it can be regenerated). v6, the spec and the published version
`1.0.0` were not changed. **No variant is published or approved.**_

Run:
```bash
python3 pipeline/charsys/hair_experiments.py --blender <blender>
```
Per variant the runner does: build (compare file), the 16-view harness, the comparison sheet, region renders on the 6
measured views, and the pilot metrics. These are the same tools and settings as the v6 baseline (48 samples, fill 0.94).

## Results (mean over the 6 measured views; v6 target for hair contour ≤ 3.0% of head height)
| Variant | Change | IoU | Hair contour mean | Hair contour p95 | Outline | Head fraction | Head width | Visual check |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H00 reference | none (control) | 0.841 | 3.40% | 7.2% | 1.43% | +4.0% | +5.7% | equals v6 (control reproduces 0.841 / 3.40) |
| H01 longer tufts | length ×1.15–1.35 | 0.834 | 4.03 | 8.3 | 1.50 | +5.4 | +7.6 | bigger mop |
| H02 up/out direction | tufts turned up and out | 0.827 | 4.78 | 10.0 | 1.56 | +4.8 | +10.2 | too wide |
| H03 irregular + asymmetric | jitter 12 mm, ±25% size, left +12% | 0.837 | 3.78 | 8.1 | 1.45 | +4.2 | +7.6 | messier, but bigger |
| H04 gaps | width 82%, 15% removed, base inset 12 mm | **0.845** | 3.13 | 6.9 | 1.40 | +4.1 | +5.7 | **scalp shows through: rejected** |
| H05 projecting spikes | 12 pointed up/out tufts | 0.841 | 3.20 | 7.6 | 1.38 | +6.1 | +4.4 | hard thorns, not felt tufts; too tall |
| H06 layered | tip lift ×1.6, pointier | 0.823 | 4.77 | 9.7 | 1.60 | +4.3 | +9.6 | bigger, wider |
| H07 felted surface | coarser noise, longer/denser fibres | 0.843 | 3.34 | 7.0 | 1.42 | +4.3 | +6.1 | slightly rougher; marginal |
| H08 = H04 + H05 + H07 | combination | 0.842 | **3.07** | 7.5 | 1.37 | +6.3 | +4.7 | scalp and thorns: rejected |
| H09 stronger gaps + short spikes | width 76%, 22% removed, inset 18 mm | 0.843 | 3.15 | 7.0 | 1.40 | +4.4 | +5.7 | large bald patches: rejected |
| H10 narrow clumps only | width 82% | 0.842 | 3.37 | 7.2 | 1.43 | +4.0 | +5.7 | no change |
| H11 = H10 + soft tufts | 8 blunt crown tufts | 0.842 | 3.35 | 7.1 | 1.42 | +4.0 | +5.6 | no change |
| **H12 drop clumps over dark base** | width 82%, 15% removed, **no inset** | **0.844** | **3.14** | **6.9** | **1.40** | **+4.0** | **+5.6** | **gaps show dark hair, no scalp: best clean result** |

Evidence:
- `hair_multiview_sheet.jpg`: all variants, 8 camera angles. The six measured views are aligned to the reference
  (reference outline in magenta); the two #29 views are shown as rendered.
- `hair_focus_sheet.jpg`: reference, H00, H04, H12 and H11.
- `hair_experiments_summary.json`: every metric per view.

## What the measurements show
1. **Making the hair bigger always hurts.** Longer, more upward or outward, or more layered tufts all worsen IoU
   and hair contour (H01, H02, H06). v6 hair is already too wide (+5.7%) and too tall (+4%).
2. **The gain comes from removing whole clumps at the outline** (H04, H12: hair contour 3.40 → 3.13–3.14%; the
   largest gains are in the side and back-¾ views). Narrower clumps alone do nothing (H10).
3. **Metrics alone are misleading.** H04, H08 and H09 score best but expose the scalp, because the inset base mass
   reveals the head. H12 shows that the inset is not needed for the gain. Every hair change therefore needs the
   visual check, not just the numbers.
4. **Spikes** improve the outline slightly, but make the head taller (+6%). The pointed shape reads as thorns, not
   the soft, blunt felted tufts of #7/#21.
5. **Surface felting** (H07) is a marginal change at this render size.
6. **No variant meets the ≤ 3.0% hair-contour target**; the best is 3.07% (H08, rejected) and 3.14% (H12). All
   variants still read as a rounded mop. The references have fewer, larger, separated locks with deep notches
   between them. The clump layout (104 small clumps over an ellipsoid), not its parameters, now limits the result.

## Recommendation (not applied)
- H12 is the only candidate that is both better and visually clean. Measured gain: IoU +0.003, hair contour −0.26
  points.
- Adopting it changes the hair identity, so it needs **your approval**. If approved, it would become spec version
  1.1.0, published with `--identity-change-approved-by`.
- The next real step for hair is a new layout, `hair_clumps/2`: about 30–40 larger locks, grouped into the lock
  families visible in #7/#21/#27, with notches cut down to the dark base, measured with the same runner.

## CP-2: `hair_clumps/2` lock layout (2026-11-14)
Diagnosis, measured on the existing H00/H12 renders without new renders:
- The v6 hair is **too full, never too small**. In the hair zone, the subject alone covers 7–17% of the reference
  hair area; the reference alone covers only 2–3%.
- The crown is a broad dome. In the side view the top 0–8% of the figure is 74–116% too wide (the reference has a
  few narrow tufts there), and the band 8–12% below the top is about 20% too wide in every view.
- The head mesh is **wider than the base hair mass** at every height (0.155–0.160 m against 0.145–0.153 m
  half-width). That is why close-lying locks expose skin, and why v6 needed wide side clumps.

The new generator `hair_clumps/2` (in `pipeline/charsys/hair.py`) uses lock families over the dark base mass:
- the v6 fringe (7 locks);
- blunt crown tufts;
- top, side and back rows of larger locks, with optional split tips;
- an optional **scalp cap**: the head surface above an azimuth hairline, offset by 6 mm, so no skin shows without
  widening the silhouette.

Runs used the 8 sheet views only (`--sheet-views-only`), which take about 115 s instead of 175 s. Metrics are on the
same 6 measured views as before.

| Variant | Hypothesis tested | IoU | Hair contour | Head fraction | Head width | Visual | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H00 (v6) | control | 0.841 | 3.40% | +4.0% | +5.7% | rounded mop | — |
| H20 lock families | lower dome, close locks, 38 locks | 0.851 | 2.85% | +2.6% | +0.8% | **smooth helmet**, long locks merge, skin at temple | rejected (visual) |
| H21 shingled rows | shorter overlapping rows, blunt raised ends, rougher felt (40 locks) | 0.844 | 3.08 | +4.2 | +4.9 | layered locks as in the refs; **skin at temple/behind ear** | partial |
| H22 temple fix | 3 changes at once (mistake) | 0.840 | 3.40 | +2.3 | +4.4 | skin still visible | rejected |
| H23 = H21 + scalp cap | cap covers skin without widening | 0.845 | 3.02 | +4.2 | +4.9 | no skin | kept |
| H24 = H23 + flared lower locks | the refs' lower locks flare out | 0.840 | 3.23 | +4.1 | +7.1 | wider | rejected (falsified) |
| **H25 = H23, less lock bulge** | volume drives the error | **0.8455** | **2.93%** | +4.1% | +4.1% | no skin, layered felted locks, soft crown tufts | **meets the target; candidate** |

Evidence: `cp2_hair_clumps_v2_sheet.jpg` (8 angles: reference, H00, H12, H20, H23, H25) and
`hair_experiments_summary.json`.

H25 (`experiments/hair/H25_v2_scalp_cap_less_bulge.json`) results:
- Hair contour **2.93%** against the ≤3.0% target (v6 3.40%).
- IoU 0.8455 (v6 0.841).
- Head width +4.1%, smaller than v6 (+5.7%).
- Head fraction +4.1% against v6's +4.0%: effectively equal, a 0.1-point rise within measurement noise.
- Its build rigs cleanly: 73 deform bones, 0 unweighted vertices.

Remaining weaknesses, seen visually:
- Behind the ear the cap reads as a smooth, short-cropped patch, not locks.
- The crown tufts are thinner and more pointed than in #7/#21.
- Per-view worst cases: side 3.52%, back-¾ 3.71%.

**H25 is not adopted or published.** It is an identity change and waits for your approval. If approved, it becomes
spec 1.1.0, published with `--identity-change-approved-by`. Version 1.0.0 and v6 are unchanged; the v1 hair path
still rebuilds v6 exactly (checked: 0.0 m).

## H26 after the H25 review (2026-11-14, not approved)
Your H25 review found:
- smooth cap patches at the temples and behind the ears;
- an undercut at the nape;
- too few dense irregular locks at the back;
- crown tufts too small and narrow.

H26 (`experiments/hair/H26_v2_dense_rows_fanned_crown.json`) is a spec override only, with no code change. It uses
the v6 row structure (4 back rows of 9–10 locks, 3 side rows per side), reaching the nape and behind the ears, with
H25's low lift and bulge, and 6 large, fanned, leaf-shaped crown tufts. 85 locks (140 parts). The scalp cap stays
only as an under-layer.

| | v6 (H00) | H25 | **H26** |
| --- | --- | --- | --- |
| IoU | 0.841 | 0.8455 | **0.8463** |
| Hair contour (target ≤ 3.0%) | 3.40% | 2.93% | **2.99%** |
| Head fraction | +4.0% | +4.1% | **+3.5%** |
| Head width | +5.7% | +4.1% | **+2.0%** |
| Worst views | #7 front 4.29, side 4.13 | back-¾ 3.71 | **#7 front 3.63**, side 3.52 |

Visual result (`H26_review_views_1-4.jpg`, `H26_review_views_5-8.jpg`; columns: reference, v6, H25, H26):
- Fixed: dense layered back, nape covered to the hood, no cap patches at the temples or behind the ears.
- Fixed: larger, fanned crown tufts.
- Fixed: rig compatible (73 deform bones, 0 unweighted vertices).
- Remaining: the crown tufts form a fairly regular ring. The references are more one-sided and irregular, with a
  dominant tuft.
- Remaining: the fringe is unchanged from v6.
- Remaining: #7 front is worse than H25.

The review sheets are made from existing renders by `pipeline/charsys/review_views.py` (no rendering).

## H27–H29: natural irregularity on top of H26 (2026-11-14, experimental, not approved)
New optional per-family controls in `hair_clumps/2`, configuration only:
- `az_jitter`, `el_jitter_deg`, `dir_jitter`, `length_jitter`, `width_jitter`;
- `dominant {index, scale}`.

They draw from their own random stream, so H26 rebuilds unchanged.

| Variant | Hypothesis | IoU | Hair contour | Head fraction / width | #7 front | Visual | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H26 | baseline | 0.8463 | 2.99% | +3.5 / +2.0% | 3.63% | regular crown ring | — |
| H27 | crown (shifted asymmetric) + rows, both irregular | 0.8403 | 3.68% | +2.0 / +3.8% | 5.39% | less ring-like, but rounder, wider mop; lost the tall front tufts | rejected (two groups changed; metric and visual agree) |
| **H28** | **crown irregularity only** (mild asymmetry −160..120°, jittered spacing, elevation, lean, length, width; dominant front tuft ×1.3) | **0.8493** | **2.92%** | +3.4 / +2.4% | **2.97%** | irregular crown with a dominant front tuft; back, nape and temple coverage as H26; no cap patches | **candidate** |
| H29 | row irregularity only (mild) | 0.8453 | 3.14% | +3.4 / +2.4% | 3.67% | no visible gain | rejected |

Evidence: `H28_H29_review_views_1-4.jpg`, `H28_H29_review_views_5-8.jpg` (reference | H26 | H28 | H29) and
`H27_review_views_1-4.jpg`.

**Remaining:**
- The crown is a few large tufts; the references have more, finer, fibrous tufts.
- A small dark gap at the crown top in the back views.
- The fibrous felt surface is unchanged: same fur and noise as H26, not addressed in this step.

**Generic vs. character data:**
- The generator, families, scalp cap and irregularity controls are generic.
- Family counts, angles, lengths, irregularity amounts, the dominant tuft and the hairline are character data.
- **Assumption that remains:** the hair is placed on an ellipsoid around the head (`proportions.hair_ellipsoid_*`).
  Very different scalp shapes (long faces, ears on top) would need a surface-projected placement.
