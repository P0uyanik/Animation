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

## 3b. Blended emotions: a continuous state (T-097A, opt-in)
An emotion action with `"blend"` plays from the character's **continuous emotion state** (`EmotionState`,
`engine/scene/acting.h`) instead of its own envelope. Actions without `blend` (and every existing file, shot and bake)
take the path of section 3 unchanged.
```json
{"type": "emotion", "character": "girl", "name": "surprised", "start": 18, "blend": true,
 "affect": {"pleasantness": 0.2, "energy": 0.9}, "modulation": {"tempoScale": 1.3, "intensityScale": 0.8}}
```
| Field | Meaning |
| --- | --- |
| `blend` | `true` or `{rise?, decay?, keep?}`: rise / decay in seconds (default: the file's `blend.rise` / `blend.decay`, else `timing.onset` / `timing.release`); `keep: true` plays on top of the other blended emotions instead of replacing them |
| `affect` | optional `{pleasantness, energy}` (-1..1) of this emotion; default: the file's `affect`, else 0 |
| `modulation` | optional `PersonalityModulation` (`intensityScale`, `tempoScale`, `holdScale`, `gazeShift`, `preferredGestures`); chosen by T-097B, applied here |
| `end`, `intensity` | as in section 3: the release starts `decay` before `end` (without `end`: after rise + hold) |

Optional file fields (format stays `plush.emotion/1`; plain play ignores them): `"blend": {"rise", "decay"}` and
`"affect": {"pleasantness", "energy"}`. No library file sets them today.

**State dynamics** (`EmotionChannel`, `EmotionBlender` in `engine/scene/emotion.{h,cpp}`): every emotion weight
(0..1), the pleasantness and the energy (-1..1) are channels. A blended action re-targets, at its start, its own weight
to its intensity over its rise time and (unless `keep`) every other blended emotion of the character to 0 over that
emotion's decay time; at its release it re-targets its weight to 0 over its decay (skipped if something re-targeted it
in between). Pleasantness and energy move to the weight-averaged affect of the target weights (scaled down when the
weights sum to less than 1). A move is a cubic Hermite segment from the current value **and velocity** to the target,
arriving at rest: from rest it is exactly the smoothstep ramp of plain emotions, and a move re-targeted mid-way keeps
value and velocity (C1, no jump, no kink). Rise is used when the value increases, decay when it decreases. Values are
clamped to the channel's range.

**What reads the state** (sampled once per scene frame, Catmull-Rom between frames, which is C1 where secondary motion samples):
- **Face:** per morph, Σ (state weight × face weight) on top of the morph's track, like section 3.
- **Posture:** one tier-1 layer per blended emotion for the whole range (`ClipLayer::sampled`). The per-frame state
  weights become sequential override weights (`overrideWeights`), so the postures give the normalized blend
  (1 − S) × underlying pose + Σ wᵢ × postureᵢ, whatever their order. Blended postures share their start, so they apply
  below every later gesture.
- **Gaze and living face:** the emotion's `faceMotion` × its state weight (gaze bias, blink rhythm, eye darts,
  channels); `attention` pulses at every start of the emotion (× intensity).
- **Tempo:** posture clip clocks integrate (1 + 0.25 × energy) / tempoScale (`emotionTempo`, `kEnergyTempo`), so a
  loop speeds up or slows down with the state without a phase jump. Gestures play at the tempo of their start.

**Personality modulation** (applied, not chosen; `modulatedTiming`): intensity × `intensityScale` (clamped to 1);
rise, decay, gesture offset and gesture blends × `tempoScale`; hold × `tempoScale` × `holdScale`; `gazeShift` 1
removes the emotion's averted-gaze bias (0 keeps it). `preferredGestures` is carried but not used here (T-097B chooses).

C++ use (T-097B): a `ReactionPlan` maps to `EmotionBlender::retarget(time, plan.target, rise, decay)` with the timing
from `modulatedTiming`; `EmotionBlender::evaluate(t)` gives the `EmotionState` at any time (random access).

Tests: `tests/test_emotion_blend.cpp` (continuity of value and velocity, bounded rates under random re-targets,
cross-fade sums, normalized override weights, modulation, and in a scene on the girl test package: no face or body pops
at quarter frames, gaze, loop tempo, plain emotions unchanged). Evidence: `docs/evaluation/animation/T-097A/`.

## 4. Layering (order of a character's pose)
1. Keyed and generated tracks.
2. Base clip (tier 0).
3. **Emotion postures and gestures (tier 1, by start; blended postures share the first blended start).**
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
