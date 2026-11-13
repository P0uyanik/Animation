# Next steps

**Exact next task:** review the automated pilot (`docs/evaluation/boy_pilot/PILOT_REPORT.md`). Proposed next step:
make the pilot run on the user's own Blender, from a Claude session on the user's computer or by running the
commands in the report's §8. This verifies the version, headless mode and Python access, then reproduces v6 there.
Then improve the hair silhouette (the largest identity gap).
- No full integration, no other characters, no iteration 5.

## After your review (candidates, to be agreed)
1. Character corrections you request (approval checkpoint for A, B, C).
2. Collision-aware reach/touch (arm vs table rim) and "step closer, then reach" (BUGS-22, BUGS-24).
3. Director: side views for touch inserts, ray-tested camera placement against props (BUGS-23, BUGS-27).
4. Editing: viewport picking + drag gizmos for locks/props, undo/redo, keep authored mirror data (BUGS-03/17/18).
5. Garment detail: skirt relief pattern, seams, pocket flaps (BUGS-20).
6. Cache built characters on disk (BUGS-25); build and measure on your own computer (Windows, vcpkg).
7. An assistant-facing command interface (validated JSON actions over a local socket or file drop) — only if you want it.

## Resume checklist (every session)
1. Read `PROJECT_STATE.md`, this file, `BUGS_AND_ISSUES.md`.
2. `git status` / `git log --oneline | head`.
3. Build: `cmake -S . -B build -G Ninja -DPLUSH_OIDN_ROOT=<oidn> && cmake --build build -j3`.
4. Test: `ctest --test-dir build` (expect 4/4: unit tests + 3 image regressions).
5. Regenerate characters if the kit changed: `python3 tools/charkit.py`.
6. Evidence: `tools/render_iteration4_evidence.sh` (resumable), comparisons: `python3 tools/make_it4_comparison.py`.
