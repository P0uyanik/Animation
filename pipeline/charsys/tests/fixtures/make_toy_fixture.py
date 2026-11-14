"""ENGINEERING TEST FIXTURE (not a production character): a small procedural toy with a skeleton that differs from
the boy in every way the engine adapter could depend on: bone names (pelvis/torso_lo/skull/arm_up_lf/..._rt),
hierarchy (a deform helper `belly` between torso bones, a 2-bone `tail_1/tail_2`, no fingers, no lids),
proportions (0.62 m, head 40% of the height) and morph names ("Squint", "Puff").

    blender -b --factory-startup -P pipeline/charsys/tests/fixtures/make_toy_fixture.py -- <out.blend>"""
import math
import sys

import bpy
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
C = bpy.data.collections.new("toy_fixture")
bpy.context.scene.collection.children.link(C)
C["ps_character_id"] = "toy_fixture"
arm = bpy.data.armatures.new("toy_rig")
rig = bpy.data.objects.new("toy_rig", arm)
C.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
B = {}


def bone(name, head, tail, parent=None, deform=True):
    b = arm.edit_bones.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    if parent:
        b.parent = B[parent]
    b.use_deform = deform
    B[name] = b


bone("root_ctrl", (0, 0, 0), (0, 0.1, 0), deform=False)  # non-deform control: must not be exported
bone("pelvis", (0, 0, 0.20), (0, 0, 0.26), "root_ctrl")
bone("torso_lo", (0, 0, 0.26), (0, 0, 0.30), "pelvis")
bone("belly", (0, -0.02, 0.28), (0, -0.06, 0.28), "torso_lo")  # deform helper (preserved, no role)
bone("torso_hi", (0, 0, 0.30), (0, 0, 0.36), "torso_lo")
bone("neck_a", (0, 0, 0.36), (0, 0, 0.39), "torso_hi")
bone("skull", (0, 0, 0.39), (0, 0, 0.60), "neck_a")
for s, sx in (("lf", 1), ("rt", -1)):
    bone(f"eye_{s}", (sx * 0.045, -0.105, 0.50), (sx * 0.045, -0.13, 0.50), "skull")
    bone(f"arm_up_{s}", (sx * 0.07, 0, 0.35), (sx * 0.13, 0, 0.29), "torso_hi")
    bone(f"arm_lo_{s}", (sx * 0.13, 0, 0.29), (sx * 0.18, 0, 0.23), f"arm_up_{s}")
    bone(f"paw_{s}", (sx * 0.18, 0, 0.23), (sx * 0.20, 0, 0.20), f"arm_lo_{s}")
    bone(f"leg_up_{s}", (sx * 0.05, 0, 0.20), (sx * 0.05, 0, 0.11), "pelvis")
    bone(f"leg_lo_{s}", (sx * 0.05, 0, 0.11), (sx * 0.05, 0, 0.03), f"leg_up_{s}")
    bone(f"foot_{s}", (sx * 0.05, 0, 0.03), (sx * 0.05, -0.05, 0.0), f"leg_lo_{s}")
bone("tail_1", (0, 0.06, 0.22), (0, 0.12, 0.25), "pelvis")
bone("tail_2", (0, 0.12, 0.25), (0, 0.17, 0.32), "tail_1")
bpy.ops.object.mode_set(mode="OBJECT")


def blob(name, centre, radii, segs=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, location=centre)
    o = bpy.context.object
    o.name = name
    o.scale = radii
    bpy.ops.object.transform_apply(scale=True)
    for c in o.users_collection:
        c.objects.unlink(o)
    C.objects.link(o)
    return o


parts = [blob("t_head", (0, 0, 0.49), (0.12, 0.11, 0.11), 32), blob("t_body", (0, 0, 0.29), (0.08, 0.07, 0.09)),
         blob("t_tail", (0, 0.13, 0.27), (0.025, 0.06, 0.05), 16)]
for s, sx in (("L", 1), ("R", -1)):
    parts += [blob(f"t_arm.{s}", (sx * 0.13, 0, 0.29), (0.07, 0.03, 0.06), 16),
              blob(f"t_leg.{s}", (sx * 0.05, 0, 0.11), (0.035, 0.035, 0.10), 16)]
mat = bpy.data.materials.new("M_toy_felt")
mat.diffuse_color = (0.55, 0.35, 0.6, 1)
for p in parts:
    p.data.materials.append(mat)
bpy.ops.object.select_all(action="DESELECT")
for p in parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object
body.name = "toy_body"
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
# morphs with fixture-specific names (no engine expression has these names)
body.shape_key_add(name="Basis")
for kname, f in (("Squint", lambda v: v.co + Vector((0, 0, -0.01)) if v.co.z > 0.45 and v.co.y < -0.08 else v.co),
                 ("Puff", lambda v: v.co + Vector((v.co.x * 0.08, 0, 0)) if 0.40 < v.co.z < 0.50 else v.co)):
    k = body.shape_key_add(name=kname)
    k.value = 0.0
    for i, v in enumerate(body.data.vertices):
        k.data[i].co = f(v)
bpy.ops.wm.save_as_mainfile(filepath=out)
unweighted = sum(1 for v in body.data.vertices if not v.groups)
print(f"[toy_fixture] {len(arm.bones)} bones, {len(body.data.vertices)} vertices, unweighted {unweighted} -> {out}")
