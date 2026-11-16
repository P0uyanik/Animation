# T-032: character fidelity measurement (girl and boy 1.1.0)

Status: **implemented and run; nothing published or approved.** Branch `t-032-claude-fidelity`, from `origin/main`
(`e94f3bc`).

> **The scores support visual judgement but never replace it** (owner decision). Every run writes side-by-side
> sheets for human review (`girl/sheets/`, `boy/sheets/`), and every report says so. The numbers below are measured
> facts about the renders. Whether a difference matters is decided by looking at the sheets.

Method, definitions and limits: [docs/CHARACTER_FIDELITY.md](../../../CHARACTER_FIDELITY.md).

## What was built

All new; no generator, engine, clip, spec or frozen file was touched.

- **`tools/fidelity/`** (shared, character-independent):

  | file | role |
  |---|---|
  | `run.py` | the single command |
  | `blender_render_side.py` | region ids and projected landmarks, same cameras as the turnaround tool |
  | `analysis.py` | alignment and all metrics |
  | `metrics.py` | IoU, landmark error, CIEDE2000, colour, VISUAL_TARGET texture statistics |
  | `sheet.py` | review sheets |
  | `suggest.py` | spec-value suggestions, never applied |
  | `annotate_regions.py` | the one-time region annotation helper |
  | `tests/test_metrics.py` | unit tests |

- **Per-character annotation data** in `assets/characters/<id>/references/annotations/`:
  - `fidelity_index.json`: the views measured, the build variant, and region rules (the boy's legacy object names);
  - one `<view>.json` per view: hand-read landmarks and region polygons;
  - `region_hints.json`: provenance of the polygons;
  - girl: `sheet30_front`, `sheet30_front_left`, `sheet30_left`, `sheet30_back_right`, `sheet30_back`
    (`sheet30_right` is excluded as a duplicate of `sheet30_left`);
  - boy: `val27_front`, `val27_threequarter_right`, `val27_side_right`, `val27_back`, `val27_back_threequarter`
    (#27 is the neutral arms-down turnaround that has silhouette masks; #7, #24 and #29 have a hand in a pocket).
- **`docs/CHARACTER_FIDELITY.md`.**

## Runs (evidence in this folder)

| | girl, current main spec (0.7.1) | boy 1.1.0 (1.0.0 spec + `1.1.0.override.json`) |
|---|---|---|
| build | `girl_auburn_bun_glasses.spec.json` → master (A-pose, as #30) | spec + override → `_compare.blend` (arms down through the rig, fur on, as #27); backpack body hidden per `reference_index.json` |
| **fidelity score** | **63.0 / 100** | **64.5 / 100** |
| silhouette (figure IoU) | 0.794 (sub-score 59) | 0.855 (71) |
| regions (area-weighted IoU) | 0.57 | 0.70 |
| landmarks (mean error) | 0.081 head heights (73) | 0.070 head heights (77) |
| proportions (mean relative error) | 10.9% (64) | 16.3% (46) |
| colour (mean ΔE00) | 9.8 (51) | 9.5 (53) |
| texture (mean \|log2 ratio\|) | 80 | 62 |
| files | `girl/report.md`, `girl/fidelity.json`, `girl/sheets/*.png` | `boy/report.md`, `boy/fidelity.json`, `boy/sheets/*.png` |

Per view (figure IoU / landmark error in head heights):

- girl: front 0.824 / 0.039, front-left 0.809 / 0.070, left 0.739 / 0.070, back-right 0.745 / 0.133,
  back 0.856 / 0.092;
- boy: front 0.846 / 0.058, 3/4 right 0.859 / 0.076, side right 0.857 / 0.077, back 0.855 / 0.070,
  back 3/4 0.859 / 0.070.

### Largest differences, from the reports (median over views)

Girl:
1. hair accessories (flowers, band): silhouette overlap 0.16; colour ΔE00 19.2 (hue 54° towards yellow).
2. Arms 26% too short (shoulder to hand). In the reference the arms reach further out and lower. The front sheet
   shows it.
3. Face skin ΔE00 19.8: render darker by 23 L*. The luma-matched ΔE00 is only 5.4, so this is mostly lightness:
   the lighting or exposure of the face, or a skin base that is too dark.
4. Glasses overlap 0.34. Face and limb skin overlap 0.37.
5. Overall silhouette 21% narrower. Eyes 20% too small (width relative to head height); eye spacing 10% too narrow.
6. Blouse +29% area and fuzz +223% vs the reference. The render's blouse reads as fleece; the reference reads as
   smooth cotton.
7. Hair volume −23%, hair length −11%.
8. Visibility: in the side view (`sheet30_left`) the render's hair covers the whole face (eye, nose, mouth, chin
   hidden), while the reference shows the profile. The brows and ears are hidden in the render's front views.

Boy:
1. Visible gap between the legs 36% shorter: the trouser legs touch down to the shoes.
2. Hair width at the temples (eye level) −71%: the render's side hair stops above the eye line, while the reference
   locks hang over the ears.
3. Eyes: overlap 0.02, area −41%, width −24%. The render's heavy upper lid leaves only the lower part of the eyeball
   visible, and the irises count as hidden.
4. Hands (skin_limbs) overlap 0.13, area −67%: the sleeves cover more of the hands.
5. Backpack straps overlap 0.18.
6. Face skin ΔE00 21.5: render darker by 23 L* and more saturated (luma-matched 5.6). Hoodie ΔE00 14.5: render
   darker by 16 L* (luma-matched 3.5).
7. Fuzz −66% to −68% on the hoodie, trousers and backpack: the reference fleece is much more textured at this scale.
8. Visibility: the ear tops are hidden in 4 of 5 views; the brows are hidden under the fringe (visible in #27).

Spec-value suggestions are listed at the end of each `report.md` and in `fidelity.json` (`suggestions`). They are
suggestions only and were not applied. For example:

- girl: `face.eyes.radius_m` 0.036 → 0.045; `body.params.arm.*_len` ×1.43;
- boy: `proportions.eye_radius_m` 0.037 → 0.051;
- colour shifts per material.

Most colour differences are largely lightness (high ΔE00, low luma-matched ΔE00). Check the lighting and exposure
before changing base colours.

### Observation: the camera yaw of `sheet30_back_right`

`reference_index.json` labels this view −135° ("yaw from the label"). The reference image looks almost square-on.
With `--reference-index` pointing at trial copies of the index (the index itself is not modified), the figure IoU of
this view against the same girl master is:

| yaw | −135 (index) | −150 | −160 | −170 | −175 | 180 |
|---|---|---|---|---|---|---|
| figure IoU | 0.745 | 0.781 | 0.804 | 0.827 | 0.836 | 0.841 |
| hair IoU | 0.664 | 0.705 | 0.734 | 0.761 | 0.776 | 0.786 |

The fit improves steadily towards 180°. The view is probably close to a straight back view, so its yaw in
`reference_index.json` deserves an owner or analyst check. Until then, this view's numbers partly measure a camera
mismatch.

## Checks

| check | result |
|---|---|
| `python3 tools/fidelity/tests/test_metrics.py` (synthetic images: IoU, landmark error, CIEDE2000 on 8 Sharma et al. pairs, sRGB↔Lab, colour statistics, alignment, crotch and column measures, texture, polygon tracing and rasterisation, determinism) | **ALL PASS (35/35)** |
| Analysis determinism: `run.py --renders` twice on the same renders, both characters | `fidelity.json`, `report.md` and all sheets **byte-identical** |
| Render repeatability: girl, full second run from the same master (groom_turnaround + render side) | all 15 render images **pixel-identical**; score 63.0297 both times |
| Render side vs turnaround camera (same bounding box and `place_camera` code) | IoU between the region-pass silhouette and a background-threshold mask of the beauty render: 0.991–0.993 (boy), 0.945–0.957 (girl). In the girl's case, nearly all the disagreement is region pixels whose beauty colour is within the threshold of the grey background (grey-brown hair, shadowed boots) |
| Annotation review | every view's polygons and landmarks checked on overlays (method in CHARACTER_FIDELITY.md) |

- The renders are deterministic for a given master on this machine. A rebuild from the spec can differ slightly
  where the builders are not deterministic (the boy's `hair_mass`, known since T-016).
- Run time: girl about 80 s including the build; boy about 40 s (5 views each, 640 px, 32 samples, 4 CPU cores,
  Blender 5.3 via the `bpy` 5.3.0 wheel and a `blender` wrapper script).

## Commands

```
python3 tools/fidelity/run.py --character girl_auburn_bun_glasses \
    --build assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json --blender <blender> --out <dir>/girl
python3 tools/fidelity/run.py --character boy_yellow_hoodie \
    --build assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json \
    --override assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.1.1.0.override.json --blender <blender> --out <dir>/boy
python3 tools/fidelity/tests/test_metrics.py
```

## Limits and notes

- The references are stylised renders with their own light. Colour numbers include lighting; use the luma-matched
  ΔE00 next to the plain ΔE00.
- Joints on the reference (shoulders, hands, neck) are estimated through clothing, to about ±4 px. Differences in
  arm length below about 8% are within that uncertainty; the 20–26% found here are not.
- The single score is a heuristic weighting (documented). Use it to follow one character across builds, not to rank
  characters.
- The region polygons come from colour classification with hand seeds. Thin features (cords, buttons, embroidery)
  are not separate regions.
- Frozen material was left untouched: boy 1.0.0, 1.1.0 and v6, `tests/data`, image baselines, `docs/references`,
  the reference images and `reference_index.json`.
