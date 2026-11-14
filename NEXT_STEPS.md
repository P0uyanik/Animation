# Next steps

**Exact next task:** the user runs `pipeline/blender/boy_pilot/reproduce_v6.py` with their installed Blender
(`docs/evaluation/boy_pilot/LOCAL_REPRODUCTION.md`) and sends back `out/local_v6/VERIFICATION.md`.
- Then record the verified local v6 baseline (Blender version, verdict, differences).
- No v7, no character changes, no iteration 5 before that.

**Next concrete milestone (CP-2, character production pipeline):**
1. On the same computer, run the pipeline check. It writes only into `--out`:
   ```bash
   python3 pipeline/charsys/verify_charsys.py --blender <your blender> --out out/charsys_check
   ```
   Send back `out/charsys_check/CHARSYS_VERIFICATION.md`. It proves, on your Blender, that the spec build equals v6
   and that version 1.0.0 reopens and links into episode shots.
2. Then `hair_clumps/2`: a new lock layout (30–40 larger locks in lock families, notches down to the dark base).
   - Experimental, measured with `pipeline/charsys/hair_experiments.py`.
   - Target: hair contour ≤ 3.0%, IoU not lower, clean visual from all 8 angles.
   - If met, it is proposed to you as candidate 1.1.0. Nothing is adopted without your approval.
3. Decisions open for you (no action until you decide):
   - approve version 1.0.0 as the `approved` boy;
   - adopt H12 (small, clean hair gain) or wait for `hair_clumps/2`.

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
