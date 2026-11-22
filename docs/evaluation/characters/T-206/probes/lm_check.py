import bpy, sys, math, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); sc = bpy.context.scene
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18 / 70); d = Vector((0, -math.cos(math.radians(5)), math.sin(math.radians(5))))
cam.location = Vector((0, 0, float(a[2]))) + d * (0.66 / 2 / math.tan(fov / 2)); cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x = sc.render.resolution_y = 1024; sc.render.resolution_percentage = 100
bpy.context.view_layer.update()
P = {}
for n in ("LM_eye_L", "LM_eye_R", "LM_mouth", "LM_chin", "LM_nose"):
    v = world_to_camera_view(sc, cam, bpy.data.objects[n].matrix_world.translation); P[n[3:]] = (v.x, 1 - v.y)
    print(n, [round(x, 4) for x in bpy.data.objects[n].matrix_world.translation])
sp = abs(P["eye_L"][0] - P["eye_R"][0]); ey = (P["eye_L"][1] + P["eye_R"][1]) / 2
print("RATIOS chin,mouth,nose per eye spacing:", [round((P[k][1] - ey) / sp, 3) for k in ("chin", "mouth", "nose")])
A = json.load(open(a[1]))["landmarks"]; s = abs(A["eye_L"][0] - A["eye_R"][0]); e = (A["eye_L"][1] + A["eye_R"][1]) / 2
print("REF    chin,mouth,nose per eye spacing:", [round((A[k][1] - e) / s, 3) for k in ("chin", "mouth", "nose")])
# eye spacing relative to head width at the eye line (reference: ear_top_L - ear_top_R as a proxy)
print("REF eye spacing / ear-to-ear:", round(s / abs(A["ear_top_L"][0] - A["ear_top_R"][0]), 3))
eL = bpy.data.objects.get("LM_ear_L"); eR = bpy.data.objects.get("LM_ear_R")
if eL:
    vL = world_to_camera_view(sc, cam, eL.matrix_world.translation); vR = world_to_camera_view(sc, cam, eR.matrix_world.translation)
    print("OUR eye spacing / ear-to-ear:", round(sp / abs(vL.x - vR.x), 3))
