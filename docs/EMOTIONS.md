# Body emotions (T-003, Acting Foundation stage A)

**Status:** implemented and tested on the boy (published 1.0.0, 4 facial morphs) and the girl (unpublished build,
full face library). Script-made, technical quality (owner decision Option 1). Nothing is approved.

An emotion is shared data: one file combines a face mix, a body posture, an optional gesture and timing. Any humanoid
plays it with one action. There is no per-character code, data or copy.

```
content/emotions/<name>.emotion.json --"emotion" action--> expression weights (generated morph keys)
                                                       \--> clip layers (posture, gesture; tier 1) --> bake --> Blender
```

## 1. Format `plush.emotion/1` (`content/emotions/<name>.emotion.json`)
| Field | Meaning |
| --- | --- |
| `format`, `version` | `"plush.emotion"`, `1` |
| `name`, `description` | identifiers |
| `face` | `{expression name: weight}` at intensity 1. Names are **engine expression names** (`smile`, `sad`, `angry`, `surprised`, `laugh`, `squint`, `confused`, `blink`, `browDown`, `jawOpen`, ...). They are resolved per character exactly like the `expression` action: the character's expression map, else a morph of that name. Where the engine has no name (worried, wide-open, curious), the file names the face-library preset (`Worried`, `WideOpen`, `Curious`) |
| `body` | `{clip, mask?, loop?}`: the posture clip (`content/clips/`, hold or loop). `mask` overrides the clip's body-part mask; `loop` overrides its loop flag |
| `gesture` | optional `{clip, offset, blendIn, blendOut, mirror?, face?}`: a one-shot clip `offset` seconds after the start; `face` is an optional face accent with the gesture's timing (e.g. the yawn's open jaw) |
| `timing` | `{onset, hold, release}` in seconds and `curve`: `"smooth"` (smoothstep, default) or `"linear"` |
| `variants` | `{name: patch}`: a JSON merge patch over the file (a `null` removes a key). Played as `"<name>/<variant>"` |
| `source`, `license`, `attribution` | provenance (script clips: `"script"`, `"project"`) |

Readers ignore unknown fields; the engine keeps the file as read (`EmotionDef::raw`). A new major change gets
`version` 2.

## 2. Library
| Emotion | Face (engine names) | Posture clip | Gesture | Timing (s) |
| --- | --- | --- | --- | --- |
| `happy` | smile 1.0 | `emo_happy` (hold): chest lifted, chin up, arms slightly open | — | 0.4 / 1.5 / 0.6 |
| `happy/laugh` | laugh 1.0, squint 0.3 | `emo_laugh` (loop 0.67 s): bouncing chest and head | — | 0.3 / 1.5 / 1.0 |
| `sad` | sad 1.0 | `emo_sad` (hold): slumped torso, head down, arms forward | — | 0.8 / 1.5 / 0.8 |
| `sad/cry` | sad 1.0, squint 0.6 | `emo_sob` (loop 1.2 s): deeper slump with sob heaves (no tears) | — | 0.8 / 1.5 / 0.8 |
| `angry` | angry 0.9, browDown 0.5 | `emo_angry` (hold): forward lean, head jutting, tense bent arms | — | 0.3 / 1.5 / 0.6 |
| `surprised` | surprised 1.0, jawOpen 0.25 | `emo_surprised` (hold): pulled back, hands raised | — | 0.5 / 1.2 / 0.6 |
| `confused` | confused 1.0 | `emo_confused` (hold): head tilt and turn | `gest_shrug` at 0.3 s | 0.4 / 2.2 / 0.6 |
| `afraid` | Worried 0.7, WideOpen 0.6 | `emo_afraid` (loop 0.4 s): hunched, arms guarding, tremble | — | 0.5 / 1.5 / 0.7 |
| `sleepy` | squint 0.4, blink 0.45 | `emo_sleepy` (loop 4 s): slumped, drooping, swaying head | `gest_yawn` at 0.8 s (jawOpen 0.8) | 1.0 / 3.2 / 1.0 |
| `curious` | Curious 1.0 | `emo_curious` (hold): leaning in, head tilted | — | 0.5 / 1.5 / 0.6 |

The clips are made with the T-002 tools on the neutral mannequin: `pipeline/clips/make_emotion_clips.py` (it reuses
`make_clips.py`'s pose helpers and the shared exporter; `--check` prints a forward-kinematics plausibility table).
Posture masks name only the roles a posture changes (torso, neck, head, arms); hips, legs and fingers are never in an
emotion mask. Gestures start and end in the relaxed pose.

## 3. The `emotion` action
```json
{"type": "emotion", "character": "girl", "name": "sad/cry", "start": 120, "end": 220, "intensity": 0.8}
```
- `name`: library name, optionally `/variant`; found in `content/emotions/` by walking up from the scene file.
- `end` optional: without it the emotion lasts onset + hold + release. If `end − start` is shorter than
  onset + release, both ramps share the length.
- `intensity` 0..1 (default 1) scales the face weights and the body deviation from the underlying pose.

**Compilation** (`engine/scene/actions.cpp`, `emotion.{h,cpp}`):
- **Face:** per morph, generated per-frame linear keys over the scene range = the morph's generated track so far +
  Σ (emotion weight × envelope × intensity), clamped to 0..1. Hand keys on the morph still win (generated tracks are
  a fallback).
- **Body:** the posture and the gesture become clip layers of **tier 1**, envelope = onset/hold/release (gesture:
  its own blends), weight = intensity. Emotion layers blend in the clip's own (semantic, reference-space) rotations,
  so intensity k gives k × the deviation on every role.
- **Crossfade:** when an emotion starts before the previous one of the same character has ended, the previous one
  releases from that start over (its release + the new onset) and the new onset takes the same time; without an
  explicit `end` the new emotion's end moves by the extra onset time. The sum keeps a transition no faster than the
  faster of the two ramps it replaces.

## 4. Layering (order of a character's pose)
1. Keyed and generated tracks.
2. Base clip (tier 0).
3. **Emotion postures and gestures (tier 1, by start).**
4. Clip actions (tier 2, in action order) override their masks; walk keeps hips, legs and root; hand keys win.
5. Life layer, then constraints (IK reach/touch/foot plants, hand pose, look) — they keep priority over emotions.

Without emotion actions nothing of this runs: the three s010 bakes are byte-identical with `main`.

## 5. Missing-morph rule
A face name the character cannot resolve produces **one** warning per character, emotion and name
(`SceneEvaluator::warnings()`, printed by `plush-render`), e.g.
`emotion 'sad': character 'boy' has no morph for expression 'sad' (face part skipped, body plays)`.
Nothing is invented for it; the other face names and the whole body still play. The boy 1.0.0 resolves only
`smile`, `browDown`, `jawOpen` and `blink`.

## 6. Tests and evidence
- `pipeline/clips/test_emotions.py` (AC2–AC6 on the boy and girl packages, see its docstring);
  `tests/test_emotions.cpp` (format, variants, library).
- `episodes/e902_emotion_test/shots/s010` (`pipeline/clips/make_emotion_shot.py`), sheets by
  `pipeline/clips/emotion_sheets.py`; evidence in `docs/evaluation/animation/T-003/`.

## 7. Limits (known)
- Script postures: technical quality, not acting quality; the reference videos remain the benchmark.
- Postures are mechanical holds or simple loops; the shoulder/hip pivot limit of T-002 applies (arms do not follow
  the chest bend).
- **Eyes read as closed in the Blender render whenever the head pitches down** (sad, cry, angry, afraid, sleepy,
  curious), on both characters, although the baked Blink weight is 0 and the eyes aim at the camera. Head-level or
  head-up postures render open eyes. Cause not investigated (render/master side, protected); see the T-003 report.
- The boy's face shows only smile, brow-down, jaw and blink: most emotions read through his body only.
