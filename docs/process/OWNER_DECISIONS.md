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

## 2026-11-15: permanent workflow rules (supersede conflicting earlier wording)
1. Every sub-agent (Codex, Antigravity, Claude Implementer) works on its own task branch and worktree and pushes
   its completed work to GitHub. Sub-agents never merge into `main`.
2. The Supervisor independently reviews and tests every branch, checks and resolves conflicts, and merges all
   verified changes (merges and pushes to `main` with owner approval).
3. Reliable two-way communication between the Supervisor and the local Claude relay session is mandatory:
   Supervisor -> relay by session message; relay -> Supervisor by comments (or pushes) on the never-merged relay PR
   P0uyanik/Animation#2 (branch `relay-channel`), which wake the Supervisor. Fallback: the Supervisor reads the
   relay's transcript. If the channel fails, the Supervisor investigates and repairs it.
