"""Exports Blender actions authored on the neutral mannequin as plush.clip/1 files (headless Blender).

    blender -b --factory-startup -P pipeline/clips/export_clip.py -- --blend <file with the mannequin and actions> \
        --out content/clips [--action <name> ...]

Every action carrying a "ps_clip_meta" custom property (JSON: name, fps, frame_count, loop, mask, contacts, source,
license, attribution, dense, ...) is exported; --action limits it to the given ones. The rig is the armature whose
collection has ps_character_id. Any future clip authored in Blender on the mannequin uses this exporter. The .blend
is only read (never saved)."""
import argparse
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
    ap.add_argument("--action", action="append", default=[])
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.get("ps_character_id"))
    for act in bpy.data.actions:
        if "ps_clip_meta" not in act or (a.action and act.name not in a.action):
            continue
        print("[export_clip]", CT.export_action(rig, act, os.path.abspath(a.out)))


main()
