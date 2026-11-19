# Timing data (T-104)

Animation timing as data, calibrated against the reference videos (`docs/references/video_paperboat.mp4`,
`video_watertable.mp4`). Frames at 24 fps.

| File | Format | What |
| --- | --- | --- |
| `reference_timing.json` | `plush.reference_timing/1` | The reference timing table: every measured observation (video, 0-based frame range, beat, evidence) and the beat ranges derived from them (`beats.<beat>.frames = [low, high]`). Read by the animcheck timing rule (`tools/animcheck/timing.py`). |
| `calibrated.timing.json` | `plush.timing_profile/1` | The calibrated timing profile: one value per beat inside its reference range, and the scale-aware travel speed. Read by the engine (`anim/personality.h` `TimingProfile`) and by `episodes/e907_exchange/make_shot.py --timing calibrated`. |

## Status: default (T-104d, owner decision 2026-11-19)

The calibrated profile is the **default**: a scene without a `"timing"` key uses it. `"timing": "none"` keeps the shared
engine defaults (`scene/interaction.h`); a named profile that cannot be found is a load error. A scene outside a content
tree with no profile above it falls back to the shared defaults silently. Details: `docs/PRODUCTION_PIPELINE.md`,
"Animation timing". Every existing shot baked bit for bit the same after the switch (`docs/evaluation/animation/T-104d/`).

## What the profile sets
- **Engine defaults** for interaction frames a scene leaves out (`scene/interaction.h`, `InteractionContext::timing`):
  reach / grasp contact, touch end, hold end (at least the travel time of the carry), place contact and end, and the
  hand-over's receiver start, contact, shared hold and release. Frames written in an action always win.
- **Beats of authored shots**: `make_shot.py --timing <name>` builds the e907 exchange from the beats
  (`episodes/e907_exchange/shots/s010_<name>/`).
- **Scale-aware travel**: carry and reach times come from the distance in **arm lengths** of the acting character
  (`travel.arm_lengths_per_frame`), so a doll-sized arm is not driven at human speed in metres.

## Per-character tempo (`content/personality/<id>.json`, `tempo`)
| Field | Meaning | boy_yellow_hoodie | girl_auburn_bun_glasses |
| --- | --- | --- | --- |
| `beat_scale` | multiplier on every beat except holds (> 1 = slower) | 1.2 (slower, reluctant) | 0.85 (quicker) |
| `hold_scale` | multiplier on `hold` and `shared_hold` | 1.0 | 1.25 (with holds) |

Missing fields are 1. They are read only when a scene opts into a timing profile; for the engine, only for characters
that also carry their personality profile.
