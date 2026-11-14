# Milestone 2026-11-14: M3.2, first end-to-end production path

| Item | Result |
| --- | --- |
| Decision | TD-42: the C++ engine animates, Blender (Cycles) renders final shots |
| Built | `engine/scene/shot_bake.{h,cpp}` (`plush.shot_bake/1`); `plush-render --bake`; `SceneEvaluator::cameraAt` / `morphControlWeight`; `pipeline/charsys/shot_render.py`; `pipeline/production/run_shot.py`; `episode.link_master` (refactor, same behaviour) |
| Pilot shot | `episodes/e000_pilot/shots/s010/shot.scene.json`: 4 s at 30 fps; published boy 1.0.0 + unpublished girl M3.1 (built from her spec in the shot's build folder); walk, look, expressions, life layer, camera push-in. 120 frames rendered + mp4 |
| Accuracy | Bone reconstruction ≤ 0.0003 mm / 0.0°; bake round trip 0 mm (C++ test); all morphs mapped to facial controls |
| Cost | Bake 0.2 s; Cycles 8.6 s per frame (640×360, 32 samples) |
| Tests | New C++ bake test; `ctest` 4/4 (frozen images unchanged); 19,466 assertions; `verify_charsys` PASS |
| Disconnected | Plush Studio; episode and sequence assembly; audio; SDF props and engine-only characters; radiometric light match; relaxed arm idle for imported characters |
| Approvals | Nothing published or approved |

Agents: one primary agent, no subagents. Token counts are not exposed to me and are not estimated.
