"""Shared body helpers (T-043): the generic helpers that shared code used to import from the frozen legacy builder
body_v6.py. Copied verbatim (body_v6.py is frozen and keeps its own copies, which the legacy boy path still uses);
new and shared code imports them from here. Released behaviour: changing any of these changes every character that
uses them, so a behaviour change needs a new function (and a new generator version), never an edit.
"""
import bpy

import geom as G


def face_y(head, x, z):
    p, _ = G.surface_point(head, (x, -1.0, z), (0, 1, 0))
    return p.y if p is not None else -0.14


def bind_to_nearest_bone(ob, rig, allowed):
    """Weights each unweighted vertex 1.0 to the nearest deform bone segment the object may follow."""
    bones = [b for b in rig.data.bones if b.use_deform and (allowed is None or allowed(b.name))]
    segs = [(b.name, rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in bones]
    groups = {g.name: g for g in ob.vertex_groups}
    left = 0
    for v in ob.data.vertices:
        if sum(g.weight for g in v.groups) >= 1e-4:
            continue
        p = ob.matrix_world @ v.co
        best, bd = None, 1e9
        for name, h, t in segs:
            d = t - h
            u = max(0.0, min(1.0, (p - h).dot(d) / max(d.length_squared, 1e-12)))
            dist = (p - (h + d * u)).length
            if dist < bd:
                best, bd = name, dist
        if best is None:
            left += 1
            continue
        g = groups.get(best) or ob.vertex_groups.new(name=best)
        groups[best] = g
        g.add([v.index], 1.0, "REPLACE")
    return left


def cleanup_weights(ob):
    import numpy as np
    me = ob.data
    n = len(me.vertices)
    co = np.array([v.co[:] for v in me.vertices])
    tot = np.array([sum(g.weight for g in v.groups) for v in me.vertices])
    bad = np.nonzero(tot < 1e-4)[0]
    good = np.nonzero(tot >= 1e-4)[0]
    before = len(bad)
    if before and len(good):
        groups = {g.index: g for g in ob.vertex_groups}
        for i in bad:
            j = good[np.argmin(np.sum((co[good] - co[i]) ** 2, axis=1))]
            for g in me.vertices[j].groups:
                groups[g.group].add([int(i)], g.weight, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    after = sum(1 for v in me.vertices if sum(g.weight for g in v.groups) < 1e-4)
    return before, after
