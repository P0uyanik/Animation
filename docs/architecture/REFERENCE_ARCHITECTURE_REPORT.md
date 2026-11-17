# Reference video analysis and architecture report (T-076)

Evaluation only, 2026-11-17. No code, spec, preset or asset was changed. Branch `t-076-claude-reference-architecture`
from `origin/staging`.

**Method.** I extracted every frame of both reference videos with FFmpeg: `video_paperboat.mp4` has 289 frames and
`video_watertable.mp4` has 121, both at 24 fps. I viewed them as 1-second contact sheets of 24 frames each, plus
full-resolution single frames for faces, camera framing and the fold. The 0.25 scene-change filter found no cuts, so
I located the cuts by eye on the frame sheets.
- **Citations:** `PB f123` is paperboat frame 123 and `WT f45` is water-table frame 45 (0-based, 24 fps). Files are
  cited by repository path.
- **Evidence** (JPEG ≤ 2048 px, DELIVERY_PLAN §9b), in `docs/evaluation/review/T-076/`:
  - [pb_shots.jpg](../evaluation/review/T-076/pb_shots.jpg): first and last frame of every paperboat shot;
  - [pb_fold_f050-086.jpg](../evaluation/review/T-076/pb_fold_f050-086.jpg): the fold, every 4th frame;
  - [wt_1s.jpg](../evaluation/review/T-076/wt_1s.jpg): the water-table shot, one frame per second.
- **Labels:** **[D]** = decided (TD or owner decision); **[R]** = my recommendation; **[M]** = measured on frames;
  **[J]** = visual judgement.

---

## 0. Summary (for the owner)

1. **The current architecture fits the videos.** Blender owns the look and the final render; the engine owns
   animation; `plush.shot_bake/1` connects them [D: TD-42]. What is missing is in the content systems, not the split:
   - hands and fingers (two-handed grasps, hand poses);
   - props from real meshes, not only primitives;
   - effects: water, glow and sparkles;
   - sets and lighting presets;
   - personality profiles that drive the animation.
2. **Main inefficiency: two parallel scene paths.** The engine-era objects (water height field, SDF props, `attachTo`,
   floating) never reach Blender (`engine/scene/shot_bake.cpp:50`, `objects_not_baked`). In parallel, the
   `plush.asset/1` props do reach Blender, but only as primitives (`docs/ASSET_LIBRARY.md`: "file meshes are not
   imported yet").
   - [R] Merge the two into one data-driven prop/effect path: assets with affordances, plus a bake that carries
     events and prop states.
   - [R] Water and sparkles are then rendered in Blender from engine-timed events, with no fluid simulation needed.
3. **Interactions should be data, not code.** [R] Props declare affordances (sockets, grasp shape, one or two hands,
   states, physics kind). Verbs are JSON phase recipes compiled onto the existing T-022 actions
   (`engine/scene/interaction.h`), with T-047 collision, T-051 finger poses and T-053 timing.
   - A new prop needs only an asset file.
   - A new verb needs only a verb file, unless it needs a new primitive.
4. **Treat the videos as an acting and look target, not as literal continuity.** They show generative-video
   artefacts:
   - the paper turns into a boat in 5 frames (`PB f084`–`f089`);
   - hand ownership swaps mid-fold (`PB f050`–`f060`);
   - after the fold, the wide shot goes back to drawing (`PB f112`);
   - two different water tubs: a blue plastic tub (`PB S4`–`S6`) and a wooden water table (`WT`).
   
   Reproduce the look, timing, framing and acting, and author a fold that a viewer can follow.
5. **Priority stays on reference-quality characters.** Of the capabilities the videos need, most character ones
   are partial (§3.3). The highest-value non-character gaps are:
   - G1: the hand-pose library and two-handed grasp (T-051);
   - G3: the personality profile reader (T-053);
   - G4: file-mesh props;
   - G5: lighting and camera presets.

   Water, fold and sparkles stay deferred per Priority v5 (`docs/ROADMAP.md`).

---

## 1. Architecture: division of responsibilities

### 1.1 Who owns what

| Component | Owns | Why | Status |
| --- | --- | --- | --- |
| **C++ engine** (`engine/anim`, `engine/scene`, `engine/model`) | All motion: clips and layers (`clip_layers.cpp`), emotions (`emotion.cpp`), face layer (`face_layer.cpp`), life layer (breath, blink, weight shift), body mechanics (`anim/body_mechanics.cpp`), IK and hand–prop actions (`scene/interaction.cpp`), secondary spring chains (`anim/secondary.cpp`), director camera planning (`docs/ACTIONS_AND_DIRECTOR.md` §director), shot bake (`scene/shot_bake.cpp`) | Deterministic, testable (doctest, CTest), fast enough for interactive preview, character-independent through packages and rig profiles (TD-38, TD-39) | [D] TD-42 |
| **Engine renderer** (`engine/render`, Embree + OIDN) | Motion previews in Studio, the frozen image regressions | Already exists and is tested; no look work | [D] frozen (OWNER_DECISIONS 2026-11-17 "renderer freeze"); guarded path |
| **Blender** (`pipeline/charsys`, headless) | Building characters (body, face, groom, garments, build-time drape `garments/drape.py`, materials `materials/presets.json`), immutable masters (`asset_store.py`, T-075), final render (`shot_render.py`, Cycles; Eevee option in `run_shot.py --engine`) | Renders every character material (TD-42 evidence); production tools for fibres, cloth and shading | [D] TD-37, TD-42 |
| **Python pipeline** (`pipeline/production/run_shot.py`, `tools/`) | Orchestration with content-hash caching, cast resolution (`current`, T-062), gate (`tools/check_all.py`), fidelity (`tools/fidelity`), lip-sync extraction (`tools/lipsync`), regression | Glue and checks; no runtime animation | [D] |
| **Plush Studio** (`apps/studio`, ImGui + OpenGL/GLFW/GLEW, `vcpkg.json`) | User-facing editor: projects, timeline, Production panel driving `run_shot` (T-001) | The product UI; never renders finals | [D] |
| **FFmpeg** | Encoding shots (`run_shot --video`), evidence sheets; later episode assembly and audio mux | Standard, free | exists for encode; assembly missing (V8) |
| **Lip-sync aligner** | Rhubarb 1.13.0 (offline) → `plush.visemes` → shared visemes (`content/visemes/shared_visemes.json`) → engine face layer | Offline, open-source; output is plain data | toolchain in main (T-054a); real aligner untested (T-054b queued) |

### 1.2 Recommended additions [R]
These need no new heavy dependencies.
- **Blender Geometry Nodes for effects:**
  - a water-surface displacement from ripple events: a sum of damped rings, analytic and deterministic;
  - sparkle particles and the waterline glow (emission plus the compositor glare node).
  
  Geometry Nodes are already used for fibres (TASK_LOG, T-015 batch). This avoids Mantaflow and other fluid
  simulations, which are slow on CPU and hard to keep bit-reproducible.
- **Blender light-rig and camera presets as data** (V5): named presets that a shot references. Look parameters then
  live where the look is rendered.
- **No new renderer, simulator or engine library.** Embree stays inside the frozen renderer. Collision queries for
  animation use the exported collision bodies planned in T-047, not Embree.

### 1.3 Inefficiency and duplication in the current split
| # | Finding (evidence) | Effect | Recommendation [R] |
| --- | --- | --- | --- |
| A1 | Two object paths: engine `ObjectDesc` (box, SDF, water height field `waterHalfSize`/`ripples`, `floatOn`, `attachTo`; `engine/scene/scene.h:25–41`) vs `plush.asset/1` props with `parent`/`parentSwitch` (`docs/ASSET_LIBRARY.md`). The bake drops everything except boxes: `objects_not_baked`, "SDF props, paper boats, water: not part of bake v1" (`shot_bake.cpp:50`) | The water, floating boat and ripples already animated in the engine (`milestone03_watertable.scene.json`) cannot reach the final render; two attachment mechanisms (`attachTo` vs `parentSwitch`) | Production uses only `plush.asset/1`. Re-express water and floating as asset affordances plus bake events (§2.3). Keep `ObjectDesc` only for legacy previews and regressions |
| A2 | Blender draws only primitive props: "file meshes are not imported yet" (`docs/ASSET_LIBRARY.md`; `shot_render.py` builds box/sphere/cylinder) | No real table, tub, paper boat, crayons or chair in a final render | Import `mesh.path` (`.blend` linked, as characters are, or `.glb`) in `shot_render.py`. This is the smallest step with the largest set-dressing gain |
| A3 | Lights are authored in engine scene units and translated approximately (`shot_render.py:199` `setup_world`, `--light-scale`; TD-42 trade-off) | The look is tuned in the engine's units for a renderer that is not the final one | Lighting is authored in Blender as named light-rig presets that belong to a set asset. The engine scene names the preset; the engine preview uses a rough stand-in. This finishes moving look ownership to Blender |
| A4 | Two arm-body clearance methods: T-030 capsules (`interaction.h`, `BodyCapsule`) and the T-040r1 SDF post-pass (unmerged) | Double maintenance; neither gives smooth shots | Already planned as T-047 (one collision body, solved inside the animation). Endorse it |
| A5 | Personality is read layer by layer: `body_mechanics.cpp:39` reads profile records itself; the face, blink, tempo and gaze layers do not read them yet | Each layer would interpret the profile differently | One profile reader (T-053) resolves a profile into typed parameters once, and every layer receives them |
| A6 | Material looks exist twice: engine `bsdf`/`fuzz` and Blender presets | Previews do not match finals | Accepted by the freeze. Judge motion in engine previews and look in Blender renders (T-074 `preview` profile). Do not chase parity |

---

## 2. Scene interactions

### 2.1 Ownership
| Element | Defined in | Animated by | Rendered/simulated by | Notes |
| --- | --- | --- | --- | --- |
| **Sets** (classroom, table, shelves, windows) | Set asset: a `plush.asset/1` collection plus layout JSON (V7) | static, or camera only | Blender (linked `.blend`, like character masters) | A set carries its light-rig and camera presets [R] |
| **Props** (paper, boat, crayons, tub, cup) | `plush.asset/1` + affordances (§2.2) | engine: attachment, IK contact, state tracks | Blender (mesh, material preset, state shape keys) | Primitives today; file meshes missing (A2) |
| **Rigid physics** (a prop falls or slides) | asset `physics.kind: rigid` | engine: simple scripted or keyed motion | — | The videos show none; keep keyed, no rigid-body simulator [R] |
| **Hair and accessory dynamics** | groom `hair.dynamics`, accessory chains | engine spring chains (`anim/secondary.cpp`) | Blender skins the baked bones | exists; T-061 adds accessory chains |
| **Garments** | `garment/1` | follow skinning; drape settled once at build (`garments/drape.py`) | Blender | Animated cloth simulation is not needed by the videos (sleeves follow the arm, `PB S4`) |
| **Water surface** | asset affordance `surface: water` | engine emits ripple events (contact, float) and buoyancy bob | Blender GN displacement from the events + glass/water shader | engine height field exists (`scene.h`), not baked (A1) |
| **Paper fold** | asset `states` (flat → fold steps → boat) as shape keys or mesh swaps, built in Blender | engine `prop.state` track, keyed by the `fold` verb with hand contacts | Blender | Deferred (Priority v5); never a cloth simulation [R] |
| **Glow and sparkles** | effect asset (`plush.effect`, proposed) | engine event (start, anchor prop, intensity curve) | Blender GN particles, emission, compositor glare | missing |
| **Character–object contacts** | affordances + verbs | engine IK (`interaction.cpp`), collision (T-047), fingers (T-051) | — | partial (T-022) |

### 2.2 Proposed data-driven interaction system [R]
**Principle.** Props say what they afford. Verbs say how an action unfolds. Characters say how they move, through
their profile. The engine compiles all three onto its existing primitives. Nothing is coded per prop or per
character.

**(a) Affordances on the asset** (opt-in fields; `plush.asset/1` readers ignore unknown fields, otherwise `/2`):
```json
"affordances": {
  "grasp":  [{"socket": "grip",   "shape": "pinch|cylinder|flat|wrap", "hands": 1, "approach": [0,0,1]}],
  "grasp2": [{"sockets": ["edge_l", "edge_r"], "shape": "flat", "hands": 2}],
  "place":  [{"socket": "base", "onto": ["surface"]}],
  "surface":{"kind": "table|water", "socket": "top", "extent": [0.6, 0.4]},
  "lean":   [{"socket": "rim_front", "hands": 2}],
  "states": {"kind": "shape_keys", "names": ["flat","fold1","fold2","fold3","boat"]},
  "physics":{"kind": "static|carried|floating", "mass_kg": 0.005, "buoyancy": 0.9}
}
```

**(b) Verb library** (`content/interactions/<verb>.verb.json`). Each verb is a list of phases. Every phase has:
- a target: a prop socket, a character landmark (`chin`, `other_hand`) or a point;
- a hand shape from the T-051 pose library;
- a gaze rule;
- default timing at 24 fps, scaled by the profile's `tempo`.

The engine compiles phases onto existing tracks (`ik.*`, `orient.*`, `hand.*.grasp`, `parentSwitch`,
`<prop>.parent.weight`), plans arms outside the body (T-047), adds lean and weight shift (T-045) and checks
contacts (> 5 mm reported, as today).

| Verb | Phases | Primitives used | Exists? |
| --- | --- | --- | --- |
| reach / touch / point | anticipate → reach → contact → hold → return | arm IK, fingertip target | yes (`reach`, `touch`, `point.clip.json`) |
| grasp / hold / place / hand-over | reach → close → attach → carry → place/release | IK + `parentSwitch` | yes, one hand per prop (T-022) |
| **grasp2 / carry2 / place2** | both hands reach paired sockets → attach to a two-hand mid-frame → lower → release | two-hand coordination (new primitive) | no ("two-handed grasps" not supported, `docs/ACTIONS_AND_DIRECTOR.md:95`) |
| **lean-on** | both palms to `lean` sockets, torso lean, weight onto hands | IK + T-045 lean | no (prop interactions "do not lean the body", ACTIONS:96) |
| **self-contact** (hand to chin or mouth, clasp hands) | hand to a character landmark, finger pose | IK to a landmark + T-051 pose | no |
| **smooth / press / fold** | palms flat on the sheet, slide; pinch an edge, lift, crease, set the next `state` | IK along a path + `state` track | no |
| push / slide / pour | contact, move the prop along a path or tilt | IK + prop transform track | no (not in the videos) |
| **release-float** | lower onto the water, release, emit ripple, floating bob | `place` + `surface: water` event | partial (`reach` makes ripples on engine water, ACTIONS:25; not baked) |

**(c) Adding content with specs only:**
- **New prop** (e.g. a crayon): write `content/assets/crayon.asset.json` with the mesh, material preset, sockets
  `grip` and `tip`, `grasp` (`pinch`, 1 hand) and `place` (`onto: surface`). Every verb that needs a `grasp`
  affordance can use it at once.
- **New verb** (e.g. `stack`): a `stack.verb.json` made of `grasp` → carry → `place` onto another prop's `top`
  socket. It needs engine code only if it needs a new primitive. The two-hand primitive and path-following IK are
  the only new primitives these videos need.
- **New character:** nothing. Hands come from the rig profile and HandFrame (TD-39), timing from the profile.

### 2.3 Bake extension (backward compatible, like the `props` block) [R]
Optional new blocks in `plush.shot_bake/1` frame data, omitted when a shot has no such content (unchanged JSON for
old shots):
- `prop_states`: `{prop: {state: weight}}`;
- `events`: `[{type: "ripple", prop/surface, at, start, amplitude}, {type: "sparkle", anchor, start, rate, curve}]`.

`shot_render.py` maps them to shape-key weights and Geometry Nodes inputs.

### 2.4 Simulation: baked in Blender or procedural in the engine
| Effect | Where | Reason |
| --- | --- | --- |
| Hair and accessory sway | engine, procedural (spring chains) | interactive, character-independent, already exists |
| Prop carry, place, float bob | engine, procedural | timing follows actions; deterministic |
| Water ripples | Blender GN, analytic from engine events | the look (refraction, highlights) is a render matter; analytic rings are deterministic and cheap; the videos show stylised rings (`PB f191`–`f238`) with no splashing |
| Sparkles, glow | Blender GN particles with a fixed seed + compositor | a pure look effect |
| Paper fold | Blender-built state meshes, engine-timed | a readable authored fold beats a simulation; no cloth simulation |
| Garment cloth | build-time drape only (exists) | the videos show no free cloth motion |

---

## 3. Reference analysis

### 3.1 `video_paperboat.mp4` (854×480, 24 fps, 289 f = 12.04 s, 6 shots, average shot length 2.0 s) [M]
Characters, left to right in the wide shots: **W** = white-haired girl (`girl_white_hair_blue_dress`), **G** = girl
(`girl_auburn_bun_glasses`), **B** = boy (`boy_yellow_hoodie`).

| Shot | Frames (s) | Camera | Action and interaction | Expressions | Environment, light, effects |
| --- | --- | --- | --- | --- | --- |
| S1 wide | f000–031 (0.00–1.33) | eye level just above the desk, about a 40–50 mm look, almost locked (slight drift) | all three seated at a desk on small wooden chairs, working on paper; G draws with two hands flat; B holds a sheet up with both hands; very little motion | W: big blue eyes, closed soft smile, blink `f005`–`f007`; G: looking down, closed smile, concentrating; B: heavy lids, eyes down, flat mouth, slouched (`f000`, `f031`) | dressed classroom (shelves, toys, crayons, scissors pot, window), warm high-key daylight from behind (rim on the hair), soft front fill, background softly out of focus |
| S2 insert | f032–111 (1.33–4.63) | close-up of G's hands and the desk, longer lens, very shallow focus (background fully blurred), slow push-in and slight tilt down (G's torso grows in frame from `f032` to `f096`) | G smooths the sheet with flat palms (`f032`–`f048`); W's (blue cuff) and B's (yellow cuff) hands enter `f040`–`f046`; a corner is lifted and creased `f050`–`f070`; the hand changes from yellow to cream cuff `f053`→`f056` (artefact); triangle pressed flat `f072`–`f083`; **sheet turns into a boat in about 5 f** `f084`–`f089` (no readable fold); G holds the boat with both hands `f096`–`f111` | faces out of frame (G's chin `f070`–`f082`) | warm wood desk, paper with subsurface glow and soft creases, cuffs show knit and fleece texture |
| S3 wide | f112–150 (4.67–6.25) | same set-up as S1 | **continuity break:** back to drawing (`f112`); G holds a small folded paper; small head moves | W: eyes closed and drowsy `f121`–`f128`, then open; B: heavy lids throughout; G: closed smile | as S1 |
| S4 close-up | f151–190 (6.29–7.92) | low, at the water level of a **blue plastic tub**, longer lens, very shallow focus | G lowers the boat with two hands `f151`→contact ≈ `f175` (≈ 24 f, slow and even), fingers open and withdraw `f175`–`f190`; W and B are blurred behind | — | cool blue tub, water reflections; fingertips meet the boat's sides |
| S5 extreme close-up | f191–238 (7.96–9.92) | at water level on the boat, slow push-in or slight arc, very shallow focus | the boat floats with a slight bob; concentric ripples; **golden waterline glow begins about `f198`** and grows; **sparkle particles** from about `f203`, denser by `f230` | — | ripples with strong specular rings; emissive gold band; bokeh room behind |
| S6 reveal | f239–288 (9.96–12.04) | starts on the tub and G's hands, **cranes or tilts up and pulls back** to frame all three faces (`f239`→`f288`), high-angle medium | G leans on the rim with both hands; W clasps her hands at her chin; B appears behind the girls looking down at the boat | G: open-mouth delighted smile, eyes wide (`f256`–`f288`); W: wide eyes, lips parted, clasped hands, "ooh" (`f252`–`f288`); B: eyes open, brows down, mouth small, "engaged" (`f264`–`f288`) | glow and sparkles continue; warm room |

### 3.2 `video_watertable.mp4` (828×1108 portrait, 24 fps, 121 f = 5.04 s, 1 shot) [M]
| Aspect | Observation |
| --- | --- |
| Camera | **portrait 3:4**, high angle (about 30° down) three-quarter view over a **wooden water table**; slow push-in with a slight move to the right: the boy's head grows and moves left, and the table's left corner leaves the frame between `f000`, `f064` and `f120` (`wt_1s.jpg`); moderate depth of field; a blurred teddy bear in the right foreground |
| Characters | B on the left, standing and leaning on the rim with both hands; G in the centre, standing; W on the right, hands on the rim |
| G | hand at the mouth or chin, "oh" mouth, eyes wide (`f000`–`f012`); eyes closed with the mouth open as the hand leaves the chin (`f016`–`f021`); reaches and points at the boat (`f022`–`f060`) while talking; straightens up, arms down, closed soft smile (`f096`–`f120`) |
| B | head down, eyes on the boat, brows slightly down, mouth closed; blinks (`f020`–`f025`, `f060`–`f065`, `f081`–`f084`); almost no body motion |
| W | hands on the rim, lips parted while watching (`f000`–`f018`), blinks `f019`–`f021` and `f107`–`f109`, closed soft smile at the end (`f120`) |
| Props and effects | paper boat drifting slowly to the right (about 15 % of frame width over 5 s); concentric ripples around it fading; coloured pebbles visible under clear water |
| Light | warm backlight from large windows (rim on the hair), soft fill, high key, cream walls with children's drawings |

These timings agree with the existing measured guides (`docs/characters/*/REFERENCE_BEHAVIOUR.md` §4: the girl's
reach ≈ 8–10 f, blinks ≈ 4–6 f, the boy's long holds), so no profile values need changing.

### 3.3 Capabilities needed to reproduce both videos
Status: **E** = exists, **P** = partial, **M** = missing.

| # | Capability | Owner | Status (evidence) | Covered by / proposed |
| --- | --- | --- | --- | --- |
| C1 | Characters at reference fidelity (felt skin, wool hair, knit/fleece garments, eyes) | Blender | **P**: T-063 judges ≈ 45–50 % overall (`docs/evaluation/review/T-063/README.md` §1) | T-065, T-070, T-066, T-067, T-068, T-059, Boy 2.0 |
| C2 | Seated pose at a desk; standing lean on a rim | engine | **P**: `sit_down.clip.json` exists; a body lean onto the hands is missing (ACTIONS:96) | new verb `lean-on` (G2) |
| C3 | One-hand reach, grasp, place, point | engine | **E** (`interaction.cpp`, T-022; `point.clip.json`) | — |
| C4 | Two-handed hold and place (boat `PB S2` `f096`–`f111`, `S4`) | engine | **M** (ACTIONS:95) | T-051 + new two-hand primitive (G1) |
| C5 | Finger poses: flat palm, pinch, clasped hands, hand to chin | engine | **P**: grasp curl by contact search only; no pose library (T-051 has no task file yet; `docs/ROADMAP.md` phase 2) | T-051 |
| C6 | Smoothing and folding paper with readable steps | Blender states + engine timing | **M** (`paper_sheet.asset.json` is a box primitive) | deferred (Priority v5); `fold` verb + prop states when a scene needs it |
| C7 | Contacts without passing through (hands vs paper, rim, body) | engine | **P** (T-030 capsules; T-040 not merged) | T-047 |
| C8 | Facial expressions: soft smile, open smile, "oh", agape watching, heavy lids, concentrated brows | Blender shapes + engine face layer | **P**: presets and action units exist (TD-41, `face_layer.cpp`, `content/emotions`); shape quality is the T-063 gap; a pursed or rounded "ooh" mouth may be missing (`SYSTEM_GAPS.md` "Pucker") | T-065 |
| C9 | Blink timing per character, coupled to action changes | engine | **P**: life-layer blinks exist (`scene.h` `LifeParams`); profile values are not wired | T-053 |
| C10 | Personality tempo, posture and gaze per character | engine | **P**: profiles are drafts (`content/personality/*.draft.json`); only body mechanics reads them (`body_mechanics.cpp:39`) | T-053 |
| C11 | Talking while gesturing (G, `WT f022`–`f060`) | engine + tools | **P**: lip-sync toolchain without a tested aligner (T-054a); dialogue in the shot spec is pending | T-054b, T-054 |
| C12 | Hair and accessory secondary motion (buns, curls, bow) | engine | **P**: spring chains exist (`secondary.cpp`); accessory chains are in T-061 | T-061, T-070 |
| C13 | Arcs and slow-in/slow-out on gestures | engine | **P** (T-061 critique) | T-061 |
| C14 | Props from real meshes (desk, chair, tub, water table, boat, crayons, scissors pot) | Blender | **M**: primitives only (`ASSET_LIBRARY.md`) | G4: file-mesh import in `shot_render.py` |
| C15 | Dressed classroom set | Blender | **M** | V7 classroom kit (after V5) |
| C16 | Warm daylight rig: backlight/rim, soft fill, high key | Blender | **P**: lights translated from the engine (`shot_render.py:199`); no presets | G5: light-rig presets (V5) |
| C17 | Camera: lens, focus distance, f-stop, push-ins, crane, multiple shots per scene | engine plans, Blender renders | **E/P**: director plans close-ups with 70 mm f/2.8 and an 8 % push-in (ACTIONS:70–87); DOF is passed to Blender (`shot_render.py:354–366`); a crane or tilt-reveal move (`PB S6`) and named camera presets are missing | G5 |
| C18 | Portrait and landscape outputs (`WT` 828×1108) | pipeline | **E** (`production.render.resolution`, `run_shot.py`) | — |
| C19 | Water surface with ripples, floating bob | engine events + Blender render | **P**: engine-only height field (`scene.h:35–40`), not baked (`shot_bake.cpp:50`) | deferred; §2.3 events when a scene needs it |
| C20 | Golden glow and sparkles | Blender | **M** | deferred; effect asset (§2.1) |
| C21 | Multi-shot editing: cuts, inserts, shot order | engine director + pipeline | **P**: cuts inside one scene by the director; joining separate shots into a sequence is missing | V5/V8 episode assembly (FFmpeg concat + shot list) |
| C22 | Render time for a 10–15 s, 3-character sequence on CPU | Blender | **P**: CPU final ≈ 200–400 h per 2.5 min episode (`docs/evaluation/render/T-050/README.md`); no GPU (OWNER_DECISIONS) | T-074 |

---

## 4. Personality consistency

**Goal.** Each character behaves the same way in every shot and episode because behaviour is data that every shot
reads. It is never re-authored per shot.

| Mechanism | What it holds | Status | Recommendation [R] |
| --- | --- | --- | --- |
| **Profile** `content/personality/<id>.json` (`plush.personality/0`, `content/personality/SCHEMA.md`) | tempo, energy, posture, attention, boredom, gaze, blink, face rest, smile, gestures, reaction, interaction; each value cites its reference (`kind`, `source`) | 3 drafts with cited values (T-053a, T-057) | T-053 reader resolves the profile once (A5); the owner approves each profile with a side-by-side clip |
| **Expression library** per character | semantic presets baked per face (TD-41); per-character rest weights | exists (face library); the quality is the face-v2 gap | add the missing reference shapes (round "ooh", sided mouth corner) as opt-in action units |
| **Gesture and hand-pose sets** | named gestures per character, taken from the references: G hand-to-chin, point, two-hand careful handling; W clasped hands; B hands in pockets, one-handed practical handling | listed in profile `gestures`; poses missing | T-051 pose library; profiles select gestures by name |
| **Per-character limits** | allowed ranges such as B `energy` max, no open smiles at rest for G (owner decision), W neutral = closed soft smile, B no quick or abrupt moves, no eye-rolls (owner decision) | text only (OWNER_DECISIONS 2026-11-17, REFERENCE_BEHAVIOUR §7) | a `limits` section per profile, enforced by the engine (clamp and warn) and by the gate |
| **Automated checks against the references** | measured values: blink interval and duration, reach frames, hold lengths, motion amplitude, smile share | values exist in the guides (§4 tables) | a `tools/animcheck` personality check (T-061 creates `tools/animcheck`): run each character's eval shot and compare the measured statistics with profile ranges; FAIL outside the range |
| **Continuity of approved assets** | the approved master, spec and fingerprints are immutable; shots cast `current` | T-062 in main; T-075 running | profiles get versions and an `approved` pointer like characters; a shot records the profile hash next to the cast |

**Consistency with what the references and owner decisions say** (all reproduced by the videos above):
- **Boy:** subtle and low-energy. Heavy lids at rest (`PB S1`, `S3`), long stares at the task. Engagement is shown as
  eyes open with brows down, not a smile (`PB f264`–`f288`). Calm, slow small moves only (OWNER_DECISIONS
  2026-11-17 §1).
- **Girl:** cheerful and intelligent. Brown eyes, a closed gentle smile at rest (`PB S1`, `WT f120`) and an open
  smile on success (`PB S6`). She leads and explains: hand to chin, then pointing (`WT f000`–`f060`). Her handwork
  is careful and two-handed (`PB S2`, `S4`).
- **Third character:** subtly goofy, bubbly and the stillest of the three. Lips parted while watching (`WT f000`–`f018`,
  `PB f252`–`f288`), clasped hands, closed soft smile at rest, blue felt bow (visible in every wide frame,
  `PB f000`, `f288`, `WT f000`).

---

## 5. Gaps and improvements (prioritised; recommendations only, no scheduling change)

The ranking follows the current priority (reference-quality characters first, `docs/ROADMAP.md` Priority v5) and
the queue in `docs/process/TASK_LOG.md`.

| Rank | Gap | Why (video evidence) | Fit with the queue |
| --- | --- | --- | --- |
| 0 | Character look (face, hair, skin, materials, garments) | every shot; the close-ups (`PB S2`, `S4`) magnify hands, cuffs and knit | running/queued: T-065, T-070, T-066–T-068, T-059, Boy 2.0. Unchanged top priority |
| G1 | **Hand-pose library + two-handed grasp/carry/place** | `PB S2` and `S4`: most of the screen time in inserts is two hands on one prop | T-051 (phase 2); add the two-hand primitive to its scope or as T-051b |
| G2 | **Lean-on and self-contact verbs** (rim, chin, clasp) | `WT` all three lean on the rim; G hand to chin; W clasps her hands (`PB S6`) | after T-047 (needs collision), uses T-051 poses |
| G3 | **Profile reader (T-053) + personality checks** | consistency across shots; blink and tempo values are already measured | T-053 phase 4; add the `limits` section and the animcheck personality check |
| G4 | **File-mesh props in Blender** (`shot_render.py`) + affordances in `plush.asset` | no desk, tub or boat in any final render without it | small task; prerequisite for V5 |
| G5 | **Light-rig and camera presets as data** (warm backlit high key; insert, CU, wide; crane or tilt reveal) | consistent look across cuts (`PB S1` vs `S3` match) | V5 scope; T-074 render profiles |
| G6 | **Unify scene objects onto `plush.asset/1`**; retire `ObjectDesc` water/SDF/`attachTo` from production | A1 duplication | small engine/doc task; keeps regressions |
| G7 | **Bake events and prop states** (§2.3) + Blender ripple/sparkle GN | `PB S5`–`S6`, `WT` | deferred (water and paper not a priority); design now, build when a scene needs it |
| G8 | **Paper fold as authored states** | `PB S2` (the reference morphs; ours should read) | deferred (Priority v5) |
| G9 | **Sequence assembly** (shot list → FFmpeg concat, audio) | 6 cuts in 12 s | V5/V8 |
| G10 | Lip-sync aligner + dialogue in shots | G talks in `WT` | T-054b, then T-054 |

**Do not reproduce** these reference artefacts:
- the 5-frame paper morph (`PB f084`–`f089`);
- hand-ownership swaps (`PB f053`→`f056`);
- the S2→S3 continuity break (`PB f111`→`f112`);
- the tub that changes between the two videos;
- small hair and design drift (the boy's hair silhouette in `PB f288`).

The character design references stay the target for appearance (OWNER_DECISIONS 2026-11-17).
