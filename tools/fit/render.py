"""Blender worker. One flat Workbench object-colour pass per reference camera.

A job with "kind": "face_measure" runs the T-214 face measurer passes instead (see measure_views)."""
import math
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import ROOT, child, read, write

sys.path.insert(0, str(ROOT / "pipeline/blender"))
import compare_harness as cameras


def main(job_path):
    job = read(job_path)
    out = Path(job_path).resolve().parent
    bpy.ops.wm.open_mainfile(filepath=str(child(out, job["blend"])))
    scene = bpy.context.scene
    root = next(c for c in bpy.data.collections if c.get("ps_character_id"))
    objects = [o for o in root.all_objects if o.type in ("MESH", "CURVES")
               and not o.hide_render and not o.name.startswith("WGT")]
    colours = {"eye.L": (1, 0, 0), "eye.R": (0, 1, 0),
               "brow.L": (0, 0, 1), "brow.R": (1, 1, 0)}
    for o in objects:
        o.color = (*colours.get(o.name, (1, 1, 1)), 1)
    cam = bpy.data.objects.new("Fit camera", bpy.data.cameras.new("Fit camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_y = job["height"]
    scene.render.resolution_x = job["height"] // 2
    scene.render.resolution_percentage = 100
    scene.display.render_aa = "OFF"
    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "OBJECT"
    shading.show_shadows = shading.show_cavity = shading.show_specular_highlight = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    empties = {o.name[3:]: o for o in root.all_objects if o.name.startswith("LM_")}
    for i, view in enumerate(job["views"]):
        prefixes = tuple(view.get("hide_objects_prefix", ()))
        for o in objects:
            o.hide_render = (o.name == "glasses_lens" or
                             (o.name.startswith(prefixes) and not o.name.startswith("garment.")))
        lo, hi = cameras.bbox([o for o in objects if not o.hide_render])
        cameras.place_camera(cam, (lo + hi) / 2, view["yaw_deg"], view["elevation_deg"],
                             view["focal_mm_estimate"], lo, hi,
                             scene.render.resolution_x / scene.render.resolution_y, 0.9)
        bpy.context.view_layer.update()
        points = {}
        for name, obj in empties.items():
            p = world_to_camera_view(scene, cam, obj.matrix_world.translation)
            points[name] = [p.x * scene.render.resolution_x, (1 - p.y) * scene.render.resolution_y]
        name = f"pass-{i:03d}"
        write(child(out, name + ".json"), points)
        scene.render.filepath = str(child(out, name + ".png"))
        bpy.ops.render.render(write_still=True)


# ----------------------------------------------------------------------------------------------- T-214 measurer
# Object classes of the measurer's ID masks. 0 is background. Names follow charsys masters; fibres inherit the
# class of the mesh they grow on ("hair_bun.fibres.001" -> bun).
CLASSES = ("background", "skin", "lid", "lash", "eye_L", "eye_R", "brow", "ear", "mouth", "cavity", "glasses",
           "hair", "bun", "hair_acc", "other")
CLASS_ID = {n: i for i, n in enumerate(CLASSES)}
# Passes: full = what the camera sees (lens omitted, as tools/fit does); face = no hair, bun, hair accessories or
# glasses (anatomical contours, openings and brows under hair); hair = main hair only (crown behind a bun).
PASSES = {"full": lambda c: c != "other",
          "face": lambda c: c not in ("hair", "bun", "hair_acc", "glasses", "other"),
          "hair": lambda c: c == "hair"}


def classify(name):
    """Measurer class of a master object name (None = not part of the head build)."""
    base = name.split(".fibres")[0]
    if base.startswith(("WGT", "garment.", "LM_")) or base in ("glasses_lens",):
        return None
    if base == "body_skin" or base.startswith("lid_lower") or base.startswith("nose"):
        return "skin"
    for prefix, cls in (("lid_upper", "lid"), ("lash", "lash"), ("brow", "brow"), ("ear.", "ear"),
                        ("mouth_cavity", "cavity"), ("mouth", "mouth"), ("glasses", "glasses"),
                        ("hair_bun", "bun"), ("hair_band", "hair_acc"), ("hair_flower", "hair_acc"),
                        ("hair_bow", "hair_acc"), ("bow", "hair_acc"), ("hair", "hair")):
        if base.startswith(prefix):
            return cls
    if base == "eye.L":
        return "eye_L"
    if base == "eye.R":
        return "eye_R"
    return "other"


def _np():
    import numpy
    return numpy


def _camera_basis(target, frame_h, yaw, elev, lens=70.0, sensor=36.0):
    """T-202 face_views.py camera: square frame, vertical sensor, distance from the frame height."""
    from mathutils import Vector
    fov = 2 * math.atan(sensor / 2 / lens)
    a, el = math.radians(yaw), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
    loc = Vector(target) + d * (frame_h / 2 / math.tan(fov / 2))
    return loc, (-d).to_track_quat("-Z", "Y").to_euler()


def _read_exr(path, px):
    np = _np()
    img = bpy.data.images.load(str(path))
    try:
        a = np.empty(px * px * 4, np.float32)
        img.pixels.foreach_get(a)
    finally:
        bpy.data.images.remove(img)
    return a.reshape(px, px, 4)[::-1]


def _iris_ring(eye, rho, n=72):
    """World points of the iris edge: the eye shader paints the iris where the distance from the forward axis in
    texture space ('Generated', the unit sphere over the texture-space box) is below `rho`. Rest pose -> the
    eye bone's deformation (Armature modifier, single DEF-eye group)."""
    from mathutils import Vector
    me = eye.data
    loc, size = Vector(me.texspace_location), Vector(me.texspace_size)
    rig = next((m.object for m in eye.modifiers if m.type == "ARMATURE" and m.object), None)
    deform = eye.matrix_world
    if rig and eye.vertex_groups:
        pb = rig.pose.bones.get(eye.vertex_groups[0].name)
        if pb:
            skin = pb.matrix @ pb.bone.matrix_local.inverted()
            deform = rig.matrix_world @ skin @ rig.matrix_world.inverted() @ eye.matrix_world
    y = -math.sqrt(max(0.0, 1 - rho * rho))
    mat = eye.active_material
    kx = 1.0 / float(mat.get("ps_round_iris", 1.0)) if mat else 1.0  # felt/1 round_iris rescales unit x
    ring = [deform @ (loc + Vector((size.x * kx * rho * math.cos(t), size.y * y, size.z * rho * math.sin(t))))
            for t in (2 * math.pi * k / n for k in range(n))]
    centre = deform @ (loc + Vector((0, -size.y, 0)))
    return ring, centre


def measure_views(job_path):
    """T-214 face measurer, Blender side. Head-only build of the master: garments, rig widgets, lights and cameras
    are removed in memory (nothing is saved). Per view: three flat Workbench object-ID passes (full, face, hair)
    with a depth channel, LM_* projections, analytic iris rings and surface landmarks with ray_cast visibility.

    job: {"kind": "face_measure", "blend", "px", "views": [{"name", "yaw", "elev", "target", "frame_h",
          "expression": {"face_Smile": 1.0, ...}}], "iris_radius": {"eye_L": rho, "eye_R": rho}}"""
    np = _np()
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    t0 = time.perf_counter()
    job = read(job_path)
    out = Path(job_path).resolve().parent
    blend = Path(job["blend"])
    bpy.ops.wm.open_mainfile(filepath=str(blend if blend.is_absolute() else child(out, job["blend"])))
    scene = bpy.context.scene
    classes = {}
    for o in list(bpy.data.objects):
        cls = classify(o.name) if o.type in ("MESH", "CURVES") else None
        if o.type in ("LIGHT", "CAMERA") or (o.type in ("MESH", "CURVES") and cls is None
                                              and o.name != "glasses_lens"):
            bpy.data.objects.remove(o, do_unlink=True)
        elif cls:
            classes[o.name] = cls
    lens = bpy.data.objects.get("glasses_lens")
    if lens:
        lens.hide_render = lens.hide_viewport = True  # transparent: omitted as in tools/fit
    for name, cls in classes.items():
        o = bpy.data.objects[name]
        o.hide_render = cls == "other" or name.startswith("hand.")
        o.color = (CLASS_ID[cls] / 32.0, 0.5, 0.0, 1.0)  # R/G: strands vary brightness (+0..0.5 id)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    face_keys = [k for k in rig.keys() if k.startswith("face_")]
    lm = {o.name[3:]: o for o in bpy.data.objects if o.name.startswith("LM_")}
    cam = bpy.data.objects.new("T214 camera", bpy.data.cameras.new("T214 camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
    px = int(job["px"])
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.display.render_aa = "OFF"
    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "OBJECT"
    shading.show_shadows = shading.show_cavity = shading.show_specular_highlight = False
    shading.show_object_outline = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.view_layers[0].use_pass_z = True
    tree = bpy.data.node_groups.new("T214 id+depth", "CompositorNodeTree")
    scene.compositing_node_group = tree
    nodes = tree.nodes
    layers, split, join = (nodes.new(t) for t in ("CompositorNodeRLayers", "CompositorNodeSeparateColor",
                                                  "CompositorNodeCombineColor"))
    group_out = nodes.new("NodeGroupOutput")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    tree.links.new(layers.outputs["Image"], split.inputs[0])
    tree.links.new(split.outputs[0], join.inputs[0])
    tree.links.new(split.outputs[1], join.inputs[1])
    tree.links.new(layers.outputs["Depth"], join.inputs[2])  # B = camera depth (m)
    tree.links.new(layers.outputs["Alpha"], join.inputs[3])
    tree.links.new(join.outputs[0], group_out.inputs[0])
    timings = {"load_s": time.perf_counter() - t0, "views": {}}
    rho = job.get("iris_radius", {})
    result = {"px": px, "classes": list(CLASSES), "views": []}
    for view in job["views"]:
        tv = time.perf_counter()
        for k in face_keys:
            rig[k] = 0.0
        for k, v in (view.get("expression") or {}).items():
            rig[k] = float(v)
        rig.update_tag()
        bpy.context.view_layer.update()
        cam.location, cam.rotation_euler = _camera_basis(view["target"], view["frame_h"], view["yaw"], view["elev"])
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        inv = cam.matrix_world.inverted()
        f = 70.0 / 36.0 * px

        def project(p):
            c = inv @ Vector(p)
            return [px / 2 + f * c.x / -c.z, px / 2 - f * c.y / -c.z, -c.z]

        def visible(p, target=None, tol=1.5e-3):
            d = Vector(p) - cam.location
            dist = d.length
            hit, loc, _n, _i, ob, _m = scene.ray_cast(dg, cam.location, d.normalized(), distance=dist + 5e-3)
            if not hit:
                return True
            return (loc - Vector(p)).length < tol and (target is None or ob.original.name == target)

        rec = {"name": view["name"], "yaw": view["yaw"], "elev": view["elev"], "target": view["target"],
               "frame_h": view["frame_h"], "expression": view.get("expression") or {},
               "camera": {"matrix_world": [list(r) for r in cam.matrix_world], "lens": 70.0, "sensor": 36.0},
               "landmarks": {}, "iris": {}, "surface": {}}
        for name, o in lm.items():
            p = o.matrix_world.translation
            rec["landmarks"][name] = project(p) + [list(p)]
        for side in ("L", "R"):
            eye = bpy.data.objects.get(f"eye.{side}")
            if eye and f"eye_{side}" in rho:
                ring, centre = _iris_ring(eye, rho[f"eye_{side}"])
                rec["iris"][f"eye_{side}"] = {"ring": [project(p)[:2] for p in ring], "centre": project(centre),
                                              "centre_world": list(centre)}
        # Surface landmarks (LM_* are centres): nose tip = most anterior skin vertex near LM_nose; chin = skin
        # point nearest LM_chin (BVH). Visibility by ray_cast; hidden points are reported as hidden.
        skin = bpy.data.objects.get("body_skin")
        if skin:
            ev = skin.evaluated_get(dg)
            me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3) @ np.array(ev.matrix_world)[:3, :3].T + np.array(ev.matrix_world)[:3, 3]
            if "nose" in lm:
                # Apex of the nose bump: the skin vertex near LM_nose farthest out from the head centre (ears).
                c = np.array(lm["nose"].matrix_world.translation)
                ears = [np.array(lm[k].matrix_world.translation) for k in ("ear_L", "ear_R") if k in lm]
                centre = np.mean(ears, axis=0) if ears else c + np.array([0, 0.08, 0])
                axis = (c - centre) / np.linalg.norm(c - centre)
                near = co[np.linalg.norm(co - c, axis=1) < 0.012]
                if len(near):
                    tip = near[np.argmax((near - centre) @ axis)]
                    rec["surface"]["nose_tip"] = project(tip) + [tip.tolist(), visible(tip, "body_skin")]
            if "chin" in lm:
                tris = [tuple(p.vertices) for p in me.polygons]
                bvh = BVHTree.FromPolygons([Vector(v) for v in co], tris)
                loc, _n, _i, dist = bvh.find_nearest(lm["chin"].matrix_world.translation)
                rec["surface"]["chin"] = project(loc) + [list(loc), visible(loc, "body_skin"), dist]
            ev.to_mesh_clear()
        stem = f"view-{view['name']}"
        arrays = {}
        for pas, keep in PASSES.items():
            for name, cls in classes.items():
                o = bpy.data.objects[name]
                o.hide_render = not keep(cls) or name.startswith("hand.")
            path = child(out, f"{stem}-{pas}.exr")
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            a = _read_exr(path, px)
            path.unlink()
            alpha = a[..., 3] > 0.5
            ratio = 16 * a[..., 0] / np.maximum(a[..., 1], 1e-6)
            arrays[f"{pas}_cls"] = np.where(alpha, np.clip(np.floor(ratio + 0.3), 0, len(CLASSES) - 1), 0).astype(np.uint8)
            if pas == "face":
                arrays["face_depth"] = np.where(alpha, a[..., 2], np.inf).astype(np.float32)
        np.savez_compressed(child(out, stem + ".npz"), **arrays)
        rec["arrays"] = stem + ".npz"
        result["views"].append(rec)
        timings["views"][view["name"]] = time.perf_counter() - tv
    for k in face_keys:
        rig[k] = 0.0
    result["timings"] = timings
    write(child(out, "measure-views.json"), result)


if __name__ == "__main__":
    job_file = sys.argv[sys.argv.index("--") + 1]
    if read(job_file).get("kind") == "face_measure":
        measure_views(job_file)
    else:
        main(job_file)
