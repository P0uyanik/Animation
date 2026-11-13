# Feature status

Legend: **Implemented** (works and tested) · **Experimental** (works, limited or lightly tested) ·
**Planned** · **Placeholder** (UI or data exists, behaviour incomplete). "Tested" means what is in the Evidence column.

| Area | Feature | Status | Evidence |
| --- | --- | --- | --- |
| Core | Errors, logging, thread pool, files, time ticks | Implemented | unit tests |
| Modeling | SDF primitives, smooth union/subtract, mirror | Implemented | unit tests (closed mesh, area) |
| Modeling | Surface-nets mesher with surface projection | Implemented | unit tests, renders |
| Modeling | Lumpy noise displacement | Experimental | renders |
| Modeling | Add/remove primitives in the app | Planned | |
| Modeling | Polygon mesh editing, sculpting | Planned | |
| Character | Character asset (skeleton, parts, fuzz, locks, materials) JSON | Implemented | loads/renders |
| Character | Edit primitive shapes + rebuild in Studio | Experimental | built, not click-tested by a person |
| Character | Save character from Studio | Experimental | writes expanded file (BUGS-03) |
| Rigging | Automatic skin weights from primitives | Implemented | unit test |
| Rigging | Linear blend skinning, FK | Implemented | unit test, animation renders |
| Rigging | IK, constraints, parent switching | Planned | |
| Animation | Tracks with smooth/linear/step keys | Implemented | unit tests |
| Animation | Set/delete keys in Studio, timeline markers, playback | Experimental | screenshot test |
| Animation | Dope sheet, curve editor, pose library | Planned | |
| Hair/fuzz | Surface fuzz with stray fibres | Implemented | unit test (outward), renders |
| Hair/fuzz | Yarn locks (core + twisted fibres) | Experimental | renders |
| Hair/fuzz | Spring-bone secondary motion | Planned | |
| Rendering | CPU path tracer (Embree), MIS, sun/rect/sky lights | Implemented | unit tests, renders |
| Rendering | Standard / plush / fiber materials | Implemented | energy + pdf unit tests |
| Rendering | Procedural textures (noise, knit, wood, wall, iris, blush) | Implemented | renders |
| Rendering | Thin-lens depth of field, aperture blades | Implemented | renders |
| Rendering | Denoising (OIDN) with fibre-aware guide | Implemented | renders |
| Rendering | AgX-style filmic tone mapping | Implemented | renders |
| Rendering | Subsurface scattering (skin), motion blur, EXR output | Planned | |
| Rendering | GPU path tracing backend | Planned (optional) | |
| Studio | Window, docking UI, OpenGL preview viewport with texture colours | Implemented | screenshot test (software GL) |
| Studio | Outliner, inspector (objects, lights, camera, materials) | Experimental | screenshot test |
| Studio | In-app progressive path tracing + save image | Implemented | screenshot test |
| Studio | Render animation to video from the app | Experimental | code path uses plush-render; CLI tested |
| Studio | Undo/redo, transform gizmos, viewport picking, new project | Planned | |
| Physics | Rigid bodies (Jolt), interactions | Planned | |
| Export | Frame sequences + resume + H.264 video | Implemented | milestone animation |
| Export | Audio, ProRes master | Planned | |
| Platform | Linux build | Implemented | CI-less local build |
| Platform | Windows build | Placeholder | vcpkg.json written, not built yet |
