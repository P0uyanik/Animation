# Feature status

Legend: **Implemented** (works and tested) · **Experimental** (works, limited or lightly tested) ·
**Planned** · **Placeholder** (UI or data exists, behaviour incomplete). "Tested" means what is in the Evidence column.

| Area | Feature | Status | Evidence |
| --- | --- | --- | --- |
| Core | Errors, logging, thread pool, files, time ticks | Implemented | unit tests |
| Modeling | SDF primitives, smooth union/subtract, mirror | Implemented | unit tests (closed mesh, area) |
| Modeling | Surface-nets mesher with surface projection | Implemented | unit tests, renders |
| Modeling | Brick culling in the mesher (8³ bricks, near-primitive lists) | Implemented | unit test vs exhaustive evaluation |
| Modeling | Exact disc primitive | Implemented | glasses lenses render clear |
| Modeling | Lumpy noise displacement | Experimental | renders |
| Modeling | Geometric relief: strands, knit, ribbed | Implemented | renders |
| Modeling | Add/remove primitives in the app | Planned | |
| Modeling | Polygon mesh editing, sculpting | Planned | |
| Character | Character asset (skeleton, parts, fuzz, locks, materials) JSON | Implemented | loads/renders |
| Character | Edit primitive shapes + rebuild in Studio | Experimental | built, not click-tested by a person |
| Character | Save character from Studio | Experimental | writes expanded file (BUGS-03) |
| Rigging | Automatic skin weights from primitives | Implemented | unit test |
| Rigging | Linear blend skinning, FK | Implemented | unit test, animation renders |
| Rigging | Two-bone IK, eye look-at, attach objects to bones | Implemented | unit tests (IK reach, aim), milestone 02 |
| Rigging | Articulated fingers: curl/thumb/spread/point, contact grasp (sphere, cylinder) | Implemented | unit test (fist, point, grasp adapts to size), hand-pose test scene |
| Rigging | Dual-quaternion skinning, skin-weight smoothing | Implemented | unit test (DQ = linear for rigid), renders |
| Animation | Tracks with smooth/linear/step keys | Implemented | unit tests |
| Animation | Set/delete keys in Studio, timeline markers, playback | Experimental | screenshot test |
| Animation | Expressions as morph targets (smile, frown, surprise, mouthClose), blink lids, brows | Implemented | unit test, expression sheets A/B/C (iteration 4) |
| Animation | Morph relaxation after projection (no crumpling) | Implemented | expression sheets; tried/rejected variants logged |
| Animation | Life layer: breathing, weight shift, head drift, automatic blinks, head follows gaze with lag | Implemented | unit tests (blink count/determinism, chest motion, head lag); v4 animation |
| Animation | Actions: look, expression, reach (grip, lift, place, release, lean), touch, walk | Implemented | unit tests (reach, touch ≤ 6 mm, walk: no skating); v4 animation |
| Animation | Automatic camera director (shot plan from actions, focus, push-in, occlusion check vs characters) | Experimental | v4 animation shot list; no unit test; occlusion ignores props |
| Animation | Walking | Experimental | straight paths on flat floors only; unit test (planted feet) |
| Animation | Dope sheet, curve editor, pose library | Planned | |
| Hair/fuzz | Surface fuzz with stray fibres | Implemented | unit test (outward), renders |
| Hair/fuzz | Yarn locks (felt core tube + twisted fibres) | Experimental | renders, close-ups |
| Hair/fuzz | Explicit lock curves: taper, curl, felt core, fibre halo; lock groups per bone | Implemented | unit test, renders of 3 hairstyles |
| Hair/fuzz | Hair-lock editor in Studio (points, thickness, curl, add/duplicate/delete, apply, save) | Implemented | scripted edit test + screenshot; not click-tested by a person |
| Hair/fuzz | Felted clump volumes (fringes, crowns, spiky clumps) and hair-mass volume under locks | Implemented | head close-ups, comparisons with references |
| Hair/fuzz | Spring-bone secondary motion | Planned | |
| Rendering | CPU path tracer (Embree), MIS, sun/rect/sky lights | Implemented | unit tests, renders |
| Rendering | Standard / plush / fiber materials | Implemented | energy + pdf unit tests |
| Rendering | Procedural textures (noise, knit, wood, wall, iris, blush) | Implemented | renders |
| Rendering | Thin-lens depth of field, aperture blades | Implemented | renders |
| Rendering | Owen-scrambled Sobol sampling | Implemented | measured error vs 1024-spp reference |
| Rendering | Fibre level of detail | Implemented | measured: 5.7x fewer segments, RMSE 0.007 |
| Rendering | Adaptive sampling | Experimental | measured −11% at threshold 0.1 on milestone 02 |
| Rendering | Denoising (OIDN) with fibre-aware guide | Implemented | renders |
| Rendering | AgX-style filmic tone mapping | Implemented | renders |
| Rendering | Glass (thin lenses) and water (refraction), shadow-free option | Implemented | unit test, renders |
| Rendering | Subsurface scattering (random walk) for skin | Implemented | furnace unit test; face close-up before/after |
| Rendering | Motion blur, EXR output | Planned | |
| Rendering | GPU path tracing backend | Planned (optional) | |
| Studio | Window, docking UI, OpenGL preview viewport with texture colours | Implemented | screenshot test (software GL) |
| Studio | Outliner, inspector (objects, lights, camera, materials) | Experimental | screenshot test |
| Studio | In-app progressive path tracing + save image | Implemented | screenshot test |
| Studio | Render animation to video from the app | Experimental | code path uses plush-render; CLI tested |
| Studio | Viewport shows curves (hair, frames, straps) as tubes | Implemented | screenshot |
| Studio | Save, close and reopen a project with edits | Implemented | automated round trip (lock count + keyframe survive) |
| Studio | Undo/redo, transform gizmos, viewport picking, new project | Planned | |
| Scene | Rippling water surface, floating objects, staged paper fold | Implemented | milestone 03 renders |
| Scene | Ripples generated by actions (lift-off, placing, fingertip touch); objects stop floating while held | Implemented | v4 animation |
| Scene | 30 fps default for new scenes | Implemented | iteration-3 scenes keep explicit 24 fps |
| Integration | External assistant (e.g. ChatGPT) controlling the app | Planned | not implemented; actions JSON is the intended target |
| Character | Three reference characters (kit script), default pose/expressions, lashes, glasses | Implemented | lineup, close-ups |
| Character | Iteration-4 reconstruction (faces, felted hair, garment silhouettes, baked mouths with teeth/tongue, ribbed bands, vest motifs) | Implemented, awaiting your approval | `docs/iteration4/compare_*`, `renders/it4/` |
| Character | Character creation UI (new character from scratch in the app) | Planned | kit is a script today |
| Physics | Rigid bodies (Jolt), interactions | Planned | |
| Export | Frame sequences + resume + H.264 video | Implemented | milestone animation |
| Export | Audio, ProRes master | Planned | |
| Testing | Look regression (milestone 01, neutral face v2, A/B/C lineup) | Implemented | CTest (lineup re-baselined in iteration 4, logged) |
| Platform | Linux build | Implemented | CI-less local build |
| Platform | Windows build | Placeholder | vcpkg.json written, not built yet |
