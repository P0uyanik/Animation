# T-051: per-finger grasps on the grasp sites and the hand-shape table

Implementer: Claude (cloud), branch `t-051-claude-finger-grasps`, input `d2567cb` (`integration/t-094c`, T-112a merged).
Design: `docs/architecture/INTERACTION_AFFORDANCES.md` sections 2.3 and 5. Runs in parallel with T-112b (which keys
the `hand.<s>.band` tracks); this task only reads them.

## 1. Result
Complete, with one open point (section 7): the boy 2.0.0's fingers are wider than the felt cup's 45 mm band allows, so
on the current boy two fingertips stay up to 3.8 mm outside the band (every fingertip still rests on the cup, none
inside it, the thumb is opposed, the hands stay 63 mm apart).

## 2. Files
| Path | Purpose |
| --- | --- |
| `engine/anim/animation.h`, `animation.cpp` | `HandPose` per-finger fields, `fingertipRadius`, per-finger pose / grasp in `applyHandPose`, the T-051 tracks in `applyConstraints` (hand pose only) |
| `engine/anim/hand_shape.h`, `hand_shape.cpp` (new) | `plush.hand_shape/1` loader + validation, table, `findHandShapeDir`, `biased` (personality rest-curl bias), `keyHandShape` |
| `engine/CMakeLists.txt` | `anim/hand_shape.cpp` in `plush_anim` |
| `content/hand_shapes/*.hand_shape.json` (11, new) | `wrap`, `pinch`, `palm`, `hook`, `cradle` (design 2.3 values), `relaxed`, `point`, `count_1`..`count_3`, `chin_touch` |
| `tests/test_hand_shapes.cpp` (new), `tests/CMakeLists.txt` | 7 doctest cases (section 5) |
| `docs/evaluation/animation/T-051/*` | this report, measure tool + results, render helper, sheet script, eval shot, preview and strict sheet |

## 3. What was implemented
**Track contract (design 5), all optional; absent = today's pose, bit for bit.**
| Track | Value | Read by |
| --- | --- | --- |
| `hand.<s>.band` | (lo, hi, thumb): band from the grasp centre along the grasp axis (m, hand rest frame); thumb 0 opposed, 1 along, 2 tucked | T-112b keys it; T-051 reads it |
| `hand.<s>.graspFace` | box-face inward normal (hand rest frame); the solid is the slab `abs(dot(p - centre, n)) <= graspRadius` | new, optional (section 7) |
| `hand.<s>.f<k>` | (curl, spread, free) for finger k = 0 little .. 3 index; free >= 0.5 keeps it out of the search (pinch) | hand-shape table |
| `hand.<s>.thumb` | (opposition, curl) | hand-shape table |
| `hand.<s>.stagger` | frames per finger; default 1 with a band, else 0 | hand-shape table / band |

**Per-finger grasp** (`applyHandPosePerFinger`, used only when one of those tracks is keyed):
- Surface: cylinder (`graspAxis`), sphere, or box-face slab (`graspFace`); skin radius = `fingertipRadius` = half the
  mean spacing of neighbouring finger roots (from the skeleton; test boy 6.3 mm, girl 6.6 mm, engine skeleton 5.25 mm,
  boy 2.0.0 11.2 mm, girl 0.11.0 6.6 mm).
- Each finger: both segments close until any finger point (knuckle, both segment middles, tip) touches the surface;
  if that is not the tip, the distal segment closes on (to 1.25 of the full curl) until the tip touches; a finger that
  never touches closing both together (a short finger) searches the proximal curl that lets its distal segment reach;
  an open hand that already touches a flat face extends at most 0.3 of a full curl until clear.
- Band: the fingers' natural contact heights are moved as a whole into [lo + skin, hi - skin]; if they span more than
  that, spaced evenly across it in their order. Each finger reaches its height by its spread (a bracket grown outwards
  from no extra spread, only solutions that still touch; else the nearest touching one).
- Thumb: aimed at a direction in the plane of the grasp axis and the finger direction (phi = 0 along the axis on the
  thumb's side, growing away from the fingers), then curled onto the surface about the axis across it and the palm
  normal. Opposed: smallest phi with the tip on the other half of the object from the fingertips (split by the plane
  through the axis and the palm normal), on the surface and inside the band; along: phi nearest 0 that fits; tucked:
  aimed along the fingers, curl at most 0.6.
- Weights: per digit (stagger), the searched pose is blended with the hand-track pose as before (thumb: slerp).
- Stagger: each finger reads its curl and grasp weight `lag` frames late: closing index 0, middle 1, ring 2, little 3
  stagger steps; opening reversed; the thumb goes with the index. Direction = the grasp weight (else curl) over the
  stagger window.
- Nothing touches the wrist or the palm contact point (the hand bone does not depend on the fingers), so the T-047
  collision plan and the 0.3 mm contact correction are unchanged.

**Hand-shape table** (`content/hand_shapes`, one file per shape, unknown keys are errors so no per-character field can
slip in; ids must match file names; `kind` grasp / rest / gesture; grasp shapes need `approach`, `search`
(all / pinch / none), `thumb`, `pinch_radius` for a pinch, `palm` facing / up). `keyHandShape` writes a shape onto a
hand's tracks (pinch: non-index fingers keyed free). `biased(shape, bias)` adds a personality rest-curl bias (no
character data in the table). Wiring the table into the verb expander is the follow-up after T-112b (task file).

## 4. Measures on the e907 exchange (current cast: boy 2.0.0, girl 0.11.0)
`episodes/e907_exchange/shots/s010` as is vs `shots/s010_band` (= s010 + the two band tracks T-112b will key from
felt_cup's sites: boy R `grip` band 45-90 mm -> (-0.021, 0.024, 0); girl L `grip_b` band 10-55 mm -> (-0.024,
0.021, 0)). `build/measure_t051` (source here), every frame of each hold; `measure_s010.json`, `measure_s010_band.json`.

| Hand (frames, closed) | | worst tip-skin gap | deepest tip / knuckle centre vs surface | furthest outside the band | thumb (< 0 = opposed half) | wrist / palm vs no band |
| --- | --- | --- | --- | --- | --- | --- |
| boy R (f21-f51) | single search | 19.34 mm | -8.18 mm (inside) | 29.95 mm | +2.5 mm | |
| | per finger | **0.00 mm** | +11.15 mm | 3.83 mm (section 7) | **-19.5 mm** | **0.000000 mm** |
| girl L (f48-f66) | single search | 13.62 mm | -7.02 mm (inside) | 10.80 mm | +5.8 mm | |
| | per finger | **0.00 mm** | +6.60 mm | inside (6.27 mm margin) | **-24.3 mm** | **0.000000 mm** |

Closest boy-girl digit points at the shared hold (f45-f51), minus both skin radii: single search 56.5 mm, per finger
62.7 mm (the hands never meet). Boy fingertip heights at f48 (prop frame, thumb first): 46.8, 91.9, 71.2, 63.7,
41.2 mm; girl: 48.7, 16.6, 27.3, 37.8, 48.4 mm.

## 5. Tests
| Command | Result |
| --- | --- |
| `cmake --build build` (Release, PLUSH_BUILD_STUDIO=OFF, renderer OFF) | builds, no warnings |
| `build/tests/plush_tests` | **186 / 186** cases (179 before + 7 new), 765360 assertions; golden `interaction_hashes.json` (linux-x86_64-gcc-13) passes unchanged |
| `build/tests/plush_tests -tc="*T-051*"` | 7 / 7 (below) |
| `ctest` (build/) | plush_tests passed; renderer tests skipped (renderer OFF, as before) |
| `tools/check_all.py --base d2567cb --task T-051 --blender <bpy 5.3 wrapper>` | Frozen PASS, Write-set PASS (18 paths, all in the claim), Shared-systems lint PASS, C++ build / tests PASS, Python tests and links PASS, **Blender tier PASS** (full tier: boy fidelity 67.42 vs baseline 67.63, girl 62.23 vs 62.29, white-haired girl PASS); Guarded paths FAIL = needs the `Supervisor-Approved:` trailer (expected) |

Blender: no binary on this runner; bpy 5.3.0 module through `tools/bpy_blender.py` (as the CI adapter).

New cases (`tests/test_hand_shapes.cpp`; boy = `boy_yellow_hoodie_1.0.0`, girl = `girl_auburn_bun_glasses_m3` test
packages, engine = `girl_white_hair` SDF skeleton, as every engine test):
1. cup, both bands (`grip` 45-90, `grip_b` 10-55), three skeletons, f24 and f30 of a grasp scene: worst tip gap
   0.50 / 0.43 / 0.00 mm (single search 8.15 / 13.62 / 7.87 mm), no point inside, every tip (thumb too) inside the
   band, thumb on the opposite half (-27 / -25 / -25 mm), wrist and palm identical to the scene without the band.
2. box face, three skeletons, both hands: worst tip gap 0.00 / 0.00 / 0.02 mm, no tip inside.
3. stagger: at f13 of a 10-14 close index 16.4 deg, middle 10.6, ring 4.7, little 0.0; done 3 f after; opening reversed;
   no stagger without a band or with `stagger` 0.
4. no T-051 tracks (or tracks without keys): pose bit-identical to the single search.
5. table: 11 shapes, the five grasp shapes with the design 2.3 values, `relaxed` = the engine rest hand, no character
   id or name in any file, `biased`.
6. validation: every problem reported (unknown key, range, id mismatch, missing approach / pinch radius, enums).
7. gestures through `keyHandShape` + `applyConstraints` on three skeletons: point / count_1..3 extend the right
   fingers (index reach 81.9 / 57.6 / 56.6 mm vs little 60.8 / 40.0 / 26.2 mm), chin_touch poses.

Not tested: the hand-shape table driving a shot (wiring into the verb expander is a follow-up); `pinch` on a real
prop (no small-prop scene at this SHA); Windows / clang toolchains (CI).

## 6. Baselines
- Frozen / published: none changed (`check_all` Frozen assets PASS; no file under `assets/characters/*/versions/`).
- Golden interaction hashes: unchanged (the file is untouched and the test passes); a scene without T-051 tracks
  never enters the per-finger path (`HandPose::perFinger()` false -> the original code, unchanged).
- Image regressions: renderer not built here (OFF, as on this runner); the engine renderer does not read hand tracks
  differently, and no regression scene has T-051 tracks.
- Guarded paths: `tests/CMakeLists.txt` and `tests/test_hand_shapes.cpp` need the `Supervisor-Approved:` trailer at
  merge (task file).

## 7. Problems, limitations, open questions
1. **Band vs the boy 2.0.0's hand.** His finger roots are 22 mm apart (skin radius 11.2 mm): four fingers need about
   88 mm, the felt cup's `grip` band is 45 mm (and the cup is 100 mm tall). The fingers are spread as far as they can
   while still touching; index 3.8 mm below and little 1.9 mm above the band. The girl and the test skeletons fit.
   The hands still stay 63 mm apart, so e907 is unaffected, but the band cannot hold all four fingers of this hand.
   Options (Supervisor): widen the cup's bands (content, T-112b / asset owner), let fingers that do not fit stay off
   the surface (free), or accept as is.
2. **Box face track.** A box face needs its normal, which today's tracks do not carry (`graspShape` gives a box no
   axis), so the per-finger path reads an optional `hand.<s>.graspFace`. Keying it from `graspShape` for box faces is
   in `engine/scene` (T-112b or the wiring follow-up). The slab ignores the face's side extents.
3. The cylinder surface is infinite along the axis (the anim layer does not know the cup's height); the band keeps
   the contacts on the cup.
4. Thumb on the boy 2.0.0: aimed about 110 deg from the axis to reach the band (his thumb root sits above it).

## 8. Visual
- Preview (Cycles 8 spp, 240x180): `t051_preview_cycles8spp.jpg`.
- Strict sheet (Cycles 32 spp, 480x360, identical cameras / lights / samples per row):
  `t051_hands_strict_sheet.jpg`. Rows: front (the boy's hand), back (the girl's hand), top (both wraps); columns:
  reference key frames (T-053a `pb_hands*`), single search, per-finger grasp.
- What changed: front, the boy's fingers now wrap the cup (creases of four separate curls; before, the flat hand
  stood off the wall); top, before the boy's thumb tip is inside the cup at the rim (the -8 mm penetration of
  section 4), after it lies on the outside; back, the girl's hand is nearly the same at this scale (her single-search
  fingers were already close), her fingers are slightly more closed.
- What stayed identical: wrist, palm, arms, cup, both bodies, camera and lights (same frame, same cast).
- Deviation from the references: the references show short, separate fingers with visible tips (girl at PB f098
  holding the boat with fingertips on both sides). The current hand meshes are mitten-like (fingers share one skin),
  so separate fingertips do not read even with per-finger curls; that is the character mesh, not this task's scope.
