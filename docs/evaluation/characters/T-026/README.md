# T-026 Girl visual issues (fuzz, sheen, face skin, boot lining)

Status: **T-026a fuzz improved: 4 of the 6 fibre presets now pass (boot fleece is still 12% short). T-026b
determined: the sheen shortfall is in the shader, not the light or the denoiser; the measurement is now
VISUAL_TARGET-conformant and every sheen row still fails. T-026c cause found, partly fixed. T-026d fixed.**
No target value or test threshold was changed. Nothing was published or approved; the girl is still unpublished
and the boy (no material/garment opt-in) is untouched.

All changes are in shared, character-independent code: `pipeline/charsys/materials/` (builder, presets,
render/measure scripts), `pipeline/charsys/render_calibration.json` and the footwear lining in
`pipeline/charsys/garments/generator.py`. The girl's spec needed no change.

## a) Fibre fuzz (`PS Shared Surface Fibres/1`, presets)

Changes:
- The group is the same single shared group (now version 2) and still has no character branches.
  - It adds a per-fibre tilt spread (the `Lean Variation` input, up to ±60°).
  - It stores a per-strand `ps_fibre_tone` attribute on the curve domain.
  - The shaft radius is now 0.16 × length instead of 0.11. A 4–6 mm fibre is therefore 1.3–1.9 mm wide, which
    is the VISUAL_TARGET felt-fibre width of 1–2 px at H = 256 for the 0.256 m reference. The old shafts were
    under 1 px, which the target rejects as noise, and OIDN averaged them away.
- The fibre material (Principled Hair) gets four new preset fields, all 0..1:
  - `color_variation`: per-strand value scaled by 1 ± v;
  - `root_transparency` and `tip_transparency`: alpha fade at the root and at the tip;
  - `lean_variation`: the tilt spread above.
- Fibres now use the raw base colour. `saturation_compensation` offsets the surface's sheen/rim layers, which the
  fibres don't have; with dense fibres it pushed felt hair to 127% saturation.
- Density is now realistic. It was 0.6–1.2 fibres/cm², a sparse sprinkle. It is now 8–28 fibres/cm² (felt 28,
  boot fleece 26, fleece 22, wool yarn 18, felt hair 16, cotton knit 8). The `wide` LOD is still × 0.25.

Fuzz RMS (/255, median of three 64 × 64 px patches at H = 256; target 3–8):

| Preset | before (T-019 sheet) | after | |
| --- | ---: | ---: | --- |
| felt | 1.26 | **3.24** | PASS |
| wool yarn | 2.71 | **5.25** | PASS |
| fleece | 2.87 | **4.03** | PASS |
| felt hair | 1.58 | **5.55** | PASS |
| boot fleece | 2.29 | 2.65 | FAIL (12% short) |
| cotton knit | 2.33 | 2.51 | FAIL |
| skin-felt (must stay < 3) | 0.46 | 0.49 | PASS |

Render cost (480 × 576, 8 spp + OIDN, CPU, 4 cores, this machine): fibres on 1.85 s/frame vs fibres off
0.99 s/frame (+0.86 s/frame). T-019 measured +0.04 s/frame on a different machine with the sparse fibres.

Characters still don't attach GN fibres; only the swatch rig calls `add_fibres_geometry`. So the fuzz gain shows
on swatches, not on the girl's garments (see Remaining).

## b) Sheen P90/P50: light, metric or shader?

The diagnostics (iteration 2) used felt, wool yarn and skin-felt, measuring the sheen median on the sphere:

| Setup | felt | wool yarn | skin-felt |
| --- | ---: | ---: | ---: |
| 8 spp + OIDN (T-019 setup) | 1.0445 | 1.0343 | 1.0569 |
| 64 spp + OIDN | 1.0464 | 1.0385 | 1.0593 |
| 256 spp, no denoiser | 1.0445 | 1.0329 | 1.0588 |
| 64 spp + OIDN, grazing key (80° az / 20° el) | 1.0522 | 1.0476 | 1.0725 |

- **Denoiser/sampling:** at most 0.003. Not the cause.
- **Light:** the rig already has a rim (160°). A grazing key adds only 0.008–0.016. Not sufficient.
- **Metric:**
  - The definition is applied as written: P90/P50 of the pixels with Y / blur31(Y) ≥ 1.
  - The setup deviated from VISUAL_TARGET in one way: it measured one ROI instead of three patches with the
    median reported. That single ROI also reached past the sphere's silhouette into the backdrop. Its values
    were inflated, not depressed: three patches fully inside the sphere read lower (for example felt 1.024 vs
    1.045 at iteration 4).
  - The fix is `sheen_rois_px`: three patches on the key-lit side of the sphere (upper-left, left, top; centres
    at 0.55 R, 72 px at H = 256).
  - The same three-patch rule now applies to fuzz (`fuzz_rois_px`).
  - Pass now requires all of: median in range, at least 2 of 3 patches in range (VISUAL_TARGET step 3), and no
    patch missing its nearest limit by more than 20%. The median condition makes this stricter than the
    document's rule.
- **Shader (the cause):**
  - For near-Gaussian texture, P90/P50 ≈ 1 + 0.97 σ_rel. The target (≥ 1.08) needs about 8% relative luminance
    modulation below the 31 px scale.
  - The surfaces had about 2%. Fuzz must stay ≤ 8/255, so the missing structure has to sit in the 9–31 px band:
    nap clumps and highlights broken by fibre, not finer grain.
  - The benchmark crops confirm it. Measured with the same code at H = 256, soft sleeves give 1.04–1.14: plain
    sleeves 1.04, sleeves with fibre-broken highlights 1.11–1.14.
- After this task's fibres: felt 1.045, felt hair 1.064, boot fleece 1.063, fleece 1.040, wool yarn 1.039. All
  sheen rows still fail. A mid-scale nap/clump sheen layer in the shared shader is the next step (Remaining).

## c) Face skin greyer than body skin

The face and body share one mesh (`body_skin`) and one material (`M_skin_face`); only the hands use `M_skin`.
Diagnostic variants on main (iteration 1; face band = body_skin above 45% of the frame):

| Variant | face Y' | legs Y' |
| --- | ---: | ---: |
| baseline | 115.5 | 140.2 |
| hair hidden | **138.2** | 140.2 |
| glasses hidden | 117.4 | 140.2 |
| body material on the face | 116.0 | 140.2 |
| subsurface off | 116.4 | 140.4 |
| key light only | **38.3** | 93.7 |

- **Cause:** occlusion. The groom hood (fringe, temple puffs, side curls together; no single object) blocks the
  key and the −50° side fill. It is not the material slot, preset, normals or SSS. Chroma is equal (face S50 22%,
  legs 23%; R/B 1.29 vs 1.30): the face reads grey because it is darker.
- **Shared fix 1, calibration:**
  - Key moved from 35/45° to 30/40° (still inside VISUAL_TARGET's 25–45° / 35–55°), with a 24° source for a
    0.03–0.10 H facial penumbra.
  - Fill moved from −50/15° to −20/10°, towards the camera axis, where framing hair, hoods or hats can't block it.
  - Strengths renormalised so the documented front-facing irradiance is unchanged (key 2.6 → 2.27, fill
    0.95 → 0.637).
- **Shared fix 2, preset:** a new surface field `shadow_transmission` (0.75 per surface crossing, ≈ 0.56 per
  closed rope) on the plush-hair presets (wool yarn, felt hair). Porous yarn locks cast partial shadows; camera,
  diffuse and glossy rays still see the full shader.
- **Result (`girl_skin_metrics.json`):**
  - face band Y' 112.5 → 120.5;
  - face/legs 0.80 → 0.84 (band) and 0.767 → 0.781 (forehead/cheek/chin patch median);
  - forehead 176, already level with the reference.
- **What remains:** the cheeks (99–109). Even with the hair removed entirely, the face reaches only 0.89–0.94 of
  the legs: the cheeks face downward on the head sphere and carry blush. The reference front view has face ≈ legs.

## d) Boot-top lining ring

Measured at the left boot top (radius from the ankle axis):
- leg 0.036 m;
- lining 0.057–0.075 m;
- shaft rim 0.067–0.071 m, up to z 0.1297;
- lining top z 0.1286;
- cuff tube inner edge 0.073 m.

So the opening showed a dark hole between the leg and the lining, then the shaft rim as a separate ring.

Two causes, both in the shared footwear code:
1. `build()` runs `_ensure_clearance` on every piece with the garment ease (0.022 m). That pushed the lining's
   inner edge 2 cm off the leg.
2. The lining sat below the shell rim, which rises above `top_z` once the shell gets its clearance.

Fix:
- The lining's inner edge now follows the measured leg cross-section (`_section_radii`, 48 sectors) plus the
  collision clearance.
- It carries `ps_garment_rest_clearance_m`, which `build()` honours instead of the ease.
- It is seated 0.5 mm above the clearance-adjusted shell rim, and its outer edge ends on the cuff tube's centre
  line, inside the tube.

After: lining 0.039 → 0.088 m at z 0.1301–0.1321, above the rim (≤ 0.1297). `boot_top_before_after.png` shows
the hole and inner ring gone in front and 3/4 views.

## Evidence

- `metrics_before.json`: the frozen T-019 swatch sheet, measured with this task's three-patch method
  (`swatches.json` ROIs; same layout). It was rendered with the pre-T-026 calibration. 2/11 presets, 12/30 rows.
- `metrics_after.json`, `swatch_sheet.png`, `swatches.json`: final sheet, 480 × 576 per preset, 8 spp + OIDN,
  `character_neutral/1`, close LOD. 2/11 presets, 17/30 rows.
  - Every sheen row and boot fleece/cotton knit/woven cotton/denim fuzz fail.
  - Buttons/plastic and glasses/acrylic pass.
  - `measure_swatches.py` exits 1 while the aggregate fails.
- `girl_turnaround_before_after.png`: reference next to before (main e94f3bc), then reference next to after.
  640 px, 32 spp + OIDN, the shared calibration of each revision.
- `face_closeup_before_after.png`, `face_closeup_after_640.png`: orthographic 0.32 m close-up, 640 px, 32 spp.
- `boot_top_before_after.png`.
- `girl_skin_metrics.json`, `timings.json`.

```bash
blender -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- \
  --out docs/evaluation/characters/T-026/swatch_sheet.png --metadata docs/evaluation/characters/T-026/swatches.json \
  --width 480 --height 576 --samples 8 --lighting character_neutral/1 --fibres-lod close
blender -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- \
  --image docs/evaluation/characters/T-026/swatch_sheet.png --metadata docs/evaluation/characters/T-026/swatches.json \
  --out docs/evaluation/characters/T-026/metrics_after.json
blender -b --factory-startup -P pipeline/charsys/build_character.py -- \
  --spec assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --out <dir> --no-glb --no-compare
blender -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <dir>/girl_auburn_bun_glasses_master.blend \
  assets/characters/girl_auburn_bun_glasses/references/reference_index.json <renders> \
  --views sheet30_front,sheet30_front_left,sheet30_left,sheet30_back --height 640 --samples 32 --ids \
  --closeup "face:0:5:0,-0.1,0.8:0.32"
```

Blender: no binary on this host, so `bpy==5.3.0` (Python 3.13) runs behind a `blender` wrapper that accepts
`-b --factory-startup -P <script> -- <args>`. CPU only.

## Checks

| Command | Result |
| --- | --- |
| `python3 pipeline/charsys/tests/test_material_presets.py` | PASS 54/54 (schema set extended with the 4 fibre look fields) |
| `blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>` | PASS (rc 0) |
| `python3 tests/garment_generic_test.py --blender <blender> --out <dir>` | PASS (rc 0) |
| `python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>` | PASS 8/8 |
| `python3 pipeline/charsys/verify_charsys.py --blender <blender> --out <new dir>` | PASS: build, geometry fingerprint (boy byte-identical), store, reuse |
| `blender ... face_system_test.py -- <girl master> <dir> --no-render` | rc 0; 0 lid/glasses overlaps and 0.0% eye visibility in blink gazes |
| `blender ... face_test.py -- assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend <dir>` | rc 0; neutral eye 37.2%, Blink 0.0%, Smile +4.5 mm, JawOpen 13.6 mm (same as T-019) |

`git diff origin/main -- assets tests/data docs/references` is empty: frozen boy versions, test data, baselines
and references are untouched.

## Render budget

| Run | What |
| --- | --- |
| Iteration 1 | Face diagnostics: 6 variants at 320 × 640, 16 spp |
| Iteration 2 | Sheen diagnostics: 4 swatch runs × 3 presets |
| Iteration 3 | Lighting variants (5 key + 4 fill configs, plus key-only per-hair-object shadows, 320 × 640) and a 2-view girl check |
| Iteration 4 | Full swatch sheet |
| Finals | Swatch sheet; fibres-off timing sheet; girl before turnaround and close-up; girl after turnaround and close-up |

The girl after-turnaround was rendered twice. The first final showed that the boot ring persisted, which led to
the clearance and rim fix. **This is one render over the stated budget.**

## Remaining

- Boot fleece fuzz 2.65 (needs ≥ 3; more tone variation or density). Cotton knit, woven cotton and denim are
  also below 3, but those were not in scope.
- Sheen fails on all presets. It needs a shared mid-scale (9–31 px) nap/clump highlight layer; the light and
  measurement have been ruled out.
- Face/legs is 0.84. The remainder is cheek orientation, blush and hood occlusion. A dedicated face fill or a
  less occluding groom would close it (the groom is outside this task's area).
- Characters don't attach GN fibres to garments or boots. The girl's boots use the `fleece` preset, not
  `boot fleece`, and show no fibre fuzz in the turnaround.
- The hair reads grey-brown against the auburn reference (groom/hair colour, not in scope).
- Before/after turnarounds use the calibration of their own revision, as the task's "shared calibration".
