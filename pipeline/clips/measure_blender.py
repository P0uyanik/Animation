"""C3 measurement, Blender side: the authoring mannequin's posed role frames for every clip action (headless Blender).

    blender -b --factory-startup -P pipeline/clips/measure_blender.py -- --blend <mannequin_clips.blend> --out <json>

Per action and clip frame: per role the posed direction and twist reference (engine axes) of the evaluated Blender
pose (clip_tools.Rig.posed_frames). measure_clips.py compares them with the engine playing the exported clip on the
mannequin's engine package."""
import argparse
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clip_tools as CT  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.get("ps_character_id"))
    R = CT.Rig(rig)
    out = {}
    for act in bpy.data.actions:
        if "ps_clip_meta" not in act:
            continue
        meta = json.loads(act["ps_clip_meta"])
        rig.animation_data_create()
        rig.animation_data.action = act
        frames = {}
        for f in range(int(meta["frame_count"])):
            bpy.context.scene.frame_set(f)
            frames[f] = {r: {"dir": d, "twist": t} for r, (d, t) in R.posed_frames().items()}
        out[meta["name"]] = {"fps": meta["fps"], "frames": frames}
    json.dump(out, open(a.out, "w"))
    print("[measure_blender]", a.out, {k: len(v["frames"]) for k, v in out.items()})


main()
