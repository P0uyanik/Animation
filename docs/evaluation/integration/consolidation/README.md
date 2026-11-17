# Consolidation: `integration/consolidated`

Branch `integration/consolidated`, created from `integration/batch1` (f7b2f2c). It is pushed and has **not** gone to main: the owner approves it first.
Environment:
- Blender: bpy 5.3.0 in a Python 3.13 venv behind a `blender` wrapper (`tools/bpy_blender.py`).
- C++: Ninja build, embree 4.3.0 and OIDN 2.3.3 (official prebuilt).
- Cycles: CPU with OIDN.

Merges, each `git merge --no-ff`:

| # | Branch | Head | Result |
|---|---|---|---|
| 1 | `t-034-claude-garment-cloth` (T-026 → T-028 → T-028b → T-034) | c6608c5 | merged, 1 conflict |
| 2 | `t-033b-claude-hair-r2` | 1ed964f | merged, clean |
| 3 | `t-038-codex-build-determinism` | 5739c86 | merged, 1 conflict |
| 4 | `t-031b-claude-face-r2` | 03cd265 | merged after the wait rule (README present, 20 min without commits at 07:20 UTC); 2 conflicts |
| 5 | `t-040-claude-pose-clearance` | – | **not merged**; see below |

**T-040 was not merged.** The branch appeared at 07:08 UTC and was still receiving commits at 07:38, 07:52, 09:08 and 09:17. At the 3-hour limit (09:45 UTC, start 06:45) it had no `docs/evaluation/animation/T-040/README.md`. So the "mesh-based arm clearance ≥ 0" check does not apply. The clip and the e905/e906 numbers below use batch1's arm clearance (T-030, during IK only).

## 1. Conflicts and resolutions

| File | Merge | Resolution |
|---|---|---|
| `pipeline/charsys/materials/render_swatches.py` | T-034 | Kept both sides. Batch1's `render_engine.configure(scene, --engine cycles\|eevee)`, then T-034's `--denoiser oidn\|off` (Cycles only, applied after `configure`). The metadata keeps `engine_settings`; `denoiser` is `OPENIMAGEDENOISE`/`none` for Cycles and `OFF` for EEVEE. |
| `pipeline/charsys/build_character.py` | T-038 | Kept T-033's shared hair-fibre callback (`GROOM.build(..., hair_fibres)`) and T-038's `--timings` gate on `model_s`. All other T-038 determinism changes merged unchanged: seed, sorted iteration, `strip_runtime_timings`. |
| `assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json` | T-031b | One combined spec, **0.9.0** (section 2). |
| `pipeline/charsys/render_calibration.json` | T-031b | Kept T-026's key direction and strength (30/40 deg, 2.27) and fill (−20/10 deg, 0.637). Took T-031b's softer key angle, 28 deg. **T-031b's new Front fill was A/B-tested and not kept** (section 5). |

### A fix made during integration (not a merge conflict)

The owner's clip check (d) exposed a regression from T-034. On girl 0.9.0, a **60 cm grey-green spike** of shorts fabric followed the waving forearm in e904 s010 (`regression_found_shorts_spike_frame24_before_fix.png`).

- **Cause:** `drape.round_rim` bevels the shell rims with `bmesh.ops.bevel`, and the bevel interpolates the integer `ps_body_vertex` attribute of the new vertices between unrelated body vertices.
- **Effect:** `bind_to_body` copies weights from that body vertex. Five shorts leg-rim vertices at the crotch took `DEF-forearm.R` weights of 0.65–0.83.
- **Fix** (`pipeline/charsys/garments/drape.py`, commit 1425c84): after the bevel, every new vertex takes the source index of the nearest original vertex. Only skin weights change; geometry is unchanged, so determinism and fidelity are unaffected.
- **Result:** garment vertices whose skinning source is more than 5 cm away: blouse 21 → 0, shorts 15 → 0, boots 2 → 0.
- **Still open:** the vest still has 884 such vertices (1243 before the fix). These are its draped, hanging panels, sourced from nearby torso skin. The vest's arm weights stay on the shoulder/armhole, and the clip shows no artefact.
- `garment_generic_test` passes after the fix (final gate).
- **Workflow note:** `run_shot.py` caches unpublished masters by spec+override hash only, so code changes do not invalidate them. I moved the stale girl masters out of the three shot build folders before re-running.

## 2. Girl spec 0.9.0: provenance

`girl_auburn_bun_glasses.spec.json`, `metadata.spec_version` **0.9.0**.

**Version history.** Two branches had each labelled different content 0.8.0: T-031 (face) and T-033 (hair). That label is **retired** in `metadata.history` and is not used. T-031b's branch-local "0.9.0" (face only) is superseded by this combined 0.9.0, which the owner asked for. The history says so explicitly.

| Section | Source branch | Notes |
|---|---|---|
| `face` (whole section), `body.params.head`, `body.params.neck`, `identity.approved_decisions.neutral_expression` | **T-031b** (face v2 r2) | Identical to T-031b's spec. Its other sections were unchanged from batch1. |
| `hair` (structures, finish, components.finish, fibres, provenance), `materials.assignments.hair` | **T-033b** (felted hair v2 r2) | Identical to T-033b. |
| `clothing.garments`, `clothing.provenance` | **T-034** (garment fibres, cloth drape) | Identical to T-034. |
| `hair.dynamics` | **T-021** | Copied unchanged from `girl_auburn_bun_glasses.dynamics.override.json`. Its structure names (temple_puffs, side_curls, back_curls, nape_curls, bun) all exist in T-033b's groom. The override file is kept, and applying it again is idempotent (e904). |
| everything else (`schema`, `proportions`, `accessories`, `rig`, `fur`, `animation`, `components`, the rest of `body` and `materials`) | 0.7.1 (batch1) | No branch changed these. |

Checked programmatically: each section equals its source branch's section, and the sections changed by different branches do not overlap.

**Consequence:** the canonical e905/e906 now cast the girl **with** hair dynamics. Batch1 left this as a Supervisor decision. Her baked bones go from 174 (batch1 dynamics variant) to 239: T-033b's groom has 40 chains.

## 3. Gate (`tools/check_all.py --base origin/main --build-dir build/cpp --artifacts-dir build/check* --blender <wrapper>`)

| Check | Phase 1 (merges 1–3) | Phase 2 (+ T-031b, spec 0.9.0) | Final (+ drape fix, evidence) |
|---|---|---|---|
| Frozen assets | **FAIL**: `pipeline/blender/boy_pilot/fingerprint.py` | **FAIL**: same | **FAIL**: same |
| Guarded paths | **FAIL**: needs Supervisor approval (list in section 9) | **FAIL**: same | **FAIL**: same 18 files |
| Shared-systems lint, C++ build, CTest (4/4), plush_tests (83 cases, 21591 assertions), Python tests | PASS | PASS | PASS |
| Documentation links | FAIL, caused by my own stray OIDN download inside the checkout (removed); PASS on re-run | PASS | PASS |
| Blender tier | PASS: boy 64.20, girl 63.32 | PASS: boy 64.13 (−0.36), girl 65.41 (+2.37) | PASS: boy 64.13, girl 65.45 (+0.04 vs the proposed 65.41: run-to-run render variation; the drape fix changes only weights) |

**Frozen-asset failure.** T-038 changed `pipeline/blender/boy_pilot/fingerprint.py`, which is in `tools/frozen_manifest.txt`:
- fingerprint format v2;
- **default coordinate grid 0.01 mm → 0.1 mm** to avoid rounding-boundary noise;
- canonical hashing.

I kept the change because the owner ordered T-038 merged, and I did **not** update the frozen manifest. Two consequences:
- The coarser default grid is a loosening of the boy fingerprint test. T-038's determinism test still also checks a strict 0.01 mm fingerprint.
- This needs an explicit owner/Supervisor decision.

## 4. Test results

| Test | Result |
|---|---|
| `verify_charsys` (store 1.0.0) | PASS: geometry fingerprint ok, master byte-identical after all tests. Boy 1.0.0/1.1.0 published files unchanged (the frozen-asset check flags nothing in them). |
| `test_export_engine` | ALL PASS (13/13) |
| `face_test` (boy master, gate) | PASS |
| `face_system_test` (girl 0.9.0) | PASS: 36 states and 10 gaze poses, 0 eye/lid and 0 eye/glasses intersections. Eye visibility at rest 76.1 %, neutral mouth open 18.2 mm (teeth 7.7 %, tongue 9.9 %). Identical to T-031b's own numbers, so the merge did not disturb the face. |
| `groom_generic_test` | PASS (24 checks, 0 failures) |
| `hair_generic_test` | PASS |
| `tests/garment_generic_test.py` | PASS (phases 1, 2 and final, including after the drape fix) |
| `test_material_presets` | ALL PASS (54/54) |
| Determinism (`test_determinism.py --character all`: build twice, compare fingerprints) | PASS after merge 3 and again with spec 0.9.0. Boy and girl: 0 changed objects at 0.1 mm and at the strict 0.01 mm. |

## 5. Render calibration (T-031b): A/B result

Both runs use the same girl 0.9.0 master and the fidelity tool (5 views, 640 px, Cycles 32 spp). The only difference is T-031b's Front fill. `calibration_ab.json` has the full numbers.

| Region | With Front: ΔL* / ΔE00 | Without Front: ΔL* / ΔE00 | Pre-T-031b build (gate 1) |
|---|---|---|---|
| skin_face | +3.41 / 3.57 | **−0.99 / 3.49** | −15.50 / 13.53 |
| skin_limbs | +4.16 / 3.54 | **−0.39 / 2.71** | −8.07 / 6.70 |
| blouse | +2.22 / 9.25 | **−2.42 / 5.48** | −2.52 / 5.26 |
| shorts | +4.51 / 5.64 | **+1.25 / 2.62** | +1.25 / 2.40 |
| vest | +5.40 / 5.19 | **+1.73 / 2.76** | +4.66 / 4.27 |
| hair | +0.84 / 2.49 | −1.29 / 2.03 | −1.44 / 2.11 |
| score | 64.48 | **65.50** | 63.32 |

**Decision: the Front fill is not kept.**
- T-031b tuned it on the pre-T-026 lights, where the fill came from the side (−50 deg) and was blocked by the curls.
- On the merged lights, T-026's fill already sits near the camera axis.
- The face skin fix itself is T-031b's felt-skin bleed and warm skin, and it works without the extra light: face ΔL* goes from −15.5 to −1.0.
- With the Front fill added, the face gets no better and the limbs, blouse, shorts and vest all get worse.
- The 28 deg key angle is kept. It was not A/B-tested on its own; the boy moved 64.20 → 64.13 with it.

## 6. Fidelity (`tools/fidelity/run.py`, final gate numbers)

| Character | Score | Baseline | Subscores (colour / landmarks / proportions / regions / silhouette / texture) |
|---|---|---|---|
| girl 0.9.0 | **65.41** | 63.04 | 0.715 / 0.729 / 0.689 / 0.448 / 0.641 / 0.702 |
| boy 1.1.0 | **64.13** | 64.49 (−0.36, within the 2.0 policy) | 0.526 / 0.766 / 0.459 / 0.696 / 0.710 / 0.586 |

**Ranked differences, girl:**
1. Boots silhouette overlap 0.07, render area −90 %.
2. Hair accessory overlap 0.15, area +19 %.
3. Vest overlap 0.16, area −71 %.
4. Arms 26 % too short relative to height.
5. Hair accessory colour ΔE00 20.6.
6. Eyes overlap 0.31, area −11 %.
7. Limb skin overlap 0.36, area −34 %.
8. Face skin overlap 0.38, area −10 %.

**Ranked differences, boy:**
1. Leg gap 36 % too short.
2. Hair width at eye level −71 %.
3. Eyes overlap 0.02, area −39 %.
4. Limb skin area −67 %.
5. Backpack area −37 %.
6. Face skin ΔE00 20.7 (22 L* darker).
7. Eyes 24 % too small.
8. Eye area 41 % too small.

**Proposed baseline change (guarded).** `docs/evaluation/characters/fidelity_baseline.json`: girl 63.0418 → **65.4074**, with the source set to `fidelity/girl/fidelity.json`. The boy baseline is **left at 64.4891**: lowering it to the measured 64.13 would loosen the regression threshold. The drop is within policy and comes from the key angle.

## 7. Owner's visual check (evidence in this folder)

- `girl_0.9.0_turnaround_vs_reference.png`: front, 3/4, side and back, each next to its reference view. 800 px height, Cycles 64 spp + OIDN, shared calibration `character_neutral/1`, `groom_turnaround.py`.
- `girl_face_front_vs_reference.png`, `girl_face_34_vs_reference.png`: orthographic face close-ups (Cycles 64 spp), each next to a crop of the reference view. The references are 468 px tall, so their crops are upscaled and softer. Made with `make_face_closeups.py`.
- `girl_0.9.0_idle_wave_dynamics_2s.mp4`: e904 s010, 48 frames at 24 fps (2.0 s). Idle (`idle_relaxed`) + `wave`, head turns, hair dynamics on, batch1 arm clearance (T-040 not merged). 640×480, Cycles 16 spp + OIDN, `run_shot.py`. `girl_0.9.0_idle_wave_strip.png` shows every 8th frame.
- Fidelity: `fidelity/girl/overview.png`, `fidelity/boy/overview.png`, plus both `fidelity.json` files.

**What I see:**
- **Good:** face colour now matches the reference. Eyes, glasses, open-smile neutral and the felt vest/blouse/shorts read well. The wave is clean after the fix.
- **Hair:** the T-033b ringlets look frizzy/ropey and red-dark, not the smooth soft-brown felt waves of the reference. This is most visible in the close-ups: fibres and flyaways are harsh at close range.
- **3/4 view:** the side curls cover half of the face.
- **Head shape:** long forehead and neck; the reference is rounder, with a curtain fringe and visible ears.
- **Proportions:** boots too tall and too wide; arms short.

## 8. Regression: e905 / e906

Run with `run_shot.py --blend-only` (bake + per-frame Blender evaluation) and `measure_e905.cpp` (T-030). Files: `e905_measurements.json`, `e905_run_shot_blend_only.json`, `e906_run_shot_blend_only.json`, `e906_measure_shot/`.

| | Batch1 | Consolidated | Cause of the change |
|---|---|---|---|
| Eyes in sockets, boy e905 / e906 | 0.101 / 0.039 mm | 0.101 / 0.039 mm | – |
| Eyes in sockets, girl e905 / e906 | 0.002 / 0.0016 mm | 0.0004 / 0.0004 mm | T-031b eyes |
| Eyes in sockets, girl e904 clip | 0.0002 mm | 0.0002 mm | – |
| Bone reconstruction error | ≤ 0.0022 mm | ≤ 0.0031 mm (e904 clip), ≤ 0.0021 mm (e905/e906) | dynamics chains in the base spec |
| Girl baked bones | 174 (dynamics variant) | 239 | dynamics in the base spec, T-033b's 40 chains |
| Contacts: boy palm → grip at grasp / at hand-over; girl palm → grip_b | 0.00008 / – / 0.00013 mm | 0.00008 / 0.00008 / 0.00013 mm | – (exact, all < 0.001 mm) |
| Palm → socket while held | ≤ 0.00018 mm | ≤ 0.00013 mm | – |
| Prop jump at the parent switches; cup uprightness | 0.00016 / 0.00013 mm; cos 1.0 | 0.00016 / 0.00007 mm; cos 1.0 | – |
| Max cup speed | 16.8 mm/frame | 18.07 mm/frame (T-030: 18.0) | girl hand-over position (below) |
| Boy right arm, min gap at full IK / any IK weight | +7.13 / +1.24 mm | **+6.96 / +1.24 mm** | girl hand-over position (below) |
| Girl right arm, min gap at full IK / any IK weight | +5.25 / −20.2 mm | **+5.57 / −30.5 mm** | wider garment envelope (below) |
| Girl left arm, idle clip only | −35.5 mm | −41.4 mm | wider garment envelope (below) |
| Deeper than the clip arm during IK fades | 0.0 | 0.0 | – |
| e906 gaze / smoothness | PASS; boy 16.02, girl 19.13 deg/frame | PASS; boy 16.02, girl 19.13 deg/frame | – |
| e906 principles | girl arm.R ease 1.79, arc 0.169 | identical | – |

**Why the arm numbers moved:**
- The engine's body clearance model includes torso garment vertices (`engine/scene/interaction.cpp`, `bodyClearanceModel`).
- T-034's cloth drape makes the blouse and vest fuller: girl torso_upper side radii 84.1 / 73.4 → 94.8 / 79.8 mm, torso_lower side +5 mm. The pelvis front radius shrinks (98–106 → 93 mm).
- So the same clip arms read deeper against her (−41 mm idle left arm).
- Her hand-over hand also shifts, which moves the boy's IK path slightly: +6.96 mm at full IK, max cup speed +1.3 mm/frame.
- The full-IK gaps stay positive. The negative idle/fade gaps were outside T-030's scope, and T-040 is the task that makes them ≥ 0.

## 9. Guarded files (need Supervisor approval; no approval trailers were added)

Flagged by the gate:
- `pipeline/charsys/materials/presets.json`
- `pipeline/charsys/shot_render.py`
- `pipeline/charsys/tests/face_expression_sheet.py`
- `pipeline/charsys/tests/face_test.py`
- `pipeline/charsys/tests/fixtures/face_synthetic_b.override.json`
- `pipeline/charsys/tests/groom_dynamics_test.py`
- `pipeline/charsys/tests/groom_generic_test.py`
- `pipeline/charsys/tests/test_determinism.py`
- `pipeline/charsys/tests/test_export_engine.py`
- `pipeline/charsys/tests/test_material_presets.py`
- `pipeline/charsys/tests/test_render_engine.py`
- `pipeline/charsys/tests/test_shot_eyes.py`
- `pipeline/clips/measure_clips.py`
- `tests/CMakeLists.txt`
- `tests/garment_generic_test.py`
- `tests/test_interaction.cpp`
- `tests/test_secondary.cpp`
- `tests/test_shot_workflow.cpp`

Also guarded:
- `docs/evaluation/characters/fidelity_baseline.json`: the **proposed** girl baseline change. It is listed as guarded in `tools/guarded_paths.txt`; the gate does not flag it because an existing approval trailer already covers the path.

Frozen:
- `pipeline/blender/boy_pilot/fingerprint.py` (T-038; section 3).

## 10. Open problems

1. **T-040 not merged:** not ready within 3 hours. Merge it in a follow-up and repeat section 8 with its mesh-based clearance.
2. **The T-038 frozen file and its coarser fingerprint grid** need an owner decision.
3. **Hair look (T-033b)** vs the reference: frizzy ropes, too red-dark, harsh fibres at close range, and side curls covering the face at 3/4. Also the hair accessory colour (ΔE00 20.6).
4. **Girl proportions** (fidelity ranks 1, 3, 4): boots, vest coverage, arm length. Head shape: long forehead and neck, no ears.
5. **Vest skinning sources:** 884 vertices are sourced more than 5 cm away (draped panels). No artefact is visible, but a vest-specific check would be worth adding to `garment_generic_test`.
6. **Test gap:** no test caught the shorts spike. `garment_generic_test` should check `ps_body_vertex` source distance after drape/bevel.
7. **run_shot master cache** ignores code changes (key = spec + overrides).
8. **Canonical e905/e906 now include hair dynamics,** through spec 0.9.0. Batch1 had left this as a Supervisor decision.
9. **Boy fidelity baseline:** 64.49 kept, boy measures 64.13 (key 24 → 28 deg). Revert the angle, or accept and lower the baseline; either is the owner's call.
