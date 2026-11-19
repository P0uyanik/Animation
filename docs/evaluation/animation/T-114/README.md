# T-114 evidence: two-character acting scene (e909 s010)

Input `1e3ea34` (`integration/t-113`), branch `t-114-claude-two-char-acting`. Task: `docs/tasks/T-114.md`.
Engine Release build of the input (no engine change). Blender: the pinned `bpy` 5.3.0 module (Python 3.13) behind
`tools/bpy_blender.py`, as no Blender binary was available. Shot: `episodes/e909_two_char_acting/shots/s010/shot.scene.json`,
written by `episodes/e909_two_char_acting/make_shot.py`. 286 frames at 24 fps (11.9 s).

## 1. The shot
Staging, set, camera and hand-over point are the e907 ones (`episodes/e907_exchange/shots/s010_verbs`, read at run time),
so the two current rigs' natural hands and the head spacing measured in T-095 carry over. The cast is `"current"` (boy
2.1.0, girl 0.12.0). There is no `timing` key, so the calibrated default applies (T-104d), times each profile's tempo.

| Frames (bake) | Beat | Built from | Reference (T-106) |
| --- | --- | --- | --- |
| 1-57 | He is bored: he looks off to his side, `boy_unimpressed` 0.18. | authored look + emotion | PB [0, 32) heavy-lid stare; WT [0, 20) unimpressed hold |
| 12 → 16.5 | She notices the cup: `girl_wonder` and the wonder point. Her notice delay is 4.5 f; WideOpen > 0.1 at f21. | event `object_appears` (her profile) | WT [0, 39) wonder, hand at chin, rounded mouth |
| 31-57 | She looks, anticipates, reaches and grasps the far handle (contact f57). | `pick_up` L, set b | WT [22, 39) reach: 17 f, here 14 f approach + contact |
| 67-97 | She holds the cup out to him and looks at him. He glances at it (f58-71) and away again (f72-87). | `carry` + authored looks | WT [39, 61) point hold 22 f; here 20 f |
| 88 → 109 | The pass starts. He answers late (21 f, inside his 16-26 f): look at her, `boy_interested`, `boy_reluctant_shrug`. EyeWide > 0.1 at f113. | `pass` `react: true` (his `partner_acts`) | WT [60, 81) late blink and head lift (0.875 s) |
| 113-132 | He reaches and takes the near handle (contact f132). | pass receiver, grip | |
| 131 → | **Delight beat:** she smiles (`happy` 0.85, peak at f141) and looks up at him. | authored emotion + look | PB [255, 289) open smile (current cast: closed `Smile`) |
| 132-163 | **Shared hold, 31 f:** both faces read. He looks up at her (f143-161). | pass `release` explicit (T-116 note) | WT shared hold; T-116 |
| 163-195 | She lets go. He lifts the cup to eye height and looks at it. | `carry` + settle 16 | WT [87, 121) raised head hold; PB [125, 132) + 0.79 s hold |
| 195-238 | He sets it down where it stood (contact f221). | `place` (verb) | PB [151, 191) lower + release (1.00 + 0.67 s) |
| 221 → 242 | Both react. He answers late again: a look at the cup on the table and `boy_interested`. She watches the cup land, then looks up at him with her smile. | event `success` (him) + her authored looks | WT [96, 121) end hold, settled smile |
| 262-286 | A held look between them, 24 f. | authored looks | WT [87, 121) final hold (1.42 s) |

The pick-up, carry, pass and place phases (`x_t114_phases` in [s010.expanded.scene.json](s010.expanded.scene.json)) come
from the verbs. [dump_expanded.cpp](dump_expanded.cpp) (scratch, after T-112b) writes that file: the verbs expanded and
the reaction actions appended.

## 2. Choices driven by the task notes
- **Current-cast-safe faces (T-113 open point 1).** No SmileOpen and no Pout on the current cast. Her delight is the
  shared `happy` (`Smile`). `boy_reluctant` (Pout) is never used. Her `success` reaction would be `girl_delighted`, so
  on the current cast the success event names only the boy. `boy_unimpressed` is held at 0.18: its lid (blink 0.5)
  then stays under personality.py's 0.1 blink-run threshold. At 0.5 it read as a 103-frame "blink" and failed.
- **Gaze inside the range during blinks (T-113 open point 3).** The engine's default eye limits are 30° sideways and
  25° down. Both specs' `gaze_range_deg` is [16, 8]. The first bake drove the eyes to 30° / 25° during blinks, the
  e908 failure. The scene now sets `life.gaze.max*Deg` 1.5° inside the spec range, because the engine limit is soft and
  overshoots up to 1.1° here. Measured worst case during blinks: girl 15.6° / 6.5°, boy 15.0° / 6.6° (`measure_beats`).
  - A larger neck assist (35° yaw, 0.5 head follow) leaned the heads together and hid her face at the notice
    (preview round 3). So the e907 limits stay: 15° neck yaw and 0.3 head follow.
  - Far looks therefore stop slightly short of their targets: the off-side look and the look across at the partner.
    They still read in the previews.
- **Faces read in the shared hold (T-116).** His hair covered his face whenever his neck pitched down (preview round
  1: shared hold and place). Changes:
  - his neck pitch assist is 15°;
  - the cup is lifted to eye height for his look at it;
  - the shared hold is 31 f, so he can look up at her;
  - the success event is at the place contact, so his late reaction (21 f) ends before the held look.

## 3. Checks (current cast, s010)
| Check | Result |
| --- | --- |
| Bake log (`run_shot --stages prepare,bake`) | 0 warnings |
| `animcheck.py --check` | pass (exit 0) |
| `personality.py` | no fail (boy 5 blinks, 4-7 f; girl 13 blinks, 3-4 f) |
| `timing.py` on the expanded scene | 8 beats, 0 warnings ([timing_s010_expanded.json](timing_s010_expanded.json)) |
| `acting.py` on the expanded scene | 1 warning, warnings-only rule (see below) |
| T-051 measures, both hands ([measure_t051_s010.json](measure_t051_s010.json)) | closed hold: tip gap 0.00 mm on both. Deepest tip/knuckle +6.60 mm (girl) and +11.15 mm (boy), so nothing is inside the cup. Band: girl inside (margin 6.27 mm); boy 3.83 mm outside, the known T-051 §7.1 case. Thumb opposed (-24.3 / -19.5 mm). Same numbers as T-112c on e907. |
| `tests/acting/test_e909_beats.py` | 12 OK (5 data, 7 with the bake) |
| `ctest` (`plush_tests`, includes the golden bakes) | passed; renderer tests skipped (renderer not built here) |

The acting warning reads "`boy_reluctant_shrug` amplitude 0.48 (86°) > 0.3 + 0.1". It is his right-arm reach for the
cup, which starts 4 f after the shrug inside the same window. Measured over f109-140: left arm (shrug only) 0.02, right
arm 0.35. The rule cannot separate a gesture from an overlapping reach. No content change was made.

## 4. Candidate cast copy (s010_t113)
`make_shot.py --candidate` writes `shots/s010_t113` (evaluation only). It differs from s010 in two ways:
- the girl is built from her 0.12.0 spec plus `docs/evaluation/characters/T-113/candidates/girl_t113.override.json`;
- the success event also lists her, so her profile's `success` reaction plays `girl_delighted` (SmileOpen).

The boy stays current. The bake has no warnings, the same beats, and SmileOpen peaks at 0.9 at f232 (> 0.3 over
f228-275). The acting, timing and animcheck results are the same as s010.

**Which looks better:**
- Her open smile (SmileOpen) is closer to the PB f272 reference than the current closed smile. It comes at the place,
  while she watches the cup land, and her face is partly turned down there.
- In this staging, the current cast's smile at his acceptance (f150, facing him) reads more clearly as the delight beat.

So the candidate wins on the face itself (the owner's SmileOpen decision, T-113 open point 1); the s010 timing of
the beat stays the better staging. Both are in the strip.

## 5. Evidence
- Previews: Cycles at 480x270, 8 spp, single frames. Four rounds, iterated on the issues above (scratch, not kept),
  before the final render.
- [strip.jpg](strip.jpg): T-106 reference moments (WT cropped to the boy and the girl; PB reveal) above the final
  s010 frames and the s010_t113 frames ([make_strip.py](make_strip.py)).
- [e909_s010.mp4](e909_s010.mp4): Cycles, 640x360, 16 samples (the shot's `production.render`), all 286 frames.
  - Rendered in two `run_shot --stages render` passes: f1-218, then f219-286 (the first pass hit the session's 2 h
    background limit).
  - About 25 s per frame on 4 CPU threads, plus about 28 min of per-frame Blender setup for the full range.
  - Encoded with ffmpeg (libx264, crf 20, yuv420p).
- Candidate frames f232 and f275: single-frame renders at the same settings.
- Measures: [measure_beats_s010.json](measure_beats_s010.json), [measure_beats_s010_t113.json](measure_beats_s010_t113.json),
  [personality_s010.json](personality_s010.json), [animcheck_s010.json](animcheck_s010.json),
  [acting_s010_expanded.json](acting_s010_expanded.json).

## 6. Not used / open
- **T-120 `gazeLegibility`** (Supervisor note, 2026-11-19) is not in this input's engine (`1e3ea34`), so it is not
  used. This shot's eye limits (section 2) serve the same purpose at the scene level.
- The acting rule's gesture amplitude counts an overlapping reach (section 3). It is a tool limitation; no content
  change was made.
- A SmileOpen / Pout decision for the next published versions would let s010 use `girl_delighted` (section 4).
