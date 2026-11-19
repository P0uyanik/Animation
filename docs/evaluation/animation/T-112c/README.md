# T-112c evidence: hand shapes from the T-051 table, box-face grasps, the pass receiver's band

Input `ae9be36` (`integration/t-051`), branch `t-112c-claude-verb-hands`, merged with `origin/integration/r3-promote`
(`82b6d4d`, the T-110 back-out: Blender material code and docs only, no engine, test or content file) before READY.
Task: `docs/tasks/T-112c.md`. Supervisor decisions (2026-11-19): Q1 (a), Q2, Q3 (all below).

## 1. What was built
| Criterion | Implementation | Test (`tests/test_verbs.cpp`) |
| --- | --- | --- |
| 1 table | `interaction.cpp`: the inline `handShapePoses` (T-112b) is gone. A grasp's non-wrap `shape` is looked up in the hand-shape table (`findHandShapeDir(scene path)` + `loadHandShapeTable`, once per compile, `InteractionContext::handShapes`). `reachTo` keys the shape's `approach` on the way in and its `pose` at contact with T-051's `keyHandShape` (`hand.<s>`, `.index`, `.f<k>`, `.thumb`, `.stagger` where the shape sets them); the release keys pose → approach → relaxed (extra per-finger tracks back to the relaxed hand). The shape's `search`: `none` = as posed, `pinch` = index + thumb search on a sphere of `pinch_radius` just inside the socket, the other fingers keyed free. `wrap` keeps `kOpen` and today's search (the table's wrap is the same values). A name that is not a `grasp` shape of the table is an error. | "the table's grasp shapes against T-112b's inline values; wrap is kOpen"; "a grasp keys the hand shape of the table found above the scene" (a temp content tree with a changed palm); T-112b "non-wrap hand shapes key their open / closed poses" (pinch expectations now the table's, Q2) |
| 2 graspFace | The verb expander sets `"graspFace": true` on a site grasp of a box prop (box primitive or box collision proxy) under the finger gate (as the band: a profile, or `"fingers": true`). `reachTo`: when the socket is on a box face (`GraspShape::face`), `wrap`, `pinch` and `palm` key the T-051 face search: `.grasp` (mid-plane point), `.graspRadius` (half thickness), `.graspAxis` 0, `.graspFace` (inward normal, hand rest frame, Step), `.grasp.weight` 0 → 1 over the last 4 f and back to 0 over 5 f on release (`Hold::faceGrasp`). `hook` and `cradle` stay as posed. | "box-face sites key hand.<s>.graspFace - per-finger palm grasp on the felt tray, boy and girl"; T-112b "two-handed tray" (assertion replaced, Q1) |
| 2b receiver band (Q3) | `pass` under the finger gate writes the receiver site's band / thumb / box face into the handover (`toBand`, `toThumb`, `toGraspFace`); the handover's receiver `reachTo` uses them as its `GraspStyle`. Authored handovers have none of these keys and are unchanged. | "a pass gives the receiver its site's finger band (gated like the giver's)" |
| 3 s010_verbs | no scene change: the verbs now key both bands (section 3) | measures, preview, strict sheet |
| 4 golden | unchanged | `golden: interaction scenes bake byte-identically` |
| 5 tests | 4 new cases, 2 T-112b cases changed with Supervisor approval (section 2), nothing loosened | full suite |

## 2. Differences from T-112b's inline values (criterion 1) and changed assertions
| shape | approach | pose | search | same as inline? |
| --- | --- | --- | --- | --- |
| `palm` | 0.08, 0.3, 0 | 0.15, 0.35, 0 | none | identical (bit-identical floats; test) |
| `hook` | 0.2, 0.1, 0 | 0.7, 0.1, 0 | none | identical |
| `cradle` | 0.1, 0.25, 0.2 | 0.3, 0.25, 0.2 | none | identical |
| `wrap` | 0.03, 0.05, 0.35 | same | all | identical (`kOpen` and today's search; the code path is unchanged) |
| `pinch` | 0.1, 0.2, 0.1, index 0.1 | **0.6, 0.2, 0.1, index 0.1** | **pinch, 1 cm** | **differs**: inline held pose thumb 0.5, index 0.35, no search. The table (T-051, design 2.3) is the single source: the held pose is where the index + thumb search starts, the other three fingers are keyed free (`.f0`-`.f2` = 0.6, 0.1, free). |

The `.f<k>` / `.thumb` / `.index` tracks a table shape keys also get a key at the reach start (the relaxed hand) and at
the end of the release, so the hand is the same before and after the grasp.

Changed assertions (Supervisor-approved):
- T-112b "non-wrap hand shapes": pinch expects the table's pose (0.6, 0.2, 0.1), index 0.1, and its contact search
  (radius 0.01, axis 0, weight 0 → 1 → 0, `.f0`-`.f2` free, no `.f3`), instead of the inline pose and "no `.grasp`".
  palm, hook and cradle keep "no `.grasp`", with the same values.
- T-112b "two-handed tray": "no `.grasp` track" is replaced by stricter checks per hand from its contact to the place
  contact: `.graspFace` = the face's inward normal (≤ 0.001), every fingertip within 2 mm of the face, none inside
  the box, hand bone and palm contact bit-identical to the same scene with `"fingers": false` (where there is still no
  `.grasp` / `.graspFace` track), the search released after the place contact. All earlier checks of that case
  (contacts, palm on socket, arm gap, tilt, place) are unchanged and give the same numbers as T-112b.

## 3. e907 s010_verbs (criterion 3)
Current cast via `run_shot --stages prepare,bake` (cast `current` → boy 2.0.0, girl **0.12.0**: the version
`docs/evaluation/characters/fidelity_baseline.json` names at this SHA). Measured with T-051's `measure_t051`
(`docs/evaluation/animation/T-051/measure_t051.cpp`, built against this branch's libraries) on the resolved scene, and
on the same scene with `"fingers": false` on the three verbs (= the single contact search). Boy R `grip`, band
45-90 mm, f30-f76 (contact → release); girl L `grip_b`, band 10-55 mm, f58-f129 (contact → end). "closed" = from
contact + 4 f. Files: `measure_s010_verbs.json`, `measure_s010_verbs_fingers_false.json`, `summarise_measures.py`.

| Hand (closed frames) | | worst tip-skin gap | deepest tip / knuckle centre vs surface | furthest outside the band | thumb (< 0 = opposed half) | wrist / palm vs fingers false |
| --- | --- | --- | --- | --- | --- | --- |
| boy R (f34-f76) | single search | 19.34 mm | -8.18 mm (inside) | 29.95 mm | +2.5 mm | |
| | T-112c verbs | **0.00 mm** | +11.15 mm | 3.83 mm (T-051 §7.1) | **-19.5 mm** | **0.000000 mm** |
| girl L (f62-f129) | single search | 13.62 mm | -7.02 mm (inside) | 10.80 mm | +5.8 mm | |
| | T-112c verbs | **0.00 mm** | +6.60 mm | inside (6.27 mm margin) | **-24.3 mm** | **0.000000 mm** |

Closest boy-girl digit points over the shared hold (f58-f76), minus both skin radii: 62.7 mm (single search 56.5 mm).
These are T-051's numbers on s010 + hand-keyed bands, now produced by the verbs. At the input SHA only the boy had his
band: the pass receiver's grasp had none, so the girl stayed on the single search (13.62 mm gap, a fingertip 7.02 mm
inside the cup). Q3 fixed that.

Bake (`plush.shot_bake/1`, sha256): input engine `f836c49f`, T-112c `bfe1c7d6`. The only difference is the girl's
left-hand finger bones (`f0a`-`f3b.L`, `thumbA/B.L` and the four `DEF-f_*.03.L`) on f45-f129 (her reach start → end).
Every other bone of both characters, the cup and all other frames are byte-identical. Expected (Q3).

## 4. Baselines (criterion 4)
- `tests/golden/interaction_hashes.json` unchanged; the golden case passes. It bakes e907 `s010` and
  `s010_calibrated`, the eval exchange / handover scenes, e901, e905 and the test_interaction scenes, so the
  s010_calibrated bake is unchanged too. Non-verb grasps never carry `shape` / `graspFace` / `toBand`, so they take
  the unchanged code paths (the inline values are not consulted for wrap).
- T-112a / T-112b legacy key-for-key tests (no profile) pass unchanged: no profile → no band, no `graspFace`, no
  `toBand` (gated).
- Unchanged: `engine/anim/**`, `content/hand_shapes/**`, `content/assets/**`, `engine/render/**`, published versions,
  frozen files, `episodes/e907_exchange/shots/s010_verbs/shot.scene.json`.

## 4b. Commands run (after the r3-promote merge unless noted)
| Command | Result |
| --- | --- |
| `cmake --build build` (Release, PLUSH_BUILD_STUDIO=OFF, renderer OFF) | builds, no warnings in the changed files |
| `build/tests/plush_tests` | **205 / 205** cases (201 at the input + 4 new), 765998 assertions; golden unchanged |
| `tools/check_all.py --base origin/integration/r3-promote --task T-112c --blender <bpy 5.3 wrapper>` | Frozen PASS, Write-set PASS (13 paths, all in the claim), lint PASS, C++ build / tests PASS (renderer tests skipped, renderer OFF), Python tests and links PASS, Blender tier: regression boy (fidelity 67.73), girl (65.01) and white-haired girl PASS. `deform_test` boy / girl failed only because the runner had no libEGL ("Couldn't open libEGL.so.1"). After `apt-get install libegl1`, the same two commands pass (rc 0, missing [], unmeasured {}). Guarded paths: `tests/test_verbs.cpp` needs the `Supervisor-Approved:` trailer at merge (expected). |
| `run_shot --stages prepare,bake` / `--blend-only` on s010_verbs (this branch and, as `--bake-engine`, the input SHA's `plush-render`) | pass, no verb constraint error |
| `build/measure_t051` + `summarise_measures.py` | section 3 |

Blender: no binary on this runner, so the bpy 5.3.0 module ran through `tools/bpy_blender.py`.

## 5. Visual results
| File | Content |
| --- | --- |
| `t112c_s010_verbs_preview_cycles8spp.jpg` | cheap preview: T-112c, f66 (mid shared hold), Cycles 8 spp, 240x180, the three T-051 close-up views (front: boy's right hand; back: girl's left hand; top) |
| `t112c_s010_verbs_hands_strict_sheet.jpg` | strict sheet (`make_sheet_t112c.py`, T-051 layout and `render_close.py`), Cycles 32 spp, 480x360, identical cameras / lights / samples per row: reference crops (T-053a) / input `ae9be36` / T-112c |

Both blends were built by `run_shot --blend-only` (bpy 5.3.0 module through `tools/bpy_blender.py`), the input one
with the input SHA's `plush-render` as `--bake-engine`. They were rendered before the r3-promote merge, so both
columns carry T-110's felt surface material. The merge removes it from this branch, but it changes no bake or
geometry.
What changed (girl only, as the bake diff says):
- back view: her left fingers curl round the cup as separate, closer curls. At the input they stand straighter
  and spread, with the top finger raised off the wall.
- top view: at the input a white fingertip of hers shows through the rim inside the cup (the -7.02 mm penetration of
  section 3). In T-112c it is gone, and the hand lies outside the wall.
What stayed identical: front view (the boy's hand, pixel-for-pixel by eye; his bones are byte-identical in the bake),
wrists, arms, the cup, both bodies, camera and lights. Deviation from the references is as T-051 §8: the hand meshes
are mitten-like, so separate fingertips do not read as clearly as in the PB key frames.

## 6. Not verified
- `pinch` on a real small prop (no small-prop scene; the keys and the search setup are tested, not the look).
- A box-face grasp in a rendered shot (the tray is tested in the engine only; no tray shot exists).
- The pass receiver with a box prop (`toGraspFace` is written and read, no scene uses it).
- Windows / clang toolchains (golden hashes are the linux gcc-13 set).
