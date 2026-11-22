# T-213 · Face export parity, knob-free master check and Blender build pin (face plan P5a)

The acceptance tooling that T-212 (`docs/research/T-212/README.md`, branch `t-212-codex-face-plan-review`) (row "Expression and engine mismatch") asks for.
It comes before any face is fitted. Tool: [`pipeline/charsys/face_parity.py`](../../../../pipeline/charsys/face_parity.py).
Test: [`pipeline/charsys/tests/test_face_parity.py`](../../../../pipeline/charsys/tests/test_face_parity.py). Full report:
[`parity_current_masters.json`](parity_current_masters.json). No asset, exporter, engine or version pointer was changed.

**Result on the three current masters (Blender 5.3.0, build `02f0899d78e3`):** the knob-free check passes on all three.
Rest positions and the raw key deltas are within the bound on all three. Neutral and smile+blink pass on all three, and
half-blink passes on auburn and the boy. **Half-blink fails on `girl_white_hair_blue_dress` 0.1.0** (6.72 mm on the
eyeballs). The sweep also finds the same cause on all three masters, at partial weights of the chained expressions
(see "Finding"). I reported both to the Supervisor and did not fix them.

## Table (mm, engine reconstruction vs Blender evaluation)

| Character (version) | Expression | Max | Mean (all vertices of keyed objects) | Mean (moved vertices) | Bound | Verdict |
|---|---|---|---|---|---|---|
| girl_auburn_bun_glasses (0.14.0) | neutral | 0.000000 | 0.000000 | – | 0.000149 | PASS |
| | half-blink (Blink 0.5) | 0.000060 | 0.000001 | 0.000016 | 0.000312 | PASS |
| | smile + blink (Smile 1, Blink 1) | 0.000091 | 0.000002 | 0.000007 | 0.000476 | PASS |
| boy_yellow_hoodie (2.3.0) | neutral | 0.000000 | 0.000000 | – | 0.000298 | PASS |
| | half-blink | 0.000000 | 0.000000 | 0.000000 | 0.000519 | PASS |
| | smile + blink | 0.000070 | 0.000000 | 0.000000 | 0.000740 | PASS |
| girl_white_hair_blue_dress (0.1.0) | neutral | 0.000007 | 0.000000 | – | 0.000149 | PASS |
| | half-blink | **6.720007** | 0.045717 | 0.445550 | 0.000312 | **FAIL** (eye.L, eye.R: 529 vertices each) |
| | smile + blink | 0.000085 | 0.000005 | 0.000008 | 0.000476 | PASS |

| Character | Rest, all exported objects (max) | Raw key − Basis deltas (max / bound) | Sweep (failing / max) | Knob-free | Jaw (expression bones), Blender − package |
|---|---|---|---|---|---|
| auburn | 0.000032 mm over 85 objects, 403 751 vertices | 0.000097 / 0.000104 mm | 9 of 56 / 8.77 mm | PASS (12 face objects) | ≤ 0.0002° |
| boy | 0.000031 mm over 90 objects, 285 520 vertices | 0.000063 / 0.000102 mm | 18 of 73 / 12.18 mm | PASS (12) | ≤ 0.0003° |
| white hair | 0.000031 mm over 69 objects, 404 246 vertices | 0.000097 / 0.000104 mm | 24 of 56 / 8.84 mm | PASS (14) | ≤ 0.0002° |

The bound column is the largest per-object bound. The check works per coordinate against each object's own bound,
while the table reports Euclidean errors. No combination correctives exist on any master. Auburn has 14
`corrective.reach.*` keys, all on garments. They are driven by arm swing, the engine never drives them, and they are 0 in
Blender at every tested expression. Runtime per master is 90–135 s, about 13–15 s of which is the export. All three
masters pin `export/4`.

## Finding: in-between chains vs meshes without in-between keys

The engine expands an in-between chain by morph *name* (`engine/model/character.cpp` `expandInbetweens`). For a weight
w below the last stop (0.75), every block named after the base morph is set to 0, and only the `@25/@50/@75` blocks
carry the motion. A mesh that has the base key but no stop keys therefore stays at rest until w = 0.75 and then ramps
from 0 to 1. In Blender the same key has a linear `AVERAGE` driver, so it follows w directly. The two agree at w = 0 and
w = 1 only. `chain_gaps` in the report lists every affected object:

- auburn: Laugh, Sadness, Squint (body_skin, lid_lower, brow, mouth, mouth_cavity). These are partial weights only.
- boy: also Bored, Skeptical, Smile.
- white hair: also **Blink, Blink.L/R, LeftEyeClosed, RightEyeClosed on eye.L / eye.R**. This master's eyeballs carry a
  `Blink` key, so the core half-blink fails. In the engine the eyeballs do not move at half-blink, while Blender moves
  them up to 6.72 mm.

Possible fixes, which are owner/Supervisor decisions and out of T-213's write-set:
- (a) the face generator writes the chain-matched scripted driver on every mesh that carries a chained base key,
  which keeps the engine unchanged;
- (b) it writes the stop keys on those meshes too;
- (c) the engine expands chains per mesh, only where that mesh has stop blocks.

Option (c) changes released look. Options (a) and (b) need a new face version.

## Quantization (derived; `quant_bound()`, `delta_bound()`)

The per-coordinate bound for one vertex is **q_p + Σ|w| · q_d + q_b**. The terms are:

| Term | export/4 (all current masters) | export/5 / export/6 |
|---|---|---|
| q_p, position | float32 write: ulp(extent)/2. At 1.6 m that is 2⁻²⁴ m = 0.0000596 mm | GRID/2 = 2⁻¹⁶ m = 0.01526 mm (+ ulp/2) |
| q_d, each delta | drop threshold 1e-7 m + float32 ulp(delta extent)/2 ≈ 0.000104 mm | DELTA_GRID/2 = 2⁻¹⁵ m = 0.03052 mm (+ ulp/2) |
| q_b, Blender's own float32 evaluation | (2 + ⌈Σ\|w\|⌉) ulp(extent): one per key add, plus the REST armature and world matrix | same |

- **Extent** is the object's largest world coordinate, and **delta extent** is its largest key-delta coordinate.
- **Σ|w|** is the sum of the engine's expanded morph weights.
- At 1.6 m this gives 0.000298 mm for the rest, 0.000312 mm for half-blink (one active block) and 0.000476 mm for
  smile+blink. The raw-delta bound is q_d alone.
- The passing expressions stay at or below about 20 % of the bound. Raw deltas reach 93 %: deltas under 1e-7 m are dropped by design. Half-blink on white hair exceeds it by a factor of about 20 000, so the
  bound separates rounding noise from a real split.

## What the tool checks

1. **Export parity.**
   - It exports the master in-process with `export_engine.py`, which is read-only on the file, or it reads `--package`.
   - It reconstructs each expression as rest + Σ w · dpos, using the engine's chain expansion, which is mirrored in
     `expand_inbetweens()`. The test pins the C++ function by hash, so an engine change fails the test until someone
     re-checks the mirror.
   - It compares that reconstruction, vertex by vertex, with Blender's evaluated mesh for the same `face_*` controls on
     the rig. Drivers and all modifiers are live, and the rig is in REST position with masks off, as in the exporter.
   - Engine vertices are matched to Blender vertices by position. When positions tie, the full delta record decides.
   - It also compares every raw key − Basis delta, and evaluated rest positions for every exported object.
   - **Core** = neutral, half-blink, smile+blink. These decide `pass`.
   - **Sweep** = every face control alone at 1.0, and every chain at 0.375, 0.625 and 0.875. These decide `sweep_pass`,
     which is always reported and gates with `--strict`.
   - A combination corrective (a key driven by 2+ `face_*` controls) fails `pass`, because the engine has no combination
     logic. Other correctives must be 0 in Blender at every tested expression.
   - Jaw angles from `expression_bones` are reported for information only.
2. **Knob-free master** (T-211 risk a).
   - Objects that carry face keys may have only ARMATURE and vertex-group MASK modifiers, with viewport = render.
   - Warp, Hook, Lattice, Surface Deform, Geometry Nodes, Displace, Smooth, Shrinkwrap and every other modifier fail
     the check.
   - Face keys must be relative to Basis, have no vertex group and not be muted.
   - No Lattice object may remain in the character collection.
3. **Blender build pin.**
   - `BLENDER_PIN = 5.3.0 + 02f0899d78e3`: the gate's bpy wheel and the owner's T-212 replay build.
   - Any other build exits with code 3 and a framed message.
   - For an intentional upgrade, run with `--accept-blender <version>+<hash>` (or `PS_FACE_PARITY_ACCEPT_BLENDER`) on
     every master. The override must name exactly the running build and is recorded in the report. When all masters
     pass, update `BLENDER_PIN` in a reviewed commit.

Exit codes: 0 pass, 1 a check failed, 2 export refused, 3 build pin.

## How P2–P6 call it

```
blender -b --factory-startup -P pipeline/charsys/face_parity.py -- --character girl_auburn_bun_glasses --out <report.json>
blender -b --factory-startup -P pipeline/charsys/face_parity.py -- --blend <candidate master.blend> [--strict] [--no-sweep]
blender -b --factory-startup -P pipeline/charsys/face_parity.py -- --all --out <report.json>   # auburn first
# from a Blender script: import face_parity as FP; rep = FP.run_master(path); rep["pass"], rep["sweep_pass"]
```

| Phase | Use |
|---|---|
| P2 fit | After the fit, bake the knob into Basis and remove the helpers, then run on the candidate. The knob-free check catches a helper left live, and parity catches a key that no longer matches Basis. |
| P3 `face_generic/4` | Gate every candidate build. A new face version should pass `--strict`, which means fixing the chain gap above in the generator. |
| P4 expressions / rig | Re-run after rebuilding the lid keys and correctives. A new combination corrective fails until the engine supports it. |
| P5 identity card | The card records the report's `pass`, `sweep_pass` and Blender pin. |
| P6 release | Run `--all` on the candidates before a version switch, and re-run on every Blender upgrade (pin). |

## Replay

```
blender -b --factory-startup -P pipeline/charsys/face_parity.py -- --all --out docs/evaluation/characters/T-213/parity_current_masters.json
python3 pipeline/charsys/tests/test_face_parity.py                     # plain checks, about 0.1 s, no bpy / numpy
python3 pipeline/charsys/tests/test_face_parity.py --blender <blender>  # + auburn master and a broken temp copy, about 3 min
```

The `--all` run took 5 min 50 s on a 4-vCPU container. Ledger: 0 renders, 0 asset builds, 3 exports (temporary),
0 CI.
