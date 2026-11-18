"""Small geometry helpers shared by the T-068 garment types (sneakers, backpack, patch pockets, decals).
No character data: every size comes from the caller."""
import math

import bpy
from mathutils import Vector


def sgnpow(v, e):
    return math.copysign(abs(v) ** e, v)


def solidify(ob, thickness, offset=1.0):
    """Apply a SOLIDIFY of ``thickness`` (offset 1 = grow along the normals, -1 = inwards)."""
    if thickness <= 0:
        return ob
    mod = ob.modifiers.new("garment_thickness", "SOLIDIFY")
    mod.thickness, mod.offset = thickness, offset
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.select_set(False)
    return ob


def superellipsoid(G, C, name, centre, radii, n, segs=40, rings=24):
    """Closed superellipsoid (exponent ``n``: 2 = ellipsoid, larger = boxier) with poles on Z."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    e = 2.0 / n
    verts = []
    for j in range(1, rings):
        phi = -0.5 * math.pi + math.pi * j / rings
        cp, sp = math.cos(phi), math.sin(phi)
        for i in range(segs):
            th = 2 * math.pi * i / segs
            verts.append((cx + rx * sgnpow(cp, e) * sgnpow(math.cos(th), e),
                          cy + ry * sgnpow(cp, e) * sgnpow(math.sin(th), e),
                          cz + rz * sgnpow(sp, e)))
    verts.append((cx, cy, cz - rz))
    verts.append((cx, cy, cz + rz))
    bottom, top = len(verts) - 2, len(verts) - 1
    faces = []
    for j in range(rings - 2):
        a0, b0 = j * segs, (j + 1) * segs
        for i in range(segs):
            k = (i + 1) % segs
            faces.append((a0 + i, a0 + k, b0 + k, b0 + i))
    last = (rings - 2) * segs
    for i in range(segs):
        k = (i + 1) % segs
        faces.append((bottom, k, i))
        faces.append((top, last + i, last + k))
    return G.new_object(name, verts, faces, C)


def catmull_rom(points, samples_per_span=8, closed=False):
    """Smooth curve through ``points`` (Vectors), uniform Catmull-Rom."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    if n < 3:
        return pts
    out = []
    spans = n if closed else n - 1
    for i in range(spans):
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1, p2 = pts[i % n], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        for k in range(samples_per_span):
            t = k / samples_per_span
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(pts[-1])
    return out


def resample(points, count):
    """``count`` points equally spaced by arc length along an open polyline."""
    pts = [Vector(p) for p in points]
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    if total <= 1e-9:
        return [pts[0].copy() for _ in range(count)]
    out, j = [], 0
    for k in range(count):
        s = total * k / (count - 1)
        while j < len(pts) - 2 and lengths[j + 1] < s:
            j += 1
        seg = max(lengths[j + 1] - lengths[j], 1e-12)
        out.append(pts[j].lerp(pts[j + 1], (s - lengths[j]) / seg))
    return out


def ribbon(G, C, name, points, normals, width, thickness, round_share=0.45, profile=12, caps=True):
    """A flat strap along ``points`` lying on a surface with the given outward ``normals``: a rounded-rectangle
    cross-section ``width`` wide (across the path, in the surface) and ``thickness`` deep (along the normal). The path
    is the centre of the strap. ``round_share`` rounds the long edges (0 = box, 1 = ellipse)."""
    pts = [Vector(p) for p in points]
    nrm = [Vector(n).normalized() for n in normals]
    n = len(pts)
    exp = 2.0 / (2.0 + 8.0 * (1.0 - max(0.0, min(1.0, round_share))))  # superellipse exponent of the section
    ring = []
    for k in range(profile):
        a = 2 * math.pi * k / profile
        ring.append((sgnpow(math.cos(a), exp), sgnpow(math.sin(a), exp)))
    verts, faces = [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        t = t.normalized() if t.length > 1e-9 else Vector((0, 0, 1))
        nn = (nrm[i] - t * nrm[i].dot(t))
        nn = nn.normalized() if nn.length > 1e-9 else nrm[i]
        b = t.cross(nn).normalized()
        for cx, cy in ring:
            verts.append(tuple(p + b * (cx * width * 0.5) + nn * (cy * thickness * 0.5)))
    for i in range(n - 1):
        a0, b0 = i * profile, (i + 1) * profile
        for k in range(profile):
            j = (k + 1) % profile
            faces.append((a0 + k, a0 + j, b0 + j, b0 + k))
    if caps:
        faces.append(tuple(range(profile - 1, -1, -1)))
        base = (n - 1) * profile
        faces.append(tuple(base + k for k in range(profile)))
    return G.new_object(name, verts, faces, C)


def outer_hit(bvhs, point, direction, reach=0.4):
    """Outermost surface along a line: cast from ``point + direction * reach`` back along ``-direction`` against
    every BVH and return the first (outermost) (location, normal) or (None, None)."""
    d = Vector(direction).normalized()
    origin = Vector(point) + d * reach
    best, best_n, best_dist = None, None, None
    for bvh in bvhs:
        loc, normal, _, dist = bvh.ray_cast(origin, -d, reach * 2.0)
        if loc is not None and (best_dist is None or dist < best_dist):
            best, best_n, best_dist = loc, normal, dist
    if best is not None and best_n.dot(d) < 0:
        best_n = -best_n
    return best, best_n


def layer_top(bvhs, start, direction, max_gap, reach=0.12, first_gap=0.08):
    """Outer surface of the stack of layers lying directly on ``start`` (a point on the body) along ``direction``:
    step outwards from hit to hit while consecutive surfaces are at most ``max_gap`` apart (a solidified panel, a
    garment over another); a larger gap (e.g. an arm beyond the torso) ends the stack. The first surface may be up
    to ``first_gap`` from the body (a loose garment's ease). Returns (point, normal)."""
    d = Vector(direction).normalized()
    pos = Vector(start) + d * 1e-5
    last, last_n, travelled = Vector(start), d.copy(), 0.0
    while travelled < reach:
        best, best_n, best_dist = None, None, None
        for bvh in bvhs:
            loc, normal, _, dist = bvh.ray_cast(pos, d, reach)
            if loc is not None and (best_dist is None or dist < best_dist):
                best, best_n, best_dist = loc, normal, dist
        if best is None or (best - last).length > (first_gap if travelled == 0.0 else max_gap):
            break
        last, last_n = best, (best_n if best_n.dot(d) > 0 else -best_n)
        travelled += best_dist
        pos = best + d * 1e-5
    return last, last_n


def store_body_vertices(ob, body, allowed):
    """Write the ``ps_body_vertex`` POINT attribute (generator.bind_to_body copies that body vertex's weights): for
    every vertex the nearest rest-pose body vertex among the indices in ``allowed``."""
    from mathutils.kdtree import KDTree
    allowed = sorted(allowed)
    tree = KDTree(len(allowed))
    for i in allowed:
        tree.insert(body.matrix_world @ body.data.vertices[i].co, i)
    tree.balance()
    attr = ob.data.attributes.get("ps_body_vertex") or ob.data.attributes.new("ps_body_vertex", "INT", "POINT")
    for v, datum in zip(ob.data.vertices, attr.data):
        datum.value = tree.find(ob.matrix_world @ v.co)[1]
    return ob
