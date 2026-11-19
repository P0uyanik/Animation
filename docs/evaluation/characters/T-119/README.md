# T-119: garments round 3 and limb skin tone

Candidates on the current cast (girl 0.12.0, boy 2.1.0). Nothing is published or made current; published versions,
`*.spec.json`, `fidelity_baseline.json`, `garments/`, `garments_v2/` and the three older preset files are untouched.
Input `integration/r4-start@5a90975` (the task prompt's input; the task file names `origin/main`).

## Result per criterion

| # | criterion | result | evidence |
|---|---|---|---|
| 1 | girl: rounded collar seated at rest, half reach, full one-arm reach | **met, with a limit**: the collar lies on the vest neckline as one even rounded collar and stays there in both reaches; its outer edge still stands off the shoulder behind the vest neckline | [girl sheet](girl/girl_0.12.0_vs_T-119_strict.jpg) rows 1-4, [measures](measures_girl.json) |
| 1 | girl: two separately gathered bloomer cuffs | **met, with a limit**: two separate thigh bands, the shell gathered into them; from the front the two bands meet on the centre line and the cleft between the lobes is shallow | [girl sheet](girl/girl_0.12.0_vs_T-119_strict.jpg) rows 5-6 |
| 1 | boy: ankle notch closed through ankle flexion | **met**: no skin between hem and shoe at rest, toes up 25 deg, toes down 30 deg; the hem's ragged outline is unchanged and now shows trouser fabric | [boy sheet](boy/boy_2.1.0_vs_T-119_strict.jpg) rows 1-4, [measures](measures_boy.json) |
| 2 | boy limb skin within 5 L* of the reference (T-116 method) | **not met: 18.5 -> 14.9 L\***. Deliberate, see "Limb skin" below: the number is set by the reference's shadowed neck, and closing it with hand tone turns the hand brown next to the cheek | [fidelity](fidelity/), [hand tone](evidence/hand_tone_val27_front.json), [pickup](evidence/pickup_hand_tone.jpg) |
| 3 | candidate overrides here; one cheap preview each, then one strict sheet each | done | `*.T-119.override.json`, `girl/`, `boy/` |
| 4 | plain tests; default builds identical | 54/54; default builds identical in every garment piece, hand and material name | [tests.txt](tests.txt) |

## What was built
- **`garment/3`** (`pipeline/charsys/garments_v3/`, opt-in, registered in `versions.py`): extends `garment/2` by import.
  New item fields `collar_seat` (round collars), `cuff_gather` (shorts), `ankle_close` (trousers); see the package
  README. A `garment/3` block without a new field builds the `garment/2` geometry.
- **`skin_presets_r3.json`** (new file of the presets/3 family, id `skin-felt-limbs/3`) and its lookup in
  `materials/builder.py` (lookup only: no shader code changed).
- **Opt-in hook in `build_character.py`** (6 lines): `materials.assignments.skin_limbs`, when present, gives the hands
  their own material `M_skin_limbs`. The hands already had a material of their own (`M_skin`; face and body use
  `M_skin_face`), both built from the one `skin` slot. Without the slot the build is exactly as before.
- Overrides: `make_overrides.py` writes both from the published specs. The girl's override also sets the collar's
  fixed lift to 0 and the T-093b crotch arch off (the seat and the gather replace them).

## Garments: numbers (measure.py on the built masters, current against candidate)

| girl collar | rest | half reach | full one-arm reach |
|---|---|---|---|
| stand-off from the layers under it, p50 / p95 (mm): current | 12.6 / 24.3 | 12.8 / 24.5 | 12.5 / 24.9 |
| candidate | 9.7 / 22.0 | 9.5 / 21.5 | 9.1 / 20.6 |
| moved from its rest place, max (mm): current | - | 33.5 | 64.5 |
| candidate | - | 8.0 | 24.4 |

The current collar carries weight of the head (`DEF-spine.006`) and both upper arms, so it turns with the head and is
lifted by the arm; the candidate is carried by the chest and the shoulders only. The candidate's 24 mm at full reach
is its reach key lifting the collar's side over the rising sleeve.

| girl bloomers | current | candidate |
|---|---|---|
| gap between the two cuff bands on the centre line | -54.5 mm (they overlap) | +1.0 mm |
| shell hanging below the bands | 17.7 mm | 0 |

| boy ankle: skin not covered by any garment piece, cm2 | rest | toes up 25 deg | toes down 30 deg |
|---|---|---|---|
| current | 21.4 | 21.6 | 33.8 |
| candidate | 0 | 0 | 0 |

## Limb skin
`tools/fidelity/run.py` at its defaults (the run behind the published report T-116 cites; my run of the current
build reproduces its 18.3 dE00 / +18 L*):

| skin_limbs (median over the five val27 views) | dL* | dE00 | luma-matched dE00 | dC* |
|---|---|---|---|---|
| current 2.1.0 | +18.5 | 18.3 | 5.0 | -4.2 |
| candidate | +14.9 | 14.7 | 1.7 | -3.0 |

Per view dL* current -> candidate: front 14.1 -> 11.4, three-quarter 24.2 -> 21.7, side -1.6 -> -3.7, back
18.5 -> 14.9, back three-quarter 23.0 -> 20.6. skin_face is unchanged (-3.2). Fidelity score 67.7 -> 68.5.

**Why the 5 L\* target is not met.** The fidelity "limbs" region is all skin below the chin line: the hands and the
neck. On val27_front (boxes on the fidelity sheet, [numbers](evidence/hand_tone_val27_front.json)):

| median L\* / a\* / b\* | reference | current render | candidate render |
|---|---|---|---|
| hand, lit side | 73.2 / 11.9 / 14.4 | 72.7 / 10.3 / 19.3 | 69.6 / 15.0 / 17.8 |
| hand, shade side | 57.5 / 15.7 / 16.7 | 65.6 / 10.1 / 18.3 | 62.7 / 14.8 / 16.5 |
| neck | 46.6 / 24.0 / 25.9 | 56.8 / 13.9 / 19.1 | 56.7 / 13.9 / 19.1 |
| cheeks | 70.4 / 13.7 / 14.9 | 72.8 / 13.2 / 19.7 | 72.8 / 13.2 / 19.7 |

The reference's lit hand is as light as its cheeks; its region median (47-52) is the neck in the hood's shadow plus the
shade-side hand. The render's limb region is mostly hand (its neck is nearly hidden: region area -30%), so its median
is the hand's 63-72. A hand base colour that moves the region median by the missing 14 L\* (182/128/104, tried) gives
the brown hand in [pickup_hand_tone.jpg](evidence/pickup_hand_tone.jpg), right; the reference has no such hand.
The candidate instead matches the reference's hands: mean of both hands L\* 66.2 (reference 65.3, current 69.2),
a\* 14.9 (13.8, 10.2), b\* 17.1 (15.6, 18.8) - slightly deeper and pinker, no longer paler and greyer than the cheek.
Preset `skin-felt-limbs/3` = `skin-felt/3` with a shorter subsurface scale (0.05 -> 0.02) and half the rim sheen
(0.5 -> 0.25); base colour 226/178/162 in the override.

What would move the remaining number is the neck (face/body material, hood shadow, how much neck shows), not the
hands. That is outside this task's write-set and I did not attempt it.

## Limitations
- **Collar.** The vest stands 3 cm off the body (its ease), so its neckline is higher and wider than the blouse
  neckline. The collar is laid over it and its outer edge stands off the shoulder behind it (p95 22 mm, was 24 mm):
  light still passes under that edge in the side view. Closing it needs the vest's neckline lowered or its ease
  reduced (vest data), not more collar work.
- **Bloomers.** The thighs are 2 cm apart, so two cuff bands of this thickness meet on the centre line; the two legs
  read from the bands and a shallow cleft, less clearly than G08's two separate lobes.
- **Ankle.** The trouser hem itself is unchanged (same ragged notch); what shows inside it is now a close cuff in the
  trouser fabric instead of skin.
- The collar's reach key is driven in Blender only (like the `garment/2` reach keys).
- The sheets are pose sheets (current | candidate, same camera and light per row, 16 spp / 360 px,
  `character_neutral/1`) laid out with the T-087 tile code; `tools/review/recipe.py` has fixed turnaround rows and no
  pose rows, so it was not used. There is no reference column: the references show no reach or ankle flexion. Both
  columns are A-pose masters posed by the same script (arms down 35 deg, then the row's pose). Hair is hidden in the
  girl's collar rows only (her curls cover the collar from the side).
- The rejected dark-hand tile in `pickup_hand_tone.jpg` is a 4 spp preview from an earlier build, upscaled.
- Default-build identity: every garment piece, hand and material name of a default build equals the published
  master. Six other meshes (ears, lids) differ between any two builds in this environment, including a build made
  before any change here against the published master; that noise is not from this task.

## Tests
`python3 pipeline/charsys/tests/test_garments_r3.py --blender <b> [masters...]` -> 54/54 ([tests.txt](tests.txt)).
Also run, unchanged and passing: `test_garments_v2.py --quick` 45/45 and `test_garments_v2_t093b.py --quick` 9/9 (their
git check skips: no `origin/main` in this clone), the `garment/1` guard `tests/garment_generic_test.py` (exit 0, 12 min),
`test_versions.py` 107/107,
`test_materials_r2.py` 104/104, `test_materials_r2_graphs.py` 52/52, `test_skin_presets.py` 24/24,
`test_material_presets.py` 54/54, `test_skin_material.py` 10/10, `tools/tests/test_version_switch.py` 96/96,
`tools/check_doc_links.py`. Not run: the full (non-quick) `test_garments_v2.py`, `tools/check_all.py`, CI.
Blender: bpy 5.3.0 module behind a `blender` wrapper (`tools/bpy_blender.py`).

## Reproduce
```
python3 docs/evaluation/characters/T-119/make_overrides.py
blender -b --factory-startup -P pipeline/charsys/build_character.py -- --spec <published spec> --out <dir> --no-glb \
    [--override docs/evaluation/characters/T-119/<id>.T-119.override.json]
blender -b --factory-startup -P docs/evaluation/characters/T-119/pose_shots.py -- <out> girl|boy \
    current=<master> candidate=<master> [--samples 2 --px 200]        # preview; defaults 16 / 360 = sheet
python3 docs/evaluation/characters/T-119/compose_sheet.py <out> <sheet.jpg> "<title>"
blender -b --factory-startup -P docs/evaluation/characters/T-119/measure.py -- <out.json> girl|boy current=<master> candidate=<master>
python3 tools/fidelity/run.py --character boy_yellow_hoodie --build <master> --blender <b> --out <dir>
```

ledger: build 49 · render 53 · tests 21 · ci 0 · wait 0 (min)
