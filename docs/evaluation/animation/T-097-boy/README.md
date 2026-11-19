# T-097-boy · boy acting (boy_yellow_hoodie 2.0.0)

Personality target: subtle, low energy, delayed interest, sideways glances, small mouth changes, reluctant gestures.
Reference first: every timing and face value below is read from the T-106 boy rows
(`docs/evaluation/animation/T-106/performance.csv`), mainly watertable (WT), where the girl points beside him.
Status: implemented and tested on the current boy (2.0.0); not approved (the owner reviews the clip and strip).

## Evidence
- `e908_boy_acting_s010.mp4`: Cycles, 640×360, 16 samples, the whole shot (f1-f179, 7.5 s).
- `strip_vs_watertable.jpg`: top row the reference moments (WT f20, f50, f62, f81, f110), bottom row the same beats of
  e908 (f20, f45, f53, f72, f160), from the Cycles frames.
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
| (no gesture shown) | | f82-f133 `boy_reluctant_shrug` (extrapolation) |
| [87, 121) 34 f hold, raised head, small closed mouth | | f145-f179 34 f end hold |

The reaction is authored as explicit actions with the values the profile plans (`reaction.events.partner_acts`:
emotion, intensity 0.7 with `intensity_scale` 0.6, gaze shift 0.2, gesture) because T-097D (scene events → reaction
playback) had not landed at the input SHA. **When T-097D lands, this shot's `events` key may also schedule the planned
reaction on top of the explicit one**: the scene then needs its explicit reaction actions removed (or T-097D's opt-out);
not done here (T-097D is not on this branch).

## Data (each value's source is in the file)
| File | What |
| --- | --- |
| `content/personality/boy_yellow_hoodie.json` | `reaction.intensity_scale` 0.6, `gaze_shift` 0.3, `gesture_min_intensity` 0.4, `events` (partner_acts, object_appears, success, failure); T-106 citations added to hold, blink, gaze and attention sources; the shrug in `gestures` |
| `content/emotions/boy_interested.emotion.json` | delayed, low-key interest: lids lift, brows down, lips part, no smile; onset 0.875 s / hold 1.42 s (WT [60, 81) / [87, 121)); face authored for his expressed intensity 0.42 → JawOpen 0.034 (PB [259, 289) median 0.033) |
| `content/clips/boy_head_lift.clip.json` | the emotion's posture: slight lift + ~5° CCW roll at 0.42 (WT [60, 81)) |
| `content/clips/boy_reluctant_shrug.clip.json` | the shared `gest_shrug` at 0.45 of its swing, right arm + chest only, re-timed: slow rise (30 f), dwell, quicker fall (8 f); flat mouth, no brow raise |
| `episodes/e908_boy_acting/make_clips.py` | writes both clips from the library clips (no Blender) |

Values **not** tuned because shared tests pin them (asked the Supervisor; not changed here):
- `reaction.delay_frames` stays [4, 8] (`tests/test_personality.cpp:410-411`). T-106 measures 21 f (WT f39 → f60); the
  shot plays 21 f explicitly. Proposed value: [16, 26].
- `blink.duration_frames` [4, 6] (test pins the 5 f middle). T-106 envelopes are 6-8 f including partly closed frames.
- `blink.interval_frames.mean` 30 (pinned; T-106 WT spacings 40 / 21 f → 30.5 f agree).

## Checks (final bake, `run_shot --stages prepare,bake`, plush-render bake)
| Check | Result |
| --- | --- |
| `tools/animcheck/acting.py` (T-097C) | 0 warnings; glance 21 f after the event (≥ 4); shrug amplitude 0.10 (18°) ≤ 0.30; longest still run 96 f ≥ 12 |
| `tools/animcheck/personality.py` | 0 failures; 6 blinks 4-6 f, mean interval 31.7 f; idle median 0.0013 H/f ≤ 0.004 |
| `tools/animcheck/timing.py` | 0 warnings |
| `tools/animcheck/animcheck.py --check` | pass |
| `tests/acting/test_boy_signature.py` | 14 tests OK (includes a fresh bake + acting / personality on it) |

## Deviations from the references and limitations
- **Hands**: in WT he leans on the rim with both hands on it (`posture.rest_hands`); here his arms hang from the
  idle (no rim-rest pose exists in the clip library; a hand-on-rim hold would also block the shrug). The face, gaze,
  lids and head timing follow the reference; the body rest pose does not.
- The stimulus is off screen (no partner in a solo shot); the prop does not change.
- The shrug is invented (no gesture in the references), kept small, slow and in his base tempo (owner decision
  2026-11-17).
- Wrist speed during the shrug alternates by about ±1.5 mm/f frame to frame; it does not come from the clip (smoothing
  the clip keys did not change it), so it is engine-side and within the animcheck thresholds.
