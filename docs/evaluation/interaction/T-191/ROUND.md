# T-191 round handover (context limit; follow-up goes to a fresh session)

State: READY at 58071dd, accepted by the R6 Supervisor (merging on integration/t-191, test registered there).
Open, owner-level (taken by R6 to the owner): 1) enable body clearance in e912 via `*_t191` shot copies (one
`{"type": "collision", "character": X, "bodyClearance": true}` per character); 2) staging for what the lean cannot
fix: e912 s020 f115-138 (her head over his held hand-over forearm, -102 mm) and s030 f57-91 (stand-up, -95 mm) —
wider seats (now 0.40-0.43 m with 0.3 m heads) and/or a lower hand-over point nearer the boy.

How to reproduce the numbers (fresh clone):
1. `cmake --preset fast-dev && cmake --build build/fast-dev -j4`
2. per shot: `python3 pipeline/production/run_shot.py --shot <shot>/shot.scene.json --blender /usr/local/bin/blender --stages prepare`
   (~1 min/shot) -> `<shot>/build/shot.resolved.scene.json`
3. build the tool (command line in `tools/motion_checks/body_contact.cpp`'s header; link the .a files from
   build/fast-dev/engine with -O3 -DNDEBUG, no embree/tbb needed), run it on the resolved scene, and on a copy with
   the collision actions appended for the "after"; `body_contact_report.py label=trace.json@A-B ...` for the tables.
4. frames: `plush-render <scene> --bake bake.json`, then Blender `pipeline/charsys/shot_render.py -- --bake ...
   --cast <shot>/build/cast.json --profile review --samples 16 --resolution 640 360 --frames F-F` (~100 s/frame).

Lessons: the lean alone does not move hip-height forearms (hence the arm yield); the arm yield must stay away from
planned contacts (a hand-over check failed at 23 mm before that rule); a larger lean limit hurts the middle of three
seated characters; pairs are solved in order, not jointly (a joint per-frame solve is the next step if needed).
