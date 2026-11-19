import sys, math, bpy
sys.path.insert(0, "/home/user/Animation/pipeline/charsys")
import body_generic as BG, hands_r2 as HR, spec as S, geom as G
from mathutils import Vector
out = sys.argv[-1]
spec,_ = S.load("/home/user/Animation/assets/characters/" + sys.argv[-3])
P, H = spec["body"]["params"], float(spec["body"]["height_m"])
bpy.ops.wm.read_factory_settings(use_empty=True)
C = bpy.data.collections.new("c"); bpy.context.scene.collection.children.link(C)
M = {"skin": G.material("M_skin", (240, 200, 175), roughness=0.6)}
J = BG.joints(P, H, None); fr = BG.hand_frames(P, H, J)
parts = BG.build_body(C, M, P, H, J, fr)
old = [o for o,r in parts if r=="hand" and o.name=="hand.L"][0]; old.name="old_hand"
oldL = old.copy(); oldL.data = old.data.copy()
fr2 = BG.hand_frames(P, H, J)
parts2, rep = HR.replace_hands(C, M, [(oldL,"hand")], P, H, J, fr2, G)
print(rep)
for o,r in parts:
    if o.name != "old_hand": bpy.data.objects.remove(o)
new = [o for o,r in parts2 if o.name=="hand.L"][0]
H_SCALE = P["hand"]["palm_len"] / 0.068
pn = fr["L"]["palm_n"]; d = fr["L"]["d"]; sv = fr["L"]["side_v"]
def ctr(o):
    import numpy as np
    return Vector(np.mean([tuple(v.co) for v in o.data.vertices], axis=0))
old.location = -sv*0.075*H_SCALE ; new.location = sv*0.075*H_SCALE
target = (ctr(old)+old.location+ctr(new)+new.location)/2
sc = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); C.objects.link(cam); sc.camera = cam
H_SCALE = P["hand"]["palm_len"] / 0.068
view = sys.argv[-2]
dirv = {"back": -pn, "palm": pn, "side": (-pn+d*0.0+Vector((0,-1,0))).normalized()}[view]
cam.location = target - dirv*0.62*H_SCALE
cam.rotation_euler = (target - cam.location).to_track_quat("-Z","Y").to_euler()
cam.data.lens = 85
for loc,e in (((1,-1,1.5),3.0),((-1,-0.5,0.5),1.0)):
    l = bpy.data.objects.new("l", bpy.data.lights.new("l","SUN")); l.data.energy=e; C.objects.link(l); l.rotation_euler = (Vector((0,0,0))-Vector(loc)).to_track_quat("-Z","Y").to_euler()
sc.world = bpy.data.worlds.new("w"); sc.world.color=(0.3,0.3,0.32)
sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device="CPU"; print("oldverts", len(old.data.vertices)); sc.render.resolution_x=640; sc.render.resolution_y=480
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
