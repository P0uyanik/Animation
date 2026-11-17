# Character fidelity measurement (T-032)

A shared, character-independent tool that compares renders of a character's current build against the owner's
reference views. It measures silhouettes, landmarks, proportions, colour and texture, and it produces review
sheets, `fidelity.json` and a short report.

> **Binding rule (owner decision).** Fidelity scores support visual judgement but never replace it. The tool always
> writes side-by-side images for human review, and every report says so. A good score is not an approval, and a bad
> score is not a rejection. Look at the sheets.

Code: `tools/fidelity/`. Per-character data: `assets/characters/<id>/references/annotations/`. First results:
[docs/evaluation/characters/T-032/](evaluation/characters/T-032/README.md).

## Command

```
python3 tools/fidelity/run.py --character <id> --build <master.blend | spec.json> --blender <exe>
    [--override <override.json> ...] [--out <dir>] [--views id,...] [--height 640] [--samples 32]
    [--renders <dir>]            # analysis only: reuse the renders/ folder of an earlier run
    [--reference-index <json>]   # experiments only (for example, a trial camera yaw)
```

## T-023 quality-gate integration (T-037)

Character fidelity is an optional check inside the Blender tier of `tools/check_all.py`; unrelated changes do not
run it. The gate runs `tools/fidelity/run.py` once for every affected fidelity-enabled character when any of these
change relative to the gate's comparison base:

- that character's `assets/characters/<id>/spec/` data (including overrides);
- that character's `assets/characters/<id>/references/` data, including annotations; or
- a shared body, face, groom/hair, garment, material, build-geometry, or render-calibration generator under
  `pipeline/charsys/`.

The guarded main-branch baseline is
`docs/evaluation/characters/fidelity_baseline.json`. It records each character's score, exact build and overrides,
and common render settings. The Blender-tier line in the at-most-ten-line summary reports the measured score and
signed delta from that baseline. A score increase is informational. A drop of exactly 2.0 points is allowed; a drop
**greater than 2.0 points fails** with `visual regression, needs owner review`. This automated rule does not change
the binding rule above: reviewers still inspect the sheets.

Each run writes `fidelity.json`, `report.md`, renders, and `sheets/*.png` below
`build/check-all/<phase>/fidelity/<character>/`. The quality-gate artifact upload includes the side-by-side per-view
sheets and `overview.png` on both success and failure.

The baseline is a guarded path. It may be changed only in an explicit Supervisor-approved commit carrying the exact
trailer:

```
Supervisor-Approved: docs/evaluation/characters/fidelity_baseline.json
```

Do not update the baseline as part of an ordinary character or generator change, and do not use an increase to
auto-approve visual quality. A baseline update records an owner-reviewed decision; it does not alter the fidelity
metrics, weights, or tolerances.

- **`--build`** takes either a built `<id>_master.blend` or a spec `.json`. A spec is first built with
  `pipeline/charsys/build_character.py` (plus any `--override` files) into `<out>/build`. When
  `fidelity_index.json` asks for the `compare` variant (pose with the arms lowered), the tool uses the
  `<id>_compare.blend` that the builder writes next to the master.
- **Renders** come from the existing turnaround tool `pipeline/charsys/tools/groom_turnaround.py` with the shared
  calibration `character_neutral/1`. It uses the camera of each reference view (yaw, elevation and focal length from
  `reference_index.json`). The view's `hide_objects_prefix` (for example, the boy's backpack body on #27) is applied
  to a temporary copy of the .blend.
- **Render side** comes from `tools/fidelity/blender_render_side.py`. It uses the same cameras (same bounding box,
  `compare_harness.place_camera`). It renders flat region ids and projects the landmarks. The .blend is never
  modified.
- **Outputs** (in `--out`):

  | file | content |
  |---|---|
  | `sheets/<view>.png` | reference \| render (aligned) \| silhouette and landmark difference \| region outlines |
  | `sheets/overview.png` | all views stacked |
  | `fidelity.json` | every number, the score, the ranked differences and the suggestions |
  | `report.md` | short report: score, per-view table, top 15 differences, suggestions |
  | `renders/` | beauty renders, region ids and projected landmarks (reusable with `--renders`) |

- **Requirements:** Python 3 with numpy and Pillow (no scipy or OpenCV), plus a Blender 5.3 executable. Without a
  Blender binary, a `bpy==5.3.*` wheel in a venv works with a small `blender` wrapper that accepts
  `-b --factory-startup -P <script> -- <args>`.
- **Run time:** about 80 s for the girl including the build (about 40 s from an existing master). About 40 s for the
  boy (5 views, 640 px, 32 samples, 4 CPU cores).

## Per-character data (annotations as data)

`assets/characters/<id>/references/annotations/`:

| file | content |
|---|---|
| `fidelity_index.json` | measured views, excluded views with the reason, build variant (`master` or `compare`), object-name rules for regions (legacy object names) |
| `<view>.json` | hand-annotated 2D landmarks and region polygons for one reference view (pixels in `references/views/<view>.png`, x right, y down) |
| `region_hints.json` | provenance of the polygons: seed boxes, zones and hand ellipses for `annotate_regions.py` |

The reference images, `reference_index.json` and the older `landmarks.json` files are only read, never written.

### Landmarks

On the reference side, landmarks are hand-read on 4x–5x gridded zooms. Precision is about ±2 px on the face and
about ±4 px for joints estimated through clothing. A hidden point is left out. The character's left (`_L`) is screen
right in front views. On the render side, landmarks are projected from bones, landmark empties and mesh vertices,
never hand-annotated:

| landmark | reference definition | render source (shared rule) |
|---|---|---|
| `eye_L/R` | centre of the visible eye opening | `LM_eye_*` empty |
| `iris_L/R` | iris centre | front-most vertex of the eyeball `eye.*` |
| `eye_inner/outer_L/R` | ends of the eye opening | visible eyeball vertices nearest to / farthest from the face midline |
| `brow_inner/outer_L/R` | brow ends | `brow.*` vertices nearest to / farthest from the midline |
| `nose`, `mouth`, `chin` | nose tip, mouth centre, lowest point of the face | `LM_nose`, `LM_mouth`, `LM_chin` |
| `mouth_corner_L/R` | mouth corners | outermost `mouth` vertices (front views) |
| `ear_top_L/R` | highest visible ear point | highest `ear.*` vertex |
| `hairline` | lowest hair edge on the face midline, above the eyes | lowest hair vertex near the midline, in front of the eyes (front views) |
| `neck` | neck axis at shoulder-joint height | head of `DEF-spine.004` |
| `shoulder_L/R` | shoulder joint centre | head of `DEF-upper_arm.*` |
| `hand_L/R` | centre of the palm | midpoint of `DEF-hand.*` |
| `foot_L/R` | bottom of the sole under the ankle | the point on the ground below the head of `DEF-foot.*` |
| `hem_<garment>` | lowest visible edge of the garment | lowest visible vertex of the garment's `main` mesh in the torso band (\|x\| < 0.6 shoulder half-width) |

- **Visibility:** surface points are tested with a ray cast from the camera. The glasses are see-through for this
  test. A point that is hidden in the render but annotated on the reference is reported (for example, "ear tops
  hidden in the render"). Skeletal points count as always visible.
- **Feet:** on both sides the foot point is snapped to the lowest silhouette pixel in its column.
- **Hems** are compared on height only.

### Regions

Region polygons are semi-automatic (`tools/fidelity/annotate_regions.py`, a one-time helper that the measurement
never runs):

1. The figure is the existing silhouette mask `references/views/<view>_mask.png`.
2. The annotator picks seed boxes per region. These are flat patches, several per region for lit and shaded parts.
   The annotator can also give zones where a region may appear.
3. Every figure pixel takes the region with the nearest seed colour (CIE Lab) among the regions allowed there.
   A 5×5 majority filter removes speckle.
4. Each region's connected components (holes filled, at least 15 px) are traced. They are simplified with
   Douglas–Peucker at 0.5 px into polygons in pixel-corner coordinates. Rasterising a polygon back with
   `analysis.poly_mask` reproduces the component.
5. Eyes and glasses are hand ellipses or polygons.
6. `skin` is split at the annotated chin line: `skin_face` above it, `skin_limbs` below it.
7. The annotator reviews an overlay and corrects the seeds or zones until it is right. The written polygons are the
   annotation.

Region names: `skin_face`, `skin_limbs`, `hair`, `hair_accessory`, `eyes`, `glasses`, `garment:<item>`,
`accessory:<item>`.

On the render side, `blender_render_side.py` classifies objects by the builder's component collections:

- **hair:** the dominant material is `hair`; other materials are `hair_accessory`.
- **clothing:** `garment.<item>.*` maps to `garment:<item>`.
- **body, ears and lids** map to `skin`.
- **face:** `eye.*` maps to `eyes`; brows, lashes and mouth map to `face_detail`.
- **accessories:** `glasses*` maps to `glasses`; other accessories map to `accessory:<token>`.
- **fur curves** follow their surface.

Per-character `region_rules` in `fidelity_index.json` win; the boy uses them for his legacy v6 object names. The
render side applies the same chin split as the reference, using the projected `LM_chin`. `skin_face` includes eyes
and face details, as the filled reference polygon does. Glasses are rendered in a second pass, so the eyes stay
visible through the lenses in the main pass.

The tool compares only the regions that the reference view annotates. Render regions that are not annotated are
listed as `render_regions_not_annotated`.

### Annotating a new character

1. Write `fidelity_index.json`: the views, the variant whose pose matches them, and region rules if the object
   names are legacy.
2. Read the landmarks on gridded zooms and write `region_hints.json` with seeds and zones per view.
3. Run `annotate_regions.py <hints> <view> --preview p.png`, iterate, then write the polygons into `<view>.json`.
   The T-032 files were written this way.

## Metrics

- **Alignment:** the reference crop and the render are framed differently. The render is scaled uniformly so that
  its figure height (sole to top, bun included) equals the reference figure height. Bottoms and horizontal centres
  are aligned, then the integer shift within ±10 px horizontally and ±3 px vertically with the best figure IoU is
  kept. Width is never normalised, so a too narrow figure stays visible.
- **Silhouette IoU:** figure vs background, and per region (hair, each garment, skin face and limbs, eyes, glasses,
  accessories) in the reference frame. The area ratio render/reference is also reported.
- **Landmark error:** distance in the reference frame divided by the reference head height (chin to figure top).
  Views without a visible chin use the median head fraction of the other views.
- **Proportions:** each image is measured in its own frame. All values are dimensionless ratios:
  - `head_to_height`;
  - `eye_line` and `mouth_line` (fraction of the height);
  - `eye_width_to_head`, `eye_area_to_head` and `eye_spacing_to_head`;
  - `arm_length` (shoulder to hand) and `shoulder_width`;
  - `leg_gap_height`: the visible gap between the legs, crotch to sole, which also catches legs that touch;
  - `figure_width`;
  - `hem_<garment>_height`;
  - `hair_area` (silhouette area / height²), `hair_width_at_eyes` (temples) and `hair_length`.

  The relative difference is render/reference − 1, as a median over the views.
- **Colour:** CIEDE2000 (D65) between the median Lab of the reference region and of the render region.
  - Reference pixels exclude overlapping regions (eyes, glasses, islands). Masks are eroded by 1 px.
  - Also reported: the luma-matched ΔE00 (VISUAL_TARGET.md: compare after matching the median lightness), the signed
    ΔL*, ΔC* and Δh, and the spread (median ΔE00 of each pixel to its own median).
  - The references are themselves stylised renders with their own lighting. A ΔE00 that is mostly ΔL* (high ΔE00,
    low luma-matched ΔE00) points at lighting or exposure as much as at the base colour.
- **Texture / fuzz:** the VISUAL_TARGET metrics per region, with the render resampled to the reference scale and
  mask-normalised blurs:
  - fuzz: high-frequency luma RMS after subtracting a 9 px Gaussian blur;
  - sheen: P90/P50 of luma divided by a 31 px blur;
  - variance of the Laplacian;
  - median saturation.

  Blur sizes are scaled from the H = 256 px convention by (reference head height / 256). The values are reported as
  render/reference ratios. They are relative comparisons at the reference resolution, not the absolute VISUAL_TARGET
  bands. Silhouette edge roughness (perimeter / smoothed perimeter) is reported per view.
- **Fidelity score (0–100):** a weighted mean of six sub-scores, each from 0 to 1:

  | part | weight | sub-score |
  |---|---|---|
  | silhouette | 0.25 | (mean figure IoU − 0.5) / 0.5 |
  | regions | 0.15 | region IoU weighted by reference area |
  | landmarks | 0.20 | 1 − mean error / 0.3 head heights |
  | proportions | 0.15 | 1 − mean \|relative error\| / 0.3 |
  | colour | 0.15 | 1 − mean ΔE00 / 20 |
  | texture | 0.10 | 1 − mean \|log2 ratio\| / 1.5 |

  The weights and ranges are a heuristic, documented here. The score is for tracking one character across builds,
  not for comparing characters.
- **Ranked differences:** every difference is put in plain words and given a severity: its size divided by a
  tolerance. The tolerances are:

  | kind | tolerance |
  |---|---|
  | proportions | 5% (hair and eye area: 10%) |
  | line heights | 2% of the height |
  | landmarks | 0.05 head heights |
  | region IoU loss | 0.15 |
  | colour | ΔE00 4 |
  | texture | half a log2 step |
  | hidden landmarks | 1 + 0.5 per view |

  Example wording: "eyes 24% too small (width relative to head height)", "hair width at the temples (eye level)
  −71%", "hoodie colour dE00 14.5 (render darker by 16 L*, …)".
- **Suggestions (optional, never applied):**
  - proportions: the spec value times reference/render for eye size, eye spacing, arm length and shoulder width;
  - colours: the current base sRGB moved in Lab by (reference median − render median), averaged when several regions
    share one material.

  The spec paths come from the known spec schemas (`face_generic`, `garment/1` and material assignments, and the
  legacy `body_v6` fields). The suggestions are first-order: a person decides, edits a new spec version and
  re-measures.

## Tests and determinism

- `python3 tools/fidelity/tests/test_metrics.py` tests on synthetic images (35 checks):
  - IoU;
  - landmark error (y-only hems);
  - CIEDE2000 against the published Sharma et al. 2005 test pairs (8 pairs, error < 1e-3);
  - sRGB↔Lab round trip;
  - colour statistics;
  - alignment of a scaled and shifted synthetic figure;
  - crotch and column measures;
  - texture statistics;
  - polygon tracing and rasterisation;
  - byte-identical analysis output.
- `python3 tools/fidelity/tests/test_ci.py` tests affected-character selection and the score-delta boundary,
  including that a 2.0-point drop passes and any larger drop fails with the owner-review reason.
- The analysis is deterministic: `--renders` on the same renders gives byte-identical `fidelity.json`, `report.md`
  and sheets (checked on both T-032 runs). The renders themselves come from Cycles (32 samples, OIDN). See the T-032
  README for the render repeatability measured on this machine.

## Known limits

- The references are stylised images with their own light, lens and pose. The tool compares like with like as far
  as the data allows: the same yaw, elevation and focal estimate, the same calibration, the variant with the
  matching pose. Pose differences (arm angle, a hand in a pocket) still show up as silhouette and landmark
  differences. That is one more reason the sheets come first.
- Shoulder, hand and neck points on the reference are estimated through clothing (±4 px). Arm-length differences
  under about 8% are within that uncertainty.
- Camera yaws come from `reference_index.json`. A wrong yaw there shows up as a low IoU in that view. For example,
  girl `sheet30_back_right` is labelled −135°, but the reference looks almost square-on (see the T-032 README).
- Region polygons come from colour classification, so fine features under about 3 px (cords, buttons, embroidery)
  are not separate regions.
