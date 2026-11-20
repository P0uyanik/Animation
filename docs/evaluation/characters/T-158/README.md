# T-158: deterministic character builds

Input e2c8904. Blender: bpy 5.3.0 module via tools/bpy_blender.py (Python 3.13). The wrapper ignores `-t 1`.

## Root cause
- `bmesh.ops.create_uvsphere` (used through `geom.uv_sphere`) returns its faces and edges in a run-dependent order
  and edge direction. Over 4 processes, the edge lists were 4 different. The vertex positions and per-face corner order are stable.
- The order changes SUBSURF output (ears) and `bisect_plane` output (`trim_shell`, upper lids) by about 1 float ulp
  (max 7.45e-9 m). This flips the 1e-7 m mesh hash T-137 used (`docs/evaluation/characters/T-109/mesh_hash.py`).
- Minor: `trim_shell` (face_v3/lids.py) and `refine_eye_regions` (face_features.py) iterate Python sets of BMesh
  elements, whose order follows memory addresses.
- A sorted canonical order is not enough: boy 2.0-2.2 ears then miss the published masters at 0.01 mm
  (`ear_order_repro.py`: sorted asc/desc, from_pydata, bm.sort, fixed edge direction all miss, natural 6/6 match).
  The natural face order is a pointer-hash permutation.

## Fix (Supervisor option b)
- `pipeline/charsys/uv_sphere_topology.json`: edge and face order of one radius-1 create_uvsphere run per size in
  use (12x8, 16x8, 20x10, 24x12, 28x12, 32x16, 48x24, 64x32, 96x64), recorded by `record_uv_sphere_topology.py`.
- `geom.uv_sphere`: replays that order. The live vertex order and positions are kept, because the seam merge orders
  vertices differently at small radii. Recorded vertices are matched to live ones by direction (KD-tree, < 1e-4).
  The call raises if the face set no longer matches. A size without a recording keeps the live order and prints a note.
- `trim_shell` and `refine_eye_regions`: sort by element index.
- `tests/test_determinism.py`: adds `--character current` (boy 2.2.0, girl 0.13.0, third 0.1.0 candidate),
  `--runs N` and `--jobs N`. The default (boy, 2 runs, used by check_all) is unchanged.

## Results
| check | result |
|---|---|
| before fix, girl 0.13.0, 4 runs, 1e-7 m hash | runs 2-4 differ (ear.L/R + one lid_upper), `determinism/before_fix_*` |
| after fix, 4 runs each: boy 2.2.0, girl 0.13.0, third 0.1.0 | identical, fingerprint_v2 0.1 mm and 0.01 mm (`determinism/determinism.json`) and 1e-7 m hash, 220/207/175 objects (`determinism/mesh_hash_1e-7_4runs.json`) |
| asset_store regenerate, all 9 published versions | main: 8 pass; fix: the same 8 pass (`regenerate_main/`, `regenerate_fix/`) |
| boy 1.0.0 | fails on main and on the fix (hair_mass), pre-existing, not touched |
| tools/regression/run.py (full) | ok: boy and girl fingerprint byte-equal, export equal, renders within noise, fidelity ok. Third character not buildable by the regression (candidate spec only) (`regression.json`) |
| verify_charsys | PASS |
| test_determinism.py default (boy, 2 runs) | PASS |

Not tested: the full tools/check_all.py; CI.
