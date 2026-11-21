# T-184 · Garment under skin when seated (and in the walk): opt-in `seated` field

Owner defect 2026-11-21 ~12:30Z, found by T-175. Branch `t-184-claude-seated-garments`, input `origin/main@7135087`.
Round file: [`ROUND.md`](ROUND.md). **Status: CHECKPOINT.** Nothing is released: the fix is an opt-in item field,
switched on only by the two evidence overrides in [`overrides/`](overrides/).

## What to look at
| File | What |
| --- | --- |
| [`sheet_girl_seated.jpg`](sheet_girl_seated.jpg) | girl, seated (T-175 f150): before / after, rows front and lap |
| [`sheet_boy_seated.jpg`](sheet_boy_seated.jpg) | boy, seated: before / after (no visible change expected) |
| [`sheet_girl_walk.jpg`](sheet_girl_walk.jpg) | girl, walk (T-175 f24, forward swing): before / after |
| [`numbers.json`](numbers.json) | every number below |

Renders: Cycles, review profile, 512 px tiles, 16 samples (motion evidence, not image quality). Blender: bpy 5.3.0
through `tools/bpy_blender.py`. Motion: T-175's review shot `t-175-claude-locomotion@c384f1d`, read only; the two
frames used are stored in [`bake_excerpt.json`](bake_excerpt.json).

## Cause (two separate faults)
1. **Weights.** Every vertex of a shell piece is bound with the weights of the body vertex it was extruded from.
   Puff, leg split, cuff gather and drape then move it, up to 53 mm on the girl's shorts. 1,271 of her 17,488
   leg-tube vertices sit over skin carried 100 % by the thigh while they are carried by the pelvis and spine, so they
   stay behind when the thigh bends. This is the engine check's −58 mm (seated) and −28 mm (walk, same vertices).
2. **Collision.** The post-skinning collision is weighted by the rest distance to visible skin. The shorts' front
   panel is far from bare skin at rest, so its weight is about 0 (exactly 0 on 288 of the 364 vertices that were
   under visible skin in the first seated pose), and nothing corrects it when the bare thighs are bent up through it.

## Fix: `seated` on `shorts` / `trousers` (`pipeline/charsys/garments_v3/seated.py`)
Applied at bind time, after the `garment/2` binding. No geometry, modifier, shape key or driver is added.
- `leg_weights`: a shell vertex takes the weights of the skin under it, in the hip zone only (hems and shins keep
  their weights), blended back to the old weights within `centre_m` of the centre plane.
- `collision`: full collision weight where bare leg skin comes within `radius_m` in the hip bends `hip_deg`
  (default 45, 90, 110 degrees); never lowers a weight.

Field reference: the module docstring and `pipeline/charsys/garments_v3/README.md`.

## Numbers
**Engine check** (`tools/motion_checks/run.py`, package skinning, limit −5 mm, every 4th vertex), whole T-175 shot:

| Character, piece | Part | Before | After |
| --- | --- | --- | --- |
| girl `shorts.main` | sit / stand | −57.9 mm, 25 vertices, 96 frames | −26.9 mm, 16 vertices, 89 frames |
| girl `shorts.main` | walk | −28.3 mm, 11 vertices, 100 frames | −13.8 mm, 2 vertices, 88 frames |
| girl `shorts.gusset` | sit / stand | −15.5 mm, 7 vertices | unchanged |
| girl `shorts.gusset` | walk | −5.6 mm, 3 vertices | unchanged |
| boy `trousers.main` | walk | −19.7 mm, 14 vertices | unchanged |
| boy `trousers.main` | sit / stand | −11.8 mm, 3 vertices, 12 frames | unchanged |

**As rendered in Blender** (`tools/seated_probe.py`, every vertex, armature + collision; "under" = deeper than 1 mm):

| Character, piece | Frame | Under visible skin, before → after | Under hidden skin, before → after |
| --- | --- | --- | --- |
| girl `shorts.main` | seated | 149 vertices (worst −6.8 mm) → 0 | 0 → 9 (worst −19.2 mm) |
| girl `shorts.main` | walk | 0 → 5 (worst −1.9 mm) | 3 (−6.1 mm) → 4 (−3.2 mm) |
| boy `trousers.main` | seated | 0 → 0 | 594 → 612 (worst −22.4 mm both) |
| boy `trousers.main` | walk | 0 → 0 | 24 → 15 (worst −10.5 mm both) |

Rest pose: no garment vertex moves more than 0.004 mm between a build without and with the field.

## What the sheets show
- **Girl, walk:** before, the forward thigh comes out through the shorts leg and the hem is torn open; after, the leg
  tube and its cuff follow the thigh. This is the clear improvement.
- **Girl, seated:** before, the thighs come straight through a flat front panel; after, cloth is gathered round the
  thigh roots and no vertex is under visible skin. The change is small on screen: see the first limit.
- **Boy:** no visible change (his trousers cover the leg; he had nothing under visible skin).

## Limits (accepted for this round by the Supervisor, stated plainly)
1. **The girl's thighs still leave the shorts through the front panel when seated.** Her bloomer legs end about 2 cm
   below the hip joint and her trunk is round, so at a deep bend the leg tubes and cuffs lie inside the trunk. The fix
   wraps the panel round the thighs; it does not re-drape the shorts over them. That needs a pose corrective or a
   cloth simulation.
2. **The engine check does not pass.** What is left on `shorts.main` (−26.9 / −13.8 mm) and the unchanged gusset
   flags are the crotch bridge between the legs, paired by the check with inner-thigh skin 10–15 mm away; against the
   real surface in Blender the gusset is at most 2 mm deep.
3. **The collision part is Blender only.** Engine previews still show bare thighs through the front panel.
4. Switching worn items (`set_active_items`) rebuilds the collision weights by the old rule; `seated.bind` must then
   run again. Only `pipeline/charsys/tools/garment_pose_eval.py` does that today.
5. Walk, after: 5 shorts vertices are 1–1.9 mm under visible skin at f24 (before: 0, with the thigh outside the leg).

## Opt-in evidence (released versions, packages and goldens unchanged)
- Without the field nothing in `seated.py` runs; `core.py` stores no property and reports nothing (test `bind`).
- Boy 2.3.0 built from its spec with this code: `geometry.bin` byte-identical to the package of the published master
  (`03d6bf4aa2af87bb…`).
- Girl 0.14.0 built from its spec with this code against a build on a clean `origin/main@7135087`: positions, joints,
  weights and UVs of all 86 meshes identical. Normals and index order of the 7 buttons and the 2 vest embroidery
  pieces differ; the same kind of difference (the 2 embroidery pieces) separates the clean `origin/main` build from
  the published package. This is build-to-build variation already on `main`, not from this branch (reported, not
  touched).
- `test_garments_r3.py --quick` 67/67, `test_garments_v2.py --quick` 46/46, `release_rule.py` 0 violations.
- No file under `assets/` uses the field (test `plain`).

## Tests
`python3 pipeline/charsys/tests/test_garments_seated.py --blender <blender>`: 45/45. Plain (no Blender): no user of
the field under `assets/`, the overrides change nothing else, the module names no character. Blender: validation
(good blocks, 9 rejected forms per character), and a synthetic body whose shorts leg tubes are carried by the trunk:
without the field `garment/3` binds exactly like `garment/2`; with it the tubes follow their thigh (44 → 0 vertices
inside a bent leg), shin and trunk vertices keep their weights, the centre keeps part of the old weights; collision
weights rise only where bare skin comes close, are never lowered, and the rig is left at rest.
Not run: the full Blender tier of `tools/check_all.py` and `verify_charsys.py` (no generator default changed; the
default builds above cover the build path).

## Rebuild
```
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec <current spec> --out <dir> --no-glb \
    --override docs/evaluation/characters/T-184/overrides/<id>.T-184.override.json
blender -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake docs/evaluation/characters/T-184/bake_excerpt.json \
    --cast <cast.json> --out <dir> --profile review --blend-only
blender -b --factory-startup -P docs/evaluation/characters/T-184/tools/seated_probe.py -- --shot <dir>/shot.blend --out <out>
python3 tools/review/shot_sheet.py docs/evaluation/characters/T-184/sheet_girl_seated.json
```
`<cast.json>`: `{"boy": {"master": ..., "character_id": ..., "package": ...}, "girl": {...}}` (published masters for
"before", the builds above for "after"). Sheet rows are the probe's tiles: 3–4 girl walk, 5–6 boy seated, 7–8 girl
seated (front, lap). The engine check needs T-175's full bake (its branch), not the excerpt.

## Follow-ups (not in this task)
- Boy: trouser hem at the ankle against foot skin inside the shoe (engine check −16..−20 mm in the walk, real depth
  0.2–5.8 mm, skin hidden). Out of scope by Supervisor decision.
- Limit 1: a seated corrective or cloth pass for short leg tubes.
- Girl build variation in button / embroidery normals on `main` (see "Opt-in evidence").

## For the Supervisor (files outside this claim)
`pipeline/charsys/release_rule.py`, a helper and one `FEATURES` entry (scope `characters`: every file under
`assets/characters/`; checked here: detects both overrides, 0 files under `assets/`):
```python
def _garment_field(d, field):  # T-184: a clothing item that switches a garment/3 item field on
    return _walk(d, lambda k, v: k == "garments" and isinstance(v, list)
                 and any(isinstance(g, dict) and g.get(field) not in (None, False) for g in v))

    "seated": {"scope": "characters", "detect": lambda d, t: _garment_field(d, "seated"), "old": "T-184 (new)"},
```
`pipeline/charsys/tests/test_release_rule.py` `SAMPLES`:
```python
    "seated": [{"clothing": {"garments": [{"type": "shorts", "seated": True}]}},
               {"override": {"clothing": {"garments": [{"type": "trousers", "seated": {"collision": False}}]}}}],
```
`pipeline/charsys/tests/TESTS` (the Python tests step then runs the plain checks; the Blender checks need
`--blender` and are a local run unless a Blender unit is added for them):
```
run test_garments_seated.py                  # T-184 seated field (plain checks; --blender adds the bind checks)
```
`docs/process/GENERATOR_PINS.md`, table "Opt-in flags inside released modules":
```
| `seated` on a `shorts` / `trousers` item (weights and collision weights for a deep hip bend) | garments_v3/seated.py via garments_v3/core.py | T-184 |
```
Guarded path needing the trailer: `Supervisor-Approved: pipeline/charsys/tests/test_garments_seated.py`.
