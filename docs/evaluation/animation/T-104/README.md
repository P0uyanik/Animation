# T-104: animation timing calibration against the reference videos

Implementer: Claude (cloud), branch `t-104-claude-timing-calibration`, input `b59880a` (main `f45f446` + task file).
Owner finding: the generated animations read about 2x too fast; playback is correct, the authored timing is not.

## 1. Result
Complete. The calibrated timing is an **opt-in profile**: nothing changes for a shot unless it sets
`"timing": "calibrated"`. Making it the default is a separate one-line commit after the owner approves (section 8).

## 2. Files
| Path | Purpose |
| --- | --- |
| `content/timing/reference_timing.json` | Reference timing table: 15 observations (video, 0-based frame range, beat, evidence) and 10 beat ranges |
| `content/timing/calibrated.timing.json` | Calibrated profile: one value per beat inside its reference range; scale-aware travel |
| `content/timing/README.md` | What the files are, the opt-in rule, the personality tempo fields |
| `content/personality/boy_yellow_hoodie.json`, `girl_auburn_bun_glasses.json` | `tempo.beat_scale` / `tempo.hold_scale` only (boy 1.2 / 1.0, girl 0.85 / 1.25) |
| `engine/anim/personality.{h,cpp}` | `TimingProfile` reader (`frames`, `travelFrames`), profile lookup, the two tempo fields |
| `engine/scene/scene.{h,cpp}` | Opt-in scene key `"timing"` (parsed, checked, saved as written) |
| `engine/scene/interaction.{h,cpp}` | Interaction default frames from the profile (only frames an action leaves out) |
| `episodes/e907_exchange/make_shot.py` | `--timing <name>`: the T-095 beats with calibrated lengths -> `shots/s010_<name>/` |
| `episodes/e907_exchange/shots/s010_calibrated/shot.scene.json` | The re-timed exchange (129 f); `s010` unchanged |
| `tools/animcheck/timing.py` | Timing rule: warns on short beats and shots without a hold; never fails |
| `tools/animcheck/run_gate.py` | Runs the rule on the regression shots; WARN lines and `timing.json`, never failures |
| `tools/animcheck/thresholds.json` | One key added: `timing_still_mm_per_frame` 5.0; no existing value changed |
| `tools/animcheck/tests/test_animcheck.py` | `TimingRule` (6 tests) |
| `tests/test_timing_profile.cpp`, `tests/CMakeLists.txt` | 5 doctest cases; registration |
| `docs/evaluation/animation/T-104/*` | This report, evidence, sheet script |

## 3. Reference timing table (24 fps; `PB`/`WT` 0-based frames)
Method: the T-076 frame analysis and the character guides (section 4), plus a T-104 motion-energy curve per video
(mean absolute frame difference; WT cropped to the girl). Ranges -> calibrated values:

| Beat | Reference (frames) | Evidence | Calibrated |
| --- | --- | --- | --- |
| reach | 10-20 | WT f012-f022 point (10 f); PB S4 lower to contact (20 f) | 16 |
| anticipation | 5-12 | WT f000-f012 hand-at-chin hold; VISUAL_TARGET 5-10 | 8 |
| settle | 8-18 | WT f023-f033 (10 f, no visible overshoot) | 12 |
| hold | 12-32 | WT f033-f050 (17), f104-f120 (16); PB f136-f150 (15), S1 stare (32) | 16 |
| shared_hold | 16-30 | PB f096-f111 boat in both hands (16); S2 shared sheet f040-f070 | 18 |
| place | 20-24 | PB f151-f171 lower (report: contact about f175) | 22 |
| release | 12-18 | PB f172-f190 fingers open and withdraw | 14 |
| return | 18-53 | PB f117-f135; WT f051-f104 straighten | 20 |
| reaction_delay | 4-10 | eyes first, then the hand (VISUAL_TARGET 2-5 f gaze lead) | 6 |
| beat_interval | 18-36 | VISUAL_TARGET overall tempo (estimate) | 24 |

Travel (scale-aware): 0.045 arm lengths per frame, clamped to 10-28 frames. A carry or reach is timed by its
distance in the acting character's arm lengths, so the 18 cm-armed girl gets the time her arm needs.

## 4. The e907 exchange, before and after
Same staging, camera, cast (boy 2.0.0, girl 0.11.0) and action order; only the frame numbers change.

| Beat | Before (T-095) | After (calibrated) | Reference |
| --- | --- | --- | --- |
| look before the pick-up | f1-f4 (3 f) | f1-f11 (10 f) | anticipation 5-12 |
| his reach to the cup | f4-f18 (14) | f11-f30 (19) | reach 10-20 |
| his offer (lift) | f20-f28 (8) | f35-f45 (10) | reach 10-20 |
| her glance -> her reach | 7 f | 7 f | reaction 4-10 |
| her reach | f27-f45 (18) | f42-f64 (22) | reach 10-20 (+ her short arm) |
| shared hold | f45-f51 (6) | f64-f82 (18) | shared_hold 16-30 |
| his release and return | f51-f61 (10) | f82-f99 (17) | release 12-18 |
| her draw | f53-f65 (12) | f84-f94 (10) | reach 10-20 |
| end hold | 1 f | 30 f (f99-f129) | hold 12-32 |
| total | 66 f, 2.75 s | 129 f, 5.38 s | |

animcheck timing rule: before 3 warnings (offer 8 f, shared hold 6 f, release 10 f), after 0. Longest still run
(all hands and heads < 5 mm/f): before 14 f, after 30 f.

Why her reach is 22 f: a sweep of her reach length on the resolved scene (`build/measure_t082`) gave her forearm
-3.1 mm inside her vest at 17 f, +0.6 mm at 19 f (32.5 deg elbow swing), +1.0 mm at 20 f (25 deg) and +1.0 mm with 5 deg
from 22 f. The travel speed in the profile (0.045 arm lengths per frame) is set from that and from VISUAL_TARGET's
hand speeds; it is data, no special case.

## 5. Tests
| Command | Result |
| --- | --- |
| `cmake --build build` (PLUSH_BUILD_STUDIO=OFF, renderer OFF) | builds, no warnings |
| `build/tests/plush_tests` | **132 / 132** cases (127 before + 5 new), 43076 assertions |
| `ctest` (build/) | 1 passed, renderer tests skipped (renderer OFF, as before) |
| `python3 tools/animcheck/tests/test_animcheck.py` | **14 / 14** (8 before + 6 `TimingRule`) |
| `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` | PASS (clip_gestures 6, personality 3 + limits, wave_touch 4); timing: 0 warnings |
| `run_shot.py --shot .../s010_calibrated/shot.scene.json --stages prepare,bake,render --blend-only` | no engine warnings |
| `tools/animcheck/animcheck.py --check` on both e907 bakes | PASS (no clip or touch gestures, as T-095) |
| `build/measure_t082 <resolved scene>` | `clearance_*.json`, table below |
| `docs/evaluation/animation/T-095/measure_t095.py` | `measure_*.json`, table below |
| `tools/animcheck/timing.py` | `timing_*.json` |
| `python3 tools/check_cast.py --base origin/main` | PASS |

| Check | Before | After |
| --- | --- | --- |
| smallest arm gap (all four arms) | 0.90 mm (girl L) | 1.00 mm (0.998, the planner margin) |
| girl L elbow swing | 30 deg | 5 deg |
| largest arm rotation step | 26.5 deg/f (boy R) | 15.8 deg/f |
| heads, closest surfaces | 8.4 cm (f31) | 7.4 cm (f45) |
| heads while sharing the cup | >= 12 cm | >= 10.9 cm |
| cup drift while shared / held | <= 0.0003 mm | <= 0.0003 mm |

## 6. Baselines (unchanged)
| What | Before | After |
| --- | --- | --- |
| e907 s010 bake (`run_shot`, sha256) | `8588f191edb21fd8` | `8588f191edb21fd8` |
| animcheck regression bakes | clip_gestures `18e02718`, personality `21e2eed6`, wave_touch `229382dc` | identical |
| `make_shot.py` without `--timing` (with the packages) | `s010/shot.scene.json` | byte-identical |
| doctest | 127 / 127 | 127 old cases pass |

No face, garment, material, environment, published-version or frozen file is touched. `content/scenes/eval/exchange`
is unchanged (the eval copy of the default s010).

## 7. Visual results
| File | Content |
| --- | --- |
| `t104_preview_cycles4spp.jpg` | Cheap preview (Cycles 4 spp, 240 px): dope sheet, six beats before / after, references |
| `t104_before_after_strict_sheet.jpg` | Strict sheet (Cycles 32 spp, 640x360, shot camera): dope sheet; rows before / after at his contact, offer held, her contact, shared hold, his release, end hold; a reference row (PB f157, f172, f272, WT f22, f40, f110) |
| `t104_before_after.mp4` | Before and after side by side, same camera, Cycles 10 spp 640x360, 24 fps, 129 frames (the before half holds its last frame after f66) |

The before half of the movie is the T-095 movie (`T-095/t095_exchange_shot_camera.mp4`, same settings). The s010
bake is byte-identical to the one it was rendered from, so it was not rendered again.

## 8. Limitations and open questions
1. **Default switch**: to make the profile the default, one line: the engine falls back to `"calibrated"` when a scene
   has no `"timing"` key (or `make_shot.py`'s `--timing` default). Not done: owner approval first.
2. Per-character tempo reaches the engine only for characters that carry their personality profile; e907 does not
   (it would also switch on the personality face and life layers), so `make_shot.py` reads the tempo fields itself.
3. The task brief says "boy slower/reluctant"; his profile's owner brief is "impatient, easily bored". `beat_scale`
   1.2 follows the task; it slows his actions, not his attention changes.
4. The heads come 1 cm closer than before (7.4 cm at f45, while she glances at the cup and he looks up); still clear.
5. Reference measurements are at 1-2 frame precision; the motion-energy curves include camera moves (noted per
   observation). WT f051-f104 includes a camera push-in.
6. Workbench needs a GPU here, so the cheap preview used Cycles at 4 spp (allowed by REVIEW_RECIPE).

## 9. Commits
`git log b59880a..t-104-claude-timing-calibration`; the READY line names the final SHA.

## 10. Resource use
Token usage: not available.
