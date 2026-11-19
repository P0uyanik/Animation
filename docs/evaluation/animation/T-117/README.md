# T-117: 8 s cup-exchange showcase (e910 s010)

Input `dc21833` (`integration/t-114`), branch `t-117-claude-showcase`. Task: [docs/tasks/T-117.md](../../../tasks/T-117.md).
Shot: `episodes/e910_showcase/shots/s010/shot.scene.json`, written by
[make_shot.py](../../../../episodes/e910_showcase/make_shot.py). 192 frames at 24 fps (8.0 s), calibrated timing.

- Movie: [e910_s010.mp4](e910_s010.mp4), 640x360, 24 fps, Cycles 16 spp.
- Contact sheet: [contact_sheet.jpg](contact_sheet.jpg), 16 frames ([make_contact_sheet.py](make_contact_sheet.py)).

## Cast: shot-level overrides only
The current versions stay boy 2.1.0 / girl 0.12.0, and `fidelity_baseline.json` is unchanged. The shot builds each
character from the published candidate spec plus two overrides (`production.cast`, `{"spec", "overrides"}`):

| | spec (candidate, T-122) | overrides |
|---|---|---|
| boy | `boy_yellow_hoodie.2.2.0.spec.json` (2.1.0 + T-109 face r4 + T-113 closed-lid fit, Pout) | T-118 `boy_yellow_hoodie.hair_r5.override.json` (groom/4), T-121 `hands_r2.override.json` |
| girl | `girl_auburn_bun_glasses.0.13.0.spec.json` (0.12.0 + T-109 face r4 + T-113 closed-lid fit, SmileOpen + T-115) | T-118 `girl_auburn_bun_glasses.hair_r5.override.json` (groom/4), T-121 `hands_r2.override.json` |

Also used:
- the verbs `pick_up`, `carry` and `pass`, with the T-051 / T-112c finger grasps (on with the timing profile);
- the personality reactions (scene `events`);
- the calibrated timing;
- T-120 gaze: scene `"gazeLegibility": {"rangeDeg": [16, 8]}` and the boy's `{"headPitchDeg": 10}`.

Every authored look lasts at least 11 f; `make_shot.py` refuses shorter ones. T-110 felt was not used: its fix is not
in the input.

## 1. Beats (from the bake and the expanded scene)
| Frames | Beat | Built from |
|---|---|---|
| 1-47 | He is bored: slouch (profile), `boy_unimpressed` 0.18. His fidgets: looks off f1-11, at the cup f12-22, off again f23-37. Her hand goes to her chin and back down (f5-48), and she looks at the cup. | authored looks, `girl_chin_think` |
| 24 → 47 | She looks at him (event at f24). He notices 23 f later and his lids start to lift (`boy_interested`). | `partner_acts` event, his profile delay |
| 40-81 | He looks at the cup, reaches (f57-76), grasps it (contact f77) and lifts it off the table (f82). | `pick_up`, set a, right hand |
| 64-148 | Her wonder (`girl_wonder` 0.7, WideOpen peak 0.56 at f70) while he carries the cup up (f81-97). | authored emotion, `carry` |
| 100-136 | He holds it out. She reaches (10 f) and takes the far handle (f115). **Shared hold f114-136 (22 f):** he looks at her and she looks at him, and both faces read. | `pass` with explicit receiverStart, contact and release |
| 136-153 | He lets go. She draws the cup in and looks at it. | pass release, `carry` |
| 142 → 146 | **Delight beat:** she reacts 4.5 f after the success event. `girl_delighted`, SmileOpen peaks at 0.9 at f153 and stays above half from f150 to the end. She looks at him from f153. | `success` event, her profile |
| 146 → 169 | His late, reluctant answer, 23 f after her delight: `boy_interested` and its head lift. He looks away from f176 to the end. | `partner_acts` event, authored look |

## 2. Checks (final bake)
| Check | Result |
|---|---|
| `run_shot --stages prepare,bake` | 0 warnings |
| `animcheck.py --check` | pass ([animcheck_s010.json](animcheck_s010.json)) |
| `personality.py` | no fail. Boy: 5 blinks of 4-5 f. Girl: 7 blinks of 3-4 f ([personality_s010.json](personality_s010.json)). |
| `timing.py`, expanded scene | 6 beats, 0 warnings ([timing_s010_expanded.json](timing_s010_expanded.json)) |
| `acting.py`, expanded scene | 0 warnings ([acting_s010_expanded.json](acting_s010_expanded.json)) |
| Eyes against the head ([measure_beats_s010.json](measure_beats_s010.json); e909's `measure_beats.py`) | ≤ 16.0° yaw and 8.0° pitch on both, blinks included |
| T-051 grasp ([measure_t051_s010.json](measure_t051_s010.json)) | Closed hold: tip gap 0.00 mm on both hands. Deepest point +7.7 mm (girl) and +13.0 mm (boy), so nothing is inside the cup. Thumbs opposed. Band: girl inside (margin 5.0 mm), boy 10.65 mm outside (issue 4). |
| `ctest` | passed; the renderer tests were skipped because the renderer was not built |

The expanded scene ([s010.expanded.scene.json](s010.expanded.scene.json)) was written by T-114's `dump_expanded.cpp`.
The grasp measure is T-051's `measure_t051.cpp`. Both were built as scratch tools and are not part of the build.

## 3. Remaining issues
1. **The boy's lid lift at his notice is weak (f47-80).** EyeWide peaks at only 0.39, at f106. The heavy lid still
   dominates, so "he notices" reads mostly through the look and the reach. His profile scales his reactions by 0.6,
   and this shot fires the event at salience 0.9 so that no gesture plays at the notice.
2. **Blinks on key frames.**
   - Both characters blink together at his grasp: girl f76-78, boy f77-79.
   - He blinks at her SmileOpen peak (f152-155).
   - A double blink (f171-174, f178-181) takes half of his look away. That look reads from f182 on.
   - These are life-layer blinks; nothing in the shot authors them.
3. **There is no shrug.**
   - I tried the mirrored `boy_reluctant_shrug` on his left arm, at f1 as a sigh-shrug fidget and at f126 / f144 in
     the end beat.
   - Every time, animcheck measured it on his right wrist, which travels further in the pick-up and release. It
     failed there on onset and stop step and on ease.
   - The tool picks the furthest-travelling wrist for a clip, so it cannot separate a gesture from an overlapping
     verb (the same tool limitation as T-114 §3).
   - His end beat is therefore the head lift of his late reaction plus the look away, as the task allows ("shrug or
     head lift"). No tool or threshold was changed.
4. **The boy's grasp band, f79-137.** His fingertips sit 10.65 mm outside the `side_a` band. This is the T-051 §7.1
   case, larger than e909's 3.83 mm, probably because of the cup yaw (issue 5) and hands_r2.
5. **The cup during the shared hold (f114-136).**
   - At e907's yaw of -75°, his hand hid the cup from the camera, so the table yaw is now -45°.
   - The cup wall now shows beside his hand, but about half of the cup is still covered (contact sheet f116 / f128).
6. **Some looks stop short.**
   - Her look at him (f153-192) ends at her 16° eye limit (f169), and her head stops at the 15° neck cap
     (T-120 open point 3).
   - His look at the cup in her hands (f139-175) is capped at 8° of eye pitch plus 10° of head pitch. He looks
     *towards* the cup, not at it (T-120 open point 1).
7. **Framing.** The e907 camera crops below the hips, and her bun comes close to the top edge.

## 4. Render time
- Cycles at 640x360, 16 spp, bpy 5.3.0 module on 4 CPU threads, about 31 s per frame including Blender's per-frame
  setup.
- Two `run_shot --stages render` passes:
  - f1-96: 50.2 min;
  - f69-192: 65.4 min.
- The second pass re-rendered f69-96. After the first pass, the pass's explicit `receiverStart` (her 10 f reach)
  changed her left arm from f69 on. The bake is identical to the rendered one for f1-68.
- The movie therefore uses f1-68 from the first pass and f69-192 from the second.
- Encoding: ffmpeg, libx264 crf 20, yuv420p.
- Before the final render: six previews at 480x270, 8 spp, about 36 s each, plus two more after the cup yaw change.
- Building the two candidate masters took 2 x 2.2 min; the engine bake takes 15 s.
