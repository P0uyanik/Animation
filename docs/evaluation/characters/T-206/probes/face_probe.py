"""T-206 face probe (scratch only): smooth deformation bases as shape keys + landmark-ratio fit, timed.
blender -b --factory-startup -P face_probe.py -- <out> <master.blend> <annotation.json>"""
import bpy, sys, os, json, time, math
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
a = sys.argv[sys.argv.index("--") + 1:]; out, blend, ann = a[:3]
os.makedirs(out, exist_ok=True)
T0 = time.time(); bpy.ops.wm.open_mainfile(filepath=blend); t_load = time.time() - T0
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for k in [k for k in rig.keys() if k.startswith("face_")]: rig[k] = 0.0
body = bpy.data.objects["body_skin"]
# camera as T-202 front view
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18 / 70); d = Vector((0, -math.cos(math.radians(5)), math.sin(math.radians(5))))
cam.location = Vector((0, 0, 0.84)) + d * (0.66 / 2 / math.tan(fov / 2)); cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x = sc.render.resolution_y = 512; sc.render.resolution_percentage = 100
if "--head-only" in sys.argv:
    keep = {body.name, rig.name, cam.name} | {o.name for o in bpy.data.objects if o.name.startswith("LM_")}
    for o in list(bpy.data.objects):
        if o.name not in keep: bpy.data.objects.remove(o, do_unlink=True)
dg = bpy.context.evaluated_depsgraph_get()
def eval_coords():
    dg.update(); e = body.evaluated_get(dg); m = e.data
    p = np.empty(len(m.vertices) * 3, np.float32); m.vertices.foreach_get("co", p); p = p.reshape(-1, 3)
    W = np.array(e.matrix_world); return p @ W[:3, :3].T + W[:3, 3]
# landmark vertices: nearest skin vertex to each LM_ empty (rest), fixed index from then on
P0 = eval_coords()
lm_idx = {}
for n in ("LM_eye_L", "LM_eye_R", "LM_mouth", "LM_chin", "LM_nose"):
    c = np.array(bpy.data.objects[n].matrix_world.translation); lm_idx[n[3:]] = int(np.argmin(((P0 - c) ** 2).sum(1)))
def project(P, idx):
    r = {}
    for k, i in idx.items():
        v = world_to_camera_view(sc, cam, Vector(P[i].tolist())); r[k] = (v.x, 1 - v.y)  # image coords, y down
    return r
def ratios(pts):
    sp = abs(pts["eye_L"][0] - pts["eye_R"][0]); ey = (pts["eye_L"][1] + pts["eye_R"][1]) / 2
    return np.array([(pts["chin"][1] - ey) / sp, (pts["mouth"][1] - ey) / sp, (pts["nose"][1] - ey) / sp])
A = json.load(open(ann))["landmarks"]
tgt = ratios({"eye_L": A["eye_L"], "eye_R": A["eye_R"], "chin": A["chin"], "mouth": A["mouth"], "nose": A["nose"]})
# deformation bases (Basis-space, smooth falloffs around head landmarks); built once as shape keys
kb = body.data.shape_keys.key_blocks; B = np.empty(len(kb["Basis"].data) * 3, np.float32); kb["Basis"].data.foreach_get("co", B); B = B.reshape(-1, 3)
Mi = np.linalg.inv(np.array(body.matrix_world))
def loc(i): return (Mi @ np.append(P0[i], 1))[:3]
eye_z = (loc(lm_idx["eye_L"])[2] + loc(lm_idx["eye_R"])[2]) / 2; chin = loc(lm_idx["chin"]); mouth = loc(lm_idx["mouth"])
head_r = 0.16; hc = np.array([0, chin[1], eye_z])
w_head = np.clip(1 - np.linalg.norm((B - hc) / [head_r * 1.4, head_r * 1.6, head_r * 1.3], axis=1), 0, 1) ** 1.5
below = np.clip((eye_z - B[:, 2]) / (eye_z - chin[2]), 0, 1.4)
t = time.time()
bases = {
 "lower_face_length": np.stack([0 * B[:, 0], 0 * B[:, 1], -below * (eye_z - chin[2]) * 0.10], 1) * w_head[:, None],
 "mouth_drop": np.stack([0 * B[:, 0], 0 * B[:, 1], -np.exp(-((B[:, 0] - mouth[0]) ** 2 + (B[:, 2] - mouth[2]) ** 2) / (2 * 0.02 ** 2)) * 0.006], 1) * (B[:, 1] < chin[1] + 0.04)[:, None],
 "lower_face_width": np.stack([B[:, 0] * 0.10 * np.clip(below, 0, 1), 0 * B[:, 1], 0 * B[:, 2]], 1) * w_head[:, None],
}
for name, D in bases.items():
    k = body.shape_key_add(name=name, from_mix=False); k.data.foreach_set("co", (B + D).astype(np.float32).ravel()); k.slider_min, k.slider_max = -3, 3
t_basis = time.time() - t
names = ["lower_face_length", "mouth_drop"]

def f(x):
    for n, v in zip(names, x): kb[n].value = float(v)
    return ratios(project(eval_coords(), lm_idx))
t = time.time(); r0 = f([0, 0]); t_eval = time.time() - t
# Gauss-Newton with finite differences (each eval = one depsgraph update of the skinned head)
x = np.zeros(2); hist = [(0, r0.tolist())]; nev = 1; t = time.time()
for it in range(4):
    r = f(x); J = np.stack([(f(x + h) - r) / 0.05 for h in np.eye(2) * 0.05], 1); nev += 3
    # fit chin + mouth ratios (first two); nose kept as a check
    dx = np.linalg.lstsq(J[:2], (tgt - r)[:2], rcond=None)[0]; x = np.clip(x + dx, -3, 3); hist.append((it + 1, f(x).tolist())); nev += 1
t_fit = time.time() - t
res = {"load_s": round(t_load, 1), "basis_build_s": round(t_basis, 2), "eval_s": round(t_eval, 3), "fit_s": round(t_fit, 2), "evals": nev,
       "target_ratios(chin,mouth,nose per eye spacing)": tgt.round(3).tolist(), "start": r0.round(3).tolist(), "fitted": np.round(hist[-1][1], 3).tolist(), "weights": dict(zip(names, x.round(3).tolist())),
       "landmark_vertices": lm_idx}
# before/after Workbench front crops for the eye only
sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = 512; sc.render.image_settings.file_format = "PNG"
for tag, xv in (("start", [0, 0]), ("fitted", x)):
    for n, v in zip(names, xv): kb[n].value = float(v)
    t = time.time(); sc.render.filepath = os.path.join(out, "face_" + tag + ".png"); bpy.ops.render.render(write_still=True); res["workbench_" + tag + "_s"] = round(time.time() - t, 1)
json.dump(res, open(os.path.join(out, "face_probe.json"), "w"), indent=1); print("PROBE", json.dumps(res))
