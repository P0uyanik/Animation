# Personality profile schema `plush.personality/0` (T-053a draft 2026-11-17; reader T-053, 2026-11-18)

A character-independent description of **how** a character moves and emotes. Data only: one shared reader
(`engine/anim/personality.{h,cpp}`, T-053) resolves a profile into typed parameters; no character names or behaviour
live in shared code.

Files: `content/personality/<character_id>.json` (`profile_version` = the profile's own version; T-053 promoted the
T-053a / T-057 drafts to candidate `1.0.0`, path B: the owner approves the profile clips). The reader still finds
`<id>.draft.json` when no `<id>.json` exists. `content/personality/shared.json` (`plush.personality_action_units/1`)
holds the shared action-unit aliases and the neutral idle amplitude.

Scene use: character `"personality": "<id>"` (absent or `false` = no profile, behaviour exactly as before T-053).
Body mechanics `"bodyMechanics": {"personality": "<id>"}` keeps working and wins for the body mechanics layer.

## Value records
Every leaf parameter is a record, so each number carries its evidence:

```json
{ "value": 0.45, "unit": "0-1", "kind": "measured", "source": "WT f020-f085 (strips/wt_boy_eyes_f000-120.jpg)" }
```

| Field | Meaning |
| --- | --- |
| `value` | number, string, list or object |
| `unit` | `frames@24`, `s`, `deg`, `0-1` (normalised), `per_min`, `H` (head widths, as in VISUAL_TARGET.md), or `enum` |
| `kind` | `measured` (counted in a reference video), `reference` (read from a still), `estimate` (visual judgement of a reference), `extrapolation` (not shown; invented in the same spirit), `default` (global envelope from `docs/references/VISUAL_TARGET.md`) |
| `source` | citation keys from `docs/characters/REFERENCE_INVENTORY.md` |

Normalised `0-1` scales: 0 = the shared neutral default (no effect), 1 = strongest believable setting. A reader must
treat a missing parameter as 0 / neutral (opt-in, owner decision 2026-11-17).

## Sections
| Section | Parameters | Drives |
| --- | --- | --- |
| `tempo` | `action_speed` (multiplier on clip speed, 1 = library default), `reach_frames`, `anticipation_frames`, `settle_frames`, `overshoot` (fraction of travel), `hold_frames`, `careful_place_frames` (optional: slow two-handed placement) | timing of actions |
| `energy` | `level` (0-1), `idle_motion_amplitude` (H), `gesture_amplitude` (0-1) | overall liveliness |
| `posture` | `slouch` (0-1), `head_pitch_deg` (+ = down), `head_tilt_deg` (optional, sideways), `shoulders_forward` (0-1), `rest_hands` (enum list), `weight_shift` (0-1), `lean_toward_task` (0-1) | rest pose layer |
| `attention` | `primary_target` (enum: `task_object`, `speaker`, `camera`), `span_s` (time on one thing before attention drifts), `glance_at_others` (per_min), `glance_hold_frames` | gaze/look-at director |
| `boredom` | `enabled`, `onset_s` (idle time before fidgets), `fidget_interval_s`, `fidget_set` (list of behaviour names), `escalation` (what changes with time) | idle/fidget behaviour |
| `gaze` | `saccade_interval_s`, `fixation_on_task` (0-1), `eyes_lead_head_frames`, `look_down_bias` (0-1) | eye motion |
| `blink` | `interval_frames` (mean, min, max), `duration_frames`, `closed_frames`, `couple_to_action_change` (bool), `long_blink_on_gaze_drop` (false, or `{duration_frames}`) | blink generator |
| `face` | `resting` (reference reading: absolute action-unit weights; documentation), `rest_offset` (offsets on the model's own neutral, applied at all times), `expression_bias` (per action unit, offset −1..1 added × the expression activity), `watching_mouth` (offsets while a look action plays), `lid_rest` (Blink weight at rest, reference reading), `asymmetry` (0-1) | face (evaluator morph composition) |
| `smile` | `frequency` (0-1), `default_mouth` (enum), `open_smile_share` (0-1) | smile choice |
| `gestures` | record whose `value` is a list of `{name, description, hand, source}` (named gestures the character is shown doing) | gesture library selection |
| `reaction` | `delay_frames` (stimulus → first face change), `channel_order` (e.g. `["eyes","brows","mouth","head"]`), `positive_style`, `engaged_style` | reaction director |
| `interaction` | `prop_handling` (enum: `careful`, `practical`, ...), `two_handed` (0-1), `leads_task` (0-1), `contact_slowdown_frames` | prop / partner behaviour |
| `gaps` | free-text list of behaviour the references do not show | review |
| `limits` | `blink_interval_frames`, `blink_duration_frames`, `reach_frames`, `hold_frames`, `action_speed` (ranges `[lo, hi]`), `idle_motion_max_H_per_frame`, `face_offset_max` (numbers), `head_pitch_deg` (range) | engine clamps (with a warning) and `tools/animcheck/personality.py` |

## What the engine applies (T-053)
| Parameter | Layer | Mapping |
| --- | --- | --- |
| `blink.interval_frames.mean` | life / face blinks | mean interval = mean / 24 s (an explicit scene `blinkInterval` wins, clamped into `limits.blink_interval_frames`) |
| `blink.duration_frames`, `closed_frames` | life / face blinks | whole blink = middle of the duration; shut = middle of closed (≤ half); close : open = 40 : 60 |
| `energy.idle_motion_amplitude` | life | k = value / `shared.json` neutral (0.004 H), clamped 0.25–2: sway × k, head drift × k, breathing × √k |
| `gaze.eyes_lead_head_frames` | life (head follow) | head lag = middle / 24 s (unless the scene sets `headLagSec`) |
| `face.rest_offset`, `expression_bias`, `watching_mouth` | face | added to the resolved control weight (aliases in `shared.json`); bias × max animated expression weight; watching × look envelope (6 f ramps) |
| `tempo.action_speed` | clip layers | clip clock × tempo for gestures and clip actions (not base clips / auto idle); effective speed clamped into `limits.action_speed`; one-shot clips hold their last frame |
| `tempo` settle / overshoot / anticipation, `energy`, `posture` | body mechanics | as T-045 (`applyPersonalityToBodyMechanics`) |
| `limits.reach_frames` | actions (read only) | a reach / touch whose `contact − start` lies outside gives a warning |

Read but not applied yet (no engine layer for them; see the T-053 report): attention, boredom / fidgets, saccade
interval, look-down bias, smile choice, gestures, reaction, interaction.

Face weights use the shared action units of `pipeline/charsys/face_library/expressions.json`.
All frame values are at 24 fps.
