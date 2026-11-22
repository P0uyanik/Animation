# T-206: tools to make faces closer to the references, and a wool look for hair (research)

Owner request 2026-11-22 ~18:20 CET. Research only: no character, generator, package or pipeline file changes. All
probes ran on scratch copies of the released masters (bpy 5.3.0, 4 CPU cores, no GPU). Inputs: the T-202 sheets
(released faces next to the references), [T-196](../../../audit/T-196/REPORT.md) (keep the engine/Blender split, prefer
Blender built-ins), [T-193](../T-193/README.md) (hair motion), [T-141](../T-141/README.md) (native hair curves),
[T-090](../T-090/README.md) (the existing reference-fit tool `tools/fit`). T-204 (Codex, running) builds the face
reference targets; this plan uses them and does not duplicate them.

## Short answer

- **Faces: fit the numbers in the character spec, faster and against better targets.** We already have a fit tool
  (`tools/fit`, T-090) that changes spec values and scores the result against the references. It got small gains
  (+2.8 and +0.3 points) because each try rebuilds the whole character (about 200 s), so it only managed 3 tries,
  and it compared full-body views where the face is about 100 pixels wide. The fix is not a new outside tool.
  It is (1) a **head-only build** for the fit, (2) **T-204's targets** as the score, and (3) a proper search with
  hundreds of tries. In our probe one head-only try took **0.044 s**. The same try in the full character took
  2.1 s, and a full rebuild takes about 200 s.
- **Don't fit the mesh directly as the main method.** When we change the skin, the eyes, lids, brows and glasses
  stay where they were, because they are separate objects (seen in the probe). The result also stops being spec
  data. A small final correction on the skin is possible later, but only inside a new face generator version.
- **Automatic face landmarks on our plush faces: only as a cross-check.** MediaPipe finds eyes and mouth on the
  reference fronts and 3/4 views. It fails on every side view, and its jaw outline lands on the neck or collar. On
  our boy render it detects the face at one image size and not at another. Differentiable renderers are too much
  machinery for about 30 numbers. One of them (nvdiffrast) is research-only, so we can't use it for YouTube.
- **Wool hair: brush the fibres along the locks, use less fuzz, and use smaller hair shapes.** In the references
  the wool fibres run along each lock, with a thin soft fuzz at the edges. Ours stick out from the surface like a
  carpet, and the hair shapes are larger than in the references. The best probe result (D below) used Blender's
  own hair-curve node groups through our existing T-141 tool: strands combed along the locks, felt fuzz at half
  length, curly flyaways off. It is not slower to render (72 s vs 77 s per 768 px frame) and it gives the same
  strands on every run. The volume has to come from the hair shapes in the spec, not from the shader.

## What the probes showed

| Probe | Result |
|---|---|
| **MediaPipe Face Landmarker** (Apache-2.0) on the 17 T-202 reference tiles and 17 render tiles | Landmarks found: reference fronts and 3/4 views 12 of 12, reference side views 1 of 5 at 256 px and **0 of 5 at 512 px**. On our renders: girl front yes, girl 3/4 and side no. Boy front only at 512 px, boy 3/4 only at 256 px, boy side no. Third girl front and 3/4 yes, side no. The eye and mouth points sit on the features. The jaw and chin points follow a human-shaped face and end on the neck or collar (overlays not kept; numbers in `results.json`) |
| **Landmark ratios, girl 0.14.0 vs ref_30 front** (hand-placed reference points, distances in eye spacings) | Chin / mouth / nose below the eyes: ours 0.72 / 0.43 / 0.29, reference 0.83 / 0.47 / 0.29. Eye spacing as a share of ear-to-ear width: 0.455 vs 0.449. **The point positions are already close.** So the "not normal" look comes from things points don't measure: eye opening shape and size, lids, cheek and jaw outline, glasses size, and the hair framing the face. T-204's measures have to cover these |
| **Shape-key fit, girl head** (two smooth deformations, Gauss-Newton search) | Reached the target chin and mouth ratios exactly in 17 tries. **0.044 s per try** with only the head loaded, 2.1 s per try in the full master (garments re-evaluate). A full rebuild in T-090 took 143–224 s. The eyes and glasses did not move with the skin (see the warning above) |
| **Wool hair, girl 0.14.0**, 4 variants, front and 3/4 views ([sheet](sheets/hair_variants.jpg), [100 % detail](sheets/hair_detail_100.jpg)) | **A** as released. **B** felt fuzz at half length, density ×0.7, curly flyaways ×0.2: less fuzz, but it shows dark blotches in the lock shader that the fuzz used to hide. **C** = B plus a yarn-groove bump in the shader: grooves visible on the bun, barely anywhere else (the "along the lock" texture coordinate is missing or different on several hair parts, e.g. all zero on the fringe). **D** = B plus strands combed along the locks (T-141 tool, low lift, no flyaway layer): **visible fibre direction along every lock, closest to the references**. Still missing: the thin bright fuzz at the edges, and the shapes are too large. Render time at 768 px / 16 spp, front: A 77 s, B 64 s, C 55 s, D 72 s. Two separate D builds gave the same strand hash `267db152…` |

## Faces: options ranked

Quality fit: how well it brings our faces closer to the references. Effort is in task-days (E).

| # | Option | Quality fit | Determinism, headless bpy 5.3 on CPU | Licence | E | Risks |
|---|---|---|---|---|---|---|
| **F1** | **Spec-parameter fit, upgraded**: `tools/fit` with a head-only build, T-204 targets as the score, and a seeded search over 100–300 tries (scipy Powell/Nelder-Mead or `cma`) | High: changes only what the generator can make, so every result is still a valid, reviewable spec | Yes: the spec values are the output, the search is seeded, Workbench passes. Scoring already runs headless | ours; scipy and `cma` are BSD | 4–5 | The look may need a knob the spec lacks (then F3). Overfitting to one view (fit three views together) |
| F2 | Speed-up for F1: measure once how each parameter moves each target (about 30 head-only builds), then solve directly (Gauss-Newton). The probe used this | High, together with F1 | Yes | ours | 1–2 | It can mislead for large changes. Use it to get close, then F1 checks the result with real builds |
| F3 | New face/head knobs where F1 gets stuck, e.g. outline control points for the head shape, glasses size and height, eye opening shape. Added as spec data in a new generator version | Medium–high, only where needed | Yes | ours | 2–3 | A new generator version, and re-approval of characters that switch to it |
| F4 | A last skin correction after F1, stored as a corrective shape key, with eyes, lids, brows and glasses placed again after it | Medium: fixes outline details | Yes, if stored as data | ours | 2 | Features detach if they are not placed again. The expression shape keys must be rebuilt on top. Only inside a new face generator version |
| F5 | Automatic landmarks (MediaPipe; anime landmark detectors) | Low–medium: cross-check only | MediaPipe: yes on CPU. The model downloads from `storage.googleapis.com` (reachable) | MediaPipe Apache-2.0. `kanosawa/anime_face_landmark_detection` has **no licence** (not usable). `nagadomi/animeface-2009` MIT, 2009-era | 0.5 | Fails on side views and on our renders at some image sizes. Wrong jaw outline |
| F6 | Differentiable rendering: Mitsuba 3 (BSD-3, CPU variant `llvm_ad_rgb` installs and runs here), PyTorch3D (BSD, no ready Linux wheel; needs torch, whose CPU wheel server is blocked), nvdiffrast | Medium for mesh fitting only. Our generator is Blender Python, so we can't differentiate through it | Mitsuba: yes on CPU. nvdiffrast needs an NVIDIA GPU | **nvdiffrast: "non-commercially means research or evaluation purposes only" (excluded)** | 8+ | A second renderer to keep in step with Cycles. Weeks of work for about 30 numbers that F1 can search directly |
| F7 | Human-generator add-ons: MPFB2/MakeHuman, MB-Lab. Paid ones for comparison: KeenTools FaceBuilder, Human Generator, Reallusion Headshot | Low: realistic human heads, not plush faces. Adopting one would replace our face generator | MPFB2 runs in bpy | MPFB2 code GPL-3, assets CC0. **MB-Lab: models made with it are AGPL-3** | — | Wrong style. A topology change would break the rig and expression keys |
| F8 | Camera matching (fSpy, GPL-3) | Low: it needs straight lines in the picture, and our turnaround images have none. We already estimate 70 mm and the elevation, and the fit registers scale and offset | — | GPL-3 app | — | — |
| F9 | Hand sculpting in Blender (GUI) | High in skilled hands | The stored result is deterministic | — | ? | Needs an artist. Not code-driven. Same detaching problem as F4 |

**Compare metrics to use** (already in `tools/fit` and `tools/fidelity`, or cheap to add): landmark error as a share
of head height (exists); eye-opening IoU per eye (exists); figure IoU (exists); **face-outline distance below the
hairline** (new, from the reference masks); iris size and lid-line position (T-204); colour checks (exist).
Perceptual scores (LPIPS) need torch and pretrained weights from blocked hosts, so they are left out.

## Wool hair: options ranked

| # | Option | Quality fit | Determinism, headless bpy 5.3 on CPU | Licence | E | Risks |
|---|---|---|---|---|---|---|
| **H1** | **Combed strands along the locks** (D): Blender's own hair node groups (Interpolate, Clump, Curl, Frizz, Noise, Set Profile; all present in our build) through `groom/hair_curves.py`, made a groom option in the build. Felt fuzz shortened, curly flyaways off or very sparse | High: the fibre direction matches the references | Yes. Strands are made in the rest shape, and two runs gave the same hash. Built and rendered headless here | Blender built-ins | 3–4 | T-141 measured about 5× slower shot assembly because of the per-frame "follow the surface" step. Needs a baked binding. Strands also grow on hidden inner faces (cull them) |
| **H2** | **Smaller hair shapes**: thinner locks, lower crown, smaller bun and side volume. Uses existing groom spec values (structure heights, thickness, `tips`, `clump`), and the F1 fit can tune them against the reference hair outline | High: the volume difference is the largest one on the sheets | Yes (spec data) | ours | 1–2 per character | Hair-to-body contact changes, so T-183/T-194 checks must be rerun |
| H3 | **Edge fuzz**: a thin, short, sparse fibre layer only on lock edges and tips (by curvature or a tip attribute), Principled Hair BSDF (Chiang; Huang also present) | Medium–high: it gives the soft bright rim of the references | Yes | built-ins | 1 | It must not depend on the camera angle (shots move). Rim light strength also depends on the lighting |
| H4 | **Clean up the lock shader**: less contrast in the dark noise, soft sheen, slight colour change along the length | Medium: needed once the fuzz is reduced (probe B) | Yes | ours | 1 | Colour checks (`colour_checks.json`) must still pass |
| H5 | Yarn-groove bump in the shader only (C) | Low–medium: cheap, but our hair parts lack a consistent "along the lock" coordinate | Yes | ours | 1 + coordinate fix | Hardly visible at shot scale |
| H6 | Outside yarn/wool generators (`qwiglydee/fabric-o-matic`, MIT/CC0, texture only; university yarn projects, mostly unlicensed) | Low: textures for cloth, not hair locks | — | mixed | — | Immature. Nothing ready for hair |
| H7 | Blender's experimental hair simulation (motion) | Not a look tool. T-193 already said no for now | — | — | — | — |
| H8 | Paid groom add-ons (Hair Tool, HairFactory and similar) | Comparison only. They build on the same hair curves and node groups | — | paid | — | Not allowed |

## Recommendation and plan

**Faces: F1 + F2, with F3 only where the fit gets stuck. Hair: H1 + H2 + H3 + H4.** All of it is our own code on
Blender built-ins, so it fits T-196's architecture. Every result is spec data, reviewed on T-202-style sheets
before any new character version.

| Step | What | E | Depends on |
|---|---|---|---|
| 1 | **Head-only fit build**: build the head skin and face features (eyes, lids, brows, nose, mouth, ears, glasses), skip garments, hair and fibres. Workbench face crops at the reference crop size | 1.5–2 | — |
| 2 | **Fit score from T-204**: read `targets.json` and the T-204 measures as score terms per view. Add the face-outline term. Use the close-up uploads (G01–G03 for the girl, upload 14 for the third girl) at full resolution instead of the full-body sheet views | 1–1.5 | T-204 merged, step 1 |
| 3 | **Search**: seeded Powell or CMA-ES over about 20–40 head and face spec values, 100–300 tries per character (under 1 h on CPU), F2 start from about 30 builds | 1–1.5 | 1, 2 |
| 4 | Run the fit for the three characters → override proposals → full build → T-202 sheet → **owner review** | 1 per character | 3 |
| 5 | (only if needed) F3 new knobs in a new face/head generator version | 2–3 | 4 |
| 6 | **Hair H1**: `hair_curves` as an opt-in groom key, with a baked binding, inner faces culled, and the flyaway layer optional | 3–4 | — (can run in parallel with 1–4) |
| 7 | **Hair H3 + H4**: edge fuzz layer and lock shader clean-up | 2 | 6 |
| 8 | **Hair H2**: hair shape sizes per character (by hand, or by the step 3 fit on hair outlines), then rerun the T-183/T-194 contact checks | 1–2 per character | 3 (if fitted), 7 |
| 9 | New character versions with sheets, regression and owner approval | 1 per character | 4/5, 8 |

Total about 12–16 task-days for the core (steps 1–4 and 6–7) plus 2–4 per character. Order: steps 1 and 6 can
start now and run in parallel. Step 2 waits for T-204. **How T-204 fits in:** its `targets.json` becomes the fit's
target list. Its measuring script must also run on our Workbench crops, so that the same code measures the
reference and our render. If its measures are pixel-based, the fit only needs the camera and registration from
`tools/fit` to put both in the same coordinates.

## Questions for the owner

1. Faces: is it OK that the fit only changes existing spec values first (steps 1–4), and new face knobs come only
   if the review shows they are needed?
2. Which views count most for "close to the references": front, 3/4 or side? The fit weighs them equally today.
3. Hair volume: should the hair be about as large as in the references (clearly smaller than now), or only a bit
   smaller?
4. Wool look: is probe D ("combed strands") the direction you want? Should curly flyaways stay a little or go
   completely?
5. Can a hair version and a face version of the same character ship together, so there is one review instead of two?

## Appendix

### A. Files
- `sheets/hair_variants.jpg`: reference ref_30 next to A–D, front and 3/4 (768 px renders scaled to 340 px).
  `sheets/hair_detail_100.jpg`: crown and fringe at 100 % (A, C, D) next to reference G04.
- `results.json`: all probe numbers (render times, strand counts and hashes, MediaPipe detections per tile, face
  fit numbers).
- `probes/`: the scripts. `hair_probe.py` (variants base, lowvol, yarn, combed; the combed blend is first made with
  `pipeline/charsys/groom/hair_curves.py --options probes/combed.json`), `face_probe.py` (shape-key fit,
  `--head-only`), `lm_check.py` (landmark ratios), `mp_probe.py` (MediaPipe, run in a separate venv with
  `mediapipe` 1.2.3 and the model files from `storage.googleapis.com/mediapipe-models/...`). They read the released
  masters and write only to the output folder you give them.

### B. Reproduce (repository root, scratch output)
    blender -b --factory-startup -P pipeline/charsys/groom/hair_curves.py -- --blend <girl 0.14.0 master> \
        --out <scratch>/combed.blend --options docs/evaluation/characters/T-206/probes/combed.json
    blender -b --factory-startup -P docs/evaluation/characters/T-206/probes/hair_probe.py -- <out> <master or combed.blend> \
        base|lowvol|yarn|combed 768 16          # yarn as in the sheet: YARN_FREQ=150 YARN_STRENGTH=1.0 TAG=150
    blender -b --factory-startup -P docs/evaluation/characters/T-206/probes/face_probe.py -- <out> <girl master> \
        assets/characters/girl_auburn_bun_glasses/references/annotations/sheet30_front.json [--head-only]

Renders used all cores and seed 0. They are not bit-exact like the pinned single-thread builds. They are only for
looking at.

### C. Licences checked (2026-11-22, from the projects' own licence files unless noted)
MediaPipe Apache-2.0 · Mitsuba 3 BSD-3 · PyTorch3D BSD · **nvdiffrast NVIDIA Source Code License, research or
evaluation only** · MPFB2 code GPL-3, assets CC0 · **MB-Lab code GPL-3, database and generated models AGPL-3** (renders
excluded) · fSpy GPL-3 (GitHub metadata) · fabric-o-matic MIT/CC0 (GitHub metadata) · anime landmark repos: none or
MIT. Blender's hair node groups ship with Blender (`datafiles/assets/nodes/procedural_hair_node_assets.blend`).
The project already uses them (T-141).

### D. Hosts
Reachable: `pypi.org` (mediapipe, mitsuba installed in a scratch venv), `storage.googleapis.com` (MediaPipe
models), `github.com` via git and the search API, `polyhaven.com`, `ambientcg.com`, `raw.githubusercontent.com`.
Blocked by the proxy (no connection): `download.pytorch.org` (torch CPU wheels, needed for PyTorch3D and LPIPS),
`huggingface.co` (many landmark and perceptual models), `dlib.net` (dlib landmark model), `www.adrianbulat.com`
(face-alignment models), `docs.blender.org`, `extensions.blender.org`. None of them is needed for the
recommendation.
