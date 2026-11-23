"""Blender side of set light rigs (T-221): builds a plush.light_rig/1 rig (set_lights.py) in a scene, and saves the
lights and world of a Blender scene as a rig file (so a rig lit and tuned in Blender is kept as data).

    blender -b --factory-startup -P pipeline/charsys/set_lights_blender.py -- dump --blend <file.blend> --id <rig id>
        --out content/sets/rigs/<rig id>.light_rig.json [--description "..."]

dump writes every LIGHT object of the open scene (and its world: Background colour/strength, or an Environment
Texture image as "hdri" relative to the output file) in Blender axes and units. Nothing character-specific."""
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import set_lights  # noqa: E402

TYPES = {"area": "AREA", "sun": "SUN", "point": "POINT", "spot": "SPOT"}
PREFIX = "rig."
SIGNIFICANT = 6  # float32 holds ~7 significant digits: 6 survive a build -> dump round trip unchanged


def _rotation(l):
    if "rotation_deg" in l:
        return Euler([math.radians(x) for x in l["rotation_deg"]], "XYZ")
    d = Vector(l["direction"]) if "direction" in l else Vector(l["aim"]) - Vector(l["location"])
    return d.normalized().to_track_quat("-Z", "Y").to_euler()  # lights emit along their local -Z


def build(rig, scene):
    """Adds the rig's lights and world to the scene (replacing scene.world). Returns a report."""
    objs = []
    for l in rig["lights"]:
        ld = bpy.data.lights.new(PREFIX + l["name"], TYPES[l["type"]])
        ld.color = tuple(l["color"])
        ld.use_shadow = l.get("cast_shadow", True)
        if l["type"] == "sun":
            ld.energy = l["strength"]
            ld.angle = math.radians(l.get("angle_deg", 0.526))
        else:
            ld.energy = l["energy"]
        if l["type"] == "area":
            ld.shape = l["shape"]
            ld.size = l["size"][0]
            if len(l["size"]) == 2:
                ld.size_y = l["size"][1]
        if l["type"] in ("point", "spot") and "radius" in l:
            ld.shadow_soft_size = l["radius"]
        if l["type"] == "spot":
            ld.spot_size = math.radians(l["spot_size_deg"])
            ld.spot_blend = l.get("spot_blend", 0.15)
        ob = bpy.data.objects.new(PREFIX + l["name"], ld)
        ob.location = Vector(l.get("location", (0.0, 0.0, 0.0)))
        if l["type"] != "point":
            ob.rotation_euler = _rotation(l)
        scene.collection.objects.link(ob)
        objs.append(ob)
    world = bpy.data.worlds.new(PREFIX + rig["id"])
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    wd = rig.get("world")
    if wd is None:
        bg.inputs["Strength"].default_value = 0.0
    elif "color" in wd:
        bg.inputs["Color"].default_value = (*wd["color"], 1.0)
        bg.inputs["Strength"].default_value = wd["strength"]
    else:
        path = set_lights.hdri_path(rig)
        if not os.path.isfile(path):
            raise set_lights.RigError(f"rig {rig['id']}: HDRI {path} not found")
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(path, check_existing=True)
        mp = nt.nodes.new("ShaderNodeMapping")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp.inputs["Rotation"].default_value[2] = math.radians(wd.get("rotation_deg", 0.0))
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = wd["strength"]
    return {"rig": rig["id"], "lights": len(objs), "objects": [o.name for o in objs],
            "world": "hdri" if wd and "hdri" in wd else "color" if wd else "none"}


def _r(v):
    v = float(f"{float(v):.{SIGNIFICANT}g}") + 0.0
    return 0.0 if abs(v) < 1e-9 else v


def _deg(radians):
    return round(math.degrees(radians), 4) + 0.0  # 0.0001 deg, stable through float32


def dump(scene, rig_id, out_path, description=""):
    """The scene's lights and world as a rig dict (validated). Light names drop a leading 'rig.'."""
    for vl in scene.view_layers:  # matrix_world of objects just created is valid only after an update
        vl.update()
    lights = []
    for ob in sorted((o for o in scene.objects if o.type == "LIGHT"), key=lambda o: o.name):
        ld = ob.data
        name = ob.name[len(PREFIX):] if ob.name.startswith(PREFIX) and len(ob.name) > len(PREFIX) else ob.name
        t = {v: k for k, v in TYPES.items()}[ld.type]
        loc, rot, _ = ob.matrix_world.decompose()
        e = rot.to_euler("XYZ")
        l = {"name": name, "type": t}
        if t != "sun":
            l["location"] = [_r(x) for x in loc]
        if t != "point":
            l["rotation_deg"] = [_deg(x) for x in e]
        if t == "area":
            l["shape"] = ld.shape
            l["size"] = [_r(ld.size), _r(ld.size_y)] if ld.shape in ("RECTANGLE", "ELLIPSE") else [_r(ld.size)]
        if t == "sun":
            l["strength"] = _r(ld.energy)
            l["angle_deg"] = _deg(ld.angle)
        else:
            l["energy"] = _r(ld.energy)
        if t in ("point", "spot"):
            l["radius"] = _r(ld.shadow_soft_size)
        if t == "spot":
            l["spot_size_deg"] = _deg(ld.spot_size)
            l["spot_blend"] = _r(ld.spot_blend)
        l["color"] = [_r(x) for x in ld.color]
        if not ld.use_shadow:
            l["cast_shadow"] = False
        lights.append(l)
    rig = {"format": set_lights.FORMAT, "version": set_lights.VERSION, "id": rig_id}
    if description:
        rig["description"] = description
    rig["lights"] = lights
    w = scene.world
    if w is not None and w.node_tree is not None and w.node_tree.nodes.get("Background"):
        bg = w.node_tree.nodes.get("Background")
        strength = _r(bg.inputs["Strength"].default_value)
        env = next((n for n in w.node_tree.nodes if n.type == "TEX_ENVIRONMENT" and n.image), None)
        if env is not None and bg.inputs["Color"].is_linked:
            src = bpy.path.abspath(env.image.filepath)
            wd = {"hdri": os.path.relpath(src, os.path.dirname(os.path.abspath(out_path))), "strength": strength}
            mp = next((n for n in w.node_tree.nodes if n.type == "MAPPING"), None)
            if mp is not None:
                wd["rotation_deg"] = _deg(mp.inputs["Rotation"].default_value[2])
            rig["world"] = wd
        elif strength > 0:
            rig["world"] = {"color": [_r(x) for x in bg.inputs["Color"].default_value[:3]], "strength": strength}
    return set_lights.validate(rig)


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--blend", required=True)
    d.add_argument("--id", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--description", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    rig = dump(bpy.context.scene, a.id, a.out, a.description)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(rig, indent=1) + "\n")
    print(f"[set_lights] wrote {a.out} ({len(rig['lights'])} lights, world {'world' in rig})")


if __name__ == "__main__":
    main()
