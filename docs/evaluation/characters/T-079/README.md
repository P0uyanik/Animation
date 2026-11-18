# T-079: hair v3 round 3 (`groom/2`): boy crown/whorl, girl ringlets and fringe, third character fringe and waves

Date: 2026-11-18. Blender: bpy module 5.3.0 (Linux, CPU, Cycles + OIDN) through `tools/bpy_blender.py`.
Status: **candidate for owner review (path B).** Nothing is published, approved or promoted. No character spec changed
and **no generator code changed** (`groom_hybrid.py` untouched): round 3 is candidate data only, shown through the spec
overrides in [candidates/](candidates/). Approved characters cannot change: no published spec pins `groom/2`
(checked by the new test and the regression guard, see Checks).

Targets: `assets/references/owner_uploads/turnaround_all_three_2026-11-17.webp`, each character's own front reference
(last column of each sheet) and, for the boy, the close-up upload
`assets/characters/boy_yellow_hoodie/references/uploads/01_closeups_hair_top_crown_face_fleece_2026-11-17.webp`.
Bases: current approved versions from `fidelity_baseline.json` (boy spec + `1.1.0.override`, girl spec +
`0.10.0.override`); the third character still has no spec, her base is T-044's stand-in (only hair and head colours are
evidence). Starting point: T-070's round 2 ([report](../T-070/README.md)).

## Render vs reference

Row 1 = owner turnaround (last column: the character's own front reference); row 2 = round 3 (ortho,
`character_neutral/1`, Cycles 16 spp + OIDN; last column = a crop of the same front still = face crop).

- Boy: [sheets/boy_render_vs_reference.jpg](sheets/boy_render_vs_reference.jpg) and the close-up upload comparison
  [sheets/boy_closeup_vs_upload.jpg](sheets/boy_closeup_vs_upload.jpg) (top-down and crown views)
- Girl: [sheets/girl_render_vs_reference.jpg](sheets/girl_render_vs_reference.jpg)
- Third character: [sheets/third_render_vs_reference.jpg](sheets/third_render_vs_reference.jpg)
- Single stills: `media/<character>_<front|threequarter|side_a|side_b|back>.jpg`, plus `media/boy_top.jpg`,
  `media/boy_crown.jpg`. Round 2 for comparison: [T-070 sheets](../T-070/sheets/) (same cameras and yaws).

## What changed against round 2 (candidate data only, `tools/make_candidates.py`)

**Boy** (target 1: no horn-like tufts; spiky, taller crown with the whorl at the top; longer petal clumps; less
roundness and volume)
- Whorl moved from the back crown (az 180, el 66) to the **top** of the head (el 80); every clump and the felt base
  gather radiate from it. New `whorl` rosette: 5 short petals curling round the whorl point.
- Crown: the 4 fat, hooked tufts (arched lift) are replaced by **6 upright pointed petals** (straight rising lift
  0.03 → 0.12 m over a short 10–14° arc, so they stand up instead of bending over into hooks/horns) plus 3 thin wisps.
- Petal clumps longer (top 44–58°, was 36–50°; back 34–46°) and slimmer (thick ≈ 0.45 × width, was ≈ 0.5–0.6),
  pointed leaf tips (taper 2.2, was 1.6) with an outward flick: a jagged, star-like outline instead of a round one.
- Less volume: felt base height 0.016–0.03 m (was 0.022–0.04), lower lifts everywhere, side clumps narrower; the
  front side clumps moved 3° back (az 47–66) so the face stays as visible as in round 2.

**Girl** (target 2: varied, looser ringlets; soft swept fringe; keep the four-lobe bun)
- Ringlets: each group (side, back, outer) is split into **two interleaved sets** with different coil radius
  (0.016–0.022 m), pitch (0.07–0.095 m), length and curl start; per-lock jitter 0.22, wobble 0.2, sway 8 mm, start
  jitter 6 cm (round 2: 0.12 / 0.1 / 4 mm / 3 cm, one set per group). 13 back ringlets (was 10). Curls start
  closer to the scalp, so the straight ribbed band above them is shorter.
- Fringe: new `fringe_sweep` clumps — 7 slim felt strands from the part line that sweep across the forehead
  (flow towards the left temple, curved, grooved, lifted edge) over the felt fringe base, whose edge is now
  **diagonal** (high at the part, down to the brows at the sweep side) so a little forehead shows, as in the
  reference.
- Bun (four lobes), band, flowers: unchanged.

**Third character** (target 3: soft fringe, no jagged points; fluffy soft S-waves instead of rope-like strands)
- Fringe: 19 broad clumps in two overlapping layers with **blunt, rounded tips** (taper 3.2–4.0, was 1.4) and uneven
  lengths, instead of 14 pointed triangles. Own keep-out (el 6°) so no fringe vertex enters the face window.
- Waves: broader, flatter felt locks (flatten 0.4, was 0.35; back width 0.08–0.09 m, was 0.07–0.078), 12 back
  locks (was 9) and 3 side locks per side (was 2), so the locks overlap into one wavy mass; more irregularity
  (0.14), more wave jitter/wobble, calmer tips (no outward noodle flicks).
- Fluffier surface: halo fibre layer denser (7 / cm², was 4) and curlier (0.3, was 0.08), more flyaways; crown
  grooves 24 × 0.06 (was 40 × 0.14), so the crown no longer shows vertical ridges.

## Measurements

### Face visibility (T-049 grid metric + occlusion-corrected variant; `data/<c>_facevis.json`)

| | T-070 front / 3/4 R / 3/4 L | **T-079 front / 3/4 R / 3/4 L** | occluding T-070 → T-079 (front / R / L) |
|---|---|---|---|
| boy | 0.996 / 0.953 / 0.958 | **1.000 / 0.961 / 0.971** | 0.993 / 0.999 / 0.998 → 0.996 / 0.999 / 0.999 |
| girl | 1.000 / 0.923 / 0.923 | **1.000 / 0.923 / 0.923** | 0.998 / 0.996 / 0.996 → unchanged |
| third | 0.960 / 0.803 / 0.808 | **0.974 / 0.819 / 0.821** | 0.957 / 0.959 / 0.964 → 0.971 / 0.975 / 0.977 |

Eyes: 100 % visible for boy and girl in every view; third 1.00 front, 0.905 at 3/4 (unchanged from rounds 1–2).
**No value is worse than round 2.** (The girl's 3/4 T-049 number is still the round-2 0.923 explained in T-070: hair
behind the far cheek, not in front of the face.)

### Keep-out (build report): boy 0 · girl 0 · third 0 (round 2: 0 / 0 / 4).

### Build cost (`data/<c>_build.json`)

| | boy | girl | third |
|---|---|---|---|
| hair vertices (r2 → r3) | 48.7 k → 54.2 k | 162 k → 169 k | 120 k → 139 k |
| fibre points (r2 → r3) | 3.16 M → 3.11 M | 3.71 M → 4.22 M | 7.65 M → 10.3 M |
| chain bones (r2 → r3) | 78 → 96 | 103 → 112 | 114 → 145 |
| hair build / peak RSS | 0.5 s / 780 MB | 1.6 s / 1390 MB | 1.1 s / 1925 MB |

The third character's denser halo raises her fibre count by 35 %; she is the slowest to render.

## Remaining differences vs the references (honest list)

### Boy
1. **Top-down view vs the close-up upload:** the whorl is at the top now and the clumps radiate from it, but seen
   from above they read as flat overlapping leaves; the upload shows thick, rounded, sausage-like petals clearly
   separated by dark gaps around a round knot. Rounder petal sections would bring back the round-2 puffiness the
   task asked to reduce from the front; I chose the front/turnaround silhouette.
2. **Crown:** upright pointed petals, no hooks/horns, but they are shorter and more numerous than the 2–3 long
   leaves in the close-up crown view.
3. **Fibre wisps:** the reference's loose curly wisps over the petals are sparser in the render.
4. Not hair (unchanged boy build): face longer and skin darker/more orange than the turnaround.

### Girl
1. Ringlets are varied and looser, no longer identical rows, but still somewhat rope-like in the lowest row; the
   reference curls are softer and fuzzier. A short ribbed band remains between the smooth back and the curls.
2. Fringe: swept and diagonal now, but thinner/flatter than the reference's full rolled fringe.
3. Bun band still a visible blue-grey ring (unchanged; not in this task's scope).

### Third character (test base)
1. Waves: one soft wavy mass now, no separate ropes, but the reference's S-curls are more regular, smaller and
   stacked; mine are larger, looser and in places still ribbon-like at the lock ends.
2. Fringe: soft and blunt now; slightly heavier and more even than the reference's wispy fringe.
3. Bow flatter than the reference (unchanged); body/face/outfit are a stand-in.

### All characters
- Fibres still have a random lie direction (the shared fibre group has no combing direction); not changed here.

## Render budget

- Evidence stills (Cycles 16 spp + OIDN, 512–560 px): **17** (5 per character in the sheets + boy top-down and crown
  close-up). ≤ 30.
- Not evidence: 11 iteration strips at 260–360 px, 6 spp (boy 5, girl 2 + 2 face close-ups, third 2).
- Head-turn videos and the T-049 motion proxy were **not** re-run in this round (not in the acceptance list; chain
  counts are in the build reports).

## Files

- `pipeline/charsys/tests/test_hair_v3_r3.py` — new plain-Python test (25 checks): T-079 candidates validate and pin
  `groom/2`, the round-3 targets are present in the data, T-044/T-070 candidates still validate, published specs do
  not pin `groom/2`.
- `docs/evaluation/characters/T-079/` — this report; `candidates/` (overrides, `characters.json`, third base spec,
  copied from T-070); `tools/` (copied from T-070, `make_candidates.py` with round-3 data, `make_sheets.py` round-3
  labels, new `make_boy_closeup_sheet.py` and `iter.sh` iteration helper); `sheets/`, `media/`, `data/`.
- Not changed: `pipeline/charsys/groom_hybrid.py`, `pipeline/charsys/materials/presets.json` (allowed by the
  write-set, not needed).

### Reproduce

```sh
B=<blender>  # bpy 5.3 wrapper
$B -b --factory-startup -P pipeline/charsys/build_character.py -- --spec <spec> [--override <current override>] --out base/<c> --no-glb --no-compare
python3 docs/evaluation/characters/T-079/tools/make_candidates.py
$B -b --factory-startup -P docs/evaluation/characters/T-079/tools/build_candidate.py -- --base base/<c>/<id>_master.blend \
   --candidate docs/evaluation/characters/T-079/candidates/<c>.hair_v3.json --out final/<c>
$B -b --factory-startup -P docs/evaluation/characters/T-079/tools/preview.py -- final/<c>/<id>_hairv3.blend ev/<c>_views.png \
   <centre> <width> <yaws> --px 512 --spp 16 [--tall 1.7]   # as T-070 (boy px 560)
python3 docs/evaluation/characters/T-079/tools/make_sheets.py ev docs/evaluation/characters/T-079
# boy close-up: preview.py ... boy_top.png 0,0.01,0.9 0.42 0 --el 80 ; boy_crown.png 0,0.01,0.93 0.36 0 --el 22
python3 docs/evaluation/characters/T-079/tools/make_boy_closeup_sheet.py ev/boy_top.png ev/boy_crown.png docs/evaluation/characters/T-079
$B -b --factory-startup -P docs/evaluation/characters/T-079/tools/face_visibility.py -- final/<c>/<id>_hairv3.blend facevis.json
```

## Checks

After `git merge origin/staging` (23f10e4), on commit 6a5e424:
`python3 tools/check_all.py --base origin/main --task T-079 --full --blender <bpy 5.3 wrapper>` with the pinned
OpenImageDenoise 2.3.3 (`PLUSH_OIDN_ROOT`, checksum-verified prebuilt) and the apt list from `.github/ci-dependencies.json`:

- PASS: frozen assets; write-set (T-079: 41 paths vs origin/staging, all inside the claim); shared-systems lint;
  C++ build; C++ tests; Python tests and links; Blender tier, full (verify_charsys, determinism, export, face, groom,
  groom dynamics, garment, all-character regression: boy_yellow_hoodie PASS (fidelity 66.43, baseline 66.41),
  girl_auburn_bun_glasses PASS (64.41, baseline 64.40), girl_white_hair_blue_dress PASS (no spec yet)). Existing
  characters are unchanged: none pins groom/2.
- **FAIL (guarded path, needs Supervisor approval):** `pipeline/charsys/tests/test_hair_v3_r3.py` — the new test
  file named by the T-079 write-set (`pipeline/charsys/tests/test_hair_v3*.py`). I did not add a
  `Supervisor-Approved` trailer myself. This is the only failing check.

`python3 pipeline/charsys/tests/test_hair_v3_r3.py`: 25/25 PASS; `test_hair_v3_r2.py`: 20/20 PASS;
`test_hair_v3.py`: 30/30 PASS.

Not tested: engine import/playback of round-3 packages; the engine hair solver; head-turn motion proxy; GPU render
times.

Resource use: token usage not available.
