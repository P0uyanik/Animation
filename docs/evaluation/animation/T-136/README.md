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

## E3: gaze chain (`gazeLegibility.chain`)

```json
"gazeLegibility": {"rangeDeg": [16, 8], "chain": true}
```

The chain is optional. Without it, T-120 is unchanged, and a test checks this bit for bit. With it on:

- **Order of movement.** The eyes still lead.
  - Beyond the eyes' share (default 4° yaw / 3° pitch), the neck and head turn (default up to 25° / 10°).
  - Then the torso, chest and spine (default up to 5° / 3°), 3 frames after the head.
  - The eyes are held within their share + 2° (darts included), so pupils stay near centre.
  - Once a look has settled, the chain follows a moving target without that lag.
- **Exact targets.** The eyes aim at the live target, not at the track keyed every 3 frames:
  - `atProp`: the cup's middle;
  - `atCharacter`: the midpoint of the partner's eyes, which gives held eye contact.
- **Live-target cache.** The live targets are cached per frame at load. A held prop is read through its holder's pose, so it cannot be read during evaluation. The cache is built in two passes, so two characters in eye contact each see the other's corrected head.
- **Near targets.** When the target is so close that the two eyes cannot both reach it (vergence), the head centres between them.

### Default caps: sweep on e910 (owner: readable eyes first)

The first default (eyes T-120's range, neck 50/40, torso 25/25) reached the targets (0.3-8°) but hid the pupils (girl < 8 px on 151-160 frames). Two lower settings were swept (eyeShare y/p, neck y/p, torso y/p):

| setting | girl frames < 8 px outside blinks | girl / boy min px outside blinks | result |
|---|---|---|---|
| before (s010, T-120) | 0 | 22 / 13 | |
| wide (first default) | 10 (+ most of the shot near 8) | 2 / 7 | rejected |
| A: 6/4, 30/14, 8/4 | 6 | 5 / 8 | fails |
| **C: 4/3, 25/10, 5/3** | **0** | **24 / 18** | **now the default** |

### Per-frame angle error, e910 (`measure_gaze_error.py`, settled part of each look, mean / max in degrees)

Each eye is measured against the exact target. Looks end where the next look, authored or generated, starts (`--expanded` T-117).

| look | frames | before (s010) | after (default C) | wide caps |
|---|---|---|---|---|
| boy → cup | f100-116 | 52.4 / 52.5 | 47.8 / 48.0 | 1.2 / 3.3 |
| boy → girl | f117-138 | 37.3 / 37.6 | 32.6 / 33.2 | 0.36 / 0.78 |
| boy → cup | f139-169 | 52.2 / 52.3 | 46.8 / 47.1 | 0.38 / 0.59 |
| girl → boy | f24-51 | 23.9 / 25.5 | 16.9 / 19.1 | 1.9 / 13.5 |
| girl → cup | f52-99 | 48.8 / 52.5 | 45.3 / 50.0 | 7.7 / 12.4 |
| girl → boy | f118-132 | 32.1 / 32.4 | 25.9 / 26.3 | 0.29 / 0.29 |
| girl → cup | f133-146 | 51.9 / 52.1 | 47.9 / 48.4 | 6.3 / 6.5 |
| girl → boy | f153-192 | 24.3 / 26.7 | 17.7 / 19.9 | 1.1 / 5.4 |

The readable default gains only 4-7°. In this staging the targets are 35-50° off the head, beyond 25° of neck and 5° of torso. Exact looks need the wide caps, given per shot as a `chain` object.

Per-frame data: [gaze_error_before.json](gaze_error_before.json), [gaze_error_after.json](gaze_error_after.json) (default C), [gaze_error_wide.json](gaze_error_wide.json).

### Pupil readability (`tools/review/readability.py`, shot camera, 640x360 ID masks, mean visible pupil px L / R)

| look | before (s010) | default C | wide caps |
|---|---|---|---|
| boy side / table f1-37 | 31 / 20 | 26 / 25 | 9 / 13 |
| boy → cup f100-116 | 29 / 36 | 39 / 32 | 0 / 0 |
| boy → girl f117-138 | 33 / 41 | 43 / 34 | 1 / 0 |
| boy → cup f139-169 | 25 / 34 | 34 / 27 | 0 / 0 |
| boy away f176-192 | 50 / 28 | 58 / 53 | 30 / 16 |
| girl → table f1-23 | 33 / 25 | 27 / 33 | 0 / 0 |
| girl → boy f24-51 | 34 / 26 | 29 / 36 | 7 / 9 |
| girl → cup f52-99 | 30 / 23 | 24 / 30 | 1 / 1 |
| girl → boy f118-132 | 38 / 31 | 31 / 36 | 0 / 1 |
| girl → cup f133-146 | 29 / 22 | 23 / 29 | 0 / 0 |
| girl → boy f153-192 | 38 / 35 | 32 / 39 | 6 / 8 |

Files: [readability_s010/](readability_s010/), [readability_s010_e23/](readability_s010_e23/) (default C), [readability_sweepA/](readability_sweepA/), [readability_s010_e23_wide/](readability_s010_e23_wide/). They were made with T-123's `render_masks.py`, run through a launcher that opens the .blend first, because `tools/bpy_blender.py` ignores it.

### Open points

0. **Readable default against reach.** In e910, the default keeps the pupils but gains only 4-7°. Wide caps (`"chain": {"neckYawDeg": 50, "neckPitchDeg": 40, "torsoYawDeg": 25, "torsoPitchDeg": 25, "eyeShareDeg": [90, 90]}`) reach the targets and lose the pupils. Restaging the camera or the characters would get both; a camera-aware limit is not built.
1. **Vergence on near targets** (wide caps): her cup looks keep 6-8°.
2. **Generated reaction looks (T-097D) get the chain but not the exact live target.**
3. **Studio's in-app recompile keeps the live targets computed at load.** They are rebuilt on the next load.
4. **The bake costs about 5x more with the chain on** (e910: 3 s → 16-17 s). Accepted for now. Per-frame JSON parsing in the face, blink and gaze settings is part of that.
5. **Not rendered beyond the ID masks.**

Tests: `tests/test_gaze_chain.cpp`.
- Parsing.
- `chain: false` gives the same pose as T-120, bit for bit.
- A steep look: T-120 is 37° off, the chain 0°.
- The torso takes part, and the eyes lead.
- A near target moves the eyes only.
- Two-character eye contact: T-120 is 58-62° off, the chain under 2.5° (wide caps).
- Default caps: the eyes stay within their share + 2°, and the head takes more of the turn than T-120.
