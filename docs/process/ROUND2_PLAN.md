# Round 2 plan: APPROVED by the owner 2026-11-18 (revision 2)

**Status:** approved for execution 2026-11-18 ("approve execution, fresh supervisor yes, include T-090"). Phase A first.

**Inputs:**
- `docs/audit/CODEX_PROJECT_AUDIT.md`
- `docs/audit/SUPERVISOR_PROJECT_AUDIT.md`
- `docs/audit/PROJECT_AUDIT_COMPARISON.md`
- the owner's references and accepted design points

**Owner decisions reflected here (2026-11-18):**
- Character creation stays **fully code-based and procedural** (Codex's approach). There are no sculpted or authored
  character meshes. TD-42 and the frozen engine renderer are kept.
- **Priority order:**
  1. workflow, infrastructure, CI and agent coordination;
  2. faces, eyes, materials and garments of the two existing characters;
  3. in parallel with step 2, the two-character interaction and one **limited** environment, lighting and rendering
     experiment;
  4. after the owner approves the visual quality: hair, personality and acting, and the updated versions of the two
     characters.
- **Out of scope for now:** all former Wave 3 items (the third character, fingers T-051, old failing tests T-101,
  repository hygiene T-102, perceptual metric T-103), full environment development, and the prop hand-off T-099.

**Source tags:**

| Tag | Meaning |
| --- | --- |
| **[C]** | Codex audit |
| **[S]** | Supervisor audit |
| **[C+S]** | both audits |
| **[NEW]** | an additional recommendation in this plan |

**Effort:** S ≤ ½ day · M 1–2 days · L several days.

---

## Phase A: workflow, infrastructure, CI, agent coordination (first; merged before Phase B starts)

| Prio | ID | Task | Source | Why (evidence) | Effort | Who |
| ---: | --- | --- | --- | --- | --- | --- |
| A1 | **T-085** | **Renderer optional in the build** (`PLUSH_BUILD_RENDERER`, default OFF; one CI job keeps the frozen renderer compiling). | [S] (+ Codex port timings) | Embree is used only by the frozen renderer. It blocked local C++ builds in every cloud session (14 relay mentions) and is 1.4 h of the 1.8 h Windows dependency build. | S | Implementer |
| A2 | **T-086** | **CI efficiency:**<br>- one gate run per promotion (no duplicate main + staging run);<br>- Windows check nightly and binding instead of on every push;<br>- task branches run the fast tier until READY;<br>- every workflow on `main` monitored. | [S] (Windows nightly [C+S]) | 141 of 220 gate runs cancelled; double full gate per promotion; backup job red 13 h unnoticed. | S | Supervisor + implementer |
| A3 | **T-087** | **Comparison recipe lock and fidelity fixes:**<br>- record the input SHAs, published baseline, real compare variant (never an A-pose fallback), camera, light and settings;<br>- **one cheap first frame reviewed before any long render**;<br>- fix the A-pose fallback and the hidden-backpack filter;<br>- the 2-point drop flags for the owner instead of blocking;<br>- a standard strict sheet as the single visual deliverable. | [C] (rule [C+S], strict sheet [S]) | 10 of 26 boy stills unusable (A-pose); 11 showcase frames discarded; the girl was blocked by a score while visibly better. | M | Implementer |
| A4 | **T-088** | **Version-switch script:** publish, approve, fidelity baseline, golden baseline, presets and generator pins, cast check and approval trailers in one command, with one test. | [S] | 5 serial Supervisor fixes and CI rounds during the boy and girl switches on 2026-11-18. | M | Implementer |
| A5 | — | **Agent coordination:**<br>- relay notifications only for READY, BLOCKED and STATUS;<br>- refresh the standing docs (`IMPLEMENTATION_PLAN.md`, `IMPLEMENTER_PROMPT.md`; the task template lists every file a solution may touch; every status line carries the input SHA);<br>- Codex assignments always at the top of `NEXT_TASK.md`;<br>- **a fresh Supervisor session for round 2**, started from the handover, this plan and the audits. | [S] (+ docs [C]; `NEXT_TASK.md` rule [NEW]) | The Supervisor session cost $587 (largest single cost), mostly context re-reads on notification turns. Stale plan text; a 7 h unacknowledged instruction; T-084 initially unseen by Codex. | S | Supervisor |

**Phase A exit:** T-085 to T-088 merged with green CI on `main` (all workflows); coordination changes live; Round 2
Supervisor session started (subject to the owner's OK).

---

## Phase B: faces, eyes, materials, garments of boy and girl (procedural; starts after Phase A)

| Prio | ID | Task | Source | Why (evidence) | Effort |
| ---: | --- | --- | --- | --- | --- |
| B1 | **T-089** | **Face and eye system round 3 (procedural):**<br>- fit the eye opening, lid profile, brow spacing and cheek profile on both approved heads in front, 3/4 and side, through neutral, blink and glance;<br>- shorten the lid shells at the outer corners (the 3/4 socket rim);<br>- keep T-081's smoothing gain;<br>- add a procedural, opt-in **"felt eye" shading mode** (matte iris, lid line, one crisp highlight).<br>Boy first, then girl. Targets: original references plus B01–B03 and G01–G03. | [C] (fit) + [C+S] (eye gap) + [NEW] (felt-eye mode) | Eyes are the top gap in both audits (boy eye width −30 %, girl −19 %; boy eye "outlined like an insert"; girl's bright shelf under the eyes). | M–L |
| B2 | **T-090** | **Reference-fit optimiser (procedural tool):** tunes spec parameters automatically against the reference landmarks and masks from cheap Workbench renders (front, 3/4, side); proposes a spec override plus a strict sheet; the owner approves. Supports T-089 and T-093, and later hair and new characters. | [NEW] (generalises Codex's "matched orthographic overlays") | Replaces hand-tuned parameter rounds with a reusable, code-driven fit. | M–L |
| B3 | **T-092** | **Materials:**<br>- fabric separation under fixed neutral and warm light: quiet trouser pile, soft hoodie fleece, dense smooth vest felt, cream fleece boot cuffs;<br>- skin warmth in shadow and on the hands;<br>- one uniform Geometry Nodes fibre halo per preset (the existing fibre group);<br>- macro and shot-size patch per material;<br>- render time recorded. | [C+S] | Noisy fleece, speckled vest, hard boot rim, pale hands (limb ΔE 19.3). | M |
| B4 | **T-093** | **Garment outlines and accessories:**<br>- boy: inseam and trouser break, shoe volume (cream soles, white stripes), flap backpack (B06), plain felt drawstrings;<br>- girl: sleeve reach, split bloomers, cream boot cuff, rounded collar, blue-grey scrunchie with one pink flower;<br>- corrective shape keys for the vest flare in reach. | [C+S] (+ correctives [C]); owner-accepted design points | Garment gaps in both audits; the owner's Higgsfield decisions. | M |

**Phase B exit:** **owner approval of the visual quality**, on T-087 strict sheets of faces and eyes, materials and
garments for both characters.

---

## Phase C: in parallel with Phase B; interaction and a limited environment, lighting and rendering experiment

| Prio | ID | Task | Source | Why (evidence) | Effort |
| ---: | --- | --- | --- | --- | --- |
| C1 | **T-095** | **Readable two-person exchange** (2–3 s) on the current boy 2.0.0 and girl 0.11.0:<br>- who notices, who acts and who reacts (an earlier glance by the observer, a later hand response);<br>- camera, shoulder spacing and cup height from the two rigs;<br>- accepted at the moment the hands share the cup, against PB f12/157/272 and WT f24;<br>- a diagnostic side view and the existing contact checks are kept. | [C] (its priority 1) | Heads touch, the cup is hidden, both actors look away together. | S–M |
| C2 | **T-096** | **Inter-character clearance and visible grip:**<br>- head and hair volumes in the collision body (the head is excluded today);<br>- grip poses that keep the prop visible;<br>- investigate the 4.5 mm cup-hold drift on 2.0.0. | [C+S] (+ head volumes [NEW]) | Heads touched at f45; the cup disappears in the fist. | M |
| C3 | **T-098L** | **Limited environment, lighting and rendering experiment** (one shot only, no full environment system):<br>- a minimal procedural water-table corner from data (table, back wall and window, two or three background shapes, soft depth of field);<br>- a light rig as data (window key, rim on the wool, fill);<br>- one camera preset;<br>- render the T-095 exchange still in the grey studio vs the experimental set;<br>- **measure seconds per frame** at review and final settings and project per-minute cost.<br>The result is a recommendation for or against a full environment phase, which stays out of scope. | [C+S] (lighting and staging) + [NEW] (procedural set experiment; render-time measurement from T-074) | The references use a window key, a rim on the wool, focus and a set; ours is a grey studio. No measured render budget yet. | M |

Phase C uses the **current** character versions. It shares no files with Phase B (shot data, engine collision and
interaction, a new `content/sets/` experiment folder).

---

## Phase D: approved 2026-11-18 ~22:50Z (owner distribution; supersedes the original D1-D3 table)

| Order | ID | Task | Starts |
| --- | --- | --- | --- |
| 1 | **T-091** | Hair round 4 (as planned: fewer larger overlapping masses; boy crown petals; girl centre parting, soft back transition, narrower silhouette, ringlet taper; bounded directional-fibre test; face keep-out stays) | now |
| 1 | **T-089b** | Face polish: boy regains sleepy heavy lids with the new eye size; girl rounder, fuller face and wider-open eyes | now |
| 1 | **T-093b** | Garment completion: T-090b boy trousers/shoes proposal as a candidate; girl shorts leg-split control, then re-fit | now |
| 1 | **T-104** | Animation timing calibration (running since ~21:40Z) | running |
| 2 | **T-097S** | Acting system (shared): reaction model, emotion modulation by profile, blending, animcheck signature checks; formats and code only | when T-104 merges |
| 3 | **T-097B / T-097G** | Boy / girl acting, each only its own character's files (boy subtle, delayed interest; girl cheerful, alert, open "delighted" mouth for acting beats) | after T-097S |
| 4 | **T-094** | Boy 2.1.0 and girl 0.12.0 (T-089 + T-089b, T-092, T-093 + T-093b, T-091) via the T-088 script; e907 re-render with T-097B/G acting; owner approves before current | after T-091, T-089b, T-093b are owner-approved |
| — | **T-106** | Codex: reference performance extraction (MediaPipe) as calibration targets for T-097B/G and T-104 | now |

---: | --- | --- | --- | --- |
| D1 | **T-091** | **Hair round 4 (groom data and algorithm):**<br>- fewer, larger, overlapping masses (footprint, depth, overlap, taper before fibre count);<br>- boy: crown petals with deep channels;<br>- girl: centre parting with two swept sections, soft back transition, narrower silhouette, ringlet taper;<br>- a bounded directional-fibre experiment;<br>- the face keep-out test stays. | [C+S] (+ directional fibres [C]) | M |
| D2 | **T-097** | **Personality and acting:** distinct reaction timing, gaze targets and expression changes per character from the T-053 profiles (boy subtle with delayed interest; girl cheerful and alert); an open "delighted" mouth for the girl's acting beats, rest face unchanged; on the T-095 exchange. | [C+S] (+ acting mouth [C]) | M |
| D3 | **T-094** | **Boy 2.1.0 and girl 0.12.0:** combine Phase B and T-091 through the T-088 script and T-087 strict sheets; the owner approves the switch to current; the T-095 exchange is re-rendered with the new versions. | [C+S] | S–M |

---

## Out of scope (deferred until the owner reopens it)
- **Third character (T-100).** It also needs the W01 and W03 images.
- **Fingers (T-051).**
- **The 3 old failing tests from T-077 (T-101).**
- **Repository hygiene (T-102).**
- **The perceptual metric (T-103).**
- **Full environment development (full T-098).**
- **The prop hand-off and paper fold (T-099).**
- **The full CPU render budget study (T-074).** Only the measurement in T-098L is kept.

---

## Execution strategy
1. **Phase A:**
   - T-085, T-087 and T-088 by implementers in parallel (disjoint files);
   - T-086 and A5 by the Supervisor;
   - all merged before Phase B and C start.
2. **Phases B and C in parallel**, at most 6 tasks:

   | Phase | Tasks |
   | --- | --- |
   | B | T-089, T-090, T-092, T-093 |
   | C | T-095, T-096, T-098L |

   - That is 7 candidates: start T-090 when T-089's first face fit is reviewed, or run T-098L after T-095's blocking.
   - The file claims are disjoint.
   - Every visual task delivers one cheap first frame, then one T-087 strict sheet.
   - The owner reviews **one daily batch**.
3. **Phase D** starts only after the owner approves Phase B's visual quality.
4. **Codex:** independent reviewer at the end of Phases B and C (strict-sheet and frame review against the
   references, like T-083 and T-084); the Windows check runs nightly automatically.
5. **Measured on the first 5 tasks:** discarded frames, first and last READY to merge, CI runs per merge, Supervisor
   cost per merged task.

## Decisions needed from the owner
1. Approve execution of this revised plan (or adjust it).
2. A fresh Supervisor session for round 2 (A5; recommended).
3. T-090 (fit optimiser) in Phase B: yes or no. It is procedural and reusable, but new.
