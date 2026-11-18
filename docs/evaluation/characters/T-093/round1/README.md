# T-093: garment outlines and accessories (garment/2), owner evidence

Branch `t-093-claude-garments`, input `4910b69`. Candidates are **unpublished**. Nothing here changes a published
version or a `*.spec.json`. Combining with T-092 and bumping versions is T-094.

## What to look at
| file | what it shows |
|---|---|
| `boy_2.0.0_vs_T-093/boy_2.0.0_vs_T-093_strict.jpg` | T-087 strict sheet: val27 reference \| 2.0.0 (current) \| 2.0.0 + garment/2 \| AI target (B09 front, B07 side, B06 back). Compare variant (arms down). |
| `girl_0.11.0_vs_T-093/girl_0.11.0_vs_T-093_strict.jpg` | T-087 strict sheet: sheet30 reference \| 0.11.0 (current) \| 0.11.0 + garment/2 \| AI target (G08 front, ref_41 garment sheet side/back, G04 face 3/4). A-pose masters on purpose: her references are an A-pose turnaround and her spec has no comparison pose (as in T-081/T-087). |
| `reach/reach_before_after.jpg`, `reach/reach.json` | Vest in the reach pose, side and 3/4 views, corrective keys muted (before) vs driven (after). Hair is hidden in these renders only. |
| `preview/*_preview.jpg` | The cheap first frames (recipe.py preview) that the sheets required. |
| `*.recipe.json` | The review recipes. `*/recipe.resolved.json` and `*/sheet.json` record the inputs, cameras and timings. |
| `make_overrides.py` | Writes the two candidate overrides from the published specs. Every value and the reference it was read from are listed there. |
| `reach_evidence.py` | Makes `reach/`. |
| `test_garments_v2.log` | Full run of `pipeline/charsys/tests/test_garments_v2.py` (57/57). |

## Changes per character (all values are my estimates, tuned by eye on diagnostic renders)
**Boy (2.0.0 + garment/2)**
- Inseam: the trouser gusset is shallower (depth 0.70 → 0.12), so the legs separate just below the hoodie hem, as in
  val27. Before, they were joined down to the knee. The gusset bottom rises from 0.150 m to 0.262 m. The body is unchanged.
- Trouser break: the hem settles on the shoe (flare, two soft slanted folds, front drop). Code: `hem_break`.
- Shoe volume: lower, slimmer upper (height 0.072 → 0.060 m, less width and length). The cream sole is kept. Two
  white felt side stripes run forward-up as in B09/B07. Code: `stripes`.
- Backpack (B06 canonical): rounded lid flap with a tab closure and loop, front pocket with its own flap, top grab
  loop, no zips. Navy felt. The bag is taller and boxier, with B07's depth. Code: `flap`, `tab`, `pocket_flap`.
- Drawstrings (B01/B02): plain felt cords with dark felt tips, instead of plastic tips.

**Girl (0.11.0 + garment/2)**
- Sleeve reach: sleeve_length 0.97 → 1.0 and a fuller puff.
- Rounded blouse collar: broader, flatter lobes with rounder tips (round collar parameters).
- Split bloomers: each leg's inner half is drawn to its own axis, but never past the measured inner thigh. A V crease
  opens at the front and back centre. The gap just above the hem goes from 0 to 1.35 cm. The gusset is shorter.
  Code: `leg_split`.
- Boot cuff: a turned-down cuff rolled over the shaft rim (G08 shape) replaces the thin garment/1 cuff tube.
  Code: `cuff_roll`.
- Hair accessories (groom/2 structure data only, no groom code): one pink felt flower instead of three, and a
  thicker blue-grey band at the bun base.
- Vest reach correctives: `corrective.reach.L/R` on every vest piece.

## Vest flare in reach (criterion 3)
Reach = FK upper arms rotated −75° about world X (forward). The metric is the distance of `garment.vest.main` to the
posed torso skin, in cm:

| pose | max | p99 | p95 |
|---|---|---|---|
| rest (A-pose) | 6.1 | 5.4 | 4.6 |
| reach, correctives muted (before) | **9.9** | **8.4** | 4.7 |
| reach, correctives driven (after) | **6.8** | **5.0** | 4.5 |

The keys read 0 at rest and with the arms down (the compare rotation, 35° about Y), and 1 in reach.
- **Improved:** the front panels no longer flap up over the shoulders (3/4 view).
- **Not fixed:** at this extreme reach the armhole area of the vest still tears, and the blouse shows skin at the
  armpit, in both states. That comes from the shoulder skinning, not the vest flare, and needs weight or rig work.

## Check that the published versions are unchanged
- No file of `pipeline/charsys/garments` (garment/1) or any published spec or version changed (git diff against
  `4910b69`, also checked in the test).
- A fresh build of the published boy 2.0.0 and girl 0.11.0 on this branch has the same format-2 fingerprint as the
  published masters (`fingerprint_v2.py`): 79 and 77 objects, 0 differences.
- The published boy clothing relabelled garment/2, with no new fields, builds exactly the garment/1 geometry
  (51 pieces, vertex hashes; test).

## Limitations and open points
- **Backpack `material`:** the bag's base colour is changed to navy (B06). This is the one garment `material` entry
  this task changes (preset and size unchanged). All other `material` entries are kept for T-092. T-094 combines them.
- **Boot cuff colour:** the cuff colour comes from a new `materials.cuff` part (cream `boot fleece`, the published
  boot preset). The cream fleece *material* belongs to T-092. If T-092 assigns the cuff, its value should replace this one.
- **Scrunchie:** it is still a smooth band. G04 shows a gathered scrunchie, and gathering would need groom code
  (hair is Phase D, T-091). Only structure data changed here (one flower, a thicker band).
- **Engine:** the reach correctives work in Blender renders. The engine export carries garment shape keys as
  morph targets, but nothing drives them in the engine yet.
- `pipeline/charsys/tools/garment_pose_eval.py` selects pieces by the `garment/1` tag, so it does not see garment/2
  pieces (read-only for this task).
- **Renders:** Blender 5.3.0 (bpy module wrapper), Cycles CPU at 16 spp, 360 px per tile. The boy sheet took about 6 min
  per column, the girl sheet about 9 min per column.
