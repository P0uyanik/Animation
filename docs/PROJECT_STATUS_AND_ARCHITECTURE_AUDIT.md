# Plush Studio: project status and architecture audit (state `9d9612f`, 2026-11-14)

Assessment only; nothing was changed.

**Sources:**
- `FEATURE_STATUS.md`, `docs/CHARACTER_REUSABILITY.md`, `docs/ENGINE_CHARACTER_PACKAGE.md`;
- the M1–M3.1 reports in `docs/milestones/` and `docs/second_character/`;
- the scene files in `content/scenes/`;
- targeted reads of `apps/studio/main.cpp`, `pipeline/charsys/episode.py` and the engine action parser;
- the latest test results recorded in the M3.1 report (no new builds or tests).

**Status words:**
- **implemented and tested:** automated tests exist;
- **experimental:** works and is measured, not approved;
- **missing.**

## 1. Where are we now?
Two production lines exist, and they are only partly connected.

**A. The C++ application** (`engine/`, `apps/studio`, `apps/render-cli`; iterations 1–4):
- **Characters:** its own SDF characters (`content/characters/*.character.json`: three reference characters, built
  by a script kit).
- **Runtime:** a skinning, IK and action runtime, a life layer, and a camera director.
- **Rendering:** a CPU path tracer with plush, fibre, glass and water materials and subsurface skin.
- **Studio app:** a desktop app (docking UI, preview, outliner, in-app path tracing, hair-lock editor, keys, project
  save and reopen).
- **Output:** short animated scenes. The longest is `watertable_v4`: **6.0 s**, 3 characters, H.264 video.

**B. The Blender character pipeline** (`pipeline/charsys/`; boy pilot, then M1–M3.1):
- spec-driven characters with a versioned asset store (immutable hashed versions, approval, restore);
- generic body and rig (`body_generic/1`), generic face (`face_generic/1`), expression library, glasses accessory;
- export of engine packages (`plush.imported_character`) that the C++ runtime loads.

**Characters:**
- **Boy:** `boy_yellow_hoodie` 1.0.0 is published.
- **Girl:** `girl_auburn_bun_glasses` is at M3.1 (body, rig, face, glasses). She has **no hair and no clothing**.

**What we can demonstrably do today:**
- Build a humanoid character from a spec in Blender, with body, rig, face, expressions and glasses.
- Version it.
- Export it to the engine, where these are tested in C++ (`tests/test_imported_character.cpp`): reach, grasp,
  walk, idle, look-at, blink with per-character timing, 10 semantic expressions and a jaw.
- Render short multi-character scenes with the engine's own SDF characters.

**What we cannot do today:**
- Make a finished shot with a Blender-built character that looks right. The engine renders imported characters
  with base colours only (white eyes, untextured mouth interior; found in M3.1).
- Make a shot longer than a few seconds of scripted actions.

## 2. Current capabilities
| Area | Status | Evidence / gap |
| --- | --- | --- |
| Character creation | **Implemented and tested:** spec → Blender build, asset store, versioning (`verify_charsys`, store and reuse tests). **Experimental:** generic body and face (girl, synthetic G02/G03) | No creation UI; specs are written by hand. The boy still runs on the legacy `body_v6` path |
| Rigging | **Implemented and tested:** Rigify fit from a rig profile, role-based weights, rig profiles for the engine export (3 packages in C++ tests) | Hip crease 7.0×, armpit 4.4× (M2, open); humanoid only |
| Facial animation | **Experimental and tested:** 13 action units, 14 + 2 presets, per-eye and partial blinks on the true arc, jaw bone, blink timing, oval-eye clearance (M3, M3.1) | Rounded closed lids; slit mouths only; no lip-sync |
| Body animation | **Implemented and tested (engine):** look, expression, reach (grip/lift/place/release/lean), touch, walk, idle life layer. **Experimental:** camera director | No sit, run, jump or wave; walking on straight, flat paths only; no motion library or mocap |
| Hair | **Experimental:** `hair_clumps/2` (boy H25–H28 candidates); engine SDF characters have explicit locks and fuzz | The girl's long curls and bun are not built (M4); no secondary motion anywhere |
| Clothing | **Character-specific:** the boy's garments in `body_v6`; SDF garments on the engine characters | No garment library; no cloth simulation; the girl has none (M5) |
| Interactions | **Implemented and tested (engine):** grasp of spheres and cylinders, touch ≤ 6 mm, held objects, water ripples | No rigid-body physics (Jolt planned); object shapes beyond stick and sphere untested |
| Scene management | **Implemented:** scene JSON (characters, objects, lights, camera, actions, tracks); Studio save/reopen | Scenes are hand-written JSON; no episode, shot or sequence structure; no audio |
| Rendering | **Implemented and tested:** engine path tracer with OIDN, image regressions in `ctest`. Blender Cycles is used only for evaluation sheets | Imported characters lose their materials in the engine. Render cost for minutes of film is not measured. No audio or ProRes export |

## 3. Is the architecture correct?
**Target (as stated):**
- **Plush Studio** owns the product: UI, workflow, project, episode and character data, and approvals.
- **Blender** is a headless production backend: modelling, rigging, grooming, simulation, rendering.
- **C++ engine** owns runtime animation: behaviour, interaction, playback.

| Responsibility | Target | Actual | Verdict |
| --- | --- | --- | --- |
| Character data and specs | Plush Studio | JSON specs and an asset store in `pipeline/charsys/` (Python), edited by hand. Studio has **no** reference to the Blender pipeline or imported characters (`apps/studio/main.cpp`: 0 matches) | **Gap:** the data model is right, but Studio does not own it yet |
| Character production (mesh, rig, face, hair, clothes) | Blender | Done in Blender for the boy and the girl. **But** the engine's older SDF character system (iterations 1–4, script kit, Studio hair-lock editor) is a second, parallel production path | **Duplication:** two character systems. The SDF path should become legacy or test-only |
| Runtime animation and behaviour | C++ | C++ actions, life layer, IK, grasp, walk, expressions, now data-driven for imported packages (TD-38/39, M3.1) | **Correct** |
| Rendering | Blender (per the target) | Final images come from the **C++ path tracer**. Blender renders only evaluation sheets. Animation never flows from the engine back to Blender: `episode.py` sets only a static pose and face values | **Undecided and mismatched:** no final render path works for Blender characters (the engine drops their materials; Blender gets no engine animation) |
| Separation of shared vs character data | All layers | Strong in the Blender pipeline (specs, profiles, libraries, generic modules; validated on boy, girl, G02, G03) and in the engine package adapter | **Correct, and the project's main strength** |

## 4. Are we on the right development path?
**Right:**
- The shared-before-specific discipline: generic body, face and accessories validated on structurally different
  configurations.
- The data-driven engine adapter.
- Regression protection of the frozen boy.

**Gaps and priorities to correct:**
1. **No end-to-end vertical slice** with a Blender-built character. Every milestone stops at "Blender asset +
   engine unit tests". The two integration breaks only surfaced by accident, in the M3.1 engine render:
   - materials lost in the engine;
   - no engine → Blender animation path.
2. **The final render path is undecided** (engine path tracer vs Blender Cycles). This decides whether material
   export or animation baking is needed, so it blocks hair, clothing and shading work from being judged in final
   form.
3. **Studio is not connected** to the character pipeline, the asset store or approvals; the product layer lags the
   backend.
4. **Two character systems are maintained:** the engine SDF characters and Blender charsys. This is effort spent on
   both, without a stated retirement plan for one.
5. **Polish before completeness:** many face and hair iterations (F01–F09, H25–H28, M3 tuning) on unapproved
   candidates while a whole character (hair, clothes) and the episode pipeline are missing.
   - Justified where it produced shared systems.
   - Over-invested where it tuned one character's looks.

**Not wrong, but deferred correctly:** physics, GPU rendering, Windows build.

## 5. How far are we from the final goal?
**Why a complete 2–2.5 min episode is impossible today** (at 30 fps that is 3,600–4,500 frames):
1. **No complete Blender character:** the girl has no hair or clothes, and the boy's approved 1.0.0 predates the
   face systems.
2. **No working final render path** for Blender characters (section 3).
3. **No episode layer:** no script, shot list, sequence, editing, camera continuity across shots, or audio;
   scenes are hand-written JSON of a few seconds.
4. **Behaviour vocabulary too small** for story staging: no sit, run, jump or wave; flat straight walks only; no
   lip-sync.
5. **Render throughput** for thousands of frames has not been measured.

**Remaining milestones** (rough effort; dependencies in brackets):

| Milestone | Effort | Depends on |
| --- | --- | --- |
| R. Render-path decision + vertical slice: one 10–20 s shot with Blender-built characters, from engine animation to a final image (material export or animation baking, depending on the choice) | Medium | — |
| M4. Hair system on the girl (curls, bun, flower and band accessories) via shared modules | Large | R (to judge in final render) |
| M5. Garment library (top, vest, shorts, boots) + boy convergence onto generic body and face | Large | M4 partially; R |
| S. Studio integration: open specs and versions, trigger Blender builds, approvals, scene/shot editing on imported characters | Large | R |
| E. Episode layer: script/shot list → actions, sequences, cameras across shots, audio and lip-sync, export | Large | R, S |
| B. Behaviour expansion: sit, wave, run, turn on paths, secondary motion | Medium | R |
| P. Production run: a 2–2.5 min episode, render farm or throughput work | Medium–Large | all above |

## 6. What should we do next? (three steps, in order)
1. **Decide the final render path and build one vertical slice.** Take the boy 1.0.0 and the girl M3.1 through a
   10–20 s engine-animated shot to a final image. It exposes and fixes the real integration gaps (materials, or
   animation transfer to Blender) before more character work.
2. **Complete the girl with shared modules:** hair (M4), then garments (M5). That gives two complete production
   characters on one generic path and the first real test of a garment library.
3. **Connect Plush Studio to the pipeline.** Studio should own specs, versions, builds, approvals and shot
   authoring. This starts the episode layer, so that episodes are made in the product, not in hand-written JSON
   and Blender scripts.

## Agent and token use
- One primary agent; no subagents.
- No builds, renders or tests were run for this audit.
- Actual token usage is not exposed to me, so it is unavailable.
