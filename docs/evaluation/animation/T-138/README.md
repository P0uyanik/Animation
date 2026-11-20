# T-138 (E4): grasp contact accuracy, band fit

Input `8f6c565` (`integration/t-134`). Opt-in: scene `"interaction": {"graspFit": true}`. Without it, every pose and
bake is unchanged.

## What changed
| File | Change |
| --- | --- |
| `engine/scene/scene.h/.cpp` | `InteractionOptions::graspFit` parse/save (key lines only; T-136 owns these files) |
| `engine/scene/interaction.cpp` | a banded grasp keys `hand.<s>.bandFit` = 1 (Step) when `graspFit` is on |
| `engine/anim/animation.h` | `HandPose::bandFit` + track doc (one field; **outside the extension, which named only animation.cpp**) |
| `engine/anim/animation.cpp` | band step, fit mode (below) |
| `tests/test_grasp_contact.cpp`, `tests/CMakeLists.txt` | 3 new cases |

**Fit mode** (only with `bandFit`, and only when the T-051 band step leaves a fingertip centre outside [lo, hi]):
- A finger touches the cylinder at its centre's height, so the step runs again from the touching pose.
- It aims the contact centres at `[lo + e, hi − e]`, where `e` keeps as much skin inside the band as side-by-side
  fingers allow, but at least 1 mm.
- Each finger's spread search can grow its bracket to 60° (T-051: 30°).
- The thumb uses the same `e`.
- A hand that already fits poses bit for bit as without the fit. The wrist, palm and arm do not move.

## e910 s010, boy R `grip` (45-90 mm) f79-137, girl L `grip_b` (10-55 mm) f115-192
Measured with T-051 `measure_t051` on the run_shot resolved scenes: `s010` as is vs `s010_fit/shot.scene.json` (= s010
+ `graspFit`).
| hand | | band out (max) | tip gap (held) | deepest | thumb side | closest adjacent tips | tip heights f100 (thumb, index..little) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boy R | before | 10.87 mm | 0.00 | +12.98 | −18.4 | 8.5 mm | 44.2, 98.5, 70.7, 62.2, 34.3 |
| | **after** | **4.28 mm** | 0.00 | +12.98 | −18.4 | 14.4 mm | 44.2, 92.8, 74.7, 60.3, 40.9 |
| girl L | before = after | inside (4.0 margin) | 0.00 | +7.68 | −20.6 | 9.9 mm | identical |

- The wrist is identical in both runs. `reach/run.py` reports the same moves for both bakes.
- Default path: the e910 bake with the change is byte-identical to the one before it (sha256 `14173a20…`).
- **Remainder (4.3 mm) is geometric.** The hand is too wide for the band:
  - hands_r2's finger roots are 26 mm apart, about 78 mm across the four fingers;
  - the band is 45 mm;
  - spread saturates (index error 3.8 mm at −60°, little −5.1 mm at +60°).
  - Rolling the hand made it worse (scratch: 18-29 mm). Closing the rest needs a wider band or fewer fingers on the band.
- Visual: `before_after_f80_f100.jpg` (Cycles 8 spp, 320x240, close cameras via T-051 `render_close.py`). After, the
  index and little fingers close towards the middle and the little finger no longer hangs below the band. No full
  render was made.

## Tests
- `plush_tests`: 227/227 (224 + 3 new), 772792 assertions; golden interaction hashes unchanged.
- `ctest`: pass (renderer skipped, not built).
- New cases (boy 1.0.0 / girl m3 test packages, SDF skeleton):
  1. On a 19 mm band, band out improves from 5.59 to 4.12 mm (boy) and from 4.27 to −0.63 mm (girl). Tips stay on the
     surface (≤ 0.53 mm) and the wrist does not move. The SDF hand fits this band and is unchanged.
  2. Felt_cup's own band: tips are bit-identical with and without the fit.
  3. Option parse and type error; `bandFit` is keyed only with the option and a band.

Blender: bpy 5.3.0 module (`blender` wrapper).
