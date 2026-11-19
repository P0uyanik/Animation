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

## Not done here
- The grasp close-up is a Blender FK curl, not the engine's T-051 band grasp on the cup. The T-117 pickup-camera
  render is also not done. Both need the engine export and shot run with this override.
- `tools/check_all.py` lists plain tests explicitly and is outside the write-set, so `test_hands_r2.py` still has to
  be added there at merge.
