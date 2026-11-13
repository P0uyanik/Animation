# Bugs and known issues

| ID | Severity | Area | Issue | Next action |
| --- | --- | --- | --- | --- |
| BUGS-01 | Medium | Look | Hair cap still reads slightly like a beanie/helmet; bow reads as three blue beads | Shape pass in Character workspace; ribbon-like bow primitives |
| BUGS-02 | Medium | Look | Mouth is a tiny groove; no eyebrows or eyelid blink yet | Face features pass (lip line texture, lid primitives, blink key) |
| BUGS-03 | Low | Data | Saving a character from Studio writes mirrored primitives explicitly (mirror flags lost) | Keep authored (unexpanded) parts in the asset and expand only for building |
| BUGS-04 | Fixed | Perf | Full-quality evaluator built the character twice on first in-app render | Fixed: rebuild only after in-app edits |
| BUGS-05 | Low | Look | Rug colours read pale; colored fibres over a textured base do not take the texture colour | Fibres sample the base texture at their root |
| BUGS-06 | Medium | Render | Frame time grows with fibres (~1.6M fibres ~30 s/frame at 640x360x32spp on 4 cores) | Camera-aware fibre culling and LOD; adaptive sampling |
| BUGS-07 | Low | Render | Milestone video (32 spp, denoiseBlend 0.85) shows mild grain but no strong fibre flicker | Re-check at final quality; optional temporal blending |
| BUGS-08 | Low | Studio | Screenshot test captures the frame before the last render update | Test-only; harmless |
| BUGS-09 | Info | Process | Cloud workspace is ephemeral and no GitHub remote is configured | Attach a private GitHub repository so every commit is pushed |
| BUGS-11 | Low | Look | Reaching arm bends stiffly at the elbow (linear blend skinning, no IK) | IK + dual-quaternion skinning in the animation pass |
| BUGS-10 | Info | Platform | Windows build not verified | Build with vcpkg on your machine |
