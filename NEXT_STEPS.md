# Next steps

**Exact next task:** Iteration 4 — (1) skin subsurface scattering, (2) viewport picking + drag gizmos so hair locks
and props are edited by dragging instead of numbers, (3) keep authored (unexpanded) mirror data in assets
(BUGS-03/17), (4) garment motifs and seams, (5) new-character-from-template UI. Check `docs/ITERATION_03_ACCEPTANCE_REPORT.md` first.

## Resume checklist (every session)
1. Read `PROJECT_STATE.md`, this file, `BUGS_AND_ISSUES.md`.
2. `git status` / `git log --oneline | head`.
3. Build: `cmake -S . -B build -G Ninja -DPLUSH_OIDN_ROOT=<oidn> && cmake --build build -j3`.
4. Test: `./build/tests/plush_tests` (expect all passing).
5. Smoke render: `./build/apps/render-cli/plush-render content/scenes/milestone01_classroom.scene.json --frame 1 --out renders/smoke.png --width 480 --height 270 --spp 16 --preview`.
6. Continue with the exact next task above.

## Plan to the first usable release (v0.1), in order
Each item is roughly one to three working sessions.

1. **Editing core:** undo/redo, viewport picking, move/rotate/scale gizmos, duplicate/delete, autosave.
2. **Project manager:** new project/scene from templates, asset library panel (characters, props, materials, light rigs), save-as.
3. **Character workspace:** add/remove/mirror primitives, proportion sliders, face features (lids, blink, brows, mouth shapes), hairstyle presets (buns, locks, bangs), outfit parts; fix BUGS-01/02/03.
4. **Modeling for sets and props:** primitive kits (box, cylinder, rounded shapes), SDF booleans in the UI, simple polygon edits for hard props.
5. **Animation workspace:** dope sheet, curve editor, copy/paste keys, pose library, two-bone IK, look-at, parent-switch constraint for picking up objects.
6. **Interaction & physics:** Jolt rigid bodies baked to keys; attach/detach; simple water-table ripples.
7. **Look quality:** skin subsurface scattering, motion blur, spring bones for hair/buns, fibre LOD and camera culling, light linking, EXR output.
8. **Lighting & camera:** light rigs, camera rigs/paths, focus picking, shot list.
9. **Export:** render queue in the app, audio tracks, ProRes/H.264 export, quality presets.
10. **Windows build** on your computer and hardware-specific tuning (thread count, fibre budgets).
