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
