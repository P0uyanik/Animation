# T-093b: garment completion (boy trousers/shoes, girl shorts leg split)

Built on the T-093 garment/2 candidates (read-only). Candidates in `assets/characters/<id>/spec/candidates/T-093b/`
(written by `make_overrides.py`, combined look by `make_combined.py`). Nothing is published or made current;
published versions, `*.spec.json` and the T-093/T-092 candidates are untouched.

## Results
| | decision | evidence |
|---|---|---|
| boy: T-090b trousers/shoes values on T-093 (`boy_yellow_hoodie.T-093b-T090b.override.json`) | **dropped**: the boy keeps T-093 | strict sheet `boy_2.0.0_vs_T-093b-T090b/…_strict.jpg` next to T-093's `../T-093/boy_2.0.0_vs_T-093/…_strict.jpg`; garment masks below |
| girl: `leg_split` crotch arch + sleeve/shorts re-fit (`girl_auburn_bun_glasses.T-093b.override.json`) | candidate for the owner | `girl_0.11.0_vs_T-093b/…_strict.jpg`, on T-092 presets/3: `girl_0.11.0_vs_T-093b_T-092/…_strict.jpg` |

Boy sheets for the owner remain T-093's (`../T-093/boy_2.0.0_vs_T-093*/`): the boy candidate is unchanged, so they
were not re-rendered.

**Boy.** T-093 had already moved further than the T-090b proposal on the same paths (gusset depth 0.12 vs 0.242,
shoe upper 60 vs 63.5 mm; length/width extras nearly equal, trouser length 1.0 vs 0.987). Put on T-093, the proposal
lowers the leg split (val27 front/side show the legs separating just below the hoodie hem) and raises the shoe
slightly. The sheet is nearly indistinguishable from T-093, and the trouser/shoe masks are lower in every view:

| boy (val27, compare pose) | garment score | front trousers / shoes | 3/4 | side | stock fit |
|---|---|---|---|---|---|
| T-093 | **65.83** | 0.726 / 0.643 | 0.721 / 0.596 | 0.582 / 0.682 | 67.80 |
| T-093 + T-090b values | 65.09 | 0.716 / 0.631 | 0.712 / 0.591 | 0.575 / 0.680 | 68.07 |

**Girl: the missing leg-split control.** In T-093 the shorts' shell carries a crotch bridge (the hip band of the
body selection, puffed and draped) that joins both legs at the front and back centre. `leg_split` pulls the
inner halves apart in x only, which stretches the bridge's faces, so the hem still reads as one band between the
legs (`preview/girl_shorts_T-093_workbench.jpg`; a ray at the front centre 1 cm above the hem hits the shell). New
opt-in `leg_split` keys in `garment/2` (`pipeline/charsys/garments_v2/outlines.py`): `crotch_lift` (default 0 =
off), `arch_width`, `arch_power`. Before the split, every piece below the split top within `arch_width` hip-joint
offsets of the centre line is compressed above an arch. The arch raises the hem at the centre by `crotch_lift` of
the split height and falls off with a smoothstep, so the bridge rises into an inverted V and the legs separate
(`preview/girl_shorts_T-093b_workbench.jpg`). With the defaults the T-093 output is byte-identical (test, vertex
hash of every shorts piece against a build made before the change).

**Girl re-fit** (`tools/fit/run.py`, Workbench, sheet30 front / front-left / left, A-pose, chin+nose; plus
`garment_score.py`, the T-090b garment term: a flat Workbench label pass per trial, placed by the fit's registration,
mean blouse/shorts IoU against the annotated `garment:` regions):

| run | changed | garment score | front blouse / shorts | 3/4 | side |
|---|---|---|---|---|---|
| `fit/girl_t093` T-093 | (no arch) | 50.15 | 0.424 / 0.704 | 0.244 / 0.673 | 0.288 / 0.676 |
| `fit/girl` r1 (4 trials) | sleeves 0.97-1.0, puff 24-32 mm, shorts length, lift 0.35-0.75 | start best, 49.13 | | | |
| `fit/girl2` r2 (4) | sleeve puff 30-34 mm, length, lift 0.45-0.7 | 49.86 | | | |
| `fit/girl3` r3 (5) | sleeve puff 31-34 mm, shorts puff 30-40 mm, lift 0.1-0.35, arch width 0.4-0.8 | 51.54 (trial 3) | 0.423 / 0.722 | 0.237 / 0.682 | 0.342 / 0.687 |
| `fit/girl5` **chosen** | r3 trial 3 with lift 0.3 + smoothstep falloff | **51.66** | 0.423 / 0.727 | 0.244 / 0.675 | 0.342 / 0.689 |

Rounds 1-2 showed that shorter sleeves or less sleeve puff cost blouse overlap, so the sleeves stay at full length
(1.0). The large arch (lift ≥ 0.45) cut a notch much wider than the reference's small centre V
(`fit/shorts_mask_overlay_round2.jpg`: white = both, red = reference only, blue = candidate only), and the
reference legs are fuller at the sides. Round 3 gave the best mask score at lift 0.17, but the bridge still read as
a slab on the Workbench strip. Lift 0.3 (arch_width 0.7, power 1, smoothstep falloff added after r3) opens a visible
V and scores higher than r3. Chosen: sleeve puff 30 → 32.1 mm, shorts puff 30 → 38 mm, crotch arch lift 0.3. The
stock fit score is unchanged within 0.6 (67.45-68.03).

**Vest in reach** (T-093's `reach_evidence.py`, read-only, 4 spp preview renders; `reach/`). The vest is unchanged.
The fuller blouse sleeve does not worsen the reach:

| | reach flare max / p99 | reach vertices in blouse, p95 / max depth | rest vertices in blouse, p95 depth |
|---|---|---|---|
| T-093 | 5.47 / 4.88 cm | 495, 4.0 / 19.2 mm | 110, 0.90 mm |
| T-093b | 5.43 / 4.87 cm | 472, 4.0 / 19.2 mm | 127, 0.87 mm |

## Limitations
- At rest, slightly more vest vertices sit inside the blouse (110 → 127) at the same depth (p95 0.9 mm, under
  the 2 mm test threshold).
- The girl's arch is small, as in the reference, so at sheet scale the split reads as a centre notch with the legs'
  inner walls meeting above it. The inner hem shows small pinched fold tips from the drape (T-093 has them too).
- `garment_score.py` reproduces the T-090b garment term (its script was not committed). Its numbers are close to
  T-090b's but not proven identical.
- Fit budgets are small (start + 3-4 trials per round), so the fit is a local improvement, not an optimum.
- The boy's T-090b decision rests on near-identical sheets plus the mask numbers. It is a judgement call.

## Tests
`python3 pipeline/charsys/tests/test_garments_v2_t093b.py --blender <b> --girl-t093-master <T-093 build before the
change> --girl-master <T-093b build>` → 16/16. `python3 pipeline/charsys/tests/test_garments_v2.py --blender <b>`
→ 70/70 in the full run plus the git merge-base check (71 with origin/main fetched; `--quick` 46/46). No test or
threshold of `test_garments_v2.py` changed. Log: `tests.log`. Blender: bpy 5.3.0 module behind a `blender` wrapper.

## Reproduce
`python3 docs/evaluation/characters/T-093b/make_overrides.py && python3 docs/evaluation/characters/T-093b/make_combined.py`;
fits: `tools/fit/run.py --spec <0.11.0 spec> --override <fit/girl*_start or the T-093b override> --bounds fit/<r>_bounds.json
--views sheet30_front,sheet30_front_left,sheet30_left --landmarks chin,nose --height 512 --seed <4|5|6|7>`
(`girl5` used `girl4_bounds.json`, i.e. lift held at 0.3), then `garment_score.py --fit <out> --garments blouse,shorts
--hem shorts --annotations assets/characters/girl_auburn_bun_glasses/references/annotations`. Sheets:
`tools/review/recipe.py preview|sheet <recipe>` (Cycles 2 spp/120 px preview, 16 spp/360 px sheet).

## Wall time
Times come from the tool timestamps (UTC, 22:34-00:20). Overlapping work is counted once, in the category that
was waiting. Build covers the Blender setup, diagnostic builds and the five fit rounds with their Workbench passes.
Render covers the previews and the three Cycles sheets (boy 23:15-23:29, girl 23:40-23:57, girl+T-092 00:00-00:19).
ledger: build 38 · render 48 · tests 12 · ci 0 · wait 0 (min)
