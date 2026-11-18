# T-053: personality profile system (reader, limits, checks)

Implementer: Claude (cloud) · lane C · path B (the owner approves the profile clips) · branch `t-053-claude-personality`
from `origin/staging` (e449ef1) · 2026-11-18.

## 1. Task and objective
One shared reader resolves `content/personality/<id>.json` (`plush.personality/0`) into typed parameters that every
animation layer receives; profiles derived from the references and owner decisions, with a `limits` section clamped by
the engine and checked by a personality check in `tools/animcheck/`.

## 2. Result: complete, with limitations (section 8)
All six acceptance criteria are implemented and tested. Some profile parameters are read but have no engine layer yet
(attention, boredom/fidgets, saccade interval, look-down bias, smile choice, reaction), and two need files outside the
write-set (section 8).

## 3. Files changed
Engine:
| File | Purpose |
| --- | --- |
| `engine/anim/personality.h`, `.cpp` | The reader: typed `PersonalityProfile` (tempo, energy, posture, attention, boredom, gaze, blink, face, smile, gestures, limits), strict type and range errors, `findPersonalityFile` (walks up, `<id>.json` then `<id>.draft.json`), `clampPersonalityToLimits`, shared action-unit aliases |
| `engine/anim/body_mechanics.cpp` | Its own JSON reader replaced: `applyPersonalityToBodyMechanics(params, PersonalityProfile)`; the JSON entry point now parses through the shared reader (same values: regression bakes byte-identical) |
| `engine/scene/scene.h`, `.cpp` | `CharacterDesc::personality` (id or false, saved as written); `buildPersonalities()` (once per action compile, before body mechanics and the face layers); life parameters (blink interval and shape, idle amplitude, head lag); face offsets in the morph composition (snapshot, bake, expression bones); body mechanics take the character's profile unless `bodyMechanics.personality` names one; warnings for clamped values and out-of-limit reaches |
| `engine/scene/face_layer.h`, `.cpp` | `PersonalityFace` (rest offset, expression bias, mouth while watching) with `personalityFaceOffset` and `resolvePersonalityOffsets` (action units to the character's controls) |
| `engine/scene/clip_layers.cpp` | `layerClipFrame`: tempo of gestures and clip actions (base clips and the auto idle untouched), effective speed kept inside `limits.action_speed`, one-shot clips hold their last frame |

Data and tools:
| File | Purpose |
| --- | --- |
| `content/personality/{boy_yellow_hoodie,girl_auburn_bun_glasses,girl_white_hair_blue_dress}.json` | Promoted from the `.draft.json` files (git mv): `profile_version` 1.0.0 (candidate, path B), `face.rest_offset`, `limits`, owner decisions applied (section 4) |
| `content/personality/shared.json` | Shared action-unit aliases and the neutral idle amplitude (0.004 H) |
| `tools/animcheck/personality.py` | Personality check on a bake: blinks (duration, rhythm interval, double blinks), reaches (entry frames, hold), idle head motion; reported only: peak wrist speed, idle amplitude |
| `tools/animcheck/run_gate.py` | Runs the personality check for every gate shot with profiles; `<out>/personality.json` |
| `tools/animcheck/make_shots.py`, `shots/personality.scene.json` | New gate shot: both packages with profiles, idle + one gesture each |
| `tools/animcheck/tests/test_animcheck.py` | `PersonalityCheck` unit tests (synthetic package and bake) |
| `tests/test_personality.cpp` | 9 doctest cases (section 5) |

Documentation: `content/personality/SCHEMA.md` (reader, scene use, `rest_offset`, `watching_mouth`, `limits`, what the
engine applies), `tools/animcheck/README.md` (personality check), this report, `make_evidence.py`, `shots/{before,after}/shot.scene.json`,
`reports/*.json`, the preview sheets / video.

## 4. What was implemented
**Reader.** Every leaf is a value record (or plain value); missing = neutral (the layer keeps its default). Ranges
`[lo, hi]`, `{mean, min, max}` blink intervals, action-unit weight maps (each in [-1, 1]), name lists. Wrong format,
version, types or inverted ranges are errors (the scene then warns and uses no profile).

**Scene use.** Character `"personality": "<id>"`; absent or `false` = exactly the behaviour before T-053 (no code path
changes: the evaluator only consults `persona_` when a profile resolved). `"personality": true` or a non-string is a
load error.

**Layers** (mapping in `content/personality/SCHEMA.md`):
- life: blink mean interval (frames/24), blink shape from `duration_frames` / `closed_frames` (close : open 40 : 60,
  VISUAL_TARGET), idle amplitude k = `energy.idle_motion_amplitude` / 0.004 H (sway, head drift × k, breathing × √k),
  head lag = `gaze.eyes_lead_head_frames`; an explicit scene `blinkInterval` wins but is clamped into the limits;
- face: rest offset (constant), expression bias × expression activity (max animated expression weight, blink morph
  excluded), mouth while watching × look-action envelope (6 f ramps), all added to the resolved control and clamped
  0..1; the shared face layer's blinks follow the life blink parameters;
- clip layers: tempo for gestures and clip actions, effective speed (scene speed × tempo) clamped into
  `limits.action_speed`;
- body mechanics: unchanged mapping (settle, overshoot, lag from anticipation, energy, gesture, posture).

**Profiles (decisions, all traceable in the files):**
- Boy (calm, low energy, heavy lids, long stares, never abrupt): blink mean 30 f (WT), limits from the measurements;
  `action_speed` limit [0.8, 1.0] (owner decision: no quick or abrupt moves); `hold_frames` [24, 72] (long stares).
  The draft's expression bias `Blink.L/R +0.35`, `BrowDown +0.15`, `MouthFrown +0.15` is **not applied**: the heavy
  upper lid, low brows and pout are modelled in his neutral (REFERENCE_BEHAVIOUR §1 "present even in T-pose"), and a
  lid bias would keep his eyes half shut in surprise / curiosity / concentration, which the references show fully open
  (`#28 r1c4`, `PB S6`); Happy has no frown (`#28 r1c2`). Kept: smaller smiles (`MouthSmile −0.2`, `MouthWide −0.3`).
- Girl (cheerful, intelligent): reaches 8–10 f, cheerful bias as drafted, gestures hand-to-chin and pointing kept;
  `rest_offset` empty: the closed gentle-smile neutral is in girl 0.10.0 (T-055, owner decision), a rest
  `MouthSmile` would exaggerate it. Brown eyes are model data (no profile parameter).
- Third (subtly goofy, bubbly): `mouth_rest` and `smile.default_mouth` = closed soft smile (owner decision, the draft
  said "pending"); `watching_mouth` (JawOpen 0.12, MouthO 0.15) applied while she watches; clasped hands kept in
  `rest_hands` / gestures. No engine package exists yet (V6): her profile is parsed and limit-checked, not animated.
- `face.resting` stays as the reference reading (documentation); the engine applies only `rest_offset` (empty for all
  three: every neutral cue is in the models).

## 5. Tests executed
| Command | Result |
| --- | --- |
| `cmake --build build` (Release, OIDN 2.3.3 pinned prebuilt) | OK, no warnings in changed files |
| `build/tests/plush_tests` | 122 / 122 test cases, 35632 assertions pass (9 new T-053 cases) |
| `ctest` (build/) | 4 / 4 pass (plush_tests, regression_milestone01, regression_face_neutral, regression_lineup_abc). Without OIDN the two frozen image regressions fail here (rmse 0.046 / 0.041): the denoiser was missing in this container, unrelated to T-053; with the pinned OIDN they pass |
| `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render` | PASS: clip_gestures 6 gestures, personality 3 gestures, personality limits 2 characters 0 failures, wave_touch 4 gestures |
| `python3 tools/animcheck/tests/test_animcheck.py` | 8 / 8 pass (4 new) |
| Regression bakes `wave_touch`, `clip_gestures` (plush-render --bake) before / after the change | byte-identical (`cmp`) |
| `python3 tools/check_all.py --base origin/staging --task T-053` | see section 6 |

T-053 doctest cases: shipped profiles parse within their own limits; reader errors / neutral defaults / clamping;
file lookup (draft fallback, no path ids); absent and `false` give identical poses and bakes, `personality` round-trips
through scene files; life parameters (blink 30/24 s, shape 5 f with 2.5 f shut, idle k 0.75 / 1.5, head lag 3 f; 9 vs 3
blinks in 12 s; explicit interval clamped with a warning); face (girl bias +0.2 MouthSmile during an expression, nothing
at rest, bake = evaluator weights; synthetic rest offset, watching mouth with ramps); clip tempo (boy's 1.5 × wave
plays at 1.0 = his limit, girl's 1.0 plays as 1.1); body mechanics via the character profile = via
`bodyMechanics.personality`, own profile wins; reach warnings, unknown profile, self-clamping profile, invalid scene value.

Not tested: the third character in motion (no package); Blender tier locally (section 6).

## 6. Baselines and gate
- Frozen assets, published versions, guarded engine renderer: untouched (gate "Frozen assets" PASS).
- Regression shots `wave_touch` and `clip_gestures` bake byte-identical to `origin/staging` (body mechanics read the
  same values through the shared reader).
- `check_all.py --base origin/staging --task T-053 --build-dir build` (local, build with the pinned OIDN 2.3.3):
  Frozen assets PASS, Write-set PASS (28 paths, all inside the claim), Shared-systems lint PASS, C++ build PASS,
  C++ tests PASS (CTest 4/4 incl. the frozen image regressions, plush_tests, animcheck incl. personality), Python tests
  and links PASS. With the default `build/quality-gate` dir (configured without OIDN in this container) the two
  frozen image regressions fail for lack of the denoiser only (rmse 0.046 / 0.041), unrelated to T-053.
- **Guarded paths: requires Supervisor approval for `tests/test_personality.cpp` and
  `tools/animcheck/tests/test_animcheck.py`** (both inside the claim: the test stub was registered for this task; the
  animcheck tests gain a `PersonalityCheck` class; no existing test changed or loosened; `thresholds.json` untouched).
- **Blender tier: not completed locally.** The gate requires it (content/personality is classed as full regression).
  A local run with the bpy 5.3.0 shim (`tools/bpy_blender.py`) was killed with the session worker (exit 137) before it
  finished; GitHub CI on the branch is the evidence. No character spec, generator, material or exporter changed, so the
  unchanged-character guard is expected to pass.

## 7. Visual results (current approved versions: boy 1.1.0, girl 0.10.0, via run_shot cast "current")
Evidence shot = the gate shot on the current versions (`shots/after`, `shots/before` = same timing, no profiles; both
with life and body mechanics on). Packages exported with bpy 5.3.0 (`tools/bpy_blender.py` shim), baked with the
engine. Renders are engine previews (frozen renderer, look not representative: e.g. the girl's eyes); no Cycles
render was needed to judge timing, posture and blinks.

| Measure (personality check on the bakes) | Boy before → after | Girl before → after | Profile limit (boy / girl) |
| --- | --- | --- | --- |
| blinks in 11 s | 2 → 8 | 4 → 9 (one double blink) | — |
| mean blink interval (f@24) | 119 → 31.4 | 57.3 → 27.9 | [20, 96] / [25, 39] |
| blink duration (f@24) | 4, 4 → 4–5 | 5–6 → 3–4 | [4, 6] / [3, 5] |
| reach entry (f@24) | 12 → 12 | point 14 → 12, touch 9 → 9 | [10, 16] / [8, 10] |
| hold (f@24) | 25 → 24 | touch 10 → 10 (small move, reported) | [24, 72] / [12, 40] |
| idle head speed (H/f, median) | 0.00113 → 0.00112 | 0.00143 → 0.00150 | ≤ 0.004 / ≤ 0.006 |
| idle head amplitude (H, half range; reported) | 0.016 → 0.020 | 0.025 → 0.027 | profile estimate 0.003 / 0.006 |

Before, both characters break their own blink limits (the shared 3.6 s interval); after, everything is inside.
Visible: the boy slouches with his head down toward the task and blinks at his measured rhythm; the girl stands
upright, points a little more briskly (tempo 1.1) and blinks quickly and often. Nothing changes the models. Both
characters watch the top of their task object (look target = the touch point; a first version aimed at the object's
centre near the floor and made both crane down, in before and after alike: fixed before these renders). The girl
still pitches her head steeply to watch her low, close plinth (T-045 staging made for the old test package), equally
before and after: staging, not personality. Posture differences in the stills are small (the boy's slouch and head
pitch were already on via body mechanics in T-045 shots; here "before" has neutral body mechanics); the profiles show
mostly in timing: blinks, the girl's brisker point, the boy's head lag.

Files: `preview_before_after.mp4` (engine preview, side by side, 264 f), `sheet_before_after.jpg` (key frames).

## 8. Problems, limitations and open questions
1. **Face-layer tunables not reachable from the write-set**: saccade interval and look-down bias would need the
   per-character constant face layer, built in `engine/scene/actions.cpp` `buildFaceLayers` (T-047's claim).
   Proposal: a two-line follow-up there (insert the profile's `FaceMotion` like `CharacterDesc::faceMotion`). The
   look-down bias also conflicts with "eye direction within 3° of the target during fine hand work" (VISUAL_TARGET),
   so I did not apply it as an eye offset.
2. **Clip face curves and tempo**: the face layer reads clip face curves at the layer's scene speed (actions.cpp), so
   with tempo ≠ 1 a clip's face curve runs `1/tempo` slower than its body (girl: 10 %). Fixed by the same follow-up.
3. **Reaches are planned by actions.cpp**: reach timing outside the limits is reported (warning + check), not changed.
   The touch planner pops at short plans: a 9–12 f touch gives jerk 0.49–0.77 (> 0.45, T-061) with or without profiles,
   so the girl's 8–10 f reach is only reachable with a 13 f plan (measured entry 9 f). Worth a T-061-style fix.
4. **Reported, not gated**: peak wrist speeds (boy touch 0.068 H/f, girl point 0.115 H/f) exceed the VISUAL_TARGET
   primary-action envelope 0.018–0.045 H/f, and the idle head amplitude (boy 0.020 H, girl 0.027 H half range; before the profiles 0.016 / 0.025 H)
   exceeds the profiles' `idle_motion_amplitude` estimates (0.003 / 0.006 H). Both come from the shared idle/body
   layers and library clips; the profiles have no reference-backed range for them, so I did not invent limits.
5. Read but not applied (no engine layer yet): attention, boredom / fidgets, saccades, smile choice, gestures,
   reaction, interaction. The boy's fidgets need a behaviour layer (owner decision: small and slow).
6. Stale text mentions of `*.draft.json` remain in docs outside the write-set (`docs/characters/REVIEW_CHECKLIST.md`,
   `docs/characters/girl_white_hair_blue_dress/SYSTEM_GAPS.md`, task files): for the Supervisor.
7. The blink check counts a blink within 10 f of the previous one as a double blink (shared T-046 feature, one rhythm
   event); per-blink durations are still checked.

## 9. Commits
Branch `t-053-claude-personality` (see `git log origin/staging..`).

## 10. Resource use
Token usage: not available. Repeated work: the gate shot timing was iterated (touch planner pops at short plans),
and preview frames were restarted once at lower settings.
