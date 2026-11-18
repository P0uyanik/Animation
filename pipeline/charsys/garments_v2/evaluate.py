"""``garment/2`` evaluation helpers (T-093; Blender only, character-agnostic): the reach pose and the torso-garment
flare measure used by the corrective tests and the evidence renders.

flare(item) = how far the item's pieces stand off the torso: for every vertex of the item's main piece, the distance
from its posed (evaluated: shape keys, armature, collision) position to the nearest posed torso skin (body faces
whose vertices are carried mainly by non-arm bones). Reported as max / p99 / p95 in metres; "before" = correctives
muted, "after" = correctives driven by the pose."""
import math

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree


def set_fk(rig):
    for pb in rig.pose.bones:
        if "IK_FK" in pb.keys():
            pb["IK_FK"] = 1.0


def rotate_upper_arms(rig, deg, axis="X", sides=("L", "R"), mirror=False, bone="upper_arm_fk.{side}"):
    """Rotates the FK upper arms about a world axis through the shoulder (the reach pose: axis X, deg < 0 swings the
    arms forward). ``mirror`` negates the angle on the right side (sideways poses about Y)."""
    bpy.context.view_layer.objects.active = rig
    set_fk(rig)
    bpy.ops.object.mode_set(mode="POSE")
    for s in sides:
        pb = rig.pose.bones.get(bone.format(side=s))
        if pb is None:
            raise ValueError(f"rig has no {bone.format(side=s)}")
        a = -deg if (mirror and s == "R") else deg
        hw = rig.matrix_world @ pb.head
        rm = Matrix.Translation(hw) @ Matrix.Rotation(math.radians(a), 4, axis) @ Matrix.Translation(-hw)
        pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def rest(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def corrective_keys(objects, prefix="corrective."):
    return [(ob, k) for ob in objects if ob.type == "MESH" and ob.data.shape_keys
            for k in ob.data.shape_keys.key_blocks if k.name.startswith(prefix)]


def mute(objects, muted, prefix="corrective."):
    for _, k in corrective_keys(objects, prefix):
        k.mute = muted
    bpy.context.view_layer.update()


def _evaluated_points(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m = e.to_mesh()
    pts = [e.matrix_world @ v.co for v in m.vertices]
    e.to_mesh_clear()
    return pts


def torso_bvh(body, arm_prefixes=("DEF-upper_arm", "DEF-forearm", "DEF-hand", "DEF-f_", "DEF-thumb", "DEF-palm")):
    """BVH of the posed torso skin: evaluated body faces whose vertices are all carried mainly by non-arm bones. The
    garment mask hides covered faces in the evaluated body, so the collision proxy (same mesh, unmasked) is used when
    present."""
    src = bpy.data.objects.get(f"garment.collider.{body.name}") or body
    names = {g.index: g.name for g in body.vertex_groups}
    torso = set()
    for v in body.data.vertices:
        tot = arm = 0.0
        for g in v.groups:
            n = names.get(g.group, "")
            if n.startswith("ps_"):
                continue
            tot += g.weight
            arm += g.weight if n.startswith(arm_prefixes) else 0.0
        if tot > 0 and arm / tot < 0.5:
            torso.add(v.index)
    dg = bpy.context.evaluated_depsgraph_get()
    e = src.evaluated_get(dg)
    m = e.to_mesh()
    pts = [e.matrix_world @ v.co for v in m.vertices]
    faces = [tuple(p.vertices) for p in m.polygons if all(i in torso for i in p.vertices)] \
        if len(m.vertices) == len(body.data.vertices) else [tuple(p.vertices) for p in m.polygons]
    e.to_mesh_clear()
    return BVHTree.FromPolygons(pts, faces, all_triangles=False)


def flare(body, piece):
    """{max, p99, p95, mean} distance (m) of the evaluated piece's vertices to the posed torso skin."""
    bvh = torso_bvh(body)
    d = sorted(bvh.find_nearest(p)[3] for p in _evaluated_points(piece))
    n = len(d)
    return {"max": round(d[-1], 5), "p99": round(d[int(0.99 * (n - 1))], 5), "p95": round(d[int(0.95 * (n - 1))], 5),
            "mean": round(sum(d) / n, 5), "vertices": n}


def key_values(objects, prefix="corrective."):
    """Evaluated driver values of the corrective keys (name -> value)."""
    bpy.context.view_layer.update()
    return {f"{ob.name}:{k.name}": round(k.value, 4) for ob, k in corrective_keys(objects, prefix)}


def penetration(outer, inner_pieces, reach=0.03):
    """How far the evaluated ``outer`` piece sinks into the evaluated inner layer (``inner_pieces``, e.g. the blouse
    under a vest): vertices of ``outer`` on the inner side of the nearest inner surface, with their depth (m)."""
    verts, faces = [], []
    for ob in inner_pieces:
        pts = _evaluated_points(ob)
        dg = bpy.context.evaluated_depsgraph_get()
        e = ob.evaluated_get(dg)
        m = e.to_mesh()
        base = len(verts)
        verts += pts
        faces += [tuple(base + i for i in p.vertices) for p in m.polygons]
        e.to_mesh_clear()
    bvh = BVHTree.FromPolygons(verts, faces, all_triangles=False)
    depths = []
    for p in _evaluated_points(outer):
        loc, nrm, _, _ = bvh.find_nearest(p, reach)
        if loc is not None:
            side = (p - loc).dot(nrm.normalized())
            if side < 0:
                depths.append(-side)
    depths.sort()
    n = len(depths)
    return {"inside": n, "max_depth": round(depths[-1], 5) if n else 0.0,
            "p95_depth": round(depths[int(0.95 * (n - 1))], 5) if n else 0.0}
