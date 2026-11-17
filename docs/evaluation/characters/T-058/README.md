# T-058: Boy 2.0 — body integration, face with brow/mouth controls, hoodie garment

Status: **development evidence; unpublished and unapproved (path B: owner visual approval needed).** Branch
`t-039-codex-boy2-body`. The frozen 1.0.0 / 1.1.0 specs and assets are not touched. All new behaviour is opt-in spec
data on shared systems, so it is off for every other character. No boy-specific code was added.

## Part 1: T-039 integrated with staging

`git merge origin/staging` (commit `1bbd990`). Two files conflicted. Both sides were kept:

- `spec.py`: T-043's `PART_SCHEMA` / `PART_SECTIONS` and T-039's `BODY_ONLY_SECTIONS`.
- `build_character.py`: T-043's dispatch by pin (`family(pins["face"])`) plus T-039's optional face section.

T-039's opt-in body features (`head.profile_levels` loft, `leg.ankle_x`, comparison pose, `LM_chin`) stay inside
`body_generic/1`. With the key absent, the arithmetic is unchanged (owner rule 2026-11-17: opt-in parameters with
"off = identical output"). So no new body version was registered. That would also need `versions.py`, which T-056 holds.

One test change outside the write-set:

- `pipeline/charsys/tests/test_versions.py` used `spec_files()[0]` as its pin-test base. The body-only
  `*.2.0.0-dev.spec.json` sorts first, has no hair section and has a `body_generic/1` body. It therefore crashed
  (`KeyError: 'hair'`), and the "unknown body version" case read "contradicts" instead of "unknown".
- The base is now the first full legacy spec, which is the one the test always used before. No assertion was changed.

After the merge, these checks were run: `verify_charsys` PASS, `test_export_engine` 13/13, `test_versions` 73/73
PASS, and a 2.0.0-dev build. The full gate is listed under Checks.

## Part 2: what was built

| Area | Shared change (opt-in) | Boy 2.0.0-dev spec data |
| --- | --- | --- |
| Face controls | `face_generic.py`: `action_units.split` makes per-side copies X.L/X.R (X.L + X.R = X, blended over ±6 mm at the midline) of BrowDown, BrowSad, EyeSquint, EyeWide, MouthSmile, MouthFrown, MouthPout. `action_units.pout_m` adds **MouthPout**, a forward/narrowing field applied to lips, mouth interior and skin together. `expressions.custom` adds character presets, exported to the engine under a lowerCamel name. `face_features.py`: rest shape `pout` | split BrowDown/EyeSquint/MouthSmile/MouthFrown; pout 2.5 mm |
| Face look | (spec only) | heavy upper lid at rest (`upper_edge_deg` 6, nearly flat edge); large dark-brown iris; low flat thick brows; tiny pout mouth baked as the rest shape; small nose; soft blush; larger ears |
| Expressions | — | Happy = `Smile` override (lid arcs, closed smile, pout released); Sad, Angry, Surprised = overrides; **Bored** and **Skeptical** = custom presets using the per-side controls |
| Hoodie | new `garments/hoodie.py`, type `hoodie` in `garment/1` (validated, documented). It is the shared top plus a dropped shoulder (sleeves start at the joint), the hood lying down (rolled rim with a V at the chest, bag on the upper back, edge roll), a kangaroo pocket (trapezoid pouch, rolled top edge, slanted openings), two drawstrings with tips, and rib ridges on the hem and cuffs. All dimensions scale with the body fit | mustard fleece, cream cords |
| Trousers, shoes | existing `trousers` / `shoes` types | charcoal fleece joggers; yellow felt shoes with cream soles |
| Hair | `build_character.py`: `hair_clumps/*` can now be built on a `body_generic` head. The ellipsoid comes from spec data, and `hair.py` is not changed | `groom: hair_clumps/1` pinned (the current 1.x hair, seed 11, the 1.x ellipsoid). Hair v3 (T-044) comes after owner approval |
| Pins | — | explicit `generators` block: body_generic/1, face_generic/1, hair_clumps/1, garment/1, accessories none, rigify_human/1, presets/1, export/4 |

The spec values are written reproducibly by [make_spec.py](make_spec.py).

### Controls the facial layer (T-046) can drive

`face_BrowUp.L/R`, `face_BrowDown(.L/.R)`, `face_BrowSad`, `face_MouthSmile(.L/.R)` and `face_MouthFrown(.L/.R)`
(mouth corners up/down), `face_JawOpen` and `face_MouthO` (mouth open), `face_MouthPout`, `face_Blink.L/R`,
`face_EyeSquint(.L/.R)`, `face_EyeWide`, plus presets `Smile`, `Sadness`, `Surprise`, `Anger`, `Bored`, `Skeptical`
and the shared ones. The T-046 channel table (`content/emotions/face_motion.json`, engine content, not in this
write-set) already resolves browUp, browSad, eyeWide, eyeSquint, jawOpen, mouthUp and mouthDown to these names. The
per-side and pout controls need new channel candidates there (follow-up for the engine owner).

## Evidence (21 + 3 stills: Cycles 24 samples + OIDN, shared calibration)

- Turnaround, reference vs render: [strip](turnaround_strip.png), [front](turn_val27_front.png),
  [3/4](turn_val27_threequarter_right.png), [side](turn_val27_side_right.png), [back](turn_val27_back.png),
  [back 3/4](turn_val27_back_threequarter.png)
- Face close-up next to char_C (front) and #28 r1c1 (3/4): [face_closeup.png](face_closeup.png)
- Expression set (neutral, happy, sad, surprised, angry, bored) next to #28 tiles: [expressions.png](expressions.png).
  The "REF Bored" tile is #28 r3c3 ("Colfited"/unimpressed).
- Regenerate: `python3 docs/evaluation/characters/T-058/make_sheets.py <fidelity run> <face dir> <expression dir> <out>`.

Render budget used: 24.

| Use | Stills |
| --- | ---: |
| Iterations (front + 3/4, three times) | 6 |
| Face iterations | 3 |
| Final 5-view turnaround | 5 |
| Final face, front | 1 |
| Expression set | 6 |
| Angry/Sad/Bored again after raising the brow travel | 3 |

The final turnaround and the Neutral/Happy/Surprise tiles come from the build before the brow-travel change. That
change affects only expression keys, not the rest pose.

## What matches the references

- **Identity cue: heavy lids.** The upper lid crosses the iris at about its middle and the lid line is nearly
  straight, front and 3/4 (char_C, #28 r1c1). The small sulky pout is the neutral mouth.
- **Happy** (closed lid arcs, small closed smile) and **Surprised** (round open eyes, small "o") read like #08/#28.
- **Bored** stays subtle (heavier lids, a slightly crooked mouth), as the owner decision of 2026-11-17 asks.
- **Hoodie:**
  - Loose mustard fleece; the hood rim forms a V at the chest with two cream drawstrings.
  - Kangaroo pocket with an edge; ribbed hem and cuffs; sleeves to the wrist.
  - Shoulders are covered when the arms hang (dropped shoulder).
  - The overall silhouette (front figure IoU 0.89) is similar to the reference.
- Dark joggers to the shoes, yellow shoes with cream soles. Proportions are unchanged from T-039.

## Remaining differences (honest list)

1. **Brow acting is mostly hidden by the pinned 1.x fringe.** The brow keys move 7–11 mm (measured), but the v6
   fringe covers the brow band. Angry and Sad therefore read much weaker than #28: there the fringe is shorter, the
   brows are short thick strokes, and they angle strongly. This needs hair v3 (T-044), or brows placed lower after
   the hair changes.
2. **Lid shells read as pale domes** around the eyes, especially in Happy and Bored. The reference has only a soft
   crease. This is a property of `face_generic/1`'s lid shells and lid material (the girl has it too).
3. **Face shape is longer and narrower** than char_C's round, wide face with full cheeks. The head and jaw come from
   T-039's body. The neck shows more than in the reference in close-ups.
4. **Underarm gap:** a small skin gap remains at the underarm (front and back 3/4 views).
5. **Hood:**
   - From the back, the hood bag is flatter and smaller than the reference's large hood (#08 back views). Not
     re-rendered after the change, to stay within budget.
   - The pocket is less pronounced than the reference's.
6. **Fleece look:** the hoodie fibres look sparkly orange; the reference fleece is matte mustard. Material tuning
   needs `presets.json` (T-044 holds it).
7. **Shoes are round blobs** (body_generic's ellipsoid foot). The reference has low chunky sneakers with a cream toe
   cap, laces and a white stripe.
8. **Missing:** the backpack (no shared backpack accessory), hands in the pockets (pose), and the hair silhouette
   (the 1.x clump hair is a rounder helmet than the reference's spiky felt locks; hair v3 will address it).

**Missing materials** (list only; `presets.json` not edited): "suede" (shoes), "rib knit" (cuffs, hem), "cord"
(drawstrings), "rubber/cream sole".

## Checks

- `pipeline/charsys/tests/test_boy2_face.py --blender`: **11/11 PASS**. Covers every control present, L + R = full
  (error < 1e-6), BrowDown.L leaving the right brow untouched, MouthPout forward, and the heavy rest lid.
- `pipeline/charsys/tests/test_hoodie.py --blender`: **28/28 PASS**. Covers validation (bad values rejected), every
  part present with a material, bag on the back, pocket and cords in front, sleeves to the wrists, shoulders covered.
- Full gate `python3 tools/check_all.py --base origin/main` after `git merge origin/staging` (merge `6d56f08`):

  | Check | Result |
  | --- | --- |
  | Frozen assets | PASS |
  | Shared-systems lint | PASS |
  | C++ build, CTest, plush_tests | PASS |
  | Python tests | PASS |
  | Documentation links | PASS |
  | Blender tier (run with `--blender`) | PASS: boy 1.x fidelity 64.07 (−0.42 vs baseline), girl 65.48 (+0.07); verify_charsys, determinism (boy and girl), export_engine 13/13, face, groom, hair, garment tests |
  | Guarded paths | **needs Supervisor approval**: `test_boy2_face.py` and `test_hoodie.py` (new; in the write-set) and `test_versions.py` (base-spec fix, Part 1). Every test file is guarded, and only a Supervisor commit trailer `Supervisor-Approved: <path>` clears them |

  Environment notes:
  - The first run failed the C++ tier only because this container lacked embree, glm, nlohmann-json, glfw and GLEW.
    These were installed with apt.
  - With OIDN missing, the two engine image regressions (`regression_milestone01`, `regression_face_neutral`, RMSE
    0.041 > 0.030) failed identically on unmodified `origin/main`.
  - With the official OIDN 2.3.3 Linux binaries on `CMAKE_PREFIX_PATH` (CI gets OIDN from vcpkg), CTest passes.
  - The Blender tier passed in the `--blender` run. The run with OIDN omitted `--blender` and reports "Blender
    executable not found" for that line only.

Blender: bpy 5.3.0 wheel (Python 3.13 venv) through `tools/bpy_blender.py`.
