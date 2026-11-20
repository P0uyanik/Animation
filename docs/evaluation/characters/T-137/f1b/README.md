# T-137 F1b: third girl, rounder eyes, lower fringe, closed-eye lash curve

Overrides only, on `spec/candidates/T-126a/...` + the T-126 overrides (written by `make_overrides.py`):
- `girl_white_hair_blue_dress.eyes.override.json`: level eyes, no inner skin wedge, centred lid arch,
  iris 0.462 r, and the opt-in `lids.closed_fit.lash_curve`.
- `girl_white_hair_blue_dress.fringe.override.json`: fringe line 13 deg lower, more even, softer taper
  (fringe + keep-out only; no groom_r5 change).

Shared option (`pipeline/charsys/face_v3/lids.py`, `curve_closed_lash`): with `closed_fit.lash_curve`
set, the closed eye keeps a dark lash curve at the lid seam instead of hiding the lash under the lower
lid. Per key factor: Blink sags (downward curve), Laugh -1.0 arches up, Squint 0 is straight.
Not set = code path not entered.

Default builds unchanged: `../checks/` mesh hashes of the default 0.13.0 auburn girl, input commit
37901c4 vs final lids.py: 207/207 objects identical (file sha 4e6d984b...). Note: the build itself is
not fully repeatable on this machine. In 9 runs, 2 of 4 at the input commit and 2 of 5 with the change
matched exactly; the others differed in 1-3 of ear.L, ear.R, lid_upper.L/R, at the input commit too
(`..._run_b5_differs.json`). So the hash shows equality on matching runs, not on every run.

Tests: `pipeline/charsys/tests/test_face_r5.py` 14/14.

Evidence (T-126 base vs candidate vs refs 01/04/14):
- `strict.jpg`; `eyes_100.jpg` 100% eye crops front and 3/4; `expressions.jpg` (Blink, LeftEyeClosed,
  Laugh, Squint show the lash curve)
- `pupils.csv` pupil px per eye: 160/32 -> 150/30 (medium / wide)

T-150 targets used as a guide. Hand estimate from the front crop, per eye (L = R):
opening H/W ~0.74 (target 0.952 +-0.075, out; base ~0.55), iris D/W ~0.58 (0.751, out),
D/spacing ~0.30 (0.356, out), iris x from outer ~0.52 (0.619, out), white above ~0.03 (0.038, in).

Open issues:
- Opening still wider than the references; iris could go larger with a rounder socket.
- Thin lower-lid rim line under the eye; closed lids show a skin dome and a fold at the outer corner
  (both already in the base).
- Sadness reads as half-closed with a dark lid line (the lash follows the lid).
- The fringe is lower but still chunkier than the references.
