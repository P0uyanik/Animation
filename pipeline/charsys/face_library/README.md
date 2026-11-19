# Face library (`expressions.json`)

Shared, character-independent facial expressions for face_generic/1-3. Nothing here names a character.

## Layers
- **Action units** (`action_units`): single facial motions every face builds from its own geometry. Examples are
  Blink.L/R, EyeWide, EyeSquint, the brows, the mouth corners, MouthWide, MouthO, and JawOpen (a bone plus a shape).
  - Optional units are built only where a spec asks for them: MouthPout (`face.action_units.pout_m`), CheekRaise
    (`face.cheeks`), and per-side copies (`face.action_units.split`).
- **Presets** (`presets`): semantic expressions defined only as action-unit weights.
  - They are baked per character into shape keys of the preset name, plus jaw drivers.
  - Blender controls (`face_<Preset>`) and engine morphs use the same names.
  - A spec may override weights (`face.expressions.override`) or add custom presets (`face.expressions.custom`).
- **Optional presets** (`optional_presets`): built only when a spec lists them in `face.expressions.optional`. Units a
  face lacks are skipped. Current entries:
  - Worried, Curious (M3);
  - SmileClosed, Thinking (T-031);
  - SmileOpen, Pout (T-109).
- **Engine names** (`engine_expressions`): lower-camel names the engine and the emotion files use, for example
  `smile` → Smile, `smileOpen` → SmileOpen, `pout` → Pout. An emotion face name that is neither an engine name nor a
  morph of the character is skipped with one warning (`emotion '…' has no morph for expression '…'`).

## Emotions built on the library (T-113)
The shared emotion library (`content/emotions/*.emotion.json` without a character prefix) stays exactly 8
(test_emotions.cpp).

Per-character sets are emotion files `content/emotions/<char>_*.emotion.json`, listed in
`pipeline/charsys/tests/test_expressions_r3.py`. Their faces mix library presets and action units, and each cites its
reference frames (T-106 intervals `[first, end)` or still references):

| character | emotion | face (at intensity 1) | reference |
|---|---|---|---|
| boy | boy_interested | EyeWide, BrowDown, MouthO, JawOpen | PB [259, 289), WT [60, 81), [87, 121) |
| boy | boy_sleepy | blink, BrowDown, MouthO, JawOpen | PB [0, 12), [12, 32), [125, 132) |
| boy | boy_unimpressed | BrowDown, blink, MouthFrown | PB [112, 125), WT [0, 20) |
| boy | boy_reluctant | **pout**, blink, BrowSad | #28 r3c3, hero24 / #08 pout |
| boy | boy_focused | blink, BrowDown, MouthO, JawOpen | PB [132, 151), [125, 132) |
| girl | girl_delighted | **smileOpen** | PB [255, 289), WT [81, 96) |
| girl | girl_wonder | WideOpen, jawOpen | WT [0, 15), [22, 39), [39, 61) |
| girl | girl_eager | EyeWide, BrowUp, MouthO, MouthSmile, JawOpen | WT [22, 39), [39, 61), [0, 15) |
| girl | girl_shy | SmileClosed, blink, BrowSad | PB [0, 32), [112, 125), [132, 151) |
| girl | girl_content | SmileClosed, MouthSmile, JawOpen, EyeSquint | WT [81, 96), [96, 121) |

- **Boy intensity.** Boy faces are authored at intensity 1 for his expressed intensity 0.42: event 0.7 × his profile's
  `reaction.intensity_scale` 0.6.
- **SmileOpen and Pout** are optional presets. A cast whose spec does not list them skips that face part. The
  published girl 0.12.0 / boy 2.1.0 do not list them; the T-109 candidates and the T-113 candidate overrides do.

## Closed lids (T-113, face_v3/lids.py `fit_closed_lids`; opt-in)
`spec.face.eyes.lids.closed_fit` makes the closed upper lid follow the eyeball instead of standing off it as a
pale dome.

- **Which keys.** Every upper-lid and lash key is processed: Blink, its in-betweens, and the baked Smile, Laugh,
  Squint, etc.
- **Fit.** Each vertex is pulled in, by its closure, towards `r (gaze envelope(u) + gap)` plus its shell thickness.
- **Fade.** The pull fades out above the rest lid edge, under the socket skin.
- **Rest-radius cap.** A linear blink + squint sum may not carry the shell past its rest radius.
- **Options:**
  - `gap`;
  - `fade_deg`, `fade_above_edge_deg`;
  - `gaze_range_deg`: the gaze sweep the closed lid clears; default the eye's own;
  - `shell_subsurface`: the upper lid shell gets a skin copy with its subsurface weight scaled. The 1–2 mm shell
    otherwise lets the white eyeball show through the skin's ~1.4 cm subsurface radius, which is the pale part of
    the dome;
  - `keep_thickness`.
- **Default.** Absent = unchanged output.
