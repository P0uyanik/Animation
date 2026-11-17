# T-038b boy `hair_mass` build determinism

Date: 2026-11-17. Blender: bpy module 5.3.0 (Linux, CPU), driven through `tools/bpy_blender.py`. Scratch output in `build/t038b/` (not committed).

## Outcome

Two clean boy builds now produce a **byte-identical `hair_mass`**: identical float32 vertex coordinates *in the same order*, identical face corners, therefore identical 0.1 mm and 0.01 mm fingerprints. The 0.1 mm snapping added by T-038 is no longer needed on this path and was removed. The geometry is still equal to v6 within the `verify_charsys` tolerances (worst numeric difference 0.0 m). The girl's fingerprints are unchanged.

## Root cause

The drift does not come from SUBSURF/DISPLACE threading. It comes from the **input topology order**:

- `geom.uv_sphere` (`bmesh.ops.create_uvsphere` + `to_mesh`) and the following face deletion (`bmesh.ops.delete` + `to_mesh`) return the same vertices in the same order, but the **polygons in a different order and with a different first corner on every call**. This happens even inside one process. Vertex positions are identical, and so is the sorted set of faces.
- SUBSURF (level 1, limit surface) then DISPLACE evaluate the same surface either way, but the float rounding follows the topology order. The applied mesh had a different vertex order on every run, and about 160 of 3905 vertices differed by up to 1.8e-7 m (float ulps; isolated test mesh). Run-to-run, any ulp change near a rounding boundary flipped a quantized fingerprint coordinate.
- Proof: canonicalizing the topology and then applying Blender's *own* unchanged SUBSURF + DISPLACE gives the same SHA-256 of the coordinate bytes on 5 of 5 evaluations in one process and across processes.

Diagnostic progression (isolated hair-mass construction, 4 evaluations each): base mesh coords identical; SUBSURF only → order + ulp differences; DISPLACE only → ulp differences; base faces → loop order and `loop_start` hashes differ every time, canonical face set identical.

## Fix (`pipeline/charsys/hair.py` only)

- New `_canonical_topology(ob)`: rebuilds the bmesh-made mesh with vertices sorted by position (aborts on duplicate positions) and faces given as smallest-index-first corner loops (winding kept), sorted. Positions are untouched. Refuses meshes that already carry modifiers, materials, UVs or shape keys.
- `build_hair` (`hair_clumps/1`, the boy's legacy path): `_canonical_topology(mass)` → `G.displace_noise(...)` (unchanged) → `G.apply_mods(mass)`. No more 0.1 mm snapping on this path.
- `pipeline/charsys/geom.py` is not modified: `displace_noise` and its other callers are unchanged.
- `build_hair_v2` (`hair_clumps/2`, the unapproved H28 experiments) still uses T-038's `_bake_hair_mass` and is unchanged. Follow-up: it can adopt `_canonical_topology` the same way, but its scalp-cap join path then needs its own check.
- The `hair_clumps` object is not affected: its SUBSURF/DISPLACE stay unapplied modifiers after `G.join`, so its stored mesh is deterministic.

## Evidence

| Check | Result |
| --- | --- |
| `test_determinism.py` (boy) 3 runs in a row (`build/t038b/det_run1..3`) | PASS ×3, `changed_objects` and `strict_changed_objects` empty |
| Raw `hair_mass` across all 6 builds of those runs | coords SHA-256 `539afc733d32a667…`, loops `bf94628c44d11c3c…`, identical (order-sensitive) |
| 0.01 mm fingerprint files across all 6 builds | byte-identical, SHA-256 `c6aca097e2d843b1…` |
| Raw `hair_mass` of two builds before the fix (`det_before`) | coords and loop hashes differ (same sorted value set in that pair) |
| `test_determinism.py --character all` | PASS (boy and girl) |
| Girl fingerprints (0.1 mm and 0.01 mm) vs a build from the base commit | identical |
| `verify_charsys.py` | PASS. v6 geometry: missing/extra/count mismatches none, worst numeric difference 0.0 m. `hair_mass` exact hash differs from v6 (informational), as it already did on the base commit. |
| `tools/check_all.py --base origin/main` | see the task report / relay line |

Max coordinate change of `hair_mass` vs the T-038 output (nearest-vertex match, 3811 vertices, 3752 faces): **max 0.082 mm** (≤ √3·0.05 mm, i.e. the removed per-axis snap), mean 0.047 mm, bbox ≤ 0.040 mm, centroid 0.001 mm. Against unsnapped Blender evaluation the change is float-ulp level, because the same Blender modifiers evaluate the same surface.

## Limitations

- Verified with the bpy 5.3.0 module on Linux. The Windows Blender 5.3 executable was not run here. The fix does not depend on thread count.
- The `.blend` container bytes are still not canonical (see T-038).
