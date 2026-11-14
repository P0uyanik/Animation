"""Reuse test for a published character version (headless Blender). Read-only on the store.

    blender -b --factory-startup -P pipeline/charsys/tests/reuse_test.py -- <version_dir> <out_dir>

Proves, by actually reopening and using the saved files:
  T1 the master reopens with its component collections, metadata, embedded spec, rig, weights, shape keys and
     facial controls, and the facial controls deform the face;
  T2 the reopened rig deforms the body (pose test on the master, not saved);
  T3 an episode shot links the master, poses the body and the face through the override, saves, and after a fresh
     reopen the pose and expression are still there and render;
  T4 a second shot (another episode) reuses the same version with a different pose; both stay independent;
  T5 edits to linked (master) data inside a shot are not saved into the shot and never reach the master;
  T6 the glTF export imports into an empty scene with skeleton, skin and morph targets, and deforms when posed;
  T7 the master file is byte-identical (sha256) before and after all of this.
Writes <out_dir>/reuse_test.json and renders shot_A.png / shot_B.png."""
import hashlib
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import episode as EP  # noqa: E402
import spec as S  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
VD, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)
MAN = json.load(open(os.path.join(VD, "manifest.json")))
CID = MAN["character_id"]
MASTER = os.path.join(VD, f"{CID}_master.blend")
COMPS = json.load(open(os.path.join(VD, "components.json")))
R = {"version_dir": VD, "version": MAN["version"], "blender": bpy.app.version_string, "tests": {}}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def check(test, name, ok, detail=None):
    R["tests"].setdefault(test, {"pass": True, "checks": []})
    R["tests"][test]["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
    if not ok:
        R["tests"][test]["pass"] = False
    print(f"[reuse_test] {test} {'PASS' if ok else 'FAIL'} {name} {'' if detail is None else detail}", flush=True)


def eval_co(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    return (np.array(ob.matrix_world) @ np.c_[co.reshape(-1, 3), np.ones(len(co) // 3)].T).T[:, :3]


def obj(name):
    return next(o for o in bpy.data.objects if o.name == name and (o.library is None or o.override_library is None))


def render(path, target_z=0.55):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 16
    sc.cycles.device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y = 240, 400
    sc.render.film_transparent = True
    cam = bpy.data.objects.new("test_cam", bpy.data.cameras.new("test_cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.35
    cam.location = (1.6, -3.2, 0.9)
    d = Vector((0, 0, target_z)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.objects.new("test_sun", bpy.data.lights.new("test_sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(sun)
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.5, 0.5, 0.5)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    px = np.array(bpy.data.images.load(path).pixels[:]).reshape(-1, 4)
    return float((px[:, 3] > 0.5).mean())


sha_before = sha(MASTER)
check("T7_master_unchanged", "master matches manifest before tests", sha_before == MAN["files"][f"{CID}_master.blend"]["sha256"])

# ---------------------------------------------------------------- T1 reopen master
bpy.ops.wm.open_mainfile(filepath=MASTER)
root = bpy.data.collections.get(CID)
check("T1_reopen_master", "root collection present", root is not None)
subs = sorted(c.name[len(CID) + 1:] for c in root.children)
check("T1_reopen_master", "component collections", set(subs) >= {"body", "face", "hair", "clothing", "accessories", "rig", "landmarks"}, subs)
check("T1_reopen_master", "metadata stamped", root.get("ps_character_id") == CID and root.get("ps_spec_sha256") == MAN["spec_sha256"],
      {k: root.get(k) for k in ("ps_character_id", "ps_spec_version", "ps_build", "ps_role")})
txt = bpy.data.texts.get("ps_character_spec.json")
check("T1_reopen_master", "embedded spec matches manifest hash", txt is not None and S.sha256(json.loads(txt.as_string())) == MAN["spec_sha256"])
check("T1_reopen_master", "asset marked", root.asset_data is not None)
for comp, objs in COMPS.items():
    have = sorted(o.name for o in bpy.data.collections[f"{CID}.{comp}"].objects)
    check("T1_reopen_master", f"component {comp}: objects as published", have == sorted(o["name"] for o in objs), len(have))
rig = next(o for o in root.all_objects if o.type == "ARMATURE")
EXP_BONES = (MAN["rig"]["rigify_bones"], MAN["rig"]["deform_bones"])  # from the version's own manifest (not boy constants)
check("T1_reopen_master", "rig bones", (len(rig.data.bones), sum(b.use_deform for b in rig.data.bones)) == EXP_BONES,
      [len(rig.data.bones), sum(b.use_deform for b in rig.data.bones)])
deform = {b.name for b in rig.data.bones if b.use_deform}
unweighted = 0
for o in root.all_objects:
    if o.type != "MESH" or o.name.startswith("WGT-"):
        continue
    gi = {g.index for g in o.vertex_groups if g.name in deform}
    unweighted += sum(1 for v in o.data.vertices if sum(g.weight for g in v.groups if g.group in gi) <= 0)
check("T1_reopen_master", "every vertex weighted to a deform bone", unweighted == 0, unweighted)
keys = sorted({k.name for o in root.all_objects if o.type == "MESH" and o.data.shape_keys for k in o.data.shape_keys.key_blocks} - {"Basis"})
check("T1_reopen_master", "expression shape keys", keys == sorted(["Blink", "BrowDown", "Smile", "JawOpen"]), keys)
face_props = sorted(k for k in rig.keys() if k.startswith("face_"))
check("T1_reopen_master", "facial controls on rig", len(face_props) == 4, face_props)
lid, mouth = obj("lid_upper.L"), obj("mouth")
lid0, mouth0 = eval_co(lid), eval_co(mouth)
EP.apply_pose(rig, face={"face_Blink": 1.0, "face_Smile": 1.0})
dl, dm = float(np.abs(eval_co(lid) - lid0).max()), float(np.abs(eval_co(mouth) - mouth0).max())
check("T1_reopen_master", "facial controls deform lids and mouth", dl > 0.005 and dm > 0.001, {"lid_mm": round(dl * 1000, 1), "mouth_mm": round(dm * 1000, 1)})
rig["face_Blink"], rig["face_Smile"] = 0.0, 0.0

# ---------------------------------------------------------------- T2 pose the reopened rig
sleeve = obj("hoodie_sleeve.L")
s0 = eval_co(sleeve)
EP.apply_pose(rig, {"upper_arm_fk.L": (math.cos(0.4), math.sin(0.4), 0, 0)})
ds = float(np.linalg.norm(eval_co(sleeve) - s0, axis=1).max())
check("T2_pose_master", "sleeve follows the arm control", ds > 0.05, round(ds, 3))
bpy.ops.wm.read_factory_settings(use_empty=True)  # discard: the master is never saved by tests


# ---------------------------------------------------------------- T3/T4/T5 episodes
def make_shot(path, pose, face, episode):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ov, rig, info = EP.link_character(VD)
    EP.apply_pose(rig, pose, face)
    bpy.context.scene["ps_episode"] = episode
    # T5: try to edit master data from inside the shot (linked mesh vertex and linked material colour)
    m = next(o for o in ov.all_objects if o.name == "head")
    m.data.vertices[0].co.z += 0.05
    mat = m.data.materials[0]
    mat.diffuse_color = (1, 0, 0, 1)
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=True)
    return info


A, B = os.path.join(OUT, "episodes", "ep_test_A", "shot_010.blend"), os.path.join(OUT, "episodes", "ep_test_B", "shot_020.blend")
arms_down = {"upper_arm_fk.L": [math.cos(math.radians(20.5)), 0, math.sin(math.radians(20.5)), 0],
             "upper_arm_fk.R": [math.cos(math.radians(-20.5)), 0, math.sin(math.radians(-20.5)), 0]}
pose_A = dict(arms_down, **{"head": [math.cos(math.radians(12)), 0, 0, math.sin(math.radians(12))]})
pose_B = {"upper_arm_fk.L": [math.cos(math.radians(-35)), 0, math.sin(math.radians(-35)), 0],
          "thigh_fk.R": [math.cos(math.radians(-20)), math.sin(math.radians(-20)), 0, 0]}
make_shot(A, pose_A, {"face_Smile": 1.0, "face_JawOpen": 0.6}, "ep_test_A")
make_shot(B, pose_B, {"face_Blink": 1.0}, "ep_test_B")
check("T3_episode_shot", "shot files saved outside the store", os.path.exists(A) and os.path.exists(B))
for name, path, pose, face in (("A", A, pose_A, {"face_Smile": 1.0, "face_JawOpen": 0.6}), ("B", B, pose_B, {"face_Blink": 1.0})):
    test = "T3_episode_shot" if name == "A" else "T4_second_episode"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=path)
    libs = [bpy.path.abspath(l.filepath) for l in bpy.data.libraries]
    check(test, "links the store master (not a copy)", len(libs) == 1 and os.path.samefile(libs[0], MASTER), [l.filepath for l in bpy.data.libraries])
    local_meshes = [m.name for m in bpy.data.meshes if m.library is None and not m.override_library]
    check(test, "no master geometry copied into the shot", not [n for n in local_meshes if not n.startswith("WGT")], local_meshes[:5])
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.override_library)
    got = {b: [round(x, 4) for x in rig.pose.bones[b].rotation_quaternion] for b in pose}
    check(test, "pose persisted after reopen", all(np.allclose(got[b], pose[b], atol=1e-4) for b in pose), got)
    ikfk = [pb["IK_FK"] for pb in rig.pose.bones if "IK_FK" in pb.keys()]
    check(test, "FK switch persisted", ikfk and all(v == 1.0 for v in ikfk), ikfk)
    check(test, "facial controls persisted", all(abs(rig[k] - v) < 1e-6 for k, v in face.items()), {k: rig[k] for k in face})
    other = {"face_Blink": 0.0} if name == "A" else {"face_Smile": 0.0}
    check(test, "other shot's expression not present (independent shots)", all(abs(rig[k] - v) < 1e-6 for k, v in other.items()))
    head = next(o for o in bpy.data.objects if o.name == "head" and o.override_library)
    check("T5_isolation", f"shot {name}: mesh data is still the linked master data", head.data.library is not None,
          {"mesh_library": head.data.library.filepath if head.data.library else None})
    for part, thr in (("hoodie_sleeve.L", 0.03), ("mouth" if name == "A" else "lid_upper.L", 0.001)):
        ob = next(o for o in bpy.data.objects if o.name == part and o.override_library)
        rest = np.array([ob.matrix_world @ v.co for v in ob.data.vertices])
        d = float(np.linalg.norm(eval_co(ob) - rest, axis=1).max())
        check(test, f"{part} deformed by the saved pose/expression after reopen", d > thr, round(d, 4))
    fill = render(os.path.join(OUT, f"shot_{name}.png"))
    check(test, "renders", fill > 0.03, round(fill, 3))
# The master's own value of the edited vertex, to prove the in-shot edit did not persist anywhere.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=MASTER)
z_master = bpy.data.objects["head"].data.vertices[0].co.z
colour = tuple(bpy.data.objects["head"].data.materials[0].diffuse_color)
bpy.ops.wm.open_mainfile(filepath=A)
head = next(o for o in bpy.data.objects if o.name == "head" and o.override_library)
check("T5_isolation", "linked vertex in shot equals master value", abs(head.data.vertices[0].co.z - z_master) < 1e-9,
      {"master_z": round(z_master, 6), "shot_z": round(head.data.vertices[0].co.z, 6)})
check("T5_isolation", "master material unchanged by shot edit", colour != (1.0, 0.0, 0.0, 1.0), [round(c, 3) for c in colour])

# ---------------------------------------------------------------- T6 glTF reuse
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(VD, f"{CID}.glb"))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"]
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
morphs = sorted({k.name for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys for k in o.data.shape_keys.key_blocks} - {"Basis"})
check("T6_gltf_reuse", "skeleton", len(arm) == 1 and len(arm[0].data.bones) == EXP_BONES[1], len(arm[0].data.bones) if arm else 0)
check("T6_gltf_reuse", "skinned meshes", len(skinned) >= 50, len(skinned))
check("T6_gltf_reuse", "morph targets", morphs == sorted(["Blink", "BrowDown", "Smile", "JawOpen"]), morphs)
sl = next(o for o in skinned if o.name.startswith("hoodie_sleeve.L"))
s0 = eval_co(sl)
pb = arm[0].pose.bones.get("DEF-upper_arm.L")
pb.rotation_mode = "QUATERNION"
pb.rotation_quaternion = (math.cos(0.4), math.sin(0.4), 0, 0)
bpy.context.view_layer.update()
ds = float(np.linalg.norm(eval_co(sl) - s0, axis=1).max())
check("T6_gltf_reuse", "imported skin deforms when posed", ds > 0.05, round(ds, 3))

sha_after = sha(MASTER)
check("T7_master_unchanged", "master byte-identical after all tests", sha_after == sha_before, sha_after[:16])
R["pass"] = all(t["pass"] for t in R["tests"].values())
json.dump(R, open(os.path.join(OUT, "reuse_test.json"), "w"), indent=1)
print(f"[reuse_test] {'ALL PASS' if R['pass'] else 'FAILURES'} -> {os.path.join(OUT, 'reuse_test.json')}")
