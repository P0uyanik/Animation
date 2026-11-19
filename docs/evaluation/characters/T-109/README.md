# T-109: face round 4 (lower face, girl lens shelf, mouth)

Implementer report data for T-109 (round 3). Input SHA `46a923f` (`integration/t-094d`, boy 2.1.0 / girl 0.12.0
current); branch `t-109-claude-face-r4`. Blender for everything here: the **bpy 5.3.0 module** (Python 3.13) behind
`tools/bpy_blender.py` (no Blender binary in the cloud container). Engine bake: `plush-render` built here
(cmake + ninja, Release, no renderer feature). Geometry, eyes and mouth only: no material, shader or fibre change
(T-110 owns the skin surface).

## Owner evidence
| | boy (2.1.0 vs T-109) | girl (0.12.0 vs T-109) |
|---|---|---|
| strict sheet (T-087 recipe, Cycles 16 spp) | [boy_2.1.0_vs_face4_strict.jpg](boy_sheet/boy_2.1.0_vs_face4_strict.jpg) | [girl_0.12.0_vs_face4_strict.jpg](girl_sheet/girl_0.12.0_vs_face4_strict.jpg) |
| recipe | [boy_2.1.0_vs_face4.recipe.json](boy_2.1.0_vs_face4.recipe.json) | [girl_0.12.0_vs_face4.recipe.json](girl_0.12.0_vs_face4.recipe.json) |
| cheap preview (Cycles 2 spp; not for approval) | [boy_preview.jpg](boy_sheet/boy_2.1.0_vs_face4_preview.jpg) | [girl_preview.jpg](girl_sheet/girl_0.12.0_vs_face4_preview.jpg) |
| face crops (Cycles 16 spp; head, no fur) | [boy_face_crops.jpg](crops/boy_face_crops.jpg) | [girl_face_crops.jpg](crops/girl_face_crops.jpg), lens region [girl_lens_shelf.jpg](crops/girl_lens_shelf.jpg) |
| e908 acting frame (candidate cast, Cycles 16 spp) | [boy_e908_f080.jpg](acting/boy_e908_f080.jpg) | [girl_e908_f110.jpg](acting/girl_e908_f110.jpg) |

- Sheet columns: original reference | current approved | T-109 candidate | AI target. Girl: A-pose master (sheet30 is an
  A-pose turnaround, as T-081/T-094); boy: arms-down compare variant (as T-094).
- Face crops: [face_probe.py](face_probe.py) (T-087 light rig, 70 mm, 6 deg elevation, one camera per view for all
  columns), columns current | T-109 | T-109 with the new preset (girl SmileOpen, boy Pout).
- Acting frames: `run_shot.py --blend-only` on scratch copies of `episodes/e908_*_acting/shots/s010` whose cast is the
  T-109 candidate (`{"spec", "overrides"}`), then [acting_face.py](acting_face.py) renders the baked frame (the shot's
  own lights) through a face camera. Left: as played; right: girl with the frame's baked `Smile` weight (0.9, the
  girl_delighted beat) moved to `SmileOpen`; boy with `Pout` 1.0 added on the late-interest beat (EyeWide 0.42,
  MouthO 0.1). The emotion files still call `smile` (content/emotions is not in this write-set; T-113 extends the set).

## What changed
### Code (all opt-in; absent = unchanged)
- `pipeline/charsys/face_v3/lower_face.py` (new): `face.shape.lower_face`, applied right after `face.shape`:
  - `cheek_pad_m` (+ `_radius_m`, `_x`, `_below_eye_m`, `_height`, `_forward`, `_top_below_eye_m`): low cheek pads,
    outward from the head axis. Nothing moves above `cheek_pad_top_below_eye_m`, so eyes, lids and socket keep their
    skin.
  - `jaw_round_m` (+ `jaw_below_eye_m`, `jaw_band_m`, `jaw_x`, `jaw_down`): fills the jaw's front corners.
  - Only skin in front of the head's depth centre moves.
- `face_v3/lids.py` + `face_v3/socket.py`: `eyes.lids.lower_fit = {"gap": g}`. The girl's grey shelf came from her oval
  eye (scale 1.03 / 0.8 / 1.0). face_generic/2 builds every lid at the eye's **global** gaze envelope: the largest
  radius the rigidly turned oval eyeball reaches in any direction, 1.08 → lid gap 0.09 r. That maximum comes from the
  eye corners. Below the eye it put the lower lid shell, and the socket skin over it, about 4 mm proud of the flattened
  eyeball, which read as a pale/grey shelf under the lenses.
  - `lower_fit` computes the envelope **per direction** (the same 11 × 7 gaze grid) and pulls the lower lid shell in to
    `r (envelope(u) + gap)`, keeping its thickness.
  - The socket skin's cover radius over the lower lid is capped the same way.
  - Nothing is pushed out; the upper lid is unchanged.
- `face_library/expressions.json`: optional presets **SmileOpen**:
  - MouthWide 0.8, MouthO 0.35, MouthSmile 0.6, JawOpen 0.25, EyeSquint 0.2, CheekRaise 0.6.
  - The open D smile of ref_30: narrower and taller than the library Smile.
- `face_library/expressions.json`: optional presets **Pout**:
  - MouthPout 1, MouthFrown 0.35, MouthO 0.15, BrowDown 0.25.
  - The boy's closed sulky pout.
- Both presets have engine names `smileOpen` / `pout`. They are built only when a spec lists them in
  `face.expressions.optional`; units a face lacks are skipped.

### Candidates (spec data; no published file or spec changed; no version bump)
- `assets/characters/boy_yellow_hoodie/spec/candidates/T-109/boy_face4.override.json` on 2.1.0:
  - lower face: cheek pads 16 mm (radius 70 mm, x 1.3 × eye x, 35 mm below the eye line); jaw 6 mm;
  - the existing face_generic/2 outline superellipse 0.6 / 2.4 gives the U-shaped lower outline of hero24;
  - rest pout rounder (MouthFrown 0.45, MouthPout 0.55 → 1.0, MouthO 0.1);
  - `Pout` listed.
  - Tried: pads at the mouth line with jaw 8–14 mm and `jaw_down` 0.5. The lower face went boxy, with a crease along
    the jaw in 3/4.
- `assets/characters/girl_auburn_bun_glasses/spec/candidates/T-109/girl_face4.override.json` on 0.12.0:
  - lower face: cheek pads 14 mm, jaw 10 mm; her outline options stay as 0.12.0;
  - `lower_fit` gap 0.005. Tried 0.02: the dark line went, but a pale band stayed (exposure 0.28);
  - closed rest smile a little fuller (MouthSmile 0.35 → 0.5, CheekRaise 0.8 → 0.9). The owner's neutral is a
    closed soft smile, so the open smile stays an acting beat;
  - `SmileOpen` listed.
- T-115: the adjustable lower-face, eye-opening and lid-profile parameters, with the current values and tried ranges,
  are in [fit_parameters.json](fit_parameters.json).

## Measurements (build reports; test_face_v4 on the sheet's candidate masters, [log](test_face_v4.log))
| | current | T-109 | limit |
|---|---|---|---|
| girl lower-lid shell exposed (front ray test, `lid_shell_exposed`) | 0.509 | **0.048** (0.0 before the rest-smile change) | ≤ 0.05 |
| 3/4 socket rim, girl / boy | 8.3 % / 8.8 % | 8.3 % / 8.8 % | 10 % |
| cheek / eye-corner fold, girl (deg) | (T-089b 14.2 / 35.8) | 15.5 / 35.6 | 45 / 40.33 |
| cheek / eye-corner fold, boy (deg) | (T-089b 12.2 / 59.5) | 11.7 / 55.1 | 45 / 157.7 |
| full blink residue front / 3/4 | closes | closes (no eye over the limit) | girl 29.1, boy 2 mm² |
| lid line at 15 deg glance (lash area glance / rest), girl L / R | – | 1.08 / 0.70 | ≥ 0.5 |
| lower-face surface moved out (95th pct, 3–12 cm below the eye line, 15–80 deg off forward), boy / girl | – | **16.6 / 17.9 mm** | ≥ 3 mm |
| face surface above the eyes (> 1.2 eye radii), boy / girl | – | 0.000 / 0.001 mm | ≤ 0.5 mm |
| eye centres, eyeball scale, brow bounds vs the published master, boy / girl | – | 0.006 / 0.000 mm | ≤ 0.5 mm |

Lens region ([girl_lens_shelf.jpg](crops/girl_lens_shelf.jpg)):
- **Before.** 0.12.0 shows a pale ledge with a dark lower line about 4 mm below the eye white, inside each lens.
- **After.** In the candidate the eye white meets the skin directly. Below it there is a soft, rounded fullness: the
  lifted cheek of the rest smile and the fuller lower face. There is no lid ledge and no line.
- **3/4.** The pale arc across the cheek is the lens rim's refraction. It is unchanged (open point 5).

## Default output unchanged
- **Method.** The published specs (boy 2.1.0, girl 0.12.0) were built twice:
  - before any code change (input SHA);
  - with the T-109 code.
- **Reports.** `build_report.json` differs only in the cloth-simulation timing fields (`seconds`).
  `components.json`, `animation_compat.json` and `spec.resolved.json` are identical.
- **Geometry.** [mesh_hash.py](mesh_hash.py) hashes every mesh's vertex set and every shape key. The T-109 rebuild
  matches the pre-change build except `lid_upper.L` (both) and `ear.L` (girl). Those objects differ just as much
  between the pre-change build and the **published** masters (girl `lid_upper.L`; boy `ear.R`).
- **Conclusion.** This is the existing run-to-run noise T-089b also saw, not this change.

## Tests
- `python3 pipeline/charsys/tests/test_face_v4.py --blender <bpy wrapper> --unit --boy <candidate master> --girl <candidate master>`
  → **55/55 PASS** (new; it reuses every test_face_v3 unit and build check and T-089b's lid-line-at-glance check, with
  the same limits). Run on the 0.12.0 default build instead, the new checks fail as they should (no options, shelf
  0.509).
- `test_face_v3.py` (plain) 7/7, `test_face_v3b.py` (plain) 10/10, `pipeline/charsys/tests/test_versions.py` 105/105.
- Not run: ctest and the engine image regressions (no engine file touched; `plush-render` was only built to bake the
  e908 frames); `verify_charsys.py` (legacy boy path, untouched); `tools/fidelity` scores (the owner decides on the
  strict sheet; T-115 runs the fit tool).

## Open points
1. **Closed lids in acting (pre-existing, both published versions).** In Smile, Laugh and the boy's Smile the
   blinked or squinted upper lids show as pale domes over the eyes (probe renders). The lid shell rotates down at its
   envelope radius. This is not changed here (lid closure is beyond this task's lid-profile scope); it is worth its
   own task.
2. **Girl lower-lid exposure 0.048 against the 0.05 bound.** The fuller rest smile lifts the lower lids with the
   cheeks. Without the rest change it was 0.0. A larger `lower_fit` gap or the old rest mix gives more margin.
3. **The emotion library still plays `smile`.** The e908 girl_delighted beat uses the library Smile. Switching it to
   `smileOpen` is a content/emotions change (T-113).
4. **Boy jaw mostly hidden in the strict sheet.** The hoodie collar covers it. The face crops and the acting frame show
   the lower face better.
5. **Glasses lens edge.** The pale ridge across the girl's cheek in 3/4 is the lens rim's refraction (`glasses_lens`).
   It is unchanged, and it is a material/accessory matter.
