# T-136: blink scheduling (E2) and gaze chain (E3)

Input: `integration/r5-start` @ 37901c4. Both are opt-in scene keys. Without them, the engine behaves exactly as
before: `plush_tests` passes 215/215 plus the new cases, the golden bake test passes, and no test, threshold or golden
was changed.

Shot: [`episodes/e910_showcase/shots/s010_e23/shot.scene.json`](../../../../episodes/e910_showcase/shots/s010_e23/shot.scene.json)
is the T-117 e910 shot. It adds only the opt-in keys below.

## E2: blink scheduling (`blinkSchedule`)

```json
"blinkSchedule": {"keyBeats": [
  {"name": "grasp", "start": 72, "end": 84},
  {"name": "her_smile", "start": 148, "end": 160},
  {"name": "look_away_reads", "start": 182, "end": 192, "characters": ["boy"]}]}
```

The schedule starts from the same rhythm the face layer already uses: the personality interval on the emotion-warped
clock. Then it applies these rules (`FaceLayer::blinkPlan`):

1. A rhythm blink moves onto the nearest free gaze shift (look start) or action change within 18 f.
   - Action changes default to the character's non-look action starts, plus a pass's contact and release.
2. No blink closes the lids inside a key beat.
   - A double blink first loses its second blink.
   - If that is not enough, the blink moves to a free shift nearby, or else to just after the beat.
3. A short beat gets at most one blink, and never a double blink.
   - A short beat is the stretch between shifts, action changes and key-beat edges that is under 24 f.
4. Gaze shifts that no blink landed on keep their usual gazeShiftBlink chance.

The plan is deterministic and has random access. Characters without a face layer keep their life-layer blinks.

### e910 blink timeline (bake; a blink is a run of morph weight > 0.1 that reaches 0.5)

| | before (s010, T-117) | after (s010_e23) |
|---|---|---|
| boy | f25-28, **f76-80**, **f152-156**, **f171-174 + f178-181** | f25-28, f86-89, f141-144, f171-174 |
| girl | f32-34, f51-54, **f76-79**, f112-114, f139-142, f148-151, f181-183 | f26-28, f54-56, f86-88, f116-118, f135-137, f181-183 |

How each problem from T-117 §3.2 changed:

- **f76-79 (grasp).** Before, both characters blinked. Now neither does: both blinks move to just after the beat (f86).
- **f152-155 (her SmileOpen peak).** Before, he blinked here. Now his blink moves onto his look start at f139 (f141).
- **f171-181 (his look away).**
  - Before, a double blink took half his look away.
  - Now a single blink sits on his gaze shift at f169, a generated reaction look, and his eyes are open from f175.
  - His look-away hold (f182-192) is clean.
  - Her f181 blink is unchanged. It is her own blink, just after she reached his face.
- **Blinks on gaze shifts.** Her f26, f54 and f135 now fall on her look starts (f24, f52, f133). Her f116 falls on the
  contact at f114.

### Personality rhythm (`tools/animcheck/personality.py`, no failures before or after)

| | blinks | durations (f) | mean interval (f) |
|---|---|---|---|
| boy before / after | 5 / 4 (one double removed) | 4-5 / 4 | 48.67 / 48.67 |
| girl before / after | 7 / 6 | 3-4 / 3 | 29.8 / 31.0 |

Files:
- [blinks_before.json](blinks_before.json), [blinks_after.json](blinks_after.json): output of
  [blink_timeline.py](blink_timeline.py).
- [personality_before.json](personality_before.json), [personality_after.json](personality_after.json).

Reproduce:
1. Run `run_shot --stages prepare,bake` on s010. This gives the before bake.
2. Add the `blinkSchedule` above to `build/shot.resolved.scene.json`, then run `plush-render --bake`.

Tests: `tests/test_blink_schedule.cpp`.
- Parsing.
- Off means identical blinks.
- Key beats have zero closure.
- Blink count stays at 75% or more of the free rhythm or higher.
- Blinks land on shifts.
- At most one blink per short beat.
- The plan is deterministic.

Not done: no render. This is a bake-level change, and frames will be checked in the next render pass.
