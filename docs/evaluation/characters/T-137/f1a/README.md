# T-137 F1a: auburn girl, eyes through the glasses

Override only, on 0.13.0: `girl_auburn_bun_glasses.eyes.override.json` (`face.eyes` only).

What changed: eyes level (yaw 0), socket carved so no skin wedge covers the inner upper eye, upper lid a
centred arch, larger iris (0.47 r), thin white above. Lash is now a brown band and the lower strands are
removed (separable: drop the `lash` block to keep the 0.13.0 lash).

Evidence (0.13.0 vs candidate vs ref_30, G01, G02):
- `strict.jpg` strict sheet; `eyes_100.jpg` 100% eye crops, front and 3/4, through the glasses
- `expressions.jpg` expression sheet (candidate)
- `pupils.csv` readability.py pupil px per eye: 160/32 -> 152/32 (medium / wide)

T-150 targets were used as a guide, not a requirement. Hand estimate from the front crop, per eye
(L = R, symmetric build):

| measure | target | candidate |
|---|---|---|
| opening H/W | 0.948 +-0.073 | ~0.73 (out, base ~0.55) |
| iris D/W | 0.742 +-0.045 | ~0.64 (out) |
| iris D/spacing | 0.369 +-0.018 | ~0.34 (just out) |
| iris x from outer | 0.623 +-0.038 | ~0.55 (out) |
| white above | 0.056 +-0.041 | ~0.02 (in) |
| white inner / outer | 0 +-0.042 / 0.248 +-0.044 | ~0.13 (out) / ~0.22 (in) |

Open issues:
- Opening is still wider than the references; rounder needs a head-socket change beyond an override.
- A thin lower-lid rim shows under the eye (build report lid_lower exposed 0.111, base 0.0).
- Closed eyes (Blink, Laugh, Squint) are a bare skin dome, as in 0.13.0; the F1b lash curve is not enabled here.

Rebuild: `build_character.py -- --spec <0.13.0 spec> --out <dir> --no-glb --no-compare --override <this override>`;
sheets: `python3 ../tools/face_sheets.py part.json strict|eyes|expr|pupils --out <dir>`.
