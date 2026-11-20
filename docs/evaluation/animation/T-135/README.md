# T-135 (E1m): reach measurements, baseline

Tool: [tools/motion_checks/reach/](../../../../tools/motion_checks/reach/README.md) (report, not a gate; 12 fixture
tests: `python3 tools/motion_checks/reach/tests/test_reach.py`). Baseline = input `37901c4`
(`integration/r5-start`), each shot's s010 baked with `run_shot.py --stages prepare,bake` and this engine build.
Per-move tables: [e907](baseline/e907/reach.md), [e909](baseline/e909/reach.md), [e910](baseline/e910/reach.md).

## Baseline (medians over the wrist moves)

| | e907 | e909 | e910 |
| --- | --- | --- | --- |
| moves (extend) | 4 (3) | 10 (6) | 7 (4) |
| path deviation mm / share of chord | 36 / 0.18 | 25 / 0.18 | 52 / 0.30 |
| moves with a straight path (deviation < 1 % of chord) | 1 | 2 | 2 |
| duration f / peak m/s / peak at | 14 / 0.81 / 0.53 | 18.5 / 0.39 / 0.59 | 13 / 0.72 / 0.47 |
| ease in / out (share below half peak) | 0.25 / 0.15 | 0.13 / 0.13 | 0.14 / 0.14 |
| peak acc / dec mm/f² | 8.7 / 13.3 | 5.5 / 4.6 | 6.3 / 8.7 |
| torso onset lead f (share of moves where torso leads) | 0 (25 %) | −1 (10 %) | +4 (43 %) |
| shoulder (clavicle) / hip rotation lead | none | none | none |
| overlap peak after the wrist peak f, neck / head / hair | 15 / 15.5 / 17 | 13.5 / 24 / 23 | 23 / 21 / 24 |
| settle after the stop f, neck / head / hair | 13 / 15.5 / 13.5 | 27 / 22.5 / 36 | 23 / 0 / 32 |

## Findings

1. **No shoulder or hip anticipation anywhere.** `DEF-shoulder` never rotates more than 0.05 °/f and the hips at
   most 0.18 °/f (pivot 0.07 mm/f) in any reach of the three shots: reaches are arm (plus some chest) only.
2. **The torso rarely leads.** It starts before the wrist in 1/4, 1/10 and 3/7 moves; in e909 7 lead windows are
   `busy` (the torso was already moving, mostly the carry), so the onset is not measured there.
3. **Straight-line moves.** Five moves (e907 boy R f22–41, e909 boy R f163–179 and girl L f68–86, e910 boy R
   f81–97 and f100–110) follow their chord exactly with a symmetric profile (ease 0.10–0.12 each side, peak at
   0.45–0.47): a smoothstep along a line, no arc. The other moves arc by 0.12–0.62 of the chord.
4. **Overlap and settle are not reach follow-through yet.** Head / neck / hair peaks come 13–24 f after the wrist
   peak and settle at the 36 f cap in many moves: in these shots they are looks, reactions and spring hair, not a
   lag behind the arm. Compare them move by move against T-134's previews, not as absolutes.

## Against T-134 previews

### E1a: e910 `s010_e1` vs `s010` (T-134 `ef8e270`)

Both baked with T-134's own engine build. `s010` from that build is frame-for-frame identical to the baseline
above, so the setting is opt-in as required. The reaches are measured on T-134's spans, boy `hand.R` f57–76 and
girl `hand.L` f104–114 (`--window`), in [e1a/](e1a/). The segmented moves of `s010_e1` are in
[e1a/s010_e1_moves](e1a/s010_e1_moves/reach.md).

| | boy s010 → e1 | girl s010 → e1 |
| --- | --- | --- |
| stall (deepest dip between speed humps / peak) | 0.24 → 0.03 | 0.11 → 0.01 |
| speed after the peak, mm/f | 30.1 24.8 17.1 **5.3** 6.1 10.5 12.6 12.2 9.2 3.7 → 35.3 29.2 16.5 10.7 10.7 7.5 4.5 2.7 3.0 2.6 | 52.4 21.4 12.2 **18.0** 16.0 6.9 → 60.0 35.3 26.3 16.4 7.1 3.7 |
| largest 1-frame / 2-frame speed drop, mm/f (share of peak) | 11.8 / 19.4 (0.39 / 0.64) → 12.7 / 18.8 (0.36 / 0.53) | 31.0 / 40.2 (0.59 / 0.77) → 24.7 / 33.8 (0.41 / 0.56) |
| path deviation / chord, bulge direction up | 0.31, +0.50 → 0.39, +0.89 | 0.35, −0.60 → 0.39, −0.80 |
| torso (chest) peak °/f, onset / peak lead f | 0.25 (below floor) → 0.68, +11 / +4 | 0.16 → 1.13, onset busy (≈ +2) / +4 |
| shoulder pivot peak mm/f, onset / peak lead f | 0.46 → 3.1, 0 / +4 | 0.34 → 4.9, +7 / +3 |
| clavicle (`DEF-shoulder`) rotation °/f | 0.05 → 0.05 | 0.05 → 0.04 |
| hips rotation / translation | 0.05 °/f, 0.07 mm/f → 0.10, 0.07 | 0.06, 0.05 → 0.24 (peak f103, ≈ 1° total), 0.05 |

- **Stall: gone in both.** The speed now falls without rising again. The boy's dip to 5.3 mm/f (f70), followed by
  a climb back to 12.6, became a 10.7 mm/f plateau that then eases out.
- **Path.** Neither reach was straight before. Both now arc more, the boy upwards and the girl downwards. The two
  straight-line moves (boy f81–97 and f100–110) are outside E1a's reaches and are unchanged.
- **Anticipation.** The chest and the shoulder pivot now peak 3–4 f before the wrist; the boy's chest starts 11 f
  before. The clavicle bone still does not rotate. Hips: the girl's turn is a 0.24 °/f bump about 6 f before her
  reach (about 1° in all), the boy's is negligible, and neither translates.
- **Slow-down.** The boy's drop is unchanged in size: 35.3 → 16.5 mm/f over 2 frames is 0.53 of the peak, against
  0.64 before. The difference is that it no longer bottoms out and re-accelerates. The girl's slow-down is softer
  but still loses 41 % of the peak in one frame (60.0 → 35.3).
- **New:** the boy's wrist nearly stops for one frame at **f52** (7.7 → 0.9 → 5.8 mm/f), in the drift before the
  reach. The baseline has 8.0 there. The hips turn slightly at the same time (0.10 °/f, f50–51).

### E1a+b+c: e910 `s010_e1` vs `s010` (T-134 `1443e7c`)

Same method as above. `s010` from this engine build is still frame-identical to the baseline. Data: [e1abc/](e1abc/).

| | baseline s010 | E1a | E1a+b+c |
| --- | --- | --- | --- |
| boy f57–76: stall / 1-frame drop / 2-frame drop (mm/f, share of peak) | 0.24 / 11.8 / 19.4 (0.64) | 0.03 / 12.7 / 18.8 (0.53) | 0.05 / 9.3 / 17.6 (0.59 of 29.6) |
| girl f104–114: stall / 1-frame drop / 2-frame drop | 0.11 / 31.0 / 40.2 (0.77) | 0.01 / 24.7 / 33.8 (0.56) | 0.00 / 19.1 / 29.6 (0.56 of 52.7) |
| chest lead (onset / peak, f) boy · girl | – · – | +11/+4 · ≈+2/+4 | +11/+3 · +12/+3 |
| clavicle `DEF-shoulder` rotation | 0.05 °/f | 0.05 | 0.05 (no lead) |
| hips rotation peak boy · girl (°/f) | 0.05 · 0.06 | 0.10 · 0.24 | 0.09 · 0.24 (no translation) |
| boy wrist at the f53 hitch (mm/f, f52–54) | 7.1 6.0 7.0 | 7.7 0.9 5.8 | 7.7 3.1 6.2 |
| boy carry f81–97: deviation mm (share), bulge up | 0 (straight) | 0 | 16 (0.12), +0.35 |
| boy carry f100–110 | 0 (straight) | 0 | 9 (0.12), +0.41 |
| girl f104–115 hips / chest (°/f) | ≤0.03 / ≤0.15 | – | 0.24→0.03 by f108 / 1.06 at f106 → 0.12 by f110; hand rotation same as baseline (peak 30 °/f f107–108, 0 from f112) |
| after contact, 30 f: head max °/f · hair max / mean °/f, swings > 0.5 °/f: boy | 0.08 · 3.2 / 0.86, 4 | – | 0.07 · 5.5 / 2.4, 5 |
| girl | 0.08 · 24 / 7.7, 4 | – | 0.07 · 24 / 8.8, 6 |

- Slow-down after the peak: softer than baseline for the girl, about the same for the boy.
- Clavicle: does not rotate, so there is no clavicle lead.
- Hips: a small turn for the girl only (0.24 °/f at f104).
- f53 hitch: reduced from 0.9 to 3.1 mm/f, but still deeper than baseline (6.0).
- Carries: now arc upward, by 12 % of the chord.
- Girl's reach end (f109–110): no turn spike. The chest turn has faded by f110 and the hand rotation matches baseline.
- After contact: the head is unchanged and does not react. Hair moves more (boy mean ×2.8) and swings 1–2 more times.
