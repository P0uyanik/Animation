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

## 2026-11-20 ~06:40Z — Morning decisions (relayed by the original Supervisor)
1. Hourly self-check/scheduling: skipped for now, fixed separately later.
2. Resume the approved queue by dependency, in parallel where independent (cap 6).
3. Guard tests `test_hair_r5` / `test_hands_r2`: option (a), a documented allowlist of NAMED owner-approved candidates
   (id, decision reference, date) checked by the tests themselves; no removal, weakening or global bypass; a test proves
   an unlisted candidate is still rejected → T-154.
4. After 3: publish boy 2.3.0, girl 0.14.0 and third character 0.1.0 as CANDIDATES with strict sheets
   (reference | current | candidate | target) + crops; current versions unchanged → T-155.
5. T-137 F1a/F1b/F2 not final (eye openings too wide). Follow-up on the same face area driven by T-150 targets.json,
   measured per eye → T-156 (Fable 5.2).
6. T-138: 4.3 mm gap not accepted. Evaluate (a) wider band, (b) fewer contacting fingers, (c) both; gaps, penetration,
   shot-size close-ups; recommend the most natural; opt-in → T-157 (Opus 5.5).
7. Fidelity v2 stays EXPERIMENTAL, not default. Validation on independent unseen examples later (Codex fits; not urgent).
8. T-124: keep the existing final preset; comparison paths to the owner before any switch to final720.
9. New task: make girl 0.13.0's build deterministic (ears/upper lids differ in ~half of 9 runs); root cause, regression
   tests (repeated builds identical), no intended-geometry change; check boy and third character → T-158 (Opus 5.5).
10. Let T-141 finish; T-144 (A3) PLAN ONLY when a slot is free.

## 2026-11-20 ~07:00Z — Release faces, publish versions, lashes first, ears (relayed by the original Supervisor)
Owner: "good progress with the faces; the main issue now is the eyelashes, which still look quite different from the
references; we also need to work on the ears; go ahead and release these changes and publish new character versions."
1. T-137 F1a, F1b, F2 (incl. F2 face override) APPROVED → merge; publish boy 2.3.0 / girl 0.14.0 (T-132 content + T-137
   faces) and third character 0.1.0 (T-126 a–d + T-137 F1b; T-133 proposal only if it improves) as candidates with strict
   sheets (reference | current | new | target), eye crops, expression sheets; guard allowlist (T-154). Boy/girl become
   CURRENT only after the owner's one-word OK on those sheets (hair/garment/finger changes not yet reviewed), via
   version_switch + fidelity_baseline rebaseline citing this decision. Third character: 0.1.0 is her first published version.
2. Eyelashes are the top face priority: T-156 becomes lash-first (thin dark upper liner, short separate outer-corner
   lashes, no brown band; refs third 01/04/14, auburn ref_30/G01/G02, boy hero24/val27), then T-150 eye-shape targets.
3. Ears: after T-158 (deterministic builds), an ears round (Fable 5.2) for all three characters → T-159.
## 2026-11-20 ~07:20Z — Hair round 6 on the base groom system (relayed by the original Supervisor)
New task T-160 (Fable 5.2): all three characters vs refs, base groom system first (shape/silhouette at shot size).
Boy: crown height, staggered whorl petals with dark channels (val27 back, B04/B05), keep pickup sightline under fringe.
Auburn girl: lower outer sweeps (less bare arc above brows), separate tapered ringlet ends (ref_30, G04/G06), bun with
wrapped strands, flower readable from front. Third girl: softer, less rope-like locks with tapered tips, softer fringe
edge, buns with wrapped strands, bow seat (refs 01/02/07/17_W04). Inputs: T-116 hair section, T-133 review, T-118/T-126b
readiness notes. Opt-in overrides; strict sheets + 100% hair crops (front, 3/4, back) + turntable/motion flicker check
(T-125); folds into next versions. NOT in scope: T-141 hair curves; T-141b NOT approved (owner to discuss); T-141 may
merge as an opt-in tool once green. Fringe coordination: T-160 owns the fringe; T-156 (eyes/lashes) does not edit it.
Also pending for the owner: T-144 A3 plan `t-144-claude-retire-versions@8a34069` docs/evaluation/T-144/PLAN.md, options
(a) registry-only retire + named archival-build allowlist (recommended), (b) file comparisons (weakens checks), (c) defer.

## 2026-11-20 ~07:35Z — T-144 A3: option (b) (relayed by the original Supervisor)
Compare each published version's stored built files against fresh builds, then retire and remove only generator code
that no current or candidate version pins. Start only after T-158 (deterministic builds) merges, when a slot is free.
Conditions as before: frozen built results stay retrievable; regression/golden checks unchanged or replaced by
equal-strength file comparisons; tag first; one revertible commit; full gate green. Report the comparison results (any
mismatches) BEFORE removing anything. Plan: `t-144-claude-retire-versions@8a34069`, docs/evaluation/T-144/PLAN.md.

## 2026-11-20 ~07:35Z — "yes go ahead with all four" (relayed by the original Supervisor)
1. Status board `docs/process/STATUS.md` (Sonnet 5.5) → T-162; then the Supervisor keeps it current at every merge or
   dispatch (same commit). Lanes: Character look (T-156, T-160, T-158 → T-159 ears); Release (T-155); Interaction
   (T-157, then hands round 2). Each task: id, model, state, ETA; owner-waiting items with sheet links and numbered
   choices; queued items with start conditions (T-144 option b after T-158; hands round 2 after T-157 + T-155).
2. Starter prop library (Sonnet 5.5) → T-163: 10–15 simple felt props (cup, bowl, plate, spoon, book, ball, box with lid,
   small toy, apple, pencil, block, basket) with affordances and grasp points per T-111/T-112, existing material
   presets; own new files only; contact sheet + one verb test per prop.
3. Temporary session cap 8 until 08:20Z, then 6.
4. No other new tasks; lanes; merges batched per lane.
Codex T-161 (relay f33c4868): reference targets for lashes, ears, hair silhouette → forward targets.json to T-156/T-160.

## 2026-11-20 ~08:10Z — Workflow efficiency R5 (relayed by the original Supervisor)
Report `docs/process/WORKFLOW_EFFICIENCY_R5.md` (+ `docs/process/T-162/data.csv`, branch
`t-162-claude-workflow-efficiency@b07c29e`, a review separate from the T-162 status board) merged docs-only.
Implement now, within lanes and cap: (1) the gate posts/edits the PR #2 comment only for integration/*, staging, main;
no session subscribes to PR #2, waits use one background `gh run watch`; checks and coverage unchanged → T-164.
(3) `tools/ready.py` preflight (branch pushed, claim + write-set, new tests registered, doc links) then ONE short READY
line to the parent with the session's cost and context size; IMPLEMENTER_PROMPT updated → T-165.
(4) Rework rule (context > ~250k and narrow feedback → fresh session with pointer brief or after compaction; one
consolidated feedback message per round) → WORKFLOW.md, IMPLEMENTER_PROMPT.md (Supervisor, done).
(5) Shared task kit: shot before/after sheet tool, logged-run wrapper keeping full logs, gate-wait helper,
one-render-at-a-time queue; reuse tools/review/recipe.py; new tasks point at the kit → T-165 (with item 3).
Item 2 (liaison rotation) NOT now: the owner picks the time. Rules: analysis-backed, no weakening of checks, revertible.

## 2026-11-20 ~08:20Z — T-155 approved, T-157 stays opt-in, T-124 defaults (relayed by the original Supervisor)
1. T-155 approved: make boy 2.3.0 and girl 0.14.0 CURRENT (version_switch, fidelity_baseline rebaseline citing this
   decision, golden/version index; full gate green before promote). Publish the third character 0.1.0 as her first
   version. If any check fails: stop and report; no loosening.
2. T-157: keep the wider contact band (option a) OPT-IN; revisit after hands round 2 is done and verified. Hands round 2
   starts once T-155 is published (queue).
3. T-124: `final720` becomes the DEFAULT final render setting (720p, adaptive threshold 0.05, persistent data; others as
   measured); the old 128 spp/0.01 preset stays available by name. Delivery: HEVC 10-bit default encode, H.264 8-bit as
   compatibility fallback (settings per the T-124 README); masters stay lossless. Small task (→ T-166): defaults in
   shot_render/run_shot and the encode step, docs/tests (assert new default + fallback), revertible, full gate green;
   golden/image tests that depend on the old preset keep their own pinned preset; nothing weakened.

## 2026-11-20 ~08:30Z — Owner liaison rotation
New owner liaison: session_01NPjxeKamtbdzi3YwrgsWXU ("Plush Studio – Owner liaison"); owner-facing reports and
READY/decision requests go there, not to session_01NPjxeNTmHt2DtBN8F8uLqB. Handover: [LIAISON_HANDOVER](LIAISON_HANDOVER.md).

## 2026-11-20 ~08:20Z+ (09:20 CET) — Guard option 1; restart T-164/T-165 (relayed by the owner liaison)
"1 yes, and restart T-165 and T-164". test_hair_r5 / test_hands_r2 accept a CURRENT version only when listed in the
allowlist with a named owner-decision ref (`current_decision`); boy 2.3.0 and girl 0.14.0 carry this decision plus the
~08:20Z switch approval; every other case still fails; no removal, weakening or global bypass. Implemented on
`integration/t-137`; unblocks the T-155 switch. T-164 was already merged into the Interaction batch; T-165 restarted.

## 2026-11-20 ~08:35Z (09:35 CET) — Temple hollow, both girls (relayed by the owner liaison)
Unnatural hollow at the temple above/in front of the ear (T-160 strict 3/4 crops, both girls). Diagnose (head geometry,
ear placement, hair-to-head connection, glasses arm), fix for both girls, smooth face–temple–ear–hair transition,
before/after close-ups. Folded into T-159 (ears) as Part A, started now on the T-158 base; candidate/opt-in only.

## 2026-11-20 ~08:50Z (09:50 CET) — Feedback on T-160 r6 and the boy's face (relayed by the owner liaison)
1. Boy face: unnatural outward bulge in the side/3/4 face contour (vs val27_threequarter_right / val27_side_right) → T-168.
2. Boy nose needs improvement → T-168 and future face tasks.
3. Hair: do not force a felt look; the reference hair is more natural. Decisions follow the reference images; goal = closer
   to refs.
4. Girls' hair gaps confirmed (auburn: too bulky/fuzzy vs glossier defined curls, bun darker/untidy, fringe covers too much
   forehead, curls shorter than G05; third: jagged spiky fringe vs soft wisps, side/back long hair flatter/stringier, less
   full than 01/02).
5. Boy hair currently better than the girls' (owner unsure); all three still noticeably different from refs.
Actions: hair round 7, all three, reference fidelity over felt look (fewer petal/leaf shapes on the boy, irregular fringe,
natural strand grouping) → T-167. r6 NOT adopted; stays opt-in (merging as an opt-in base is fine). Bow seat pending.

## 2026-11-20 ~09:00Z (10:00 CET) — Bow seat (relayed by the owner liaison)
Third girl's bow: position it from the reference images: front seat (refs 01/02), on her right side (viewer's left), at
the front hairline just below/in front of the right bun, above the temple, slightly tilted, partly over the fringe.
Refine position/size/tilt in T-167; no side seat.

## 2026-11-20 ~09:05Z (10:05 CET) — HOLD on queued work (relayed by the owner liaison)
Running tasks continue; do NOT start queued/planned tasks (T-166, T-144 option b, hands round 2, next versions, new
Codex tasks) until the owner says "Start the planned automatic tasks" (via the liaison). Free slots stay empty.

## 2026-11-20 ~09:10Z (10:10 CET) — Pause T-167 and T-168 (relayed by the owner liaison)
Pause T-167 (hair r7; WIP pushed `t-167-claude-hair-r7@dc85c98`) and T-168 (boy face; diagnosis only,
`t-168-claude-boy-face@de0eff2`) to save tokens; no restart until the owner's explicit word via the liaison.

## 2026-11-20 ~09:35–09:40Z (10:35–10:40 CET) — Pause all running tasks (owner, directly and via the liaison)
T-159 paused (~10:35 CET; `t-159-claude-ears@20a9363`, temple fix opt-in at cafa12c, ears not started), then T-155 and
T-156 (owner directly), then "Pause all running tasks" (~10:40 CET). Paused with all WIP pushed:
T-155 `t-155-claude-candidates-r2@543bfa1` (boy 2.3.0 / girl 0.14.0 current on the branch only; third 0.1.0 published,
no pointer; boy/third expression sheets not rendered), T-156 `t-156-claude-eye-targets@2f89842` (third closed + strict
renders and READY pending), T-159, T-167 `dc85c98`, T-168 `de0eff2`. T-158 and T-165 were already merged (main
2a02532). No dispatches, merges, promotions or Codex tasks; in-flight CI may finish but is not acted on. Nothing resumes
until the owner's explicit word via the liaison.

## 2026-11-20 ~09:50Z (10:50 CET) — Codex T-169 hair reference study (relayed by the owner liaison)
Analysis only, write-set `docs/evaluation/characters/T-169/**`; posted on relay-channel@2987afa (NEXT_TASK.md). Feeds T-167.

## 2026-11-20 ~09:55Z (10:55 CET) — "start all implementers" (relayed by the owner liaison)
Resumed from pushed WIP: T-155 (543bfa1; switch already done on the branch with the owner's direct OK; boy/third expression
sheets), T-156 (2f89842), T-159 (20a9363: cheek seam diagnosis, then ears), T-167 (dc85c98; fold in T-169 when READY),
T-168 (de0eff2: proposed fix, opt-in cheek-pad fade + upturned nose, candidate only). Reviews/merges resume. Queued/planned
tasks (T-166, T-144, hands round 2, next versions) STAY ON HOLD until "Start the planned automatic tasks".

## 2026-11-20 ~14:30Z (15:30 CET) — Not final: fix all reported issues first (relayed by the owner liaison)
T-156: 3/4 white flap past the outer corner (both girls), creases under the auburn lower lid, lash colour/fullness per
refs (auburn warm dark brown, fuller), pale pink teardrop above closed lids, third girl's closed-eye upper region.
T-168: smaller, rounder nose (soft nub), lower face less receding (val27). T-159: temple + cheek seam + ears for all
three incl. the boy. T-167 continues per T-169. Strict sheets + 100% close-ups with all fixes; approval only after that.

## 2026-11-20 ~15:12–15:25Z (16:12–16:25 CET) — Ownership and T-155 hold (relayed by the owner liaison)
Ears are T-159's for all three. Disjoint write-sets: T-159 = face_features.shape_face_v2 + face_generic.build_ears;
T-168 = face_v3/lower_face.py + face_features.build_nose (boy contour + nose); T-156 = face_v3/lids.py + eye/lash
materials. Merge order T-159 then T-168; one integration branch `integration/r3-faces` for the candidate builds.
HOLD T-155 (`t-155-claude-candidates-r2@2774c13`, incl. third 0.1.0): no new version until the fixes are approved;
current stays boy 2.2.0 / girl 0.13.0. The next versions bundle T-155 + T-156 + T-159 + T-168 + T-167 as ONE set.

## 2026-11-20 ~15:25Z — Reference videos (owner via the original Supervisor)
`docs/references/video_paperboat.mp4` and `video_watertable.mp4` (on ones, 24 fps) are the primary motion/acting
reference for animation, interaction and acting tasks (hands round 2, the S1 rebuild), with T-106, content/timing and
content/personality derived from them.

## 2026-11-20 ~15:45Z (16:45 CET) — T-170 world style plan (planning only; exception to the hold)
Delivered: `docs/evaluation/world/T-170/README.md` (style guide, material library, construction architecture, scene
rules, 7-phase plan ~19–25 task-days, 8 owner questions). The owner reviews it before any development.

## 2026-11-20 ~16:10–19:20Z — Ears, boy face, hair, world research (relayed by the owner liaison)
- ~16:50Z: boy ears, then ~17:15Z "same for girls' ears" → T-159 (shape/size per refs and T-161 targets; auburn glasses
  arm rests on the ear). ~17:20Z: boy face "has to be softer" → T-168 r4. ~17:25Z: hair r7 accepted for now; boy flicker
  must meet the existing limit (re-measured ~17:35Z: still over, caused by the new crown tufts).
- ~17:45Z: T-170b option 2 (Poly Haven/ambientCG hosts allowed) → T-170c CC0 test: Poly Haven wood_table,
  oak_veneer_01, laminate_floor_02, HDRI lebombo confirmed.

## 2026-11-20 ~19:20Z (20:20 CET) — Decisions (relayed by the owner liaison)
1. T-170c option 2: acg-download.struffelproductions.com allowed → T-170d (ambientCG rug/fabric test, research only).
   World scope guidance (binding): "we do not need every object seen in the reference videos, nor match them exactly. Any
   table is fine; any simple, allowed, easy-to-make objects are acceptable — that is our priority. If we build a scene
   later, its objects should make sense together and feel related. I don't want to spend this much time on building
   props." → simplest objects, minimal prop effort; T-170d trims the plan and estimate.
2. T-168: no further pass; r4 (`t-168-claude-boy-face@49b3f56`) goes into the bundled set; remaining issues (chin below
   the mouth, jaw underside, faint cheek line) logged for a later phase.
3. T-167: render r6 vs r7 comparison sheets for all three (same views/lighting, incl. 100% hair crops), owner chooses per
   character; boy flicker decision waits for this; no look changes.
4. T-156: continue; owner decides when finished.
5. T-159: ears pass 2 (`t-159-claude-ears@aca5de6`) accepted for now into the bundled set; ears slightly wide vs the head
   logged for later.

## 2026-11-20 ~20:10Z (21:10 CET) — World materials (relayed by the owner liaison)
"my goal is not to create new materials. Use whatever ready-made materials are already available and simply combine
materials that look good together. Creating materials is time-consuming and costly; not considering that now."
→ T-170 plan = ready-made materials only: the CC0 sets already picked, existing project presets and Blender built-ins.
Adjustments are limited to tint, scale and mapping. No new material authoring, no tuning rounds, no procedural material work.
The plan stays on hold. Amendment: `docs/evaluation/world/T-170/cc0_test/ambientcg/README.md` section 2.1.

## 2026-11-20 ~20:20Z (21:20 CET) — Start T-166 and T-144 (b) report step (relayed by the owner liaison)
Explicit start (not the general "Start the planned automatic tasks"): T-166 (final720 default + HEVC 10-bit delivery,
H.264 fallback, old preset kept by name; Sonnet 5.5) and T-144 option (b) REPORT STEP ONLY. The report compares builds
and lists the generator versions the bundled candidates depend on (T-156/T-159/T-167/T-168 overrides, boy 2.3.0 /
girl 0.14.0 / third 0.1.0); none of those may be retired. Nothing is removed before the owner reviews the report. Write-sets
stay disjoint from running tasks. Hands round 2, the version release and the world plan stay on hold.

## 2026-11-20 ~20:30Z (21:30 CET) — Session cap (relayed by the owner liaison)
The session cap is temporarily 7, until the bundle merges or the owner says otherwise. The T-168 session (archived ~20:06Z,
branch `t-168-claude-boy-face@49b3f56` kept) may be unarchived if follow-up work is needed before the bundle merges; otherwise it stays archived.

## 2026-11-20 ~20:50Z (21:50 CET) — T-144, T-167, release priority (relayed by the owner liaison)
1. T-144: option (c), no change now. The old generator versions are documented as "legacy, do not pin"
   (`docs/CHARACTER_SYSTEM_VERSIONS.md`). Boy 1.0.0's rebuild difference is a documented known exception. export/5 and groom/2 are kept.
   The report is merged and the session archived.
2. T-167: the boy uses hair r6 and the girls use r7. The boy's hair improvement comes later. No further hair work now.
3. PRIORITY: make the new character versions release-ready as soon as possible. Finish T-156 (owner decides on its final sheets). Then assemble
   integration/r3-faces: T-155 content + T-156 + T-159 ears/temple + T-168 r4 + hair (boy r6, girls r7). Verify every change
   shows, render final strict sheets + 100% crops for all three and send them for owner approval. Then the T-155 release (owner types OK
   in its session), test-reference updates and the full gate. Nothing else competes for slots; T-166 may finish; the world plan stays on hold.

## 2026-11-20 ~22:00Z (23:00 CET) — T-156 accepted; narrow guard allowances (relayed by the owner liaison)
1. "I accept T-156 for this release" (`t-156-claude-eye-targets@6b3ddf4`, in integration/r3-faces). Remaining limits are logged
   for later: auburn 3/4 pale strip and white past the outer corner, soft under-lid ledge, closed mound 8 mm, skin closes in the
   last quarter of the blink.
2. "I approve the narrow guard-test allowances for the three specified versions", per
   `docs/evaluation/characters/R3/RELEASE_STEP.md`: test_face_t168, test_hair_r6 and test_face_r5 allow the opt-in features (T-168
   face options, groom/5, T-156 closed_fill) ONLY for boy 2.3.0 / girl 0.14.0 / third 0.1.0, each with its owner decision
   reference, and stay strict for everything else. The test_face_v4 current pins move to 2.3.0/0.14.0 at the release.
   Next: final sheets for owner approval, then the release.

## 2026-11-20 ~22:10Z (23:10 CET) — Release numbering (relayed by the owner liaison)
Option (A): R3 is released AS boy 2.3.0 / girl 0.14.0 / third 0.1.0, rebuilt from the R3 stacked specs. This replaces the
branch-only builds from T-155 (~08:40Z), which were never published on main. On integration/r3-faces the approved pointers go back to
2.2.0/0.13.0 until the owner's final OK on the sheets. The guard allowances keep these version names.

## 2026-11-20 ~22:25Z (23:25 CET) — Hands round 2 start (relayed by the owner liaison)
Start HANDS ROUND 2 (→ T-171) automatically right after the R3 release is published and its full gate is green. This is
an explicit owner go; other held tasks stay held. Scope as queued: boy finger separation, pre-shaping during the reach,
finger-by-finger close, soft contact; then revisit T-157 option (a) as the default. Base: the released 2.3.0/0.14.0/0.1.0.
Candidate/opt-in, with strict sheets and clips for owner review.

## 2026-11-20 ~22:35Z (23:35 CET) — Test video after the R3 release (relayed by the owner liaison)
Once the R3 release is published (gate green), render a 5–8 s TEST VIDEO with the released characters (boy 2.3.0 /
girl 0.14.0 / third 0.1.0) from what already exists: reuse an existing shot/clip setup, with no new animation or environment
work. Use the new defaults (final720, HEVC 10-bit) plus an H.264 copy, and send the paths. It may run in parallel with T-171 → T-172.

## 2026-11-20 ~22:45Z (23:45 CET) — Codex T-173 local GPU render benchmark (relayed by the owner liaison)
Codex task T-173: a render benchmark on the owner's own GeForce PC. Measurement only: CPU vs OptiX vs CUDA at final720 and
legacy128. Write-set `docs/evaluation/rendering/T-173/**`. Posted at the top of NEXT_TASK.md on relay-channel@722c00e9. No other
change.

## 2026-11-20 ~22:55Z (23:55 CET) — T-174 research: animation reuse vs build (relayed by the owner liaison)
New research-only task (docs-only write-set, no implementation, no Codex). For walking, running, sitting, standing up, reactions,
object interaction and character-to-character interaction: what exists, what we can reuse, what we keep, what needs custom
work, how to simplify, and the pros and cons. Deliverable: a keep/reuse/build matrix, ONE recommended approach with a revised estimate,
risks and owner questions → `docs/tasks/T-174.md`.

## 2026-11-20 ~23:15Z (00:15 CET) — Answers to the T-174 questions (relayed by the owner liaison; record only)
(a) The content goes to YouTube, so treat the project as commercial: CMU is OK with attribution; no non-commercial (NC) data.
(b) Walk/run/sit/stand are needed eventually, not urgently. (c) Mixamo is not used unless the owner decides otherwise later.
(d) mocap.cs.cmu.edu and accad.osu.edu are allowed in the Animation environment. (e) Style must match the reference videos
(stylized, chibi timing per T-106 and content/timing), not realistic mocap. The owner is still deciding code vs no-code.
The T-174 plan stays ON HOLD; nothing starts.

## 2026-11-20 ~23:35Z (00:35 CET) — Start the T-174 locomotion layer (relayed by the owner liaison)
Explicit owner go → T-175: CMU mocap importer (on the existing retarget code), foot-lock pass, and a chibi lean/stride/timing
filter matching the reference-video style. ~3.5–4 task-days. CMU only, with attribution; no Mixamo, no NC data. Opt-in, with no change to
existing shots' defaults. The write-set is disjoint from the release, T-171 and T-172. No character geometry/look or rig change (report first).
File/function ownership with T-171 is assigned in `docs/tasks/T-175.md`. First delivery: walk + sit/stand on the boy and auburn
(third if possible), with feet-planted numbers and short clips for owner style review before wider use.

## 2026-11-20 ~23:11Z (00:11 CET) — R3 release approval (owner, typed directly in the T-155 session)
"I approve releasing R3 as boy 2.3.0, girl 0.14.0 and third 0.1.0 and making 2.3.0/0.14.0 CURRENT, without reviewing the
final sheets, on condition that all checks pass and the liaison finds no new defect on the final sheets; otherwise stop and
report." (Verified by the Supervisor in the T-155 transcript, user message 23:11:12Z.) Release write-set: the T-155 row in
OWNERSHIP.md. The branch-only 2.3.0/0.14.0/0.1.0 store folders (never on main) are replaced by the R3 rebuilds under the same numbers.

## 2026-11-21 ~00:15Z (01:15 CET) — Sheet-check condition waived (relayed by the owner liaison)
"I want to approve these versions, and there is no need for Claude to review them. Accept these versions as the Current
Versions as quickly as possible, push and merge the code, so we can start the next tasks." → The liaison no-new-defect
condition from ~23:11Z is waived. Boy 2.3.0 / girl 0.14.0 become CURRENT, third 0.1.0 is published, the test_face_v4 pins
are updated, and the full gate is still required (no test skipped). Then merge/promote, then auto-start T-171 + T-172. Final sheets
are kept for the record.

## 2026-11-21 ~00:25Z (01:25 CET) — Supervisor rotation after the R3 release (relayed by the owner liaison)
Finish the R3 release (merge + full gate green + T-171/T-172 started). Then write `docs/process/SUPERVISOR_HANDOVER_R4.md`
(pointer-based) and push it. Start no new tasks after that. The round-4 Supervisor takes over in-flight items; the round-3
Supervisor goes idle and does not archive itself while implementers still report to it.

## 2026-11-20 ~23:40Z (00:40 CET) — Waiver + third CURRENT (owner, typed directly in the T-155 session)
"I waive the liaison sheet-check condition. Release R3 now: make boy 2.3.0 / girl 0.14.0 /  third 0.1.0 CURRENT, publish
third 0.1.0, update test_face_v4 pins, run all checks, push." (Verified by the Supervisor in the T-155 transcript.) The third
character 0.1.0 becomes her first CURRENT version. Her allowlist entries in `pipeline/charsys/tests/owner_approved_candidates.json`
carry this as their current_decision.

## 2026-11-21 ~00:40Z (01:40 CET) — T-176 whole-project review (relayed by the owner liaison)
New analysis-only task → `docs/tasks/T-176.md`: architecture, workflow, agents, tokens, automation, speed, maintainability,
with evidence from our codebase. Opus 5.5, docs-only write-set `docs/audit/T-176/**`. No changes without owner approval. It
continues under the round-4 Supervisor.

## 2026-11-21 ~04:10Z (05:10 CET) — T-176 proposals 2, 3 and 5 approved (relayed by the owner liaison)
Dispatch as soon as possible, token-efficient pointer briefs, fully tested before merge; write-sets disjoint from T-171/T-175.
- **P2 visual-round budget:** process rule, applied by the Supervisor (`WORKFLOW.md`, `IMPLEMENTER_PROMPT.md`, task template):
  fresh session for a visual round over ~250k context; a short round file per visual task; sheets read as ≤1024 px crops;
  default effort high, max/fast only on owner request.
- **P3 docs-only fast path** → `docs/tasks/T-177.md` (Sonnet): pushes to main/staging touching only `docs/process/**` and
  `docs/tasks/**` run a ~1-min job; promotion accepts an integration commit differing from main only there; decided from
  the changed-path list alone, any other path → full gate; classifier tests incl. mixed pushes.
- **P5 one release rule** → `docs/tasks/T-178.md` (Opus): one release-manifest rule written by `version_switch.py` replaces
  the per-feature "no spec uses X" guards. The owner explicitly approves the required test/safeguard changes ON CONDITION
  that no essential protection or coverage is weakened: byte-immutability of published assets, frozen manifest,
  asset-store guard, goldens and the owner decision ref for CURRENT stay; the manifest is guarded; negative tests (unlisted
  version using an opt-in fails); coverage mapping old guard → new check in the README, reported to the liaison before merge.
- Other T-176 proposals (1, 4, 6–14): not decided.

## 2026-11-21 ~10:45Z (11:45 CET) — T-178 test-change approval typed by the owner (to the liaison)
Verbatim: "I approve changing and removing the per-feature guard tests for T-178, on condition that no essential protection
or coverage is weakened, as recorded in OWNER_DECISIONS 2026-11-21 ~04:10Z." The liaison asked the owner to type it in the
T-178 session too (implementer permission layers refuse relayed approvals).

## 2026-11-21 ~10:55Z (11:55 CET) — T-176 proposal 12 (light) approved; proposal 13 benchmarks only (relayed by the liaison)
- **P12 light, documentation only** → `docs/tasks/T-179.md`: one mapping table generator pin → module file → round name, and
  a short rule that opt-ins become defaults only at the next real look round via the existing pin registry. No new files
  beyond the doc, no renames, no changes to generators, code or approved character versions.
- **P13:** the liaison runs clone benchmarks itself (read-only); no repository structure, history or asset changes.

## 2026-11-21 ~11:10Z (12:10 CET) — T-176 proposal 13: light clone test, then clone profiles (relayed by the liaison)
(1) Run the full suite (`tools/check_all.py` + the gate's Blender units) in a sparse partial clone (depth 1, sparse without
`docs/evaluation/` and `assets/characters/`, fetch on demand) → `docs/tasks/T-180.md`. Liaison benchmark: depth-50 clone 80 s /
~1.85 GB; sparse 4.4 s / ~150 MB; +32 s assets/characters; +14 s docs/evaluation. (2) If all pass: LIGHT and FULL clone profiles
for new sessions via create_session parameters and a one-line dispatch rule; a test task can add paths. No repository history,
structure or asset changes. (3) Then priority on animation production; no further workflow optimisation unless needed.

## 2026-11-21 ~11:20Z (12:20 CET) — T-176 proposals 5, 7, 9 (relayed by the liaison)
- **P5:** complete T-178 preserving all protections, coverage and owner-approval requirements (owner's typed approval in the
  T-178 session still needed).
- **P7:** automatic test registration from per-directory manifests; adding a new test needs no `Supervisor-Approved` trailer;
  changing, renaming or deleting an existing test still needs approval, proven by negative tests; code review and the full CI
  stay. Owner approves the guard-policy change explicitly. Sequenced after T-178 merges (shared test/guard files) → T-182.
- **P9:** one active owner per file, glob-level only, no function-level splits, temporary and transferable (released at
  merge/abandon, handover via the ledger) → `docs/tasks/T-181.md` + rule text in `OWNERSHIP.md`.
- T-178: the owner's approval sentence was also typed in the T-178 session itself at 10:45:54Z (desktop app) and again at
  11:50:19Z; verified by the Supervisor with list_events before the stage-2 merge.

## 2026-11-21 ~12:00Z (13:00 CET) — owner guidance for T-181 / ownership (relayed by the liaison)
The ownership rule must not slow parallel work: claims as narrow as possible; new files need no claim beyond the task
folder; shared append-only registries handled by the Supervisor or merge-friendly formats, not locks; read access never
blocked; claims released at merge/abandon; overlaps reported with the conflicting task, never silently blocking. Gap found:
hard depends-on (read) overlaps were conflicts → T-181b makes them warnings. Rule text in `OWNERSHIP.md` updated.

## 2026-11-21 ~12:30Z (13:30 CET) — owner feedback on T-175, T-171, T-172; hair contact (relayed by the liaison)
- **T-175 locomotion:** walk not bouncier (keep up-down); softer, gentler footsteps; fix feet sinking while walking. Sit
  upright 90° with hands at the sides. Stand-up without the ~90° turn and extra step; fix the boy's legs intersecting.
  Fix black hands (drop hands from the mocap mask) and garment under skin when seated. → fresh session (P2, old one 465k).
- **T-171 hands:** "opt-in + proposed cup site" is the most natural → adopt, close the fingers more around the cup; fix
  fingers bending outward, unclear finger positions, hands not moving properly with the body; include the thumb-down grip
  (e910) and the ~7 mm little-finger graze. T-157(a) stays opt-in. fingerClose and the cup site become defaults only after
  the owner sees the fixed clip. → fresh session (old one 334k).
- **Hair/body contact (new T-183):** girl's hand and hair interpenetrate; hair goes into her ear; hair should follow the
  body and react to body/environment. Not in T-171/T-175 write-sets.
- **T-172:** no 720p re-render; current quality is fine for testing → close and archive.
- T-182: the owner typed the P7 policy sentence in the T-182 session at 2026-11-21T12:17:51Z (desktop app; text without the
  "I approve T-182:" prefix, otherwise verbatim); verified by the Supervisor with list_events before merge.

## 2026-11-21 ~19:20 CET (via the liaison; recorded by the R5 Supervisor)
- **T-171 r3 hands:** owner picks the third column, **thumb up (`r3`)**, as the most natural (not `r3site`). Integrate and
  use it: merge, and make it the variant shots use for the cup pick-up (per-shot keys; no engine default change → no golden
  change). Logged for later: carry / hand-over wrist bend up to 93°, no finger "press" depth yet, planArmLift popping, the
  thumb-up hand is mostly hidden behind the sleeve in e910's camera.
- **T-183 hair contact: NOT accepted.** "The hair still intersects with the body and other areas; it goes inside the body;
  this has not been fixed at all." Do not merge. New round in a fresh session: full hair vs body / garment / arm collision
  (not only hand and ear), with clear before/after close-ups showing zero penetration. Ear look undecided (default keep-out).
- **T-175 r2 walk / sit / stand: accepted**, usable → merge (opt-in for shots).
- **Global floor offset fix: no**, no work for now (T-175 per-shot compensation stays).
- **T-184 seated garments: accepted** → merge as opt-in, usable; do not wait for T-183. Seated thigh-through-panel logged
  for later.
- **P13:** yes, adopt the narrow LIGHT clone rule (code/docs tasks that never run the full suite) → CLONE_PROFILES.md §3.

## 2026-11-21 ~22:45 CET (via the liaison)
- **New T-187 "Paper-boat test scene"** (low-quality test, not for publication): released boy 2.3.0, auburn girl 0.14.0,
  white-haired girl 0.1.0; existing systems only; plain classroom staging; story: seated, the girl with glasses makes a
  paper boat (no finger-folding animation), surprise, she gives it to the boy, all stand and walk; 12–20 s, 4–5 shots,
  640x360 H.264 + contact sheet; known defects listed in the README. Estimate given: ~1–1.5 work days.
- **~23:10 CET: new T-189 "World & environment reuse survey"** (research only, no Codex, docs-only write-set): reuse
  existing CC0/permissive assets, generators, GN kits, datasets, AI-3D for classroom/kindergarten first; build on
  T-170/b/c/d; YouTube commercial use (no NC), headless bpy, deterministic, no paid lock-in without asking; blocked hosts
  listed for owner approval, not worked around.

## 2026-11-22 ~04:20 CET (via the liaison)
- **T-187 paper-boat: accepted** as low-quality test → merge as is. No revised video now: fix the underlying animation
  systems first, improve the video afterwards.
- System fixes (found in T-187), fresh sessions, disjoint write-sets, P2:
  1. Finger/thumb joints bend the wrong way despite T-171 r3 → find why; enforce finger/thumb joint limits everywhere at
     system level, not per shot → T-190.
  2. Hair goes through the table and still into her own body in T-187 → extend T-183 (r2 candidate) to environment/prop
     colliders and make shots use it; handle the fan-out in the same work; zero penetration in real shots → T-183 r3.
     r2 not accepted as final.
  3. Character–character intersections → inter-character collision check + resolution with a per-frame measure → T-191.
  4. Boy's two eyes blink out of sync → bug fix → T-192.
- New research-only task: existing/open-source/paid hair systems vs continuing T-183 (fit to plush ringlet look,
  collision with body/garments/props, headless bpy 5.3, licence, effort) → T-193. Blocked hosts listed for the owner.


## 2026-11-22 ~13:45 CET (via the liaison)
- **Hair contact:** merge the T-183 candidate now, opt-in as built. Main requirement: hair must not penetrate anything
  (body, clothing, props, environment). T-183 r3 continues (neighbour + prop colliders).
- **Hands:** finger/thumb joint bending must be completely fixed (T-190: thumbs included, all characters, all grasps and
  poses). Before/after + golden list for owner OK as planned.
- **Blink:** probably video quality → no further blink work. Eye-convergence limits not dispatched (optional, low
  priority follow-up).
- **Guidance:** use Blender and our own engine as much as possible (Blender built-ins / our engine over external tools).
- **T-193 hybrid hair: approved.** First a short analysis of which of our animation problems it solves (and which not),
  then implement; priority zero penetration into body/garments/props/environment. Coordinate with T-183 r3 (one owner
  per file). No paid tools. Do NOT change the test scene (e912) now: fix the underlying systems first. Hair resting on
  props without sliding is fine for now (T-193 Q2).
- **Sound: start now.** Emotional vocal sounds (surprise gasp/"oh!", happy "wow", small laugh, ...) attached to acting
  cues; licence-safe for YouTube (CC0 or own/permissive), no paid services; build the system + a small sound library;
  demo by muxing audio onto a COPY of the existing T-187 video (no re-render, no scene change). Separate task,
  disjoint write-set.
- **T-189 world:** Q2 yes (CC0 geometry + our materials = ready-made). Q3 (liaison): plain git, small .glb per set +
  SOURCES.json with hashes, no LFS. Q4 (liaison): voluntary credits line in video descriptions + keep SOURCES.json.
  Q5: no water for now. Q6: no paid AI-3D. Q1 (Kenney/Quaternius/itch hosts) and Q7 (Infinigen): on hold (owner being
  briefed). World plan stays on hold.
- T-191 staging asks (enable body clearance in e912; wider seats / lower hand-over point): parked by "do not change e912
  now".

## 2026-11-22 ~14:05 CET (via the liaison)
- **T-189 Q1 approved:** the environment allows kenney.nl, www.kenney.nl, quaternius.com, www.quaternius.com, itch.io.
  itch.io downloads use a separate CDN host: whoever tests it reports the exact host(s) to the liaison. Standing owner OK:
  other useful, licence-safe sites may be investigated; hosts are listed to the liaison, who adds them.
- **T-189 Q7:** Infinigen may be used if needed (isolated, licence-checked).
- **World plan:** all questions answered; still not started (priority = system fixes); the liaison relays the start.
- **New T-196 research (docs only, docs/audit/T-196/**):** Blender-first / hybrid architecture review: useful existing
  tools/resources, right development approach?, use Blender more instead of building ourselves (per area), hybrid
  across more parts; per-area map current vs Blender/hybrid (quality, effort saved, risks incl. determinism, headless,
  goldens, TD-43, migration); ranked recommendations + verdict. Builds on T-174/T-176/T-189/T-193. No changes.

## 2026-11-22 ~14:40 CET (via the liaison)
- T-195 final voices: on hold (the placeholder demo stays as is).
- T-190: the hand improvements are to be merged, further improvement later; default ON/OFF and the 33°/45° box-face
  lay-back are not decided yet (the liaison explains) → no merge until both answers are relayed.
- Motion-continuity guard and the T-196 follow-ups: not approved yet; no action until relayed.

## 2026-11-22 ~15:10 CET (via the liaison; final)
1. **T-190 approved:** default ON (finger/thumb limits for all existing and future animation); 45° lay-back for flat-hand
   box-face grips only, wrap grips keep 33°. Update ONLY the 6 identified interaction goldens (thumb corrections only)
   and rewrite ONLY the 8 identified test criteria that demanded physically impossible thumbs. No unrelated goldens,
   character features or behaviours may change; no test weakened, removed or bypassed; rewritten tests keep or improve
   guarantees. Merge once these hold and all tests pass.
2. **Motion Continuity Guard approved, after T-190:** detect and correct unnatural frame-to-frame jumps in hand targets,
   head rotation and gaze; keep intentional fast moves and camera cuts; do not change intended acting; per-frame
   speed-limit test.
3. **T-196 follow-ups:** approved Q1 (per-shot real-geometry collision audit), Q2 (compositor look preset; before/after
   for owner approval before applying), Q4 (lighting setups in Blender set files), L1 (garment–body collision +
   cloth-sim evaluation for loose pieces), L2 (corrective shape keys at strong bends, AFTER the next character release).
   Q3 (EEVEE preview evaluation) is assigned to Codex as T-197 on the owner's PC — not dispatched by the Supervisor.
   L3 not approved. Sensible order, dependencies respected, one owner per file.
4. **Voices:** on hold (no final voice selection/implementation).
- General: prefer Blender built-ins + our engine + suitable open source; no unnecessary rebuilds; keep approved designs
  and behaviours; never compromise tests or quality; fix system-level problems, not per-scene patches.
- Task IDs: T-197 is Codex's; Supervisor IDs continue at T-198.

## 2026-11-22 ~15:20 CET (via the liaison) — standing rule
- **No Fable model for any task from now on** (token cost). New dispatches: Opus 5.5 by default, Sonnet 5.5 for
  mechanical / aggregation work. Running Fable sessions (T-183 colliders, T-194 push-out) reach their next checkpoint,
  then further rounds continue in a fresh Opus session (branch + round file; no work lost). T-190 round 2, started on
  Fable at ~13:48Z, was restarted on Opus at once (session_01NPjxeMs1WeEkn4EHp9scQE).

## 2026-11-22 ~17:15 CET (via the liaison)
- **EEVEE preview profile approved** ("speed is important for testing/reviewing previews"): opt-in `preview_eevee`
  render profile for blocking/acting reviews, added after T-199 merges (T-201); Cycles stays for look review and finals.
  Check whether EEVEE renders headless in a GPU-less cloud session; if not, the profile is for the owner's PC (T-200).
- **New Codex task T-200** (relay channel): diagnose the WinError 4551 bake block on the owner's PC (no security-setting
  changes) and finish T-197's motion checks (walk, hand-over, flicker) if a safe route works. Supervisor IDs from T-201.
- T-190 finger detail (accept the 0.3–0.5° clip hyperextension correction or exempt clip fingers): still open.
- **~17:25 CET:** T-190 finger detail → (a) accept (clip hyperextension corrected by the finger limit, 0.04–0.07 mm);
  merge T-190 once all tests pass. **Standing guidance:** hands/fingers must not consume more discussion tokens — for
  sub-mm / sub-degree side effects within an approved scope the Supervisor decides (anatomically correct option, no
  weakening), records it, and does not escalate. Escalate only real look changes or test/golden changes outside an
  approved scope.

## 2026-11-22 ~18:20 CET (via the liaison)
1. **Windows block (T-200): build/bake in the cloud, render on the PC** (or another route that does not touch the owner's
   security settings). Small task T-205: a reproducible "bake package" for a shot (bake.json + manifests + what Blender
   needs, no engine exe) produced in cloud/CI and fetchable on the PC (branch or CI artifact), plus a one-command PC
   render script for the opt-in preview_eevee profile (after T-199 / T-201). Codex uses it later for e912 EEVEE checks.
2. **Codex T-204** (relay): face reference targets for all three characters (targets.json + measures + re-runnable
   script). Supervisor IDs from T-205.
3. **New research T-206 (Opus, docs only, docs/evaluation/characters/T-206/**):** (a) faces — open-source tools /
   libraries / Blender capabilities to match the reference images more accurately and faster (landmark-driven fitting
   of shape keys / face params, differentiable rendering with licences, Blender add-ons incl. paid only for comparison,
   sculpt/shape-key workflows, reference camera matching, auto-compare metrics) and what fits our procedural faces;
   (b) wool hair — wool/felt-yarn texture with less volume (hair curves + GN hair node groups, Principled Hair BSDF /
   fibre shaders, yarn/wool/felt shading, open-source generators). Quality fit, determinism/headless bpy 5.3, licence,
   effort; small feasibility renders welcome; recommendation + plan. Face work itself waits for T-206 + T-204 + owner.

## 2026-11-22 ~19:10 CET (via the liaison) — T-206 answers
1. Faces: fit existing spec values first; new face parameters only if review shows they are needed.
2. Views: ALL angles matter (front, 3/4, side, and back where the face/hair silhouette shows) — equal weights in the
   fit and in review sheets.
3. Hair volume: reasonable and natural, close to the references.
4. Hair texture: the reference hair reads as VELVETY / FLOCKED (short dense soft fibres, velvet-like sheen), not long
   combed yarn. The hair step targets a velvet/flocked look: flock/velvet options (short dense fuzz, sheen/velvet
   shading, Blender hair-curve node groups as needed) side by side with T-206 probe D and the references; the owner
   picks from the sheet. D is not locked.
5. Hair + face bundling per character: not a priority — ship what is ready independently (each needs owner approval).
6. **Standing guidance:** our engine works closely with Blender across ALL areas, making full use of Blender's
   capabilities and suitable open-source tools/libraries wherever possible.
- Start hair step H1 now (opt-in, Opus; contact checks after T-183/T-194 merge) → T-207. Face fit after Codex T-204.
- **Supervisor decision (T-198, within the approved Motion Continuity scope, ~19:45 CET):** re-record
  test_interaction/visibleGrip/boy (the fix removes a 147° one-frame hand flip; frames 11-14, hand.R + its finger/DEF
  bones only; all 6 content goldens unchanged). Speed-limit test as a ratchet over a recorded baseline (e901 f223 walk
  start + listed grasp/release finger-curl rows); fixing those curls → follow-up T-209.

## 2026-11-22 ~20:05 CET (via the liaison)
- **New research T-209 (Opus, docs/research/T-209/**, no implementation, no CURRENT change):** the most reliable approach
  for highly accurate, consistent, animation-ready stylized faces for the 3 velvety/flocked characters in Blender,
  covering the owner's 10 points (parametric generator; matching the refs; independent geometry controls; eye system +
  blinking; identity-preserving shape keys; face rig; Python/GN automation; identity preservation over animation;
  automated front/3-4 validation with landmarks + similarity metrics; production integration with free tools only, GPU
  needs, pipeline fit). Build on T-202, T-204, T-206, T-196, T-207; all angles matter. REPORT.md: comparison per point,
  one recommendation with phases + token/session cost, risks, owner decisions. The T-198 finger-curl follow-up moves
  from T-209 to T-210.

## 2026-11-22 ~20:35 CET (via the liaison)
- **New research T-211 (Opus, docs/research/T-211/**, no implementation):** the 10 T-209 face points from Blender's
  perspective — built-in Blender 5.3 features (+ bundled/free extensions) per point, checked headless where possible;
  built-in way vs our own code, duplicates to replace, real gaps, effort/risk; revised "Blender-first fit-and-lock"
  vs T-209 with savings. (Requested as T-210; T-210 was already the T-198 finger-curl follow-up, dispatched ~19:31Z.)

## 2026-11-22 ~21:40 CET (via the liaison)
- **New Codex task T-212 (relay, research only, docs/research/T-212/**, branch t-212-codex-face-plan-review):**
  independent review of the T-211 Blender-first face plan (quality, efficiency, maintainability, alternatives, risks,
  Codex's own recommendation); queued after T-208. The face decisions (T-209 D 1–5 + T-211 decision 7) stay open until
  the owner has seen Codex's view. Supervisor IDs from T-213.

## 2026-11-22 ~22:40 CET (via the liaison)
- **Face plan approved** (verbatim: "approve the face plan with Codex's changes, pilot auburn first"): T-209 D1
  fit-and-lock on our own generator (face_generic/4 if needed); D3 pass rule = every scored T-204 measure within
  tolerance + owner sheet review; D7 in T-212's amended form (spec controls first, Warp/Hook/Lattice only for leftover
  contour errors; bake on neutral skin before rig/masks, rebuild lid keys; regenerate lids, seat glasses rigidly, no
  Surface Deform; acceptance adds a held-out reference view + exported-expression parity with Blender; pin the Blender
  build). Order: **auburn pilot first**, then white-haired, then boy. Defaults kept: D2 view weights equal; D4 smiling
  refs scored against a matched smile expression; D6 face and hair ship independently. Standing: no CURRENT change
  without the owner's OK; every new character version needs the owner's sheet approval; P2 budget per session. The
  liaison wants the auburn pilot sheet (all angles, before/after/reference) when ready.

## 2026-11-23 ~06:55 CET (via the liaison; owner: "With All four open decisions i agree")
- **T-194 hair push-out:** `static_move_fade` ON stays the default (no pops; auburn nape cap left inside, hidden from
  the shot camera). The rate-limited push-out follow-up is NOT started; optional, only on the owner's request.
- **Auburn face: GO for P3** (Warp/Hook/Lattice for outline and chin on the T-215 stuck list), then a combined sheet
  before any release decision.
- Hair look (T-207) and compositor look (T-199) picks: the liaison confirms them with the owner separately.
