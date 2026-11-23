# T-220 · plush_soft is the default final look

Owner decision 2026-11-23: the T-199 compositor look `plush_soft` is the default final profile. Previews are unchanged.

## What changed
- `pipeline/charsys/render_profiles.json`: `default_profile` is now `final720_look` (was `final720`). The description of
  `final720_look` no longer says "OPT-IN"; the file note says so too.
- `final720_look` render settings and compositor block are unchanged (same as `final720` + `plush_soft`).
- `final720` (no look), `review`, `preview_eevee`, `legacy128` and the `encode` table are byte-identical to main.
- `pipeline/charsys/tests/test_render_profiles.py`: default resolves to `final720_look`; every non-default profile and the
  encode table equal main (commit 0a20253f); `final720_look` differs from main only in its description.

## Old look
Pass `--profile final720` (`shot_render.py`, `run_shot.py`, `tools/pc/render_package.py`).

## Note
Output folders of `render_package.py` for the default are now `<pkg>_render_final720_look`.
