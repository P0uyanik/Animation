# T-121: finger separation on the hand mesh (hands_r2/1, opt-in)

Input `integration/r4-start @ 5a90975`. Blender 5.3.0 (bpy module, CPU, Cycles 16–24 spp previews).

## What changed
- `pipeline/charsys/hands_r2.py` (new): separated fingers. Spacing 0.64 × palm half-width (body_generic: 0.55),
  knuckle gap 0.14 × spacing, fan spread 4° per finger step so the tips open further, finger radius ≤ 0.92 × spec,
  round fingertip pads 1.04 × radius, remesh voxel 0.30 × gap so the gap survives, then decimated to 8k vertices per hand.
  The finger points of the hand frames are replaced before the rig is fitted, so the bones follow the fingers. The bone
  names, the vertex groups and the role-"hand" heat weights stay the same.
- `pipeline/charsys/build_character.py`: one guarded branch in `main_generic`. It runs only when `body.hands` is
  `"hands_r2/1"`, and the build report gets a `hands` block. `body_v6.py` and `versions.py` are untouched.
- Opt-in through `hands_r2.override.json` (`{"body": {"hands": "hands_r2/1"}}`) as a shot- or candidate-level override.

| | boy 2.1.0 | girl 0.12.0 |
|---|---|---|
| finger radius (spec → r2) | 12.37 → 11.16 mm | 7.80 → 6.60 mm |
| knuckle gap | 3.63 mm | 2.15 mm |
| min clearance at rest / full grasp (capsules) | > 0 (see test) | > 0 (see test) |
| unweighted after cleanup / nearest-bone fallback | 0 / none | 0 / none |

## Evidence
- `boy_hand_L_current_vs_r2.png`: the boy's left hand at rest, at 0.75 grasp curl and at full grasp curl (FK finger
  controls at 40/50/35° per joint, thumb at 25/25°). On the current hand the fingers fuse into a mitten. On r2 each
  fingertip reads separately, and the fingers stay short and chubby (#7, #24, #27).
- `girl_hand_L_mesh_preview.png`: the girl's mesh, back view, r2 against the current hand.
- `default_build_check.json`: the default boy 2.1.0 build on this branch has the same fingerprint_v2 (0.01 mm) and the
  same build_report.json as the input commit.
- `hand_frames.json` and `hand_vertex_groups.json`: fixtures recorded from Blender for the plain tests.
- `scripts/`: the preview, close-up and fixture scripts (run with `tools/bpy_blender.py` or the bpy venv).

## Engine grasp (T-051 bands) and pickup camera
- `shots/current` and `shots/candidate` are copies of `docs/evaluation/animation/T-051/shots/s010_band` (e907 s010
  plus the T-051 band tracks). Only the cast differs. Current uses the published boy 2.1.0 and girl 0.12.0;
  candidate uses the same specs plus `hands_r2.override.json`. Both ran through `run_shot.py --blend-only`
  (cast export -> engine bake -> shot.blend, the C++ engine built with the renderer off). Both bakes report a maximum
  bone error of about 0.001 mm and 0 deg.
- `grasp_engine_current_vs_r2.png`:
  - Rows 1 and 2: T-051's `render_close.py` front view (the boy's right hand) and back view (the girl's left hand) at
    f48, the shared hold, with the same cameras as T-051.
  - Row 3: the e907 shot camera at f20, just after the boy picks the cup up. This stands in for the T-117 pickup
    camera, which is not built yet.
  - Row 4: a 4x crop of the boy's hand from that frame.
  - Cycles 16 spp.
- Result:
  - The girl's fingers wrap the cup separately; on the current hand they read as one mitten.
  - The boy's fingertips read at the top and bottom of the cup and in the pickup crop. Seen from the back of his hand
    (front view), the knuckles still read as one mass, more weakly than the girl's.
  - Wrist, palm, arms, cup, bodies, camera and lights are the same in current and candidate.

## Open
- `tools/check_all.py` lists plain tests explicitly and is outside the write-set, so `test_hands_r2.py` is to be
  added there at merge (Supervisor).
