# T-153 · Fidelity score v2 (opt-in)

Input `d6740c4`. No renders: everything is measured on archived JSON and sheets. v1 score, thresholds,
`fidelity_baseline.json` and the gate are unchanged; v2 is opt-in (`run.py --score-version 2` writes an extra
`fidelity_v2.json`; default stays 1). Adopting v2 is the owner's call.

**v2 = 0.8 × re-weighted v1 + 0.2 × face-state score** (T-129 proposals 1 + 2). Re-weighting: silhouette 0.20 → 0.13,
face 0.05 → 0.12. Face states (on the T-122 expression sheets): Blink lid vs adjacent skin (dE00), pale band below the
lens, mouth opening + contour vs the labelled reference crop. Without face-state sheets, v2 = re-weighted v1.
Local hair (proposal 3) and T-150 eye shape are reported separately, not pooled into the total.

## Agreement with owner decisions (calibration.csv, 13 scored pairs; "after" is the preferred side in all)

| task | char | pair | v1 Δ | v2 Δ | v1 | v2 |
|---|---|---|---:|---:|:-:|:-:|
| consolidation | girl | 0.7.1 → 0.9.0 | +2.37 | +2.46 | y | y |
| T-080 | boy | 1.1.0 → 2.0.0 | +1.22 | +0.21 | y | y |
| T-094 | boy | 2.0.0 → 2.1.0 | +0.09 | +0.62 | y | y |
| T-081 | girl | 0.10.0 → 0.11.0 | −2.11 | +0.47 | **n** | **y** |
| T-094 | girl | 0.11.0 → 0.12.0 | +2.72 | +3.41 | y | y |
| T-089 | boy | 2.0.0 → +face3 | +1.25 | +1.38 | y | y |
| T-089 | girl | 0.11.0 → +face3 | +0.26 | +0.09 | y | y |
| T-049 | boy | A → C | +0.62 | +0.53 | y | y |
| T-049 | boy | B → C | +0.55 | +0.53 | y | y |
| T-049 | girl | A → C | +2.34 | +2.39 | y | y |
| T-049 | girl | B → C | −1.11 | −0.99 | n | n (local hair: B 0.856 < C 0.877, agrees) |
| T-122 (candidate) | boy | 2.1.0 → 2.2.0 | −0.47 | +0.66 | **n** | **y** |
| T-122 (candidate) | girl | 0.12.0 → 0.13.0 | −0.88 | +1.26 | **n** | **y** |
| **total** | | | | | **9/13** | **11/13** |

Owner versions 4/5 → 5/5; system 2/2 → 2/2; design 3/4 → 3/4; T-122 candidates 0/2 → 2/2. Re-weighting alone moves
T-122 the wrong way (boy −0.68, girl −1.67, as T-129 predicted); the face-state term reverses both.

## T-129 blind spots

| blind spot | measure | before → after (0..1) | status |
|---|---|---|---|
| lid colour (Blink) | 1 − dE00(lid, skin)/20 | boy 0.79 → 0.89 · girl 0.59 → 0.76 | measured, agrees with T-122 read |
| lens shelf | pale-band fraction below lens | girl 1.00 → 1.00 | **not resolved**: no neutral row on the sheet; `girl_content` shows no pale band in either column |
| expressions | mouth opening + contour vs reference | boy 0.22 → 0.24 · girl 0.42 → 0.65 | girl delighted/Laugh resolved; boy mouths are ~30 px wide, contour is noise-level |
| eye shape | T-150 front bands | auburn 0.13.0: 0.76 (50% in band) | no 0.12.0 trace, so no pair delta; boy has no targets |
| local hair | crown / fringe / back locks patch (colour, fuzz, sheen, strand direction) | girl A 0.833 · B 0.856 · C 0.877 | girl only; boy contact sheet not boxed |
| garments (flap, collar, reach) | `local_patch` applies | — | **not measured**: T-093 has no matched archived image pair |

## Limits (read before adopting)
- **In-sample.** Boxes are hand-placed on a 20 px grid (`tools/fidelity/v2/data/*.json`, overlay
  [face_state_boxes.jpg](face_state_boxes.jpg)). After the first pass I moved the boy's skin box off the hair and
  tightened the render mouth box to exclude the lens rim and the hair under the chin. Before that fix T-122 read 1/2.
  The 2/2 is therefore not independent evidence. Freeze the boxes and weights, then test on the next owner verdicts.
- Face states come from 260 px Cycles 12 spp panels; one sheet per pair. Only T-122 has them, so other pairs use
  re-weighting only.
- Like T-129, every pair is an approval. Rejection accuracy is still unknown.

Files: `evaluation.json` (every number), `calibration_v2.csv` (table). Reproduce: `python3 tools/fidelity/v2/evaluate.py`.
Tests: `python3 tools/fidelity/tests/test_metrics_v2.py` (18/18, registered in `tools/check_all.py`).
