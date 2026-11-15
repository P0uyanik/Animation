# T-010 evidence: V1 test video (e903_test_video/s010)

**Shot** `episodes/e903_test_video/shots/s010/shot.scene.json` (e902 structure, lights, floor/wall and cast block):
- 60 frames at 24 fps (2.5 s), 960×540;
- medium two-shot at eye level (camera at 0.78 m, the characters' eye height; 40 mm);
- the boy is the published 1.0.0, the girl an unpublished spec build;
- the girl: `happy` (started before frame 1, so she is happy from the first frame), then the `wave` clip (frames 1–60,
  speed 1.35 so the whole gesture fits);
- the boy: `surprised` (frames 1–30), then `happy/laugh` (from 24, crossfade), with a neck key pitching his head down
  (frames 28–60; world head pitch reaches −14.3° at frame 44);
- both look at the camera; automatic blinks off (`blinkInterval` 100, as in e902).

**Commands**
```bash
python3 pipeline/production/run_shot.py --shot episodes/e903_test_video/shots/s010/shot.scene.json \
    --blender <blender> --video --run-dir final
python3 pipeline/clips/measure_shot.py --scene <build>/shot.resolved.scene.json --bake <build>/runs/final/bake.json \
    --out docs/evaluation/animation/T-010
python3 pipeline/clips/t010_sheets.py --frames <build>/runs/final/render --gaze docs/evaluation/animation/T-010/gaze_check.json \
    --out docs/evaluation/animation/T-010
```

**Render settings**
- Cycles at 16 samples with OIDN denoising (`use_denoising`, denoiser OPENIMAGEDENOISE).
- One test frame (44) at 16 samples looked clean. Lower sample counts were not tested.
- Blender: the bpy 5.3.0 module (Python 3.13 venv) behind a `blender` command-line wrapper.

**Results**
| Check | Result |
| --- | --- |
| mp4 | 60 frames, 2.500 s, 24 fps, 960×540, h264 |
| Gaze in the bake (`gaze_check.json`) | inside the limits for both characters. The boy: max up +14.3°, down 8.9°, left 7.3°; the girl: max down 10.1°, right 8.2°. Limits: up 20 / down 25 / left 30 / right 30. The eyes stay on the camera (0.00° off) |
| Eyes visible in the render (`eye_strips.png`, `contact_sheet.png`) | **the girl: PASS** (open in frames 1–60). **The boy: FAIL**: open in frames 6–31; heavy lids in 1–3; one eye open in 4–5 and 32–33; closed in 34–60 |
| Smoothness (`smoothness_check.json`, T-002 rule) | PASS for both. The boy: max 10.46°/frame, worst ratio 0.87 of the limit; the girl: max 19.26°/frame inside the wave, worst ratio 0.80 |
| Bone reconstruction in Blender | boy 0.0005 mm, girl 0.0004 mm, 0.0° |
| Render time | 441.6 s for 60 frames (7.36 s per frame); whole run 446.5 s wall clock |

**Boy eye finding:** the baked Blink weight is 0 in every frame, and no shape key of his is above 0.01 in the shot
file. Whether his eyes look open depends on the sign of his eye pitch relative to his head (see `eye_strips.png`).
This comes from the master's eye/lid set-up, not from the engine's gaze limit. The master is frozen, so this was not
investigated further.
