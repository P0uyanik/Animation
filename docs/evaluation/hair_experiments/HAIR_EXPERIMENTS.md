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
