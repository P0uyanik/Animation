# T-172: test video with the released R3 characters

- **Shot:** `episodes/e909_two_char_acting/shots/s010/shot.scene.json` (unchanged), frames **60-228** (169 frames, 7.04 s, 24 fps).
  Covers: she offers the cup (pass from frame 88), he answers and takes it, looks at it, sets it down (release 163), both react.
- **Versions resolved (cast `version: "current"`):** boy_yellow_hoodie **2.3.0**, girl_auburn_bun_glasses **0.14.0** (both published stores, read only).
- **Third character (0.1.0): not included.** The shot has no third-character cast entry or placement, and putting her in would need a new
  cast/placement setup, so I left her out and authored no motion.
- **Command:** `python3 pipeline/production/run_shot.py --shot episodes/e909_two_char_acting/shots/s010/shot.scene.json --blender /usr/local/bin/blender --frames 60-228 --run-dir t172b --video`
  (default profile `final720`, default codec `hevc10`). Engine built from main with `cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release`.
- **Caveat on resolution/samples:** the shot file pins `render` to 640x360 and 16 spp, and run_shot uses that. The `final720` profile
  applied only its Cycles settings (adaptive threshold 0.05, persistent data). So this is a 640x360 clip, not 1280x720. I did not
  override with `--resolution`, because the brief said to render with the defaults. A 1280x720 pass would take about 4x longer.
- **Timing (4-core CPU, Cycles):** bake 19.5 s; Blender setup 882.6 s (one-off, includes loading the character masters); render 4430.8 s
  = **26.2 s per frame**; encode 8.5 s; total about 89 min. A first attempt was cancelled at my 10-minute tool timeout and discarded.
- **Files:**
  | file | size | note |
  |---|---|---|
  | `T-172_s010_f060-228_hevc10.mp4` | 1.05 MB | master, HEVC 10-bit yuv420p10le, 640x360, 169 frames |
  | `T-172_s010_f060-228_h264.mp4` | 0.90 MB | H.264 8-bit, crf 18, re-encoded from the same PNG frames |
  | `contact_sheet.png` | 0.6 MB | 8 frames, every 21st |
  | `run_shot.json` | 3.5 KB | run report |
  Both clips are small enough to be committed here.
- **Run dir (container, may be reclaimed):** `episodes/e909_two_char_acting/shots/s010/build/runs/t172b/` (frames in `render/`, bake in `bake.json`).
- **Observation:** in the contact sheet the girl's hair and the boy's hair read well; the hand-over is visible in frames 4-8. Not a formal review.
