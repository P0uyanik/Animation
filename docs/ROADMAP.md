# Plush Studio roadmap v3 (2026-11-16, owner-approved)

**Goal:** a general-purpose, reusable animation system for complete plush/felt episodes. The owner's benchmark videos
(`docs/references/VIDEO_BENCHMARKS.md`) are the **quality bar**, not the product: every milestone delivers shared,
data-driven systems (libraries, specs, presets) validated on at least two characters or configurations, never
one-off scene work.

**Priority change (owner decision 2026-11-15):** visual quality and characters first. Deferred until needed: A3
personality styles, A5 behaviour system, motion capture (licence and format groundwork from T-007/T-009 is kept).

## Visual milestones (each is accepted by a render the owner reviews against the benchmark)
| ID | Milestone | Shared deliverable | Measurable acceptance |
| --- | --- | --- | --- |
| V1 | Test video 2–3 s (T-010) | end-to-end check of A1/A2 and the T-006 gaze fix | both characters, 1 emotion + 1 clip; eyes visible in every frame; no pops (smoothness limits from T-002); benchmark side-by-side; owner gap list |
| V2 | Plush material library | felt, wool, fibre, cotton/knit fabric, buttons, plastic; presets with fibre scale and fuzz | swatch sheet under benchmark light next to benchmark close-ups; same presets on 2 characters; render-time budget recorded |
| V3 | Girl complete | shared groom system (buns, long, curly) + shared garment library (shirt, vest, shorts, boots) | turnaround vs her reference sheet; deformation in 6 poses with no intersections; groom and garments driven only by spec |
| V3b | Boy 2.0 on the shared systems | new boy version built only from spec with `groom/1` hair, `garment/1` hoodie/trousers/shoes, material presets and shared eyes/lids; versions 1.0.0 and 1.1.0 stay frozen and unchanged | turnaround vs his reference sheet; zero boy-specific code; existing versions byte-identical |
| V4 | Hands, props, effects | grasp/hold/place/hand-over of props, paper folding as a prop deformation sequence, water surface with ripples, sparkle effect | 3 hand-interaction clips on 2 characters; water/sparkle test shot |
| V5 | Benchmark scene 10–15 s | multi-shot sequence with close-ups through `run_shot` + episode edit, in a **simple set** (a table, the props it needs, a plain backdrop) with benchmark-quality lighting and camera presets (warm daylight, bounce and rim light, shallow depth of field) | owner rates it against `video_paperboat`; gap list for the next round |
| V6 | Third character (specs only) | the generality test of V2–V3 | built with zero character-specific code; three-character scene |
| V7 | Classroom kit | modular room, windows, furniture and classroom props on the asset library (`plush.asset/1`) | the V5 scene re-shot in the classroom; assets reusable in a 2nd layout |
| V8 | First episode (2–2.5 min) | episode assembly, editing, sound hook-up | complete episode render |

## Execution order and agent split
1. **Now, in parallel:**
   - T-010 V1 test video (Claude Implementer, cloud Blender);
   - T-012 benchmark visual analysis → measurable visual target spec (Antigravity, multimodal);
   - T-013 asset library format and loader for props (Codex, engine/pipeline code).
2. **After V1:**
   - V2 material library (Claude Implementer, Blender), with Codex building the material-preset validation and
     tests.
3. **V3:** groom system, then garment library (Claude Implementer + Codex for the data, tests and engine side).
   Built generically, so the third character needs only specs.
4. **V4:** hands, props, effects (Codex: grasp/hold/place on top of the T-017 prop attachment, the paper-fold prop deformation, a water surface with ripples, sparkles; Claude Implementer: render checks).
5. **V5:** benchmark scene in a simple set with lighting/camera presets (Claude Implementer: lighting, shots, render; Codex: shot tooling).
6. **V6** when the third character's reference package arrives; **V7** classroom kit; **V8** first episode.

Third-character work that needs no references (groom structures, garment types, material presets, the shared
deformation checks) is done inside V2–V3.

**Change v3 (owner decision 2026-11-16):** hands, props and effects (V4) and the 10–15 s benchmark scene (V5) come before the classroom kit, which moves to V7. The benchmark scene uses a simple set with good lighting. Lighting and camera presets move into V5. Priority remains visual quality, natural animation and believable interaction.

**Change (owner decision 2026-11-16):** V3b Boy 2.0 added after V3. Architecture rule: anything that can be shared across characters is built as a reusable, character-independent system configured by spec, never per character (see `docs/process/OWNER_DECISIONS.md`).

## Priority v4 (owner decision 2026-11-16): reusable character creation at reference quality
Top priority is a shared character creation system that reproduces the owner's reference images (faces, eyes, noses,
mouths, expressions, proportions, hair, clothing, skin/felt/wool materials) for every current and future character,
with all differences in specs and assets. Order:
1. T-032 character fidelity measurement (supports, never replaces, visual judgement; final approval is the owner's).
2. T-031 face system v2 (eyes, nose, mouth, brows, lashes, cheeks/blush, proportions).
3. T-033 hair v2 (felted styles, soft volume, fine fibres) alongside yarn styles.
4. T-028 materials (sheen, fibres on garments) and the garment detail library.
5. Boy 2.0 (V3b) on all shared systems, accepted against his reference sheet.
6. Personality and acting (a per-character profile: posture, tempo, gaze, expressions).
7. V4/V5 effects and the benchmark scene (T-029 paper folding and the simulate stage are deferred until after 1–5).
