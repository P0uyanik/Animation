# T-104d: the calibrated timing profile becomes the default (2026-11-19)

Owner decision 2026-11-19 (`docs/process/OWNER_DECISIONS.md`, round 2 close-out item 2): the one-line default switch
from T-104 README §8.1. Input `f550cbd` (`integration/round3`).

## Implemented
- `Scene::timingProfile()` (`engine/scene/scene.h`): the profile a scene resolves to. An absent or null `timing` key
  gives `kDefaultTimingProfile` (`"calibrated"`), `"none"` gives the shared defaults, and any other value names that
  profile.
- Interaction defaults (`engine/scene/interaction.cpp`) and the notice delay of event reactions
  (`engine/scene/actions.cpp`, profile resolution only) both use it.
- A profile the scene names but that cannot be found is still a load error. If the implicit default is not found (a
  scene outside a content tree), the shared defaults apply without a warning, as with a missing personality profile.
  Supervisor answer Q1.
- `make_shot.py` is unchanged: its `--timing` default and e907 s010 stay as they are, because the owner reviews the
  exchange separately (Q4).

## What the switch changes: no existing shot
This was measured, not assumed:
- **Scene files:** none edited. All 51 `plush.scene` files in the repository were scanned. The 11 with
  reach/grasp/hold/place/handover actions write out every frame the profile would set
  (contact/end/receiverStart/release). Two scenes have `events` (e908); there the profile's `reaction_delay` (6 f)
  equals the shared `kReactionDelayFrames` (6 f), and it is not scaled per character. No scene is in
  `tools/frozen_manifest.txt`.
- **Bakes:** `run_shot.py --stages prepare,bake` (bpy 5.3.0), before (`f550cbd`) vs after (this branch). The whole
  `bake.json` was compared.

| Shot | Bake before vs after |
| --- | --- |
| `content/scenes/eval/exchange` | identical |
| `content/scenes/eval/handover` | identical |
| `episodes/e901_clip_test/shots/s010` | identical |
| `episodes/e905_props_test/shots/s010` | identical |
| `episodes/e907_exchange/shots/s010` | identical |
| `episodes/e907_exchange/shots/s010_calibrated` (explicit key) | identical |
| `episodes/e908_boy_acting/shots/s010` (events) | identical |
| `episodes/e908_girl_acting/shots/s010` (events) | identical |
| `docs/evaluation/animation/T-096/shots/e905_s010_current_t096` | identical |
| `docs/evaluation/animation/T-082/latest` | identical |

- **Goldens:** none regenerated, because none changes.
- **Image regressions:** ctest `regression_milestone01`, `regression_face_neutral` and `regression_lineup_abc` pass
  unchanged.
- **animcheck:** no regression shot (`tools/animcheck/shots/`) uses interactions or events, so the timing rule sees
  the same bakes and raises no new warnings.

## Tests
`tests/test_timing_profile.cpp` (write-set extended by the Supervisor, Q2):
- The invariant "shared timing reproduces the old shot bit for bit" is kept, now with `"timing": "none"`.
- New checks: an absent key resolves to `calibrated`, and its bake equals the explicit `calibrated` bake. `"none"`
  resolves to the shared defaults and is saved as written.

No threshold changed.

## Not tested
- No unit test covers the silent fallback outside a content tree: the test packages resolve relative to `tests/data`.
  An instrumented run of `plush_tests` showed no test scene that takes this fallback.
- No renders: the bakes are identical, so there is nothing to look at.
