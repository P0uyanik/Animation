# R3 faces bundle: stacking and verification (`integration/r3-faces`)

Owner decisions 2026-11-20 (`docs/process/OWNER_DECISIONS.md`): ~21:50 CET release path; ~22:00Z T-156 accepted and
narrow guard allowances; ~23:10 CET option A (R3 is released as boy 2.3.0 / girl 0.14.0 / third 0.1.0, rebuilt
from these specs). Nothing here makes a version current.

## Specs

`assets/characters/<id>/spec/candidates/R3/<id>.<ver>.spec.json`, written by `stack_specs.py` from the T-155
candidate specs (`spec/candidates/T-155/`) plus, in order (each layer's `override` deep-merged; dicts recursive,
lists replaced whole):

| character | layers |
|---|---|
| boy_yellow_hoodie 2.3.0 | T-159 ears, T-168 face r4 (nose, cheeks, head outline), T-167 hair r6 |
| girl_auburn_bun_glasses 0.14.0 | T-159 temple, T-159 ears, T-159 glasses (arm rests on the ear), T-167 hair r7, T-156 eyes/lids |
| girl_white_hair_blue_dress 0.1.0 | T-159 temple, T-159 ears, T-167 hair r7, T-156 eyes/lids |

Stacking checks (`stack_report.json`): no key path is written by two layers. Lists that a layer replaces whole were
compared with the candidate's: the glasses list only adds `temples.rest_on_ear`; the r6/r7 `hair.structures` keep
every candidate item (T-167 built them on T-155 specs byte-identical to these). T-156 sets 13 of the T-137 eye values
per girl again (its own retune, by design); the girls' resulting `face.eyes` equal T-156's own reviewed builds
leaf for leaf.

## Step 4: every change shows in the build

`chain_build.sh` builds the T-155 candidate (= boy 2.3.0 / girl 0.14.0 / third 0.1.0 as on this branch), then one
more layer per step, then the stacked R3 spec, then base and R3 again; every master is strict-hashed (T-158
`mesh_hash_strict.py`: all meshes, basis + shape keys, 1e-7 m). `chain_deltas.py` lists the objects each layer
changes (`chain_deltas.txt` / `.json`); `obj_delta.py` gives sizes (`chain_mm_summary.txt`, raw `chain_mm.tsv`:
per object max / 95th percentile of the nearest-vertex distance both ways, world space, mm; for a re-meshed object,
vertex counts in brackets, the number is a vertex-to-vertex distance and overstates the surface move).

| character, layer | objects changed (hash) | size (max / p95 mm) |
|---|---|---|
| boy + ears | ear.L/R (1986 -> 7938 v) | new ear mesh |
| boy + T-168 face | 59: body_skin (-206 v), mouth, brows, lids; hood and the garments refitted to the new head | mouth 9.5/9.3, head skin 16.4/7.5, hood rim 10.9/5.3; far garments (shoes, trousers): a few vertices up to 3.6, p95 0 |
| boy + hair r6 | hair_crown, hair_top, hair_top_outer, hair_whorl | crown re-meshed; top_outer 5.8/3.7 |
| auburn + temple | 48: head skin (+16 v), ears, brows, glasses, vest/collar, hair resting on the head | skin 3.8/0.6, back ringlets up to 2.4 |
| auburn + ears | ear.L/R, glasses (arm follows the ear) | glasses 4.4/1.0 |
| auburn + glasses | glasses only (arm on the ear) | 10.0/6.7 |
| auburn + hair r7 | 32 hair objects (ringlets re-meshed, curtain, temples, band, flowers) | up to ~150 on ringlets |
| auburn + T-156 eyes | 24: lids and lashes re-meshed, head skin (+10 shape keys: Blink, Blink.L/R, winks, @75), brows, mouth, glasses, fringe | skin 6.9/2.8; mouth, lens ~1.4 (features placed from the new lids) |
| third + temple | 25: head skin (+32 v), ears, brows, lids, side/temple hair | skin 3.4/0.6, side locks up to 2.3 |
| third + ears | ear.L/R | new ear mesh |
| third + hair r7 | 32 hair objects | outer/back locks up to ~83 |
| third + T-156 eyes | 18: lids and lashes re-meshed, head skin (+ Blink keys), brows, fringe/side locks (face keep-out), mouth | side locks up to 9.4 |

- Every layer changes the build, and the R3 spec build equals the layer-by-layer build exactly (girls: "NO CHANGE"
  step; boy: its last layer step is the R3 spec build). No change of an earlier layer is undone by a later one
  ("changes lost by later layers: none").
- Repeatable (T-158 strict hashes, every object): base and R3 built twice per character: identical, all six pairs.
  T-156's "6 lid/ear meshes varying between builds" does not reproduce on this base.
- Side effect to know: T-168 moves a few of the boy's shoe / trouser vertices (shoes 44 + 32 of 3584 vertices, up to
  1.8 mm; trouser ankle R 174 of 4184, up to 3.6 mm; trousers main 183 of 29684, up to 5.0 mm; p95 0). Cause, as far
  as measured: not a shared smoothing or vertex group on the body. The body skin under them does not move (every
  body vertex below 0.6 m within 0.0002 mm of the previous build); T-168 changes only the head (206 vertices fewer,
  so the body's vertex indices shift) and, through the hood, the hoodie. The moved garment vertices lie only in contact
  zones (shoe collar / trouser ankle, trouser waist under the hoodie hem), i.e. the garment fit and drape solve
  (`garments/drape.py`: collider built from the body in vertex order, cloth solver) reacts to the changed body mesh and
  hoodie. Not pinned down further (which solver step). Crop: `boy/legs_100.jpg` (T-155 build before T-168 | R3).

### T-156 shape keys and the engine package

`export_engine.py` (rig profile humanoid_rigify) on the girls' base and R3 masters: exports pass. `body_skin` gains
the morph blocks Blink, Blink.L, Blink.R, LeftEyeClosed, RightEyeClosed; these names already existed (lids), so the
package's morph-name set, `morph_inbetweens`, expression map, `expressions_missing`, `expression_bones`, `blink`
timing, roles and capabilities are unchanged. The skeleton's body bones and parents are identical (eye pivots move
< 0.1 mm); only the hair-dynamics chain bones change with hair r7 (auburn 105 -> 93, third 127 -> 163 DYN bones).
Not run here: an engine-side load of the packages (C++ build).

## Checks on this branch

Plain: test_guard_allowlist, test_face_r5, test_face_t168, test_hair_r6, test_hair_r5, test_hands_r2,
test_render_profiles, test_gate_tools, check_assets, check_cast pass. test_face_v4: 15/17, the two version pins
(release step, `RELEASE_STEP.md`). Blender suites: left to the gate.
