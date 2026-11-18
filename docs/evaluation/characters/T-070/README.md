# T-070: hair v3 round 2 (`groom/2`): closing the visual gaps to the references

Date: 2026-11-18. Blender: bpy module 5.3.0 (Linux, CPU, Cycles + OIDN) through `tools/bpy_blender.py`.
Status: **candidate for owner review (path B).** Nothing is published, approved or promoted. No character spec
changed; all current characters build byte-identically (they do not pin `groom/2`). Round 2 is shown through the
candidate spec overrides in [candidates/](candidates/).

Primary hair reference: `assets/references/owner_uploads/turnaround_all_three_2026-11-17.webp` (all views below
are matched to it by eye), plus each character's own front reference (last column of each sheet).
Bases: current approved versions — boy `boy_yellow_hoodie.spec.json` + `1.1.0.override`, girl
`girl_auburn_bun_glasses.spec.json` + `0.10.0.override` (both from `fidelity_baseline.json`). The third character
still has no spec: her base is T-044's stand-in (girl body/face/outfit with her colours), so only her head colours and
hair are evidence.

## Render vs reference

Row 1 = owner turnaround (last column: the character's own front reference); row 2 = round 2 render (ortho,
`character_neutral/1`, Cycles 16 spp + OIDN; last column = a crop of the same front render, not an extra render).

- Boy: [sheets/boy_render_vs_reference.jpg](sheets/boy_render_vs_reference.jpg)
- Girl: [sheets/girl_render_vs_reference.jpg](sheets/girl_render_vs_reference.jpg)
- Third character: [sheets/third_render_vs_reference.jpg](sheets/third_render_vs_reference.jpg)
- Head turns (2 s, ±40° yaw, 12 fps, MP4): [boy](media/boy_head_turn.mp4) · [girl](media/girl_head_turn.mp4) ·
  [third](media/third_head_turn.mp4); strips (every 3rd frame): [boy](media/boy_head_turn.jpg) ·
  [girl](media/girl_head_turn.jpg) · [third](media/third_head_turn.jpg)
- Single stills: `media/<character>_<front|threequarter|side_a|side_b|back>.jpg` (view yaws are in the sheet labels).
- Round 1 for comparison: [T-044 sheets](../T-044/README.md) (different cameras: reference-index cameras).

## What changed against round 1 (T-044)

### Shared generator `groom/2` (`pipeline/charsys/groom_hybrid.py`; both additions opt-in, absent = unchanged output)

1. **Arched clump lift** — a clumps row may give `"lift": [root, peak, tip]` and `"lift_peak"` (0.05–0.95, default
   0.6): the clump rises to the peak and settles back towards the scalp, giving rounded, puffy fleece leaves (boy)
   instead of flat leaves or straight spikes. Two-value lifts take exactly the old code path.
2. **Fixed fibre shaft** — a fibre layer may give `"shaft_radius_mm"` (+ `"tip_ratio"`, default 0.35): a small
   GN group (`PS Fibre Fixed Shaft/1`, built in `groom_hybrid.py`) after the shared fibre group sets a constant,
   tapered shaft radius. The shared group (`materials/builder.py`, not changed) scales the shaft with fibre length
   (0.16 × length), which made long halo fibres thick and frizzy; with a fixed shaft, long fibres stay fine
   (smooth roving, third character). Layers without the key are unchanged.
3. Validation for both (`lift` must have 2 or 3 values, `lift_peak` range, `shaft_radius_mm` in (0, 2],
   `tip_ratio` in 0..1).

`groom/2` is still pinned by no character, so these changes alter no existing build; the T-044 candidates still
validate (test).

### Candidate data (`tools/make_candidates.py` → `candidates/*.hair_v3.json`)

**Boy**
- All clumps rounder and puffier: thicker sections (thick ≈ 0.5 × width), shallow grooves (0.05 instead of 0.16),
  more irregularity, leaf tips with a slight outward flick; arched lifts on top/back/side clumps.
- Volume reduced: lower lifts everywhere, sides hug the head (no flare at the temples); base gather lower.
- Crown: 4 fat, short tufts (width 0.11–0.12 m) rising above the mass instead of thin horn-like spikes, plus
  3 thin curly flyaway loops.
- Fringe: 4 side-fringe clumps held at the brow line plus a broad central clump (`fringe_centre`, its own keep-out at
  el −1°) that hangs lower towards the brows.
- Colour 25/22/21 (was 19/16/15, rendered near-black; the turnaround reads charcoal).

**Girl**
- Fringe: the side-swept fringe sheets reach down to the brows at the temples (tip_el 21…−12° along the sweep, was
  24…−4°); the part-side sheet comes down the temple; keep-out el_min 5° (was 6°).
- Bun: larger (radius 0.118, height 0.17), higher (el 82°, was 76°) and multi-lobed (4 felt lobes, was 2).
- Ringlets: plumper (0.032–0.036 m wide, 0.03–0.034 thick), coils 0.019–0.02 m radius, pitch 0.078–0.08; 10 back
  ringlets (was 8), 3 per side in front of the shoulders (was 2); the smooth back curtain runs lower (leave el −14°,
  to ~z 0.55) so the curls start lower.
- Softer crown: fewer, shallower grooves (30 × 0.14, was 44 × 0.26); curtain column depth 0.15 (was 0.5).

**Third character**
- Waves: big soft S-waves the whole length (a nearly planar helix, `ellipse` 0.14, radius 0.032–0.042 m, pitch
  0.16–0.18 m, curl ramp starting at the scalp), wider locks (0.054–0.078 m); 9 back, 2 outer and 2 side locks per
  side.
- Smooth roving: fixed fibre shafts (0.14 / 0.10 / 0.07 mm), long lying fibres (2.6 / 6 / 10 mm, low curl), and
  material overrides without value blotches (`nap.value_gain` 0.05, `fibres.color_variation` 0.08,
  `micro_relief.color_strength` 0.2, `fibre.strength` 0.25). The material change is candidate data (overrides of
  the existing `felt hair` preset); `presets.json` is unchanged.
- Back mass wider from the crown down (curtain rest radii 0.215 × 0.17, az 76–284°), thin curtain under the locks.
- Fringe: 14 thinner, pointed clumps reaching the brows (was 8 short ones); buns larger (radius 0.072) and placed as
  in the turnaround (az ±54°, el 54°); bow larger (size 0.17, was 0.14).

## Measurements

### Face visibility (T-049 grid metric + T-044's occlusion-corrected variant; `data/<c>_facevis.json`)

| | T-044 front / 3/4 | **T-070 front / 3/4 (R / L)** | occluding front / 3/4 (T-044 → T-070) | eyes |
|---|---|---|---|---|
| boy | 0.981 / 0.940 | **0.996 / 0.953 / 0.958** | 0.977 / 0.981 → 0.993 / 0.999 / 0.998 | 1.00 / 0.99–1.00 |
| girl | 1.000 / 0.942 | **1.000 / 0.923 / 0.923** | 0.998 / 0.997 → 0.998 / 0.996 / 0.996 | 1.00 |
| third | 0.958 / 0.804 | **0.960 / 0.803 / 0.808** | 0.955 / 0.96 → 0.957 / 0.959 / 0.964 | 1.00 / 0.905 (T-044 0.905) |

- Boy: better than round 1 in every view.
- **Girl 3/4 is below T-044 on the T-049 metric (0.923 vs 0.942).** Ray attribution shows that all 130 blocked rays
  lie past the far cheek's silhouette and hit hair *behind* the face (side ringlets, curtain, temple masses); the
  occlusion-corrected value is unchanged (0.996 vs 0.997) and the eyes stay 100 % visible. The cause is the fuller
  side volume and the extra ringlet in front of each shoulder that the reference asks for; moving the side ringlets
  back by 10–18° did not change the number (the rays then hit the curtain). I kept the reference look (owner
  decision: visual fidelity over scores) — the Supervisor/owner should confirm this.
- Third: front better; 3/4 right 0.803 vs 0.804 (−0.001), left 0.808; occluding equal or better.

### Keep-out (build report, hair vertices inside the face window in front of the face)

boy 0 · girl 0 · third 4 (fringe-clump tip caps; T-044: 1). The boy's `fringe_centre` deliberately uses its own
keep-out (el −1°) and still reports 0 against the hair-wide window.

### Motion (T-049 head-turn proxy, `data/<c>_measure_t049.json`)

| | boy | girl | third |
|---|---|---|---|
| chains / chain bones | 39 / 78 | 23 / 103 | 37 / 114 |
| max lag in the turn | 11.8° | 14.2° | 14.2° |
| hair vertices > 2 mm inside body/garments, rest → turn max | 0.14 % (T-044 0.14 %) | 0.24 % → 0.25 % (T-044 0.11 → 0.13 %) | 0.16 % → 0.16 % (T-044 0.30 %) |

- The girl's plumper ringlets touch the shoulders more (deepest 29 mm at the turn extreme, as in T-044's 28 mm). The
  exported colliders are meant to resolve this in the engine; I did not run the engine solver.
- Third: the head-turn proxy integrates head yaw only (no gravity, no collision response), as in T-044.

### Build cost (`data/<c>_build.json`)

| | boy | girl | third |
|---|---|---|---|
| hair vertices / fibre points | 48.7 k / 3.16 M | 162 k / 3.71 M | 120 k / 7.65 M |
| hair build / peak RSS | 0.4 s / 787 MB | 1.3 s / 1372 MB | 1.0 s / 1552 MB |
| render (head-turn frame, 320 px, 8 spp) | 7.3 s | ~45 s | ~70 s |

The third character's fibre count doubled versus T-044 (fixed fine shafts need more fibres for the same coverage);
her renders are the slowest.

## Remaining differences vs the references (honest list)

### Boy
1. **Crown tufts:** fat and above the mass now, but they bend over like short hooks; the reference tufts are
   upright pointed leaves (two at the front pointing up-left/up-right). The thin flyaway loops are hardly visible.
2. **Clump shape:** rounder and puffier than round 1, but the reference clumps are longer, more clearly separated
   pointed leaves with lit tops and darker gaps; mine still merge into a mass in places, most in the back views.
3. **Silhouette:** less flared than round 1, but the outline is rounder/smoother than the reference's jagged,
   star-like outline; the top reads a little flatter.
4. **Central fringe:** hangs lower than the side fringe but not to between the brows (limited by the face-visibility
   requirement); the reference's long central clump reaches the brows.
5. **Not hair:** the face is longer and the skin darker/more orange than the turnaround (unchanged boy build under
   `character_neutral/1`); the head proportions make the hair look relatively larger.

6. **Not compared against the boy close-up upload.** `assets/characters/boy_yellow_hoodie/references/uploads/
   01_closeups_hair_top_crown_face_fleece_2026-11-17.webp` (top-down view, crown close-up) reached this branch with
   the staging merge after the iterations were done, so round 2 was not tuned against it. A visual check afterwards
   shows: (a) the clumps radiate as a rosette from a whorl near the **top** of the head, while my flow pole sits at
   the back crown (az 180°, el 66°); (b) the clumps are long, rounded-tip petals with visible fibre wisps, longer and
   more separated than mine; (c) the crown tufts are petals curling up out of that whorl. Matching it needs a
   further iteration (pole near el ~80°, longer petal clumps, crown tufts around the whorl).

### Girl
1. **Fringe:** now covers the forehead to the brows, but reads as a full, even fringe; the reference is clearly
   side-swept from the part with a rolled edge and a little forehead showing on the sweep side.
2. **Ringlets:** plumper and start lower, but they read as tight, regular rope coils (in the back almost like a
   knitted fabric); the reference curls are softer, looser and more varied. The smooth section above them shows
   vertical ribs where the reference shows long curved strands.
3. **Bun:** larger, higher and four-lobed, but rounder and smoother than the reference's deeply folded bun; the band
   is a visible blue-grey ring (the reference scrunchie is mostly hidden).
4. **Side volume:** close; the extra side ringlets lower the T-049 3/4 face-visibility number (see above).
5. **Colour:** unchanged from round 1 (close).

### Third character (test base)
1. **Waves:** big S-waves along the whole length now, but they are less regular and less clearly layered than the
   reference; some lock tips flick outward, and the reference's small curl texture inside the waves is missing.
2. **Texture:** smooth roving instead of frizz; the crown still shows faint vertical ridges (crown/curtain grooves)
   where the reference is smooth and combed.
3. **Fringe:** denser and reaching the brows, but straighter-edged and slightly shorter than the reference's soft
   wispy fringe.
4. **Bow:** larger but still flatter and less puffy than the reference's four round loops (the owner chose the
   bow; the turnaround shows a flower in that place).
5. **Buns:** size/placement close; slightly smoother than the reference.
6. Her body, face, eyes and outfit are a stand-in (not hers); judge only the hair and head colours.

### All characters
- Fibres still have a random lie direction (the shared fibre group has no combing direction), so long fibres cannot
  follow the strand flow the references show.

## Render budget

- Evidence-quality stills (16 spp + OIDN, 512–560 px wide): **30**. 15 final (5 per character, all in the sheets)
  + 15 of a first final pass that was superseded after the face-visibility fixes. No separate close-up renders
  (close-up columns are crops of the front stills).
- Head turns: **3** (24 frames each, 320 px, 8 spp + OIDN; the girl's and the third character's in frame ranges).
- Not evidence: about 80 iteration tiles (240–280 px, 6 spp) in 17 side-by-side iterations, plus 2 test tiles.

## Files

- `pipeline/charsys/groom_hybrid.py` — arched clump lift, fixed fibre shaft, validation (see above).
- `pipeline/charsys/tests/test_hair_v3_r2.py` — new plain-Python test (20 checks): T-070 candidates validate and pin
  `groom/2`, new keys validated, T-044 candidates still valid, published specs do not pin `groom/2`.
- `docs/evaluation/characters/T-070/` — this report, `candidates/` (overrides + `characters.json`, third base copied
  from T-044), `tools/` (copied from T-044; `make_candidates.py` round-2 data, `preview.py --tall`,
  `make_sheets.py` rewritten for the turnaround), `sheets/`, `media/`, `data/`.

### Reproduce

```sh
B=<blender>  # bpy 5.3 wrapper
$B -b --factory-startup -P pipeline/charsys/build_character.py -- --spec <spec> --override <current override> --out base/<c> --no-glb --no-compare
python3 docs/evaluation/characters/T-070/tools/make_candidates.py
$B -b --factory-startup -P docs/evaluation/characters/T-070/tools/build_candidate.py -- --base base/<c>/<id>_master.blend \
   --candidate docs/evaluation/characters/T-070/candidates/<c>.hair_v3.json --out final/<c>
$B -b --factory-startup -P docs/evaluation/characters/T-070/tools/preview.py -- final/<c>/<id>_hairv3.blend ev/<c>_views.png \
   <centre> <ortho width> <yaws> --px 512 --spp 16 [--tall 1.7]   # boy 0,0.01,0.87 0.56 0,-45,60,-120,180 (px 560);
   # girl 0,0,0.72 0.9 0,-150,-90,60,180; third 0,0,0.75 0.85 0,30,-100,95,180
python3 docs/evaluation/characters/T-070/tools/make_sheets.py ev docs/evaluation/characters/T-070
$B -b --factory-startup -P docs/evaluation/characters/T-070/tools/face_visibility.py -- final/<c>/<id>_hairv3.blend facevis.json
$B -b --factory-startup -P pipeline/charsys/experiments/hair_study/measure.py -- final/<c>/<id>_hairv3.blend turn/<c> --render
```

## Checks

After `git merge origin/staging` (e449ef1):
`python3 tools/check_all.py --base origin/main --task T-070 --full --blender <bpy 5.3 wrapper>` with the pinned
OpenImageDenoise 2.3.3 (`PLUSH_OIDN_ROOT`) and the apt list from `.github/ci-dependencies.json`:

- PASS: frozen assets; write-set (T-070: 47 paths, all inside the claim); shared-systems lint; C++ build; C++ tests;
  Python tests and links; Blender tier, full (verify_charsys, determinism, export, face, groom, garment, all-character
  regression: boy_yellow_hoodie PASS (fidelity 66.42), girl_auburn_bun_glasses PASS (64.40),
  girl_white_hair_blue_dress PASS (no spec yet, not buildable)). Existing characters are unchanged: none pins groom/2.
- **FAIL (guarded path, needs Supervisor approval):** `pipeline/charsys/tests/test_hair_v3_r2.py` — the new test file
  named by the T-070 write-set (`pipeline/charsys/tests/test_hair_v3*.py`). I did not add a `Supervisor-Approved`
  trailer myself.

GitHub "Quality gate" run 44211775029 (commit 7f72ea6, full tier): the same result: every check PASS
(regressions boy 66.42, girl 64.41, third PASS) except **Guarded paths** (`test_hair_v3_r2.py`) and **Merge status**
("tests FAIL after merge", which only repeats the guarded-path failure). The Gate verdict is therefore red until the
Supervisor approves that file.

`python3 pipeline/charsys/tests/test_hair_v3_r2.py`: 20/20 PASS; `test_hair_v3.py` (T-044): 30/30 PASS.

Not tested: engine import/playback of round-2 packages; the engine hair solver; a production build through
`build_character.py` with a groom/2 pin (no character pins it); GPU render times.
