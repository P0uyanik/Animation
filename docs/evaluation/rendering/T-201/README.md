# T-201 · `preview_eevee`: an opt-in EEVEE profile for blocking and acting reviews

Branch `t-201-claude-preview-eevee` from `main` 910afd5. Owner decision 2026-11-22 ~17:15 CET. **Cycles stays the default
for look review and finals.** `final720`, `final720_look`, `review`, `legacy128`, `default_profile` and the encode table
are unchanged; `test_render_profiles.py` compares them with commit `0f3787e`.

## What was built
- `pipeline/charsys/render_profiles.json`: new profile `preview_eevee` = `"engine": "eevee"`, 960×540, 16 TAA samples,
  an `eevee` block (2 shadow rays, 4 shadow steps, half shadow-map resolution, AO-only fast GI) and persistent data. No
  `cycles` or `compositor` block, so nothing about the Cycles look changes.
- `pipeline/charsys/render_engine.py` `apply_profile`: applies an `eevee` block to `scene.eevee` (unknown keys are
  refused, like `cycles`/`render`). A profile with an `engine` key must run on that engine: `preview_eevee` on a Cycles
  scene stops with *"this profile renders with eevee, but the scene is set to CYCLES: pass --engine eevee"*, so it can
  never silently render with Cycles. Profiles without an `engine` key take the old path; blocks are now read only when
  the profile has them.
- `tools/pc/render_package.py`: already chose the engine as `--engine`, else the profile's `engine` key, else cycles
  (T-205); only its docstring changed. On the PC: `tools\pc\render_package.cmd <zip> --profile preview_eevee` (needs a
  package baked after this lands). Note: as for every profile there, the shot's own `production.render` resolution and
  samples win over the profile's (e912 s010 → 640×360, 16 samples); pass `--resolution 960 540` to get the profile size.

## Headless verdict (this cloud container: 4 vCPU, no GPU, Blender 5.3.0)
**EEVEE works headless here, but slowly.** Blender reports *"Unable to initialize a Vulkan 1.1 instance"* and a few
*EGL_BAD_MATCH* lines, then renders through Mesa's software OpenGL (llvmpipe) via EGL; images are complete and correct
(all three characters, nothing in `not_rendered`). One log line, *"Could not allocate velocity geometry buffer"*, only
affects motion blur, which these renders do not use. On a CPU rasteriser EEVEE is **slower than Cycles `review`**, so in
the cloud the profile is a correctness check only; the speed-up is for the owner's PC (GPU) via
`tools/pc/render_package.py`. PC timings are still to be measured there.

## Timings (`timings.json`, one frame per Blender run, e912 s020 bake of frames 80–160)

| Frame | preview_eevee (960×540, 16) | review (Cycles 1280×720, 16) | final720 (Cycles 1280×720, 128) |
| --- | --- | --- | --- |
| s020 f80 | 936 s | 128 s | 443 s |
| s020 f160 | 627 s | 204 s | 749 s |

Render seconds from `shot_render.json` (`render_s`); setup was 30–34 s in every run.
MULTIFRAME

## Side-by-side
Row 1: full frame, preview_eevee | review | final720 (each scaled to 1280×720, then to 341 px wide). Row 2: the same
1:1 crop of the 1280×720 frame.

| Sheet | |
| --- | --- |
| [`s020_f080_sheet.jpg`](s020_f080_sheet.jpg) | shot 3, three characters at the table |
| [`s020_f160_sheet.jpg`](s020_f160_sheet.jpg) | shot 4, hand-over, auburn girl's face and glasses |

What EEVEE shows well: poses, staging, silhouettes, hand contacts, eye direction, mouth shapes, i.e. what a blocking or
acting review needs. What it does not: skin has no subsurface (flatter and paler), the glasses lenses read as cloudy,
fur/hair is darker with harder contact shadows, and the white girl's hair loses its soft bounce. **Do not judge look,
materials or lighting on it.**

## Follow-up (not in this write-set: `shot_render.py` / `run_shot.py` are owned by T-194)
Today the cloud path must pass `--engine eevee` with `--profile preview_eevee` (else `apply_profile` refuses). To make
both honour the profile's `engine` key, two lines:
- `pipeline/charsys/shot_render.py` `parse()`: default `--engine` to `None`, then after `a.profile_data = ...`:
  `a.engine = a.engine or a.profile_data.get("engine", "cycles")`.
- `pipeline/production/run_shot.py`: the same line after `a.profile_data, a.encode_args = ...` (with `--engine`
  defaulting to `None`), so its render stage passes `--engine eevee` and its run report records it.

Also cosmetic: `shot_render.json` `engine_settings` records `configure()`'s defaults (4 shadow rays); the values the
profile set are in `profile.applied` (2 rays).

## Tests
`python3 pipeline/charsys/tests/test_render_profiles.py`: all pass (the new checks are prefixed `T-201:`): old profiles,
default and encode table identical to `0f3787e`; no Cycles profile names an engine or an `eevee` block; `preview_eevee`
shape; shot_render parse takes its resolution/samples; `apply_profile` sets the `eevee` block, refuses a Cycles scene and
unknown keys; `render_package` engine choice for preview_eevee/review/final720/`--engine eevee`. With
`PLUSH_TEST_EEVEE=1` and bpy it also renders a tiny EEVEE frame (16 s here); without it that check is skipped, so the gate
does not need OpenGL. No new test file. `python3 pipeline/production/tests/test_bake_package.py`: all pass.

## How to reproduce
```
python3 pipeline/production/run_shot.py --shot episodes/e912_paper_boat/shots/s020/shot.scene.json --blender blender --stages prepare,bake --run-dir t201 --frames 80-160
blender -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake episodes/e912_paper_boat/shots/s020/build/runs/t201/bake.json \
  --cast episodes/e912_paper_boat/shots/s020/build/cast.json --out <dir> --profile preview_eevee --engine eevee --frames 80-80
# same with --profile review / final720 (no --engine)
```
