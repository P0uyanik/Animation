# T-166: final720 default render, HEVC 10-bit default encode

Owner decision 2026-11-20 item 3. Measurements: [../T-124/README.md](../T-124/README.md). One revertible change.

## What changed

| | Before | Now |
|---|---|---|
| `shot_render.py` without `--profile` | 32 spp, shot/bake resolution, adaptive 0.01 | profile `final720`: 1280x720, 128 spp, adaptive 0.05, persistent data |
| `run_shot.py` render step | `--samples` always passed (shot `production.render.samples`, else 32) | `--profile` passed (default `final720`); samples/resolution: explicit flag, then the shot's own `production.render`, then the profile |
| `run_shot.py` encode step | H.264 8-bit, CRF 18 | `--codec hevc10` (default): x265 slow, CRF 18, 10-bit 4:2:0, `hvc1` tag |

`pipeline/charsys/render_profiles.json` is the single table: `default_profile`, the profiles, and an `encode` block.

## Named alternatives (nothing removed)

- `--profile legacy128`: the previous final preset, 128 spp, adaptive 0.01, no forced resolution (the shot's own).
- `--profile review`: 16 spp review profile from T-124, unchanged.
- `--codec h264`: H.264 8-bit 4:2:0, x264 slow, CRF 18, the compatibility fallback.
- Masters stay lossless (PNG frames); only `shot.mp4` changes codec.

A golden or image test that depends on the old render settings must pin `--profile legacy128` explicitly. None of the
repository's automated tests renders through the default (`test_shot_eyes.py` uses `--blend-only`; the workflow test
uses a fake Blender), so no golden needed pinning.

## Notes

- Shots whose `production.render` names `samples` or `resolution` keep them (an explicit shot choice); the profile's
  adaptive threshold and persistent data still apply.
- `status.json` gained an additive `profile` key.
- ffmpeg must have libx265 for the default encode; `--codec h264` needs only libx264.
- Not measured here: playback on devices (see T-124 section 3).

Tests: `pipeline/charsys/tests/test_render_profiles.py` (registered in `tools/check_all.py`, one line).
