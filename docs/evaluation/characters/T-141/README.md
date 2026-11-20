# T-141 — native hair curves as an opt-in groom option (experiment)

Recommendation: **adopt "add" as an opt-in experiment option, reject "replace"**. Nothing is wired into the build;
no current or candidate character changes. A character only gets hair curves when someone runs the tool on a copy.

## What exists

- `pipeline/charsys/groom/hair_curves.py` — reads a built master, writes a **new** `.blend` (refuses to overwrite,
  refuses `assets/characters/**`). Per matching `hair_*` lock mesh: guides traced along the lock in rest space,
  then Blender's own Interpolate / Clump / Curl / Frizz / Set Hair Curve Profile node groups, then a follow group
  that binds every point to the deforming lock surface. Lock meshes stay as the silhouette.
- Options (`plush-studio.hair-curves/1`): `options/*.json`. `add` = hair curves on top of the felt fibres,
  `replace` = felt fibre layers hidden.
- Test: `python3 pipeline/charsys/tests/test_hair_curves.py --blender blender` → 37/37. **Not registered in
  `tools/check_all.py`** (outside the write-set; Supervisor item).

## Cost (4 vCPU, CPU Cycles)

Shot `e907_exchange/s010_verbs` f65, 1280x720, auburn girl swapped through `cast.json`. T-124 baseline on its
machine: final 433 s, review16 ≈ 66 s. Same-session numbers (`shot/cost_flicker.json`):

| | base | add | replace |
|---|---|---|---|
| final 128 spp, s/frame | 462 | 523 (+13%) | 472 (+2%) |
| review16, s/frame | 74 | 84 (+14%) | 81 (+10%) |
| sync + BVH, s | 10 | 17 | 14 |
| shot assembly (`shot_render --blend-only`), min | 11 | 56* | 56* |
| re-evaluation per pose change, s (auburn / third) | 1.2 / 0.9 | 3.5 / 1.8 | 3.1 / 1.5 |

\* two assemblies ran side by side; base ran alone. Still several times slower — the largest cost found.

Strands: third girl 160k curves / 1.68M points, auburn 196k / 4.27M; tool run 5–10 s per character.
Character-only crops (16 spp, 600 px): third 4 views 539 / 883 / 657 s, auburn 3 views 311 / 421 / 372 s — measured
while other jobs ran, ratios only.

## Flicker (T-125 `tools/motion_checks`, frames 60–66, 16 spp, OIDN)

Identical finding set for base / add / replace: 1 flicker issue (`fibres` held noise 0.059 > 0.045, present in the
baseline, other character's felt), 23 popping, 2 interpenetration — none from the hair. Hair region denoised noise
max 0.040 / 0.040 / 0.041, flip share 0.37 / 0.36 / 0.31. Strand set is generated in rest space, so it is the same
every frame; no strand popping seen. Only 7 frames checked; no long motion.

## Look

- `third/sheet.jpg`, `third/hair_crops_100.jpg` (refs 01/02/07/17_W04); `auburn/sheet.jpg`,
  `auburn/hair_crops_100.jpg` (ref_30/G06); `shot/f65_hair_100.jpg` (posed shot, 100%).
- add: visible strand direction along the locks, wispy tips and curly flyaways, felt body kept. Closer to the
  references' combed-wool waves than the uniform felt of the base.
- replace: reads as silky hair, loses the wool/plush fuzz, colour shifts paler/flatter. Off-style.
- At strict-sheet scale (360 px cells) base / add / replace are hard to tell apart; the difference is a close-up
  and mid-shot one (see the 100% crops).
- Not judged by the owner; no approval implied.

## Limits / open

- Strands also grow on hidden inner faces of the locks (5.2 m² on the third girl); culling them would cut cost.
- Assembly and re-evaluation slowdown (follow group does 6 nearest-surface lookups per point); a baked binding
  would be the next step before any production use.
- The output copy gets an extra UV map and rest-position attribute on the lock meshes; inputs are untouched.
- Curves have no Armature modifier in Blender 5.3; following relies on the lock mesh deformation.
- Not verified: long shots, fast head motion, hair dynamics chains under stress, memory peak (bench reports none).

## Gate (`tools/check_all.py --base origin/main --task T-141`, full Blender tier)

PASS: frozen assets, write-set (28 paths, all inside the claim), shared-systems lint, C++ build + tests, Blender
tier incl. regression (boy 67.23, auburn girl 64.13, third girl PASS — unchanged characters).
Open: `Guarded paths` wants a `Supervisor-Approved: pipeline/charsys/tests/test_hair_curves.py` trailer (Supervisor
item). `test_ci.py` failed only because the clone was shallow (commit ab9fd4c missing); 39/39 OK after
`git fetch --unshallow`.

## Reproduce

```
blender -b --factory-startup -P pipeline/charsys/groom/hair_curves.py -- --blend <master.blend> \
    --out <new.blend> --options docs/evaluation/characters/T-141/options/auburn.add.json --report r.json
python3 tools/review/recipe.py sheet docs/evaluation/characters/T-141/auburn/auburn.recipe.json --blender blender --out <dir>
python3 docs/evaluation/characters/T-141/tools/third_sheet.py --out <dir> base=<blend> add=<blend> replace=<blend>
bash docs/evaluation/characters/T-141/tools/bench_queue.sh <run dir> blender
```

Revert: one `git revert` per commit or delete the new files; nothing else references them.
