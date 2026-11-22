# T-198 golden delta (0cb0053 vs this branch)

Measured with `golden_dump_t198.cpp` (every bone's world transform per frame, both builds) and
`golden_delta_t198.py` (world turn / travel differences, chord-based so identical poses read 0).

## Content goldens (cast = the imported test packages)

All 6 identical (exchange, handover, e901 s010, e905 s010, e907 s010, e907 s010_calibrated). Round 1 had changed
exchange / e907 s010 (f60-66) and s010_calibrated (f110-121): boy head <= 29.0 deg, neck and DEF-spine.005 19.5 deg,
eyes <= 39.5 deg, <= 0.8 mm. The cause was the look arc (eyes; alone 26 deg) and the lagged look direction (head; alone
17 deg) firing on his look switch through his own head at a peak of 33-35 deg / frame, which is under the limit. Both
are now gated by the measured head-chain peak.

## test_interaction/visibleGrip/boy (re-recorded, Supervisor approval R6 ~18:45Z)

The orient blend pass (interaction.cpp). Only frames 11-14, only hand.R and the 19 bones it carries (fingers,
DEF hand bones). Before, a 147 deg one-frame flip of the hand at f11 (the shortest-path slerp changed side).
visibleGrip girl / engine: identical.

| frame | hand.R step before, deg | hand.R step after, deg | hand.R before vs after, deg | bones that differ | largest travel difference, mm (bone) |
|---|---|---|---|---|---|
| 9 | 17.6 | 17.6 | 0.0 | 0 | 0.0 |
| 10 | 21.7 | 21.7 | 0.0 | 0 | 0.0 |
| 11 | 146.7 | 25.0 | 126.7 | 20 | 112.2 (DEF-f_pinky.03.R) |
| 12 | 27.2 | 24.7 | 77.8 | 20 | 69.8 (DEF-f_pinky.03.R) |
| 13 | 19.3 | 21.4 | 37.4 | 20 | 32.5 (DEF-f_pinky.03.R) |
| 14 | 12.4 | 15.0 | 10.1 | 20 | 8.7 (DEF-f_index.03.R) |
| 15 | 4.6 | 5.5 | 0.0 | 0 | 0.0 |
| 16 | 0.0 | 0.0 | 0.0 | 0 | 0.0 |
