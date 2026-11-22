# T-204 | Face targets for the three released characters

All comparisons below run **current → reference**. H is the projected distance from the main hair crown to the chin, excluding buns. F is the widest span between the traced cheek contours, excluding ears and hair. Percentages refer to the stated image dimension. The rankings reflect what changes the likeness across views. [Full measurements](measures.csv) · [Targets, tolerances and landmarks](targets.json)

## Boy · 2.3.0

1. **Give the lower face room.** The front iris line sits at 86% → 76% H below the crown (E). The mouth-to-chin interval is only 2% → 11% H in front and 3% → 11% H on the turn (E). Raise the eyes and mouth within the head. Carry more cheek width down toward the mouth. Halfway from iris to chin, the front face spans 75% → 92% F (E). Side cheek bulge is already within tolerance at 2.3% → 2.9% H (E).
2. **Restore the long, soft centre fringe and drooping lids.** Close the fringe-tip-to-iris gap from 17% H (E) toward 6% H (T-161, M), judging it again after raising the eyes. Broaden the front opening from 14.5% to 16.6% H and reduce its height from 8.2% to 5.2% H (M). Brow clearance is already close at 11.6% H (M) against 12.4% H (E).
3. **Blend the blush into the cheek.** The red step from adjacent skin to blush is +14.3 → +9.7 a* (M). Soften that transition. The sampled cheek lightness is close at 62.6 → 62.2 L* (M). [Boy landmarks](boy.jpg)

## Auburn · 0.14.0

1. **Uncover the cheek in profile.** The uninterrupted strip from the front of the cheek to the nearest lock spans 12% → 32% H (M). Move the narrow temple lock back to expose about another 0.21 H of skin. Front cap width is close at 1.37 → 1.35 F (E). Bring the sweep down toward the brow, taking the central fringe-to-iris gap from 38% H (E) toward 29% H (T-161, M). The bun is clipped in both current front and three-quarter tiles.
2. **Restore cheek fullness beneath the glasses.** Widen the halfway cheek section from 86% to 93% F (E) and raise the front iris line by about 7% H (E). Round the opening under the lens toward height/width 0.95 (T-150, E) from 0.77 (M). On the turn, the near opening also needs more width, 13.5% H (E) → 17.8% H (M).
3. **Widen the mouth and set it higher.** On the turn, move from 12% to 17% F in width (E). In front, leave about 14% H below the mouth against the current 9% (E). Use a matched smile to judge aperture height. The sheet30 front is open-mouthed. [Auburn landmarks](auburn.jpg)

## White-haired · 0.1.0

1. **Restore the tall blue eye opening.** Front opening height/width is 0.69 (M) → 0.95 (T-150, E). Increase visible height from 14.0% to 16.8% H (E) and bring iris diameter from 66% (M) toward 75% of opening width (T-150, E). The opening already spans 20.3% → 18.0% H horizontally (E). Bring the centres closer, from 56% F (E) toward 52% F (M).
2. **Reduce the hair overhang and break up the comb-like fringe.** Above the eyes, the hair spans 2.08 F (E) → 1.66 F (M). At cheek level it spans 1.94 → 1.64 F (E). Pull the side masses inward, especially where the near lock hides the eye and cheek in profile. Break the regular central tips into soft wisps. The central tip-to-iris gap is within the T-161 tolerance.
3. **Restore the cheek and bow finish.** Increase the local blush contrast from +1.8 toward +12.6 a* (M). Bring the lit blue bow lobe from 45 toward 52 L* (M), with visible knit fibres and a softer edge. The side-view cheek bulge remains unscored because the forward lock hides its silhouette. [White-haired landmarks](white_haired.jpg)

## Sources and measurement conventions

- Evaluation base `origin/main@0cb0053a`. T-202 input `t-202-claude-face-sheets@25b2bed2` is staged under `build/in/docs/evaluation/characters/T-202/`. The reference images are in `crops/`. All nine **current** images are the right-hand 1000 px tiles in `sheets/`. This checkout has no separate `renders/` directory. The file and zero-based row are recorded for every trace. [T-202 sheet manifest](../T-202/README.md)
- The primary reference is val27 for boy, sheet30 from ref_30 for auburn, and id01 front plus f14 turns for white-haired. Hero24, canon29, f14 front and sheet 02 supply secondary checks where available. The JSON records the crops and ruler readings. The original asset paths and mirrored panels are in the T-202 composition table. [Crop mapping](../T-202/compose.py)
- T-150 supplies the girls’ front opening and iris ratios and auburn's near-eye ratios on the turn. T-161 at `t-161-codex-ref-targets@27f5637` supplies the frontal fringe, forehead, crown, cheek-level hair, bun and ear targets, plus ear projection on turns. Those rows retain the published values and tolerances. Their current readings come from the T-202 releases. Ears are visibility and placement checks. [T-150 targets](../T-150/targets.json) · T-161 targets (`t-161-codex-ref-targets@27f5637`: docs/evaluation/characters/T-161/targets.json)
- **M** means a manual pixel measurement or sampled colour. **E** means an estimated boundary, inferred centre or inherited estimate. An empty current cell means the feature is hidden, clipped or unresolved. Gap = current minus target. New working tolerances allow for tracing, expanded by the observed deviation on secondary views where recorded. Jaw and chin widths are sampled at 80% and 93% of the iris-to-chin interval. Profile bulge is the cheek’s forward offset from the chord joining eye-level and lower-jaw skin.
- Match the neutral T-202 camera first. The render lens is 70 mm, with 6° elevation for boy and 5° for the girls. Three-quarter yaws are −35°, −45° and −30° respectively. Upload lenses are estimates. Foreshortening, gaze, glasses and mirrored turns affect apparent spacing. Low-resolution plush fibres obscure seams. Several reference fronts smile. Lab values describe the pictured lighting and texture. The pink rings show the sample sites.

## Re-score a release

Run from the repository root with Python, Pillow and NumPy. The first command after setting `$m` replays all baseline rows. Add `--inputs PATH` for a different T-202 directory or `--evidence EXISTING_DIR` to regenerate the plates.

```powershell
$m = 'docs/evaluation/characters/T-204/measure.py'
python $m --output build/replay.csv
python $m --template boy front --image build/new-head.png --grid build/grid.jpg --output build/trace.json
python $m --trace build/trace.json --output build/new-scores.csv
```

Between the last two commands, fill `points` in the template from the grid of the new **square** crop. Coordinates run from 0 to 400, measured right and down. Use `example_points` for the field shapes and `trace_guide` in the targets for landmark definitions. Start with `crown` and `chin`. Trace each cheek from above the eye to the chin in increasing y. List inferred landmark names in `estimated` and leave hidden features null. Character keys are `boy`, `auburn` and `white_haired`. Views are `front`, `three_quarter` and `side`.

Ledger | builds 0 · renders 0 · CI 0 · offline scoring and overlay verification.
