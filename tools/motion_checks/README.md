# motion_checks: flicker, popping and interpenetration over time (T-125)

Automatic checks over a baked shot (`plush.shot_bake/1`) and its rendered frames. Each issue reports a frame range,
the worst frame and value, and a small JPEG evidence strip (rendered crops of the worst frame and its neighbours, plus
a plot of the measured value against the threshold). **Not part of the gate**: `tools/check_all.py` does not run it.
Measurements and the reasoning behind every threshold: `docs/evaluation/animation/T-125/README.md`.

```
# 1. bake (as the production run does) and, for flicker, render the passes (Blender, or the pinned bpy wheel)
python3 pipeline/production/run_shot.py --shot <shot>/shot.scene.json --blender <blender> --stages prepare,bake --run-dir <run>
<blender> -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake <run>/bake.json --cast <shot>/build/cast.json \
    --out <run>/blend --blend-only
<blender> -b --factory-startup -P tools/motion_checks/render_passes.py -- --blend <run>/blend/shot.blend --out <run>/passes \
    [--frames A-B] [--samples 16]
# 2. collision trace on the engine's collision bodies (C++, not part of the build)
g++ -std=c++23 -O2 -I engine -I build/engine tools/motion_checks/collision_trace.cpp -Lbuild/engine -lplush_scene \
    -lplush_model -lplush_anim -lplush_fuzz -lplush_geom -lplush_core -lembree4 -ltbb -o build/collision_trace
build/collision_trace <shot>/build/shot.resolved.scene.json > <run>/trace.json
# 3. checks
python3 tools/motion_checks/run.py --bake <run>/bake.json --scene <shot>/build/shot.resolved.scene.json \
    --trace <run>/trace.json --frames <run>/passes --out <run>/motion_checks [--strips 4] [--check]
python3 tools/motion_checks/tests/test_motion_checks.py
```

`run.py` needs only numpy and Pillow; `render_passes.py` runs inside Blender (or `tools/bpy_blender.py`). Every input
except `--bake` is optional: without `--frames` there is no flicker check and the strips have plots only; without
`--trace` only the mesh-level and prop-room interpenetration checks run.

| File | What |
| --- | --- |
| `run.py` | CLI: runs the checks, writes `motion_checks.json` (format `plush.motion_checks/1`) and `strips/*.jpg` |
| `popping.py` | second-difference / jerk outliers on joints, joint rotations, face morphs, props and skinned vertices |
| `penetration.py` | interpenetration series from the collision trace; body-garment (mesh level) and prop-room checks |
| `flicker.py` | temporal luminance noise and sign flips per region, denoised and noisy image |
| `collision_trace.cpp` | per-frame signed gaps from `engine/scene/collision.h` / `interaction.h` (the planner's own bodies) |
| `render_passes.py` | Cycles render of a `shot.blend` with the noisy image, object index (region) and depth / normal passes |
| `exr.py`, `frames.py` | numpy reader of uncompressed (multi-part) EXR; reduction to compact npz frames |
| `shot.py` | bake + package loading, linear blend skinning with morphs, camera projection |
| `evidence.py` | evidence strips |
| `thresholds.json` | all limits (documented in the T-125 evaluation README) |

## Popping (`popping.py`)

Channels, every frame of the bake: bone pivots (mm), bone rotations relative to the parent (degrees), face morph
weights, prop positions and rotations, and skinned vertices (every 16th vertex of every mesh, morphs included; mm).
With velocity `v_t = x_t - x_{t-1}` and second difference `a_t = x_{t+1} - 2 x_t + x_{t-1}`, frame t pops when

- `|a_t| >= abs_min` (visible: 8 mm/f² is about 3 px/f² at the e907 / e909 framing, 2.6 mm per pixel), and
- `|a_t| >= jerk * max(|v_{t-2}| .. |v_{t+3}|)`: the velocity changes by that share of the move's peak within one frame
  (animcheck's `max_jerk` rule on every channel). A one-frame spike scores ~2, a start or stop within one frame ~1, a
  cubic smoothstep 0.38 over 8 frames, 0.55 over 4.

Rotations use angles (`|a_t|`: the rotation between the actual pose at t+1 and the one constant angular velocity
predicts). Hits on neighbouring frames and channels of one character merge into one issue (`channels`,
`worst_channels`). Saccades, blinks and the lid / lash / eye / brow meshes they move are fast by design
(`by_design` in thresholds.json): their `override` raises the limit, so they are measured (`by_design_a_max` in
the stats) but not flagged; a lower override lists them with `"by_design": true`, still not counted.

## Interpenetration (`penetration.py`, `collision_trace.cpp`)

| Kind | Pair | Measure |
| --- | --- | --- |
| `arm` | body-body, body-garment | forearm (wrist half) and hand capsules, sleeves included, against the character's own torso + garment shell (`armClearance`, counted from the rest allowance) |
| `head` | character-character | the two head and hair shells (T-096 volumes) |
| `limb` | character-character | one character's limb capsules against the other's torso shell |
| `hand_prop` | hand-prop | hand capsule against the prop's collision proxy (`content/assets/*.asset.json`); the capsule covers palm and fingers, so a grip is inside it by the grip depth |
| `prop_body` | prop-body | proxy surface samples against each torso shell |
| `garment` | body-garment (mesh) | sampled garment vertices against their rest-nearest skin vertex carried by the same dominant bone, along the skin normal: deeper under the skin than at rest |
| `prop_room` | prop-room | proxy axis against the room's boxes (table top, floor, wall) |

## Flicker / shimmer (`flicker.py`)

Regions from the object index pass (`render_passes.py`): background (room, world), hair, fibres (garment and felt
fibre curves), skin, cloth and props. Per frame t (needs t-1 and t+1), on the denoised image and on the noisy image
before the denoiser:

- **held noise**: on pixels whose geometry holds still over t-1..t+1 (same region, depth change < 0.5 %, normal turn
  < 5°; the held-pose baseline), `1.4826 * median|r| / sqrt(1.5)` of the relative temporal second difference
  `r = (L_t - (L_{t-1} + L_{t+1}) / 2) / (mean + 0.02)`: the per-frame temporal noise.
- **flip share**: motion tolerant, for hair and fibres (sub-pixel strands are never held): the share of the region's
  pixels whose luminance changes by >= 5 % from t-1 to t and back by >= 5 % from t to t+1. Motion moves a pixel one
  way; noise, denoiser instability and strand aliasing turn it back. Per region and per 16 x 16 tile; a tile issue
  needs 3 consecutive frames (a blink or saccade turns back for one or two).
- **denoiser gain**: noisy / denoised of both measures.

The renders use the shot's production settings (Cycles, 16 samples, OIDN). `render_passes.py` reports the sampling
seed: the production setup has a fixed seed (`use_animated_seed` off), so static pixels of the noisy image are
bit-identical from frame to frame and only what moves changes its noise.
