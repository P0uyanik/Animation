# T-097-boy · boy acting (boy_yellow_hoodie 2.0.0)

Personality target: subtle, low energy, delayed interest, sideways glances, small mouth changes, reluctant gestures.
Reference first: every timing and face value below is read from the T-106 boy rows
(`docs/evaluation/animation/T-106/performance.csv`), mainly watertable (WT), where the girl points beside him.
Status: implemented and tested on the current boy (2.0.0); not approved (the owner reviews the clip and strip).

## Evidence
- `e908_boy_acting_s010.mp4`: Cycles (bpy 5.3.0, CPU), 640×360, 16 samples, the whole shot (f1-f173, 7.2 s), encoded
  with ffmpeg (x264, crf 23). Frames f51-f95 are rendered from the final shot (reaction generated from `events`); the
  other frames come from the first render (explicit reaction actions), whose bake differs from the final one only in
  f51-f95 (bones) and by ≤ 7 mm of hair dynamics elsewhere. f60-f70 rendered both ways differ in < 0.7 % of the pixels
  (hair strands). The first render ran in four run_shot chunks (a container restart killed the single run).
- `strip_vs_watertable.jpg`: top row the reference moments (WT f20, f50, f62, f81, f110), bottom row the same beats of
  e908 (f20, f45, f53, f72, f112 shrug, f165); f45 lands on a life blink (f43), from the Cycles frames.
- `acting.json`, `personality.json`, `timing.json`, `animcheck.json`: the animcheck reports of the final bake.
- Cheap previews (Cycles 8 spp, 480×270, single frames) were used while iterating; not committed.

## The shot (`episodes/e908_boy_acting/shots/s010`, written by `make_shot.py`)
Notice → reaction → gesture → hold to an event, against the WT moment of the girl's point:

| WT (T-106) | he does | e908 (scene frames) |
| --- | --- | --- |
| [0, 27) | leans, brows low, mouth nearly closed | f1-f30 bored stare at the cup (heavy lids, head down) |
| f39 | the girl's point arrives (reach [22, 39)) | f30 `events`: `partner_acts` (off screen) |
| [27, 60) 33 f | holds the same sidelong watch | f30-f51: nothing changes (21 f notice delay) |
| [60, 68) blink; [60, 81) head lifts, ~5° CCW roll | late answer | f51 blink + 11 f sidelong glance (eyes); `boy_interested` rises over 21 f |
| [81, 87) blink in the settle | | life blink f85 |
| (no gesture shown) | | f51 clip start; arm moves f84-f133 `boy_reluctant_shrug` (extrapolation) |
| [87, 121) 34 f hold, raised head, small closed mouth | | f139-f173 34 f end hold |

The reaction is generated from the scene `events` (T-097D): the planner reads `reaction.delay_frames` (middle 21 f)
and `reaction.events.partner_acts` (boy_interested at 0.7 × `intensity_scale` 0.6, duration 5.0 s, gaze shift 0.2,
`boy_reluctant_shrug`) and plays the emotion and the gesture at the notice frame (f51). Because the planner starts
the gesture with the emotion, the reluctant beat is in the clip: a 33 f rest lead (the head lift rises 21 f and settles
10 f first) and a 14 f rest tail (the layer blends out over rest). The event has no source (the partner is off
screen, there is nothing to look at), so no look is generated; the blink and the 11 f sidelong glance at the notice are
authored, as WT shows them. `partner_acts.duration_s` 5.0 keeps the raised head through the shrug and the end hold (WT
holds it to the clip's end). The checks below read the scene with the generated actions appended (as T-097D
documents); the signature tests mirror them and check them against the bake.

## Data (each value's source is in the file)
| File | What |
| --- | --- |
| `content/personality/boy_yellow_hoodie.json` | `reaction.delay_frames` [16, 26], `intensity_scale` 0.6, `gaze_shift` 0.3, `gesture_min_intensity` 0.4, `events` (partner_acts, object_appears, success, failure); T-106 citations added to hold, blink, gaze and attention sources; the shrug in `gestures` |
| `content/emotions/boy_interested.emotion.json` | delayed, low-key interest: lids lift, brows down, lips part, no smile; onset 0.875 s / hold 1.42 s (WT [60, 81) / [87, 121)); face authored for his expressed intensity 0.42 → JawOpen 0.034 (PB [259, 289) median 0.033) |
| `content/clips/boy_head_lift.clip.json` | the emotion's posture: slight lift + ~5° CCW roll at 0.42 (WT [60, 81)) |
| `content/clips/boy_reluctant_shrug.clip.json` | the shared `gest_shrug` at 0.45 of its swing, right arm + chest only, re-timed: 33 f rest lead, slow rise (30 f), dwell, quicker fall (8 f), 14 f rest tail; flat mouth, no brow raise |
| `episodes/e908_boy_acting/make_clips.py` | writes both clips from the library clips (no Blender) |

`reaction.delay_frames` [4, 8] → [16, 26] (measured: WT f39 → f60 = 21 f; the Supervisor relaxed the
`tests/test_personality.cpp` pin in 0a7297a). Values **not** tuned because shared tests pin them:
- `blink.duration_frames` [4, 6] (test pins the 5 f middle). T-106 envelopes are 6-8 f including partly closed frames.
- `blink.interval_frames.mean` 30 (pinned; T-106 WT spacings 40 / 21 f → 30.5 f agree).

## Checks (final bake, `run_shot --stages prepare,bake`; scene with the generated reaction actions appended)
| Check | Result |
| --- | --- |
| `tools/animcheck/acting.py` (T-097C) | 0 warnings; glance 21 f after the event (≥ 16); shrug amplitude 0.099 (18°) ≤ 0.30; longest still run 96 f ≥ 12 |
| `tools/animcheck/personality.py` | 0 failures; 6 blinks 4-6 f, mean interval 31.7 f; idle median 0.0013 H/f ≤ 0.004 |
| `tools/animcheck/timing.py` | 0 warnings |
| `tools/animcheck/animcheck.py --check` | pass |
| `tests/acting/test_boy_signature.py` | 15 tests OK (a fresh bake: acting / personality on it, and the generated reaction at the planned frames) |
| `plush_tests` (with T-097D and its 12 f look turn-in, 00b4019) | 168/168 |

## Deviations from the references and limitations
- **Hands**: in WT he leans on the rim with both hands on it (`posture.rest_hands`); here his arms hang from the
  idle (no rim-rest pose exists in the clip library; a hand-on-rim hold would also block the shrug). The face, gaze,
  lids and head timing follow the reference; the body rest pose does not.
- The stimulus is off screen (no partner in a solo shot); the prop does not change.
- The shrug is invented (no gesture in the references), kept small, slow and in his base tempo (owner decision
  2026-11-17).
- Wrist speed during the shrug alternates by about ±1.5 mm/f frame to frame; it does not come from the clip (smoothing
  the clip keys did not change it), so it is engine-side and within the animcheck thresholds.
- While the shrug layer blends in at the notice frame it holds the chest and right arm at the idle's frame-0 pose:
  a ≤ 2.8 mm/f settle in f51-f61, during the blink and glance.
