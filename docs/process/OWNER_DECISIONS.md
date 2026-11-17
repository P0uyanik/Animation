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
