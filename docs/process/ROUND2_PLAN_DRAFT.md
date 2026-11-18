# Round 2 plan: DRAFT for owner approval (2026-11-18)

**Status:** proposal only. Nothing in this plan starts until the owner explicitly approves it.

**Inputs:**
- `docs/audit/CODEX_PROJECT_AUDIT.md`
- `docs/audit/SUPERVISOR_PROJECT_AUDIT.md`
- `docs/audit/PROJECT_AUDIT_COMPARISON.md`
- the owner's references, including the Higgsfield set and the accepted design points

**Owner decision (2026-11-18, recorded on approval):** character creation stays **code-driven, procedural and
reusable** (the Codex approach). There are no manually sculpted characters and no authored hero meshes. Improvements
come from better procedural algorithms and better data. TD-42 is kept: Blender owns look and final render, the engine
owns animation, the engine renderer stays frozen.

**Source tags:**

| Tag | Meaning |
| --- | --- |
| **[C]** | found or recommended by Codex (T-084) |
| **[S]** | found or recommended by the Supervisor audit |
| **[C+S]** | both audits |
| **[NEW]** | an additional recommendation made in this plan, not in either audit |

**Effort:** S ≤ ½ day · M 1–2 days · L several days (implementer time including iterations; CPU and owner review are
extra).

---

## 1. Goals of round 2 (acceptance)

1. **Faces:** boy and girl faces visibly closer to the references in front, 3/4 and side, in neutral, blink and
   glance. Judged on one standard strict sheet against the original references and the owner-accepted Higgsfield
   targets (B01–B03, G01–G03).
2. **Hair:** fewer, larger, overlapping masses: the boy's crown, the girl's centre-parted fringe, a soft back
   transition and a narrower silhouette.
3. **Materials and garments:** separate, quiet fabrics. Outlines matching the references: boy inseam, shoes and flap
   backpack; girl sleeves, split bloomers, cream boot cuffs and rounded collar.
4. **Shot:** one readable two-person exchange in which both faces, both hands and the cup read at the moment of the
   hand-over, with distinct character reactions.
5. **Workflow:** fewer wasted renders, one CI run per promotion, quieter coordination, local full gate for every
   implementer.

---

## 2. Task list (prioritised)

### Wave 0: workflow and tooling (do first; small; removes the waste both audits measured)

| ID | Task | Source | Why (evidence) | Scope | Effort | Who |
| --- | --- | --- | --- | --- | --- | --- |
| **T-085** | **Renderer optional in the build** (`PLUSH_BUILD_RENDERER`, default OFF; one CI job keeps it compiling) | [S] (+ Codex's port timings) | Embree is used only by the frozen renderer. It blocked local C++ builds in every cloud session (14 relay mentions) and is 1.4 h of the 1.8 h Windows dependency build. | CMake, `vcpkg.json` features, CI job matrix | S | Implementer |
| **T-086** | **CI efficiency:**<br>- one gate run per promotion (gate on staging, fast-forward main without a second run);<br>- Windows **nightly and binding** instead of on every push;<br>- the gate skips the full tier on task branches until READY;<br>- all workflows on `main` watched. | [S] (Windows nightly: [C+S]) | 141 of 220 gate runs cancelled; every promotion ran the full gate twice; the backup job was red for 13 h unnoticed. | `.github/workflows/*`, `docs/process/GATE.md` | S | Supervisor + implementer |
| **T-087** | **Comparison recipe lock + fidelity fixes:**<br>- one tool records the input SHAs, the published baseline, the real compare variant (no A-pose fallback), camera, light and review settings, and renders **one cheap first frame for review before any long render**;<br>- fix the fidelity A-pose fallback and the hidden-backpack filter;<br>- the 2-point drop **flags for the owner** instead of blocking;<br>- the standard strict-sheet layout (reference, previous, candidate; identical cameras) becomes the single owner deliverable for visual tasks. | [C] (rule change [C+S], strict sheet [S]) | 10 of 26 boy stills rendered in A-pose and unusable; 11 showcase frames discarded; girl blocked by a score while visibly better. | `tools/review/`, `tools/fidelity/`, `docs/process/` | M | Implementer |
| **T-088** | **Version-switch script:** publish, approve, fidelity baseline, golden regression baseline, presets and generator pins, cast check and approval-trailer list in one command, with one test. | [S] | On 2026-11-18 the boy and girl switches needed 5 serial Supervisor fixes, each costing a CI round. | `tools/`, `pipeline/charsys/asset_store.py` (read), `docs/process/ASSET_STORE.md` | M | Implementer |
| — | **Coordination fixes** (no implementer):<br>- the relay notifier posts only READY, BLOCKED and STATUS;<br>- refresh the standing docs (`IMPLEMENTATION_PLAN.md`, `IMPLEMENTER_PROMPT.md`; the task template lists every file the solution may touch and requires the input SHA in each status line);<br>- Codex assignments always go at the top of `NEXT_TASK.md`;<br>- one fresh Supervisor session per round, started from the handover. | [S] (+ docs [C]; `NEXT_TASK.md` lesson [NEW]) | The Supervisor session cost $587 (largest single cost), mostly re-reading a 0.5 M-token context on notification turns. Stale plan text; a 7 h unacknowledged instruction; T-084 initially not seen by Codex. | relay workflow, process docs | S | Supervisor |

### Wave 1: character look, procedural (main visual work; runs in parallel after Wave 0's T-085 and T-087)

| ID | Task | Source | Why (evidence) | Scope | Effort |
| --- | --- | --- | --- | --- | --- |
| **T-089** | **Face system round 3 (procedural):**<br>- fit the eye opening, lid profile, brow spacing and cheek profile on the two approved heads in front, 3/4 and side, through neutral, blink and glance;<br>- shorten the lid shells at the outer corners (the 3/4 socket rim);<br>- keep T-081's socket-wall smoothing gain;<br>- add a **procedural "felt eye" shading mode** in the face system: matte iris, painted lid line, one crisp highlight, no glossy cornea sheen. The mode is generated in code and opt-in per spec. **Boy first, then girl, in the same task.** | [C] (fit) + [C+S] (eye gap) + [NEW] (felt-eye shading mode) | Eyes are the top gap in both audits (boy eye width −30 %, girl −19 %; boy eye "outlined like an insert"; girl's bright shelf under the eyes). | `pipeline/charsys/face_generic.py`, `face_features.py`, face library, the two characters' face spec data, tests | M–L |
| **T-090** | **Reference-fit optimiser [NEW]:** a reusable procedural tool that tunes a character's spec parameters automatically. It renders cheap Workbench silhouettes and landmark views (front, 3/4, side) and minimises the 2D error against the annotated reference landmarks and masks. Output: a proposed spec override plus a strict sheet. The owner still approves. Used by T-089, T-091 and the third character. | [NEW] (generalises Codex's "matched orthographic overlays") | Today parameters are tuned by hand in many full rounds. A code-driven fit converges faster and is reusable for every new character, which fits the procedural decision. | `tools/fit/` (new), reads `tools/fidelity/` annotations and `references/annotations/` | M–L |
| **T-091** | **Hair round 4 (groom):**<br>- fewer, larger, overlapping masses with varied footprint, depth, overlap and taper before fibre count;<br>- boy: broad crown petals with deep channels (B04, B05, upload 01);<br>- girl: centre parting with two swept fringe sections, soft back transition (no ridge), narrower silhouette, ringlet taper (G04–G06);<br>- a bounded **directional-fibre attribute** experiment along the locks;<br>- the face keep-out test stays. **Starts after the T-089 face fit** (fringe and eyes interact). | [C+S] (+ directional fibres [C]) | Hair is a top-3 gap in both audits. | `pipeline/charsys/groom_hybrid.py`, groom data in specs, tests | M |
| **T-092** | **Materials (T-067 revived):**<br>- fabric separation under a fixed neutral and warm light: quiet trouser pile, soft hoodie fleece, dense smooth vest felt, cream fleece boot cuffs;<br>- skin warmth in shadow and on the hands;<br>- **one uniform Geometry Nodes fibre halo** on felt surfaces, with density per preset (the existing fibre group);<br>- one macro patch and one shot-size patch per material;<br>- render time recorded. | [C+S] (+ uniform halo [S]) | Noisy fleece, speckled vest, hard boot rim, pale hands (limb ΔE 19.3). | `pipeline/charsys/materials/**` | M |
| **T-093** | **Garment outlines and accessories:**<br>- boy: inseam and trouser break, shoe volume (cream soles, white stripes), **flap backpack (B06)**, plain felt drawstrings;<br>- girl: sleeve reach, split bloomers, cream boot cuff, rounded collar, blue-grey scrunchie with one pink flower;<br>- **corrective shape keys** for the vest flare in reach (the drape is rest-pose only). | [C+S] (+ correctives [C]); design points from the owner decisions | Garments are a gap in both audits; the owner-accepted Higgsfield design points. | `pipeline/charsys/garments/**`, `accessories.py`, spec data | M |
| **T-094** | **Boy 2.1.0 and girl 0.12.0:** combine T-089 and T-091 to T-093 into new versions, through the T-088 script, with T-087 strict sheets; then the owner approves the switch to current. | [C+S] | Delivers the round's look gains as approved versions. | spec data, versions, baselines | S–M |

### Wave 1 in parallel: acting, animation and interaction

| ID | Task | Source | Why (evidence) | Scope | Effort |
| --- | --- | --- | --- | --- | --- |
| **T-095** | **Readable two-person exchange** (2–3 s) on the current boy 2.0.0 and girl 0.11.0:<br>- separate who notices, who acts and who reacts (an earlier glance by the observer, a later hand response);<br>- camera, shoulder spacing and cup height chosen from the two rigs;<br>- acceptance at the moment the hands share the cup, compared with PB f12/157/272 and WT f24;<br>- a diagnostic side view and the existing contact checks are kept. | [C] (priority 1 in T-084) | Heads touch, the cup is hidden, both actors look away together. | episode and shot data, `make_shot.py`, review renders | S–M |
| **T-096** | **Inter-character clearance and visible grip:**<br>- add head and hair volumes to the collision body (today the head is excluded) and keep the characters' heads and hair apart;<br>- grip poses that keep the prop visible (fingertip placement, thumb opposition from the hand-pose data);<br>- investigate the 4.5 mm cup-hold drift on 2.0.0. | [C+S] (+ head volumes [NEW]) | Heads touched at f45; the cup disappears in the fist; drift reported. | `engine/scene/collision.*`, `interaction.*`, `export_engine.py` (collision export), tests | M |
| **T-097** | **Personality acting pass:**<br>- distinct reaction timing, gaze targets and expression changes per character from the T-053 profiles (boy subtle and low-energy with delayed interest; girl cheerful and alert);<br>- an open "delighted" mouth for the girl's acting beats, while her rest face stays the closed smile;<br>- check that the viewer can identify each character's target from the gaze.<br>**After T-095.** | [C+S] (+ girl acting mouth [C]) | Both actors respond to the same cue at the same time; little expression change survives the wave. | `content/personality/*`, the face layer mapping, expression library, shot data | M |

### Wave 2: environment, rendering, props (after Wave 1 looks are accepted)

| ID | Task | Source | Why (evidence) | Scope | Effort |
| --- | --- | --- | --- | --- | --- |
| **T-098** | **Procedural set kit and light/camera presets as data [NEW scope; lighting C+S]:**<br>- the water-table classroom corner built procedurally from data: table, shelves, window, background props;<br>- light rigs as data (window key, rim on wool, fill);<br>- camera and focus presets;<br>- applied to the T-095 shot. | lighting and staging [C+S]; procedural environment generation [NEW] | The references use a window key, a rim on the wool, focus and a set; ours is a grey studio. | `content/sets/` (new), `pipeline/charsys/shot_render.py`, render presets | M–L |
| **T-099** | **Real prop hand-off:** file-mesh props carried through the bake to Blender (fix the placeholder cube); one paper mesh with two hand contacts and an engine-timed fold via shape keys. | [C] | `shot_render.py` renders file meshes as a cube; the paper and boat beats need real props. | `engine/scene/shot_bake.*`, `shot_render.py`, a prop asset | M–L |
| **T-074** | **CPU render budget study** (existing task file): measured seconds per frame for the approved cast at review and final settings; projected episode render time; settings that keep look and noise. | [C] (benchmark before projecting) + existing plan | 36–56 s per frame at 16 spp 720p today; no episode budget yet. | evaluation only | S–M |

### Wave 3: later (after Waves 1–2)

| ID | Task | Source | Effort |
| --- | --- | --- | --- |
| **T-100** | **Third character:** a dedicated body, dress, boots and face, built procedurally from her original references 01–15 with the T-090 fit tool; then W02, W04 and W05 details. Needs the two missing P1 images (W01 rest face, W03 buns). | [C+S] | L |
| T-051 | Fingers: per-finger grasps, two-hand support and carry (paper and boat). | existing plan + [C] (two-hand grip in the reference) | M |
| T-101 | Wire or fix the 3 old failing tests from T-077 (deformation mask, spring-chain gaps, emotion and reach). | [C] (green checks don't cover them) | M |
| T-102 | Repository hygiene: archive evaluation media older than a week (release asset or LFS), delete merged task branches after tagging, sparse-clone recipe. | [S] | S–M |
| T-103 | Optional perceptual metric (DreamSim or LPIPS) beside the fidelity composite, only if the T-087 rule change is not enough. | [S] | M |

---

## 3. Execution strategy

1. **Wave 0, about ½–1 day.** T-085, T-087 and T-088 by implementers (no file overlap); T-086 and the coordination
   fixes by the Supervisor. Merge Wave 0 before Wave 1 starts, so every Wave 1 task benefits.
2. **Fresh Supervisor session for round 2** (needs owner OK), started from `SUPERVISOR_HANDOVER.md`, this plan and
   the audits.
3. **Wave 1, parallel, at most 6 at a time:**

   | Track | Tasks |
   | --- | --- |
   | Face | T-089 |
   | Fit tool | T-090 |
   | Materials | T-092 |
   | Garments | T-093 |
   | Shot | T-095 |
   | Engine | T-096 |

   - The file claims are disjoint.
   - T-091 (hair) starts when T-089's face fit is accepted.
   - T-097 starts after T-095.
   - T-094 combines the look tasks into new versions.
4. **Review cadence:**
   - every visual task delivers **one T-087 strict sheet** and one cheap first frame before long renders;
   - the owner reviews **one daily batch**;
   - merges happen through the T-088 script.
5. **Codex role:**
   - independent reviewer per wave: a strict-sheet and frame review against the references, like T-083 and T-084;
   - optionally T-090 (fit tool) or T-074 (render budget) on the PC, where Blender 5.3 is installed;
   - the Windows nightly stays automatic.
6. **Waves 2 and 3** start only after the owner accepts the Wave 1 versions.

**Expected cost control:** the Wave 0 fixes target the measured waste:
- duplicate and cancelled CI runs;
- wrong-input renders;
- Supervisor context re-reads;
- serial version-switch fixes.

On the next 5 tasks we track discarded frames, first and last READY to merge, CI runs per merge, and Supervisor cost
per merged task.

---

## 4. Decisions needed from the owner

1. Approve this plan (or change priorities and scope).
2. Approve a **fresh Supervisor session** for round 2 (recommended), or keep this session.
3. Codex's role in round 2: reviewer only, or also T-090 or T-074.
4. Generate the two missing third-character images (W01 rest face, W03 buns) before T-100.
