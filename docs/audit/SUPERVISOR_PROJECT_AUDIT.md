# Supervisor project audit (independent), 2026-11-18

**Baseline:** `main` at 0388efb (CI on that head: see §0). Every approved task is merged:
- boy **2.0.0** and girl **0.11.0** are current;
- the T-078 progress video, the T-082 latest-characters still, hair round 3, the collision system and the Windows build;
- the owner's 20 Higgsfield images.

This audit was written before reading Codex's T-084 report and does not use it.

**Evidence sheets in `docs/audit/supervisor/`:**
- `boy_face_ref_vs_current.jpg`: original reference | Higgsfield B01 | boy 2.0.0 render.
- `girl_face_ref_vs_current.jpg`: original reference | Higgsfield G01 | girl 0.11.0 strict render.

**Process and cost numbers come from these sources:**
- the repository: git history, `TASK_LOG.md`, `RELAY_LOG.md`;
- GitHub Actions (`gh run list`, 400 most recent runs since 2026-11-16);
- the session API: `docs/audit/data/agent_sessions_2026-11-18.md`.

**References:** "Original" means the owner's first references (`docs/references/`, `references/views/`, the boy's
`01_*` upload, the girl's `ref_30`–`46`, the third character's `01_`–`15_`). "Higgsfield" means the AI-generated set
of 2026-11-18. The owner accepted it as target detail, but it is **not ground truth**: it contradicts itself in
places (backpack, soles, fringe parting, back-hair band), and the owner resolved those points.

---

## 0. Repository state check (done before the audit)

| Check | Result |
| --- | --- |
| Approved task branches merged into `main` | Yes: T-060, T-078, T-079, T-080, T-081, T-082 (+T-047), T-083, plus the owner's references and the T-066 fix evidence. |
| Unmerged branches left, and why | `relay-channel` (never merged, by design). `t-040-claude-pose-clearance` (T-040r1, redesigned into T-047, kept on purpose). `t-041-codex-gate-polish` and `t-042-codex-integrate-tool` (superseded duplicates of T-041). `supervisor-state` and `codex/authentication-and-trust` (2026-11-15, superseded: the AUTHENTICATION doc is already in main). Nothing approved is missing. |
| CI on the last trial merge (girl, video, docs) | Full gate PASS: boy 67.63, girl 62.19, third PASS. |
| CI on `main` 0388efb | see the note at the end of §0 |
| Implementer sessions | All 6 sessions archived. No task is running except the Codex audit T-084. |

---

## 1. Where the project stands (realistic)

### 1.1 Visual fidelity: my scores, from the evidence sheets and the latest renders

Scale: 10 = indistinguishable from the original reference at its own framing. 5 = clearly the same character with
conspicuous differences.

| Area | Boy 2.0.0 | Girl 0.11.0 | Third | What I see (evidence) |
| --- | ---: | ---: | ---: | --- |
| Identity, silhouette | 6 | 5 | 2 (not built) | Boy reads instantly: hoodie, spiky black hair, sleepy lids. The girl reads, but her hair mass is too wide and her head is too long. |
| Face shape | 4 | 3 | – | Both faces are long, flat and CG-smooth. The originals have a short, round, very full lower face with the cheeks below the eyes. |
| Eyes and lids | 4 | 3 | – | The originals have large, matte, felt or appliqué eyes with one crisp highlight and a dark lid line. Ours are glossy 3D eyeballs. The girl's lenses show a grey band under the eyes and her eyes sit too high and too far apart. |
| Skin and felt surface | 5 | 4 | – | Colour is now right (porcelain-peach). The surface still reads as smooth plastic with a sheen, not flocked felt with a fibre halo. |
| Hair | 5 | 4 | – | Boy: tufts are right in kind, but the clumps are too thin and flat; no thick rounded petals with deep channels. Girl: right colour and curls, wrong mass, no parting or fringe structure. |
| Garments and materials | 4 | 3 | – | Hoodie fleece is mottled, trousers shaggy, the girl's vest frayed or torn. The originals are dense, even, soft fabrics. |
| Animation, acting | 3 | 3 | – | Short test clips (reach, touch, wave, hand-over). There is no acting beat comparable to the reference videos: shared attention, readable hands, holds. |
| Interaction | 3 | 3 | – | The cup hand-over works mechanically (exact contacts), but heads collide and the cup disappears in the fist. |
| Staging, lighting, render | 3 | 3 | – | Grey studio, flat key. The references use a window key, a rim on the wool, focus and a set. |
| **Overall, at shot size** | **≈ 4** | **≈ 3.5** | **–** | |

My overall estimate is **about 3.5–4 out of 10**. The trend is positive but slow:
- boy fidelity 64.5 → 66.4 → 67.6 over two days;
- the girl's score dropped to 62.3 while she looks better.

### 1.2 What genuinely improved in the last 48 h
- Skin colour, hair colour and the end of the helmet hair; face v2 lids; the boy's sleepy look; the garments are
  present (sneakers, backpack, hood).
- **Infrastructure:**
  - an immutable store for approved assets (T-075);
  - regression and golden baselines per version;
  - determinism;
  - a collision body with an interaction planner (T-047/T-082);
  - personality profiles (T-053);
  - a green Windows build (T-060).
- These are real assets. The problem is not the platform, it is the **rate at which the look converges**.

---

## 2. The biggest visual gaps and their root causes

1. **Eye and face construction concept** (largest visual gap, both characters).
   - The originals' eyes are part of a felt doll: flat or slightly domed matte discs with a printed or embroidered
     iris, a dark felt lid line and one painted highlight, set into a short round face.
   - Our `face_generic` builds glossy CG eyeballs behind lid shells on a parametric head. Each round has fixed a
     symptom (socket rim, cheek folds, lid shells) instead of the concept.
   - The root cause is architectural, in `face_generic.py`: the eye model is a sphere-and-lid rig.
2. **Head and face proportions from primitives.**
   - `body_generic` builds the head as an ellipsoid or loft fitted to outline tables.
   - The originals' head is a very specific sculpted form: wide round cheeks below the eye line, a tiny chin, a
     short lower face.
   - Six parameter rounds have not converged. A parametric fit to 2D outlines cannot reach a specific 3D sculpt
     without many more controls.
3. **Felt and fibre surface.**
   - The originals read as wool everywhere: a fibre halo on every silhouette and a matte micro-surface.
   - Ours: shaders give colour, but the fuzz is a bump or speckle. Hair-curve fuzz (`geom.py` hair_curves) exists but
     is not applied consistently to skin, garments and hair edges.
   - At shot size this alone makes everything read as "3D render", not "felt doll".
4. **Hair mass and clump shape.**
   - The generators build many thin clumps or ringlets over a base volume.
   - The originals have few, thick, rounded, felted masses with deep valleys (boy), and a defined parting with
     big soft masses before the curls start (girl).
   - The approach is right in kind but not in scale.
5. **Fabrics.** The materials are noisy or blotchy (fleece, vest), not dense and even. This is a material-tuning
   problem, cheap to fix (T-067 was never run).
6. **Shots.**
   - No real set, light rig or camera language has been built.
   - The animation tests are technical clips. Nothing yet tests acting against the reference videos.

---

## 3. Workflow efficiency: measured

### 3.1 Numbers

| Measure | Value | Comment |
| --- | --- | --- |
| Tasks in the log | 65 (about 40 done in 4 days) | High throughput of *tasks*, slow convergence of the *look*. |
| Commits on main since 2026-11-15 | 601, of which 108 merges since 11-17 | |
| Remote branches | 117 (80 task, 16 integration) | Many stale; costs clone and fetch time and attention. |
| Repository pack | **557 MB**; `docs/evaluation` 195 MB, `docs/` 292 k lines in 1 266 files | Every new cloud session clones all of this. |
| Quality-gate runs (since 11-16, 400-run window) | 220: **141 cancelled**, 56 failed, **21 succeeded** | About 3 400 runner-minutes. |
| Gate runs on `main` and `staging` | 46 + 46 | **Every promotion runs the full gate twice on the same commit** (both branches are pushed). |
| Gate runs on task branches | 111, mostly failing **by design** | They fail on guarded-path and write-set checks until the Supervisor approves, so the signal is noise. |
| Relay log | 186 lines, 38 READY, 6 superseded READY, 7 BLOCKED | |
| Re-submissions | T-081 **8** READY lines, T-060 4, T-065/T-080/T-082 3 each | T-081's rounds were mostly integration friction (hair swap, doc links, tool support for version specs, presets pin, golden baseline), not look work. |
| Embree mentioned as a blocker on the relay | 14 times | See §3.2 B1. |
| **Agent cost: implementers** | **$555.93 for 66 sessions** (2026-11-15 → 11-18); median about $8 per task; the most expensive tasks are $19–36 | Reasonable per task. |
| **Agent cost: Supervisor** | **$587.24 for one session**: 1.89 B cache-read tokens, about 543 k tokens of context re-read on every turn | **Coordination costs more than all the implementation work.** Every notification turn re-reads about 0.5 M tokens. |

### 3.2 Bottlenecks (ranked)

| # | Bottleneck | Evidence | Effect |
| --- | --- | --- | --- |
| B1 | **The frozen renderer is still a hard build dependency.** | `vcpkg.json` requires embree; `engine/render/pathtracer.cpp` is the only user. Cloud implementers cannot build the C++ engine (14 relay mentions; T-080, T-081 and T-082 all report "C++ embree env"). | Implementers cannot run the full gate locally. Integration issues surface only in CI at merge, which drives the rework loops. |
| B2 | **Integration issues are discovered at merge time.** | 2026-11-18 alone:<br>- version specs rejected by `tiers.py`;<br>- presets pin inconsistency;<br>- missing golden baseline;<br>- write-set timing;<br>- the empty-claims test. | The Supervisor fixes them serially, and each fix costs an 18–60 min CI round. |
| B3 | **Process ceremony per merge.** | Each merge needs:<br>- guarded-path trailers, one per file (I generated 8–18 per merge);<br>- claim edits;<br>- task-log edits;<br>- integration branches, sometimes stacked 3 deep;<br>- duplicate CI. | Most Supervisor tokens go to bookkeeping, not to review or planning. |
| B4 | **Communication.** | The Supervisor session cannot receive direct messages (elevated session). Everything goes through a GitHub relay whose bot also emits a "check_suite completed" event for every relay commit. | I processed about 40 notification turns today with no action needed, and every implementer report arrives 1–5 min late. |
| B5 | **One look round = one full task.** | Hair: T-038b, T-044, T-049, T-070, T-079 (5 tasks in 2 days). Face: T-055, T-058, T-065, T-081 fixes. Each round re-pays setup (clone 557 MB, Blender build about 2–4 min per character), reporting and merging. | Expensive iterations. Most change is parameter tweaking that a tighter loop could do in minutes. |
| B6 | **The fidelity score is misaligned with what the owner sees.** | `tools/fidelity/analysis.py` weights: face **0.05**, silhouette 0.20 + regions 0.10, hair 0.15. The girl scored lower while looking clearly better, and the owner overrode it. | Implementers optimise a number that does not track visual quality. The 2-point drop rule then creates false blocks. |
| B7 | **Owner approval latency on path B.** | Every visual step waits for owner sheets. | Necessary, but the sheets differ per task, so the owner has to re-learn the format each time. |
| B8 | **Windows CI cost and value.** | The Windows job took over 1 h uncached and runs on every staging push. The product renders in Blender on Linux; the owner's PC needs Blender, not the C++ engine. | Real cost, small product benefit (see §5). |

### 3.3 What works well (keep it)
- **Claims and write-sets:** no real merge conflicts between parallel tasks in 4 days.
- **Immutable approved versions and golden baselines:** they prevented silent regressions; every regression check
  caught real changes.
- **Strict visual comparison sheets** (the T-081 strict sheet): they let the owner decide in minutes. This should
  become the standard deliverable.
- **Owner-decision log and task files:** decisions are traceable.
- **Codex in an evaluation role:** T-083 was fast (≈ 15 min), cheap and useful.

---

## 4. Is the strategy right?

The architecture decision is sound and should stay:
- Blender owns the look and the final render;
- the engine owns animation and the shot bake;
- specs are data.

The weak point is a narrower assumption: **that every hero shape (head, eyes, hair masses) must be generated from
parameters.** For a small cast of hero characters judged against specific sculpted references, this converges too
slowly, and the evidence above shows it.

**Recommendation:**
- Keep the spec-driven pipeline.
- Allow **authored mesh assets as spec data** for the few shapes where parameters fail: head sculpt, eye discs,
  hair masses. They would be created once per character in Blender, versioned and immutable like the published
  versions, and referenced from the spec.
- Procedural code then does what it is good at: fitting, rigging, skinning, shape keys, fuzz and materials.
- This is still data-driven and reusable (a new character supplies its own meshes), and it keeps TD-42.

---

## 5. Tools: actual usage

| Tool | Used by | Measured benefit | Verdict |
| --- | --- | --- | --- |
| Blender 5.3 (bpy, Cycles, OIDN) | Every character, render and regression task (cloud) | The whole look pipeline | Essential |
| Embree (via vcpkg) | Only `engine/render/pathtracer.cpp` (frozen renderer) | None for the product | **Make optional** (B1) |
| VS 2022 Build Tools, CMake, Ninja, vcpkg (owner PC, installed 2026-11-17) | T-060 only (Windows build and CI) | Windows build green, 104/104 C++ tests on MSVC | Keep installed; don't invest further. Run Windows CI nightly or on demand, not on every staging push. |
| GitHub Actions gate | Every merge | Caught real issues (Windows line endings, guarded files) | Keep; remove the duplicate main+staging runs. |
| Fidelity tool (`tools/fidelity`) | Every character task | Low: misaligned weights (B6) | Rebalance, or add a perceptual metric (§6, R6). |
| Lip-sync tools (T-054a, Rhubarb plan) | Nobody yet | None yet | Fine as is; no work until dialogue starts. |
| Relay (GitHub PR comments) | All reports | Works, but noisy (B4) | Filter it (R4). |

**Missing tools worth adding:**
- A perceptual image metric (DreamSim or LPIPS, pip-installable, CPU-capable) to compare renders against references.
- Blender's built-in **Geometry Nodes fur or fuzz on curves** for a consistent fibre halo on all felt surfaces. It is
  already in Blender, so there is no new dependency.

Not recommended now:
- image-to-3D generators (quality and licensing are uncertain; better to author the meshes);
- new physics engines (Blender cloth or bullet and the engine IK are enough for the current shots).

---

## 6. Recommendations (prioritised)

| # | Recommendation | Expected benefit | Effort | Risk | When |
| --- | --- | --- | --- | --- | --- |
| R1 | **Make the renderer and Embree optional in CMake** (`PLUSH_BUILD_RENDERER=OFF` by default); build it only in one CI job. | Every implementer can build and run the full C++ and Python gate locally. Removes the main cause of merge-time surprises (B1, B2). | S (½ day) | Low: the renderer is frozen; one job keeps it compiling | **Now** |
| R2 | **Cheaper merge ceremony:**<br>- one trailer per directory, not per file, for owner-approved version folders and golden baselines;<br>- promote by pushing `main` only, with `staging` updated without its own gate run;<br>- skip the full gate on task branches until they report READY. | About half of CI minutes and most Supervisor bookkeeping tokens (B3). | S–M | Low: the same checks still run once | **Now** |
| R3 | **A pre-merge "version switch" checklist and tooling** (publish, approve, baseline, golden, presets pin, cast check) as one script with one test. | No more serial fix-ups like today's T-080/T-081 (B2). | M | Low | **Now** |
| R4 | **Quieter communication.** The relay notifier posts only READY, BLOCKED and STATUS lines; do not subscribe to check-suite events. | Fewer Supervisor turns, lower token use (B4). | S | Low | **Now** |
| R4b | **Short-lived Supervisor context:**<br>- start a fresh Supervisor session per round, from a written handover (`SUPERVISOR_HANDOVER.md` + `IMPLEMENTATION_PLAN.md`);<br>- move merge bookkeeping into scripts (R2, R3). | The Supervisor's $587 is mostly re-reading a 0.5 M-token context on every turn. A fresh session per round should cut coordination cost by well over half. | S | Low–medium: the handover must be complete (it was tested once today) | **Now**, at the start of round 2 |
| R5 | **Look-dev loop instead of task-per-round:**<br>- one long-lived look-dev session per character;<br>- a tight render loop (≈ 1 min per still);<br>- the owner reviews one standard strict sheet per day;<br>- merge only approved versions. | Faster convergence; fewer setup, clone and report costs (B5). | M | Medium: needs disciplined claims | **Now**, starting with round 2 |
| R6 | **Fix the fidelity measure:**<br>- raise the face weight;<br>- add a perceptual metric (DreamSim or LPIPS) on face, hair and full-body crops against the original references;<br>- keep the owner's eye as the final judge;<br>- relax the 2-point rule to "flag for owner", not "block". | The numbers start agreeing with what the owner sees (B6). | M | Low | Now (rule change); metric soon |
| R7 | **Authored hero shapes as versioned spec data** (head sculpt, felt eye discs, big hair masses; see §4). | The biggest single visual gain for the faces and hair. | M–L (per character about 1–2 days of authoring) | Medium: needs a modelling session; must keep rig and shape-key compatibility | **Now for the face and eyes** (pilot on the boy); hair after |
| R8 | **Felt eye concept:** replace the glossy eyeball look with matte felt or appliqué eye discs (iris, lid line, one highlight) as a face-system option. | Large visual gain; closes gap 1. | M | Low–medium | **Now** (with R7) |
| R9 | **Uniform fibre halo:** Geometry Nodes fuzz on all felt surfaces (skin edges, garments, hair edges), with density per material preset. | "Felt doll" read at shot size (gap 3). | M | Render time +20–40 % | Now (round 2 materials) |
| R10 | **Run the materials task (T-067) before any further hair or face rounds:**<br>- dense, even fleece;<br>- smooth felt vest;<br>- boot cuffs. | Cheap, visible gains (gap 5). | S–M | Low | **Now** |
| R11 | **Repository hygiene:**<br>- move evaluation media older than 7 days to a release asset or LFS archive;<br>- delete merged task branches after archive tagging;<br>- a shallow, sparse clone recipe for implementers. | Faster session start; less noise. | S–M | Low: archived, not lost | Later this week |
| R12 | **Windows CI on demand or nightly**, not on every staging push. | About 1 h of runner time saved per promotion. | S | Low | Now |
| R13 | **A shot-layout and light study** (window key, rim on wool, focus) on the water-table opening. | Large perceived-quality gain at shot level. | M | Low | After R7–R10 |

---

## 7. Proposed order for the next 3 days
1. **Day 1:**
   - R1, R2, R4, R12: process fixes, small and immediate;
   - R6 rule change;
   - start R10 materials and R8 felt eyes on the boy.
2. **Day 2:**
   - R7 pilot on the boy: authored head sculpt and eye discs as spec data; compare on a strict sheet;
   - R9 fuzz.
3. **Day 3:**
   - apply the winning approach to the girl;
   - hair masses (R7 hair);
   - then R13.
4. **Throughout:** R5 (look-dev sessions with daily strict sheets) and R3 (version-switch script) before the next
   version publish.

The point of this order is to stop spending tasks on parameter rounds that cannot reach the reference shapes, and to
spend effort on the face, eyes and felt surface, which decide how the characters read.
