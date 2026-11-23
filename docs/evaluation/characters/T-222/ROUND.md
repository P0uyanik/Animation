# T-222 round file (L1: garment push-out + cloth evaluation): PAUSED (owner freeze 2026-11-23 ~19:07Z)

Keep this current each round so a fresh session can take over. Branch `t-222-claude-garment-contact`, input
`origin/main@625c634` (main a3c17b8 merged in for the R8 write-set). Opt-in only: `shot_render.py --garment-pushout`
/ per-shot `production.render.garment_pushout` (run_shot.py forwards it); without them nothing runs.
Blender: bpy 5.3.0 module through `tools/bpy_blender.py` (the `blender` wrapper).

## State at the freeze
| # | Target | State |
| --- | --- | --- |
| A1 | Opt-in, identity without the flag | **done**: s020 f100 (320x180, 8 spp) main vs branch, no flag: 0 / 57600 pixels differ (PNG metadata stamps only) |
| A2 | garment_body before / after, s020 + seated shot | s010 f1-80 measured for v1 only (table below); **current version (v4) not yet audited**; s020 off/on blends were built for v1, audits stopped |
| A3 | 0 pops > 5 mm per character, every frame (HARD, R8) | **v4 passes on s010 f1-80: 0 pops** (max added: boy 0.0, auburn 2.4, white 0.6 mm). s020 not yet run |
| A4 | No garment worse with push-out on (R8) | open: v1 had white tights 9.2 -> 17.1 mm; v4 not audited. If still worse: exclude `ps_garment_type` tights (skin-tight layer, rest clearance < margin) with that reason |
| B | Cloth evaluation, STATUS + wait for go | evaluated (below); strict sheet not rendered; STATUS not sent; recommendation drafted: **do not build B now** |

## Part A: how it works now (v4, `pipeline/charsys/garment_pushout.py`, module doc has the detail)
Per garment vertex: a skinned rest-outward direction (two hidden proxies), rest clearance c0. Per frame (GN, LAST
modifier of the garment, after its body_collision shrinkwraps): inside = winding number along +dir and -dir both > 0
(4 crossings each); deeper than `max_winding` 1 (body overlapping itself) is left; exit by the nearest surface point
within a 150 deg cone, else along dir; soft clamp to the rest clearance (rest pose unchanged, layers keep their order);
move faded 20 -> 30 mm; two passes; then a **rate limit**: a simulation zone lets each vertex's push change by at most
`max_step_m` 3 mm per frame. Its state is a sparse cloud (pushed vertices only, at (index, 0, 0)), baked once over the
shot (`GarmentPushOut.bake()`, scene-wide bake with an explicit selection; garment overrides made editable) and packed
into shot.blend: s010 80 frames = 490-600 s bake, +52 MB blend.

History of the pop number on s010 f1-80 (fast scan `tools/popscan.py`, same count as contact_audit's garment jumps):
v1 stateless, cap 50-80 mm: 51 pops (max +61.8) · v2 two-direction inside + cap 20-30 mm: 10 (max +22) ·
v3 rate limit before the shrinkwraps: 1 (+8.1, shrinkwrap re-projection) · **v4 rate limit last in stack: 0**.

Blender 5.3 crash found and avoided: Sample Nearest on a point cloud inside the simulation zone segfaults within 40
frames of s010; the lookup runs on a vertex-only mesh (Points to Vertices) instead.

### s010 f1-80 garment_body, v1 (superseded; for the order of magnitude), max mm off -> on
boy 31.1 -> 22.8 (pocket 31 -> 0, gusset 9 -> 0) · auburn 30.1 -> 27.0 (shorts 30.1 -> 22.6, blouse frames 80 -> 21)
· white 22.8 -> 17.1 (hem rib 23 -> 0, skirt 22.5 -> 1.8, tights 9.2 -> 17.1 worse). Full: `results/s010_v1_cmp.txt`.
Deep cases left by design: vertices inside where the seated body overlaps itself (knee pit, lap), exits 80-95 mm.

## Part B: cloth evaluation (not implemented; waiting for the go)
- Pieces: the prototype handles `dress`/`skirt` only: white `garment.dress.skirt` (0.1.0 master already tagged
  `ps_cloth_sim`). Hood and other pieces would need new proxy builders.
- Cost: prototype `sit` 1.0 s/frame; in the s010 shot 3.1-3.2 s/frame (80 frames, other jobs running).
- Determinism (one machine): same cache sha256 twice, prototype (`32e5d747...`) and in-shot (`c279b82c...`).
- Penetration, s010 in-shot, cloth vs skinned (max mm / vertices inside): f30 0 / 0 vs 21.0 / 901; f70 9.7 / 1277 vs
  15.4 / 796; f80 12.3 / 1173 vs 15.6 / 807 (`results/cloth_s010_run*.json`).
- Look (preview `results/partB_preview_lap_s010_f30_f70.png`, left skinned, right cloth): seated, the cloth skirt is
  lifted by the thighs into a short stiff shell and shows the legs; the skinned skirt drapes over the knees. Changes
  the look.
- In a shot the prototype needs: proxy/collider linked to the scene collection (not the override collection),
  companions filtered to local objects, user-editable overrides and local mesh data for the Surface Deform bind
  (`tools/cloth_shot.py` patches these in memory).
- Recommendation (draft): do not build B now; part A already takes the seated skirt from 22.5 to 1.8 mm. Revisit
  cloth for standing / walking loose motion with a softer setting and the arms as colliders.

## Next steps (when resumed)
1. Re-apply v4 to s010 and audit (`tools/apply_gpush.py`, `contact_audit.py audit --frames 1-80 --step 1 --classes
   garment_body`, `tools/gcmp.py` against `results/s010_off_audit.json.gz`); check A4 (no garment worse), decide tights.
2. s020: build the on blend with `shot_render --blend-only --garment-pushout` (off blend + bake: ~45 min + bake ~25 min;
   run one Blender job at a time, the s020 build takes ~8 GB), popscan 1-208 (hard 0), audit every frame off / on.
3. Strict sheet (`tools/review/shot_sheet.py`): s010 f30/f70 white lap + auburn shorts, columns off / push-out / cloth;
   then part-B STATUS and wait for the go.
4. READY: tests to register `pipeline/charsys/tests/test_garment_pushout.py` (synthetic, ~1 min, 26 checks incl. the
   baked rate limit); guarded files touched: shot_render.py, run_shot.py, bake_package.py (RENDER_CODE + module).

## Dev tools (`tools/`, evaluation only)
apply_gpush.py (push-out onto a copy of a keyed shot.blend, incl. bake) · popscan.py (T-194 pop rule, every frame) ·
popdiag.py / diag.py / trace.py (per-vertex diagnosis) · gcmp.py (off/on audit table) · cloth_shot.py (cloth
prototype in a shot) · render_frames.py.
