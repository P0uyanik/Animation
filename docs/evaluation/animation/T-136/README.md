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
  - Beyond the eyes' comfortable range, the neck and head turn first (up to 50° yaw / 40° pitch).
  - Then the torso, chest and spine (up to 25° / 25°), 3 frames after the head.
  - Once a look has settled, the chain follows a moving target without that lag.
- **Exact targets.** The eyes aim at the live target, not at the track keyed every 3 frames:
  - `atProp`: the cup's middle;
  - `atCharacter`: the midpoint of the partner's eyes, which gives held eye contact.
- **Live-target cache.** The live targets are cached per frame at load. A held prop is read through its holder's pose, so it cannot be read during evaluation. The cache is built in two passes, so two characters in eye contact each see the other's corrected head.
- **Near targets.** When the target is so close that the two eyes cannot both reach it (vergence), the head centres between them.

### Per-frame angle error, e910 (`measure_gaze_error.py`, settled part of each look, mean / max in degrees)

Each eye is measured against the exact target. Looks end where the next look, authored or generated, starts (`--expanded` T-117).

| look | frames | before (s010) | after (s010_e23) | vergence demand before → after |
|---|---|---|---|---|
| boy → cup | f100-116 | 52.4 / 52.5 | 1.2 / 3.3 | 14.8 → 30.1 |
| boy → girl | f117-138 | 37.3 / 37.6 | **0.36 / 0.78** | 9.8 → 19.0 |
| boy → cup | f139-169 | 52.2 / 52.3 | **0.38 / 0.59** | 12.1 → 28.1 |
| girl → boy | f24-51 | 23.9 / 25.5 | 1.9 / 13.5 | 9.8 → 11.8 |
| girl → cup | f52-99 | 48.8 / 52.5 | 7.7 / 12.4 | 18.8 → 45.4 |
| girl → boy | f118-132 | 32.1 / 32.4 | **0.29 / 0.29** | 9.4 → 15.9 |
| girl → cup | f133-146 | 51.9 / 52.1 | 6.3 / 6.5 | 20.2 → 43.3 |
| girl → boy | f153-192 | 24.3 / 26.7 | 1.1 / 5.4 | 10.0 → 14.8 |
| boy → girl (generated) | f48-69 | 38.5 / 39.9 | 20.5 / 36.5 | 10.0 → 24.5 |

Per-frame data: [gaze_error_before.json](gaze_error_before.json), [gaze_error_after.json](gaze_error_after.json).

### Pupil readability (`tools/review/readability.py`, shot camera, 640x360 ID masks, mean visible pupil px L / R)

| look | before (s010) | after (s010_e23) |
|---|---|---|
| boy side / table f1-37 | 31 / 20 | 9 / 13 |
| boy → cup f100-116 | 29 / 36 | 0 / 0 |
| boy → girl f117-138 | 33 / 41 | 1 / 0 |
| boy → cup f139-169 | 25 / 34 | 0 / 0 |
| boy away f176-192 | 50 / 28 | 30 / 16 |
| girl → table f1-23 | 33 / 25 | 0 / 0 |
| girl → boy f24-51 | 34 / 26 | 7 / 9 |
| girl → cup f52-99 | 30 / 23 | 1 / 1 |
| girl → boy f118-132 | 38 / 31 | 0 / 1 |
| girl → cup f133-146 | 29 / 22 | 0 / 0 |
| girl → boy f153-192 | 38 / 35 | 6 / 8 |

How often pupils fall below 8 px:

| | before | after |
|---|---|---|
| girl | 22 frames, blinks only | 151-160 frames |
| boy | blinks only | most of f100-169 |

**This is the main finding.** With the chain, the looks reach their targets, but the heads turn into profile and pitch down, away from this front camera. The pupils leave the frame's view. It is T-120's trade-off on the other side: exact gaze against readable pupils in this staging.

Files: [readability_s010/](readability_s010/), [readability_s010_e23/](readability_s010_e23/). They were made with T-123's `render_masks.py`, run through a launcher that opens the .blend first, because `tools/bpy_blender.py` ignores it.

### Open points

0. **Pupil readability: decide before using `chain` in a shot.**
   - The default caps (neck 50/40, torso 25/25) give exact looks but no pupils in e910's camera.
   - Lower per-shot caps (the `chain` object) trade one for the other.
   - A camera-aware limit is not built.
1. **Her cup looks keep 6-8°, because of vergence.**
   - Leaning in brings her eyes about 15 cm from the cup. They would then have to converge about 45°, but the ±16° range allows 32°.
   - Her eyes share the shortfall.
   - A smaller torso pitch for near targets would trade lean for convergence.
2. **Generated reaction looks (T-097D) get the chain but not the exact live target.**
   - These looks are not in the scene's actions, for example his f48-69 and f169+ looks at her.
   - Their error falls from 38° to 20°.
3. **Studio's in-app recompile keeps the live targets computed at load.** They are rebuilt on the next load.
4. **The bake costs about 5x more with the chain on** (e910: 3 s → 17 s). Per-frame JSON parsing in the face, blink and gaze settings is part of that.
5. **Not rendered beyond the ID masks.**

Tests: `tests/test_gaze_chain.cpp`.
- Parsing.
- `chain: false` gives the same pose as T-120, bit for bit.
- A steep look: T-120 is 37° off, the chain 0°.
- The torso takes part, and the eyes lead.
- A near target moves the eyes only.
- Two-character eye contact: T-120 is 58-62° off, the chain under 2.5°.
