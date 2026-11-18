# T-066: skin look round (`presets/2` skin family), all characters

Implementer: Claude (cloud) · lane D · path B · branch `t-066-claude-skin` (from `origin/staging`).
Blender: **bpy 5.3.0 module** (Python 3.13 venv) through `tools/bpy_blender.py`; no Blender binary in the container.

## 1. Objective
A shared, opt-in skin preset family that reads like the references' porcelain-peach felt skin (warm blush, soft
flocked matte surface, gentle rim sheen, warm creases that never glow), shown as candidates on both characters
while the approved versions stay unchanged.

## 2. Result
**Complete, path B (candidates only).** One limitation for the owner/Supervisor (§8.1): the boy builds on the frozen
legacy path, which does not read `materials.assignments.skin`. His candidate is therefore produced by applying the
same shared builder call to his built master after the build (evaluation script). Opting him in for real needs a
small hook outside this task's write-set.

## 3. Files changed
| Path | Purpose |
| --- | --- |
| `pipeline/charsys/materials/skin_presets.json` | NEW: `plush-studio.material-presets/2`, family `presets/2`, kind skin; self-contained defaults; preset `skin-felt/2` |
| `pipeline/charsys/materials/builder.py` | skin-family loader/validator (`load_skin_library`, `validate_skin_library`), id routing (`is_skin_preset`, `library_for`), `resolve_preset`/`validate_assignments`/`apply_preset` accept skin ids, new `_skin_layer` (emission off, warm SSS radius, crease warmth, flock speckle) |
| `pipeline/charsys/materials/render_swatches.py` | `--presets` may name presets/2 skin ids (default list unchanged: presets/1 only) |
| `pipeline/charsys/materials/measure_swatches.py` | targets looked up in the preset's own library |
| `pipeline/charsys/tests/test_skin_presets.py` | NEW plain-Python tests (24 checks) |
| `pipeline/charsys/tests/test_skin_material.py` | NEW Blender graph tests (10 checks) |
| `docs/evaluation/characters/T-066/candidates/*.skin2.override.json` | candidate overrides: girl 0.10.0 + skin, boy 1.1.0 + skin |
| `docs/evaluation/characters/T-066/apply_skin_candidate.py` | evaluation: apply the candidate skin to a legacy-path master |
| `docs/evaluation/characters/T-066/make_sheet.py` | evaluation: reference / current / candidate sheets |

Documentation / evidence: this README, `girl_skin_review.jpg`, `boy_skin_review.jpg`, `swatch_sheet.jpg`,
`swatches.json`, `swatch_metrics.json`. `presets.json` (claimed by T-070) is **not** touched.

## 4. What was implemented
**Opt-in by preset id.** `skin_presets.json` is a separate library with its own defaults (it does not inherit from
`presets.json`, so T-070's or any later edit of presets/1 cannot change a presets/2 skin). `builder.library_for(id)`
returns presets.json whenever it holds the id, otherwise the skin family; skin ids may never reuse a presets/1 id
(validator). Every presets/1 id therefore resolves byte-for-byte as before (tested), and a spec only gets the new
skin by naming `skin-felt/2` in `materials.assignments.<slot>.preset`.

**`skin-felt/2` look** (all values are data in `skin_presets.json`):
- matte: roughness 0.74, specular 0.24 (presets/1 `skin-felt`: 0.32 / 0.5, the glossy forehead highlight);
- soft subsurface 0.5, scale 0.05 x reference, warm red-led radius (1.0, 0.5, 0.32);
- flocked surface: fine fibre bump (220/reference), micro relief (120/reference) and a new very fine flock albedo
  speckle (700/reference, +-3.5 %), warm-tinted sheen (0.5, tint 0.45) and a gentle silhouette rim (0.55);
- **no glowing creases**: the family is non-emissive by rule (`skin.emission` must be false; the validator rejects
  true). `_skin_layer` disconnects and zeroes any emission feeding the skin, e.g. the face graph's felt "light bleed"
  that made creases glow (T-063 §P2). Creases instead get a short-range (0.04 x reference) AO **multiply** towards a
  warm tint (240, 186, 168) at strength 0.22: warmer and slightly deeper, never lighter than the skin around them.

**Per-character data (candidate overrides, not shared code):**
- girl: skin + face colour porcelain-peach (238, 202, 184) (was 202, 176, 169); `face.skin.occlusion.bleed` 0 (the
  emission), lift 1.1 to (248, 210, 190) as an albedo-only warm lift; blush (238, 122, 118), softness 0.85, radius
  45 mm, 8 mm lower and 6 mm further out so it shows below the glasses rims as in ref_30/ref_34, nose 0.7.
- boy: skin (236, 190, 166) (legacy albedo 181, 107, 70 read as tan, far from the porcelain upload 01), blush
  (226, 128, 112) in the existing legacy blush graph; applied to `M_skin` (head, neck, hands, lids) and `M_ear`.

Decision/assumption: "benchmark light" = the shared `character_neutral/1` calibration (the T-019 swatch light).

## 5. Tests executed
| Command | Result |
| --- | --- |
| `python3 pipeline/charsys/tests/test_skin_presets.py` | **PASS 24/24** (library valid; ids disjoint; presets/1 resolution identical; non-emissive, matte, SSS, rim, warm crease tint; validator rejects emission/loud flock/id clash; approved versions name no presets/2 id; candidates opt in and validate) |
| `blender -b --factory-startup -P pipeline/charsys/tests/test_skin_material.py` | **PASS 10/10** (presets/1 graph gets no skin node or family tag; emission removed and 0; blush graph stays the root of the albedo chain; crease + flock present; warm SSS; no node stacking on re-apply) |
| `python3 pipeline/charsys/tests/test_material_presets.py` | **ALL PASS 54/54** (unchanged presets/1 suite) |
| swatch render + `measure_swatches.py` (`--presets skin-felt,skin-felt/2 --lighting character_neutral/1 --samples 16`) | skin-felt/2: fuzz 0.34 (target 0-3) PASS, saturation retention 104.5 % PASS, **sheen P90/P50 1.003 FAIL** (target 1.12-1.32); presets/1 skin-felt under the same light: 1.007, also FAIL (see §8) |
| `python3 tools/check_all.py --base origin/staging --task T-066 --blender <bpy wrapper>` | see §5.1 |

The new test files are not yet wired into `tools/check_all.py` (outside the write-set); the Supervisor may add them.

### 5.1 Gate
`python3 tools/check_all.py --base origin/staging --task T-066 --artifacts-dir <tmp> --blender <bpy wrapper>`
(full tier, 24 min, this container):

| Check | Result |
| --- | --- |
| Frozen assets | PASS |
| Guarded paths | FAIL: **needs Supervisor approval** of the new files `pipeline/charsys/materials/skin_presets.json`, `pipeline/charsys/tests/test_skin_material.py`, `pipeline/charsys/tests/test_skin_presets.py` (new files in guarded areas; all are in T-066's claimed write-set) |
| Write-set | PASS (15 paths, all inside the claim) |
| Shared-systems lint | PASS |
| C++ build / C++ tests | FAIL **environment**: CMake cannot find `embree` 4 in this container, so nothing C++ was built or run. T-066 changes no C++ file; GitHub CI on the branch is the evidence. |
| Python tests and links | PASS |
| Blender tier | girl_auburn_bun_glasses **PASS** (unchanged-character guard: fingerprint, export, renders; fidelity 64.40 = baseline); girl_white_hair_blue_dress PASS (not buildable, skipped by design); boy_yellow_hoodie **FAIL on engine export only** (`character.json` digest 78a885ab... vs golden 6430c025...); fingerprint byte-equal, renders identical, fidelity 66.41 = baseline. |

**The boy export failure is pre-existing, not T-066:** `tools/regression/run.py --character boy_yellow_hoodie` run
from a clean `origin/staging` worktree (902867b) in the same container gives the **same** digest 78a885ab... and
the same FAIL. The boy's legacy build never enters the material builder (his materials are byte-identical, §6).
Likely the stored boy golden (T-041) predates a later export or environment change; for the Supervisor to check
against CI on staging.

## 6. Baselines: approved versions unchanged
- Girl 0.10.0 built with the staging code (before any T-066 edit) and with the T-066 code: material node-graph
  digest of all **79 materials identical**, `fingerprint_v2` **identical**. Boy 1.1.0 likewise: **17 materials
  identical**, fingerprint identical (the legacy path never enters the builder for skin).
- No file under `assets/`, no spec, no frozen file, no baseline and `presets.json` changed (diff list in §3).
- `test_skin_presets.py` guards it going forward: the approved versions of `fidelity_baseline.json` must name no
  presets/2 id.

## 7. Visual results (18 Cycles stills, budget 24)
`girl_skin_review.jpg`, `boy_skin_review.jpg`: per character front + 3/4 face close-ups, reference | current
(approved) | candidate, 640 px, 32 spp, OIDN, `character_neutral/1`. `swatch_sheet.jpg`: skin-felt vs skin-felt/2.
Stills used: girl current front + 3/4 (+1 3/4 at the wrong yaw, unused), girl candidate iterations 3 fronts +
final front/3/4, boy current 2 + re-framed 2, boy candidate 2, swatches 2.

What changed (candidate vs current):
- **Girl**: the glossy forehead hot-spot and the glowing patches under the glasses and on the chin are gone; the skin
  is matte, porcelain-peach; rosy cheeks now show below the rims and the nose is pink, as in ref_30/ref_34.
- **Boy**: tan, slightly glossy skin becomes porcelain-peach and matte with a soft rosy blush, much closer to upload
  01 (face close-up) and canon29.
- Unchanged: geometry, face shapes, eyes, brows, hair, clothes, lighting, camera.

Remaining differences (honest):
- Girl: without the emissive bleed the lower face (chin, under the nose) is darker than before and than the
  references, which are lit with a much softer frontal fill. A non-glowing fix is lighting (the shared calibration,
  not this task) or more SSS; I did not push it further to keep within budget.
- The flocked fuzz is very fine: visible only as a faint matte grain at 640 px (the reference shows a velvety micro
  fuzz). The skin fuzz ceiling (< 3/255) limits how far it can go.
- Boy: ears read slightly more yellow/cream than the face (thin-shell SSS); the reference ears are pinker. The
  reference skin is also a touch pinker overall. Both are colour data in his candidate override.
- Girl 3/4 crop: the fixed close-up camera puts the face right of centre (same framing for current and candidate).

## 8. Problems, limitations, open questions
1. **Boy opt-in path (needs a decision/follow-up):** `build_character.main_legacy` (body_v6/1) builds `M_skin` in
   `body_v6.make_materials` and ignores `materials.assignments`. A real boy pin-bump needs either a small legacy hook
   ("apply `materials.assignments.skin` to `M_skin`/`M_ear` after `make_materials`", as `apply_skin_candidate.py`
   does) in `build_character.py`, or the boy on the generic path (Boy 2.0). Both are outside T-066's write-set.
2. **Version registry:** `versions.py` (outside the write-set) registers only `presets/1`. The family is tagged
   `presets/2` in the file and on built materials (`ps_material_family`), but a spec cannot pin
   `generators.materials: presets/2` yet; opt-in is by preset id as the task specifies. Registering `presets/2`
   belongs with the first pin-bump.
3. **Sheen metric:** `sheen_p90_p50` fails for both skin presets under `character_neutral/1` (1.003-1.007 vs
   1.12-1.32; the presets/1 skin-felt targets were set under the harness light). I did not loosen the target; the
   visual read (matte with a soft rim) follows the references, which have no sharp sheen on skin.
4. The girl's candidate also changes face data (blush placement, occlusion lift): skin-look data, but the owner
   should confirm the blush position.

## 9. Commits
Branch `t-066-claude-skin`: 177d932 (preset family, builder, tests, overrides), 1738225 (tuning, swatch tools, evidence), f5409ab (merge origin/staging 902867b), plus the report commit (see RELAY_LOG line).

## 10. Resource use
Token usage: not available. Repeated work: one girl 3/4 still rendered at the mirrored yaw (unused), boy current
re-rendered once for framing; three girl front iterations.

## Reproduction
```sh
B=<blender or tools/bpy_blender.py wrapper>; W=<scratch>
G=assets/characters/girl_auburn_bun_glasses/spec; T=docs/evaluation/characters/T-066
$B -b --factory-startup -P pipeline/charsys/build_character.py -- --spec $G/girl_auburn_bun_glasses.spec.json \
  --override $G/girl_auburn_bun_glasses.0.10.0.override.json --override $T/candidates/girl_auburn_bun_glasses.skin2.override.json \
  --out $W/girl_c --no-glb --no-compare
# boy: build 1.1.0 as usual, then
$B -b --factory-startup -P $T/apply_skin_candidate.py -- $W/boy/boy_yellow_hoodie_master.blend \
  $T/candidates/boy_yellow_hoodie.skin2.override.json $W/boy_c.blend
# close-ups (empty index {"views":[]}); girl centre z 0.83 width 0.34, boy z 0.80 width 0.36
$B -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- <master> $W/empty.json $W/r --height 640 \
  --samples 32 --closeup 'front:0:0:0,0,0.83:0.34' --closeup 'q34:-35:0:0,0,0.83:0.34'
$B -b --factory-startup -P pipeline/charsys/materials/render_swatches.py -- --out $W/swatch_sheet.png \
  --metadata $W/swatches.json --width 480 --height 576 --samples 16 --lighting character_neutral/1 --presets skin-felt,skin-felt/2
$B -b --factory-startup -P pipeline/charsys/materials/measure_swatches.py -- --image $W/swatch_sheet.png \
  --metadata $W/swatches.json --out $W/swatch_metrics.json
python3 $T/make_sheet.py <out.jpg> <title> "<label>|<ref>|<x0,y0,x1,y1>|<current.png>|<candidate.png>" ...
```
