# Owner decisions (binding for planning)

## 2026-11-15: architecture direction after the architecture discussion
1. **Animation clips:** reusable body animation clips are authored first in Blender (or from motion capture) on the
   shared skeleton. The C++ engine uses, combines, blends and personalises them. Our own authoring tools come later,
   only if needed.
2. **Behaviour system:** controllable, not autonomous. It suggests character reactions and actions as ordinary
   timeline actions, which the owner reviews, edits or removes.
3. **Development priority after T-001:**
   - first the **Acting Foundation** (movements, emotions, body language, interactions);
   - then the **Asset Library** and the reusable classroom environment.

   These systems must eventually work together.

## 2026-11-15: standing requirements
- **Third main character:** the third main character is the generality test of the shared character pipeline.
  Minimise character-specific implementation: shared material/shader systems (plush, felt, wool, hair fibres,
  clothing), a shared hair grooming system, and shared body, rig, skinning, face, clothing and deformation systems.
  Characters differ by specs and parameters. The reference package follows at the stage that introduces this
  character.
- **Visual benchmark:** the owner's test videos (`docs/references/video_watertable.mp4`,
  `docs/references/video_paperboat.mp4`) and the character reference sheets are the visual and animation benchmark
  for all future development. Avoid work that does not move the project towards that target.

## 2026-11-15: multi-agent orchestration (Claude Implementer, Codex, Antigravity)
1. The Supervisor is the central authority and makes all final decisions.
2. Minimise token use for the Supervisor and the Claude Implementer; keep enough Claude quota to coordinate Codex
   and Antigravity.
3. Delegate implementation tasks to Codex and Antigravity whenever appropriate (they use the owner's existing
   ChatGPT and Google subscriptions through the local Claude Code session on the owner's computer; no API billing).
4. Each agent gets a clear, independent task with defined acceptance criteria.
5. Each agent creates its own task branch from the latest `main`; agents never modify or push to `main`.
6. The Supervisor reviews all completed work (code quality, architecture, tests), requests fixes and re-reviews when
   needed, and merges verified branches into `main` without conflicts or regressions.

## 2026-11-16: shared-systems principle (binding)
Everything that can be shared across characters must be designed as a reusable, character-independent system
(code with no character names, configured by spec/preset data, tested on at least two characters or a synthetic
configuration), never implemented separately per character. Character-specific legacy (boy 1.0.0/1.1.0) stays frozen
and is migrated through new versions (Boy 2.0, roadmap V3b). Task prompts and reviews enforce this rule.

## 2026-11-16: open-source tooling (owner-approved; installs allowed when needed)
Priority: (1) Blender Geometry Nodes + hair curves for real fibre fuzz on felt, wool and yarn (shared material/groom
builders); (2) EEVEE draft renders alongside Cycles finals (`--engine eevee|cycles`); (3) engine secondary motion
(spring chains, shared layer) and a `run_shot` simulate stage using Blender's built-in Bullet rigid body, cloth,
Dynamic Paint waves and particles (V4: water, ripples, sparkles, falling/floating props); (4) OpenTimelineIO edit
export and Rhubarb Lip Sync with V5. Later/not now: OpenUSD (V7/V8), MaterialX, Filament, OpenVDB, Bullet in engine.

## 2026-11-16: code-based first, hybrid only if proven necessary
Continue improving the code-based shared systems (face v2, hair v2 r2, cloth rest-shape simulation, surface detail)
before deciding on a hybrid workflow (optional sculpted asset slots). Decide by measurement (fidelity) plus the owner's
visual verdict. Every system must be reusable across all current and future characters. Every task reports technical
limitations that block reference quality, with a proposal for overcoming them.

## 2026-11-17: branch cleanup after merges
After each successful merge into `main`, the Supervisor deletes the merged task/integration branches (remote and
local) only when: all checks passed on the merged `main`; a verified backup bundle (`git bundle verify`) containing
those branches exists; and `git branch -r --merged origin/main` confirms each branch is fully contained in `main`.
Never delete an unmerged branch, a branch with commits not in `main`, `relay-channel`, or `supervisor-state`.

## 2026-11-17: continuous integration via `staging` (owner-approved)
- `staging` = `main` + tasks reviewed and gate-tested by the Supervisor. Every new task branches from `origin/staging`
  and merges `origin/staging` into itself before its final report (owning agent resolves conflicts, reruns check_all).
- Merge promptly: a task is merged into `staging` the same day it is accepted; at most 3 tested tasks wait unapproved.
- Standing approval (path A): validated technical changes (engine, tools, tests, CI, performance; no visible change)
  go `staging` → `main` after a green gate and Supervisor review, with notification afterwards.
- Path B: anything that changes the look (characters, materials, specs, renders) needs the owner's visual approval.
- Rejections are undone on `staging` with revert commits only. `main` advances only by fast-forward to a gate-green
  `staging` commit, with a verified backup before and merged-branch cleanup after (see 2026-11-17 branch cleanup).
- Ownership map `docs/process/OWNERSHIP.md`: parallel tasks never share files; specs are split into per-area parts.

## 2026-11-17: shared systems with versioned behaviour (owner-approved)
Architecture: shared systems + versioned behaviour + character-specific data/assets (never character-specific code).
- Each character spec pins the generator versions it uses; behaviour changes create a new version; a character
  changes only when the owner approves its upgrade (before/after renders). At most two active versions per system.
- Shared defaults stay neutral; new features are opt-in parameters (off = identical output).
- Visual quality is never sacrificed for reusability. Any change to a shared system rebuilds and renders ALL
  characters in CI: an unintended fingerprint change or a fidelity drop is a FAIL needing owner review, with
  side-by-side render comparisons attached.
- Order: finish/validate/merge all running and suspended work first; then spec parts + generator versioning +
  all-character visual regression; then Boy 2.0 and new features.

## 2026-11-17: girl 0.9.0 approved as an intermediate version
The consolidated girl spec 0.9.0 is approved for `main` as an intermediate state, NOT as final visual approval.
Open visual gaps (hair structure and colour, proportions, vest, boots, ears, hair accessories) remain tracked.

## 2026-11-17: automation Phase 2 not built now
PR-per-task automation (Phase 2) is deferred: the staging workflow, integrate.py and the quality gate already cover
its benefits. Instead: a small push-triggered cleanup workflow deletes only branches fully merged into main (the
cloud proxy blocks deletion), and the owner sets a main-branch ruleset once. Revisit Phase 2 with >4 permanent
parallel Implementers, external reviewers, or if the owner prefers reviewing in GitHub.

## 2026-11-17: delivery plan approved (docs/process/DELIVERY_PLAN.md, rev. 2)
The overall approach is approved (no PR per task; READY signal + Supervisor merge queue; staging; fast path-A
promotion; path-B visual approval via version pin bumps). Owner's four required improvements, now part of the plan:
1. Parallel tasks within the same lane are allowed when their files and dependencies don't conflict (file claims).
2. Full all-character regression is mandatory for any change to shared systems or visuals.
3. Versioned changes must not alter existing characters unintentionally (unchanged-character guard in CI).
4. Backups must be durable (backup tags, CI bundles with restore test, off-site copy) and the automatic branch
   cleanup must be thoroughly tested (unit + end-to-end + dry run) before it deletes anything.
The workflow must stay reliable, efficient and free of unnecessary bottlenecks.

## 2026-11-17: backups on the owner PC; GitHub protection
The owner's local computer is the off-site backup destination (read-only mirror + verified bundle, set up via
Remote Control when the PC is online). The owner asked the Supervisor to handle GitHub security settings; the cloud
proxy blocks settings changes, so the Supervisor prepared importable rulesets (docs/process/github-rulesets/).

## 2026-11-17: roadmap priority v5
Water simulation and paper folding are not priorities for now. Personalities: the boy is impatient and easily
bored; the girl is cheerful and intelligent; both must show in movement, expression and behaviour (shared
personality-profile system, data per character). A third character follows once the shared systems are complete and
reliable. Approved: evaluate strand grooming vs sculpted hair and choose the best; explore GPU rendering options and
costs before any extra expense; include dialogue and lip sync; develop detailed natural finger animation; include
Blender checks in GitHub CI where practical. All implementations efficient and reusable across all characters.
See docs/ROADMAP.md "Priority v5".

## 2026-11-17: the references are the primary target
The reference images, character models and videos were designed around each character's personality (boy:
impatient and easily bored; girl: cheerful and intelligent) and already reflect those traits. Goal: match them as
closely as possible in appearance, expressions, movements and animation quality. Always treat the original
references as the primary target; improvements and personality features must support those designs, never change or
contradict them.

## 2026-11-17: no GPU rental available
The owner cannot rent a GPU at present. Render planning assumes CPU only (cloud containers, and the owner's PC when
available) until this changes; T-050's rental recommendation is on hold. Mitigations to evaluate before the
benchmark scene: render settings tuned for CPU (resolution, samples + OIDN, adaptive sampling), splitting frame
ranges across several cloud sessions, the owner's PC hardware, and only rendering final takes at full quality.

## 2026-11-17: character details from the reference conflicts (T-053a)
1. Boy: impatience stays subtle, calm and low-energy, as in the original references (small, slow fidgets in his base
   tempo; no quick, abrupt or comic moves; no eye-rolls).
2. Girl: eye colour brown.
3. Girl: neutral mouth closed, with a gentle smile (open smile belongs to Happy).
Apply consistently across models, animations and personality profiles; the original references stay the primary target.

## 2026-11-17: third character
The owner supplied 15 reference images for the third character (working id `girl_white_hair_blue_dress`). Personality:
a little goofy, not very bright, bubbly and cheerful; reflected in expressions, movements and behaviour while staying
faithful to the reference images (references remain the primary target). She is built (V6) once the shared systems
are complete; reference intake and gap analysis (T-057) start now.

## 2026-11-17: hair v3 approach; third character details
1. **Hair v3 = hybrid C** (T-049): felted base volumes + a limited number of broad felt clumps/locks at the edges, face
   keep-out as spec data. The final result must closely match the references; renders go to the owner for approval.
2. Third character, "exactly as in the references" (Supervisor's application of the references, per T-057 §8):
   - **Hair accessory: the blue felt bow** (identity render, 10 sheets, both videos, material spec "BOW"); the 4-petal
     flower appears only in the technical hair/rig blueprints `w05`–`w08`.
   - **Neutral mouth: closed soft smile** (all tiles labelled Neutral, videos at rest); lips slightly parted while
     watching (behaviour); the small open smile of the turnaround/line-up renders is her presentation/Happy face.
   - **Goofiness subtle**, as in the references (open-mouthed watching, following the others, comic face tiles; no big
     comic moves).
   - Dress: cable-knit skirt and knit bodice; boots: shaggy fleece (majority + material spec; `w09` is a construction sheet).

## 2026-11-17: girl 0.10.0 approved as intermediate
Girl 0.10.0 (closed gentle-smile neutral, T-055) is approved as an intermediate version, **not** final visual approval.
The next improvement round must address the remaining differences, especially mouth, cheeks, skin tone, eyes and hair,
with the original references as the primary target.

## 2026-11-17: animation evaluations use the current approved versions; T-060 locally
1. Future animation evaluations and evidence must use the latest approved character versions, so the combined quality
   is assessed (old versions only where a frozen regression test needs them). Implemented by T-062 + Implementer rule.
2. T-060 (Windows build): option B — install the C++ Build Tools on the owner's PC (owner approval for the install and
   licence). The owner frees space on D: personally; agents never delete or move the owner's personal files.

## 2026-11-17: T-063 plan approved
Start P6 (fidelity tool fixes, T-064) and P1 (face v2, T-065) now; the girl look round (T-059) follows the shared-system
improvements (face v2, skin T-066, materials T-067). **Visual fidelity to the original references takes priority over
numerical scores**; the fidelity score supports, never overrides, the owner's side-by-side judgement.

## 2026-11-17: facial geometry
The characters still have significant facial geometry issues (chin, jawline, overall face shape). The underlying 3D
head/face geometry must be improved to match the original references; added to face v2 (T-065) as its first criterion.

## 2026-11-17: GitHub Free, public repository; hair v3 merged as a system, round 2
- The owner is on GitHub Free and made the repository public again to avoid Actions limits (CI and rulesets as before).
- Hair v3 (`groom/2`) is approved for merging as a technical system; round 2 (T-070) improves its visual fidelity.
  Current approved character versions stay unchanged until the owner approves new renders.

## 2026-11-17: T-069 audit recommendations approved
1. Boy candidates F09 (face) and H28 (hair): rejected (superseded by face v2 / hair v3) → archived.
2. Root status docs: refresh `CURRENT_STATUS.md` and `NEXT_TASK.md` as pointers; archive the other five (T-071).
3. Engine-era demo scenes: archive, except any a test/CTest still uses.
4. Retire `hair_clumps/2` (experiments only) once its experiments are archived (no character pins it).
5. `apps/export-obj`: archive (after T-060 releases the root CMakeLists).
6. Boy 1.1.0 is described as "current approved", not "published".
7. Blender-only tests run in the local full tier (not on GitHub) to save Actions time.
8. Evidence size policy for future tasks (DELIVERY_PLAN §9b).

## 2026-11-17: third character accessory re-confirmed
The owner pointed to the third character's material specification sheet (bow) as her design: she wears the **blue felt bow**.
The 4-petal flower in the all-three turnaround sheet is not her look.

## 2026-11-17: architecture: renderer freeze, CPU render optimisation, docs, approved-asset preservation
1. **Engine renderer frozen:** the C++ engine's path tracer gets no new features; it stays for previews and its
   existing tests. Look/material/render work happens only in Blender (TD-42). `engine/render/` is a guarded path.
2. **CPU-only render optimisation** (T-074): evaluate Cycles, Eevee, denoising and other free options; **final
   visual quality first**. Study now, presets implemented (path B) before the benchmark scene.
3. **Documentation reflects the current architecture** (Blender = look and final render; engine = animation and
   preview; Python = pipeline and checks): README, technical decisions, implementer prompt (with T-071).
4. **Approved character assets are preserved and reusable:** each approved version is stored immutably
   (`assets/characters/<id>/versions/<ver>/`, hashes), the generator cannot overwrite it, and shots can reuse the
   stored master (T-075). `assets/characters/*/versions/` is a guarded path.
These must not distract from the current priority (reference-quality characters): T-075 runs now (it protects the
approved characters during the visual rounds); T-074 starts when a slot frees; docs go with T-071.

## 2026-11-17: finish running tasks first
No new tasks start until the running ones (T-060, T-061, T-065, T-070, T-071, T-072, T-075) finish. Each is merged
as soon as it passes review and the gate, keeping `main` up to date so the owner can see the results. T-074 and the
rest of the queue are on hold until the owner says otherwise.

## 2026-11-18: queue resumed; Supervisor decides overnight
The owner lifted the "no new tasks" hold: define and start the next tasks of the plan (`docs/process/IMPLEMENTATION_PLAN.md`)
and handle questions while the owner is away (~8 h). The original Supervisor session stays Supervisor (handover
reversed). Path B results wait for the owner's render approval; Codex stays on T-060 only.

## 2026-11-18: overnight results approved as shared systems
Approved and merged as opt-in shared systems (approved character versions unchanged until new versions are approved):
T-065 face v2 + fitted head, T-066 skin, T-068 garment details, T-053 personality profiles, T-070 hair round 2.
Hair: round 3 requested (boy crown from the close-up sheet, girl curls/fringe, third fringe/waves). Collisions (T-047):
before/after renders first, then the owner decides.

## 2026-11-18: always work with the latest, most reference-faithful character versions
All work (evaluations, shots, videos, new tasks) uses the latest character versions that most closely match the original
references. Mechanism: new shared systems are combined into **new character versions** as soon as they are approved
(pin bump), the owner approves those versions on renders, and the cast `"current"` (fidelity baseline) then points to
them, so every shot and test follows automatically. Old versions stay frozen and are used only with a stated
`legacy_reason`. Next: after the progress video (T-078), new boy and girl versions combining face v2 + fitted head,
skin presets/2, hair v3 (round 3 when approved), garment details and personality profiles.

## 2026-11-18: finish the running tasks, then stop and review
No new tasks after the running ones (T-060, T-078, T-079, T-080, T-081, T-082). Each is merged as soon as it passes
(path B after the owner's render approval). Then the owner reviews all results (progress video with boy 2.0.0 and
girl 0.11.0, hair round 3, collisions) to find issues and plan the next round. Follow-ups noted in
`docs/process/IMPLEMENTATION_PLAN.md` §5 stay unstarted until then.

## 2026-11-18: hair round 3 approved; keep improving fidelity until the characters match the references
Owner reviewed T-079 (hair v3 round 3): the characters look closer to the original references; merged as a system.
Standing direction: continue improving visual fidelity, round after round, until the characters match the references
as closely as possible (each round ends with a side-by-side sheet against the references for owner approval). The
"finish running tasks, then review" hold still applies to starting the next round.

## 2026-11-18: Codex assigned T-083 (fidelity gap report)
Owner: "give a task to codex to analyze our videos to compare with references and to create a report to know how far
we are from the original references". Codex (owner's PC, via relay) gets T-083, evaluation only (docs). This widens
the earlier "Codex only T-060" rule by this one task.

## 2026-11-18: boy 2.0.0 is the new current; girl 0.11.0 pending a strict comparison
- Owner: "I approve Boy 2.0.0 as the new current version." T-080 publishes 2.0.0 into the asset store, moves the
  `approved` pointer and the boy entry of `fidelity_baseline.json` (score 67.63 vs 66.41), then merges.
- Girl 0.11.0: owner wants a side-by-side sheet (original references | 0.10.0 | 0.11.0, identical angles and
  lighting) before deciding. **The girl's current version stays 0.10.0 until the owner approves a change.**

## 2026-11-18: girl 0.11.0 is the new current
Owner reviewed the strict comparison sheet (reference | 0.10.0 | 0.11.0, identical cameras and lighting,
`docs/evaluation/characters/T-081/girl_0.10.0_vs_0.11.0_strict.jpg`) and approved 0.11.0 as current. The fidelity
score drop (64.40 → 62.29, from the wider hair silhouette) is accepted by the owner; visually 0.11.0 is closer
(skin, hair colour, curls, neck, face). The hair width goes into hair round 4. T-081 publishes 0.11.0, moves the
`approved` pointer and the girl entry of `fidelity_baseline.json`, then merges.

## 2026-11-18: design points from the owner's Higgsfield reference set (owner: "accept suggestions")
The new references (stored in each character's `references/uploads/`, listed in their README) are primary targets
for round 2. Where they disagree with each other or with the earlier references, the owner accepted:
- **Boy backpack:** the flap design of `02_higgsfield_B06_backpack_back` (rounded flap, tab closure, front flap pocket,
  top grab loop, navy felt) is canonical; B07's zipped side-pocket design is used only for depth and strap path.
- **Boy sneakers:** cream soles and white stripes (earlier references and B07); B09 only for laces, stitching, toe cap.
- **Boy drawstrings:** plain felt cords with dark tips (B01/B02), not braided cords with metal tips (B08).
- **Girl fringe:** centre parting with two swept sections, as in G01, G02 and G04.
- **Girl back hair:** soft transition from the back section into the ringlets (earlier `ref_30`); G05 only for the
  bun, scrunchie and ringlet shape, not its horizontal ridge.
- **Girl collar:** rounded blouse collar (earlier references); G07 only for vest felt, embroidery, buttons and pocket.
- **Girl hair accessories:** blue-grey scrunchie with one pink felt flower (G04, `ref_30`).
- **Third character accessory:** the blue felt bow of `18_higgsfield_W02_blue_felt_bow` is canonical (no flower).

## 2026-11-18: two independent project audits before round 2
Owner: verify main is complete, then two independent, critical audits: Codex (T-084, `docs/audit/CODEX_PROJECT_AUDIT.md`)
and Supervisor (`docs/audit/SUPERVISOR_PROJECT_AUDIT.md`), then `docs/audit/PROJECT_AUDIT_COMPARISON.md`. Findings and
recommendations only; no major implementation before the owner decides. Round 2 waits for this.

## 2026-11-18: round 2 approved (character creation stays procedural)
- Owner agrees with Codex on the main audit disagreement: **character creation stays code-driven, procedural and
  reusable**; no manually sculpted or authored character meshes. Better procedural algorithms are welcome.
- Round 2 plan `docs/process/ROUND2_PLAN.md` (revision 2) **approved for execution**: Phase A workflow/CI/coordination
  first; Phase B faces, eyes, materials, garments; Phase C (parallel) two-character interaction + one limited
  environment/lighting/render experiment; Phase D (after owner approves Phase B visuals) hair, personality/acting,
  boy 2.1.0 / girl 0.12.0. Out of scope: third character, T-051, T-101–T-103, full environment, T-099, full T-074.
- **T-090 reference-fit optimiser included** in Phase B.
- **Fresh Supervisor session for round 2: yes.** The previous Supervisor session hands over and goes idle.

## 2026-11-18 (~19:20Z): Phase B review of T-092 and T-093 strict sheets (relayed by the previous Supervisor session)
- **T-092 materials (presets/3): approved** as the material system improvement. It enters the characters with the
  Phase D versions (boy 2.1.0, girl 0.12.0) through T-094, as planned. Nothing becomes current now.
- **T-093 garments: not approved yet; one more refinement round** on the same task (the system-only, opt-in merge
  stays; nothing becomes current). Focus: boy backpack per B06 (rounded flap, tab closure, front flap pocket, top grab
  loop, navy felt; B07 only for depth/strap path); girl collar and vest edges cleanly finished (no torn or frayed
  geometry, rounded blouse collar); less visible vest penetration in reach; sleeves, split bloomers with gathered
  cuffs, sneakers (cream soles, white stripes; B09 only for laces/stitching/toe cap), plain felt drawstrings with dark
  tips. Deliverable: updated T-087 strict sheets with the AI-target column and the reach before/after sheet, also on
  top of T-092 presets/3.

## 2026-11-18 (~19:40Z): roles (relayed by the previous Supervisor session)
Owner: "Let's keep one main Supervisor responsible for architecture, task planning, and coordination, with Codex as an
independent reviewer. We can use short-lived specialist architects only when deeper technical analysis is genuinely
needed, to avoid unnecessary token costs and coordination overhead." Recorded as `docs/process/DELIVERY_PLAN.md` §0
(roles, specialist architects, track labels in `TASK_LOG.md`). No change to current priorities or running tasks.

## 2026-11-18 (~20:00Z): two small optimisations (relayed by the previous Supervisor session)
Approved: (1) a time ledger, one line per READY report (build, render, tests, CI, wait in minutes, from timestamps the
tools already print); (2) lightweight previews while iterating (Workbench for geometry, low-sample Cycles crops for
looks), full T-087 Cycles settings mandatory for final sheets, approvals and goldens. Not approved: build caching,
selective regressions. Owner: "Keep both implementations lightweight and avoid unnecessary token consumption,
excessive logging, or additional agent communication." Applies to new tasks and rework rounds; running tasks are not
interrupted. Recorded in `IMPLEMENTER_PROMPT.md` (report item 11), `docs/tasks/_TEMPLATE.md`, `REVIEW_RECIPE.md`.

## 2026-11-18 (~20:35Z): no environment development for now (relayed by the previous Supervisor session)
Owner: "I don't want to work on environment development for now. Please keep it out of the current priorities."
T-098L stays a completed experiment; no environment follow-up task in this round. The T-098L render-cost finding
(final 1080p/128 spp about 16-20 min per frame on 4 CPU cores) was noted; no action requested.
Open owner finding (no task approved): the generated animations feel too fast. Playback and encoding are correct
(24 fps); the cause is the authored timing (beats packed with almost no holds). A timing-calibration proposal is
under discussion with the owner; nothing starts until the owner approves.

## 2026-11-18 (~22:35Z): Phase B approved (relayed by the previous Supervisor session)
Owner, after the strict sheets: "approve T-093 and T-089". With T-092 already approved, **Phase B is complete**.
- **T-093 garments (round 2, garment/2):** approved as the garment system (B06 flap backpack, cleaner collar and vest
  edges, reach correctives).
- **T-089 face and eyes round 3 (face_generic/3):** approved as the next face step. Notes for later face rounds: the
  boy keeps the new eye size but must keep sleepy heavy lids (the candidate reads slightly too alert); the girl still
  needs a rounder, fuller face and wider-open eyes (Codex's T-090b girl-face proposals are input for that round).
- Nothing becomes current until the Phase D versions (T-094: boy 2.1.0, girl 0.12.0). **Phase D is not started**; the
  owner decides which Phase D tasks run.

## 2026-11-18 (~22:50Z): Phase D approved (relayed by the previous Supervisor session)
Owner: "yes pass it to the supervisor and approve T-106 for codex". Distribution:
- **Now (cloud):** T-091 hair round 4; T-089b face polish (boy heavy lids, girl rounder face and wider eyes; the T-090b
  girl-face proposal is not adopted as is); T-093b garment completion (T-090b boy trousers/shoes proposal as a
  candidate, girl shorts leg-split control); T-104 continues. **T-097S** acting system (reaction model, emotion
  modulation and blending, animcheck signature checks; formats and code only) starts as soon as T-104 merges,
  because both claim `engine/anim/personality.*`, `content/personality/*` and `tools/animcheck/**`.
- **After T-097S** (split ~23:00Z, see below): T-097-boy and T-097-girl acting in parallel, each only its own character's files. The
  white-haired girl is out of scope now.
- **After T-091, T-089b and T-093b are owner-approved:** T-094 boy 2.1.0 and girl 0.12.0 via the T-088 script and
  T-087 strict sheets; then the e907 exchange is re-rendered with T-097B/G acting. The owner approves before current.
- **Codex: T-106** reference performance extraction (offline MediaPipe on the two reference videos; data table and
  contact sheets; tooling and evaluation only).

## 2026-11-18 (~23:00Z): T-097S split (relayed by the previous Supervisor session)
Owner judged T-097S too large; replaced by: **T-097-0** acting interface (`engine/scene/acting.h` + build stubs, the
Supervisor, merged first), then in parallel **T-097A** emotion blending, **T-097B** personality-driven reactions and
**T-097C** acting signature checks (small, when a slot frees up). The per-character acting tasks are renamed
**T-097-boy** and **T-097-girl** (after T-097A and T-097B merge; own character's files and solo test shots only).
The white-haired girl stays later. All other Phase D instructions stand.

## 2026-11-18 (~23:10Z): standing approval for tonight (relayed by the previous Supervisor session)
Owner (verbatim): "You have my approval to proceed without waiting for any further confirmations from me tonight.
treat all currently proposed and queued Round 2 tasks as approved, and continue the work according to the execution
order and dependencies you already defined. You do not need additional approval from me to move the work forward,
including starting the next tasks when their prerequisites are met. continue in the planned sequence, run parallel
tasks where appropriate, and only interrupt the flow if you hit a real blocker or need a major scope decision beyond
the current approved plan."
How the Supervisor applies it:
- Start each queued task when its prerequisites are met (T-097-0 -> T-097A + T-097B -> T-097C when a slot frees ->
  T-097-boy + T-097-girl; T-094 after T-091, T-089b, T-093b), at most 6 cloud tasks, Codex T-106 as assigned.
- Visual results (T-091, T-089b, T-093b, T-104, acting test shots): the Supervisor reviews the strict sheets against
  the original references; clearly closer -> merge as an opt-in system and continue; not clearly better -> one more
  focused round instead of merging. Every strict sheet is kept for the owner's morning review.
- T-094: build and publish boy 2.1.0 and girl 0.12.0, render the sheets and the re-rendered exchange, but leave the
  current pointers on boy 2.0.0 / girl 0.11.0 until the owner has seen the result.
- Standing rules unchanged. Interrupt the owner only for a real blocker or a scope decision beyond the plan
  (environment, third character, GPU, new dependencies). Morning: one short summary (merged, waiting, sheets, costs).

## 2026-11-19 (~02:55Z): round 2 close-out and round 3 start (relayed by the previous Supervisor session)
Owner, asked to choose explicitly: "I confirm all".
Round 2 close-out:
1. **T-094:** boy 2.1.0 and girl 0.12.0 become **current** (T-088 version-switch script) once the exchange re-render
   is finished and its CI is green.
2. **T-104:** the calibrated animation timing becomes the **default** (T-104d, the one-line default switch).
3. **T-091:** the flagged girl forehead (bare forehead in the face-front crop) is **accepted** as is.

Round 3, start now (disjoint claims, at most 6 cloud tasks):
- **T-111** interaction architect (short-lived): design doc + task files for object affordances in the asset format
  and a data-driven verb library mapped onto the existing planner (pick up, carry, pass, place first). Docs only.
- **T-101:** fix or wire the 3 old failing tests from T-077; no test loosened.
- **T-110** felt surface: one consistent Geometry Nodes fibre halo on felt surfaces (density per material preset);
  owns the skin surface (less plastic look).
- **T-109** face round 4 (after item 1 is current): fuller/rounder lower face, no grey shelf under the girl's lenses,
  mouth shapes at rest and in acting; geometry/eyes/mouth only.
- **Codex T-115:** tools/fit with a larger search budget on T-109's face parameters on the new current versions;
  proposals only; input for T-109 (top of NEXT_TASK.md).
Queued, no further approval needed to start when prerequisites are met: T-112 affordances + verb library and T-051
finger grasps (after T-111); T-113 expression library expansion (after T-109); T-114 two-character acting scene (after
T-113); T-102 repo cleanup after this wave. Still out of scope: third character, real props/paper fold (T-099),
environment, GPU, lip sync. Usual rules: cheap preview first, Cycles strict sheets for the owner, ledger lines; the
owner approves new character versions before they become current.

## 2026-11-19 (~03:00Z): overnight, Codex unavailable (relayed by the previous Supervisor session)
Owner: "Handle every thing." The standing overnight approval continues for the round-3 list and the round-2
close-out. Codex is not available until about 09:00 owner time: cloud work does not wait for Codex (T-109 starts once
the new versions are current, without T-115's results; its proposals are folded in later). The Codex assignment is
posted at the top of NEXT_TASK.md so it is ready when Codex returns.

## 2026-11-19 (~03:05Z): keep going (relayed by the previous Supervisor session)
Owner: "We have to go forward. No stop." Start each next task as soon as its prerequisites are met (T-109 -> T-113 ->
T-114; T-111 -> T-112a -> T-112b + T-051; T-102 at the end); do not idle for the owner or Codex. Hard limits unchanged:
no version becomes current beyond the approved T-094 switch without the owner, no loosened tests or thresholds, frozen
assets untouched.

## 2026-11-19 (~09:20Z): new independent review of the current state (relayed by the previous Supervisor session)
T-107 reviewed boy 2.0.0 / girl 0.11.0 (input 45679f3), now outdated. The owner wants a new independent Codex review of
the current state covering every improvement since: **T-116** (`docs/tasks/T-116.md`), evaluation only, right after
T-115 READY.

## 2026-11-19 (~10:10Z): 8-second cup-exchange showcase (relayed by the previous Supervisor session)
Pre-approved new task **T-117** (`docs/tasks/T-117.md`): one ~8 s, 192-frame boy + girl cup exchange on the current
versions with all merged opt-in improvements as shot-level overrides (faces, expressions, verbs + finger grasps,
reactions, gaze), review-quality 640x360 MP4 + contact sheet + short issue list. Starts automatically when T-113 and T-114
are on main; current versions and fidelity_baseline.json stay unchanged. Other queued work continues in parallel.

## 2026-11-19 (~11:40Z): round 4 starts now (relayed by the previous Supervisor session)
Owner: "i agree, use fable for three". Use the weekly capacity before the next reset (Sat 2026-11-21 00:00 UTC);
run work in parallel where write-sets do not overlap, about 7 sessions in total.
- T-118 hair round 5, T-119 garments round 3 + limb skin tone, T-120 gaze legibility: Fable 5.2.
- T-121 finger separation, T-122 candidate versions boy 2.2.0 / girl 0.13.0 (published as candidates only; not
  current; fidelity_baseline.json unchanged without explicit owner approval): Opus 5.5.
- T-123 (Codex): readability check tool (cup and pupil visibility per frame), then the end-of-round review.
- T-110 felt surface: PARKED (small gain, hoodie colour worse, +21-24% render time); branch kept.
- Unchanged: T-114 -> T-117 (Opus 5.5, merged round-4 results as opt-in overrides only); T-102 at the end. Hard limits
  unchanged.

## 2026-11-19 (~11:55Z): third-character readiness as a design input (relayed by the previous Supervisor session)
Bounded scope addition to T-118 (hair r5) and T-119 (garments r3): read the girl_white_hair_blue_dress references and
make the generators able to express her features (buns, S-wave locks, bow attachment; Peter Pan collar, rib cuffs as
reusable components), plus a `third_character_readiness.md` note each. No model, spec, version or render of her; her
references untouched; round 4 judged on the boy and girl only. Expected extra cost 10-20% on those two tasks.

## 2026-11-19 (~12:30Z): delivery format and render optimisation (relayed by the previous Supervisor session)
1. No 1080p. Final delivery is 720p (1280x720); consider efficient formats (e.g. 720p 10-bit HEVC/AV1 instead of 8-bit
   H.264).
2. 24 fps stays, every frame rendered (no "on twos", no 12 fps).
3. GPU rental (RunPod) waits until the render optimisation task (**T-124**, Opus 5.5, parallel to round 4) is finished.
   Measurement-driven: report what each setting really costs and changes, no predetermined target; profiles stay
   opt-in until the owner approves one as default.

## 2026-11-19 (~13:10Z): no GPU for now; motion checks; third character after round 4 (relayed)
1. No GPU rental for now (no RunPod accounts, keys, pods or endpoints). Evaluations and reviews first; T-124 continues
   on the cloud CPU.
2. Approved now: **T-125** automatic motion checks (Opus 5.5): flicker/shimmer, popping, interpenetration over time on
   baked/rendered frames; first cases e907 and T-114/T-117; thresholds from measurements; gate wiring only with
   Supervisor approval, never loosening existing tests.
3. Approved after round 4 is completed: **T-126** third character girl_white_hair_blue_dress, first version (body +
   face/eyes Opus 5.5; long hair on groom/4 Fable 5.2 using the T-118 readiness note; dress with the T-119 collar/cuff
   components, bodice, flared cable-knit skirt, tights, boots and a skirt cloth-sim prototype Fable 5.2;
   colours/materials Opus 5.5; Codex fit search then independent review). Her references stay untouched; the 18_W02
   bow is canonical. Published as a candidate with strict sheets; the owner approves before anything becomes current.
   Separate write-sets so parts run in parallel.
Not approved yet: GPU test/serverless, first story scene; the Codex end-of-round review timing stays as planned.

## 2026-11-19 (~13:35Z): CI speed task T-127 (relayed by the previous Supervisor session)
Approved items 1-5: shard the Blender tier (all shards required for the verdict), pinned prebuilt dependency image
with a fallback, cancel superseded runs on task/integration branches only, batch promotions, per-test durations.
NOT approved: item 6 (no reuse of built characters between tests, not even within one run). Binding: no negative
effect on workflow, reliability or stability; no test, threshold, golden or required check removed, skipped or
weakened; speed without loss of quality. Proof before merge: same test inventory, red probes (Blender, C++, Python,
regression), two consecutive green runs, before/after wall-clock and runner-minutes.
Also (~13:15Z): the third character starts when all round-4 implementation tasks are merged; it does not wait for
the Codex end-of-round review.

## 2026-11-19 (~13:50Z): tooling trial T-128 (relayed by the previous Supervisor session)
Approved as its own task (Opus 5.5), coordinated with T-127 so they never edit the same workflow files: (2) ccache for
session builds + mold linker, (3) OpenImageIO, ffmpeg/libvmaf, scikit-image compared against the existing code,
(4) pytest -n / ctest -j with 3x serial vs 3x parallel identical results. Binding: test first, adopt only on measured
benefit, no test removed/skipped/weakened, every change opt-in with a one-commit revert, owner told before any
default changes.

## 2026-11-19 (~14:10Z): "Animation" session environment (relayed)
New personal cloud environment "Animation" (env_01MTWJVTWBHG13yZcRS4DzCz): same network as Default; setup script
preinstalls the apt C++ packages, the checksum-verified bpy 5.3.0 wheel, numpy, Pillow (if missing) and a `blender`
shim (warn-only steps). All new implementer sessions use it; implementers note in the ledger whether setup was still
needed. Revert: start sessions without environment_id (Default); the owner can edit/delete it in Settings.

## 2026-11-19 (~14:20Z): workflow improvements evaluation checkpoints (relayed)
"Include an evaluation of these improvements in our upcoming phases and plans." A lightweight evaluation (Sonnet 5.5,
existing data only) at the end of round 4 (**T-130**, `docs/process/WORKFLOW_EVAL_R4.md`) and again at the end of
round 5: environment setup, CI speed (T-127), tooling trial (T-128), batch promotions, model choice (Fable 5.2 vs Opus
5.5), render optimisation (T-124, once a profile is chosen), Codex availability. Measured numbers only, with n and
dates; adopt / keep / revert per item; the report goes to the owner.

## 2026-11-19 (~15:00Z): Codex score calibration; review timing (relayed)
Codex does **T-129**, a fidelity score calibration analysis (option C): where the automatic fidelity score disagrees
with the owner's visual verdicts and why, with ranked metric-change proposals (analysis only, existing data only). The
independent character review (T-123 part 2) stays at the end of round 4. Reason: Codex tokens are limited, so
prioritise work that stays useful across future versions. (The workflow evaluation is renumbered **T-130**.)

## 2026-11-19 (~15:05Z): boy 2.2.0 / girl 0.13.0 become current (relayed)
Owner, verbatim: "approve 2.2.0 and 0.13.0 as current". **T-131** runs the T-088 version switch (as T-094 step 2):
test_store first; approve; rebaseline fidelity_baseline.json (boy 67.72 -> 67.25, girl 65.01 -> 64.13, owner-accepted:
the gains are lid colour, lens shelf and expressions, which the score does not measure, see T-129); golden baselines;
full gate before promotion; stop and report on any failure, nothing loosened. Hair r5, garments r3 and fingers stay
opt-in for 2.3.0 / 0.14.0.

## 2026-11-19 (~15:10Z): candidate versions 2.3.0 / 0.14.0 (relayed)
Owner, verbatim: "approve the 2.3.0 and 0.14.0 candidates task". **T-132** (Opus 5.5): 2.3.0 / 0.14.0 = 2.2.0 / 0.13.0
+ T-118 hair r5 + T-119 garments r3 (limb skin as accepted) + T-121 fingers; candidates only (no current change, no
fidelity_baseline or golden change); strict + expression sheets, 100% crops, fidelity report; an ingredient that
regresses is left out and reported. Starts when T-119 and the T-131 switch are on main.

## 2026-11-19 (~15:20Z): third character starts now (relayed)
Owner, verbatim: "Yes, please start building the third character now, as you recommended. Start with the body, face,
hair, and materials". Replaces the "after round 4" start for T-126 a (body/face, Opus 5.5), b (hair, Fable 5.2) and
d (materials, Opus 5.5, render cost vs the T-124 baseline); c (dress + skirt cloth prototype, Fable 5.2) starts once
T-119 is on main; Codex fit + review after the first version. Candidate only (0.1.0), strict sheets; boy and girl
untouched; shared-code changes sequenced by the Supervisor. Pending owner approval, not started: girls' hair lead
(incl. auburn round 6), materials round 3, expression fidelity, cup-hold readability.

## 2026-11-19 (~20:00Z): round-5 plan, Phases 1 and 2 in parallel (relayed)
Owner: "Yes, I approve this plan. ... Start Phase 1 and Phase 2 in parallel, but limit concurrent sessions and avoid
overloading the Supervisor and wasting usage capacity." Purpose: fix every e910 issue (T-117 §3), Animlog feedback
(timing/spacing, arcs, overlap, anticipation) and the girls' eye shapes; shared improvements first, the scene second.
Cap: at most 6 implementer sessions at once; waves; finish nearly-done work first; Animation environment.
Phase 1: T-134 E1 reach mechanics (Fable, one session), T-135 E1m measurements, T-136 E2 blinks + E3 gaze chain (one
session, shared files), T-138 E4 grasp accuracy (after T-134), T-139 E5 animcheck attribution, T-140 C1 framing.
Phase 2: T-137 faces F1a/F1b/F2 (Fable, one session, overrides; owner approves each). Phase 3 later: S1 shot
(staging -> acting -> final, owner looks between), S2 Codex review, D1 adopt proven features as defaults (owner).
All engine changes opt-in; no test, threshold, golden or current-version change.

## 2026-11-19 ~20:30Z: architecture cleanup A1–A4 (relayed by the original Supervisor)
Owner: "approve A2 first, then A1 and A4, then A3. Make sure these changes do not negatively affect our existing work,
ongoing development, or project stability." Basis: read-only architecture review of main 6d7bf37 (legacy pre-TD-42
renderer/SDF/apps ~5.5k LOC still built and run per CI; hand-written hair spline maths; all past generator versions kept).
- A2 = T-141 (Fable): native Blender hair-curve fluff experiment, opt-in, after T-137 faces.
- A1 = T-142 (Opus): legacy renderer/SDF/apps out of default build + per-run CI (nightly, tests kept, archive not delete).
- A4 = T-143 (Sonnet): extend T-102 cleanup (archive lipsync, experiments, duplicate helpers byte-identical).
- A3 = T-144 (Opus): LAST; plan which generator versions to retire, owner approves before anything is removed.
Binding: no negative effect on existing work/stability; no test, threshold, golden or required check removed or
weakened (nightly move needs a documented equivalent); current/candidate characters unchanged; archive not delete; a
revert path; green full gate before each merge; no branch deletion. Phase 1+2 keep priority within the 6-session cap.

## 2026-11-19 ~20:45Z: A1 changed to full removal (relayed by the original Supervisor)
Owner: "I approve changing A1 to a full removal of genuinely unused legacy code from main. I also approve removing tests
that exclusively cover the deleted legacy functionality, provided they have no relevance to any active system. Before
removing anything, carefully verify all dependencies, preserve the legacy code and tests through a permanent Git tag,
and ensure all active functionality and regression tests remain intact. Do not remove any shared components still
needed by the current engine, especially collision-related SDF functionality. Run all required checks before merging,
and make sure the entire change can be safely reverted." T-142 updated: dependency report first (to owner), permanent
tag `archive/legacy-engine-renderer-2026-11-19`, one revertible commit, full gate + nightly Windows + backup runs.
A2/A4/A3 unchanged.

## 2026-11-19 ~20:55Z: Codex does T-150 then T-151 (relayed by the original Supervisor)
Owner order: Codex (about 40% allowance left) does T-150 (eye-shape targets for both girls, forwarded to T-137) then
T-151 (independent dependency map for A1/T-142, compared with T-142's report before any deletion). Analysis only.

## 2026-11-19 ~22:20Z: token economy for all sessions (relayed by the original Supervisor)
Keep token use as low as reasonably possible; essential work only; STATUS/READY in a few lines; short reports and
READMEs; no re-reading large files or re-running renders without need. Added to IMPLEMENTER_PROMPT.md.

## 2026-11-19 ~22:45Z: A1/T-142 decisions D1–D3 (relayed by the original Supervisor)
- D1 = option B: keep Studio Production, Viewport, Timeline; remove the obsolete Render panel; replace readImageRgb8
  with stb_image. Remove the legacy renderer only after the remaining Studio is verified (Linux + nightly Windows
  build, shot_workflow tests, headless smoke run that opens a scene and steps the timeline), with evidence.
- D3 confirmed: keep all SDF, fuzz and shared character code used by active systems (sdf.* whole, character.*, fuzz/).
- D2: main has no branch protection or rulesets; the "required check" is our own (ci_status.py REQUIRED_JOBS, gate
  verdict needs, combine_check_reports.py, check_all renderer_skip). Update all in the SAME commit that removes the
  renderer job; prove with a green full run plus a T-127-style broken-commit probe that still turns the gate red.
  Tag first (archive/legacy-engine-renderer-<date> via backup), one revertible commit, manual nightly Windows + backup runs.
- Owner wants the third character's combined 0.1.0 published as a CANDIDATE (not current).

## 2026-11-19 ~23:10Z: rotate the round-2 Supervisor (relayed by the original Supervisor)
Adopt Codex T-152 recommendation 1: finish the current batch, write `SUPERVISOR_HANDOVER_R3.md`, then the round-3
Supervisor takes over from that file.
## 2026-11-19 ~23:30Z — Phase 3 S1a/S1b/S1c postponed
Owner (relayed by the original Supervisor and the round-2 Supervisor): Phase 3 S1a (staging preview), S1b (acting
preview) and S1c (final render) of the 8 s shot are POSTPONED. Do not start them overnight. Replacement tasks to
follow; until then no tasks outside the approved list. Supersedes the S1a/S1b/S1c items in SUPERVISOR_HANDOVER_R3.md.

## 2026-11-19 ~23:40Z — Replacement for S1a/S1b: fidelity score fix only
Owner (relayed by the original Supervisor): the only replacement is the fidelity score fix, T-153 (Opus 5.5):
T-129 proposals as a new opt-in score version; current score, thresholds, baseline and gate unchanged; evaluate
against all past owner decisions (incl. T-122) and T-129 blind spots (T-150 targets for eye shape); report + tests.
Adopting it as default needs the owner. NOT approved: review page, prop library, third-character expression set.
