# Bugs and known issues

| ID | Severity | Area | Issue | Next action |
| --- | --- | --- | --- | --- |
| BUGS-01 | Medium | Look | Iteration 2: hair cap clumpier with strand relief and a scalloped fringe, but the overall silhouette still reads partly as a hat; bow still reads as blue beads | Guide-curve clump tool; ribbon primitive for the bow |
| BUGS-02 | Fixed | Look | Mouth/brows/blink missing | Iteration 2: measured-surface mouth groove, smile/open morphs, brows, eyelid blink |
| BUGS-12 | Low | Look | Brows sit very close under the fringe; no eyelashes; closed lids look flat | Lash line fibres, lid crease |
| BUGS-13 | Low | Look | Yarn locks looked like plastic sheets in close-ups | Improved: matte felt cores; next: guide-curve lock tool, per-lock colour variation |
| BUGS-14 | Low | Render | Adaptive sampling only gives ~11% on this scene (noise is everywhere: GI, DOF, fibres) | Better light sampling (light tree), path guiding later |
| BUGS-03 | Low | Data | Saving a character from Studio writes mirrored primitives explicitly (mirror flags lost) | Keep authored (unexpanded) parts in the asset and expand only for building |
| BUGS-04 | Fixed | Perf | Full-quality evaluator built the character twice on first in-app render | Fixed: rebuild only after in-app edits |
| BUGS-05 | Low | Look | Rug colours read pale; colored fibres over a textured base do not take the texture colour | Fibres sample the base texture at their root |
| BUGS-06 | Medium | Render | Frame time grows with fibres (~1.6M fibres ~30 s/frame at 640x360x32spp on 4 cores) | Camera-aware fibre culling and LOD; adaptive sampling |
| BUGS-07 | Low | Render | Milestone video (32 spp, denoiseBlend 0.85) shows mild grain but no strong fibre flicker | Re-check at final quality; optional temporal blending |
| BUGS-08 | Low | Studio | Screenshot test captures the frame before the last render update | Test-only; harmless |
| BUGS-09 | Info | Process | Cloud workspace is ephemeral and no GitHub remote is configured | Attach a private GitHub repository so every commit is pushed |
| BUGS-11 | Fixed | Look | Reaching arm bent stiffly | Iteration 2: two-bone IK + dual-quaternion skinning + weight smoothing |
| BUGS-15 | Medium | Look | Skin has no subsurface scattering yet (doll skin still slightly matte/plastic in close-ups) | Random-walk SSS in the path tracer |
| BUGS-16 | Low | Look | Glasses lenses reflect the cool fill light as a blue band over B's brows | Light linking or a warmer fill |
| BUGS-17 | Medium | Edit | Mirrored lock groups are expanded on load; editing one side does not update the other | Keep authored groups and expand only for building (same as BUGS-03) |
| BUGS-18 | Medium | Edit | Hair editing is numeric (control points as numbers); no drawing on the head in the viewport yet | Viewport picking + drag gizmos |
| BUGS-19 | Low | Anim | Paper fold is a staged blend; the boat snaps a few mm when released onto the water | Ease the release height; contact constraint |
| BUGS-20 | Low | Look | Garment motifs (vest embroidery, skirt pattern) and seams are not modelled yet | Decal/pattern layers |
| BUGS-10 | Info | Platform | Windows build not verified | Build with vcpkg on your machine |
