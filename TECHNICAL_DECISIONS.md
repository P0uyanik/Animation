# Technical decisions

Decision log. Each entry: decision, why, alternatives, consequences. Status: **Accepted** unless noted.
Revision 2 (2026-11-13) supersedes parts of the original architecture study (the doc
"Plush Animation Engine — Architecture & Feasibility Study") because the brief changed:
no Blender in the workflow, use the existing (unknown) computer, no GPU purchase.

## TD-01 Standalone app with its own content creation (supersedes study decision 2)
- **Decision:** All characters, props and environments are created inside Plush Studio. No DCC tool is required.
- **How:** style-specific procedural modeling instead of a general polygon modeler (see TD-02, TD-03).
- **Consequence:** we never build a Blender clone; modeling tools are narrow but fast for this style.

## TD-02 Soft modeling with signed distance fields (SDF)
- **Decision:** Characters and soft props are trees of rounded primitives (ellipsoid, capsule, round cone,
  round box) combined with smooth union / smooth subtraction, meshed with projected surface nets.
- **Why:** plush/felt shapes are soft blobs; SDFs give organic blends, symmetry, non-destructive editing,
  and **automatic skin weights** (each primitive belongs to a bone). Optional noise displacement gives felted lumps.
- **Alternatives:** polygon modeling + sculpting (years of tool work), subdivision surfaces (needs topology tools).
- **Consequence:** meshes are generated, not hand-topologized; no UV maps (see TD-06). Hard-surface sets use boxes/kits.
  Polygon editing can be added later for hard props.

## TD-03 Rigging: skeleton + automatic weights from primitives
- Linear blend skinning; weights = normalized exp(-distance/falloff) to the driving primitives, top 4 bones.
- Later: dual-quaternion skinning and pose-driven correctives where linear blending pinches.

## TD-04 Final renderer: CPU path tracer on Intel Embree 4 (supersedes study decision 3)
- **Why:** hardware unknown and no GPU purchase allowed. Embree runs on any x86-64 CPU (and Apple Silicon via
  embree-aarch64 builds), scales with cores, uses system RAM (fibres need lots of memory), and has native curve primitives.
- **Measured (cloud build machine, 4 cores, no GPU):** milestone frame 960x540, 64 spp, ~1.6M fibres: 77 s.
- **Alternatives:** Vulkan/DirectX ray tracing (needs RTX/RDNA2+ GPU), CUDA/OptiX (NVIDIA only), embedding Cycles
  (huge build, internal API). A GPU backend can be added later behind `PathTracer` if your machine has a capable GPU.
- Integrator: unidirectional path tracing, next-event estimation, MIS (rect + sky), sun = NEE-only cone light,
  thin-lens DOF with aperture blades, Russian roulette, firefly clamp. Deterministic per pixel/sample seeds.

## TD-05 Materials
- Layered surface BSDF: Lambert base, GGX specular (VNDF sampling), clear coat, Charlie sheen (Estevez & Kulla).
- `plush` = diffuse + sheen; `fiber` = Chiang et al. 2016 hair model (after pbrt-v3) for wool, fuzz and yarn.
- Energy conservation and pdf consistency are unit-tested.

## TD-06 Procedural textures in rest space (no UVs)
- Textures are evaluated from the rest-pose position ("pref") so they stick to deforming surfaces.
- Implemented: noise, knit, wood planks, wainscot wall, iris, blush. Image textures (triplanar) later.

## TD-07 Hair and fuzz: hybrid
- Hair = SDF hair cap (volume + lumpy displacement) + procedural surface fuzz + **yarn locks**
  (solid core tube + twisted fibres) that drape from the widest point of the head.
- Fuzz = procedural fibres bound to the mesh (triangle + barycentric + local frame), regenerated per frame,
  with stray long fibres for the soft halo. Rendered as Embree round linear curves.
- Spring-bone secondary motion is planned; strand simulation is deferred.

## TD-08 Denoising
- Intel Open Image Denoise 2 (optional, CPU). It is a local neural-network filter that generates no content
  (flagged earlier as question 6; continuing to use it unless you object).
- Fibre-aware albedo guide (fibre offset modulates the guide) + `denoiseBlend` keep fibre texture.

## TD-09 Viewport and UI: OpenGL 3.3 core + Dear ImGui (docking) + GLFW + GLEW (supersedes study decision 5 for the viewport)
- **Why:** runs on virtually any GPU/driver incl. integrated graphics; final quality comes from the path tracer,
  so the viewport only needs a fast preview. ImGui gives the fastest tool iteration.
- Viewport shows procedural texture colours via per-vertex evaluation; fibres hidden in the preview.

## TD-10 Data and storage
- JSON files: `*.scene.json` (shot: objects, characters, lights, camera, animation tracks), `*.character.json`.
  Format + version fields in every file. No database.
- Time: integer ticks at 705,600,000 per second; frames are doubles on the timeline.
- Mirror authoring (`"mirror": true`) is expanded at load; saving from the app writes the expanded form (see BUGS-03).

## TD-11 Scene evaluation
- `SceneEvaluator` turns (scene, frame) into an immutable `FrameSnapshot` (meshes, fibres, materials, lights, camera).
  The renderer only sees snapshots. Two evaluators in the app: fast preview (no fibres, coarser) and full quality.

## TD-12 Languages, build, dependencies
- C++23 (std::expected, std::format), CMake + Ninja; Linux via apt, Windows via vcpkg (`vcpkg.json`).
- Libraries: Embree 4, glm, nlohmann/json, stb, doctest, GLFW, GLEW, Dear ImGui (pinned commit), OIDN (optional).
- Python is only used for small content-editing scripts so far.

## TD-13 Animation model
- Per-channel tracks (vec3) with smooth (clamped cubic Hermite), linear and step keys.
  Track names: `camera.position`, `camera.target`, `camera.lens`, `<object>.position`, `<object>.yaw`,
  `<character>/<bone>.rot` (Euler degrees, XYZ), `<character>/root.loc`, `<character>.position`.

## TD-14 Render jobs and export
- `plush-render` renders stills/sequences; sequences resume (existing frames skipped, temp-file then rename);
  video via the FFmpeg command-line tool (H.264 now; ProRes later).

## Iteration 2 additions (2026-11-13)

## TD-15 Expressions as SDF morph targets
- An expression edits or adds primitives of one part (e.g. mouth corners, an open-mouth cavity). At build time
  every rest vertex is projected onto the edited surface (Newton steps on the SDF), giving a morph target with
  identical topology. Weights come from tracks `<character>/expr.<name>`. Unit-tested.
- Blinks use real eyelid shells on lid bones (rigid rotation), not morphs.

## TD-16 Geometric surface relief
- Parts can add displacement patterns (`strands` for hair, `knit` stockinette, `ribbed`) to the SDF before
  meshing, so stitches and hair clumps cast real shadows. Needs finer voxels (1.1–2.2 mm) on those parts.

## TD-17 Deformation quality
- Dual-quaternion skinning per character (`"skinning": "dualQuaternion"`), Laplacian smoothing of automatic
  weights per part (`skinSmoothing`). Milestone 01 keeps linear skinning (frozen).

## TD-18 Constraints in scene evaluation
- Two-bone analytic IK (`<character>/ik.<bone>` target + `.weight`), eye aim (`<character>/lookAt`),
  object attachment to bones without jumps (`attach: {to, frame, release}`), all evaluated statelessly per frame.

## TD-19 Sampling and level of detail
- Owen-scrambled Sobol sampling (Burley 2020): 10–14% lower error at equal samples (measured).
- Coverage-preserving fibre LOD: fibres thinner than ~1/4 pixel are thinned by k and widened by k
  (pinned lock cores kept). Measured on milestone 02 frame 34: 13.4M → 2.4M fibre segments, image
  difference RMSE 0.007 (below noise), frame 138 s → 108 s.
- Tile-based adaptive sampling (`adaptiveThreshold`), off by default.

## TD-20 Regression policy
- Milestone 01 is frozen (`girl_white_hair_m01.character.json`) and compared against a reference image in CTest
  (RMSE ≤ 0.03 at 320x180). Intentional engine look changes must re-baseline the image and log why.

## Iteration 3 additions (2026-11-13)

## TD-21 Hybrid character construction
- Soft SDF primitives stay for bodies, faces, garments and props (they suit plush forms and give automatic
  weights). Everything thin, long or curly is now an **explicit curve**: hair locks, curls, buns, fringe,
  lashes, glasses frames, drawstrings, backpack straps, bow loops. Evidence: three distinct reference characters.
- A curve = Catmull-Rom path through editable control points, tapered radius, optional helical curl, a solid
  core tube (any surface material) and an optional fibre halo grown from the core surface.
- Curves live in bone-attached **lock groups** in the character file (mirrorable) and are edited in Studio.

## TD-22 Hair construction recipe
- A thin hair base hugging the skull (stops at the hairline), then layered lock groups: back/inner layer,
  outer layer, crown locks lying over the top, fringe locks forming the hairline, coiled locks for buns.
  Rejected: one big cap volume (read as a hat in iteration 2) and more fibres alone (no silhouette change).

## TD-23 Glass and water
- Smooth dielectric material (`glass`, thin or solid, IOR), delta sampling, MIS-safe. Non-shadow-casting
  materials are excluded from a second, shadow-only acceleration structure (Embree's ray masks are not
  available in the system package). Denoiser guides are taken from the first non-glass surface.
- Water = height-field grid rebuilt per frame from analytic damped circular ripples; objects can float on it.
  Chosen over a fluid solver: deterministic, editable (ripple sources are data) and cheap.

## TD-24 Character identity and personality
- Characters carry a default pose and default expression weights (e.g. the boy's half-lidded, slightly frowning
  neutral) and character-prefixed material names so several characters share a scene.
- Characters are generated by `tools/charkit.py` (data in, data out); the app edits the same files.

## TD-25 Staged paper folding
- The paper boat has a flat "unfolded" layout per vertex; `<object>.fold` blends sheet → boat. Chosen over
  physical folding simulation (research problem) — it reads as folding at film scale and is fully keyable.

## Iteration 4 additions (2026-11-13)

## TD-26 Felted hair volumes (hybrid with curves)
- Fringes, crowns and tousled clumps are **SDF volumes made of blended round-cone clumps** (root → mid → tip), with
  strand relief, noise and a fibre layer; long wavy locks and curls stay explicit curves (TD-21), lying on a soft
  **hair-mass volume** so gaps read as hair, not background. Evidence: A's fringe and C's hair against the references
  (curves alone read as separate cords/noodles; a single cap read as a hat).
- Cost: parts with ~200 primitives. Made affordable by TD-27.

## TD-27 Brick-culled SDF meshing
- The mesher evaluates the field in 8³ bricks: bricks whose centre is far from the surface are filled with the centre
  value; near the surface a brick evaluates only primitives whose bounds are within (2 × (largest blend + relief + 2
  voxels) + 4 mm). Unit test: identical vertex count, vertices on the exhaustive surface (1.5e-8 m). The margin uses
  the largest blend of the part because smooth unions are applied in order (a smaller per-primitive margin changed
  the v2 face test slightly and was rejected).

## TD-28 Mouths: baked pockets + clean morphs
- A morph target cannot open a hole in a closed skin cleanly (vertices projected into a concave cavity crumple and
  their lining hides what is inside). So each character's **resting mouth is part of the skin SDF** (a pocket with
  dark interior, upper teeth and tongue parts behind it); expressions only **fill** (`mouthClose`) or **grow**
  (`surprise`) that pocket, which project cleanly, plus groove reshaping (smile/frown).
- Morph targets are relaxed after projection: neighbour averaging with the unchanged ring fixed (Tutte-style, no
  folds), 320 cheap passes with re-projection every 8th. 12 and 40 passes were tried and left lumps.

## TD-29 Skin subsurface scattering = random walk
- Chosen over diffusion profiles (BSSRDF) because it handles thin parts (ears, fingers) and concave faces without
  special cases and needs no extra sampling structures. The walk runs only inside its own mesh (one Embree scene per
  subsurface mesh), uses the Chiang 2016 albedo inversion and throughput-proportional channel selection (uniform
  selection produced fireflies). The subsurface lobe replaces a share of the diffuse; specular is unchanged.

## TD-30 Articulated hands with contact grasp
- Finger chains (thumb + 4 two-segment fingers) driven by a few parameters (curl, thumb, spread, index override)
  instead of per-joint keys. Grasping searches each finger's curl (bisection) until its tip rests on the object's
  sphere/cylinder in the hand's frame — the same call adapts to a thin stick or a large ball.

## TD-31 Procedural life layer
- Breathing, weight shift, head drift, automatic blinks and the head following the gaze with a lag are evaluated
  analytically from (frame, seed) on top of the keyed pose: deterministic, so any frame renders on its own, and
  no simulation state to cache. Off by default; scenes opt in per character (`"life": true`).

## TD-32 Actions compile to generated tracks
- A scene can list high-level actions (look, expression, reach, touch, walk). They are compiled at load into a
  separate `Clip::generated` that is consulted only where no hand-made key exists: manual keys always override, and
  saving never bakes generated keys into the scene. Actions read the scene (object positions, sizes, reach) so the
  same description adapts when objects move. This is also the layer an external assistant could write — a JSON
  list of actions — but **no assistant integration exists or is claimed**.

## TD-33 Director: rule-based shot planning
- Shots are planned from action beats with fixed, readable rules (establishing wide, medium on the start of a
  reach, insert at contact, reaction with the object, insert at placement, insert on a touch, wide in between;
  minimum shot length; overlaps cut in favour of the later action). Cameras stay on the master camera's side
  (180° rule), rotate away from characters in the way, focus on the subject, push in gently. Output is ordinary
  camera tracks (generated), so any hand-keyed camera track overrides it.

## TD-34 Frame rate
- Default 30 fps for new scenes (`FrameRate{30,1}`); iteration-3 scenes keep their explicit 24 fps test setting.
  Animation previews render at 640x360; stills at 1280x720.
