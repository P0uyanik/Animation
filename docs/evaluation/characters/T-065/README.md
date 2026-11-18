# T-065: face v2 — `face_generic/2` (opt-in)

Branch `t-065-claude-face-v2` (from `origin/staging`, staging merged in before the report). Path B: the candidates below
are **evidence for the owner's visual review only**. No character spec, preset or hair file was changed; nothing is
published, promoted or pinned.

Blender used: the bpy **5.3.0** module (Python 3.13) behind a `blender` wrapper (no Blender binary in the container).
Renders: Cycles CPU, 16 spp + OIDN, 384 px, orthographic face framing, shared calibration `character_neutral/1`.

## Result in one look

**Final owner sheets.** Each sheet shows face v2 on the fitted head (`body_generic/2`). Columns: reference | current approved version | candidate, front then 3/4. All are in `head_v2/`, as JPEG ≤ 2048 px.

![overview](head_v2/overview_owner_sheet.jpg)

- Per character:
  - [boy](head_v2/boy_owner_sheet.jpg). Current = published 1.1.0, rendered here with the same framing and light. The published master was not changed; I checked its checksum.
  - [girl](head_v2/girl_owner_sheet.jpg). Current = 0.10.0, using T-055's stills: same calibration, slightly different framing.
  - [third character](head_v2/third_owner_sheet.jpg). Head-only test; she has no approved version yet.
- Outline overlays and landmark errors: see "Criterion 0" below.

**Remaining differences (honest list, visual first):**
1. **Skin colour** (T-066).
   - The boy's skin is tan; the reference is porcelain peach.
   - The girl's and the third character's skin is greyish pink.
2. **Hair** (T-044). The boy's is a clump helmet, the girl's are tubular ringlets, and the third character has none in this test.
3. **Lower lid.** A faint pink line shows under the iris on the girl and the third character. It is weaker than before.
4. **Third character.**
   - A faint horizontal shading band on her lower face.
   - The socket edge still reads slightly at the outer corner in 3/4.
5. **Boy.**
   - In Happy, a faint ring of the closed shell.
   - The 3/4 cheeks are still less full than #28.
6. **Girl.**
   - The neck is long (body data, T-059).
   - Her Angry brows are weaker than ref_34.
7. **Expressions on the old head.** The Sad, Surprised, Angry and Bored stills in the AC 1–7 expression sheets below are on the previous head.
8. **Side profile below the eyes.** It differs by cheek volume; only the chin set-back is fitted (see Criterion 0).

The sheets below are the AC 1–7 evidence on the previous head.

Sheets (reference row on top, candidate below):

- Boy front / 3/4: [boy_face_vs_reference.png](boy_face_vs_reference.png). Panels: char_C | current 2.0-dev (`face_generic/1`) | v2 candidate | #28 r1c1 | v2 3/4.
- Boy expressions (#28 tiles, 3/4 at 25°): [boy_expressions.png](boy_expressions.png). Shows Neutral, Happy, Sad, Surprised, Angry, Bored/sleepy.
- Girl front / 3/4: [girl_face_vs_reference.png](girl_face_vs_reference.png).
- Girl expressions (ref_34 matrix): [girl_expressions.png](girl_expressions.png). Shows Neutral, Happy, Sad, Surprised, Angry.
- Third character front / 3/4: [third_face_vs_reference.png](third_face_vs_reference.png).
- Third character expressions: [third_expressions.png](third_expressions.png). These are **workbench geometry previews, not Cycles** (render budget, see below). They show Neutral soft smile, Happy, Sad, Surprised, Angry, Sleepy and the parted-lips rest.

Single stills are in `renders/<who>/<Preset>_<yaw>.png`.

![boy expressions](boy_expressions.png)
![girl expressions](girl_expressions.png)
![third expressions](third_expressions.png)

## What face_generic/2 does (code: `pipeline/charsys/face_generic.py` `build_v2`, `pipeline/charsys/face_features.py` "face_generic/2")

A spec opts in with `generators.face = "face_generic/2"` (and `face.generator` the same). `face_generic/1` is untouched:
`build()` hands a v2-pinned spec to `build_v2` before any v1 code runs. Every v1 helper `build_v2` reuses is called
unchanged, and v2 only adds new functions. So every existing character builds byte-identically (see Gate).

1. **Lids blended into the skin** (`face.eyes.socket`, AC 1).
   - The head mesh is refined around each eye: a smooth subdivision, so the original vertices do not move.
   - In each eye's frame, the skin wraps the lid shells:
     - inside the opening, skin in front of the eyeball moves behind it;
     - from each lid edge, for `band_deg` / `lower_band_deg`, the skin stays behind the shell. That band is the visible lid with its lash line;
     - over `ramp_deg` the skin then rises to just outside the shell (`clearance_m`). Where it crosses the shell is the soft crease;
     - beyond that it is a smooth maximum of the face and the shell, so it only rises where the shell would show, then blends back to the face.
   - Upper and lower profiles blend smoothly at the eye corners. Beyond `corner_deg` the skin only covers the shells.
   - A light Laplacian pass smooths the covered skin.
   - The lids keep the face skin material.
   - Blink, squint and the smile's lower-lid lift slide the lid out from under the crease, as real lids do, so the skin stays put.
   - EyeWide retracts the lid under the crease, so the socket skin rotates with it. This is a head shape key `EyeWide` with weights over the eye's width.
   - The lower lids ride on the cheek skin: the head's `MouthSmile`/`CheekRaise` displacement is copied onto the lower-lid shells.
   - Diagnostic in the build report, `lid_shell_exposed`: the share of each shell visible from the front.
     - Upper shells: 2–4 % (only the band shows).
     - Lower: 1–18 %. That is the band plus the inner surface of large lower lids.
2. **Round, full-cheeked faces** (`face.shape`, AC 2).
   - `outline_roundness`/`outline_exponent`/`outline_top_below_eye_m`: the front-view lower outline moves towards a superellipse.
   - `face_width_m`.
   - `lower_face_length_m`: stretch or shorten eye→chin. The neck below fades.
   - `lower_face_recede_m`: side profile, the face curves back towards the chin.
   - `cheek_fullness_m` (+ v1 `cheek_roundness_m`): bulge along smooth radial directions. v1's normal brush left bumps on the girl's coarse cheek; v2 does not use it.
   - `jaw_depth_roundness`.
   - v1 chin/forehead options still apply.
   - New action unit **`CheekRaise`** (`face.cheeks`).
   - New rest shapes in `face.mouth.rest_shape`:
     - **`soft_smile`**: MouthSmile 0.35 + CheekRaise 0.6 by default. It is the closed gentle smile with cheek lift (owner decision);
     - **`parted`**: the third character while watching.
   - `rest_mix` is honoured for every rest shape. This fixes T-055 limitation 1.
   - `MouthSmile`, `MouthFrown` and `CheekRaise` keep their absolute targets over a baked rest, so Frown and Sadness are not weakened.
   - The smile coupling's hard front cut-off on the head is tapered (no step on the cheeks).
3. **Brows** (`face.brows.shape`, AC 3).
   - Presets: `flat_stroke` (boy), `soft_arch` (girl), `short_arc` (third). The spec's own values override the preset.
   - Soft strokes tapered at both ends with round caps.
   - Acting keys as v1 plus `brow_sad_outer`.
   - Visibility under the fringe is spec data (`height`). For the boy it is now 0.72 r, just under the fringe tips, so Sad and Angry read.
4. **Eyes** (AC 4).
   - Size, spacing and height come from the existing spec keys.
   - v2 is tested with the third character's 46 mm wide-set eyes (centres 134 mm apart) and flattened eyeballs (`scale` y 0.78–0.8). The gaze envelope is honoured.
   - Iris per spec: boy dark brown, girl brown, third blue (checked).
5. **Mouth** (AC 5).
   - `face.mouth.fullness` {upper, lower, forward_m, lower_forward}: fuller, pillowed lips. The outer edge stays on the skin, and all keys keep their relative motion.
   - Boy: small pout as before (`rest_shape: pout`).
   - Girl: wider fuller soft smile.
   - Third: `parted`.
6. **Compatibility** (AC 7).
   - Same rig controls and engine expression map as v1 (T-046 face layer).
   - T-058 per-side units and MouthPout unchanged (`split` runs after the v2 steps). The boy candidate has all of them.

## Candidates (spec data in this folder; not character spec versions)

`candidates/*.override.json` are applied on top of the current specs by `build_candidate.py`. This driver registers
`face_generic/2` in-process. The registry line belongs in `pipeline/charsys/versions.py`, which is outside this task's
write-set (see "Needed from the Supervisor").

| Candidate | Base | Main face values |
| --- | --- | --- |
| Boy 2.0-dev + face v2 | `boy_yellow_hoodie.2.0.0-dev.spec.json` | round outline (exp 2.3), lower face +12 mm, recede 16 mm, cheeks 11 mm; eyes flattened 0.8, protrusion 0, lower lid −34°; socket band 9°/6°; brows `flat_stroke` at 0.72 r; skin occlusion lift 0.35 / bleed 0.2 (was 1.6 / 0.72: creases glowed white) |
| Girl next + face v2 | girl spec + 0.10.0 override | outline 0.6, cheeks 15 mm, recede 10 mm; eyes flattened 0.8, protrusion 4 mm (was 13.2); brows `soft_arch`, lighter; `soft_smile` with CheekRaise; lips wider (19 mm half width) and fuller (upper ×1.3, lower ×1.6) |
| Third character head-only test | girl body, no hair, no glasses | pale skin (248, 218, 204); blue iris; eyes r 46 mm, 134 mm apart, 16 mm lower; `short_arc` brows; tiny mouth, `soft_smile` rest; variant `third_headonly_parted_face2.override.json` = `parted` rest |

The face-shape values in the table are the ones the AC 1–7 Cycles stills were rendered with. The candidate files now hold the criterion-0 version: the `body_generic/2` head outline, no face-level outline, length, recede or jaw options, and reduced cheek fullness (boy 6 mm, girl 3 mm + the inherited 7 mm, third 4 mm + 7 mm).

Rebuild:

```text
blender -b --factory-startup -P docs/evaluation/characters/T-065/build_candidate.py -- --spec <spec> [--override <0.10.0>] --override docs/evaluation/characters/T-065/candidates/<candidate>.json --out <dir> --no-glb --no-compare
```

Render:

```text
blender -b --factory-startup -P docs/evaluation/characters/T-065/render_face.py -- <master> <out> --shots "Neutral@0,Neutral@30,Smile@25"
```

Sheets:

```text
python3 docs/evaluation/characters/T-065/make_sheets.py docs/evaluation/characters/T-065/renders docs/evaluation/characters/T-065 [<baseline dir>]
```

## Judged against the references (visual first)

**Closer than before [J]:**
- **Lids.** The pale shell domes and goggles are gone on all three. The upper lid reads as a skin band with the lash line and a soft crease above. Happy and Blink close with skin, not black arcs on pale domes.
- **Boy.**
  - The lower face is a round U, as in char_C and the #08 bald head. The chin is softer and the boxy jaw corners are gone.
  - The neck under the chin is now hidden.
  - Brows are visible, so Sad and Angry read as in #28. Bored keeps the heavy lid.
- **Girl.** No grey goggle shading inside the glasses. Soft arched light brows. A closed gentle smile with lifted cheeks and fuller lips.
- **Third character.** Big blue wide-set eyes set into a round full-cheeked face, a tiny nose and a tiny soft-smile mouth. This is recognisably the "14" face construction.

**Remaining differences (honest list):**
1. **Skin colour/material.** Not this task (T-066).
   - The boy is still brown/olive instead of porcelain-peach.
   - The girl's skin is pale grey-pink.
   - I only lowered the candidates' occlusion lift/bleed, because the felt "crease glow" made the new creases bright.
2. **Lower lid band.** On the girl and the third character it reads as a thin bright pink/white line under the iris. The reference has a soft shadowed lower lid. Cause: the lid shell's rim and the lower band catch light. Lowering `lower_band_deg` or a darker lid rim material would help; not tuned within budget.
3. **Third character's upper lid** sits high (40°), so white shows above the iris. In "14" the lid touches the iris top: `upper_edge_deg` about 25–30°. Spec data, not tuned within budget.
4. **Boy Happy:** the closed eyes show as arcs at the outer half plus a faint ring of the closed shell. In #28 they are thin even arcs.
5. **Boy face shape.**
   - The 3/4 cheek is still flatter than #28. #28 has more cheek volume below the eyes.
   - The head stays wide and the forehead high: the body loft, not this task.
   - The ears sit high.
6. **Girl.**
   - The cheek shape is close, but the head and neck proportions (long neck, narrow chin) are body data (T-059).
   - Happy is still the library open smile, smaller than ref_30.
   - Angry brows are not as strongly furrowed as ref_34 "Anger" (needs a larger `brow_down_m` in her spec).
7. **Surprise (EyeWide)** stretches the socket skin. A slight fold shows at the inner corner on the boy (30° lid travel).
8. **Brows behind the fringe** are placement only. A fringe keep-out above the brows belongs to hair v3 (T-044).
9. **Fidelity scores were not run** (judgement first, per the owner). T-064 owns the fidelity tool fixes.

## Criterion 0 (scope extension): head geometry fitted to the references — `body_generic/2`

The owner's request about chin, jawline and face shape arrived as a Supervisor message after my first READY. I
verified it in `docs/tasks/T-065.md` on staging and did it on the same branch.

### Head version

- **Code:** `pipeline/charsys/body_generic.py`, `fit_head_outline`. It declares `body_generic/2`.
- **Opt-in:** the new spec data `body.params.head.outline`. A head without `outline` builds exactly as before (byte-identical).
- **What it does to the head primitive, before the body remesh:**
  1. Scales the lower head vertically so the chin sits `chin_t` eye spacings below the eye line.
  2. Scales every horizontal slice of the lower face to the reference's front half width. With `front_eye_width`, widths are relative to the reference face width at the eye line, so the cranium keeps its width.
  3. Fits the side profile below mid-face, relative to mid-face (how far the chin sits back from the mouth and cheeks).
- Above mid-face the reference silhouette is cheek volume and the eye. Forcing the face front to it made a muzzle, so the cheeks come from the face options instead.
- The remesh then smooths the whole head. The ellipsoid head gets a denser mesh (96×64) when fitted, and the neck tube narrows inside the fitted head so it cannot show through the receded jaw.
- **Outline data:** `head_outlines.json`, read by hand on 2–6× gridded zooms of the reference views. This is the repository's landmark method; automatic skin segmentation was tried and was unreliable (blush, glasses, ears).
  - Boy: val27_front / val27_side_right.
  - Girl: sheet30_front / sheet30_left. Her cheeks are partly behind hair and her side profile behind the glasses: ±2 px.
  - Third: uploads 01 / 15.

### Candidates and tools

- The candidates pin `body_generic/2`; their face-level outline options were removed (the head now carries the shape).
- Cheek volume was reduced, because it stacked on the fitted head and made a crease.
- Tools:
  - `outline_measure.py`: the built head's outline, in the reference's units;
  - `outline_sheets.py`: overlays and error table.

### Evidence (`head_v2/`)

Outline overlays: green = the reference outline, blue = before (current version), red = after.

![boy](head_v2/boy_outline_overlay.png)
![girl](head_v2/girl_outline_overlay.png)
![third](head_v2/third_outline_overlay.png)

Landmark errors in eye-spacing units (`head_v2/outline_errors.md`):

| Character | Version | chin depth | front outline (mean abs) | side outline (mean abs) | cheek width | jaw width |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| boy | before | +0.005 | 0.093 | 0.075 | +0.077 | +0.104 |
| boy | after | +0.000 | 0.031 | 0.068 | +0.011 | +0.013 |
| girl | before | −0.035 | 0.143 | 0.415 | +0.048 | +0.212 |
| girl | after | +0.030 | 0.087 | 0.279 | +0.017 | +0.010 |
| third | before (face v2 test, v1 head) | −0.240 | 0.089 | 0.390 | −0.084 | — |
| third | after | −0.005 | 0.010 | 0.257 | −0.020 | +0.005 |

**What I see [J]:**
- **Boy.** The lower outline now follows char_C's round U into a small soft chin, and the neck is hidden.
- **Girl.** The long jaw that sloped into the neck (her "before" side profile had no chin) becomes a short round lower face with a small chin.
- **Third character.** The flat-bottomed lower face becomes the round full face of "14".

**Limits:**
- **Side error stays 0.26–0.28 for the girl and the third character, by design.** This measure compares the silhouette, and the reference silhouette below the eyes is the cheeks. I fit only the chin set-back to it, so the remaining difference is cheek volume.
- The chin underside is flatter than the reference.
- A faint horizontal shading band remains on the third character's lower face in the geometry previews.

### Geometry previews (workbench, not Cycles)

`head_v2/<who>_head_v2_geometry.png`: front, 3/4 and side, face parts only.

### Final Cycles sheets on the fitted head

Approved by the Supervisor: up to 12 extra stills; 9 were used. Each character has front Neutral, 3/4 Neutral and
Happy. The sheets are in `head_v2/` and the stills in `head_v2/renders/`.

![boy](head_v2/boy_final_face_vs_reference.png)
![girl](head_v2/girl_final_face_vs_reference.png)
![third](head_v2/third_final_face_vs_reference.png)

Lid fixes in the same round (spec data only):
- girl and third character: `lower_band_deg` 2.5 (was 5) and `corner_deg` 50;
- third character: `upper_edge_deg` 28 (was 40). Her upper lid now meets the iris top, as in "14".

**What I see [J]:**
- **All three:** round lower faces with short soft jaws and small chins, matching the reference outlines.
- **Girl:** her chin no longer melts into the neck.
- **Third character:** the round full face of "14".

**Remaining:**
- A faint pink line still shows under the iris on the girl and the third character. It is weaker than before.
- A faint horizontal shading band on the third character's lower face.
- In the boy's Happy, the closed lid still shows a faint ring.
- The skin colour belongs to T-066.
- The boy's Sad/Surprised/Angry/Bored and the girl's Sad/Surprised/Angry stills in the AC 1–7 sheets above are from the previous head. They were not re-rendered: the extra budget went to front, 3/4 and Happy.

Cycles total: 24 (AC 1–7) + 9 candidate + 2 current boy 1.1.0 (criterion 0) = 35. The original budget was 24, plus 12 approved by the Supervisor.

## Tests

- `python3 pipeline/charsys/tests/test_face_v2.py --blender <bpy wrapper> --boy/--girl/--third <masters>`: **40/40 PASS**
  on the final candidates (`body_generic/2` head and face v2). This adds the `body_generic/2` checks: declaration, outline fit on a
  synthetic head (chin depth, widths, cranium unchanged), and the candidates pinned to it.
  - Unit checks:
    - pin dispatch;
    - declaration;
    - brow presets;
    - rest shapes;
    - released-key bake semantics;
    - v1 build source reaches no v2 code.
  - Build checks per candidate:
    - generator /2;
    - upper shells ≤ 8 % visible;
    - no warnings;
    - EyeWide socket key;
    - T-046/T-058 controls and the engine expression map;
    - CheekRaise;
    - soft-smile corner lift 3.1–3.5 mm;
    - third: no eye overlap, blue iris.
- Gate (GitHub "Quality gate" run 44205655505 on `2e2ea3c`, criterion 0 included, after `git merge origin/staging`; same result as run 44195415311 on `2315636`): Frozen assets, Write-set
  (35 paths, all in the claim), Shared-systems lint, C++ build, C++ tests, Python tests and links, Blender tier (full;
  regression + unchanged-character guard jobs for boy, girl, third character: all PASS) **PASS**. **FAIL only:** Guarded
  paths, `pipeline/charsys/tests/test_face_v2.py` (new test, needs Supervisor approval), and the derived "Merge status"
  line that follows from it. Locally (bpy wrapper) the same, plus C++ build (embree not installed in this container) and
  `OWNERSHIP.md parses` (the staging claims table had no rows at that moment); `test_export_engine` passed after fixing
  the local wrapper to print `SystemExit` messages.

## Render budget (24 Cycles stills, all used)

| Stills | Purpose |
| ---: | --- |
| 1 | boy 2.0-dev baseline (the "current version" panel) |
| 4 | first Cycles check of the boy's blended lids |
| 1 | third character close-up: checking a workbench artefact |
| 7 | boy final: front, 3/4, Happy, Sad, Surprised, Angry, Bored |
| 3 | girl, **discarded** (built with a refinement bug, since fixed) |
| 6 | girl final: front, 3/4, Happy, Sad, Surprised, Angry |
| 2 | third character final: front, 3/4 |

- Workbench (OpenGL, geometry only, no Cycles) previews were used for iteration and for the third character's expression sheet.
- The boy's 7 final stills come from the build just before two fixes: refinement without the whole-mesh relax, and the socket smoothing pass. The final code's boy face surface differs from it by at most 0.43 mm (p99 0.21 mm, under 1 px at this framing). Measured by nearest-surface distance over 26 k face vertices.
- Not rendered in Cycles:
  - girl bored/sleepy;
  - the third character's expression set (workbench only).

## Needed from the Supervisor / other tasks

- **`pipeline/charsys/versions.py`**: append `_r("face", "face_generic", 2, "face_generic")` and `_r("body", "body_generic", 2, "body_generic")`.
- **`pipeline/charsys/build_character.py`**: add `"body_generic/2": main_generic` to the build-path table. This is outside the claim; the candidate driver patches it in-process.
- **About 9 more Cycles stills**, to re-render the owner sheets on the fitted head. This is outside the write-set; `build_candidate.py` and the test register it in-process meanwhile.
- **Character spec versions** for an owner-approved pin bump (path B). The candidate overrides here are the data to start from.
- **T-044 (hair)**: a fringe keep-out above the brows, so brow acting stays visible.
- **T-066 (skin)**: a skin preset that keeps creases warm but not glowing. The candidates turn the felt occlusion lift/bleed down.
- No `presets.json` change is needed for face v2.
