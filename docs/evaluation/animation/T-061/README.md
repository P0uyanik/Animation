# T-061: animation principles pass (slow-in / slow-out, arcs, spacing metrics, accessory chains)

Branch `t-061-claude-animation-principles` (from `origin/staging`; staging merged before the gate). Implementer report.

## 1. Task and objective
Shared, data-driven fix for the external critique of the T-045 wave (constant-speed lift from a 4-frame blend at
clip speed 1.5, near-linear hand paths, static accessories), plus a gate tool that measures it.

## 2. Result: complete (AC1–AC5), with the limits in §8
- AC1 slow-in / slow-out that survives blending and retiming (clip layers and the IK gestures): implemented, tested.
- AC2 arcs (successive breaking in joint space, automatic breakdowns, contacts ≤ 5 mm): implemented, tested.
- AC3 `tools/animcheck/` (speed profile, ease ratios, arcs, steps, overshoot / settle) in the gate with justified
  thresholds: implemented; old engine 19 failures, new engine 0 on the regression shots.
- AC4 accessory spring chains through data (presets, attach by bone name), documented for T-044 / T-058
  ([ACCESSORY_CHAINS.md](ACCESSORY_CHAINS.md)): implemented and tested on the toy fixture; no shot shows it yet
  (no package has accessory bones; the exporter does not yet pass `attach` through, see there).
- AC5 evidence: the T-045 shot (layer on) before / after with the current versions (boy 1.1.0, girl 0.10.0), speed
  and wrist-path plots. Render budget **exceeded** (≈ 4.5 renders, §7).
- **On by default.** Every clip action and IK gesture of every shot now uses the principles; scene
  `"animPrinciples": false` restores the old behaviour bit for bit (verified on the evidence shot's bake). All 104
  existing test cases and the 4 CTest regressions pass unchanged.

## 3. Files changed
| File | Purpose |
| --- | --- |
| `engine/anim/principles.h`, `.cpp` (new) | Settings (`AnimPrinciples`, scene JSON), quintic ease and eased clock, amplitude → blend length, succession ranks, movement-based ease-preserving time warp, elbow-opening breakdown, arc measure |
| `engine/anim/animation.h`, `.cpp` | Two-bone IK with a separate elbow weight; optional `ik.<bone>.lag` track (absent = identical) |
| `engine/anim/secondary.h`, `.cpp` | Spring presets (built-in + data), `preset` on chains, `attach` entries resolved against the skeleton, scene `attach` |
| `engine/scene/scene.h`, `scene.cpp` | Scene field `animPrinciples` (validated, saved as written); clip-layer fields; accessory chain resolution at load; `clipLayerPlans()` (read only) |
| `engine/scene/clip_layers.cpp` | Per-rank eased envelopes, eased clock, warp, breakdowns, plans |
| `engine/scene/actions.cpp` | Clip actions: amplitude-based blends, warp, eased clock, breakdown search; touch / reach: eased weight ramps, earlier start for big moves, elbow lag / lead |
| `engine/CMakeLists.txt`, `tests/CMakeLists.txt` | New source and test files |
| `tests/test_anim_principles.cpp` (new) | 8 test cases (§5) |
| `tools/animcheck/` (new) | `animcheck.py`, `run_gate.py`, `make_shots.py`, `shots/*.scene.json`, `thresholds.json`, `tests/test_animcheck.py`, `README.md` |
| `tools/check_all.py` | Gate hook: sub-check `animcheck` on the "C++ tests" line; animcheck unit tests in the Python tests |
| `tools/regression_paths.txt` | `full tools/animcheck/**` |

Documentation and evidence (this folder): `README.md`, `ACCESSORY_CHAINS.md`, `make_shot.py` (writes
`shot_before/`, `shot_after/`), `plot_curves.py`, `make_media.py`, `speed_profiles.png`, `wrist_paths.png`,
`curves_summary.json`, `t061_before_after.mp4`, `before_after_sheet.jpg`. Not changed: `engine/scene/interaction.*`,
`face_layer.*`, `emotion.*` (no hook needed), pipeline, specs, clips (`content/clips/**` untouched), `.github`, frozen files.

## 4. What was implemented
All shared and data driven: role names of the clip system only, numbers in `AnimPrinciples` (scene-overridable).

**Slow-in / slow-out that survives blending (AC1).** Clip-action layers (tier 2; base clips and emotion layers keep
their ramps):
- Ramps use the quintic ease (zero velocity *and* acceleration at both ends).
- **Minimum blend from the amplitude**: at compile time the largest global rotation change of a driven bone between
  the pose without the layer and with it at full weight (at the start, and at the end) gives
  `T = 1.875 A / 150 °/s`, clamped to 0.35–0.8 s; blend = max(authored, T). The lengthened blends take at most half
  of a finite layer (a short clip keeps a full-weight part). An authored 0 stays a cut.
- **Eased clock**: where the clip itself is moving at its first / last frames (a clip cut mid-motion), its clock
  accelerates from 0 with the blend in and decelerates to 0 with the blend out (layer length kept; middle at most
  1.25× faster; skipped when the ramps exceed 40 % of the layer). The library clips start and end at rest, so this
  applied to none of the evidence gestures; it is covered by the unit tests.
- **Ease-preserving retiming** (`speed` ≠ 1): the clip is split into its movements at the motion minima (reversals,
  holds); each movement gets one constant rate from its peak motion (`1 + a·w`, solved so the total length equals
  the linear one, local rate ≤ 1.15× the request). Big actions absorb the change, anticipations, settles and holds
  keep their authored spacing, every movement keeps its own ease shape, and rates change only where the motion is at
  a minimum. (A first version that varied the rate frame by frame sharpened the anticipation → lift transition on the
  boy's production rig: onset 0.22; replaced.)
- **IK gestures** (`touch`, `reach` with an object; `actions.cpp`): weight ramps are dense quintic keys; when the arm's
  rotation needs a longer ramp in than authored, the ramp starts earlier (at most +50 % of the authored ramp, never
  before the hand's previous IK keys or the shot start); contact frames are unchanged.

**Arcs (AC2).**
- **Successive breaking**: each succession rank (trunk / clavicle 0, upper arm / thigh / neck 1, forearm / shin /
  head 2, hand / foot 3, fingers 4) starts its blend in 0.06 s after the previous one and trails its blend out by the
  same, in joint space (the shoulder leads, elbow and wrist follow; fingers last).
- **IK**: the elbow's IK weight trails the shoulder's by 0.1 s on the way in and leads it on the way out
  (`ik.<hand>.lag` track, Step keys); both reach full weight / zero at the authored frames. Out: the elbow opens first
  and the hand swings back round the shoulder instead of dropping down its incoming line.
- **Breakdowns**: for each clip blend whose wrist path deviates less than 0.10 of its chord (chord ≥ 5 cm), the
  planner tries opening and further bending the elbow mid-blend (`4x(1−x)` bump on the forearm's rank, ≤ 35°), keeps
  the direction that curves the path more and bisects the smallest angle reaching 0.10. On the evidence and
  regression shots no blend needed one (succession already curves them); the unit test forces it with `minArc 0.6`
  (girl: −35°, arc 0.225 → 0.249; boy: no direction helps, left unchanged).
- Interaction contacts: touch fingertip on target ≤ 5 mm with and without the principles; reach grip within 5 mm of
  the old one at contact and placement (test §5); `interaction.*` untouched.

Planning measurements use the pose with the automatic base idle present (temporarily prepared if the first compile
has not built it yet), so a first load and a recompile plan the same blends.

**Measurable (AC3).** `tools/animcheck` (metrics and thresholds: [tools/animcheck/README.md](../../../../tools/animcheck/README.md)).
Gate: `run_gate.py` bakes `tools/animcheck/shots/{wave_touch,clip_gestures}.scene.json` (engine test packages, the
T-045 shot and library clips at ×1, ×1.5 mirrored, ×0.8) with `plush-render --bake` and checks them (~2 s).

| Threshold (guarded, never loosened) | Value |
| --- | --- |
| `max_ease_ratio` (first / last 20 % mean ÷ peak) | 0.55 |
| `max_first_step` (onset / stop frame ÷ peak) | 0.18 |
| `max_jerk` (largest frame-to-frame speed change ÷ peak) | 0.45 |
| `min_arc` / `min_arc_screen` (deviation ÷ chord, 3D / camera) | 0.10 / 0.10 |
| `max_step_mm` / `max_rot_step_deg` (per frame) | 130 / 45 |

(Applied to segments with a chord ≥ 100 mm.) Justifications in the tool README.

**Accessory secondary motion (AC4).** Built-in presets `drawstring`, `strap`, `bow_tail`, `tassel`; package or scene
`presets` override them; chains may name a `preset`; `attach` entries create chains from bones found by name prefix
(`<p><n>`, `<p>.<n>`, `<p>_<n>`, numeric order) or listed, with a default tip; the T-021 solver is unchanged.

**Assumptions.** (1) "On by default" (the task asks for the behaviour, not an option); `false` keeps the old one.
(2) The ramp out of an IK gesture keeps its authored length (the next action may own the arm right after it).
(3) Clip face curves keep the linear clock (face_layer is outside the write-set): with retiming, face curves of a
clip can be up to ~2 frames off the warped body timing (none of the evidence clips has face curves that matter).

## 5. Tests executed
- `build/tests/plush_tests`: **112 / 112 test cases pass** (104 existing unchanged + 8 new), 34 750+ assertions.
  `ctest`: **4 / 4 pass** (three image regressions unchanged). OIDN 2.3.3.
- `tests/test_anim_principles.cpp` (boy 1.0.0, girl m3, toy fixture, synthetic skeletons):
  | Test | Key numbers |
  | --- | --- |
  | ease, eased clock, blend length, ranks, settings validation | quintic peak slope 1.875; clock covers the layer, zero rate at the ends |
  | ease-preserving retiming | ×1.5: a 6-frame hold keeps 4.2 of its 4.8 frames (linear: 3.2); constant rate inside a movement; same total length; loops |
  | wave ×1.5, blendIn 4 (both characters) | wrist speed over the first 4 frames ÷ peak: boy 0.022 (off 0.39), girl 0.023 (off 0.27); monotonic acceleration; base pose back after |
  | successive breaking | frame 27: upperArm 0.37 / forearm 0.19 / hand 0.06 of their blend (girl 0.42 / 0.22 / 0.08) |
  | breakdowns | forced: applied on the girl (−35°), arc up; unchanged outside blends |
  | IK gestures | fingertip at contact ≤ 5 mm (on and off); elbow trails (frame 22: upperArm 0.38–0.45, forearm 0.19–0.27); reach grip within 5 mm of the old one |
  | off / saved setting | `false` = `{"enabled": false}`; round trip; invalid values fail the load |
  | accessory chains | prefix resolution (numeric order, tip), presets, errors; toy tail attached from the scene lags ≤ 77 mm and settles < 2 mm by 3 s; `"enabled": false` = kinematic |
- `python3 tools/animcheck/tests/test_animcheck.py`: 4 / 4 (constant-speed straight move fails, eased arc passes).
- `python3 tools/animcheck/run_gate.py --render build/apps/render-cli/plush-render`: both shots PASS.
- Full gate (`tools/check_all.py --base origin/main --task T-061 --blender <bpy 5.3 wrapper>`): §5a.
- Blender used: **bpy 5.3.0 module** (Python 3.13) through `tools/bpy_blender.py`; no Blender binary available.
- Not tested: walking shots with clip layers retimed; emotion layers (unchanged by design); a real garment with
  accessory bones (none exists yet); the exporter path for `attach`.

### 5a. Gate
Local (`python3 tools/check_all.py --base origin/main --task T-061 --blender <bpy 5.3 wrapper>`, after merging
`origin/staging`): Frozen assets, Write-set, lint, C++ build, C++ tests (CTest 4/4, plush_tests 112/112, animcheck
2/2 shots), Python tests and links all PASS; the Blender tier (verify_charsys, determinism, export, face, groom ran
and passed) did not finish locally: the session's worker restarted during the all-character regression (twice in
this session), so the full tier is taken from CI.

CI (GitHub "Quality gate", full tier, trial merge into staging), run 44193932269 on `ce37520` (staging merged):
**every check PASS except Guarded paths** (and "Merge status", which only reports that a line failed): C++ build,
C++ tests (incl. animcheck), Python tests and links, Blender tier with the regression jobs boy PASS (fidelity 66.41),
girl PASS (64.40), white-haired girl PASS. **Gate verdict: red only because of the guarded-path trailer**
(`Supervisor-Approved: <path>`), which an Implementer cannot add: Supervisor action needed for the six paths below.
On the first push (run 44183710969) every check passed except (a) **Guarded paths** (the Supervisor trailer an Implementer
cannot give: `tests/CMakeLists.txt`, `tests/test_anim_principles.cpp`, `tools/animcheck/tests/test_animcheck.py`,
`tools/animcheck/thresholds.json`, `tools/check_all.py`, `tools/regression_paths.txt`) and (b) the T-062 cast check
in the Python tests, which flagged my evidence shots for pinning old versions — fixed by the current-version casts
(locally `test_run_shot_current.py` PASS). Regression jobs: boy PASS (fidelity 64.07), girl PASS (65.46),
white-haired girl PASS (references only).

## 6. Baselines
No frozen file, package, clip, spec or test data was edited. The existing 104 test cases and the 4 CTest regressions
(including the frozen image regressions) pass unchanged; `"animPrinciples": false` gives the old bake bit for bit
(checked on the T-045 shot: every bone matrix of all 132 frames equal). Character builds, fingerprints and exports are
not affected by engine animation code (gate: Blender tier, §5a).

## 7. Visual results
Shot: the T-045 evidence shot, body mechanics on, unchanged except the cast (`make_shot.py`): `shot_before` =
`"animPrinciples": false`, `shot_after` = defaults. Cast: the **current approved versions** (`run_shot` cast
`"current"`, owner decision 2026-11-17): boy **1.1.0**, girl **0.10.0** (`cast.json` of both builds). Cycles 16
samples + OIDN, **480×270** (lower than T-045's 640×360 to save time), 132 frames, `run_shot.py` in chunks of
16–40 frames (the session's worker restarted twice during rendering; finished chunks were kept). Every rendered frame
was checked against a full-length bake of the final engine: all bone matrices equal.

**Render budget exceeded.** Used ≈ 4.5 renders instead of 2: a first before/after pair with the T-045 cast (boy
1.0.0, girl spec without overrides), a re-render of 66 "after" frames after the final retiming change, and then the
before/after pair again with the current versions once the Supervisor note about current versions reached this
session (it was sent before the first render but delivered only afterwards). Only the current-version renders are
used here; the arm motion metrics of both casts are identical (`curves_summary.json` unchanged).
- `t061_before_after.mp4`: before | after, 24 fps.
- `before_after_sheet.jpg`: touch (f22–34), wave lift (f66–75) and lowering (f104–112), before over after.
- `speed_profiles.png`, `wrist_paths.png`, `curves_summary.json`: from the engine bakes of both shots.

What changed (current versions, `curves_summary.json`):
- **Wave lift (×1.5):** before, the 4-frame blend gives a burst then a dip before the clip's own lift (13 → 12 → 36
  mm/frame); after, one movement: slow start (1–3 mm/frame), fast middle (peak 88 vs 71 mm/frame: the retime puts the
  speed-up into the lift and keeps the anticipation's spacing), cushioned arrival. Boy ease-in 0.12 → 0.04.
- **Touch:** starts 3–4 frames earlier and gentler; the hand now goes out on one arc and comes back on another (camera
  view arc boy 0.10 → 0.36 / 0.41, girl 0.08 / 0.15 → 0.25 / 0.43; 3D girl entry 0.08 → 0.17). The return is quicker
  (boy peak 15 → 25 mm/frame) because the out ramp keeps its authored length while the elbow leads.
- Poses, contacts and timing of the holds are unchanged; nothing else in the shot moves differently.

Regression shots (test packages, gate): before → after, **19 → 0 threshold failures**:

| Shot · gesture | ease in / out | onset / stop step | jerk | arc 3D in / out | arc screen in / out | max step mm / ° |
| --- | --- | --- | --- | --- | --- | --- |
| `wave_touch` · boy touch @24 | 0.36 / 0.45 → **0.07 / 0.04** | 0.19 / 0.18 → **0.04 / 0.02** | 0.33 → **0.35** | 0.21 / 0.21 → **0.18 / 0.22** | 0.05 / 0.09 → **0.14 / 0.28** | 26 / 14 → **32 / 17** |
| `wave_touch` · boy clip wave @66 x1.5 | 0.44 / 0.13 → **0.07 / 0.12** | 0.23 / 0.03 → **0.04 / 0.05** | 0.35 → **0.35** | 0.32 / 0.35 → **0.28 / 0.35** | 0.27 / 0.14 → **0.14 / 0.14** | 69 / 22 → **87 / 29** |
| `wave_touch` · girl touch @28 | 0.40 / 0.09 → **0.15 / 0.11** | 0.22 / 0.06 → **0.09 / 0.08** | 0.36 → **0.34** | 0.14 / 0.18 → **0.20 / 0.22** | 0.25 / 0.30 → **0.45 / 0.51** | 22 / 12 → **21 / 14** |
| `wave_touch` · girl clip wave @70 x1.5 | 0.28 / 0.08 → **0.05 / 0.07** | 0.14 / 0.02 → **0.02 / 0.03** | 0.31 → **0.34** | 0.37 / 0.39 → **0.36 / 0.39** | 0.27 / 0.29 → **0.30 / 0.29** | 72 / 30 → **97 / 40** |
| `clip_gestures` · boy clip point @6 | 0.28 / 0.60 → **0.12 / 0.31** | 0.28 / 0.04 → **0.03 / 0.05** | 0.51 → **0.20** | 0.09 / 0.35 → **0.22 / 0.29** | 0.09 / 0.57 → **0.30 / 0.40** | 41 / 12 → **49 / 13** |
| `clip_gestures` · boy clip wave @100 x1.5 | 0.26 / 0.20 → **0.07 / 0.07** | 0.11 / 0.04 → **0.06 / 0.03** | 0.31 → **0.40** | 0.38 / 0.41 → **0.35 / 0.42** | 0.25 / 0.28 → **0.27 / 0.27** | 93 / 29 → **116 / 37** |
| `clip_gestures` · boy clip gest_shrug @176 x0.8 | 0.31 / 0.31 → **0.32 / 0.48** | 0.31 / 0.31 → **0.07 / 0.08** | 0.51 → **0.22** | 0.07 / 0.08 → **0.56 / 0.63** | 0.08 / 0.07 → **0.81 / 1.10** | 32 / 11 → **25 / 11** |
| `clip_gestures` · girl clip point @9 | 0.39 / 0.28 → **0.19 / 0.36** | 0.15 / 0.03 → **0.06 / 0.07** | 0.35 → **0.23** | 0.23 / 0.21 → **0.17 / 0.21** | 0.33 / 0.19 → **0.20 / 0.17** | 32 / 12 → **32 / 12** |
| `clip_gestures` · girl clip wave @103 x1.5 | 0.17 / 0.06 → **0.05 / 0.07** | 0.07 / 0.02 → **0.02 / 0.03** | 0.31 → **0.34** | 0.37 / 0.40 → **0.35 / 0.39** | 0.23 / 0.25 → **0.27 / 0.25** | 72 / 29 → **96 / 40** |
| `clip_gestures` · girl clip gest_shrug @179 x0.8 | 0.30 / 0.31 → **0.45 / 0.42** | 0.30 / 0.31 → **0.13 / 0.06** | 0.53 → **0.24** | 0.05 / 0.05 → **0.39 / 0.44** | 0.04 / 0.04 → **0.51 / 0.59** | 17 / 11 → **17 / 10** |

Production evidence shot (no threshold fails before or after: there the auto idle starts with the arms down, so the
old 4-frame blend has less to cover than on the A-posed test packages):

| Gesture (current versions) | ease in / out | onset / stop step | jerk | arc 3D in / out | arc screen in / out | max step mm / ° |
| --- | --- | --- | --- | --- | --- | --- |
| boy touch @24 | 0.11 / 0.07 → **0.12 / 0.05** | 0.02 / 0.06 → **0.03 / 0.04** | 0.38 → **0.37** | 0.19 / 0.20 → **0.32 / 0.35** | 0.10 / 0.10 → **0.36 / 0.41** | 21 / 10 → **25 / 13** |
| boy clip wave @66 x1.5 | 0.12 / 0.07 → **0.04 / 0.25** | 0.04 / 0.03 → **0.03 / 0.06** | 0.35 → **0.37** | 0.28 / 0.31 → **0.27 / 0.30** | 0.18 / 0.20 → **0.19 / 0.20** | 71 / 23 → **88 / 28** |
| girl touch @28 | 0.14 / 0.07 → **0.03 / 0.07** | 0.03 / 0.05 → **0.03 / 0.06** | 0.37 → **0.31** | 0.08 / 0.16 → **0.17 / 0.29** | 0.08 / 0.15 → **0.25 / 0.43** | 16 / 8 → **17 / 11** |
| girl clip wave @70 x1.5 | 0.17 / 0.15 → **0.16 / 0.27** | 0.17 / 0.04 → **0.05 / 0.08** | 0.33 → **0.35** | 0.39 / 0.42 → **0.37 / 0.41** | 0.34 / 0.38 → **0.34 / 0.37** | 78 / 32 → **96 / 39** |

**Against the references.** The references show no wave or touch timing (`REFERENCE_BEHAVIOUR.md`: holds, the
girl's slow, even boat placement); key poses are unchanged, so the identity and poses of both characters stay as
before. The changes are spacing and arcs only, in line with "cheerful" (girl) and "impatient" (boy, quicker return).
The faster wave middle (up to 116 mm / 40° per frame at ×1.5 on the test packages) is within the strobe guards but
is the most visible change; `retimeMaxRate` / `easePreservingRetime` tune or switch it per shot.

## 8. Problems, limitations, open questions
1. **On by default** changes the motion of every existing shot with clip actions or touch / reach (intended by the
   task). Supervisor / owner: confirm, or switch it to opt-in (one default in `AnimPrinciples`).
2. **Render budget exceeded** (≈ 4.5 renders, §7).
8. The animcheck gate shots use the engine test packages (boy 1.0.0, girl m3: the only committed packages, so the
   check stays engine-only and runs in seconds); the evidence uses the current versions. The T-062 evaluation shots
   (`content/scenes/eval/*`, current casts) could also be checked with animcheck in the Blender tier from their bakes
   (not wired in this task: their casts need a Blender build).
3. **Exporter**: `attach` / `presets` are not passed through by `export_engine.py` (pipeline, outside this task);
   chains with `"preset"` are. Proposal in [ACCESSORY_CHAINS.md](ACCESSORY_CHAINS.md) for T-058 / T-044.
4. **Girl Blender reconstruction offset** seen in every render run (before and after alike, both casts, i.e.
   pre-existing): `shot_render` reports `max_bone_error_mm` 11–19 mm (0° rotation) for the girl in chunks with a mid-gesture check
   frame, 0.001 mm at rest. Translation only: probably the T-045 pivot carry on a connected bone in Blender. Not
   investigated (outside the write-set); worth a look by the T-045 / shot_render owner.
5. Face curves of retimed clips follow the linear clock (≤ ~2 frames off), §4.
6. Breakdowns did not trigger on any real shot (succession already curves the paths); they are exercised only with a
   raised `minArc`.
7. The thresholds are calibrated on two characters and five library clips; a new clip that fails them must be fixed
   (clip or engine), not the thresholds.

## 9. Commits and branch
Branch `t-061-claude-animation-principles`; head commit in the relay line (`RELAY_LOG.md`, branch `relay-channel`).

## 10. Resource use
Token usage: not available. Compute: ≈ 130 min of Cycles rendering (≈ 4.5 renders, §7), gate runs (local partial,
CI full), many engine-only bakes (seconds each). Repeated work: the partial after re-render and the re-render with the
current versions (§7).
