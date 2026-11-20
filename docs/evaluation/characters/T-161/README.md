# T-161 | Lash, ear and hair targets

**Restore the dark blink curve on all three characters.** In the pictured blinks it spans 92-97% of the closed lid in reference and 0-13% in the candidates (E). The open-eye correction differs by character.

| Rank | Feature | Reference compared with current |
|---|---|---|
| 1 | Blink, all three | The reference line dips in the middle and tapers at both corners. Auburn loses it entirely. Boy and white-haired retain a short outer fleck. Compare row 3 of each plate. |
| 2 | Open upper liner, both girls | The continuous ink spans 105% of opening width on G01 and 98% on 01, including overhang (M). Both candidates stop at about 43% (M), leaving the nose-side lid bare. Keep the short separate tips on the outer half. Boy already has the full bar and no separate tips. |
| 3 | Ear visibility on turns | Near-ear extension beyond the cheek runs 22%, 26% and 19% of projected head width for boy, auburn and white-haired. Candidates give 10%, 4% and 0% (E). Inspect hair overlap before changing ear size. Both girls show an inner hollow in reference profile. [Profile pairs](profile.jpg) |
| 4 | Fringe and lock ends | Boy's central fringe-to-eye gap grows from 6% to 22% of head height (M). His rear tips form fewer, wider leaves. Auburn's rear ringlets interlock into a rope pattern. White-haired has broader wave ends and more hair at shoulder level (1.90 vs 1.69 head widths, E). The white-haired centre-fringe gap is within the working band. |

**Evidence and scope.** Each plate pairs reference (left) with candidate (right). Rows show front, open eye, blink, near ear on a turn, rear locks, then profile or shoulder. Captions give source alias, top-left pixel and square crop width. The JSON resolves the aliases to repository paths. Input is `d704adc006e6f988b25566e232853038d886e259`. T-122 uses the candidate column (boy 2.2.0, auburn 0.13.0). White-haired uses T-126a pass 2 for eyes and T-126b for hair/ears. Only the T-137 task brief is present in this checkout or its local refs, so its proposed blink and fringe changes are unverified. [Boy](boy.jpg) · [Auburn](auburn.jpg) · [White-haired](white_haired.jpg)

**Reading a trace.** [Targets](targets.json) give a value, symmetric working tolerance, source and protocol for each measure. [Comparisons](measures.csv) preserve each numerator/denominator in the displayed 300 px crop. F is projected head width across the widest cheek contours, excluding ears and hair. Hh runs from the main hair crown to the chin, excluding buns. Positive vertical offsets follow each measure's definition. M denotes a manual pixel measurement or resolved count. E covers inferred boundaries, small or merged tips and visual categories. `?` means the boundary is hidden. Zero means visible absence, or an absent bun/accessory as defined. Tolerances are tracing and pose allowances chosen for review. Categories use exact labels.

Match yaw, elevation, gaze and expression. The strict sheets use a 70 mm lens, with 5-6 degrees elevation. Upload lenses are unknown. G01/G02 include refraction, wire-rim overlap and oblique foreshortening. Boy's relaxed opening is shallow, so a pixel of thickness changes his ratio substantially. For blinks use neutral opening height at the same face scale. Skull contours beneath hair and buried ear roots are inferred. Mirrored turns permit near-ear comparisons but cannot establish left-right asymmetry.

**Re-measure a render.** From the repo root, use Python 3. The scorer uses the standard library. The optional four-click image picker uses OpenCV. Supply matched crops of a new render and use the JSON protocol for each row.

```powershell
$m = 'docs/evaluation/characters/T-161/measure.py'
python $m --character auburn --template --output build/new.csv
python $m --pick build/new-eye.png
python $m --input build/new.csv --output build/scored.csv
```

In `new.csv` fill `current_source` with image path and view, `current_trace` with measured pixel lengths (`15/174`), a count, or a category, and `current_mark` with M or E. The picker prints a ratio trace after two endpoint clicks for each segment. Trace signed offsets along the stated axis and add the sign manually. Record a short descriptive label for a different category. Keep unseen features as `?`. Run the last command after editing. To replay the supplied comparison, omit `--input` and choose a fresh output path.

Ledger | build 0 · render 0 · CI 0 · wait 0. Offline analysis and CSV replay only.
