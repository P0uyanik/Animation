# T-046: facial animation (living faces)

Branch `t-046-claude-facial-animation` (from `origin/staging`, staging merged before the gate). Implementer report.

## 1. Task and objective
Owner feedback "faces are static": a shared, data-driven engine facial layer drives the face controls exported
today (morphs, lid bones, eye bones) from emotions, looks and clips. It adds blinks with variety, eye darts and gaze
holds, brow raises on attention, brows and mouth corners that follow the emotion, and breathing-linked face motion.
The task also fixes the open gaze test.

## 2. Result: complete (all five acceptance criteria), with two documented caveats
- AC1–AC4 are implemented and tested. AC3 (`look_keeps_gaze`) is fixed: 3.94° → 0.0004° with these packages; its
  0.5° limit is unchanged.
- AC5: a 5 s Cycles render of both characters (idle → happy → surprised → sad), a face contact sheet and a
  comparison with the reference faces. **Caveat:** two fixes came after the render (budget: two renders used, see §7).
  - The girl's blink at frames 95–96 does not close her eyes in the render. Fixed afterwards (blinkClears).
  - The "sad, looks down" target was made gentler afterwards.
  - Both fixes are verified without rendering: Blender ray casts and an engine preview.
- Gate: everything passes except **Guarded paths**. It needs Supervisor trailers for `tests/CMakeLists.txt`,
  `tests/test_emotions.cpp` and `tests/test_face_layer.cpp` (expected for an Implementer, see §5).

## 3. Files changed
Engine / data / tests (all in the task's write-set):
| File | Purpose |
| --- | --- |
| `engine/scene/face_layer.h`, `.cpp` (new) | The facial layer: face library, `faceMotion` parsing, envelopes, clip face curves, blink / saccade / channel evaluation |
| `engine/scene/scene.h`, `scene.cpp` | Applies the face state: morph weights (evaluate, bake), lid blink, eye offsets, expression bones; life `face` switch; gaze assist settings; per-character `faceMotion` |
| `engine/scene/actions.cpp` | Gathers face events (looks, emotions with their final crossfaded envelopes, clip layers) and builds one layer per character; loads `content/emotions/face_motion.json` |
| `engine/scene/emotion.h`, `.cpp` | Optional `faceMotion` section of `plush.emotion/1` (variants patch it like the rest) |
| `engine/anim/animation.h`, `.cpp` | Gaze fix: neck/chest assist in `applyConstraints`; shared `breathSignal`, `lifeHash01`, `applyLidBlink` (the life layer uses them, unchanged output) |
| `engine/CMakeLists.txt`, `tests/CMakeLists.txt` | New source and test files |
| `content/emotions/face_motion.json` (new) | Shared face library: channels → candidate controls, `blinkClears`, neutral tunables |
| `content/emotions/*.emotion.json` (8) | New `faceMotion` sections (and in the `laugh` and `cry` variants) |
| `content/clips/gest_yawn`, `gest_shrug`, `wave` `.clip.json` | New optional `face` blocks (channel curves) |
| `tests/test_face_layer.cpp` (new) | 11 test cases (§5) |
| `tests/test_emotions.cpp` | The library test now reads only `*.emotion.json` files: the folder also holds `face_motion.json`. The `n == 8` check and every assertion are unchanged |

Documentation and evidence: this README; `t046_render_cycles.mp4`, `face_contact_sheet.jpg`, `face_curves.jpg`,
`reference_vs_render_f40.jpg`, `shot/shot.scene.json` (evidence shot), `make_sheet.py`, `plot_bake.py`.

## 4. What was implemented
**Facial layer** (`scene/face_layer.h`). Active while a character's life layer is on; scene life `"face": false`
turns it off. Everything is a function of frame and seed (random access, deterministic). The engine contains no
character names.
- **Channels → controls.** `face_motion.json` maps channels (`browUp`, `browDown`, `browSad`, `eyeWide`,
  `eyeSquint`, `jawOpen`, `mouthUp`, `mouthDown`) to ordered candidates. Names resolve through the character's
  expression map, else as morph names. The first candidate the character has wins (e.g. `browUp` → `BrowUp.L` +
  `BrowUp.R` on the girl). A character without the control skips the channel silently (the boy has no brow-up or
  mouth-corner controls).
- **Emotion → face.** The emotion's existing face mix keeps its smoothstep onset/release and crossfades (no pops).
  The new `faceMotion` section blends, with the same final envelope, the blink rate, double-blink chance, blink
  duration, saccade rate and amplitude, long-hold chance, gaze bias, attention pulse, breath, micro motion and
  channel weights. Sad looks down 9°; surprised lifts the brows and widens the eyes; afraid darts fast.
- **Blinks.** The life layer's jittered schedule runs on an emotion-warped clock. Surprised blinks about 6× less
  than afraid: 5 vs 29 blinks in 59 s. Added: double blinks (neutral 12 %), blink length per emotion (sleepy:
  slow, heavy) and gaze-shift blinks when a look starts (50 %; never for the look a shot opens with). With neutral
  data the layer reproduces the old `blinkAmount` schedule exactly; double blinks only add.
- **blinkClears.** Controls that open the eyes (`eyeWide`, `surprised`, `WideOpen`) fade to 0 while the lids close.
  On the girl, Blink plus Surprise or EyeWide left the lid behind the eyeball (found in the render, §7).
- **Saccades and gaze holds.** Darts every ~0.9 s with holds of 0.4–1.6× (25 % long holds of 2.5×). About 35 %
  return to the fixation point; neutral amplitude ≤ 1.6°. Each dart takes ~45 ms + 2.5 ms/° (main sequence). They
  are added to the look aim on all `eye.*` bones, plus the emotion's gaze bias.
- **Attention.** Each look start (0.3) and emotion onset with `attention` (surprised 1.0, curious 0.7, afraid 0.6,
  happy 0.4) gives a brow raise and eye widening. Shape: rise 0.25 s, hold 0.35 s, settle 0.9 s.
- **Breath and micro motion.** The jaw opens up to 0.025 at the top of each inhale, on the same breath cycle the
  chest uses. Mouth corners (±0.045) and brows (0.04) drift on slow, incommensurate waves.
- **Clip face curves.** Clips may carry `"face": {"tracks": {channel: [[clipFrame, value]...]}}`. They play with
  the clip layer's envelope (base, emotion posture or gesture, clip action).
- **Per character.** A scene character may carry `"faceMotion"` (same schema), a constant layer under the
  emotions: a hook for the personality profiles of T-053a (e.g. "boy: long stares"). It is saved and loaded with the
  scene.
- **Mannequin.** The engine-built SDF character has no morphs: its lid bones blink with the layer's blink
  (`applyLidBlink`) and its eyes dart.

**Gaze fix (AC3).** When the look target lies beyond the eyes' comfortable range (the soft limit's onset):
- The neck turns by the excess, up to 70° yaw and 35° pitch; beyond that the chest twists, up to 35° yaw.
- This is done in `applyConstraints` before the eyes are aimed, so where the eyes end up no longer depends on an
  emotion posture bowing the head.
- The assist follows the target 0.2 s later, averaged like the life layer's head follow, so the eyes still lead.
- A hand-keyed neck is left alone.
- The settings are part of `GazeLimits` (scene life `gaze`: `assistYawDeg`, `assistPitchDeg`, `assistBodyYawDeg`,
  `assistLagSec`).
- It changes behaviour only where the eyes had hit their limit. T-027 had listed "eyes sit at the 30° limit in
  e906" as an issue.

**Decisions and assumptions** (documented, not asked):
1. The new emotion section is named `faceMotion`, not `face`, because `face` already holds the expression mix. Code
   and tools read it.
2. The layer is part of the living face, so it runs only with life on. With life off, morph weights are exactly the
   animated ones. This keeps `test_emotions.py` AC2/AC3/AC6 and every image regression unchanged; none of the
   regression scenes has life.
3. Missing face channels produce no warnings (they are optional by design). Unreadable data does warn.
4. Clip face blocks were written into the clip JSON directly. `pipeline/clips/make_clips.py` (outside the
   write-set) does not know them yet, so regenerating those three clips would drop the blocks (follow-up below).

## 5. Tests executed
| Command | Result |
| --- | --- |
| `cmake --build build` (OIDN 2.3.3 from the pinned release, `PLUSH_OIDN_ROOT`) | builds, no new warnings |
| `build/tests/plush_tests` | **89 / 89 test cases, 0 failed** (78 before + 11 new) |
| `ctest` (build/) | **4 / 4** (plush_tests + 3 frozen image regressions) |
| `python3 pipeline/clips/test_emotions.py --boy <e906 boy pkg> --girl <e906 girl pkg> --out build/t046/emo_face` | AC2, AC3, AC4, AC6 PASS; AC5 `look_keeps_gaze` **0.00036°** (was 3.94° on the same staging and packages; T-027 reported 3.43°) PASS; `hand_keyed_head_wins` 0.0° PASS; AC5 overall still FAIL because of `boy_reach_keeps_hand` 0.056 m, **identical on untouched staging** (reach/interaction, not in this task, see §8) |
| `PLUSH_OIDN_ROOT=… python3 tools/check_all.py --base origin/main` | PASS: frozen assets, shared-systems lint, C++ build, CTest, plush_tests, Python tests, doc links, Blender tier. FAIL: guarded paths (Supervisor trailers, see below) |
| `… check_all.py --base origin/main --blender <bpy 5.3 wrapper>` | see §5.1 |

New test cases (`tests/test_face_layer.cpp`), both imported characters (`girl_auburn_bun_glasses_m3`,
`boy_yellow_hoodie_1.0.0`) and the engine-built mannequin (`boy_dark_hair` SDF):
- **Continuity per control** over idle → happy → surprised (+ look) → sad, 260 frames:
  - Max change per frame: girl 0.124, boy 0.124, mannequin 0.124 (limit 0.15).
  - Blink and blink-cleared controls: ≤ 0.53/frame (limit 0.8).
  - Eye bones: ≤ 1.9°/frame, except the look's own jump.
  - All weights stay in [0, 1].
- **Blink statistics (2 min neutral):**
  - Girl: 38 blinks, mean interval 3.38 s (her package says 3.2 s), CV 0.23, 3 double blinks.
  - Boy: 34 blinks, 3.81 s (3.6 s), CV 0.21, 3 double blinks.
  - Deterministic; never below the old schedule.
  - Emotion rate: surprised 5 vs afraid 29 blinks in 59 s.
- **Emotion transitions** (girl):
  - BrowUp: idle 0.02 → happy 0.35 → surprised 0.77.
  - BrowSad: 0 → sad 0.60. MouthFrown: 0.007 → sad 0.35.
  - Eye pitch: 0° → sad −8.7°.
- **Eye darts:** 25 holds in 30 s, 12–103 frames, max offset 1.6°.
- **Skipped controls (boy):** no brow-up or mouth controls (skipped, no warning); the eyes still move. Life off:
  weights are exactly the animated ones. `face:false`: the original blink.
- **Mannequin:** lid bones close by 52°.
- **Clip face curve:** wave → MouthSmile +0.25 during the clip, 0 after.
- **blinkClears:** at every fully closed frame during surprise, EyeWide and Surprise are below 0.001.
- **Per-character faceMotion:** blinkRate 2 → 38 vs 18 blinks per minute. It is saved, and malformed data warns.
- **Gaze assist** (unit skeleton): aim error 0° with the assist vs > 40° without. The eyes lead (neck < 1° two
  frames after the jump, > 20° later). A keyed neck is untouched.

### 5.1 Gate with the Blender tier
`PLUSH_OIDN_ROOT=… python3 tools/check_all.py --base origin/main --blender <wrapper>`. Blender: the **bpy 5.3.0
module** (Python 3.13) behind a small `blender -b … -P script -- args` wrapper (no Blender binary here).
- First run: everything PASS except guarded paths and `test_export_engine` 11/13. Its two failing checks expect
  the exporter's error text, which the first wrapper did not print for `SystemExit("message")`.
- After fixing the wrapper (outside the repository): `test_export_engine` **13/13 ALL PASS**.
- **Final gate** on the merged commit (staging merged again): every check PASS, including the full Blender tier,
  except **Guarded paths** (Supervisor trailers).
- verify_charsys, determinism, face, groom, hair, garment and material-preset subchecks: PASS.

## 6. Baselines
- Frozen assets: gate check **PASS** (`tools/frozen_manifest.txt`). No asset, spec, package, master or published
  version was touched.
- Image regressions `regression_milestone01`, `regression_face_neutral`, `regression_lineup_abc`: **PASS**
  (RMSE limit 0.03, unchanged). Their scenes have no life layer.
- Existing doctest cases: all 78 still pass (blink-morph, per-character blink timing, the life head-follow lag,
  shot bake = evaluate, look-at limit tests…).

## 7. Visual results
- **Render** `t046_render_cycles.mp4`:
  - Settings: Cycles, 640×360, 16 samples, denoised; frames 1–150 at 30 fps (5 s); 15.8 s/frame on 4 CPU cores.
  - Camera: both characters, head and shoulders.
  - Beats: idle 1–19, happy 20–, surprised 66– (both look up-left: attention), sad 102– (look down).
  - Render budget: two renders. A 6-frame test (it revealed the gaze-shift blink on the shot's opening look, fixed)
    and the full shot, rendered in five 30-frame chunks of the same render.
- **Face contact sheet** `face_contact_sheet.jpg`: boy (top) and girl (bottom) at idle, happy, surprise onset,
  surprised, both blinks and sad. **Curves** `face_curves.jpg`: every baked control that moves, and eye yaw/pitch
  relative to the head, for both characters.
- **Compared with the references** (`reference_vs_render_f40.jpg`: `docs/references/char_C_boy.jpg`, the girl's
  `sheet30_front.png`, render frame 40):
  - Identity is unchanged: the layer only moves existing controls, and offsets at rest are ≤ 0.05.
  - The boy keeps his heavy-lidded rest (T-053a finding 1).
  - The girl keeps open eyes, high brows and her soft smile, and gains brow lifts, wider eyes in surprise and sad
    brows and corners.
- What changed vs before:
  - Blinks vary (doubles, gaze-shift blinks, rate per emotion).
  - Eyes dart and hold, lead the head, and drop in sadness.
  - Brows flash on attention; brows and mouth corners follow the emotion; the jaw breathes.
- **Deviations / caveats:**
  1. In the render, the girl's blink during surprise (frames 95–96) does not close her eyes. Cause, measured by
     ray casts in `shot.blend`: on her lid meshes, the Surprise or EyeWide shape key (either one) keeps the closed
     lid behind the front of the eyeball.
     - Fixed after the render with `blinkClears`. A re-bake plus Blender ray cast at frame 95 now hits the lid
       25/25 (before: eyeball 25/25).
     - Trade-off: during a blink in surprise, the rest of her Surprise shape (brows, mouth) dips for ~0.25 s, as
       seen in `face_curves.jpg` frames 93–98.
     - The clean fix is asset-side: a corrective Blink×Surprise (and EyeWide) shape key in the girl's face
       (Lane B/D).
  2. In the sad beat, the boy's head bows so far that his face is mostly hidden by his fringe. This comes from the
     shared `emo_sad` posture clip together with the look-down target. The target was made gentler afterwards (not
     re-rendered); the posture itself is unchanged.
  3. The boy's package (frozen 1.0.0 / spec build) exports only Blink, Smile, JawOpen and BrowDown. In sad and
     surprised his face moves only through eyes, blinks, jaw and the shared posture: no brow raise or mouth corners
     until his face exports more controls.

## 8. Problems, limitations, open questions for the Supervisor
- **Guarded paths** need `Supervisor-Approved:` trailers for `tests/CMakeLists.txt`, `tests/test_emotions.cpp` and
  `tests/test_face_layer.cpp`.
  - New test file and registration only.
  - In `test_emotions.cpp` the library loop now skips non-`*.emotion.json` files; no assertion was removed or
    loosened.
- **`test_emotions.py` AC5 `boy_reach_keeps_hand`** fails with 0.056 m on untouched staging and on this branch
  alike: the reaching hand moves when the emotion plays. This is the reach/arm-clearance path (T-040r1's
  interaction files); not changed here.
- **Clip generator:** `make_clips.py` should learn the clip `face` blocks before the clips are regenerated
  (pipeline, outside this write-set).
- **Asset follow-up:** corrective shape keys for Blink combined with eye-opening expressions (girl), and brow-up /
  mouth-corner controls for the boy's next version.
- **Gaze assist default on:** shots where a look target was beyond the eye range now turn the neck (and the chest
  beyond 70°) instead of leaving the eyes stuck at their limit. Settings are per character if a shot needs the old
  behaviour (`assist*` = 0).
- **Personality profiles** (T-053a) can feed the per-character `faceMotion` block. T-053a's measured blink rates
  (36–48/min in 5 s of video) are above the current neutral (~17/min); left for the personality task.

## 9. Commits
Branch `t-046-claude-facial-animation`. Commits: gaze assist; facial layer; tuning; opening-look fix; blinkClears +
evidence; per-character faceMotion; staging merges (2); report. Gate was run on `aa1f1bb` (report-only commit follows).

## 10. Resource use
Token usage is not exposed. Renders:
- Cycles: 156 frames (6 test + 150 shot).
- Engine previews: 7 low-resolution frames.
- Blender `--blend-only` scene builds (no rendering) for the ray-cast diagnosis: 3.

Repeated work: `test_emotions.py` was run 5 times while fixing the gaze; character masters were built twice (the
e906 cache and the evidence shot's own cache).
