# T-097C evaluation: acting signature and consistency checks

Rule: `tools/animcheck/acting.py` (documented in `tools/animcheck/README.md`, section "Acting rule"). Warnings only:
gesture amplitude, notice delay (first glance after an event), still hold for quick characters, each read from the
character's personality profile. Input `7bc08ff` (main + T-104), engine built in Release, `plush-render --bake`.

## Regression shots (`run_gate.py`)

```
PASS clip_gestures.scene.json: 6 gestures, 0 failures
PASS personality.scene.json: 3 gestures, 0 failures
PASS personality.scene.json: personality limits, 2 characters, 0 failures
INFO personality.scene.json: acting: 2 characters, 0 warnings (warnings only)
PASS wave_touch.scene.json: 4 gestures, 0 failures
exit 0
```

Only `personality` carries profiles (the other two shots are skipped by the acting rule, as by the personality check).

| Character (profile) | quick | gesture amplitude | glances after events | longest still run | required hold |
| --- | --- | --- | --- | --- | --- |
| boy (`boy_yellow_hoodie`) | no (beat 1.2, speed 1.0) | no clip gesture | none within 48 f of an event | 115 f (f1-f116) | 12 f (12 × hold_scale 1.0) |
| girl (`girl_auburn_bun_glasses`) | yes (beat 0.85, speed 1.1) | `point` @110: 0.44 (80°) ≤ 0.6 + 0.1 | none within 48 f (her look f192 is 76 f after the boy's touch f116) | 109 f (f1-f110) | 15 f (12 × hold_scale 1.25) |

## Out-of-character variant (flags fire on a real bake)

The `personality` shot with two edits (not committed): the girl's look back at the task moves to f117, one frame after
the boy's touch (f116); the boy plays the `point` clip at f215.

```
WARN boy: boy clip point @215 amplitude 0.44 (79 deg) > profile 0.3 (+0.1)
WARN girl: glance at f117 1 f after 'boy touch' (f116) < notice delay 2 f
acting: 2 characters, 2 warnings (warnings only)
```

Exit 0 (warnings only). The same `point` clip is in character for the girl (gesture amplitude 0.6) and flagged for the
boy (0.3); the girl's quick notice delay (2-4 f) still needs 2 f.

## Tests

`python3 tools/animcheck/tests/test_animcheck.py`: 18 tests OK (14 before + 4 `ActingRule`: amplitude against the
profile and the `limits` override, touch not a gesture; notice delay on partner actions and explicit `events`, own
actions and late looks ignored; quick character with hold_scale needs the longer hold; warnings only and missing
profile is a warning). No existing test, check or threshold changed (`thresholds.json` untouched).
