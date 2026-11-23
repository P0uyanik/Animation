"""T-221 tests: set light rigs, Blender part (set_lights_blender.py + shot_render.setup_world). Headless, no render.

    blender -b --factory-startup -P pipeline/charsys/tests/test_set_lights_blender.py -- [<out.json>]
        [--fingerprint-only --charsys <dir>]     (prints the no-rig scene fingerprint of another checkout's shot_render)

SYNTHETIC scenes only (no character data). Checks:
  1. No-rig identity: shot_render.setup_world(rig=None) on a synthetic bake (rect, sun and sky lights, two boxes)
     builds a scene whose fingerprint (every object's name, type, matrix, light data, box size and colour, the world
     colour and strength) equals the one recorded from origin/main's shot_render before T-221 (NO_RIG_FINGERPRINT).
  2. Rig build: all four light types land with the rig's energy, colour, size, shape, angle, radius, spot size and
     shadow flag; area/spot/sun emit along their aim/direction (local -Z); a colour world sets the background; the
     bake's engine lights are NOT built when a rig is active, while its box objects still are.
  3. HDRI world: a tiny .hdr written by the test is loaded through an Environment Texture with the rig's rotation
     and strength; a missing HDRI file is refused.
  4. Dump round trip: dump(build(rig)) rebuilds to the same lights (location, orientation, energies within 1e-5)
     and the same world; the water_table_corner_window rig round-trips through build and dump unchanged.
Exit code 1 on any failure."""
import hashlib
import json
import math
import os
import sys
import tempfile

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CHARSYS = ARGV[ARGV.index("--charsys") + 1] if "--charsys" in ARGV else os.path.join(HERE, "..")
sys.path.insert(0, os.path.abspath(CHARSYS))
sys.argv = ["shot_render", "--"]  # shot_render parses its own argv only in main()
import shot_render  # noqa: E402

# setup_world(rig=None) fingerprint of the bake below, recorded with origin/main 6029c6e (before T-221):
#   blender -b --factory-startup -P <this> -- --fingerprint-only --charsys <main checkout>/pipeline/charsys
NO_RIG_FINGERPRINT = "68687398dccd3f4b4846fbdbe0dc79001dcf17cadac887be9f758e019771bf1d"
BAKE = {"lights": [{"type": "rect", "corner": [-1.95, 0.6, 1.2], "edgeU": [0.9, 0.0, 0.43], "edgeV": [-0.1, 1.2, 0.2],
                    "color": [1.0, 0.9, 0.8], "intensity": 2.5},
                   {"type": "sun", "direction": [0.3, -0.6, -0.74], "angleDeg": 4, "color": [1.0, 0.92, 0.82],
                    "intensity": 1.4},
                   {"type": "sky", "color": [0.6, 0.62, 0.66], "intensity": 0.4}],
        "objects": [{"name": "floor", "min": [-3, -0.05, -3], "max": [3, 0, 3], "baseColor": [0.4, 0.4, 0.4]},
                    {"name": "table", "min": [-0.3, 0.4, -0.2], "max": [0.3, 0.45, 0.2], "baseColor": [0.5, 0.3, 0.2]}]}
FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def fingerprint(scene):
    scene.view_layers[0].update()
    r = lambda v: [round(float(x), 6) + 0.0 for x in v]  # noqa: E731
    out = []
    for o in sorted(scene.objects, key=lambda o: o.name):
        e = {"name": o.name, "type": o.type, "matrix": [r(row) for row in o.matrix_world]}
        if o.type == "LIGHT":
            d = o.data
            e.update(ltype=d.type, energy=round(d.energy, 6), color=r(d.color), shadow=d.use_shadow)
            if d.type == "AREA":
                e.update(shape=d.shape, size=round(d.size, 6), size_y=round(d.size_y, 6))
            if d.type == "SUN":
                e.update(angle=round(d.angle, 6))
        if o.type == "MESH":
            e.update(dims=r(o.dimensions), verts=len(o.data.vertices),
                     colour=[r(m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value) for m in o.data.materials])
        out.append(e)
    bg = scene.world.node_tree.nodes.get("Background")
    out.append({"world": r(bg.inputs["Color"].default_value), "strength": round(bg.inputs["Strength"].default_value, 6),
                "linked": bg.inputs["Color"].is_linked})
    return hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()


def no_rig_identity():
    scene = fresh()
    boxes = []
    rep = shot_render.setup_world(json.loads(json.dumps(BAKE)), scene, 1.0, boxes)
    fp = fingerprint(scene)
    if "--fingerprint-only" in ARGV:
        print("NO_RIG_FINGERPRINT", fp, rep)
        return
    check(fp == NO_RIG_FINGERPRINT, f"no rig: setup_world scene identical to origin/main ({fp[:16]})")
    check(rep == {"lights": 2, "objects": 2} and len(boxes) == 2, "no rig: report and boxes as before (no rig key)")


try:  # absent in a pre-T-221 checkout (--fingerprint-only --charsys <main>)
    import set_lights  # noqa: E402
    import set_lights_blender as SLB  # noqa: E402
except ImportError:
    set_lights = SLB = None

RIG = {"format": "plush.light_rig", "version": 1, "id": "fixture_rig",
       "lights": [{"name": "key", "type": "area", "location": [-1.0, -1.0, 1.5], "aim": [0.0, 0.0, 1.0],
                   "shape": "RECTANGLE", "size": [1.0, 0.5], "energy": 80.0, "color": [1.0, 0.9, 0.8]},
                  {"name": "sun", "type": "sun", "direction": [0.2, 0.5, -1.0], "strength": 3.0, "angle_deg": 2.0,
                   "color": [1.0, 1.0, 0.9]},
                  {"name": "bulb", "type": "point", "location": [0.0, 1.0, 2.0], "radius": 0.1, "energy": 20.0,
                   "color": [1.0, 0.8, 0.6], "cast_shadow": False},
                  {"name": "spot", "type": "spot", "location": [1.0, -2.0, 2.0], "rotation_deg": [45.0, 0.0, 30.0],
                   "spot_size_deg": 40.0, "spot_blend": 0.2, "energy": 50.0, "color": [1.0, 1.0, 1.0]},
                  {"name": "disk", "type": "area", "location": [0.0, 2.0, 1.0], "aim": [0.0, 0.0, 1.0], "shape": "DISK",
                   "size": [0.3], "energy": 5.0, "color": [1.0, 1.0, 1.0]}],
       "world": {"color": [0.5, 0.5, 0.6], "strength": 0.3}}


def forward(ob):
    return (ob.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()


def rig_build():
    scene = fresh()
    boxes = []
    rep = shot_render.setup_world(json.loads(json.dumps(BAKE)), scene, 1.0, boxes, rig=RIG)
    lights = {o.name: o for o in scene.objects if o.type == "LIGHT"}
    check(sorted(lights) == sorted("rig." + l["name"] for l in RIG["lights"]),
          f"rig: exactly the rig's lights, none of the bake's ({sorted(lights)})")
    check(len(boxes) == 2 and rep["objects"] == 2 and rep["lights"] == 5 and rep["light_rig"]["rig"] == "fixture_rig",
          "rig: box objects still built, report names the rig")
    k, s, b, sp, dk = (lights["rig." + n] for n in ("key", "sun", "bulb", "spot", "disk"))
    check(k.data.type == "AREA" and k.data.shape == "RECTANGLE" and abs(k.data.size - 1.0) < 1e-6
          and abs(k.data.size_y - 0.5) < 1e-6 and abs(k.data.energy - 80.0) < 1e-4, "area: shape, size, energy")
    want = (Vector((0, 0, 1)) - Vector((-1, -1, 1.5))).normalized()
    check((forward(k) - want).length < 1e-6 and (k.location - Vector((-1, -1, 1.5))).length < 1e-6,
          "area: at its location, emitting towards its aim")
    check(abs(abs(k.matrix_world.to_3x3().col[0].z)) < 1e-6, "area: aimed with a level horizon (local X horizontal)")
    check(s.data.type == "SUN" and abs(s.data.energy - 3.0) < 1e-6 and abs(math.degrees(s.data.angle) - 2.0) < 1e-4
          and (forward(s) - Vector((0.2, 0.5, -1.0)).normalized()).length < 1e-6, "sun: strength, angle, direction")
    check(b.data.type == "POINT" and abs(b.data.shadow_soft_size - 0.1) < 1e-6 and not b.data.use_shadow
          and tuple(round(x, 6) for x in b.data.color) == (1.0, 0.8, 0.6), "point: radius, no shadow, colour")
    check(sp.data.type == "SPOT" and abs(math.degrees(sp.data.spot_size) - 40.0) < 1e-4
          and abs(sp.data.spot_blend - 0.2) < 1e-6
          and all(abs(math.degrees(a) - w) < 1e-4 for a, w in zip(sp.rotation_euler, (45, 0, 30))),
          "spot: size, blend, rotation_deg")
    check(dk.data.shape == "DISK" and abs(dk.data.size - 0.3) < 1e-6, "area disk: one size")
    bg = scene.world.node_tree.nodes["Background"]
    check(tuple(round(x, 6) for x in bg.inputs["Color"].default_value[:3]) == (0.5, 0.5, 0.6)
          and abs(bg.inputs["Strength"].default_value - 0.3) < 1e-6, "colour world: background colour and strength")
    no_world = dict(RIG)
    no_world.pop("world")
    scene = fresh()
    SLB.build(no_world, scene)
    check(scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value == 0.0, "no world: black, strength 0")


def hdri(tmp):
    img = bpy.data.images.new("t221_hdr", 8, 4, float_buffer=True)
    img.pixels = [0.5] * (8 * 4 * 4)
    os.makedirs(os.path.join(tmp, "hdri"))
    img.filepath_raw = os.path.join(tmp, "hdri", "room.hdr")
    img.file_format = "HDR"
    img.save()
    rigs = os.path.join(tmp, "rigs")
    os.makedirs(rigs)
    rig = {"format": "plush.light_rig", "version": 1, "id": "hdr_rig", "lights": [],
           "world": {"hdri": "../hdri/room.hdr", "strength": 1.5, "rotation_deg": 90.0}}
    p = os.path.join(rigs, "hdr_rig.light_rig.json")
    json.dump(rig, open(p, "w"))
    scene = fresh()
    rep = SLB.build(set_lights.load(p), scene)
    nt = scene.world.node_tree
    env = next((n for n in nt.nodes if n.type == "TEX_ENVIRONMENT"), None)
    mp = next((n for n in nt.nodes if n.type == "MAPPING"), None)
    bg = nt.nodes["Background"]
    check(rep["world"] == "hdri" and env is not None and env.image is not None
          and os.path.samefile(bpy.path.abspath(env.image.filepath), os.path.join(tmp, "hdri", "room.hdr")),
          "HDRI: environment texture loads the file relative to the rig")
    check(bg.inputs["Color"].is_linked and abs(bg.inputs["Strength"].default_value - 1.5) < 1e-6
          and abs(math.degrees(mp.inputs["Rotation"].default_value[2]) - 90.0) < 1e-4, "HDRI: strength and rotation")
    back = SLB.dump(scene, "hdr_rig", p)
    check(back.get("world") == rig["world"], f"HDRI: dump keeps the relative path, strength, rotation ({back.get('world')})")
    os.remove(os.path.join(tmp, "hdri", "room.hdr"))
    try:
        SLB.build(set_lights.load(p), fresh())
        ok = False
    except set_lights.RigError as e:
        ok = "not found" in str(e)
    check(ok, "HDRI: a missing file is refused")


def snapshot(scene):
    scene.view_layers[0].update()
    return {o.name: (o.matrix_world.translation.copy(), forward(o), o.data.energy, Vector(o.data.color))
            for o in scene.objects if o.type == "LIGHT"}


def same_lights(sa, sb):
    if sorted(sa) != sorted(sb):
        return False
    return all((a[0] - b[0]).length < 1e-5 and (a[1] - b[1]).length < 1e-5 and abs(a[2] - b[2]) < 1e-5
               and (a[3] - b[3]).length < 1e-5 for a, b in ((sa[n], sb[n]) for n in sa))


def round_trip(tmp):
    s1 = fresh()
    SLB.build(RIG, s1)
    first = snapshot(s1)
    d = SLB.dump(s1, "fixture_rig", os.path.join(tmp, "fixture_rig.light_rig.json"))
    s2 = fresh()
    SLB.build(d, s2)
    check(same_lights(first, snapshot(s2)), "dump round trip: rebuilt lights equal (location, direction, energy, colour)")
    check(d["world"] == RIG["world"] and [l["name"] for l in d["lights"]] == sorted(l["name"] for l in RIG["lights"]),
          "dump round trip: names and world kept")
    wtc = set_lights.find("water_table_corner_window")
    s3 = fresh()
    SLB.build(wtc, s3)
    back = SLB.dump(s3, wtc["id"], wtc["_path"], wtc.get("description", ""))
    ref = {k: v for k, v in wtc.items() if k != "_path"}
    by = {l["name"]: l for l in ref["lights"]}
    check(all(json.dumps(l, sort_keys=True) == json.dumps(by[l["name"]], sort_keys=True) for l in back["lights"])
          and back["world"] == ref["world"] and len(back["lights"]) == len(ref["lights"]),
          "water_table_corner_window: build + dump gives the file back")


def main():
    no_rig_identity()
    if "--fingerprint-only" in ARGV:
        return 0
    rig_build()
    with tempfile.TemporaryDirectory() as t:
        hdri(t)
    with tempfile.TemporaryDirectory() as t:
        round_trip(t)
    out = next((a for a in ARGV if a.endswith(".json")), None)
    if out:
        json.dump({"failures": FAILS, "passed": not FAILS}, open(out, "w"), indent=1)
    print(f"\n{'FAILED' if FAILS else 'PASSED'}: {len(FAILS)} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
