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
