# T-097A evidence: emotion blending

Input SHA 9807cdc. Blender: bpy 5.3.0 module (Python 3.13) behind a `blender` wrapper (only for `run_shot` prepare).

## Bake hashes before/after (AC3)
`plush-render --bake`, input-SHA build ("before") vs this branch ("after"), same prepared packages.
Every shot with emotion actions (none opts in to `blend`) and every standalone scene:

| Bake | sha256 (first 16) before | after | |
| --- | --- | --- | --- |
| e902_emotion_test/s010 (22 emotion actions) | 0da06ac629383b8b | 0da06ac629383b8b | identical |
| e903_test_video/s010 | 2a2717bfe681cced | 2a2717bfe681cced | identical |
| e904_secondary_motion/s010 | 742eed65d7ed8ab5 | 742eed65d7ed8ab5 | identical |
| e904_secondary_motion/s020 | 62119eaa00cc44cf | 62119eaa00cc44cf | identical |
| e905_props_test/s010 | a2a5dc43b803a6e2 | a2a5dc43b803a6e2 | identical |
| e907_exchange/s010 | 8588f191edb21fd8 | 8588f191edb21fd8 | identical |
| content/scenes/milestone01_classroom | 15d8861b6881 | 15d8861b6881 | identical |
| content/scenes/milestone02_classroom | 03c96799524a | 03c96799524a | identical |
| content/scenes/test_face | 98c1514c1b12 | 98c1514c1b12 | identical |
| content/scenes/test_lineup | 1cfcac390819 | 1cfcac390819 | identical |

No emotion file, clip or shot was changed.

## Transition curves (AC1, AC2)
`curves.svg` (from `curves.csv`, `plot_curves.py`): the same four actions (happy 10, surprised 18, sad 30, afraid 110)
on the girl test package, life off, sampled at quarter frames. Solid = blended state, dashed = plain T-003 crossfade.
Top: face morphs; bottom: head height. Regenerate with
`PLUSH_T097A_EVIDENCE=docs/evaluation/animation/T-097A build/tests/plush_tests -tc="*evidence*"` then the script.

Key numbers (tests/test_emotion_blend.cpp messages):
- Body: worst second difference at quarter frames: blend 0.0246, sharpest single plain emotion 0.0246,
  hard cut 1.54 m/frame² (the metric sees a pop; the blend adds none).
- Face: worst step per frame 0.124 (plain crossfade 0.124); worst second difference 0.035 (plain 0.039).
- Re-target mid-rise: value and velocity continuous; largest velocity change per ms 0.014.
- Rates under 200 random re-target sequences: worst 5.24 /s at a 0.25 s minimum time (bound checked 10 /s).
- Loop tempo from energy: afraid head crossings over 3 s: energy +0.8 → 36, -0.8 → 24 (1.5 x, as designed).
- Gaze: sad eye pitch -9.1 deg; with modulation gazeShift 1: -0.2 deg.

Not verified: no Blender render of a blended shot (no shot opts in; renders are evidence only when a check needs them).
