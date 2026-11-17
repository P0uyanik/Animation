# T-039: Boy 2.0 part 1 — body and proportions

Status: **development evidence; unpublished and unapproved.** Body only: no face, hair, garments, accessories or fur.
The frozen 1.0.0 and 1.1.0 specs and assets are untouched. Codex started this task (WIP `6f2b09f`). Claude resumed
it: merged `integration/consolidated`, then fitted the proportions in head units and gathered the evidence below.

## What changed

- `assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json`: a body-only `body_generic/1`
  spec. Its head uses an asymmetric profile loft (Codex). In this pass, the shoulders, arms, hands, hips/legs, feet,
  neck, torso depth, crown, jaw and the comparison arm pose were fitted to the reference in head units (table below).
- `pipeline/charsys/body_generic.py` (shared). Every addition is opt-in, and its default is the previous behaviour:
  - `head.profile_levels` (+ `profile_exponent`, `profile_segments`, `profile_steps`; Codex): an asymmetric head
    loft. If it is absent, the ellipsoid head is used as before. During the merge, this was combined with
    `integration/consolidated`'s optional face-shape options (`lower_half_height`, `lower_roundness`,
    `lower_depth_roundness`, `neck.top_radius`). Both are kept: the loft replaces the ellipsoid only when
    `profile_levels` is set.
  - The profile rows are resampled with a Catmull-Rom curve before the loft (`_dense_profile`). The shared
    `geom.interp_profile` smoothsteps between keys, which terraced the head into visible horizontal bands in Codex's
    renders. This path runs only when `profile_levels` is set, and only this 2.0.0-dev spec sets it.
  - `leg.ankle_x`: the feet are set wider than the hips (A-stance). The knee follows linearly, and the foot joints sit
    under the ankle. Default is `hip_x`, giving the same vertical legs as before (bit-identical arithmetic).

## Proportions in head units (the fitting target)

1 HU = chin to the top of the **bare** skull. In the reference, the skull is hidden under the hair, so its top comes
from the bare-skull fraction 0.314 of body height (Codex's 0.300–0.320 target, from the side silhouette and the
eye/brow/ear landmarks). The render HU is the projected `LM_chin` to the top of the silhouette. Landmarks are the T-032
annotations and the fidelity tool's render landmarks. Values are from the front view (`val27_front`); the ratio is
render / reference.

| measure (HU) | reference | before (Codex WIP) | after (final) | after ratio |
|---|---:|---:|---:|---:|
| chin → shoulder joints | 0.246 | 0.181 | 0.248 | 1.01 |
| shoulder width (joint to joint) | 0.677 | 0.612 | 0.672 | 0.99 |
| arm, shoulder → palm centre | 0.906 | 0.915 | 0.895 | 0.99 |
| palm centre above sole | 1.046 | 1.068 | 1.033 | 0.99 |
| palm half-spread from the midline | 0.492 | 0.361 | 0.514 | 1.04 |
| foot half-spread (shoe/foot centres) | 0.262 | 0.172 | 0.234 | 0.90 |
| figure height | 3.185 | 3.162 | 3.159 | 0.99 |

The three-quarter view (`val27_threequarter_right`) agrees within about 10%: arm 0.92, shoulder width 0.90, palm
spread 0.94, feet 0.88. The camera yaw there is an estimate, and the shoulder/palm points are read through the hoodie
(±4 px ≈ ±0.025 HU), so the front view is the deciding one. All values, both views, are in
[fidelity_proportions.json](fidelity_proportions.json).

## Fidelity tool proportions (relative to figure height), for continuity with T-032

`tools/fidelity/run.py` divides by the figure height. In the reference, that height **includes the hair** (about 8% of
the bare height; ~12% on the bigger back-view silhouette). The body-only render has none, so every body ratio reads
too long or wide by about that much even when the body matches in head units. These numbers are reported but were not
used as targets.

| proportion (median of views) | frozen 1.1.0 | Codex WIP | final |
|---|---:|---:|---:|
| arm length / height | -20.3% | +10.7% | +8.4% (front +8.4, side +5.6, 3/4 +5.4) |
| shoulder width / height | +0.1% | -2.3% | +7.0% (front +8.9, 3/4 -1.1, back +14.5) |
| figure width / height | — | -11.7% | -2.4% |
| leg gap / height, front | -35.7%* | +31.5% | +21.3% |
| leg gap / height, back | — | +11.2% | +3.8% |
| head (chin→top) / height | +2.0% (with hair) | -13.7% | -13.6% (bare skull vs hair-inclusive: expected) |

\* 1.1.0 value is the median over the views T-032 measured. The oblique leg-gap values (+3500%, +8100%) are excluded:
there the reference's loose trouser legs overlap and the centre column sees almost no gap.

## Visual evidence

Cycles at 640 px with the shared character-render calibration, 32 samples and OIDN (the fidelity render path,
`build/t039_it3`). Reference on the left, body render on the right:
[front](turnaround/val27_front.png) · [three-quarter right](turnaround/val27_threequarter_right.png) ·
[side right](turnaround/val27_side_right.png) · [back](turnaround/val27_back.png) ·
[back three-quarter](turnaround/val27_back_threequarter.png) · all five: [strip](turnaround/turnaround_strip.png).
Regenerate with `python3 docs/evaluation/characters/T-039/make_turnaround.py <fidelity run> <out dir>`.

## What matches

- The figure is about 3.2 bare heads tall. The shoulder line, shoulder width, arm length and hanging-hand position
  all match within about 1% in head units (front view). The hands hang at the hip as in the reference, slightly away
  from the body.
- Head: smooth and round with a domed crown. The face plane is flatter and the rear cranium fuller (side view). The
  jaw now carries forward to a broad, short chin like the reference's. The terracing from Codex's loft is gone.
- The torso has the depth of a soft child body; it was a plank in side view. The hips are lower, so the crotch sits
  closer to where the reference's trousers place it.
- The hands are mitten-sized: palm and fingers about 25% larger than the WIP.

## What deviates, and why

- **Foot spread 0.90 HU-ratio.** The reference marks the centres of chunky, out-turned shoes. A wider bare-foot stance
  would splay the legs further. The shared trouser generator still places leg columns at the hip x, so the A-stance is
  kept small (hip_x 0.064 → ankle_x 0.080). Revisit with the 2.0 shoes and trousers.
- **Leg gap +21% (front).** A bare crotch sits higher than the crotch of loose joggers. This is not an anatomy target.
- **Feet are rounded blobs** (body_generic's ellipsoid foot), sized to sit inside the shoes. The silhouette belongs
  to the shoes.
- **Neck visible.** The chin-to-shoulder distance matches, but the reference's hoodie collar hides the neck; the bare
  body shows it.
- **Skull height is an assumption** (0.314 of bare height). Every HU value scales with it. If the hair/face task
  finds a different skull top, the HU table should be recomputed; the spec is relative to height, not HU.
- **Skin colour, fuzz and the region scores** are not in scope: there are no face, hair or garments, and skin
  material is not part of this task.

## Checks (final state)

- `pipeline/charsys/verify_charsys.py`: **PASS** (legacy boy build-from-spec and v6 geometry fingerprint OK, asset
  store, reuse).
- `pipeline/charsys/tests/test_export_engine.py`: **ALL PASS (13/13)**, including "boy 1.0.0 master unchanged".
- `pipeline/charsys/tests/test_determinism.py --character all`: **PASS** for boy and girl at both 0.1 mm and 0.01 mm.
- Girl unchanged: girl built from `origin/integration/consolidated` and from this branch with `-t 1`
  (`PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`), then compared with `fingerprint_v2.py` at 0.01 mm. Result: **identical,
  72/72 objects**.

Iteration renders used: 3 (`build/t039_it1` = Codex WIP re-measured after the merge, `it2`, `it3` = final). Blender:
bpy 5.3.0 wheel in a Python 3.13 venv, through `tools/bpy_blender.py`.
