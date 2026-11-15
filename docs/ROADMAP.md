# Plush Studio roadmap v2 (2026-11-15, draft for owner approval)

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
| V4 | Classroom kit | asset library format + modular set (room, windows, desk, chairs, water tub, paper, crayons) + lighting/camera presets (warm daylight, shallow depth of field) | 3 camera setups rendered vs the benchmark; assets reusable in a 2nd layout |
| V5 | Hands, props, effects | grasp/hold/place/hand-over of props, paper folding as a prop deformation sequence, water surface with ripples, sparkle effect | 3 hand-interaction clips on 2 characters; water/sparkle test shot |
| V6 | Benchmark scene 10–15 s | multi-shot sequence with close-ups through `run_shot` + episode edit | owner rates it against `video_paperboat`; gap list for the next round |
| V7 | Third character (specs only) | the generality test of V2–V3 | built with zero character-specific code; three-character scene |
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
4. **V4:** classroom kit (Codex: the asset pipeline; Claude Implementer: modelling and lighting; Antigravity:
   finding licensed reference props and reviewing them).
5. **V5–V6:** Codex for interaction, prop attachment and effects code; Claude Implementer for rendering.
6. **V7** when the reference package arrives; **V8** after that.

Third-character work that needs no references (groom structures, garment types, material presets, the shared
deformation checks) is done inside V2–V3.
