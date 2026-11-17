# Personality profile schema `plush.personality/0` (DRAFT, T-053a, 2026-11-17)

A character-independent description of **how** a character moves and emotes. Data only: shared systems (T-053)
read it; no character names or behaviour live in shared code. Profiles are drafts until T-053 implements a reader
and the owner approves the result against the references.

Files: `content/personality/<character_id>.draft.json` (the `.draft` suffix is dropped on approval).

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
| `face` | `resting` (action-unit weights), `expression_bias` (per action unit, added offset −1..1), `lid_rest` (Blink weight at rest), `asymmetry` (0-1) | face layer |
| `smile` | `frequency` (0-1), `default_mouth` (enum), `open_smile_share` (0-1) | smile choice |
| `gestures` | record whose `value` is a list of `{name, description, hand, source}` (named gestures the character is shown doing) | gesture library selection |
| `reaction` | `delay_frames` (stimulus → first face change), `channel_order` (e.g. `["eyes","brows","mouth","head"]`), `positive_style`, `engaged_style` | reaction director |
| `interaction` | `prop_handling` (enum: `careful`, `practical`, ...), `two_handed` (0-1), `leads_task` (0-1), `contact_slowdown_frames` | prop / partner behaviour |
| `gaps` | free-text list of behaviour the references do not show | review |

Face weights use the shared action units of `pipeline/charsys/face_library/expressions.json`.
All frame values are at 24 fps.
