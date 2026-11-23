"""Renders an engine-animated shot in Blender (headless). Blender is the production renderer; the C++ engine owns the
animation (TD-42). Read-only on every character master.

    blender -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake bake.json --cast cast.json --out <dir>
        [--frames A-B] [--resolution W H] [--samples N] [--light-scale X]
        [--engine cycles|eevee] [--blend-only] [--profile final720|review|legacy128] [--hair-pushout [on|spec.json|{json}]]

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
  * camera, lights (sun, rect, sky) and box objects are translated from the bake;
  * scene props (plush.asset/1, T-017/T-022): each prop in the bake's per-frame "props" block gets its asset's
    primitive mesh (box / sphere centred; cylinder standing on its base along +Y, optionally "open_top" with a "wall"
    thickness) and its first material preset from the shared library (pipeline/charsys/materials); the object is
    keyed every frame from the baked world matrix. Assets are found by id in content/assets above the baked scene.
  * eye sockets (T-030): on every frame, as Blender evaluates the applied bake, each eye's centre (sphere fit of its
    evaluated eyeball, any mesh bound only to an "eye.*" role bone and without shape keys) is compared with its
    socket (the rest centre carried by the head bone); the largest distance per character is reported.
  * hair push-out (T-194, opt-in, --hair-pushout): after the bake is keyed, hair is kept out of the real evaluated
    meshes (own body and garments, the other characters, props, box objects): chain bones re-keyed per frame and a
    per-vertex Geometry Nodes clamp on every hair object (hair_pushout.py). Without the flag nothing of it runs.
Writes shot.blend (masters stay linked), frame_####.png, shot_render.json (timings, reconstruction error, eye sockets)."""
import argparse
import json
import math
import os
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episode  # noqa: E402
import hair_pushout  # noqa: E402
import render_engine  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402

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
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--light-scale", type=float, default=1.0)
    ap.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    ap.add_argument("--blend-only", action="store_true")
    ap.add_argument("--hair-pushout", nargs="?", const="on", default=None,
                    help="T-194: push hair out of the real meshes (on, a spec JSON file or inline JSON; hair_pushout.py)")
    ap.add_argument("--profile", default=None,
                    help="render profile from render_profiles.json (T-166: default final720; legacy128 = the previous "
                         "128 spp / 0.01 preset); sets resolution/samples unless given")
    a = ap.parse_args(argv)
    profiles = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_profiles.json")))
    a.profile = a.profile or profiles["default_profile"]
    if a.profile not in profiles["profiles"]:
        ap.error(f"unknown --profile {a.profile!r} (have: {', '.join(profiles['profiles'])})")
    a.profile_data = profiles["profiles"][a.profile]
    if a.resolution is None and "resolution" in a.profile_data:
        a.resolution = list(a.profile_data["resolution"])
    if a.samples is None:
        a.samples = int(a.profile_data["samples"])
    return a


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
            "skipped_driven_bones": sorted(driven & set(src.values())), "master": info["master"],
            "eyes": eye_sockets(ov, rig, src), "ov": ov, "head_bone": src.get("head")}


def sphere_centre(points):
    """Least-squares sphere centre of points (N x 3). Moves rigidly with the points, so it is the same eye point in
    every frame whatever the gaze; for an eyeball it is the ball's centre, for a lid shell the centre it wraps."""
    P = np.asarray(points, dtype=np.float64)
    A = np.c_[2.0 * P, np.ones(len(P))]
    x = np.linalg.lstsq(A, (P * P).sum(axis=1), rcond=None)[0]
    return Vector(x[:3])


def mesh_points(o, mesh=None):
    me = mesh if mesh is not None else o.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def eye_sockets(ov, rig, src):
    """Eye-socket alignment probes (T-030). For every eye role ("eye.*" in the package) the character's meshes bound
    only to that role's bone (and without shape keys: blinking lids are not rigid) are its eye objects. Eye centre:
    the sphere centre of the evaluated mesh. Socket centre: the rest eye centre (armature space) carried by the head
    bone's evaluated pose, i.e. where the face holds the eye. An eye turning about its centre keeps the two equal; an
    eye that does not follow the head, or swings about a pivot off its centre, drifts off."""
    head = src.get("head")
    if head is None or head not in rig.data.bones:
        return []
    bpy.context.view_layer.update()  # linked override objects have no evaluated matrix_world before this
    Wi = rig.matrix_world.inverted()
    out = []
    for role, bone in sorted(src.items()):
        if not role.startswith("eye.") or bone not in rig.data.bones:
            continue
        for o in ov.all_objects:
            if o.type != "MESH" or not any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers):
                continue
            if o.data.shape_keys is not None or len(o.data.vertices) < 4:
                continue
            used = {o.vertex_groups[g.group].name for v in o.data.vertices for g in v.groups if g.weight > 0}
            if used != {bone}:
                continue
            out.append({"role": role, "object": o, "head": head, "rest_centre": Wi @ sphere_centre(mesh_points(o))})
    return out


def measure_eyes(st, deps):
    """Largest eye-centre to socket-centre distance (m) of this character at the evaluated frame."""
    rig, worst = st["rig"], 0.0
    W = rig.matrix_world
    for e in st["eyes"]:
        hb = rig.pose.bones[e["head"]]
        socket = W @ hb.matrix @ hb.bone.matrix_local.inverted() @ e["rest_centre"]
        ev = e["object"].evaluated_get(deps)
        centre = sphere_centre(mesh_points(ev, ev.to_mesh()))
        ev.to_mesh_clear()
        worst = max(worst, (centre - socket).length)
    return worst


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


def setup_world(bake, scene, light_scale, boxes=None):
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
        if boxes is not None:
            boxes.append(cube)
        rep["objects"] += 1
    return rep


def find_assets(scene_path):
    """plush.asset/1 files by id, from the nearest content/assets above the baked scene."""
    d = os.path.dirname(os.path.abspath(scene_path))
    while True:
        lib = os.path.join(d, "content", "assets")
        if os.path.isdir(lib):
            out = {}
            for n in sorted(os.listdir(lib)):
                if n.endswith(".asset.json"):
                    j = json.load(open(os.path.join(lib, n)))
                    out[j.get("id")] = j
            return out
        if os.path.dirname(d) == d:
            return {}
        d = os.path.dirname(d)


def prop_mesh(name, asset):
    """The asset's primitive as a Blender mesh in Blender axes (engine +Y up -> Blender +Z). Returns (mesh, note)."""
    m = asset.get("mesh", {})
    k = float(asset.get("scale", 1.0))
    bm = bmesh.new()
    note = ""
    prim = m.get("primitive")
    if prim == "cylinder":
        r, h = m["radius"] * k, m["height"] * k
        bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r, radius2=r, depth=h)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
        if m.get("open_top"):  # a vessel: no top cap (a solidify modifier gives the wall)
            top = [f for f in bm.faces if f.normal.z > 0.9 and min(v.co.z for v in f.verts) > h - 1e-6]
            bmesh.ops.delete(bm, geom=top, context="FACES_ONLY")
    elif prim == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=m["radius"] * k)
    elif prim == "box":
        sx, sy, sz = (v * k for v in m["size"])
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sz, sy), verts=bm.verts)
    else:  # file meshes are not imported here yet: a small placeholder cube, reported
        bmesh.ops.create_cube(bm, size=0.05)
        note = f"mesh source {m.get('path', '?')} not imported (placeholder)"
    me = bpy.data.meshes.new(f"PROP_{name}")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = prim in ("cylinder", "sphere")
    return me, note


def setup_props(bake, scene):
    """One object per baked prop instance. Returns ({name: object}, report)."""
    names = []
    for fd in bake["frame_data"]:
        for n in fd.get("props", {}):
            if n not in names:
                names.append(n)
    rep = {"props": {}, "unknown_material_presets": []}
    if not names:
        return {}, rep
    ids = {}
    try:
        sc = json.load(open(bake["scene_path"]))
        ids = {p["name"]: p["id"] for p in sc.get("props", [])}
    except (OSError, KeyError, ValueError):
        pass
    assets = find_assets(bake.get("scene_path", "."))
    library = MATERIALS.load_library()["presets"]
    objs = {}
    for n in names:
        asset = assets.get(ids.get(n), {"mesh": {}, "material_presets": []})
        me, note = prop_mesh(n, asset)
        ob = bpy.data.objects.new(f"prop.{n}", me)
        scene.collection.objects.link(ob)
        ob.rotation_mode = "QUATERNION"
        m = asset.get("mesh", {})
        if m.get("primitive") == "cylinder" and m.get("open_top"):
            sol = ob.modifiers.new("wall", "SOLIDIFY")
            sol.thickness = float(m.get("wall", 0.004)) * float(asset.get("scale", 1.0))
            sol.offset = -1.0
        preset = (asset.get("material_presets") or [None])[0]
        if preset in library:
            mat = MATERIALS.build_material(f"M_prop_{n}", preset)
        else:
            mat = bpy.data.materials.new(f"M_prop_{n}")
            mat.use_nodes = True
            if preset:
                rep["unknown_material_presets"].append(preset)
        me.materials.append(mat)
        objs[n] = ob
        rep["props"][n] = {"asset": ids.get(n), "primitive": m.get("primitive"), "material_preset": preset,
                           "preset_found": preset in library, **({"note": note} if note else {})}
    return objs, rep


def key_props(objs, fd, frame):
    for n, ob in objs.items():
        if n not in fd.get("props", {}):
            continue
        M = Ci @ mat(fd["props"][n]) @ C  # engine world -> Blender world (mesh is built in Blender axes)
        loc, rot, sca = M.decompose()
        ob.location, ob.rotation_quaternion, ob.scale = loc, rot, sca
        for path in ("location", "rotation_quaternion", "scale"):
            ob.keyframe_insert(path, frame=frame)


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
    boxes = []
    rep["world"] = setup_world(bake, scene, a.light_scale, boxes)
    props, rep["props"] = setup_props(bake, scene)
    pushout = None
    if a.hair_pushout is not None:
        tp = time.time()
        pushout = hair_pushout.PushOut(scene, hair_pushout.load_spec(a.hair_pushout), states, props, boxes)
        pushout_s = {"setup_s": round(time.time() - tp, 2), "chains_s": 0.0}
    cam = bpy.data.objects.new("shot_camera", bpy.data.cameras.new("shot_camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    err = {n: [0.0, 0.0] for n in states}
    eyes = {n: [0.0, None] for n in states}
    for f in range(fa, fb + 1):
        fd = frames[f]
        key_camera(cam, fd["camera"], f)
        key_props(props, fd, f)
        done = {n: apply_frame(st, fd["characters"][n], f) for n, st in states.items()}
        if any(late for _, late in done.values()):
            scene.frame_set(f)
            for n, (target, late) in done.items():
                fix_late(states[n], target, late, f)
        evaluated = False
        if any(st["eyes"] for st in states.values()):  # eye-socket alignment on every frame, as Blender evaluates it
            scene.frame_set(f)
            evaluated = True
            deps = bpy.context.evaluated_depsgraph_get()
            for n, st in states.items():
                if st["eyes"]:
                    d = measure_eyes(st, deps)
                    if d >= eyes[n][0]:
                        eyes[n] = [d, f]
        rekeyed = set()
        if pushout is not None:  # after the eye check: it reuses that evaluation (eyes do not depend on hair bones)
            tp = time.time()
            if not evaluated:
                scene.frame_set(f)
            rekeyed = pushout.frame(f, _key_bone)
            pushout_s["chains_s"] += time.time() - tp
        for n, st in states.items():
            target = done[n][0]
            if f in (fa, (fa + fb) // 2, fb):  # check the reconstruction: evaluated bone poses == baked poses
                scene.frame_set(f)
                for pb_name, P in target.items():
                    if (n, pb_name) in rekeyed:  # moved on purpose by the hair push-out
                        continue
                    E = st["rig"].pose.bones[pb_name].matrix
                    err[n][0] = max(err[n][0], (E.translation - P.translation).length)
                    err[n][1] = max(err[n][1], math.degrees(E.to_quaternion().rotation_difference(P.to_quaternion()).angle))
    if pushout is not None:
        tp = time.time()
        pushout.install()
        pushout_s["install_s"] = round(time.time() - tp, 2)
        pushout_s["chains_s"] = round(pushout_s["chains_s"], 2)
        rep["hair_pushout"] = {**pushout.report, "timing": pushout_s}
    for n, st in states.items():
        rep["characters"][n] = {"master": st["master"], "baked_bones": len(st["bones"]), "facial_controls": len(st["controls"]),
                                "unmapped_morphs": st["unmapped_morphs"], "bones_left_to_drivers": st["skipped_driven_bones"],
                                "max_bone_error_mm": round(err[n][0] * 1000, 4), "max_bone_error_deg": round(err[n][1], 4),
                                "eye_objects": [e["object"].name for e in st["eyes"]],
                                "eye_socket_max_mm": round(eyes[n][0] * 1000, 4) if st["eyes"] else None,
                                "eye_socket_worst_frame": eyes[n][1]}
    r = scene.render
    engine_settings = render_engine.configure(scene, a.engine, a.samples)
    rep["profile"] = {"name": a.profile, "applied": render_engine.apply_profile(scene, a.profile_data)}
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
