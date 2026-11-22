"""T-197 benchmark. Run from the repository root. Every intermediate is under build/t197."""
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path.cwd()
BUILD = ROOT / "build/t197" / os.environ.get("T197_RUN", "review")
EP = ROOT / "episodes/e912_paper_boat"
CHAR = ROOT / "pipeline/charsys"
RECIPE = ROOT / "docs/evaluation/characters/T-155/girl/recipe.resolved.json"
BLENDER = "D:/Animation/tools/blender-5.3/blender.exe"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def environment():
    for key, folder in {"TEMP": "tmp", "TMP": "tmp", "BLENDER_USER_RESOURCES": "resources",
                        "APPDATA": "roaming", "LOCALAPPDATA": "local", "XDG_CACHE_HOME": "cache",
                        "CUDA_CACHE_PATH": "cuda-cache", "OPTIX_CACHE_PATH": "optix-cache",
                        "BLENDER_USER_CONFIG": "resources/config", "BLENDER_USER_DATAFILES": "resources/datafiles",
                        "BLENDER_USER_EXTENSIONS": "resources/extensions", "BLENDER_USER_SCRIPTS": "resources/scripts",
                        "BLENDER_USER_CACHE": "cache", "__GL_SHADER_DISK_CACHE_PATH": "gl-cache"}.items():
        dest = BUILD / folder
        dest.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(dest)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONUTF8"] = "1"


def sheet():
    import bpy
    import render_calibration as calibration
    recipe = read(RECIPE)
    master = ROOT / recipe["columns"][-1]["blend"]
    bpy.ops.wm.open_mainfile(filepath=str(master))
    sc = bpy.context.scene
    for obj in list(sc.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    rig = next(obj for obj in sc.objects if obj.type == "ARMATURE")
    for key in rig.keys():
        if key.startswith("face_"):
            rig[key] = 0.
    rig.update_tag()
    lights = calibration.apply(sc)
    cam = bpy.data.objects.new("ReviewCam", bpy.data.cameras.new("ReviewCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = recipe["cameras"]["lens_mm"]
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = recipe["cameras"]["sensor_mm"]
    cam.data.clip_start = .01
    return lights


def sheet_view(view, lights):
    import bpy
    from mathutils import Vector
    import render_calibration as calibration
    v = next(v for v in read(RECIPE)["cameras"]["views"] if v["name"] == view)
    cam = bpy.context.scene.camera
    a, e = map(math.radians, (v["yaw_deg"], v["elevation_deg"]))
    direction = Vector((math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e)))
    cam.location = Vector(v["target"]) + direction * (v["frame_height_m"] * cam.data.lens / cam.data.sensor_height)
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    calibration.orient(lights, direction)


def prop_scene():
    """s020 rest props on the original set. Focus the review camera on the hull."""
    import bpy
    from mathutils import Euler, Matrix, Vector
    import shot_render as shot
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    path = EP / "shots/s020/shot.scene.json"
    data = read(path)
    colors = {m["name"]: m["baseColor"] for m in data["materials"]}
    boxes = [dict(o, baseColor=colors[o["material"]]) for o in data["objects"]]
    shot.setup_world({"lights": data["lights"], "objects": boxes}, sc, 1.)
    assets = shot.find_assets(str(path))
    props = {p["name"]: p for p in data["props"]}
    objects, _ = shot.setup_props({"scene_path": str(path), "frame_data": [{"props": props}]}, sc)

    def matrix(xf):
        rotation = Euler(tuple(map(math.radians, xf["rotationDeg"])))
        return Matrix.LocRotScale(Vector(xf["translation"]), rotation, Vector(xf["scale"]))

    world = {}
    for name, spec in props.items():
        pose = matrix(spec["transform"])
        if "parent" in spec:
            parent = spec["parent"]
            socket = assets[props[parent["name"]]["id"]]["sockets"][parent["socket"]]
            pose = world[parent["name"]] @ matrix(socket) @ pose
        world[name] = pose
        objects[name].matrix_world = shot.Ci @ pose @ shot.C
    target = objects["boat"].matrix_world.translation + Vector((0, 0, .018))
    cam = bpy.data.objects.new("BoatDetail", bpy.data.cameras.new("BoatDetail"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    offset = Vector((.10, -.34, .095))
    cam.location = target + offset
    cam.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 70
    cam.data.clip_start = .01
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = offset.length
    cam.data.dof.aperture_fstop = 5.6
    sc.view_settings.exposure = data["render"]["exposureEV"]


def render(engine, names, out):
    import bpy
    import gpu
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(CHAR))
    import render_engine
    profile = read(CHAR / "render_profiles.json")["profiles"]["review"]
    if engine.startswith("eevee"):
        gpu.init()
        print("GPU", gpu.platform.renderer_get(), gpu.platform.backend_type_get(), flush=True)
        if "MX350" not in gpu.platform.renderer_get():
            raise RuntimeError("Unexpected EEVEE device")
    last_scene = None
    for index, name in enumerate(names):
        kind, _, label = name.partition("-")
        if kind == "sheet":
            if last_scene != kind:
                lights = sheet()
            sheet_view(label, lights)
        else:
            prop_scene()
        last_scene = kind
        sc = bpy.context.scene
        bpy.context.preferences.filepaths.temporary_directory = str(BUILD / "tmp")
        bpy.context.preferences.filepaths.render_cache_directory = str(BUILD / "cache")
        light = engine == "eevee-light"
        render_engine.configure(sc, "cycles" if engine == "cycles" else "eevee",
                                8 if light else profile["samples"], cycles_device="CPU",
                                cycles_denoiser="OPENIMAGEDENOISE")
        if engine == "cycles":
            render_engine.apply_profile(sc, profile)
            sc.cycles.seed = 0
            sc.cycles.use_denoising = True
            sc.cycles.denoising_use_gpu = False
            sc.cycles.use_adaptive_sampling = True
        else:
            sc.eevee.shadow_pool_size = "64" if light else "128"
            sc.eevee.use_raytracing = not light
            sc.eevee.ray_tracing_method = "SCREEN"
            sc.eevee.ray_tracing_options.resolution_scale = "4"
            if light:
                sc.eevee.shadow_ray_count = 1
        sc.render.threads_mode = "AUTO"
        sc.render.resolution_x, sc.render.resolution_y = profile["resolution"]
        sc.render.resolution_percentage = 100
        sc.render.film_transparent = False
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_depth = "8"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.filepath = str(out / (name + ".png"))
        start = time.time()
        tick = time.perf_counter()
        print("START", name, flush=True)
        if bpy.ops.render.render(write_still=True) != {"FINISHED"} or not Path(sc.render.filepath).is_file():
            raise RuntimeError("Failed to render " + name)
        seconds = time.perf_counter() - tick
        with (out / "times.csv").open("a", newline="") as fp:
            csv.writer(fp).writerow([name, index == 0, round(seconds, 3), start, time.time()])
        if engine == "cycles" and seconds > 300:
            names[:] = names[:3]


def run(engine, names):
    out = BUILD / engine
    out.mkdir(exist_ok=False)
    with (out / "smi.csv").open("w") as smi, (out / "blender.log").open("w") as log:
        sampler = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,memory.used,utilization.gpu",
                                    "--format=csv,noheader,nounits", "-lms", "500"], stdout=smi)
        try:
            subprocess.run([BLENDER, "-b", "--factory-startup", "--gpu-backend", "vulkan",
                            "--python-exit-code", "3", "-P", __file__, "--", engine, *names],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        finally:
            sampler.terminate()
            sampler.wait()


if __name__ == "__main__":
    if "--" in sys.argv:
        engine, *names = sys.argv[sys.argv.index("--") + 1:]
        render(engine, names, BUILD / engine)
    else:
        environment()
        engine, = sys.argv[1:]
        if engine not in {"cycles", "eevee", "eevee-light"}:
            raise SystemExit("Specify cycles, eevee or eevee-light")
        names = ["sheet-face_threequarter", "sheet-front", "prop-boat", "sheet-threequarter", "sheet-face_front"]
        if engine != "cycles":
            with (BUILD / "cycles/times.csv").open() as fp:
                names = [row[0] for row in csv.reader(fp)]
            if len(names) < 3:
                raise RuntimeError("Finish the Cycles measurement first")
        run(engine, names)
