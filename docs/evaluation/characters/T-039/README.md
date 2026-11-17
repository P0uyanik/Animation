# T-039: Boy 2.0 body and proportions

Status: **development evidence; unpublished and unapproved.** This work introduces a body-only successor spec and
does not change the frozen 1.0.0 or 1.1.0 specifications or published assets.

## What changed

- Added `boy_yellow_hoodie.2.0.0-dev.spec.json`, a body-only `body_generic/1` spec whose dimensions come from the
  five neutral `val27` references and T-032 annotations.
- Added an optional asymmetric head profile loft to `body_generic/1`. The profile describes skull/jaw width and
  independent face/back depth by height, instead of forcing the head to be a tapered ellipsoid.
- Allowed a generic body build without face, hair, clothing, accessories or fur sections. Body-only builds still
  carry `LM_chin`, can write the neutral comparison pose, and retain the normal rig/export metadata.
- The body remains a generator result, not a copied legacy mesh. Face, hair, garments, accessories and fur are
  intentionally outside this part of Boy 2.0.

## Visual evidence

Each image is exactly 640 px wide: the owner reference is on the left and the body-only 2.0.0-dev render is on the
right.

- [front](turnaround/val27_front.png)
- [three-quarter right](turnaround/val27_threequarter_right.png)
- [side right](turnaround/val27_side_right.png)
- [back](turnaround/val27_back.png)
- [back three-quarter](turnaround/val27_back_threequarter.png)

The output deliberately has no hair or clothes. The comparison is for the underlying height, skull, shoulder,
limb and torso relationships; garment silhouette and hair volume are not targets in this task.

## Fidelity proportions: before and after

Relative difference is `render / reference - 1`. Before is the frozen 1.1.0 T-032 measurement. After is measured
from `build/t039_fidelity_01/renders` with the same T-032 frame, landmark-distance and centre-column formulas. The
machine-readable values are in [fidelity_proportions.json](fidelity_proportions.json).

| proportion | before (1.1.0) | after (2.0.0-dev body) | result |
|---|---:|---:|---|
| arm length / figure height | -20.3% | +10.7% | the large short-arm error is removed; the remaining overshoot is close to the +/-4 px joint annotation limit |
| shoulder width / figure height | +0.1% | -2.3% | within the 5% fidelity tolerance |
| visible leg gap / figure height | -35.7% | +21.4% (front/back only) | direction corrected; still dominated by bare legs versus loose trousers |
| bare skull / figure height | n/a (legacy value includes hair) | 0.314 | inside the 0.300-0.320 body target |

For the two stable straight views, leg gap is +31.5% in front and +11.2% in back. Oblique views are excluded from
that summary because the T-032 metric samples one centre column: loose overlapping trouser legs can turn the gap
almost off in the reference while separated bare legs remain visible. Tuning anatomy to that oblique garment
artifact would make the underlying legs incorrect.

## Results and limits

The body reads as the same short, large-headed child: the shoulder line is on target, the skull fraction is on
target, the old short-arm error is substantially reduced, and the front/back leg separation is now visible. The
profile loft also produces the flatter face plane and fuller rear cranium seen in the side reference.

This is not a whole-character fidelity score. A body-only render cannot meaningfully match hair, eyes, hoodie,
trousers, shoes, backpack, colour or texture regions, so those score components would punish intentionally absent
work. The references also estimate shoulders and palms through clothing, and their trouser silhouette is not a
direct measurement of nude leg anatomy. Final arm and leg tuning should be revisited when the 2.0 garments are
fitted, without changing the frozen specifications.

## Build evidence

- Body build: `build/t039_body_01/boy_yellow_hoodie_master.blend`
- Neutral comparison pose: `build/t039_body_01/boy_yellow_hoodie_compare.blend`
- Five 640 px fidelity renders and projected landmarks: `build/t039_fidelity_01/renders/`

The fidelity analysis process was interrupted after the render side completed, so T-039 records the proportion
subset directly from those deterministic render/landmark files rather than claiming a misleading aggregate score.
