# T-097B · Personality-driven reactions (2026-11-18)

Implemented: `engine/scene/reaction.{h,cpp}` (planner), `engine/anim/personality.{h,cpp}` (typed, optional
`reaction` section), `content/personality/SCHEMA.md` (documented fields and defaults). Tested: `tests/test_reaction.cpp`
(11 cases, replaces the T-097-0 stub), one addition to `tests/test_personality.cpp`. Not wired into scene playback
(`actions.cpp` is outside the write-set): plans are computed, not yet scheduled, so no shot or bake changes.

## What it does
`planReaction(event, profile, ctx)` → `ReactionPlan` (`scene/acting.h`, unchanged): notice delay, one-emotion target
(`EmotionState` with pleasantness / energy from a shared circumplex table), duration, preferred and chosen gesture,
and `PersonalityModulation` (intensity, tempo and hold scales, gaze habit). `planReactions` does it for a cast; the
actor of a `PartnerActs` event is skipped. Character independent: no names or per-character values in code; the
shipped profiles are unchanged and only their existing `reaction.delay_frames` is now read.

Split with T-097A: the plan's timing (`noticeDelay`, `duration`) is final; the target weight is the event intensity
before personality, and `modulation.intensityScale` is applied once by the emotion system (`expressedIntensity()`).

## Calibration of the shared defaults
| Default | Value | Evidence |
| --- | --- | --- |
| notice delay | 6 f | T-104 `reaction_delay` reference [4, 10] f, calibrated beat 6 f (`content/timing/`); with a timing profile its beat is used |
| `object_appears` duration | 1.5 s | T-106 reveal / watch beats: PB boy f259-289 1.25 s, PB girl f255-289 1.42 s, WT boy f27-60 1.38 s (all cut-limited) |
| `partner_acts` duration | 1.0 s | T-106 PB girl eye adjustment f125-132 0.29 s + hold f132-151 0.79 s = 1.08 s |
| `success` duration | 1.6 s | T-106 PB white-haired girl clasped-hands hold as the boat lights f250-289 1.62 s |
| `failure` duration | 1.5 s | extrapolation: not shown in the references; same scale as the others |
| emotions | curious / curious / happy / sad | T-106 observations: eyes wide, lips part (curious) on reveal and watching; open smile / clasped hands on success |
| intensities | 0.7 / 0.5 / 0.8 / 0.6 | estimate: success strongest (open smile), watching a partner weakest (eye-only adjustment) |

`tests/test_reaction.cpp` reads `content/timing/reference_timing.json` and `T-106/performance.json` and checks these
numbers against the cited rows, so a change of either side is caught.

## Baselines (bake hashes, input 7bc08ff vs this branch)
Bakes with plush-render built from the input SHA (separate worktree) and from this branch, repository root replaced by
`<ROOT>` before hashing (sha256, first 16 hex):

```
animcheck/clip_gestures.bake.json             base 8b4b21cf32f38ccd  new 8b4b21cf32f38ccd  identical
animcheck/personality.bake.json               base 0bf52653c9ae52dc  new 0bf52653c9ae52dc  identical
animcheck/wave_touch.bake.json                base e3d7f880a80c7be0  new e3d7f880a80c7be0  identical
content/scenes/milestone01_classroom.scene.json base 5be3f00a29204e0d  new 5be3f00a29204e0d  identical
content/scenes/milestone02_classroom.scene.json base 718aa4a78af03299  new 718aa4a78af03299  identical
content/scenes/test_face.scene.json           base c2e1919cd22ac8dd  new c2e1919cd22ac8dd  identical
content/scenes/test_lineup.scene.json         base 67618aeec3a20498  new 67618aeec3a20498  identical
```
animcheck gate (`tools/animcheck/run_gate.py`) logs identical, all PASS. Episode shots (`episodes/*`) need run_shot
with Blender (package path set by run_shot); not baked here. No engine code path calls the planner, so they cannot change.

ledger: see the READY line.
