"""Benchmark the published character turntable from the repository root."""
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

BUILD = (Path("build") / os.environ.get("T173_RUN", "t173")).resolve()
SCRIPT = Path(__file__).resolve()
BLENDER = "D:/Animation/tools/blender-5.3/blender.exe"
PRESETS = Path("pipeline/charsys/render_profiles.json")


def render(device, preset, frames, out):
    import bpy

    scene = bpy.context.scene
    from mathutils import Vector
    sys.path.insert(0, str(Path("pipeline/charsys").resolve()))
    import render_calibration as calibration
    for obj in list(scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    lights = calibration.apply(scene)
    camera = bpy.data.objects.new("Turntable", bpy.data.cameras.new("Turntable"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 70
    camera.data.sensor_fit = "VERTICAL"
    camera.data.sensor_height = 36
    scene.render.threads_mode = "AUTO"
    scene.render.engine = "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.cycles.seed = 0
    scene.cycles.use_adaptive_sampling = True
    profile = json.loads(PRESETS.read_text())["profiles"][preset]
    scene.render.use_persistent_data = False
    for group in ("cycles", "render"):
        for key, value in profile.get(group, {}).items():
            setattr(getattr(scene, group), key, value)
    scene.cycles.samples = profile["samples"]
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.use_denoising = True
    bpy.context.preferences.filepaths.temporary_directory = os.environ["TEMP"]
    scene.cycles.device = "CPU" if device == "CPU" else "GPU"
    if device != "CPU":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = device
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == device and "MX350" in d.name
        enabled = [(d.name, d.type) for d in prefs.devices if d.use]
        print("Enabled:", enabled, flush=True)
        if not enabled:
            raise RuntimeError(f"No MX350 enumerated for {device}")
    print("Config:", scene.render.engine, scene.cycles.device, scene.cycles.denoiser,
          scene.cycles.samples, scene.cycles.adaptive_threshold, flush=True)
    for i, frame in enumerate(frames):
        scene.render.filepath = str(out / f"{frame}.png")
        start = time.perf_counter()
        scene.frame_set(frame)
        yaw = math.radians({1: -15, 2: 0, 3: -45, 4: 90}[frame])
        elevation = math.radians(5)
        direction = Vector((math.sin(yaw)*math.cos(elevation), -math.cos(yaw)*math.cos(elevation), math.sin(elevation)))
        camera.location = Vector((0, 0, 0.56)) + direction * 2.45
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        calibration.orient(lights, direction)
        result = bpy.ops.render.render(write_still=True)
        seconds = time.perf_counter() - start
        if result != {"FINISHED"} or not Path(scene.render.filepath).is_file():
            raise RuntimeError(f"Render failed at frame {frame}")
        with (out / "times.csv").open("a", newline="") as file:
            csv.writer(file).writerow([frame, i == 0, round(seconds, 3)])
        if device == "CPU" and preset == "final720" and seconds > 600:
            frames[:] = frames[:3]


def run(device, preset, frames):
    out = BUILD / f"{preset}-{device}"
    out.mkdir(parents=True, exist_ok=False)
    for key, name in {"TEMP": "tmp", "TMP": "tmp", "BLENDER_USER_RESOURCES": "resources",
                      "CUDA_CACHE_PATH": "cuda-cache", "OPTIX_CACHE_PATH": "optix-cache"}.items():
        path = BUILD / name
        path.mkdir(exist_ok=True)
        os.environ[key] = str(path)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    (out / "requested.json").write_text(json.dumps(frames))
    sampler = None
    with (out / "smi.csv").open("w") as smi, (out / "blender.log").open("w") as log:
        if device != "CPU":
            sampler = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,memory.used,utilization.gpu",
                                        "--format=csv,noheader,nounits", "-lms", "500"], stdout=smi)
        try:
            scene = Path("assets/characters/girl_auburn_bun_glasses/versions/0.13.0/girl_auburn_bun_glasses_master.blend")
            result = subprocess.run([BLENDER, "-b", "--factory-startup", str(scene), "--debug-cycles",
                                     "--python-exit-code", "3", "-P", str(SCRIPT), "--",
                                     device, preset, *map(str, frames)], stdout=log, stderr=subprocess.STDOUT)
        finally:
            if sampler:
                sampler.terminate()
                sampler.wait()
    print(device, preset, result.returncode, flush=True)
    return result.returncode


if "--" in sys.argv:
    device, preset, *numbers = sys.argv[sys.argv.index("--") + 1:]
    render(device, preset, list(map(int, numbers)), BUILD / f"{preset}-{device}")
else:
    device, preset, *numbers = sys.argv[1:]
    sys.exit(run(device, preset, list(map(int, numbers))))
