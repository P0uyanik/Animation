# T-089b: face polish (boy heavy lids, girl rounder face and wider eyes)

Implementer report data for T-089b (round 2 Phase D). Input SHA `a682abb` (`integration/phase-d`); branch
`t-089b-claude-face-polish`. Blender used for everything here: the **bpy 5.3.0 module** (Python 3.13) behind a
`blender` wrapper (no Blender binary in the cloud container). Owner notes: `docs/process/OWNER_DECISIONS.md`
2026-11-18 ~22:35Z. The T-090b girl-face proposal is **not** adopted (none of its values are used).

## Owner evidence
| | boy (2.0.0 vs T-089b) | girl (0.11.0 vs T-089b) |
|---|---|---|
| strict sheet (T-087 recipe, Cycles 16 spp) | [boy_2.0.0_vs_face3b_strict.jpg](boy_sheet/boy_2.0.0_vs_face3b_strict.jpg) | [girl_0.11.0_vs_face3b_strict.jpg](girl_sheet/girl_0.11.0_vs_face3b_strict.jpg) |
| blink / glance strip (Cycles 16 spp) | [boy_blink_glance_strip.jpg](boy_sheet/boy_blink_glance_strip.jpg) | [girl_blink_glance_strip.jpg](girl_sheet/girl_blink_glance_strip.jpg) |
| recipe | [boy_2.0.0_vs_face3b.recipe.json](boy_2.0.0_vs_face3b.recipe.json) | [girl_0.11.0_vs_face3b.recipe.json](girl_0.11.0_vs_face3b.recipe.json) |
| cheap preview (Cycles 8 spp; not for approval) | [boy_preview_strip.jpg](preview/boy_preview_strip.jpg) | [girl_preview_face.jpg](preview/girl_preview_face.jpg) |

Sheet columns: original reference | current approved | T-089b candidate | AI target (B01/B02, G01/G02; face rows).
Strips: eye region, head only (no hair, clothing or glasses), neutral / blink 50 % / blink 100 % / glance (eye bones
15 deg), front and 3/4 (yaw −35), columns **current approved | T-089 candidate | T-089b candidate**; made with
[face_strip.py](face_strip.py) + [compose.py](compose.py) (T-087 light rig, 70 mm, 6 deg elevation).

## Candidates (spec data; no published file or `*.spec.json` changed; no version bump)
Each is one complete override on the published spec (= the T-089 override with the changes below; the metadata lists
them under `changes_from_T-089`).
- `assets/characters/boy_yellow_hoodie/spec/candidates/T-089b/boy_face3b.override.json` on `boy_yellow_hoodie.2.0.0.spec.json`
- `assets/characters/girl_auburn_bun_glasses/spec/candidates/T-089b/girl_face3b.override.json` on `girl_auburn_bun_glasses.0.11.0.spec.json`

**Boy: sleepy heavy lids, eye size kept.** Only two values change against T-089:
- `eyes.lids.upper_edge_deg` 14 → **4**: the flat felt lid line comes down over the top third of the iris, as in
  hero24 / val27 and B01. Eyeball (r 52 mm, spherical), socket, trims, lid rolls and lid line are unchanged.
- `eyes.felt.highlight` z 0 → −0.12: the single highlight stays below the heavier lid.
- Tried: 6 deg (h/w 0.51, a little alert), 0 deg (lid at the pupil, reads closed).

**Girl: rounder, fuller face; wider, rounder eyes.**
- Face (`face.shape`, the existing face_generic/2 round-face options): outline superellipse (roundness 0.9,
  exponent 2.6), lower face 16 mm wider per side at its widest (band 40 mm below the eye line), cheek fullness
  3 → 10 mm (radius 50 → 55 mm), rounded jaw corners (0.6, 3/4 view). Layout (mouth, nose, chin) unchanged.
- Eyes: radius 48 mm kept; the eyeball is narrowed less (x scale 0.9 → **1.03**); lid edges opened (43/−46 →
  52/−54 deg); upper outer trim 66 → 72 deg; blink overlap 14 → 33 deg (the wider eye needs it to close at 3/4).
- Socket: wall smoothing 10 → 25 and the new **corner relax** (25 passes, below).

## Code: one opt-in `face_v3` socket option
`pipeline/charsys/face_v3/socket.py`: `eyes.socket.corner_relax_iterations` (default **0** = unchanged),
`corner_relax_deg` (14), `corner_relax_factor` (0.5). A weighted Laplacian relax of the skin in a narrow azimuth band
at each eye corner, the opening's own vertices included. Why: a wider (less narrowed) girl eyeball makes the opening's
corner meet the socket wall at a sharp fold. T-081's wall smoothing cannot reach it, because it keeps the opening
fixed. Isolated on girl builds (T-081 fold probe, eye corner; 0.11.0 = 40.3 deg):

| variant | corner fold deg |
|---|---|
| T-089 candidate | 35.2 |
| + face shape only | 35.2 |
| + lids 52/−54 (scale 0.9) | 34.2 |
| + x scale 1.0 | 66.1 |
| + x scale 1.0 + socket corner 56 deg | 91.9 |
| + x scale 1.0, wall smoothing 25 | 46.9 |
| + x scale 0.97, wall smoothing 40, corner blend/close | 54.4 |
| + x scale 1.0, wall 25, **corner relax 20** | **32.0** |
| final (x 1.03, corner relax 25) | **34.4** |

Default path unchanged: the T-089 girl candidate rebuilt with the new code gives the identical face build report and
identical `body_skin` vertices (the lid/ear meshes hold the same vertex sets; only their vertex order differs between
builds, from code this task did not touch). No character name in the shared code (tested).

## Measurements (T-089's `measure_eyes.py`, front neutral, right eye; same tool for every column)
| | width mm | height mm | height / width | 3/4 near eye w × h | side w × h |
|---|---|---|---|---|---|
| boy 2.0.0 (T-089 README) | 48.8 | 26.5 | 0.54 | 50.0 × 26.3 | 17.5 × 25.0 |
| boy T-089 | 63.75 | 39.0 | 0.61 | 66.25 × 39.75 | 28.0 × 39.5 |
| **boy T-089b** | **62.25** | **29.75** | **0.48** (reference ≈ 0.45) | 65.75 × 30.75 | 28.25 × 30.5 |
| girl 0.11.0 (T-089 README) | 59.0 | 53.3 | 0.90 | 66.8 × 53.0 | 34.8 × 49.8 |
| girl T-089 | 61.25 | 59.0 | 0.96 | 68.75 × 59.0 | 37.0 × 57.5 |
| **girl T-089b** | **68.5** | **60.0** | 0.88 | 77.5 × 60.0 | 38.25 × 60.0 |

Girl eye width / eye-centre spacing (116 mm build spacing, the T-089 README's ratio): 0.51 (0.11.0) → 0.53 (T-089)
→ **0.59** (T-089b); reference 0.66 (sheet30). The opening height stays near 60 mm whatever the lid edges do: the
socket skin, not the lids, sets it.

Checks per candidate (from `test_face_v3b.py`, on the masters the sheets were built from):

| | boy T-089 → T-089b | girl T-089 → T-089b | limit |
|---|---|---|---|
| full blink residue front / 3/4 (mm²) | 0 / 0 → 0 / 0 | 0 / 27.2 → 0 / **8.4** | boy 2, girl 29.1 |
| 3/4 socket rim (share of past-corner shell visible) | 4.5 % → 8.8 % | 0.5 % → 7.8 % | 10 % |
| cheek / eye-corner folds (deg) | 12.2 / 59.5 → 12.2 / 59.5 | 19.5 / 35.2 → **14.2 / 34.4** | 45 / published (157.7, 40.3) |

## Tests
- `python3 pipeline/charsys/tests/test_face_v3b.py --blender <bpy wrapper> --unit --boy <T-089b boy master> --girl <T-089b girl master>`
  → **39/39 PASS**. New file. It reuses every test_face_v3 plain, unit and build check, with the same limits, on the
  T-089b candidates. It adds:
  - corner relax is opt-in (default 0); only the girl candidate sets it, and it ran;
  - boy: opening height/width ≤ 0.52 (0.478), width ≥ 60 mm (62.25);
  - girl: width ≥ 66 mm (68.5); the round-face options are in the build report.
- `python3 pipeline/charsys/tests/test_face_v3.py` (plain) 7/7; `test_versions.py` 94/94.
- Not run: `ctest` and the engine image regressions (no engine or renderer file touched); `verify_charsys.py`;
  fidelity (`tools/fidelity`).

## Not done / open points
1. **Fit re-run (criterion 4, optional): not run.** T-091's hair candidate is still in progress
   (`t-091-claude-hair-r4`, no READY), so a fair silhouette fit is not yet possible.
2. **Girl width 0.59 of spacing, not 0.66.** Past x scale ≈ 1.03 the eye-corner folds (1.06: 42.6 deg) and the
   3/4 socket rim (1.06: 11.9 %) exceed their limits. Reaching 0.66 needs a socket or head change around the eye.
   An eye spacing change would also do it, but it moves the glasses and is an identity decision.
3. **Girl upper lid.** The reference eye is a full circle. The candidate's upper lid line and dark outer lash strands
   still cut the top of the iris slightly (sheet face rows). That is lash/lid-line styling, outside this task.
4. **Boy 3/4 rim 8.8 %** (T-089 4.5 %). The lower lid edge exposes a little more upper shell past the corner. It is
   within the 10 % bound and not visible in the sheet's face 3/4 row.
5. Boy eye-corner fold 59.5 deg (unchanged from T-089; T-089 open point 1). The corner relax might help here too;
   not tried, to keep the boy change to the lids only.
