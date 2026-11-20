# T-156: eye shape to the T-150 targets (both girls)

Input `t-137-claude-faces @ 321466a`; targets `docs/evaluation/characters/T-150/targets.json` (main `e2c8904`).
Blender: bpy 5.3 behind `tools/bpy_blender.py`. Overrides only; no current version, spec or published file changed.

**Result: every front metric of both girls is inside its T-150 band, on both eyes (auburn 11/28 -> 28/28,
third girl 9/28 -> 28/28).** Opening width 67 -> 62 mm (auburn) and 71 -> 61 mm (third girl) at the same height.

## What changed
- `auburn/girl_auburn_bun_glasses.eyes.override.json`, `third/girl_white_hair_blue_dress.eyes.override.json`
  (`face.eyes` only; they replace the T-137 F1a / F1b eye overrides, the F1b fringe override stays as it is).

| key (`face.eyes.`) | auburn T-137 -> T-156 | third T-137 -> T-156 | effect |
|---|---|---|---|
| `socket.corner_deg` | 42 -> 37 | 46 -> 36 | narrower opening (width, H/W, D/W, inner white) |
| `lids.upper_edge_deg` / `lower_edge_deg` | 38 / -36 -> 34 / -41 | 38 / -36 -> 33.5 / -38.5 | less white above, iris centred in height |
| `iris.radius` (`pupil` = half) | 0.47 -> 0.453 | 0.462 -> 0.452 | D/spacing |
| `lids.upper_roll_deg` | -18 -> 6 | -18 -> 1 | corners level (inner drop), outer corner angle |
| `lids.upper_yaw_deg` (new, opt-in) | 8 | 8 | lid peak over the middle of the opening (apex) |
| `lash.span_deg`, `strands`, `thick_m`, `flare` | 52 -> 36, 3.4 -> 2.6 mm, 0.6 -> 1.2 | 56 -> 36, 3.4 -> 2.6 mm, 0.6 -> 1.2 | lash ends at the corners, thin inner end |
| `lids.lower_curve`, `lids.trim.up_outer_deg` | 0.15 -> 0.6, 72 -> 46 | same | lower corners; upper shell tip past the outer corner (3/4) |

- Shared code, opt-in: `pipeline/charsys/face_v3/lids.py` `lid_yaw` (`lids.upper_yaw_deg` / `lower_yaw_deg`).
  A lid edge is close to a circle about the eye's forward axis, so its peak always sat over the iris; the nose-side
  skin makes the opening narrower on the inner side, so the peak was at 0.63 W from the outer corner (band
  <= 0.586) whatever the roll (tried -6 .. +14 deg). The yaw turns the lid (and its lash) about the eye's vertical
  axis; the eyeball does not move. Key absent = the previous return value, bit for bit (unit test).

## Measurement (reproducible)
`eye_measure.py` (headless, no render, about 6 s): one ray per pixel of the 0.24 x 0.12 m eye window (1280 x 640)
against the evaluated skin, lid, lash and eyeball meshes, from the strict sheet's face camera; metrics as defined
in the T-150 README. `--camera probe --overlay` draws the trace on a 100 % eye strip (checked against the T-137
baseline render). `report.py` prints the tables below from `*/measure_*.json`.

```
blender -b --factory-startup -P docs/evaluation/characters/T-156/eye_measure.py -- <master.blend> <out.json> [--yaw -35]
python3 docs/evaluation/characters/T-156/report.py <T-150 targets.json> auburn|white_haired front <before.json> <after.json>
```

Before = the T-137 F1a / F1b build, after = this task. Differences from T-150's hand traces: glasses, hair and lens
refraction are not occluders here; the T-137 READMEs' hand estimates (H/W ~0.73) were lower than this measure of the
same build (0.83 / 0.79).

TABLES

## Evidence
- `auburn/strict.jpg`, `third/strict.jpg`: strict sheets (T-137 build | T-156 | references), Cycles 16 spp.
- `auburn/eyes_100.jpg`, `third/eyes_100.jpg`: 100 % eye crops, front and 3/4, Cycles 8 spp.
- `preview.jpg`: the cheap preview run first (4 spp, hair and clothes hidden; one trial before the shell trim).
- `auburn/expressions.jpg`, `third/expressions.jpg`: candidate expression sheets (6 spp). Blink closes fully in the
  measure (0 open pixels, both girls).
- `*/pupils.csv`: pupil pixels at shot size (T-137 method).
PUPILS

## Not reached by an override, and what it would need
- **Outline is in band but not a circle.** The opening is the socket's azimuth / elevation window in the skin
  (`face_v3/socket.py`): a near-vertical inner wall, a flat bottom and a straight lower-outer edge.
  `lids.lower_curve` and `lower_roll_deg` barely move it. Needs a rounded window in `lid_socket_v3` (corner radius,
  separate inner / outer `corner_deg`).
- **H/W sits at the low side (0.90, band from 0.875) and white above at the high side (0.075).** The reference
  irises are taller than wide (T-150 traces: D/W 0.74 with only 0.06 + 0.03 W of white at H/W 0.95, about 1.2 : 1);
  ours are round (`felt.round_iris`). A taller opening adds white, a larger iris breaks D/spacing. Needs an iris
  aspect in `face_v3/felt_eye.py`. The third girl's `arch_w` (0.46, band from 0.45) is the same trade.
- **Lash.** It turns with the lid and is symmetric about the lid peak; the references have a thick outer and a thin,
  shorter inner end. Needs a per-side lash span / thickness in `face_generic.build_eyes`.
- **Oblique (G02) targets: not reached** (table above, 11/28). Yaw is not matched to G02 (-35 deg used, the eye-crop
  view), the lens is not modelled, and the far eye is too wide (H/W 1.39 vs 1.78). Front bands were the goal.
- Unchanged from T-137: thin lower-lid rim under the eye; a small upper-shell tip at the outer lash end (3/4
  exposure 0.085 -> 0.037 auburn, 0.137 -> 0.042 third with the trim).

## Tests
`python3 pipeline/charsys/tests/test_face_r5.py --blender blender`: 20/20 (14 existing + 6 for the lid yaw: guard,
no spec under `assets/` uses it, overrides touch `face.eyes` only, unchanged without the key, peak shift with it).
No test, threshold or golden changed. Not run: ctest, verify_charsys, face_system_test (no default path changed).

Rebuild: `build_character.py -- --spec <spec> --out <dir> --no-glb --no-compare --override <...>` (auburn: 0.13.0
spec + this override; third: T-126a spec + T-126 hands, hair, dress, materials + T-137 fringe + this override);
sheets: `python3 docs/evaluation/characters/T-137/tools/face_sheets.py <part.json> strict|eyes|expr|pupils --out <dir>`.
