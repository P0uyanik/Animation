# T-097-girl · The girl's acting (girl_auburn_bun_glasses 0.11.0)

Cheerful and alert: quick glances, hand to chin, pointing, and an open "delighted" smile as an acting beat; her rest
face stays the modelled closed gentle smile. Everything is character data (profile, clips, emotions) plus one solo
shot; no shared code, shared test or other character was changed by this task.

Clip: [e908_s010.mp4](e908_s010.mp4) (Cycles, 640×360, 16 samples, 156 frames @24) ·
strip: [strip.jpg](strip.jpg) (reference moments above, e908 below) · cheap previews first (Cycles 8 samples,
480×270): [preview_strip.jpg](preview_strip.jpg) (eight key frames of the first full pass: the camera at 16° and the
lean hid her face at the point and the delight, the cup stood in front of the hand) and
[preview_after_fixes.jpg](preview_after_fixes.jpg) (f040 wonder, f100 delighted with the camera at 7° and the glance up).

## The shot: `episodes/e908_girl_acting/shots/s010`
`make_shot.py` writes it (cast `"current"`, girl 0.11.0). She stands at a small table with a felt cup. Beats (scene
frames @24, also in the shot as `x_t097_girl.beats`):

| Frames | Beat | Reference |
| --- | --- | --- |
| 1–16 | alert, looking off to her left; closed rest smile | — |
| 13 | **event** `object_appears` (the cup; scene `events`) | — |
| 17 | **notice**: eyes to the cup (3-frame saccade, head follows) = event + 4 f | `reaction.delay_frames` 4–6 (T-104 reaction delay 4–10 f, alert: the low end) |
| 19 | **reaction**: `girl_wonder` (eyes wide, brows up, rounded mouth) + `girl_wonder_point` starts | WT [0, 15) |
| 35–50 | hand at the chin, wonder | WT [0, 15) 15 f |
| 50–57 | leaves the chin | WT [15, 22) 7 f |
| 57–74 | **gesture**: leans in and points down at the cup | WT [22, 39) 17 f |
| 74–96 | holds the point (the rounded mouth closes) | WT [39, 61) 22 f |
| 86 | **event** `success` during the hold | — |
| 90 | **delighted**: `girl_delighted` (open smile) = event + 4 f | PB [255, 289) wide open smile |
| 92 | a quick glance up to the camera, sharing the delight (invented: WT keeps the eye line low until f081) | — |
| 96–116 | draws the hand back | WT [61, 81) 20 f |
| 116–131 | straightens | WT [81, 96) 15 f |
| 131–156 | end hold upright, arms down; the open smile has released into the closed rest smile by f136 | WT [96, 121) 25 f |

Explicit emotion / clip / look actions: T-097D (scheduling reaction plans from scene `events`) had not landed; the
profile's `reaction.events` carry the same choices for the planner (below).

## Files
| File | What |
| --- | --- |
| `content/personality/girl_auburn_bun_glasses.json` | tuned toward T-106 (table below); every record names its source |
| `content/emotions/girl_wonder.emotion.json` | wonder: `WideOpen` 0.8 (eyes wide, brows up, rounded mouth), jaw 0.1, `emo_curious` posture; 0.25 s onset |
| `content/emotions/girl_delighted.emotion.json` | the acting-beat open smile: engine `smile` 1.0 = the model's open Smile preset, brows up, light squint, `emo_happy` torso (no arms: the gesture keeps them); releases over 0.8 s |
| `content/clips/girl_chin_think.clip.json` | rest → hand to chin (14 f) → hold 15 f → lower |
| `content/clips/girl_point_down.clip.json` | rest → lean and point down 17 f → hold 22 f → draw back 20 f → straighten 15 f |
| `content/clips/girl_wonder_point.clip.json` | the watertable signature in one clip (rise, WT [0, 96) beats); used in e908 |
| `episodes/e908_girl_acting/` | `make_shot.py`, `make_girl_clips.py` (Blender, shared clip helpers read-only), `girl_arm_ik.py` (pose solver on her proportions), `girl_beats.py` (beat table shared by clips and shot), `calibrate_clips.py` + `clip_calibration.json`, `measure_girl.py`, the shot |
| `tests/acting/test_girl_signature.py` | 20 signature tests (data always; bake checks when a bake exists, the library-clip check also needs the engine build) |
| this folder | evidence: reports of the final bake (`acting.json`, `personality.json`, `animcheck.json`, `timing.json`, `e908_measure.json`), `make_strip.py`, clip, strips |

## Profile values and sources
| Value | Before | Now | Source |
| --- | --- | --- | --- |
| `reaction.delay_frames` | [2, 4] (extrapolation) | [4, 6] | T-104 `reaction_delay` 4–10 f; alert → low end |
| `reaction.tempo_scale` | — | 0.9 | quick (brief; T-104 `beat_scale` 0.85); planned delay 5 × 0.9 = 4.5 f ≥ 4 |
| `reaction.gaze_shift` | — | 0.9 | T-106: every WT/PB gaze row of hers is on the task (`fixation_on_task` 0.9) |
| `reaction.gesture_min_intensity` | — (0.35) | 0.3 | WT [0, 15): the hand goes to the chin at a mild wonder |
| `reaction.hold_scale` | — | 1.25 | T-104 `hold_scale`; T-106 point hold 0.92 s, end hold 1.04 s |
| `reaction.events` | — | object_appears → girl_wonder + `girl_wonder_point`; partner_acts → curious + `girl_point_down`; success → girl_delighted (gaze 0.6) | T-106 WT [0, 61), PB [255, 289) |
| `reaction.delighted_style` | — | text | PB [255, 289); owner decision 2026-11-17 (open smile = Happy) |
| `gaze.saccade_interval_s` | [0.8, 2.0] (estimate) | [0.6, 2.5] | T-106 girl gaze segments 0.29–2.46 s (median 0.85 s) |
| `attention.glance_hold_frames` | [12, 24] (extrapolation) | [7, 24] | T-106 PB [125, 132) 7 f, WT [81, 96) 15 f |
| `tempo.reference_beats` (new, data) | — | 15 / 7 / 17 / 22 / 20 / 15 / 25 f | T-106 WT acting beats; = `girl_beats.py` |
| `tempo.reach_frames` | [8, 10] | unchanged | pinned by `tests/test_personality.cpp`; T-104 10 f; the T-106 17 f includes the lean (note in the source) |
| `blink.interval_frames` / `duration_frames` | 33 / [3, 5] | unchanged (sources extended) | pinned by `tests/test_personality.cpp`; T-106 rate 35.7/min = 40 f is set per shot (e908 `blinkInterval` 1.667 s) |
| `limits.blink_interval_frames` | [25, 39] | [25, 40] | T-106 rate interval 40 f |
| `limits.gesture_amplitude_max` | — (energy 0.6) | 0.6 | WT full-arm point; e908 measured 0.54 |
| `gestures` | names | + `clip` per entry, + `wonder_point` | the three girl clips |

## Results (round 1: the rendered run; the report JSONs in this folder are round 2)
| Check | Result |
| --- | --- |
| T-097C acting (`tools/animcheck/acting.py`) | 0 warnings; notice delays 4 f (object_appears) and 6 f (success, the glance at f92) ≥ 4; gesture amplitude 0.54 ≤ 0.6; longest still hold 44 f (f112–f156) ≥ 15 |
| T-053 personality limits (`personality.py`) | pass: 4 blinks, mean interval 30.3 f in [25, 40], durations 3 f; idle 0.0040 H/f |
| T-061 animation metrics (`animcheck.py --check`) | pass: peak rotation step 42.2 °/f (limit 45), entry jerk 0.345 (limit 0.45), overshoot 0.1 %, settle 4 f |
| T-104 timing (`timing.py`) | 0 warnings |
| hand at chin (wonder hold f37–f49) | knuckles 26 mm mean (max 28) from the chin point under her chin: the curled fingers rest against it (round 2: 36 mm, 37.6 max) |
| index at the cup (point hold) | 1.1° mean (max 2.7°) off the cup |
| delighted mouth | `Smile` 0 before the success event, 0.9 in the beat, 0 from f136 to the end (closed rest smile) |
| engine warnings (bake log) | none (an earlier `blinkInterval` of 1.6667 s rounded above the 40 f limit and was clamped with a warning; now 1.6666 s) |
| library clips `girl_chin_think`, `girl_point_down` on her package (`animcheck.py --check`) | pass (the lower of `girl_chin_think` needed 18 f and a stronger ease, it failed `ease_out` / `stop_step` at 14 f) |

Commands: `python3 tests/acting/test_girl_signature.py` (20 OK with the bake and the engine build; 16 + 4 skipped without a bake), `build/tests/plush_tests`
(157/157), `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` (all PASS, acting
0 warnings), `python3 pipeline/clips/tests/test_clip_files.py --selftest` (the girl clips PASS).

## Findings and limits
- **Hand to chin vs the T-047 clip-arm lift.** Her arms are 0.18 m and her vest is full. A pose whose forearm crosses
  in front of the chest is turned out about the shoulder by the engine's clip-arm lift (the collision body), which put
  the hand 5–7 cm off the chin. The solver keeps forearm and wrist 0.14 m in front of the body with the elbow at
  shoulder height; the knuckles then rest ~2.5 cm in front of the chin point (fingers curled against it). A raised
  elbow is the cost; WT's lower elbow is not reachable on this rig without entering the body.
- **Point direction is staged, not forced.** The cup is placed where her held index ray meets the table
  (`calibrate_clips.py --place-cup`), so the arm keeps a natural straight-ahead point.
- **Clip tempo.** The girl's gesture clips play 1.1× (`tempo.action_speed`); the clips are authored at the reference
  durations × 1.1, so playback matches the T-106 frame counts.
- **Invented:** the 14 f rise to the chin (WT starts at the chin), the opening look to her left, the glance to the
  camera at the delight (WT keeps the eye line low until f081), and the success event itself (no prop animation in
  the scene format; the cup does not change).
- Blinks are generated by the life layer (coupled to action changes); their frames do not copy WT's f015/f054/f079.
- `tests/acting/test_girl_signature.py` is not yet in `tools/check_all.py`'s list (shared file; Supervisor).

## Round 2: reactions from scene `events` (T-097D)
The shot now keeps its `events` (with `kind`) and lets T-097D play them from the profile; the explicit actions that
duplicated them are gone (the notice look, `girl_wonder`, `girl_wonder_point`, `girl_delighted`). Authored remain only
what the planner cannot produce: the opening look off to her left, the sustained watch of the cup while she points (a
planned look lasts at most its reaction: `gaze_shift` <= 1) and the glance up to the camera at the success (the
success event has no source, so no planned look). The planner looks only at characters and scene objects, so the cup
event's source is `cup_spot`, a small box standing inside the cup (hidden by its wall).

Profile and girl-file tuning so the beats land as in the round-1 strip: `reaction.events.object_appears.duration_s`
1.5 -> 1.2 s (x tempo 0.9 x hold 1.25 = 32 f: the wonder releases at f062, before the point lands at f072, as WT
closes the mouth in [39, 61)); `girl_wonder` posture masked to spine and chest (the blended `emo_curious` tilted her
head 4 deg further forward and moved her chin 8 mm off the hand). Planned actions (engine) = the shot's recorded
`x_t097_girl.planned_reactions`: look 17.5-49.9 at `cup_spot`, `girl_wonder` 17.5-61.9 (0.7, blended), clip
`girl_wonder_point` at 17.5, `girl_delighted` 88.5-145.5 (0.9, blended). The reactions now start 1.5 f earlier than in
round 1 (planned delay 4.5 f instead of 4 + 2).

Checks on the scene as it plays (authored + planned actions): acting 0 warnings (glances 4.5 f and 6 f after the
events, gesture amplitude 0.545, still hold 44 f), personality pass, timing 0 warnings, animcheck `--check` pass,
hand at chin 36 mm mean (37.6 max), no engine warnings; `tests/acting/test_girl_signature.py` 21 OK; gate PASS.
`plush_tests` all pass after merging `integration/t-097-girl` 085e6a1 (the Supervisor's fix to
`tests/test_reaction_playback.cpp`: the girl's planned gesture follows its emotion).

Evidence: [preview_round2.jpg](preview_round2.jpg) (Cycles 8 samples, eight key frames) and
[strip_round2_preview.jpg](strip_round2_preview.jpg) (the reference strip with the round-2 preview frames). The poses
and beats are the round-1 ones (1.5 f earlier, slightly less head tilt in the wonder), so the round-1 Cycles clip
`e908_s010.mp4` was not re-rendered.

## Strip notes (round 1)
- e908 f066 is mid-lean (the hand is leaving the chin towards the point); WT f030 is already further into the point:
  e908 starts the sequence with an invented 14 f rise to the chin, so its point lands at f074 (WT f039 + 35).
- The open smile reads (f100); her mouth at the end hold is the modelled closed smile (f150), as at WT f110.
- Render: two runs of one bake (frames 1-77, then 78-156 after a background time limit; frame data identical),
  joined with ffmpeg (24 fps, x264 crf 22).

ledger: build 6 · render 72 · tests 6 · ci 0 · wait 0 (min) (round 1)
ledger: build 3 · render 3 · tests 6 · ci 0 · wait 0 (min) (round 2)
