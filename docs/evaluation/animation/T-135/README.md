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

Pending: `run.py --baseline docs/evaluation/animation/T-135/baseline/<shot>/reach.json` on each E1 preview bake.
