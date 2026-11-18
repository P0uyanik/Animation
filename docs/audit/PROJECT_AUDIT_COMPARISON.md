# Project audit comparison: Codex (T-084) vs Supervisor, 2026-11-18

Sources:
- [CODEX_PROJECT_AUDIT.md](CODEX_PROJECT_AUDIT.md): Codex on the owner's PC, commit `ec1d316`, 14:21 UTC.
- [SUPERVISOR_PROJECT_AUDIT.md](SUPERVISOR_PROJECT_AUDIT.md): Supervisor, committed sealed at `e3666f9`, 13:55 UTC,
  before Codex started (13:57) and before its report existed.

**Independence:**
- Both audits used the same baseline (`main` 0388efb) and the same raw usage data.
- Neither saw the other's text before writing.
- The Supervisor's report is unchanged since sealing. Everything below is written after reading both.

---

## 1. Headline verdicts

| | Codex | Supervisor |
| --- | --- | --- |
| Where we stand | Two characters approved and reusable, recognisable in a lineup; none carries a reference-quality close-up through a shared action. The third character is not delivered (0/10). | About 3.5–4 out of 10 at shot size. The platform is strong; the look converges too slowly. The third character is not built. |
| First investment | **Re-stage one readable 2–3 s two-person exchange** on 2.0.0 and 0.11.0, and fit the eyes and fringe in parallel. | **Fix the face and eye concept and the felt surface** (authored hero shapes, felt eye discs, fuzz, materials), plus cheap process fixes. Shots come after. |
| Workflow | Integration is fast: 28 min median from the last READY to merge. The avoidable delay is **upstream**: renders on wrong inputs (10 A-pose stills, 11 superseded frames) and changing deliverables. | Integration surprises surface at merge time (no Embree locally). Merge ceremony and duplicate CI are heavy. **Coordination (one Supervisor session, $587) costs more than all 66 implementer sessions ($556).** |
| Architecture | Keep TD-42 and the frozen renderer. No replacement generator or rig needed. | Keep TD-42. Allow **authored meshes as spec data** for hero shapes, and make the frozen renderer an **optional** build target. |

---

## 2. Scores side by side (out of 10)

| Area | Boy, Codex | Boy, Supervisor | Girl, Codex | Girl, Supervisor | Agreement |
| --- | ---: | ---: | ---: | ---: | --- |
| Face and expressions | 5 | 4 | 5 | 3 | Codex is milder on the girl's face. |
| Eyes | 5 | 4 | 4 | 3 | Both name the eyes as a main gap. Codex measures eye width −30 % (boy) and −19 % (girl). |
| Hair | 6 | 5 | 5 | 4 | Same diagnosis: too many small spikes or too wide a mass; needs fewer, larger groups. |
| Skin | 5 | 5 | 6 | 4 | Codex credits the girl's matte skin more. |
| Materials | 5 | 4 | 5 | 3 | Same: noisy fleece, speckled vest, hard boot rim. |
| Garments | 6 | 4 | 5 | 3 | Same items (sleeves, shorts, boot cuff, pack). |
| Proportions | 6 | (in silhouette 6) | 5 | (5) | Codex has measurements (inseam −31 %, arms −26 %). |
| Animation | 4 | 3 | 4 | 3 | Both: no independent acting beats. |
| Interactions | 4 | 3 | 4 | 3 | Both: heads touch, cup hidden. |
| Third character | 0 delivered (prototype 3–5) | not built | | | Full agreement. |

**Reading:** the scores differ by 0–2 points, Codex being consistently a little more generous. The **ranking of gaps is
nearly identical**: eyes and face, hair mass, material noise, garment outlines, readable interaction.

---

## 3. Where they agree (high confidence)
1. **Keep TD-42.** Blender owns look and render, the engine owns animation, the engine renderer stays frozen. No new
   rendering path.
2. **The eye and face fit is the top character gap** for both approved characters.
3. **Hair needs fewer, larger, overlapping masses**, not more fibres. Fit them on the actual fitted heads first.
4. **Materials:** separate the fabrics (quiet trouser pile, soft hoodie fleece, dense vest felt, cream boot cuffs)
   under a fixed light. This is cheap and visible.
5. **Garment outlines before decoration:** boy inseam, shoe volume and pack flap; girl sleeves, split bloomers and
   boot cuff.
6. **The cup hand-over reads badly** (heads touching, cup hidden), even though the solver is precise.
7. **The fidelity composite can fall while the look improves.** The girl's approved change proves it.
8. **The third character waits** until the shared face, hair and garment fits are accepted, then gets a dedicated body
   and outfit. A stand-in must never be approved.
9. **No new heavy dependencies:** no second physics library, mocap suite, dynamic cloth or new lip-sync tool now.
10. **The Higgsfield images settle design choices, not physical truth.** Both reports treat them as owner-accepted
    detail targets with known contradictions.

---

## 4. Where they disagree, and my assessment

| Topic | Codex | Supervisor | Assessment (Supervisor, after reading both) |
| --- | --- | --- | --- |
| **What to do first** | A readable two-person exchange (camera, spacing, glances, cup height) as priority 1. | Face, eyes and felt surface first; the shot-layout study later. | **Codex is right that a shot is the real acceptance test**, and it touches different files (shot data, camera), so it can **run in parallel** with the face work. Recommend both at once, not one before the other. |
| **How to fix the faces** | Fit aperture, lids and cheeks on the existing parametric heads; rebuild the lid shells only if fitting fails. | The sphere-and-lid eye and the parametric head are the wrong concept for felt-doll references: use felt eye discs and authored head sculpts as spec data. | **Genuine disagreement and the most important decision.** Codex's path is cheaper and lower-risk; mine is a bigger bet with a bigger possible gain. Proposal: **A/B on the boy.** One task fits the current system (Codex's way); one task pilots a felt-eye-disc option and an authored head (my way); the owner picks on one strict sheet. Cost ≈ 2 tasks, and it settles the approach for all characters. |
| **Fidelity score** | Keep it as a regression signal; review the real comparison variant. Found that it can fall back to an A-pose master and hides the backpack. | Re-weight it (face counts only 5 %), add a perceptual metric, and turn the 2-point rule into "flag for owner". | Compatible: keep it as regression (Codex) **and** relax the blocking rule now (cheap). A perceptual metric is optional and later. Codex's A-pose fallback finding is the more urgent fix. |
| **Windows build** | The investment paid off in portability (104/104 MSVC tests); consider making a scheduled Windows run binding. | Small product benefit; run it nightly or on demand, not on every push. | Converge on a **scheduled (nightly) Windows run, binding on its result**, not on every push. |
| **Frozen renderer and Embree** | Keep it frozen (documents the dependency roles). | Make it an optional build target, so cloud implementers can run the full gate (Embree blocked them 14 times). | Not a real conflict: still frozen, just optional. Codex did not examine the cloud build blocker. **Adopt.** |
| **Where the workflow loses time** | Upstream: changing inputs, wrong-pose renders, deliverable changes, stale standing documents; one instruction took 7 h to acknowledge. Integration itself is fast. | Merge ceremony, duplicate CI, notification noise, Supervisor context cost, merge-time surprises. | **Both are right about different layers.** Codex measured the task layer, the Supervisor the coordination layer; the fixes are complementary (§5). |
| **Token waste** | Session totals are not a direct measure of waste. The strongest evidence of avoidable spend is the discarded renders and the duplicate branch. | The Supervisor's long context re-read on every turn is the largest single cost. | Both points hold. Codex is right that dollars are not waste per se. But $587 for coordination is a structural cost that a fresh Supervisor per round would cut without losing anything. |
| **New tools** | None beyond the existing stack (shape keys, Geometry Nodes fibre group, directional fibre attribute as a bounded experiment). | Geometry Nodes fuzz on all felt (already in Blender), plus an optional perceptual metric. | Agree on "no new tools now". The perceptual metric moves to "later, optional". |

---

## 5. Findings only one side made (all verified or plausible)

**Only in Codex's audit:**
- **10 of 26 boy evidence stills were rendered on A-pose masters, so unusable for scoring**, and 11 showcase frames
  were discarded after the cast changed. This is the clearest concrete waste.
- The fidelity tool can **fall back to an A-pose master**, and its object filter hides the backpack.
- `shot_render.py` turns file-mesh props into a placeholder cube, so real props (paper, boat) are not yet carried
  through to the Blender render. This matters for the reference shots.
- `garments/drape.py` settles a **rest shape** only; the vest flares in reaching poses (skinning, not cloth).
- Standing documents are stale: the implementation plan still says "Codex: T-060 only", and the T-082 task file omits
  the two shot files that produced the solution.
- PC tool inventory: Build Tools, CMake, Ninja and vcpkg are in real use for the Windows build. No `ffmpeg` or `gh` on
  the PC; Blender 5.3 is present and pinned.

**Only in the Supervisor's audit:**
- CI: **141 of 220 gate runs cancelled, 21 succeeded**. Every promotion runs the full gate **twice** (main and
  staging).
- **Embree blocks local C++ builds** in every cloud session (14 relay mentions), which pushes integration problems to
  merge time.
- The face counts for only **5 %** of the fidelity composite.
- The repository pack is **557 MB**, and every session clones it.
- The **Supervisor session cost $587** (largest single line).

**Found after both reports, during the state check (2026-11-18 ~14:20 UTC):**
- The **"Verified repository backup" job has failed on every push to `main` since 01:30 UTC**, because its restore
  test runs the Python tests without numpy and Pillow (introduced by the T-077 wiring).
- Neither audit caught it, and the Supervisor missed it for 13 h because only the quality-gate results were watched.
- Fixed in the same merge as this report: the backup workflow installs numpy and `Pillow==11.3.0`. Lesson: monitor
  **every** workflow on `main`, not only the gate.

---

## 6. Most valuable recommendations, combined and ranked

| Rank | Recommendation | From | Benefit | Effort | Risk | Adopt |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | **Lock the comparison recipe:**<br>- one input SHA per task;<br>- the published baseline;<br>- the real compare variant (never an A-pose fallback);<br>- fixed camera and light;<br>- a cheap first frame reviewed before long renders. | Codex | Stops the most clearly measured waste (A-pose stills, superseded frames). | S | Low | **Now** |
| 2 | **Process quick wins:**<br>- make the renderer and Embree optional (local full gate for everyone);<br>- one gate run per promotion;<br>- relay notifications only for READY, BLOCKED and STATUS;<br>- a fresh Supervisor session per round from the handover;<br>- monitor all workflows on `main`. | Supervisor (+ the post-audit backup finding) | Large drop in coordination tokens and CI minutes; fewer merge-time surprises. | S each | Low | **Now** |
| 3 | **Face A/B on the boy.** (a) Fit eyes, lids and cheeks in the current face system (Codex). (b) Pilot felt eye discs plus an authored head shape as spec data (Supervisor). Owner chooses on one strict sheet. | both | Settles the biggest visual gap and the approach for all three characters. | M + M | Medium (b) | **Now**, both in parallel |
| 4 | **Readable two-person exchange** on the current pair: glances, spacing, cup height, camera; head-to-head clearance. | Codex (+ Supervisor gap) | The first real acting test; touches shot files only, so it runs in parallel. | S–M | Low | **Now** |
| 5 | **Groom refit:** fewer, larger, overlapping masses (boy crown, girl fringe and parting, soft back transition) on the fitted heads. | both | Large silhouette gain. | M | Medium | **Now** (after or with 3) |
| 6 | **Materials and garment outlines:** fabric separation under a fixed light, boot cuffs, sleeves and shorts, vest weights in reach, backpack flap. | both | Cheap, visible. | S–M | Low | **Now** |
| 7 | **Fidelity rule change:** the 2-point drop flags for the owner instead of blocking. Keep the score as a regression signal. Fix the A-pose fallback and backpack filter. | both | Fewer false blocks; the number stays useful. | S | Low | **Now** |
| 8 | **Scheduled (nightly), binding Windows run** instead of every push. | both (converged) | Saves runner time; keeps portability. | S | Low | Now |
| 9 | **Refresh the standing documents** (implementation plan, prompts, task files list every file the solution touches). | Codex | Fewer stale instructions; faster acknowledgements. | S | Low | Now |
| 10 | **Third character:** a dedicated body, outfit and face from her original references, after 3–6 are accepted. | both | Real proof of reuse. | L | Medium | Later |
| 11 | **Real prop hand-off** (paper mesh plus timed fold through the bake). | Codex | Needed for the reference shots. | M–L | Medium | Later |
| 12 | Uniform Geometry Nodes fibre halo and directional fibres. Perceptual metric (DreamSim or LPIPS). Repository hygiene (archive old evaluation media). | Supervisor (+ Codex directional fibres) | Felt read; better metric; faster clones. | M each | Low–medium | Later |

**Suggested round 2, combining both audits:**
1. **Process fixes first** (ranks 1, 2, 7, 8, 9: small, mostly Supervisor-side). A fresh Supervisor session then
   starts round 2.
2. Then four parallel tasks:
   - face A/B on the boy (rank 3, two tasks);
   - two-person exchange (rank 4);
   - materials and garment outlines (rank 6).
3. Groom refit (rank 5) after the face decision.
4. Girl and third character follow the winning face approach.
