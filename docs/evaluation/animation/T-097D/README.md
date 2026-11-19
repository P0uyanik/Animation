# T-097D evaluation: reactions in playback (scene `events` -> reaction plans -> look, blended emotion, gesture)

Input `3ecb85c` (origin/integration/t-097b: T-097A + T-097B + T-097C merged). Engine built Release (renderer ON,
no Open Image Denoise in this container), `plush-render --bake`. No Blender run (not needed: engine-only change).

## What plays
For each event of the opt-in scene key `events` (shape and fields: `docs/PRODUCTION_PIPELINE.md`, "Scene events") and
each reacting character, `SceneEvaluator::planReactionActions` (`engine/scene/actions.cpp`) asks the T-097B planner
for a `ReactionPlan` (its personality profile, else the shared defaults; the scene's timing profile for the shared
delay) and generates, at `frameStart + (time + notice delay) x fps`:
- a `look` at the source (`object`, or new `atCharacter`: that character's face), held `max(3 f, gazeShift x duration)`,
  then `back` to the earlier gaze; with no earlier gaze it turns in and out over 8 f on `lookAt.weight` (only
  generated looks key that track, so authored looks are untouched);
- an `emotion` with `blend: true` (T-097A), released after the planned duration (`end` = start + duration + the
  emotion's decay), `modulation` = the plan's intensity scale and gaze shift (tempo/hold are already in the plan);
- a `clip` for the plan's gesture (the planner gets the `content/clips` names as `availableGestures`).

Ordering: events by time (stable), then scene character order; per reaction look, emotion, gesture; appended after
the authored actions (ties keep authored first). The notice delay is never shorter than the profile's
`reaction.delay_frames[0]` (Supervisor note: mid delay x `tempo_scale` < 1 would otherwise undercut what the T-097C
acting rule requires). Decisions: a reaction emotion replaces the character's other blended emotions (T-097A default,
no `keep`); a scene event without a source plays no look.

## Byte identity (scenes without `events`)
sha256 (first 16 hex) of the bake, base = input `3ecb85c` build, new = this branch, same machine and inputs:

| Shot | base | new |
| --- | --- | --- |
| content_scenes_milestone01_classroom | `15d8861b68811e9e` | `15d8861b68811e9e` |
| content_scenes_milestone02_classroom | `03c96799524a39b8` | `03c96799524a39b8` |
| content_scenes_test_face | `98c1514c1b1251e3` | `98c1514c1b1251e3` |
| content_scenes_test_lineup | `1cfcac3908193894` | `1cfcac3908193894` |
| episodes_e000_pilot_shots_s010_shot | `ef73b054b1e62b31` | `ef73b054b1e62b31` |
| episodes_e900_workflow_test_shots_s010_shot | `08e01cc0955f43e4` | `08e01cc0955f43e4` |
| episodes_e901_clip_test_shots_s010_shot | `f6b8f5f4682b753a` | `f6b8f5f4682b753a` |
| episodes_e902_emotion_test_shots_s010_shot | `9e18a5d524163249` | `9e18a5d524163249` |
| episodes_e903_test_video_shots_s010_shot | `d079d105a1705c75` | `d079d105a1705c75` |
| episodes_e904_secondary_motion_shots_s010_shot | `aec1e6deb3211a09` | `aec1e6deb3211a09` |
| episodes_e904_secondary_motion_shots_s020_shot | `258f240ac4bb821e` | `258f240ac4bb821e` |
| episodes_e905_props_test_shots_s010_shot | `6b5230bc623e6a80` | `6b5230bc623e6a80` |
| episodes_e906_acting_test_shots_s010_shot | `6a6e3432cc66af28` | `6a6e3432cc66af28` |
| episodes_e907_exchange_shots_s010_calibrated_shot | `9445b1805acad761` | `9445b1805acad761` |
| episodes_e907_exchange_shots_s010_shot | `24e893c9316b169f` | `24e893c9316b169f` |
| tools_animcheck_shots_clip_gestures | `18e02718158ed3aa` | `18e02718158ed3aa` |
| tools_animcheck_shots_personality | `21e2eed6e45ed871` | `21e2eed6e45ed871` |
| tools_animcheck_shots_wave_touch | `229382dcbfc2ad5b` | `229382dcbfc2ad5b` |

18/18 identical (animcheck shots, content scenes, every episode shot incl. e902-e907). The episode shots normally get
their character packages from `run_shot` (Blender); here their `asset` fields were pointed at the test packages
(`tests/data/imported/boy_yellow_hoodie_1.0.0`, `girl_auburn_bun_glasses_m3`) in temporary copies (deleted after),
the same stand-ins for base and new. Not verified: bakes with the current published packages through `run_shot`.

## Tests
`build/tests/plush_tests`: 173 cases, all pass (167 before + 6 new in `tests/test_reaction_playback.cpp`):
- parsing / validation / save round trip of `events`;
- delayed, blended reaction for both profiles (girl and boy profiles read as they are, no tuning): the body is
  identical to the no-events scene up to the reaction start (diff 0 m), then ramps in (girl: +1 f 0.013 m, +14 f
  0.083 m, largest per-frame step 0.026 m; boy: 0.004 / 0.026 / 0.008 m); look end follows the gaze habit;
  `partner_acts` skips the actor;
- determinism: identical generated actions and poses for the same events in reversed list order; `characters` filter;
- the T-097C acting rule (`tools/animcheck/acting.py`, run on the scene with the generated actions appended) sees the
  delays: girl glance 3 f after the event (profile notice delay 2 f), boy 6 f (4 f), 0 warnings;
- a fixture profile's preferred gesture (`["no_such_clip", "point"]`) plays `point` as a clip at the reaction start;
- a quick fixture profile (`delay_frames` [2, 4], `tempo_scale` 0.5: planned 1.5 f) starts at 2 f; acting rule 0 warnings.

`python3 tools/animcheck/tests/test_animcheck.py`: 18 OK (unchanged). `ctest`: plush_tests passes; the image
regressions `regression_milestone01` (rmse 0.0464) and `regression_face_neutral` (0.0406) fail in this container
with exactly the same rmse on the unmodified base build (no denoiser here), `regression_lineup_abc` passes (0.0125).
No test, threshold or frozen asset changed.

## Limits
- Generated looks are not in the personality "watching" spans (T-053 mouth-while-watching reads authored looks only).
- A character source is looked at through its head bone, as compiled so far (a later action of that character that
  moves it is seen only if it compiled earlier in frame order).
- No render / visual review made (no character-specific acting is tuned in this task; T-097-boy/girl).
