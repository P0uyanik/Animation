# T-150 | Neutral eye-shape targets

**Both girls need a higher inner corner.** The references show an almost level line between the corners, a rounded upper lid and a narrow crescent of white above the iris. The renders bring a diagonal edge of skin down across the iris on the nose side. The gold chords in the [evidence sheet](evidence.jpg) show the difference at a glance.

| Priority | What to change | Reference and current measurements |
|---|---|---|
| 1 | Lift the nose-side opening and move the upper-lid peak toward the middle on both girls. | In front view the inner corner is within 5% of an opening width of the outer corner's height. It sits 24–33% lower on auburn 0.13.0 and 27–30% lower on the third girl. Ref_30 and G01 already overlap the strict render in overall height/width. Increasing height alone would leave the diagonal. |
| 2 | Recheck iris size and spacing together on the third girl. | The reference iris spans 74–77% of the opening width and 35–36% of the distance between iris centres. Pass 2 gives about 67% and 41–42%. T-133's proposed neutral gives 66–67% and 49%. Bringing the eyes closer increased the second ratio while leaving the first nearly unchanged. |
| 3 | Restore the thin strip of white above the iris. Check the outer white on turns. | Above the iris, auburn fronts show 5–6% of opening width and third-girl fronts show 3–5%. All measured renders reach zero. In G02 the outer white occupies 31% on the near eye and 6% on the far eye. The 0.13.0 turn shows 42% and 16%. These are through-lens appearances at the pictured yaw. |

### Applying the targets

Use the front bands in [targets.json](targets.json) on each open eye in a neutral front image. Auburn references include the glasses. For G02, compare the near and far eyes separately at matching yaw and gaze. Lens effects, frame overlap and foreshortening are inseparable in that image. Each oblique target has one observation. The third girl's front set uses 01, the open front panel of 04, and the head-front and neutral e1 crops of 14. Blinks and expressive squints require different targets.

[Measurements](measures.csv) are manual image-plane estimates. Image left/right follows the viewer. W and H are the width and height of the visible opening's bounding box, measured inside the lash. D is horizontal iris diameter, estimated from the exposed arc where the lid clips it. Spacing is iris-centre to iris-centre. Iris x runs from temple toward nose in units of W and y runs down from the opening top in units of H. White runs start at the visible iris edge along the centre axes and end at the lid, in units of W. Arch is the vertical rise to the lid peak above the corner chord at the peak's x. Corner angles span the upper and lower lid at 10% W inward from each corner. Positive drop means the inner corner is lower.

Targets are reference medians. Symmetric tolerances cover the largest observed deviation plus a tracing allowance of 0.035 in normalized units, 0.015 for D/spacing or 8° for angles. These are working bands for future matched images. Ref_30's small neutral panel and G02's rim-adjacent far corner have the greatest tracing uncertainty.

For remeasurement, the CSV gives each 480-pixel strip's source origin and uniform scale. In strip pixels, `trace_px` records left and right corner xy, peak xy, bottom y, upper/lower y at 10% then 90% W, iris centre xy and D, then white runs above/below/image-left/image-right. T-122 uses the candidate column in both sheets. T-126 uses pass 2 and T-133 uses the proposed neutral at `7bfc652`.

ledger: build 0 · render 0 · tests 0 · ci 0 · wait 0 (min)
