# T-167: hair round 7 (reference fidelity), WIP — paused 2026-11-20 on owner decision (~10:10 CET)

Branch `t-167-claude-hair-r7` from `t-160-claude-hair-r6@2dccd74`; input main `3c698c7`. Opt-in only; nothing published.

## Done so far
- `pipeline/charsys/groom_r6.py` (groom/5): new opt-in key `clump` on masses / locks (per-clump bend, twist, lumps
  from a fixed sequence, no random numbers). Specs without it build as before. `test_hair_r6.py` 42/42.
- `tools/make_overrides.py --base-dir <T-155 candidate specs @0677274>` writes `overrides/*.hair_r7.override.json`
  from the T-160 r6 overrides.
  - boy: blunt, uneven clumps, shorter outward flicks, 3 crown tufts, uneven fringe. Hair-only preview: pickup
    sightline proxy 1.0/0.891, 0.89/0.762, 0.608/0.542 (r6: 0.976/0.889, 0.853/0.721, 0.588/0.525), keep-out 0.
    One cheap Cycles preview seen (8 spp); side clump length changed after it, not re-rendered.
  - auburn girl: thinner ribbon ringlets on a wider coil, back curls 6 cm longer, shorter curtain, smoother bun,
    higher sweeps, less fuzz, glossier material override. Geometry preview only (Workbench).
  - third girl: 19 thin flat fringe wisps (keep-out violations 20, r6 58), wider / thicker / more side and back
    locks. Geometry preview only (Workbench). Bow seat unchanged.

## Not done
No Cycles evidence yet: strict sheets, 100 % hair crops next to the refs, flicker turntables, full builds of the two
girls (interrupted by the pause), README tables. Values above are first passes, not reviewed against Cycles renders.
