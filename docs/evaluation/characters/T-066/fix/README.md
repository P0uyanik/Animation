# T-066 follow-up: dark speckles on the girl's cheeks (under the glasses)

Branch `t-066-claude-skin-fix` from `c7c9d86`. Result: **BLOCKED**. The cause is the cheek geometry, not the skin
family, so it cannot be fixed inside T-066's write-set. No material change is committed: both skin-side experiments
left the speckles unchanged and are reverted, so the approved skin look is exactly as merged.

## Cause
- The speckles sit in the same places on both cheeks just below the glasses rims. The approved 0.10.0 render shows
  **light** flecks there and the candidate shows **dark** ones (`cheek_speckles.jpg`, columns 1 and 2).
- Ray casts from the close-up camera through the speckle pixels hit `body_skin` itself, at y ~ -0.098 m. No lid shell
  or glasses mesh is in front at those pixels (only along the top row, inside the rims).
- At those points the surface normal jumps between neighbouring pixels: (-0.24, -0.90, -0.37) at pixel (203, 528)
  against (-0.29, -0.64, -0.71) at (204, 531). The `body_skin` edges in that window have dihedral angles of **75-124°**
  at exactly the speckle positions (e.g. 92° at px 203/527, 124° at 204/530, 79° at 218/538, 57° at 213/550). These
  are sharp folds in the sculpted cheek/under-eye surface.
- The approved 0.10.0 mesh has the same hits and normals. The folds were already there; the old skin hid them, and
  the matte skin-felt/2 reveals them. Before, the emissive felt "light bleed" (driven by occlusion) and the glossier
  presets/1 skin turned them into light flecks; the matte, non-emissive skin shows them as small dark triangles.

## Skin-side attempts (both reverted; 4 Cycles stills, budget 4)
| Render | Change | Speckles |
| --- | --- | --- |
| f1 (front + 3/4) | every AO node in the skin material object-local (`only_local`), so lid and glasses shells don't count | unchanged; the blush also turned redder (look change) |
| f2 (front + 3/4) | only the crease AO local; skin-felt/2 subsurface scale 0.05 -> 0.02 x reference (~6 mm) | unchanged |

Neither changed the dark triangles, which fits a cause in the geometry's shading normals rather than occlusion or
scattering depth. Hiding them with emission or extra gloss would bring back the glow and sheen the owner approved
removing.

## What would fix it (outside T-066's write-set; needs a Supervisor decision)
Smooth or remove the sharp folds in the girl's cheek/under-eye surface, in the face/head shaping (`face_generic` /
`face_features` head shape or the cheek-ledge sculpt, recently touched by T-065's "eye behind cheek ledge" fix). Check
it with a dihedral-angle check on `body_skin` in the under-eye window (no edge above ~20° there) and a front close-up.
After that the matte skin renders the cheeks clean without any skin change. The boy is not affected (separate legacy
head mesh, no speckles in his sheet).
