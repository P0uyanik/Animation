# T-157 (E4): grasp gap options — wider band vs fewer contacting fingers

Input `e2c8904`. Follow-up to T-138 (residual 4.1 mm, boy R on felt_cup `grip`, band 45-90 mm).

## Opt-in route
Only with the T-138 band fit (`hand.<s>.bandFit`). The options go on a new authored track,
**`hand.<s>.bandFitOptions` = (widen lo, off bits, widen hi)**:
- **widen lo / hi** (m): the band grows below `lo` / above `hi`. The thumb uses the same band.
- **off bits**: bit k = finger bone `f<k>`. The finger closes towards the cup, then opens until its skin is half a skin
  radius clear, or fully open. It does not touch the cup.

Notes:
- The track is absent or 0 → T-138 exactly (`animation.cpp` reads it only with `bandFit`).
- No scene, verbs or asset parser changed: those files are outside the write-set. Hand-authored keys win over
  generated ones, so the shot's `animation` block switches it on (`make_variants.py`).
- **Bit mapping:** the HandPose doc says f0 = little, but the e910 rigify packages map **f0 = index … f3 = little**.
  So "little off" is bit 3 (8).

Files: `engine/anim/animation.h/.cpp` (options + off-band finger), `tests/test_grasp_contact.cpp` (1 new case).
`interaction.*` and `content/hand_shapes/` are unchanged.

## e910 s010, boy R `grip`, held f85-130 (girl L `grip_b` f120-192 unchanged in every variant)
Run: `run_shot --stages prepare` (current cast as `production`: boy 2.2.0 / girl 0.13.0 + hair_r5 + hands_r2) →
`make_variants.py` → `measure_t157` → `summarize.py`.

- **band out**: max over held frames, against the variant's band; off fingers are excluded, the thumb is included.
- **tip gap**: contacting digits.
- **clearance**: min over the digit's segment points (skin to surface; < 0 = inside).

| variant | band (mm) | band out | tip gap | finger clearance | thumb clearance | off finger clear | closest tips | tip heights f100 (thumb, index..little) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-138 | 45-90 | **+4.10** | 0.00 | 0.00 | −5.02 | – | 14.4 | 44.2, 92.8, 74.7, 60.3, 40.9 |
| a: wider band (5, 0, 5) | 40-95 | **−0.80** (all in) | 0.00 | 0.00 | −5.02 | – | 17.7 | 40.8, 94.0, 76.4, 58.7, 40.9 |
| b: little off (0, 8, 0) | 45-90 | +2.80 (index) | 0.00 | 0.00 | −5.02 | +6.06 | 21.4 | 44.2, 92.8, 67.6, 46.0, *26.3* |
| c: little off + (0, 8, 5) | 45-95 | +0.80 (thumb) | 0.00 | 0.00 | −5.02 | +6.06 | 21.4 | 44.2, 94.0, 70.1, 46.0, *26.3* |

- **The index is the limit, not the little finger.** Its spread saturates at 92.8 mm in every variant.
  - Freeing the little finger (b) does not help: the index stays 2.8 mm over 90.
  - The band must reach about 93 mm on top. The little finger can reach 31 mm at the bottom.
- **Penetration:** no finger enters the cup in any variant.
  - The thumb's proximal segment is 5.0 mm inside the skin margin (−5.02) in every variant, including the default
    bake. This was there before T-157.
- **Wrist:** identical in every variant (the wrist column of `measures/*.json`).
- **Cup rim:** the cup is 100 mm tall with an open top. With option (a) the index contact centre sits 6 mm under the
  rim (T-138: 7.2 mm).

## Visual
`options_f100.jpg`. Rows: T-138, a, b, c. Columns:
- the shot camera (640x360) — a 120x90 px crop around the hand, enlarged 3x;
- a close front view;
- a close front-left view.

Render: Cycles 8 spp, f100, `T-051/render_close.py`.

`recipe.py preview` was not used: its views are character turnarounds, not shot cameras.

- **a:** the four fingers wrap evenly over the cup face, from the rim to the lower third. It is a compact cup hold.
- **b / c:** the lifted little finger hangs 6 mm off the cup. It splays downwards (26 mm high). At shot size it reads as
  a stiff, separated finger.

## Recommendation: option (a), the wider band (40-95 mm, i.e. 5 mm at each end)
- It is the only option with every contact in its band.
- Contacts stay on the surface, nothing is added inside the cup and the wrist does not move.
- The fingers are more evenly spaced (closest tips 17.7 vs 14.4 mm).
- It keeps the four-finger wrap. Hand references for a cup hold were not re-checked in this task.
- Fewer contacting fingers needs the same band widening anyway (because of the index), and adds a hovering finger.

**Open:** making (a) the default means changing felt_cup's `side_a` band to [0.04, 0.095]. That is a
`content/assets` change, outside this write-set (it also moves `grip`'s overlap check with `side_b`, 10-55 mm,
opposite side). Until then a shot opts in with the track. The −5 mm thumb clearance is a separate, pre-existing issue.

## Tests and baselines
- `plush_tests`: 240/240 cases, 774367 assertions (1 new: T-157 options on the boy, girl and SDF test hands:
  - options at 0 = T-138 bit for bit;
  - a wider band: all in, on the surface, nothing inside, wrist fixed;
  - f0 off: clear of the cup by half a skin radius — the SDF hand fully open at 1.8 mm.)
- `ctest`: 1/1 pass. Golden interaction hashes unchanged.
- Default path, byte for byte, with and without the change (plush-render rebuilt from `e2c8904` animation.*):
  - e910 s010 bake `f03f7e34…`;
  - with `graspFit` (T-138) `58238a02…`.
- Blender: bpy 5.3.0 module (`blender` wrapper).
