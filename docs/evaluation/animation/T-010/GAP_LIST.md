# T-010 gap list: V1 test video vs the benchmark videos

Compared: `t010.mp4` / `benchmark_compare.png` (frames 24 and 44) against `docs/references/video_watertable.mp4`
(frame 60) and `video_paperboat.mp4` (frame 144). Ranked by how much each gap is visible. Each gap is mapped to a
roadmap milestone (`docs/ROADMAP.md`).

| # | Gap (what is visible) | Benchmark | T-010 render | Milestone |
| --- | --- | --- | --- | --- |
| 1 | **The girl is incomplete** | wool hair in buns with a bow, shirt, vest, shorts, round glasses | bald, skin-coloured body without clothes; only the face and glasses exist | **V3** (groom + garment library) |
| 2 | **The boy's eyes close when they look up relative to his head** | eyes stay open and readable in every shot | open only while the baked eye pitch is about ≤ −1°; one eye open and one closed at about 0° to +2° (frames 4–5, 32–33); closed from about +3° (frames 34–60; also heavy lids in frames 1–3). The bake stays inside the T-006 limits (max +14.3° up, limit 20°) | **none of V2–V6**: master-side eye/lid rig of the frozen boy 1.0.0. Needs an owner decision (see the T-010 report) |
| 3 | **Materials** | felt and wool with visible fibres, fuzz and soft sheen; knitted hoodie | smooth, uniform plastic/clay surfaces (skin, hoodie, trousers) | **V2** (plush material library) |
| 4 | **Hair** | yarn-like curly locks with fibre texture and fuzzy silhouettes | the boy: glossy solid clumps (smooth shader, hard silhouette); the girl: none | **V2** (fibre material) + **V3** (groom system) |
| 5 | **Set and light** | sunny classroom: windows, shelves, toys, warm daylight with bounce and rim light, coloured surroundings | empty grey wall and floor, flat neutral light (existing e902 lights; the project has no warm-daylight preset) | **V4** (classroom kit + lighting presets) |
| 6 | **Depth of field** | shallow, background softly blurred, focus on faces | everything sharp (`fStop` 0) | **V4** (camera presets: shallow depth of field) |
| 7 | **Motion and acting** | small natural movements, weight, hands busy with props, reactions to each other | scripted holds and clips: stiff A-pose arms at the start, mechanical wave (played at 1.35× to fit), no secondary motion, no interaction, no motion blur | **V5** (hands, props, interaction clips); acting quality beyond that is not yet a milestone |
| 8 | **Clothing detail** | ribbed cuffs, seams, buttons, layered garments | the boy's hoodie is one smooth shell (drawstrings and straps only) | **V2** (fabric presets) + **V3** (garment library) |
| 9 | **Shot design and editing** | several shots, close-ups of hands and faces, framing at the characters' level in a scene | one static medium two-shot, no cut | **V6** (benchmark scene 10–15 s, multi-shot) |

Not compared: sound, the third character (V7) and effects (water, sparkles: V5).
