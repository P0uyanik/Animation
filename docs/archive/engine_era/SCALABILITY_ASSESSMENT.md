# Can the architecture reach the reference quality?

_Assessment after look iteration 2 (2026-11-13). Evidence: renders in `docs/milestone02/`, measurements below._

## Verdict

**Yes for image quality; the limits are authoring tools and CPU render time, not the architecture.**
Every trait of the references is either already produced by the current renderer and modeling system,
or can be added inside the same architecture as a new feature (no redesign). Two things will decide how
close we actually get: (1) better shape-authoring tools for hair clumps, hands and thin details, and
(2) render throughput on your CPU for longer films.

## Trait by trait

| Reference trait | Iteration 2 result | What is still missing | Architecture change needed? |
| --- | --- | --- | --- |
| Soft plush/felt body shapes | Smooth SDF shapes, collar, soles, larger head | Finger shapes, seams | No: more primitive types (swept tubes) |
| Fuzzy silhouettes and felt halo | 2.7M procedural fibres + strays; LOD keeps cost low | Per-material fuzz tuning | No |
| Wool / yarn hair | Clumpy cap with strand relief, scalloped fringe, 56 yarn locks | Lock shapes still read as sheets up close; cap partly reads as a hat | No: a guide-curve clump tool (draw locks), spring-bone motion |
| Knit and fabric detail | Real knit stitches as geometry, ribbed option | Embroidery, seams, folds from motion | No: decal/pattern layers; cloth simulation later |
| Expressive face | Blink lids, brows, smile, open mouth, eye look-at | Eyelashes, visemes for speech, cheek squash | No: expressions are just more morph targets |
| Natural movement | IK reach, grasp and lift via attachment, DQ skinning, smoothed weights | Finger poses, full-body balance, secondary motion | No: more constraints on the same evaluator |
| Soft sunlight, GI, shadows, DOF, bokeh | Path traced | Image-based backgrounds through windows | No |
| Doll skin | Matte with blush | Subsurface scattering | No: a new BSDF lobe in the path tracer |
| Glass, water, paper | Paper only | Glasses lenses, water table | No: dielectric and thin-surface lobes |

## What the SDF modeling approach will not do well (and the plan)

- **Thin, crisp, flat things** (paper being folded, glasses frames, table joinery): add swept-tube and
  thin-shell primitives plus a small polygon toolset for hard props.
- **Hand-drawn hair flow**: procedural lock placement gets 80% of the way; the last 20% needs a tool to
  draw lock guide curves directly on the head.
- **Cloth folds from motion**: needs cloth simulation on the generated meshes (they are ordinary meshes).

## Render performance (cloud build machine: 4-core Xeon 2.1 GHz, no GPU)

| Measurement | Result |
| --- | --- |
| Milestone 02 frame, 960x540, 64 spp, before LOD | 138 s |
| Same with fibre LOD | 108 s (image difference RMSE 0.007, below noise) |
| Fibre segments with / without LOD | 2.4M / 13.4M |
| Sampler: error at 64 spp vs 1024-spp reference | 0.0271 (random) → 0.0233 (Owen-Sobol) |
| Adaptive sampling (mean tile error 0.1), same frame | 96 s (-11%), image difference RMSE 0.0034 |
| Milestone 02 animation, 72 frames at 640x360, 32 spp | 35 s per frame on 3 cores; 22.8 s on 4 cores with adaptive sampling (27.5 min total) |
| Final-quality wide frame, 1280x720, 128 spp | 219 s |
| Final-quality close-up, 960x540, 128 spp (more fibres on screen) | 287 s |

**Projection to final quality (from the measured 1280x720/128 spp frame).** 1920x1080 has 2.25x the
pixels: about 8 minutes per frame on this 4-core cloud machine. A typical modern 8-core desktop CPU is
roughly 3–4x faster: about 2–3 minutes per frame. A 3-minute short (4,320 frames) is then about 6–9 days
of continuous rendering on one desktop, less with lower sample counts plus denoising for wide shots.

**Conclusion on speed:** quality is not blocked by the CPU, but throughput is. For short films this is
workable with overnight batches; for a regular series we will want (in order): adaptive sampling,
smarter light sampling, rendering on several of your machines, and an optional GPU backend if your
hardware allows. None of these require changing the scene, material or character formats.
