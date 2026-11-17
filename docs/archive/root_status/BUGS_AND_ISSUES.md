# Bugs and known issues

| ID | Severity | Area | Issue | Next action |
| --- | --- | --- | --- | --- |
| BUGS-01 | Low | Look | Hat-like hair: iteration 4 replaced cap brims with felted clump volumes and a hair mass; A's long side locks still read as thick cords next to the reference's thin wavy locks | Thinner, wavier side locks with more halo; awaiting your review |
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
| BUGS-15 | Fixed | Look | Skin had no subsurface scattering | Iteration 4: random-walk SSS (TD-29) |
| BUGS-16 | Low | Look | Glasses lenses reflect the cool fill light as a blue band over B's brows | Light linking or a warmer fill |
| BUGS-17 | Medium | Edit | Mirrored lock groups are expanded on load; editing one side does not update the other | Keep authored groups and expand only for building (same as BUGS-03) |
| BUGS-18 | Medium | Edit | Hair editing is numeric (control points as numbers); no drawing on the head in the viewport yet | Viewport picking + drag gizmos |
| BUGS-19 | Low | Anim | Paper fold is a staged blend; the boat snaps a few mm when released onto the water | Ease the release height; contact constraint |
| BUGS-20 | Low | Look | Garment detail: iteration 4 added B's vest felt motifs and ribbed cuffs/hems (A, C); still missing: A's skirt relief pattern, seams, pocket flaps and buttons on B's pockets | Pattern layers per garment region |
| BUGS-21 | Medium | Anim | A mouth can only open where a pocket is baked into the face (all three have one); opening a mouth from a closed surface with a morph crumples (tried, rejected) | Keep baked pockets; for new characters add a closed pocket by default (as C) |
| BUGS-22 | Medium | Anim | No collision between bodies and furniture: an arm can pass over/through a table rim, feet are not tested against props | Simple capsule-vs-box checks in reach/touch planning |
| BUGS-23 | Low | Camera | Director's occlusion check only considers characters (not props); shot rules are fixed | Ray tests against the scene for camera placement |
| BUGS-24 | Low | Anim | Chibi arms are ~0.21 m long: reach/touch targets must be close; actions lean the body and warn when still out of reach | Step closer automatically (walk + reach) |
| BUGS-25 | Low | Perf | Character build time grew (A 9–12 s, B 7–9 s, C 13–25 s with load) because of felted clump volumes and denser hair | Cache built characters on disk |
| BUGS-26 | Info | Look | A's brows sit hidden under the fringe (as in the reference), so brow motion is not visible on A | By design; brows visible on B and C |
| BUGS-27 | Low | Look | In the touch insert the index fingertip is partly hidden behind the hand from the director's camera angle | Director: choose the side view for touch inserts |
| BUGS-10 | Info | Platform | Windows build not verified | Build with vcpkg on your machine |
