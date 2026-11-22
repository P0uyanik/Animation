# T-199 · Compositor look preset ("plush_soft") — opt-in, awaiting owner approval

Branch `t-199-claude-compositor-look`. Source: T-196 report §4 Q2. **Nothing uses the look unless a profile asks for it;
the owner has not approved it yet, so it is not applied to any episode, shot or released asset.**

## What was built
- `pipeline/charsys/render_engine.py`: `apply_compositor_look(scene, cfg)`, called from `apply_profile` **only when the
  profile has a `"compositor"` block**. No block = the previous code path, no compositor attribute touched.
- `pipeline/charsys/render_profiles.json`: one new profile, `final720_look` = `final720` (same resolution, samples,
  adaptive threshold) + the `compositor` block below. `final720`, `review`, `legacy128` and `default_profile` are unchanged.
  Select with `--profile final720_look` (no change to `shot_render.py` / `run_shot.py` needed: `shot_render` already
  records what `apply_profile` returns).
- Recorded in the run report (`shot_render.json` → `profile.applied.compositor`): look name, all resolved parameters,
  Blender version, node chain.
- Tests: `pipeline/charsys/tests/test_render_profiles.py` (all pass). Without the block `apply_profile` returns today's dict
  and a tiny fixed-seed Cycles render is **pixel-identical** to the pre-T-199 settings and creates no node tree. With the
  look the image changes, two renders are pixel-identical (deterministic), the chain is recorded, unknown keys are refused,
  and Blender 6.0 is refused with a clear `ValueError`.

## Node chain (all Blender built-in, no external tools)
`Render Layers → Glare (Fog Glow) → Color Balance (lift/gamma/gain, warm gain) → Color Correction (saturation) →
[vignette: Ellipse Mask → Blur (size = image size × softness, via Image Info) → Math (mask·s + 1−s) → Mix multiply] → Group Output`.
Eleven nodes. It runs in scene-linear before the view transform, and the vignette scales with the render resolution.

| `plush_soft` (in JSON) | value |
| --- | --- |
| glow | Fog Glow, quality High, threshold 0.5, smoothness 0.6, strength 0.6, size 0.6 |
| grade | saturation 1.08, gain (1.03, 1.00, 0.96), lift neutral |
| vignette | strength 0.12 (corners 12 % darker), ellipse 0.95 × 0.95, softness 0.2 |

`plush_strong` (the "stronger" variant requested for the comparison; **not** in the JSON unless the owner picks it): glow
threshold 0.35, smoothness 0.8, strength 1.0, size 0.7; saturation 1.10, gain (1.04, 1.00, 0.95); vignette 0.22.

## Blender API note (the 6.0 risk)
Written for Blender **5.x only** (checked on 5.3.0). 5.x builds the look as a `CompositorNodeTree` on
`Scene.compositing_node_group` with a Group Output (no Composite node; `Glare` type/quality are input sockets). 4.x used
`use_nodes` + `node_tree` + Composite and node properties; 6.0 changes the API again (deprecation warning in the T-196
probe). Outside 5.x the function raises `ValueError` naming the Blender version, so a look render never silently comes out
without the look. The version check and the whole tree build are in this one function, so a 6.0 port is a local change.
All node and socket names are looked up by name/identifier, and unknown settings in the block are refused.

## Side-by-side (copies only; nothing in `episodes/` or released assets changed)
Frames of the T-187 paper-boat scenes (cast `current`), baked into git-ignored `build/` folders, then rendered with the real
`shot_render.py` at **final720 settings** (1280×720, 128 spp, OIDN, adaptive 0.05), one frame per Blender run:
`s020 f80` (shot 3: the boat is shown), `s020 f160` (shot 4: hand-over), `s010 f140` (shot 2: close on the girl).
Each sheet is 1023 px wide: row 1 full frame before | plush_soft | plush_strong; row 2 the same 1:1 crop (placed where the
look changes most); row 3 |after − before| × 6.

| Sheet | |
| --- | --- |
| [`s020_f080_sheet.jpg`](s020_f080_sheet.jpg) | shot 3, three faces + boat |
| [`s020_f160_sheet.jpg`](s020_f160_sheet.jpg) | shot 4, hand-over, boy's hoodie fibres |
| [`s010_f140_sheet.jpg`](s010_f140_sheet.jpg) | shot 2, girl's face, hair, paper |

What it does: highlights get a soft halo (cheeks, paper, knuckles), skin and the table go slightly warmer, colours a touch
richer, the frame edges slightly darker. Fibres stay sharp (the glow is a blur added on top, not applied to the base image).
Mean change is about 5.4/255 per channel, maximum about 27–37/255, so it is clearly visible but gentle.
**First pass note:** the first parameters (glow 0.25, vignette 6 %) changed the image by only ~1.5/255 and were not
judgeable, so they were retuned on linear EXRs before the final renders; the JSON holds the retuned values.

## Render time with / without (this container, 4 CPU cores, Blender 5.3 bpy build, one frame per run)
Render seconds per frame (`shot_render.json: render_s`), setup ≈ 37–42 s in every run:

| Frame | no look | plush_soft | plush_strong |
| --- | --- | --- | --- |
| s020 f80 | 509.6 | 485.5 | 482.2 |
| s020 f160 | 866.8 | 846.7 | 836.9 |
| s010 f140 | 811.3 | 813.4 | 810.1 |
| mean | 729.2 | 715.2 | 709.7 |

The differences (−5 % … +0.3 %) are run-to-run noise on this machine; the compositor adds no measurable time (a few
seconds at most against 8–14 min of Cycles per frame). The absolute times are slower than the ~208 s of T-124 because
this is a 4-core CPU box and these are close-up, fibre-heavy frames.

## How to reproduce
```
python3 pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/s020/shot.scene.json --blender <b> --stages prepare,bake --run-dir t199
# one frame of the bake -> shot_render with --profile final720 or final720_look (episodes/e912_paper_boat/preview.py does the subset-bake step)
python3 pipeline/charsys/tests/test_render_profiles.py
```
The strong variant was rendered from a scratch copy of `pipeline/` whose `render_profiles.json` had an extra
`final720_look_strong` profile; the repository only holds `final720_look`.

## Notes
- PNG file bytes differ between otherwise identical renders (identical pixels), so the tests hash pixels, not files.
- Open for the owner: approve `plush_soft` as is / pick `plush_strong` / ask for other values; then (a separate task) decide
  whether any episode profile should point at it. This task changes no default.
