# Hybrid character production: feasibility study for `boy_yellow_hoodie`

_2026-11-13. Feasibility only: nothing was modelled, nothing was integrated, the engine is unchanged.
Tags: **[M]** measured in this environment, **[S]** sourced (links at the end), **[E]** estimate._

Inputs:
- the 17 technical reference sheets and the original render (`docs/references/`, indexed in
  `assets/characters/boy_yellow_hoodie/references/reference_index.json`);
- the 16-view comparison harness (`docs/BLENDER_COMPARISON_HARNESS.md`);
- small throwaway tests in Blender 5.3. Script and results: `docs/evaluation/hybrid_feasibility/`.

---

## 0. Verdict

The hybrid pipeline is **feasible and is the most likely route to reference quality**. Its parts:
- **Artist:** about 70–140 hours of professional artist time **[E]** for the forms only a human can judge: face, hair
  clumps, garment shapes, expression sculpts.
- **Automation:** rigging, weights, validation, export and packaging can be largely automated in Blender. The core
  steps run headless today **[M]**.
- **Plush Studio:** the largest technical work is on the Plush side. It cannot yet load such an asset: no glTF
  import, no UVs or image textures, no bone orientations.

It should be proven with a **head-and-hair pilot** (§9) before the whole character is commissioned.

---

## 1. Recommended hybrid production architecture

```
 references (17 sheets + #7)            ┌──────────── Blender (pinned LTS, headless) ────────────┐
 reference_index.json  ──► ARTIST ──►   │ master .blend (versioned)                              │
 artist brief + harness   (desktop      │  └ automation: validate topology/naming → fit rig       │
                           Blender,     │    (Rigify) → weights → correctives → face controls     │
                           same LTS)    │    → validation poses → export package                  │
                                        └──────────────┬──────────────────────────────────────────┘
                                                       │ asset package (§3)
 comparison harness (16 views, metrics) ◄──────────────┤
                                                       ▼
                                Plush Studio: import → scenes, actions, director, render
```

Principles:
1. **The artist owns forms; scripts own everything repeatable.**
   - The artist delivers geometry and expression sculpts against a written specification (§5).
   - Everything downstream is a script that can run again: rig, weights, controls, validation, export.
2. **The master `.blend` is the single source of truth.** Every export is reproducible from it with a recorded
   pipeline version and Blender version.
3. **The harness gates every step.** No stage is accepted on opinion alone: numbers first (§9 criteria), then your
   visual approval.
4. **Plush Studio stays the only interface.** Blender runs headless behind it (TD-35); routine production uses only
   exported packages.

---

## 2. Human vs. automation, by task

Reliability:
- **High:** routinely correct; spot-check only.
- **Medium:** works, but a human must review and correct.
- **Human:** needs artistic judgement.

| Area | Task | Who | Reliability | Basis |
| --- | --- | --- | --- | --- |
| Face | Head and face sculpt (cheeks, chin, eye sockets, lids, nose, mouth, ears) matching #7/#24/#11 | **Artist** | Human | Identity lives here; Iteration 4's script-built face plateaued |
| Face | Retopology with the eye/mouth/jaw loops of #11 | Artist (scripted checks: loop count, poles, quad ratio) | Human + automated checks | Topology quality decides deformation |
| Eyes | Eyeball, iris/pupil, cornea, lash line | Artist models; procedural iris shader scripted | Medium | Shader parameters measurable against #7 colours |
| Mouth | Mouth bag, teeth, tongue (needed for the open expressions in #12/#28) | Artist | Human | — |
| Hair | Clump shell sculpts: crown spikes, fringe chunks, side/back clusters (#21) | **Artist** | Human | Silhouette-defining; #21's hybrid method |
| Hair | Fibre halo (0.5–1 mm fuzz, #21), flow direction | Scripted (Geometry Nodes / Plush fuzz) from artist-painted direction and density maps | Medium | Plush already grows fibres on meshes [M, iteration 4] |
| Body | Chibi body, A-pose, joint loops (#19) | Artist (simple, can start from a base mesh) | Human, low effort | — |
| Hands | 5-finger chubby hands, 3 loops per joint (#18; proportions from #7/#24) | Artist | Human | §2.6 item 7 conflict resolved toward #7/#24 |
| Clothing | Hoodie with hood, pocket, cuffs, drawstrings; joggers; shoes; backpack (#23) | **Artist** | Human | Shape and bulk are identity |
| Clothing | Fleece/felt surface (pile, fibre direction #25) | Scripted shaders and fibres from painted direction maps | Medium | — |
| UV | UV layout (#25) | Scripted unwrap + **artist correction** of seams on face/hoodie | Medium | Smart UV works headless [M]; seams need a human |
| Materials | Base colours, roughness, SSS values | Scripted, **tuned by the harness colour metric** (§9) | High once targets exist | Reference colours measurable [M] |
| Rig | Body skeleton: metarig fitted to the chibi proportions → Rigify | Scripted fit, human review | Medium | Rigify generates 706 bones / 160 deform in 6 s [M] |
| Rig | Fingers (MCP/PIP/DIP + thumb CMC/MCP/IP, #18) | Scripted (Rigify finger chains) | High | Standard Rigify feature |
| Rig | IK/FK arms and legs, elbow/knee poles (#20), root/hips/chest controls | Scripted (Rigify) | High | — |
| Weights | Automatic weights | Scripted | **Medium** | 2.0% of 95k vertices left unweighted on a multi-part test mesh [M] |
| Weights | Correction passes (smooth, normalise, fill unweighted, cap 4 influences) + clothing via data transfer from the body | Scripted | High after the first manual check | — |
| Weights | Final review of shoulders, armpits, hips, knees, fingers | **Human** (rigger) | Human | #20/#23 demand "no crushing, preserve bulk" |
| Face rig | Lid, brow, jaw, mouth-corner, cheek controls (#12) | Scripted bone controls | Medium | — |
| Expressions | 15 shapes of #12 + 12 presets of #28 | **Artist sculpts about 10 key shapes**; combinations, left/right splits and presets scripted | Human for key shapes | Expression shapes are identity |
| Correctives | Pose-space correctives (shoulder up, elbow 90°, knee 90°, hip flex) | Artist sculpts 6–10; drivers scripted; exported as morph targets plus a joint-angle table (§3) | Human + scripted | Plush cannot run Blender drivers |
| Hair motion | Chains per #22 (fringe 3, crown 4, side L/R) | Scripted bones; spring behaviour evaluated in Plush (new feature) | Medium | Blender has no built-in spring bones |
| Cloth | Hoodie/trouser deformation | Skinning + correctives; **no cloth simulation** | Medium | #20/#23 favour preserved bulk over draping |
| IK / interaction | Hand/foot IK, grasp contacts (#26) | Plush (exists: IK, grasp, actions); rig exports roles | Medium | Plush features exist for the iteration 4 rig |
| Validation | Poses from #19/#27/#29 (arms up, bow, sit, walk, run, kneel, squat), 9 hand poses (#18), expressions (#28), harness renders | Scripted | High | Harness exists [M] |
| Export | Package, manifest, hashes, versions | Scripted | High | glTF round trip kept rig, weights, 15 shape keys [M] |

**Minimum human work:**
- **Modelling artist:** face, hair shells, body/hands, garments, about 10 expression sculpts, 6–10 correctives,
  UV seam fixes.
- **Rigger:** a weight review pass of about one day, which can be the same person if qualified.

---

## 3. Required Blender capabilities, tools, dependencies

| Need | Tool | Status |
| --- | --- | --- |
| Pinned production Blender | Official LTS binary, checksum-verified (`pipeline/blender/install_blender.sh`) | Installer ready; **download host blocked in this environment** [M] |
| Headless automation | Blender Python API (`blender -b -P`) | Works [M] (5.3 module) |
| Body/finger/face rig | Rigify (bundled) | Present, generates headless [M] |
| Weights | Automatic weights, Data Transfer / Surface Deform modifiers, weight tools | Automatic weights measured [M]; others standard |
| Shape keys, drivers | Core Blender | Measured round trip [M] |
| Hair | Hair Curves + Geometry Nodes (bundled hair node assets) for the Blender look-dev groom | Hair curves create/export [M] |
| Look development | Cycles CPU (+ GPU on your machine if available) | Works [M] |
| Interchange: meshes/rig/morphs/UV/materials/animation | **glTF 2.0** | Round trip OK [M]; exports deform bones only (161 of 706): what Plush needs |
| Interchange: hair curves | **USD or Alembic** (both kept 3,000/3,000 curves [M]); glTF cannot (empty) [M] | Plush side: a small custom curve file written by a Blender script avoids a heavy USD/Alembic dependency in C++ [E] |
| Paid add-ons (e.g. Auto-Rig Pro) | Not required | Avoided: licensing and reproducibility |

Plush-side work (not started; listed so nothing is assumed):
1. glTF reader (e.g. cgltf, MIT, single header).
2. Mesh-based character type.
3. **Bone rest orientations** through IK, look-at, fingers, life layer and actions.
4. **UVs and image textures**: base colour, normal, roughness, masks; plus tangents.
5. Bone-role map (DEF bone names → Plush roles), so actions, grasp and the director work.
6. Morph targets from glTF (Plush has morph playback) plus the corrective weight table.
7. Hair-curve file reader and fibres on imported meshes driven by UV direction/density maps.
8. Spring-chain secondary motion.

---

## 4. Workflow: reference images → approved canonical asset

| Step | Output | Gate |
| --- | --- | --- |
| 1. Brief | Artist brief: §5 spec, reference index, view crops, harness, naming/topology rules, A-pose | — |
| 2. Blockout (artist) | Low-detail full body, A-pose, proportions only | Harness: proportions within ±5%, mean IoU ≥ 0.88 |
| 3. Head + hair (artist) | Sculpt + retopo face, eyes, mouth bag, hair clump shells | Face landmark and colour criteria (§9); your approval of the face |
| 4. Body, hands, garments (artist) | Final meshes, separate garment objects | All proportion/silhouette criteria; your approval of appearance (**visual approval gate**) |
| 5. UV + look-dev (script + artist fixes) | UVs, textures, direction maps, materials, groom | Colour ΔE criteria; texture review |
| 6. Rig + weights (script, rigger review) | Rigify rig, cleaned weights, face controls, hair chains | Validation poses render without crushing or intersections (human review checklist) |
| 7. Expressions + correctives (artist sculpts, script wiring) | About 10 key shapes → 15 + 12 sets; 6–10 correctives | Expression sheet vs. #12/#28; your approval |
| 8. Export + package (script) | Package (below) + validation report | Re-export reproduces identical hashes |
| 9. Plush import (development) | The boy in a Plush scene, driven by actions | Same-camera Plush vs. Blender comparison (TD-35) |
| 10. Canonical v1.0.0 | Frozen, tagged, backed up | Your sign-off |

**Package layout (`assets/characters/boy_yellow_hoodie/`):**
- `source/boy_yellow_hoodie_vNNNN.blend`: master; never overwritten.
- `export/…glb`: full and LOD1.
- `export/hair.*`: curves.
- `export/correctives.json`: joint-angle → morph-weight table.
- `textures/`.
- `asset.json`: version, Blender version, pipeline commit, file hashes, bone-role map, expression map, material map,
  LODs.
- `validation/`: harness sheet, measurements, pose renders.
- `CHANGELOG.md`.

**Identity preservation across revisions:**
- **Identity-locked parts:** the head mesh, eye geometry, hair shells, proportions and colours are listed in
  `asset.json` with hashes.
- **Changes to them** need a new major version and your approval (TD-36).
- **Every revision** re-runs the harness and must not lower any criterion beyond tolerance: a regression test, like
  the existing image regressions.
- **Golden renders:** a fixed turntable and expression set is kept per approved version for side-by-side checks.
- **Storage:** binaries go in Git LFS once a remote exists (no remote today, BUGS-09); bundle backups continue.

---

## 5. Artist requirements and deliverables

**Profile:**
- Stylised character artist: sculpting plus clean retopology.
- Portfolio with chibi/plush or designer-toy characters and soft cloth.
- Working in **Blender at our pinned LTS version**.
- Rigging and weight painting experience is a plus: then one person covers the review pass.
- Not needed: game-optimisation specialists, animators, texture painters (look-dev is scripted).

**Deliverables (acceptance per §9):**
1. `.blend` in the pinned version, A-pose, metres, +Z up, facing −Y, our object/material naming.
2. **Face:** quad topology with the #11 loops (≥ 3 rings around each eye and the mouth), separate eyeballs and lids,
   mouth bag with teeth and tongue, ears.
3. **Hair:** clump shell meshes as separate objects grouped by region (crown, fringe, side L/R, back) per #21/#22,
   plus a flow-direction map or guide curves.
4. **Body and hands:** five fingers with 3 loops per joint (#18), joint loops at shoulders, elbows, hips, knees (#19).
5. **Garments:** hoodie (hood, pocket, ribbed cuffs and hem, drawstrings), joggers with cuffs, shoes with cream toe
   caps and straps, charcoal-plum backpack. Separate objects, thickness modelled, no interpenetration in A-pose.
6. **Sculpt sources:** multires/sculpt layers kept, so later corrections stay possible without the artist.
7. **Expressions:** about 10 key shapes as shape keys (blink L/R, squint, smile, frown, jaw open, brow up, brow down,
   cheek puff, mouth corner up L/R), plus 6–10 corrective sculpts on poses we provide.
8. **UV seam corrections** on our automatic unwrap (face, hoodie).
9. **Handover note:** what each object is, known compromises.

**Avoiding dependency:**
- **Contract:** full IP assignment, no resale or portfolio restrictions unless agreed. Marketplaces note premiums of
  100–200% for exclusive rights, so budget for it [S].
- **Source files:** sculpt layers and clean, documented topology let a generalist make later small corrections.
- **Automation:** rig, weights, expressions, export are ours and rerun without the artist.
- **Base-mesh family:** the boy's body/head topology becomes the template the girls are sculpted from (§8), so the
  artist is paid for forms, not for re-solving topology and rigging.
- **Optional retainer:** a few hours per month for corrections.

---

## 6. Main technical risks and mitigation

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Artist output drifts from the references | High | Harness numbers in the contract's acceptance terms; staged payments per gate (blockout, head, full model) |
| Plush import path: largest engineering block (bone orientations, UV textures, glTF, roles) | High | Build in parallel from the pilot onward; keep SDF characters working; regression tests stay green |
| Automatic weights: 2% unweighted on a multi-part test mesh [M]; garments crush at joints | Medium | Scripted fill/smooth/normalise passes; garment weights by data transfer from the body; correctives; one human review |
| Hair: fibres for the felt look are expensive (iteration 4 peak memory 7.7 GB [M]) | Medium | Shells carry the silhouette; fibres only as a halo with LOD (existing Plush fibre LOD) |
| Blender behaviour differs between versions | Medium | One pinned LTS for artist and automation; scripts run in CI against it |
| **Pinned Blender binary blocked in this cloud environment** [M] | Medium (blocks automation runs) | Allow `download.blender.org` in the environment settings; meanwhile the 5.3 module for script development only |
| Shape keys exported as dense morph targets (memory) | Low | Sparse morph storage already exists in Plush [M, iteration 4] |
| Secondary motion (springs) stateful | Medium | Fixed-step deterministic solver plus per-shot cache |
| Reference inconsistencies (§2.6 of the analysis) | Medium | Priority rules in the index; artist brief states the resolved choices |

---

## 7. Effort, time and cost

**Measured [M] (this environment, 4-core CPU):**
- Rigify rig generation: 6.4 s; 706 bones, 160 deform.
- Automatic weights on 196,587 triangles in 24 objects: 34.8 s; 1.97% of vertices unweighted.
- glTF export: 8.6 MB in 2.4 s; re-import in 1.1 s with weights and 15 shape keys intact.
- Harness: 16 Blender views in 88 s; same cameras in Plush in 113 s.
- Iteration 4 baseline: mean IoU 0.79; head +15%, legs −14%, feet −30% vs. references.

**Artist effort [E]**, for one stylised chibi at the detail of the references:

| Item | Hours |
| --- | --- |
| Blockout | 4–8 |
| Head and face sculpt + retopo | 16–30 |
| Hair shells | 12–24 |
| Body + hands | 8–16 |
| Garments, shoes, backpack | 16–30 |
| Expression key shapes | 8–16 |
| Correctives | 4–8 |
| UV fixes | 3–6 |
| Two revision rounds | 8–16 |
| **Total** | **≈ 80–155 h** |

The pilot (§9) is about 25–45 h of that.

**Cost [S + E]:**
- **Market signals:**
  - Advertised freelance rates for Blender riggers and character artists cluster around US$15–35/h on marketplaces
    [S].
  - Guides quote US$300–1,500 for mid-level character models and US$1,500–5,000+ for detailed hero characters [S].
  - Exclusive rights can add 100–200% [S].
- **Our estimate [E]:** an experienced stylised artist at US$30–60/h for 80–155 h is about **US$2,400–9,300** for
  the full character, and **US$750–2,700 for the pilot**.
- **Caveats:** cheaper marketplace offers exist but carry more fidelity risk. Confirm with 2–3 real quotes using §5
  as the spec.

**Our development effort [E]**, in working sessions:

| Work | Sessions |
| --- | --- |
| Automation scripts (validation, rig fit, weights, face controls, expressions wiring, export, manifest) | 4–6 |
| Plush import path (§3, items 1–7) | 8–12 |
| Spring chains | 1–2 |
| Added metrics (§9) | 1–2 |

**Calendar [E]:**
- Pilot: about 2 weeks including artist turnaround.
- Full character to canonical v1.0.0: about 6–10 weeks, if artist availability is steady.

---

## 8. Reuse for future characters

- **Shared base-mesh family.**
  - The boy's approved body and head topology becomes the template for the girls: same loops, UV layout, rig fit and
    face controls.
  - Artists sculpt new forms on it, so rig, weights, expressions (shape-key transfer between identical topologies)
    and UVs transfer by script.
  - This is the main lever against per-character cost: rough estimate −30 to −50% artist time for characters 2 and
    3 [E].
- **Reused as is:**
  - Pipeline scripts, metrics and the artist brief template.
  - The harness: each character gets its own reference index and view crops.
- **Per episode:** new episodes use the canonical packages through Plush Studio (actions, director, life layer).
  Blender runs again only if a character changes, which is a versioned, approved event.

---

## 9. Pilot plan (head + hair + automation slice)

**Why this slice:**
- The face and hair carry the identity and are where Iteration 4 fell short.
- They test the artist's fidelity and the automation path at the lowest cost.

**Scope:**
- **Artist:** blockout of the full body; final head (face, eyes, lids, mouth bag, ears, hair shells); 4 key
  expression shapes (blink, smile, jaw open, brow down).
- **Automation:** validation of the delivery; a rig fitted to the blockout with head/neck/eye/lid/jaw controls;
  scripted weights; harness run; glTF export with the 4 shapes.
- **Plush:** none (no engine change in the pilot). It confirms the export contents against the Plush import
  requirements.

**Success criteria (all measured with the existing harness plus two small metric additions):**

| Criterion | Iteration 4 baseline | Pilot target |
| --- | --- | --- |
| Mean silhouette IoU, 6 measured views (blockout + final head) | 0.79 [M] | ≥ 0.88 |
| Head + hair fraction of height | +15% [M] | within ±5% |
| Head, torso, leg, feet widths | +13% / −4% / −14% / −30% [M] | each within ±7% |
| Face landmark ratios on #7/#27 front (eye spacing / face width, eye opening / iris, lid coverage ≈ 40%, eye line height, mouth height) | not measured | each within ±8% of the reference (landmarks annotated once on the references) |
| Hair silhouette above the brow line: contour distance (mean outline distance as % of head height) | not measured | ≤ 3% |
| Colour (hair, skin, eye iris) in matched renders | not measured | ΔE2000 ≤ 8 per region |
| 4 expressions vs. #28 tiles | — | your approval |
| Automation | — | rig + weights + export run headless without manual steps; < 0.5% unweighted after the cleanup passes; glTF round trip intact |
| Final | — | **your visual approval** of the face and hair |

**Go/no-go:**
- **Pass:** commission the rest of the body (§4 steps 4–7).
- **Fail on fidelity:** revise once with the measured gaps. If it still fails, change artist.

### Why IoU alone is not enough, and what to add

**Limits of silhouette IoU:**
- It ignores everything inside the outline: face, eyes, colour, texture.
- It is dominated by large areas, so the hair spikes, fingers and shoe shapes barely move it.
- It is sensitive to pose (hands in pockets) and to the estimated camera elevation and lens.
- It depends on reference segmentation: only 6 of 16 views are segmentable.

**Additions:**
- **Band widths:** already measured.
- **Contour distance:** mean and 95th-percentile distance between outlines. It catches hair-clump and shoe shapes.
- **Face landmarks:** about 12 points annotated once per reference view, compared as ratios.
- **Region colour:** ΔE2000 per material region. Masks come from Blender object IDs; reference regions are
  annotated once.
- **Local texture statistics:** for fleece and felt pile, e.g. gradient-orientation histograms on matched patches.
- **Perceptual similarity:** LPIPS/DISTS on matched crops, as a trend metric only. They need PyTorch, a large
  dependency, so they are optional.
- **Blind side-by-side review:** you judge unlabelled pairs (reference vs. candidate). This stays the final
  criterion.

---

## 10. Comparison with the Iteration 4 approach

| | Iteration 4 (script-built SDF) | Hybrid (artist + Blender automation) |
| --- | --- | --- |
| How forms are made | Blended primitives (ellipsoids, cones) tuned by parameters | Sculpted surfaces by an artist, judged against the same references |
| Measured fidelity | Mean IoU 0.79; head +15%, feet −30% [M]; hair cones instead of felted clumps | Target ≥ 0.88 and ±5–8% (§9), verified by the same harness |
| Face deformation | Surface-nets mesh without edge loops; mouths needed baked pockets (BUGS-21) | #11 loop topology; real mouth opening; lids from loops |
| Rig | 24 bones, no clavicles, 2-segment fingers [M] | About 160 deform bones (Rigify) [M], 3-segment fingers, IK poles, face controls |
| Expressions | SDF edits projected onto the mesh (limited, crumple-prone) | Sculpted shape keys + scripted combinations |
| Reuse | New characters need new parameter tuning | Base-mesh family: rig, UVs, expressions transfer |
| Cost | Developer time only; diminishing returns | Artist money plus Plush import work; returns grow with each character |

Why the hybrid is more likely to reach reference quality:
- The references are sculpted, designer-toy forms: soft planes, creases, irregular clumps. Primitives can approximate
  these but not reproduce them, which the Iteration 4 plateau shows.
- A skilled artist works directly in that form language.
- The harness turns "looks close" into measurable targets.
- Automation removes the expensive, repeated technical work that would otherwise make an artist-based pipeline slow.

---

### Sources (market rates)
- [Fiverr: How much does it cost to hire a 3D artist](https://fiverr.com/resources/guides/costs/3d-artist)
- [Fiverr: How much does it cost to hire a 3D sculpting artist](https://fiverr.com/resources/guides/costs/3d-sculpting-artist)
- [Upwork: 3D artist hiring costs](https://www.upwork.com/hire/3d-artists/cost/)
- [Upwork posting: Blender character rigging for cartoon animation](https://www.upwork.com/freelance-jobs/apply/Blender-Character-Rigging-for-Cartoon-Animation_~022095085744150871455/)
- [Fiverr: Blender rigging professional listing](https://fiverr.com/mryam_3d/rig-ypur-3d-characters-professionally-in-blender)
- [Polycount: paid freelance stylized character posting](https://polycount.com/discussion/238043/paid-freelance-3d-character-artist-unity-urp-stylized-character)
