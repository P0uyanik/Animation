"""Shared character-render calibration (lights, backdrop, view transform, exposure) from render_calibration.json.

Character-agnostic: a profile is data. Lights are placed relative to the camera direction, so every view of a
turnaround (and any later review render) gets the same key-from-screen-left read that the reference sheets have.
The legacy compare_harness.studio_lighting is left untouched (silhouette/baseline renders depend on it).

    import render_calibration as RC
    prof = RC.load()                       # default profile
    rig = RC.apply(scene, prof)            # world, view transform, lights
    RC.orient(rig, cam_dir)                # cam_dir: unit vector from the subject towards the camera
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "render_calibration.json")
SCHEMA = "plush-studio.render-calibration/1"
DEFAULT = "character_neutral/1"


def load(name=DEFAULT, path=PATH):
    data = json.load(open(path, encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema must be {SCHEMA}")
    prof = data["profiles"][name]
    prof = dict(prof, name=name)
    return prof


def kelvin_rgb(k):
    """Linear RGB of a black body at k kelvin, normalised to 6500 K = white (Tanner Helland fit, then linearised)."""
    def raw(k):
        t = k / 100.0
        r = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
        g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
        b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
        return [min(255.0, max(0.0, c)) / 255.0 for c in (r, g, b)]

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    c, w = [lin(x) for x in raw(k)], [lin(x) for x in raw(6500)]
    c = [a / b for a, b in zip(c, w)]
    m = max(c)
    return tuple(x / m for x in c)


def srgb_to_linear(rgb):
    out = []
    for c in rgb:
        c = c / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def apply(scene, prof=None):
    """World (camera sees the backdrop colour; everything else sees the ambient), view transform, exposure and the
    profile's sun lights. Returns the light objects with their camera-relative angles (orient() aims them)."""
    import bpy
    prof = prof or load()
    world = bpy.data.worlds.new("PS_Calibrated")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    cam_bg = nt.nodes.new("ShaderNodeBackground")
    cam_bg.inputs["Color"].default_value = (*srgb_to_linear(prof["backdrop_srgb"]), 1)
    cam_bg.inputs["Strength"].default_value = 1.0
    amb = nt.nodes.new("ShaderNodeBackground")
    amb.inputs["Color"].default_value = (*kelvin_rgb(prof["ambient"]["color_kelvin"]), 1)
    amb.inputs["Strength"].default_value = float(prof["ambient"]["strength"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(amb.outputs[0], mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    vs = scene.view_settings
    vs.view_transform = prof["view_transform"]  # a dynamic enum: its items are not listed statically
    look = prof.get("look", "None")
    if look and look != "None":  # the default look is "none"; Blender 5 names looks per view transform
        try:
            vs.look = look
        except TypeError:
            pass
    vs.exposure = float(prof.get("exposure", 0.0))
    vs.gamma = float(prof.get("gamma", 1.0))
    scene.display_settings.display_device = "sRGB"
    rig = []
    for L in prof["lights"]:
        ld = bpy.data.lights.new("PS_" + L["name"], "SUN")
        ld.energy = float(L["strength"])
        ld.angle = math.radians(float(L.get("angle_deg", 10)))
        ld.color = kelvin_rgb(float(L.get("kelvin", 6500)))
        ob = bpy.data.objects.new("PS_" + L["name"], ld)
        scene.collection.objects.link(ob)
        rig.append((ob, float(L["azimuth_deg"]), float(L["elevation_deg"])))
    scene["ps_render_calibration"] = prof["name"]
    return rig


def orient(rig, cam_dir):
    """Aims every light relative to cam_dir (unit vector from the subject towards the camera, world Z up):
    azimuth 0 = light comes from the camera, +90 = from screen-left, 180 = from behind; elevation above horizon."""
    from mathutils import Matrix, Vector
    d = Vector(cam_dir)
    fwd = Vector((d.x, d.y, 0.0))
    fwd = fwd.normalized() if fwd.length > 1e-6 else Vector((0, -1, 0))
    for ob, az, el in rig:
        # screen-left of a camera looking along -fwd is fwd x Z rotated; rotate fwd about Z by +az (counter-clockwise
        # seen from above is screen-left for a camera that looks at the subject).
        v = Matrix.Rotation(math.radians(-az), 3, "Z") @ fwd
        v = (v * math.cos(math.radians(el)) + Vector((0, 0, math.sin(math.radians(el))))).normalized()
        ob.location = v * 5.0
        ob.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()
