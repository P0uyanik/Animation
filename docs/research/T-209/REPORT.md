# T-209 · Accurate, consistent, animation-ready faces for our three characters (research)

Owner request 2026-11-22 ~20:05 CET. Research only. No character, generator, package or CURRENT version changes.
Branch `t-209-claude-face-approach-research` from `main@df3736b`. This report builds on
[T-202](../../evaluation/characters/T-202/README.md) (face sheets vs references),
T-204 (Codex, branch `t-204-codex-face-targets@d29fc7bf`, not on main yet: 50 face measures per view, targets and tolerances),
[T-206](../../evaluation/characters/T-206/README.md) (head-only fit at 0.044 s/try, MediaPipe, licences),
[T-196](../../audit/T-196/REPORT.md) (the engine plans motion, Blender measures and corrects) and T-207 (branch
`t-207-claude-hair-flock`, opt-in flock finish for hair). It does not repeat their probes.
**M** = measured here or in those tasks, **E** = estimate. E (effort) is in task-days.

## Short answer

1. **We already have the right kind of tool.** `face_generic/3` is a reusable, data-driven procedural face
   generator in Blender Python: about 340 numeric spec values per face (M, auburn: eyes, lids and lashes 148,
   mouth 66, head shape, layout and cheeks 33, ears 25, brows 13, …), a shared expression library (13 action units, 14 + 6 presets), a lid-seam blink, rig
   controls driven by `face_*` properties, and the engine's face layer for blinks, gaze and emotions. All three
   released characters build with it: boy 2.3.0, auburn 0.14.0, white-haired 0.1.0. No free outside tool makes
   plush faces better. The free ones are realistic-human tools (MPFB2, MB-Lab, BlenRig), and the useful
   fitting/landmark models are non-commercial or need hosts that are blocked.
2. **The gap is accuracy, not animation.** T-204 finds **120 of 233 measures outside tolerance (99 within, 14
   unscored)**. Examples: the boy's lower face is too short (mouth to chin 2 % vs 11 % H) and too narrow (cheek 75 %
   vs 92 % F). Auburn's cheek is hidden under the glasses and the temple lock. White-haired's eye opening is too
   flat (h/w 0.69 vs 0.95). These are rest-face proportions.
3. **Our expressions already keep identity (probe, M).** On all three masters, no shape key moves the cranium,
   ears, back of the head or neck by more than **0.074 mm**. No key changes the front head width at eye or cheek
   height (**0.00 mm**). So drift does not come from the expressions. It would come from (a) new rest-face changes
   that the expressions are not rebuilt on, and (b) new keys or correctives. Both can be gated by a measured
   **identity card**.
4. **Recommendation: "fit-and-lock" on our own generator.** (i) Measure renders automatically: project the 3D
   landmarks and use per-feature masks, so no detector is needed, at every angle including side and back. Measure the
   references once by hand (T-204). (ii) Use a head-only fit to search the existing knobs. (iii) Add a
   `face_generic/4` with the few knobs the fit lacks. (iv) Rebuild the expressions on the fitted face.
   (v) Freeze an identity card per version and check it at build time and on baked shots. All of it is free, runs
   on CPU (no GPU), and fits the T-196 split. **About 20–25 task-days**, or about 9–11 Opus and 6–8 Sonnet sessions
   (E). Phases are in section B.

## Probe: does animation change identity? (M, `probes/identity_drift_probe.py`, about 3 min CPU)

Each shape key on `body_skin` was compared with Basis. The zones come from the build's `LM_*` landmarks. The eye
zone is 1.35 × the eyeball radius (48–52 mm: these are large plush eyes), the mouth zone is 45 mm and the nose
zone is 20 mm. "Outer face" is the head skin outside all three zones. "Far" is more than 2 eye radii from the eyes
and more than 90 mm from the mouth: cranium, ears, back of the head and neck.

| Character | Keys | Far zone, max | Outer face, max (key) | Front width change, eye and cheek bands |
|---|---|---|---|---|
| boy 2.3.0 | 16 | 0.003 mm | 1.37 mm (MouthSmile) | 0.00 mm, every key |
| auburn 0.14.0 | 22 | 0.074 mm | 3.05 mm (MouthSmile, SmileClosed) | 0.00 mm, every key |
| white-haired 0.1.0 | 22 | 0.020 mm | 2.90 mm (MouthSmile, SmileClosed) | 0.00 mm, every key |

The outer-face motion is the cheek lift of the smile family, which is intended. On the girls, Blink also moves skin
inside the mouth zone by 5–6 mm. That is lower-lid skin, because the zones overlap on these large-eyed faces. It
should be checked once in phase P4. Per-key numbers are in `probes/drift_*.json`.

## A. The ten points: what we have, the gap, and the options

Licence notes: "ours" = our code. Blender add-ons that ship with Blender are GPL, but what they produce (meshes,
renders) is not restricted. "Excl." = excluded by the owner rules (paid, or non-commercial). GPU: "no" = runs on
our CPU containers.

**1 · Reusable, parameter-driven generator.** *Now:* `face_generic/3` + `face_features.py` + `face_v3/` (lids
trimmed at the corners, socket skin, felt eye). Character data only, no character names in the code. *Gap:* a few
shape controls are missing: a free head outline (front and profile), the eye opening shape, upper-lid droop, glasses
size and height.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Keep it and add `face_generic/4` knobs** (outline control points, superellipse eye opening, lid droop, glasses frame) | + every result stays reviewable spec data; rig, keys and engine names unchanged. − needs a new version and re-approval per character | ours | no | 3–4 |
| Rewrite the generator in Geometry Nodes | − GN cannot write shape keys or vertex groups that stay stable when the topology changes; a full rewrite | built-in | no | 15+ |
| MPFB2 / MB-Lab / Human Base Meshes as the base | − realistic humans, wrong style; MB-Lab models are AGPL-3; a new topology breaks the rig and keys | GPL-3 + CC0 / AGPL / CC0 | no | — |
| KeenTools FaceBuilder, Human Generator, Faceit | paid (FaceBuilder needs a paid core library for its add-on) | **Excl.** | — | — |

**2 · Matching the references.** *Now:* `tools/fit` (spec search, Workbench, landmark and IoU score) got +2.8 and
+0.3 points because each try was a full ~200 s build (T-090). T-204 has 50 measures per view with tolerances. T-206
cut a head-only try to 0.044 s (M). *Gap:* T-204's measures are traced by hand, on renders as well as references,
so a fit cannot score hundreds of tries.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Head-only fit (T-206 F1+F2) scored by an automatic render-side T-204 measurer**: the same definitions computed from projected `LM_*` points plus skin, iris, lid and hair masks from Workbench object IDs | + exact on renders at every yaw; references traced once (already done); the score is the T-204 table. − references are 99–590 px and some smile, so tolerances stay wide | ours; scipy, `cma` BSD | no | 3–4 |
| Landmark detectors on both sides (MediaPipe; hysts anime-face-detector) | + automatic. − MediaPipe fails on every side view and on some render sizes (T-206). The anime detector is MIT but frontal only, needs torch and Hugging Face weights (both blocked) | Apache-2.0 / MIT | no | 0.5 |
| Differentiable rendering (Mitsuba 3; PyTorch3D; nvdiffrast) | − cannot differentiate through our Python generator; a second renderer. nvdiffrast is research-only | BSD / BSD / **Excl.** | nvdiffrast yes | 8+ |
| 3D morphable head models (FLAME, DECA, EMOCA) | − realistic human space; the model licences are non-commercial | **Excl.** | often | — |

**3 · Independent geometry controls** (roundness, cheeks, jaw, nose, lips, forehead). *Now:* separate spec values
for most of them (`shape.cheek_*`, `outline_*`, `lower_face.jaw_*`, `forehead_*`, `chin_*`, `nose.type/size`,
`mouth.*`). *Gap:* the values interact through one outline function. The fit needs a measured sensitivity matrix
(about 30 builds, F2) to see which knob moves which T-204 measure, and the missing knobs from point 1.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Sensitivity matrix + regional deformers with compact falloff** in `face_generic/4` (each knob moves only its region; checked with the drift probe's zone method) | + "independent" becomes measured (off-region motion ≈ 0). − one more generator round | ours | no | incl. in 1 |
| Corrective sculpt stored as a shape key (T-206 F4) | + fixes the last details. − eyes, lids, brows and glasses must be placed again afterwards, and the expressions rebuilt | ours | no | 2 |
| Hand sculpting | − needs an artist; not code-driven | — | no | ? |

**4 · Eye system.** *Now:* ellipsoid eyes with a layered or felt shader and catchlights, lid shells trimmed at the
corners, lid-seam blink (computed closing angle, the lash lands on the seam), strand lashes, felt or embroidered
brows, lid tracking (0..1) with gaze, and an engine that varies the blink (double blinks, blinks on gaze shifts,
emotion-dependent speed). *Gap:* the eye opening shape and size vs the references (T-204: white-haired h/w 0.69 →
0.95, boy needs drooping lids), and no measured check that the blink closes fully at 3/4 and side views.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Keep it; add opening-shape and droop knobs; add a blink-closure check** (no sclera pixels at Blink = 1 from 5 yaws, from the Workbench masks) | + small, measurable | ours | no | 1.5 |
| Rigify face eyes (built-in "skin" system) | − bone-based lids on our separate lid shells; we would duplicate the lid-seam work | built-in | no | 3 |
| BlenRig 6 facial system | − realistic film rig for Blender 4.x, untested on 5.3, its own workflow | GPL-3 | no | 5+ |

**5 · Reusable expression shape keys.** *Now:* one shared library (action units → presets) baked per character,
with per-spec overrides and custom presets, and L/R splits. The probe shows they stay local (table above). *Gap:*
the keys are baked once on the rest face, so a fitted rest face needs a rebuild (the build already does this). There
are no combination correctives yet (smile + blink, squint + smile), and no per-key identity budget is stored.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Keep the library; add 2–4 combination correctives (driver products, the mechanism T-196 L2 plans for joints); write the per-key budget into the identity card** | + same names for rig and engine. − a few new keys per character | ours | no | 2 |
| ARKit-52 key naming | + a common standard. − we drive no capture, and the engine already maps names | — | no | — |
| Pose library / asset shelf poses | + good for hand-posing in the GUI. − nobody animates by hand here (T-196) | built-in | no | — |

**6 · Facial rig.** *Now:* Rigify deform rig with `DEF-eye` bones (gaze), a jaw bone + JawOpen shape with preset
jaw drivers, `face_<Preset>` controls driving the keys, lid tracking. The engine `face_layer` resolves channels
(`browUp`, `mouthDown`, …) per character, and visemes (`content/visemes/shared_visemes.json`) drive `jawOpen` and
`mouthUp`. *Gap:* the visemes use only two channels (no rounding or pucker). A pout/O exists but is not mapped.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Keep it; map `MouthO` and `MouthPout` into the O/U/WQ visemes; add a GUI pose panel only if a person ever animates** | + small change to engine data, no engine code | ours | no | 0.5–1 |
| Rigify face rig, BlenRig, Auto-Rig Pro, Faceit | − duplicates our controls; ARP and Faceit are paid | built-in / GPL-3 / **Excl.** | no | 5+ |

**7 · Automation (Python, Geometry Nodes).** *Now:* everything is a headless build in bpy 5.3 (pinned, single-thread
deterministic). Geometry Nodes are used for the groom and hair curves (T-141, T-207). *Gap:* none in kind; the fit
loop and the measurer are the missing automation.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Python/bmesh for the face skin, lids and keys (stable vertex order); GN only for strands (lashes as curves, flock fuzz)** | + shape keys and weights stay valid; matches the current code | built-in | no | — |
| GN for the whole face | − loses shape keys and stable topology (point 1) | built-in | no | 15+ |

**8 · Identity preservation.** *Now:* the geometry fingerprint (`fingerprint_v2`, determinism), version pointers,
owner approval. Nothing measures identity as such. *Gap:* there is no stored "what this face is" to compare a new
version, an expression or a shot frame against.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Identity card per version**: projected landmark ratios at 8 yaws, skin and hair silhouettes, T-204 render-side measures, and the drift probe's per-key zone budgets. Checked in the build gate and on **baked shots** by evaluating the deformed head mesh at sampled frames (geometry only, no render) | + catches drift from versions, correctives or engine weights > 1. − one more gate file per character | ours | no | 2 |
| Perceptual identity embeddings (ArcFace, DINOv2) | − human-face models, or weights on blocked hosts | mixed | no | — |

**9 · Automated validation, all angles.** *Now:* T-202 sheets (front, 3/4, side), `tools/fidelity` metrics (IoU,
landmarks, colour). The reference indexes have yaws −135 to 180, including backs (boy 16 views, auburn 6,
white-haired 86). *Gap:* no automatic per-angle score; side and back are judged by eye.

| Option | Pros / cons | Licence | GPU | E |
|---|---|---|---|---|
| **Per-yaw score sheet**: front and 3/4 use the T-204 measures; side uses profile depth, nose and chin advance and cheek bulge from the skin contour; back and 3/4-back use hair and head silhouette IoU and outline distance (chamfer, % H) against the reference masks; plus SSIM on aligned grey crops as a coarse look check | + measurable at every angle the owner named; CPU; seconds per view. − SSIM is weak on plush texture, so it is only a cross-check | ours; scikit-image BSD, OpenCV Apache-2.0 (both from pypi) | no | 2 |
| LPIPS or DISTS perceptual distance | + closer to "looks similar". − needs torch and pretrained weights (`download.pytorch.org` blocked) | BSD / MIT code | no | — |

**10 · Production integration.** All recommended parts are our code on Blender built-ins plus BSD/Apache Python
packages from pypi. No GPU: a Workbench head-only try is 0.044 s and a Cycles review sheet is minutes on 4 cores.
They fit the pipeline as-is: spec → build → version → T-202 sheet → owner. The engine reads only the existing names.
The T-207 flock hair is an independent groom option, and the face and hair releases can ship together. Excluded
because paid: KeenTools, Faceit, Auto-Rig Pro, Human Generator, Reallusion. Excluded because non-commercial or
copyleft output: nvdiffrast, FLAME/DECA, MB-Lab models.

## B. Recommendation: fit-and-lock on `face_generic` (phased)

| Phase | What | E | Session (E) |
|---|---|---|---|
| P0 | Owner decisions (section D); merge T-204 | 0.5 | Supervisor |
| P1 | **Render-side T-204 measurer**: head-only Workbench build, object-ID masks (skin, iris, lids, brows, hair, glasses) and `LM_*` projections, computing T-204's definitions at 8 yaws. Validated against T-204's hand traces of the same T-202 renders (agreement within tolerance) | 3–4 | 1–2 Opus |
| P2 | **Fit on existing knobs**: F2 sensitivity matrix (about 30 builds), then seeded CMA-ES/Powell over front, 3/4, side and back with owner weights. A proposal and a T-202-style sheet per character | 2 + 0.5 per char | 1 Opus + 2 Sonnet |
| P3 | **`face_generic/4`** where P2 gets stuck: outline control points (front and profile), eye-opening superellipse and lid droop, glasses frame size. Regional falloff, checked with the zone method. Refit | 3–4 | 2 Opus |
| P4 | **Expressions and rig**: rebuild the keys on the fitted rest face; 2–4 combination correctives; blink-closure check at 5 yaws; Blink and mouth-zone overlap check; map MouthO and Pout into the visemes | 2–3 | 1–2 Opus |
| P5 | **Identity card + gate**: per-version card, a `check_all` test, and a shot-level check on baked frames (deformed mesh, no render) | 2 | 1 Opus + 1 Sonnet |
| P6 | **Release**: new versions per character (with the T-207 hair if approved), Cycles sheets, regression, owner review, at most 2 review rounds | 1–2 per char | 1–2 Opus + 3 Sonnet |

**Total: about 20–25 task-days**, or 9–11 Opus and 6–8 Sonnet sessions. P1 and P5 can start in parallel. P2
needs P1. P3 needs P2's stuck list.
**Cost (E, from T-176's measured rates):** Opus build or visual sessions cost about $15–35 each when kept under
about 250k context. Sonnet run and sheet sessions cost about $4–10 each. That is about **$200–420** in total. The
biggest saving is the head-only loop: hundreds of tries in under 1 h of CPU instead of 200 s builds.

## C. Risks

- **The references limit accuracy.** They are 99–590 px and partly smiling, and T-204 marks many values E. Mitigation:
  fit to tolerance bands, not to exact numbers. Score smiling references against a matched smile key.
- **Overfitting one view.** Mitigation: fit all yaws together with owner weights, and keep a held-out reference per
  character for checking only.
- **A render measurer that disagrees with the hand traces.** P1 must show agreement before P2 uses it.
- **Features detaching when the skin changes** (T-206). Mitigation: knobs inside the generator, so the features are
  placed again from the new skin, rather than mesh edits.
- **New generator version and re-approval** for all three characters. The released versions stay unchanged until the
  owner approves.
- **Hair hides the face** (auburn temple lock, white-haired fringe). Some face measures are really hair measures, so
  they must be coordinated with T-207 and the groom shapes (T-206 H2).
- **Expressions that pass the zone budget but look wrong** (e.g. a cheek lift that hides the eyes). The sheets stay
  the final judge.

## D. Owner decisions needed

1. Approve **fit-and-lock on our own generator** (no outside face tool), including a `face_generic/4` if the fit gets stuck.
2. **View weights**: you said all angles matter. Proposed: front 0.35, 3/4 0.35, side 0.2, back 0.1 (silhouette only). Or equal weights?
3. **Pass rule**: is "all scored T-204 measures within tolerance, plus your sheet review" the acceptance bar?
4. **Smiling references**: compare them against a matched smile expression (proposed), or use neutral references only?
5. **Order**: proposed white-haired (largest eye gap), then boy (lower face), then auburn (cheek under glasses and hair).
6. Ship the face and T-207 hair as **one new version** per character (one review), or separately?

## Appendix

**Files.** `probes/identity_drift_probe.py`: the shape-key zone probe (read-only on the masters).
`probes/drift_<character>.json`: its results for the three released masters.

**Reproduce** (repository root, about 1 min per character on CPU):

    blender -b --factory-startup -P docs/research/T-209/probes/identity_drift_probe.py -- \
        $PWD/assets/characters/<id>/versions/<ver>/<id>_master.blend docs/research/T-209/probes/drift_<id>.json <eye radius m>

The eye radius is `face.eyes.radius_m` in `spec.resolved.json`: boy 0.052, girls 0.048. Pass an absolute path for
the master; the script opens it with `open_mainfile`.

**Licences checked 2026-11-22** (beyond T-206 appendix C):
- KeenTools FaceBuilder: the add-on is free, but its core library needs a paid subscription.
- BlenRig 6: GPL-3, free on GitHub (`jpbouza/BlenRig`), targets Blender 4.x.
- hysts anime-face-detector: MIT code and weights. The weights are on Hugging Face, and it needs torch.
- FLAME, DECA and EMOCA: model licences are non-commercial (known terms, not re-fetched here).
- scikit-image: BSD-3. OpenCV: Apache-2.0. Both are on pypi.

**Hosts.** Reachable: `pypi.org`, `github.com`.
Blocked by the proxy (no connection, curl status 000): `huggingface.co`, `dl.fbaipublicfiles.com` (DINOv2
weights), `download.pytorch.org`, `extensions.blender.org`, `download.openmmlab.com`.
None of them is needed for the recommendation.

**Sources.** [KeenTools FaceBuilder](https://keentools.io/products/facebuilder-for-blender) ·
[BlenRig (GitHub)](https://github.com/jpbouza/BlenRig) · [BlenRig (Superhive)](https://superhivemarket.com/products/blenrig) ·
[anime-face-detector (PyPI)](https://pypi.org/project/anime-face-detector) ·
[anime-face-detector weights](https://huggingface.co/hysts/anime-face-detector-hrnetv2)
