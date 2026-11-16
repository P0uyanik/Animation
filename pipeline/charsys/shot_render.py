"""Renders an engine-animated shot in Blender (headless). Blender is the production renderer; the C++ engine owns the
animation (TD-42). Read-only on every character master.

    blender -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake bake.json --cast cast.json --out <dir>
        [--frames A-B] [--resolution W H] [--samples N] [--light-scale X]
        [--engine cycles|eevee] [--blend-only]

bake.json: the engine's shot bake (plush.shot_bake/1, `plush-render shot.scene.json --bake bake.json`).
cast.json: {"<character name in the scene>": {"master": <master .blend>, "character_id": <root collection>,
            "package": <engine package dir>}, ...} (written by pipeline/production/run_shot.py).

Per character (any rig whose deform bones the package lists; nothing character-specific):
  * the master is LINKED with a library override (episode.link_master); only the rig is editable;
  * deform bones: constraints muted in the shot, pose keyed from the baked skinning matrices
    (P_bone = W^-1 C^-1 S C W Rest_bone, C = engine<->Blender axes); bones driven by drivers (e.g. a jaw driven by
    facial controls) are left to their drivers, which read the keyed controls;
  * morphs: the rig's facial controls face_<morph> are keyed from the baked control weights (the master's drivers
    then produce every shape key, in-between and jaw rotation exactly as in Blender);
  * camera, lights (sun, rect, sky) and box props are translated from the bake.
Writes shot.blend (masters stay linked), frame_####.png, shot_render.json (timings, reconstruction error)."""
import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episode  # noqa: E402
import render_engine  # noqa: E402

C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))  # Blender -> engine axes
Ci = C.inverted()


def to_b(v):
    return Vector((v[0], -v[2], v[1]))  # engine point/direction -> Blender


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--cast", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="")
    ap.add_argument("--resolution", type=int, nargs=2, default=None)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--light-scale", type=float, default=1.0)
    ap.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    ap.add_argument("--blend-only", action="store_true")
    return ap.parse_args(argv)


def mat(flat):
    return Matrix([[flat[c * 4 + r] for c in range(4)] for r in range(4)])  # column-major -> Matrix


def setup_character(ch, cast, scene):
    """Links the character, prepares the rig. Returns a dict used per frame."""
    info = cast[ch["name"]]
    ov, rig = episode.link_master(os.path.abspath(info["master"]), info["character_id"], scene)
    pkg = json.load(open(os.path.join(info["package"], "character.json")))
    src = {b["name"]: b["source_name"] for b in pkg["skeleton"]}
    driven = {d.data_path.split('"')[1] for d in (rig.animation_data.drivers if rig.animation_data else [])
              if d.data_path.startswith("pose.bones[")}
    bones = []
    for i, n in enumerate(ch["bones"]):
        sn = src.get(n)
        if sn is None or sn not in rig.pose.bones:
            raise RuntimeError(f"{ch['name']}: baked bone {n} has no source bone in the rig")
        if sn in driven:
            continue
        pb = rig.pose.bones[sn]
        for c in pb.constraints:  # the engine's pose replaces the rig's constraint evaluation for deform bones
            c.mute = True
        pb.rotation_mode = "QUATERNION"
        bones.append((i, pb))
    # parents first, so a parent's target pose is known when a child's local basis is computed
    depth = lambda pb: len(pb.parent_recursive)  # noqa: E731
    bones.sort(key=lambda t: depth(t[1]))
    controls = [(k, f"face_{m}") for k, m in enumerate(ch["morphs"]) if f"face_{m}" in rig.keys()]
    unmapped = [m for m in ch["morphs"] if f"face_{m}" not in rig.keys() and "@" not in m]
    return {"rig": rig, "bones": bones, "controls": controls, "unmapped_morphs": unmapped,
            "skipped_driven_bones": sorted(driven & set(src.values())), "master": info["master"]}


def _key_bone(pb, P, Pp, frame):
    if pb.parent is None:
        basis = pb.bone.matrix_local.inverted() @ P
    else:
        basis = (pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local).inverted() @ Pp.inverted() @ P
    loc, rot, sca = basis.decompose()
    pb.location, pb.rotation_quaternion, pb.scale = loc, rot, sca
    for path in ("location", "rotation_quaternion", "scale"):
        pb.keyframe_insert(path, frame=frame, group=pb.name)


def apply_frame(st, data, frame):
    """Keys one frame. Bones whose parent is baked use the parent's target pose directly. Bones whose parent is a
    non-deform rig bone (e.g. Rigify ORG palm bones that follow the baked hand) are keyed again after the frame has
    been evaluated, so their parent's pose is the one Blender will actually compute."""
    rig = st["rig"]
    W = rig.matrix_world
    Wi = W.inverted()
    target, late = {}, []
    for i, pb in st["bones"]:
        S = mat(data["skin"][i * 16:(i + 1) * 16])
        P = Wi @ Ci @ S @ C @ W @ pb.bone.matrix_local  # armature-space pose matrix of the bone
        target[pb.name] = P
        par = pb.parent
        if par is not None and par.name not in target:
            late.append(pb)
        _key_bone(pb, P, target.get(par.name) if par is not None and par.name in target else (par.matrix if par else None), frame)
    for k, prop in st["controls"]:
        rig[prop] = float(data["morphs"][k])
        rig.keyframe_insert(f'["{prop}"]', frame=frame, group="face")
    return target, late


def fix_late(st, target, late, frame):
    for pb in late:  # parents evaluated at this frame now
        _key_bone(pb, target[pb.name], pb.parent.matrix, frame)


def setup_world(bake, scene, light_scale):
    """Lights, sky and box props from the bake (approximate radiometric translation, calibrated by light_scale)."""
    rep = {"lights": 0, "objects": 0}
    world = scene.world or bpy.data.worlds.new("shot_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Strength"].default_value = 0.0
    for i, l in enumerate(bake["lights"]):
        col = tuple(l["color"])
        if l["type"] == "sky":
            bg.inputs["Color"].default_value = (*col, 1)
            bg.inputs["Strength"].default_value = l["intensity"] * light_scale
            continue
        if l["type"] == "sun":
            ld = bpy.data.lights.new(f"sun.{i}", "SUN")
            ld.energy = l["intensity"] * 3.0 * light_scale
            ld.angle = math.radians(l.get("angleDeg", 2.0))
            ob = bpy.data.objects.new(f"sun.{i}", ld)
            ob.rotation_euler = to_b(l["direction"]).to_track_quat("-Z", "Y").to_euler()
        else:  # rect: area light at the rectangle's centre, emitting towards cross(edgeU, edgeV)
            u, v = to_b(l["edgeU"]), to_b(l["edgeV"])
            ld = bpy.data.lights.new(f"rect.{i}", "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = u.length, v.length
            ld.energy = l["intensity"] * u.length * v.length * math.pi * 10.0 * light_scale
            ob = bpy.data.objects.new(f"rect.{i}", ld)
            n = u.cross(v).normalized()
            ob.matrix_world = Matrix.Translation(to_b(l["corner"]) + 0.5 * (u + v)) @ Matrix(
                (u.normalized(), n.cross(u.normalized()), n)).transposed().to_4x4()
            ob.matrix_world = ob.matrix_world @ Matrix.Rotation(math.pi, 4, "X")  # area lights emit along local -Z
        ld.color = col
        scene.collection.objects.link(ob)
        rep["lights"] += 1
    for o in bake["objects"]:
        a, b = to_b(o["min"]), to_b(o["max"])
        lo = Vector((min(a.x, b.x), min(a.y, b.y), min(a.z, b.z)))
        hi = Vector((max(a.x, b.x), max(a.y, b.y), max(a.z, b.z)))
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(lo + hi) / 2)
        cube = bpy.context.object
        cube.name = f"prop.{o['name']}"
        cube.scale = hi - lo
        m = bpy.data.materials.new(f"M_prop_{o['name']}")
        m.use_nodes = True
        m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*o.get("baseColor", (0.6, 0.6, 0.6)), 1)
        m.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.9
        cube.data.materials.append(m)
        rep["objects"] += 1
    return rep


def key_camera(cam, c, frame):
    p, t = to_b(c["position"]), to_b(c["target"])
    cam.location = p
    cam.rotation_euler = (t - p).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = c["focalMm"]
    cam.data.sensor_width = c.get("sensorWidthMm", 36.0)
    cam.data.dof.use_dof = c.get("fStop", 0) > 0
    if cam.data.dof.use_dof:
        cam.data.dof.aperture_fstop = c["fStop"]
        cam.data.dof.focus_distance = c["focusDistance"] if c.get("focusDistance", -1) > 0 else (t - p).length
    for path in ("location", "rotation_euler"):
        cam.keyframe_insert(path, frame=frame)
    cam.data.keyframe_insert("lens", frame=frame)


def main():
    a = parse()
    t0 = time.time()
    os.makedirs(a.out, exist_ok=True)
    bake = json.load(open(a.bake))
    if bake.get("format") != "plush.shot_bake" or bake.get("version") != 1:
        raise SystemExit("not a plush.shot_bake/1 file")
    cast = json.load(open(a.cast))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    fa, fb = bake["frames"]
    if a.frames:
        x, _, y = a.frames.partition("-")
        fa, fb = int(x), int(y or x)
    num, den = bake["fps"]
    scene.render.fps, scene.render.fps_base = num, den
    scene.frame_start, scene.frame_end = fa, fb
    rep = {"bake": os.path.abspath(a.bake), "frames": [fa, fb], "characters": {}, "not_rendered": []}
    states = {}
    for ch in bake["characters"]:
        if not ch["supported"]:
            rep["not_rendered"].append(ch["name"])  # engine SDF characters have no Blender master
            continue
        if ch["name"] not in cast:
            raise SystemExit(f"cast has no master for character {ch['name']}")
        states[ch["name"]] = setup_character(ch, cast, scene)
    rep["world"] = setup_world(bake, scene, a.light_scale)
    cam = bpy.data.objects.new("shot_camera", bpy.data.cameras.new("shot_camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    err = {n: [0.0, 0.0] for n in states}
    for f in range(fa, fb + 1):
        fd = frames[f]
        key_camera(cam, fd["camera"], f)
        done = {n: apply_frame(st, fd["characters"][n], f) for n, st in states.items()}
        if any(late for _, late in done.values()):
            scene.frame_set(f)
            for n, (target, late) in done.items():
                fix_late(states[n], target, late, f)
        for n, st in states.items():
            target = done[n][0]
            if f in (fa, (fa + fb) // 2, fb):  # check the reconstruction: evaluated bone poses == baked poses
                scene.frame_set(f)
                for pb_name, P in target.items():
                    E = st["rig"].pose.bones[pb_name].matrix
                    err[n][0] = max(err[n][0], (E.translation - P.translation).length)
                    err[n][1] = max(err[n][1], math.degrees(E.to_quaternion().rotation_difference(P.to_quaternion()).angle))
    for n, st in states.items():
        rep["characters"][n] = {"master": st["master"], "baked_bones": len(st["bones"]), "facial_controls": len(st["controls"]),
                                "unmapped_morphs": st["unmapped_morphs"], "bones_left_to_drivers": st["skipped_driven_bones"],
                                "max_bone_error_mm": round(err[n][0] * 1000, 4), "max_bone_error_deg": round(err[n][1], 4)}
    r = scene.render
    engine_settings = render_engine.configure(scene, a.engine, a.samples)
    w, h = a.resolution or (bake["render"]["width"], bake["render"]["height"])
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    scene.view_settings.exposure = float(bake["render"].get("exposureEV", 0.0))
    r.filepath = os.path.join(os.path.abspath(a.out), "frame_")
    r.image_settings.file_format = "PNG"
    rep["setup_s"] = round(time.time() - t0, 1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), "shot.blend"), relative_remap=True)
    if not a.blend_only:
        t = time.time()
        bpy.ops.render.render(animation=True)
        rep["render_s"] = round(time.time() - t, 1)
        rep["render_s_per_frame"] = round(rep["render_s"] / (fb - fa + 1), 2)
    rep["resolution"], rep["samples"] = [w, h], a.samples
    rep["engine"] = a.engine
    if a.engine == "eevee":
        rep["engine_settings"] = engine_settings
    json.dump(rep, open(os.path.join(a.out, "shot_render.json"), "w"), indent=1)
    print("[shot_render]", json.dumps(rep))


if __name__ == "__main__":
    main()
