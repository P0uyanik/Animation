# T-129 · Does a higher fidelity score predict owner approval?

**The score rose for 4 of 5 measurable owner-approved version changes (80%).** The exception was girl 0.11.0. The owner preferred its skin, hair colour, curls, neck and face, and accepted the wider hair that helped drive the score down. Both T-122 candidates also scored lower despite visibly improved faces. Those two judgements come from the T-122 review. The owner authorised candidate publication and had yet to approve either version. [Owner decisions](../../../process/OWNER_DECISIONS.md) · [T-122 visual evidence](../../characters/T-122/README.md)

| Comparison set | Score ranks the preferred result higher |
|---|---:|
| Owner-approved versions with a comparable, resolved score direction | 4/5 |
| T-089 face-system approval, measured separately on boy and girl | 2/2 |
| T-049 hybrid hair choice, C versus A and B on each character | 3/4 |
| T-122 candidate face improvements, reviewer judgement | 0/2 |

The five version pairs contain only approvals, so 80% measures agreement on upgrades. Rejection accuracy is unknown. Counting the measured system and design comparisons gives 9/11 owner-labelled pairs, with repeated observations from shared decisions. The CSV lists deferrals, rejected proposals and approvals lacking paired runs as `NA`. For example, T-093 round 1 required another pass on the backpack, collar and vest, and T-110 was parked partly for worse hoodie colour. A later bundled version score cannot isolate either decision.

### What the components picked up

Across the five version upgrades, silhouette and proportions each rose on 3/5. Regions, landmarks, colour and texture each rose on 2/5. Of the four upgrades with the T-064 components, face and hair each rose on 3/4 and skin on 2/4. These counts show direction only. Three comparisons explain why it matters.

- **Girl 0.10.0 → 0.11.0.** Face gained 30.97 points and hair gained 2.40. Silhouette fell 5.88, regions fell 6.00 and skin fell 12.51 despite the owner's preference for the new skin. The 5% face weight contributed only +1.55 to the −2.11 total. At T-094 the boy gained just 0.09 overall as improved proportions (+12.29) offset losses in texture (−14.01) and colour (−6.53).
- **T-122 faces.** Boy lost 0.4698 overall, mainly from proportions (−0.394 weighted points) and face (−0.153). Girl lost 0.8833, with face (−0.553) and proportions (−0.302) the largest losses. The neutral face measure already samples lid lightness, chroma and cheek blush. Its small windows miss closed-lid skin colour during a blink, the pale shelf beneath a lens and whether a delighted smile or reluctant pout actually plays. [Face windows and their scale](../../characters/T-064/README.md) · [Candidate sheets](../../characters/T-122/README.md)
- **Hair and clothing.** The earlier six-component score ranked the girl's sculpted B above hybrid C by 1.1086, although the chosen hybrid preserved a felt surface and readable locks. Today's hair score measures outline, strand direction and relief, but a whole-hair average cannot locate a bad fringe or a ridge at the back. Garment colour and mask overlap can survive a wrong flap, frayed collar or reach penetration. The boy's fidelity comparison even hides backpack objects. [Hair study](../../characters/T-049/README.md) · [Boy comparison setup](../../characters/T-080/fidelity/fidelity.json)

### Ranked changes to evaluate

1. **Score the face in the states the owner reviewed.** Align front and three-quarter crops to eye corners. Compare closed-lid colour to adjacent skin in Blink, measure pale-band area below the lens in neutral, and compare mouth opening and contour against labelled expression references. Report each state. In a trial blend of 80% existing total and 20% new face score, the new component must improve by more than 1.88 points for the boy and 3.54 for the girl to reverse the T-122 results. Clearing both would move candidate agreement from 0/2 to 2/2. These are break-even estimates; there are no archived probe scores.
2. **Trial a smaller silhouette weight.** Moving seven percentage points from silhouette to face (20% → 13% and 5% → 12%) changes T-081 from −2.11 to +0.47. On the four owner version pairs with both components, agreement rises from 3/4 to 4/4. Both T-089 comparisons stay positive, but T-122 stays 0/2 and the girl's delta worsens to −1.67. This is an in-sample sensitivity check. Freeze the weights before the next owner review and test them on those new verdicts.
3. **Add local hair and garment comparisons to the review sheet.** Score crown, fringe and back locks separately against matched reference crops. For clothing, compare flap and collar edges at rest and vest penetration in reach. Preserve each local result so the owner can see the reason for a flag. The historical hair test is whether this resolves girl B versus C while keeping the other three orderings (3/4 → 4/4 if successful). T-093 supplies a rejected first pass and an accepted revision for a future test. Neither has a matched full-score delta.

### Reading and extending the CSV

At input `b80dae6`, subtract before from after using `overall.score` and 100 × `overall.subscores` from the linked JSON paths in [calibration.csv](calibration.csv). Positive means closer by the metric. Agreement uses strict score direction, independently of the two-point regression gate. Empty numeric cells mean unavailable. For future reviews, append the exact pair, decision source, scorer revision and render variant, and keep candidate readings separate until the owner decides.

Baseline history runs from `d5cf952` (girl 0.7.1) through `c1e088c` (0.9.0, including a lighting change). For 0.10.0, `ca460a2` reports 65.40 but retains 0.9.0's 65.4074. A repeat with the old tool gave 65.4199, reversing that tiny delta. Its direction is unresolved. T-064 (`ac274c5`) rescored the same renders under new segmentation, alignment and weights. Subsequent pairs start from that new baseline, then use `96de404` / `93811bf` and `dda7073`. For T-089 use its own base run; the girl's final blink-only edit postdates its neutral score. [T-064 rebaseline](../../characters/T-064/README.md) · [T-089 matched runs](../../characters/T-089/README.md)

ledger: build 0 · render 0 · tests 0 · ci 0 · wait 0 (min)
