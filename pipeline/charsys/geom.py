"""Geometry, material and fur helpers for the automated boy_yellow_hoodie pilot (runs inside Blender).
Blender coordinates: metres, +Z up, the character faces -Y, his left is +X."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


# ----------------------------------------------------------------------------------------------- mesh building
def new_object(name, verts, faces, collection, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def superellipse_ring(cx, cy, z, rx, yf, yb, n, seg):
    """Ring around (cx, cy) at height z; yf = extent to the front (-Y), yb = to the back (+Y)."""
    pts = []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        c, s = math.cos(t), math.sin(t)
        x = cx + rx * math.copysign(abs(c) ** (2 / n), c)
        y = cy + (yb if s > 0 else yf) * math.copysign(abs(s) ** (2 / n), s)
        pts.append((x, y, z))
    return pts


def loft(name, rings, collection, cap_bottom=True, cap_top=True, smooth=True):
    """rings: list of point lists (same length), bottom to top. Quad strips plus fan caps."""
    seg = len(rings[0])
    verts = [p for r in rings for p in r]
    faces = []
    for k in range(len(rings) - 1):
        a, b = k * seg, (k + 1) * seg
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((a + i, a + j, b + j, b + i))
    if cap_bottom:
        c = np.mean(np.array(rings[0]), axis=0)
        verts.append(tuple(c))
        ci = len(verts) - 1
        faces += [(ci, (i + 1) % seg, i) for i in range(seg)]
    if cap_top:
        c = np.mean(np.array(rings[-1]), axis=0)
        verts.append(tuple(c))
        ci = len(verts) - 1
        base = (len(rings) - 1) * seg
        faces += [(ci, base + i, base + (i + 1) % seg) for i in range(seg)]
    return new_object(name, verts, faces, collection, smooth)


def interp_profile(profile, z):
    """profile: sorted list of (z, values...) -> linearly interpolated values at z."""
    zs = [p[0] for p in profile]
    z = min(max(z, zs[0]), zs[-1])
    for k in range(len(profile) - 1):
        if zs[k] <= z <= zs[k + 1]:
            t = (z - zs[k]) / max(1e-9, zs[k + 1] - zs[k])
            t = t * t * (3 - 2 * t)  # smooth between keys
            return [a + (b - a) * t for a, b in zip(profile[k][1:], profile[k + 1][1:])]
    return list(profile[-1][1:])


def profile_loft(name, profile, collection, n=2.4, seg=48, steps=40, **kw):
    """profile rows: (z, cx, cy, rx, yf, yb)."""
    z0, z1 = profile[0][0], profile[-1][0]
    rings = []
    for k in range(steps + 1):
        z = z0 + (z1 - z0) * k / steps
        cx, cy, rx, yf, yb = interp_profile(profile, z)
        rings.append(superellipse_ring(cx, cy, z, max(rx, 1e-4), max(yf, 1e-4), max(yb, 1e-4), n, seg))
    return loft(name, rings, collection, **kw)


def frames_along(points, up_hint):
    """Parallel-transported frames (T, N, B) along a polyline; N starts as the component of up_hint ⟂ T."""
    P = [Vector(p) for p in points]
    T = []
    for i in range(len(P)):
        a, b = P[max(i - 1, 0)], P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    N0 = Vector(up_hint) - T[0] * T[0].dot(Vector(up_hint))
    if N0.length < 1e-6:
        N0 = T[0].orthogonal()
    N = [N0.normalized()]
    for i in range(1, len(P)):
        n = N[-1] - T[i] * T[i].dot(N[-1])
        N.append(n.normalized() if n.length > 1e-8 else N[-1])
    B = [t.cross(n) for t, n in zip(T, N)]
    return P, T, N, B


def bezier(p0, p1, p2, count):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2 for t in (i / (count - 1) for i in range(count))]


def tube(name, points, widths, thicks, collection, up_hint=(0, 0, 1), n=2.0, seg=16, cap_start="round",
         cap_end="round", smooth=True, twist=0.0):
    """Generalised tube: cross-section superellipse, width along B (side), thickness along N (up_hint side).
    caps: 'round' (rounded dome), 'point' (single tip vertex), 'flat', or None (open)."""
    P, T, N, B = frames_along(points, up_hint)
    rings = []
    for i, p in enumerate(P):
        a = twist * i / max(1, len(P) - 1)
        nn = N[i] * math.cos(a) + B[i] * math.sin(a)
        bb = T[i].cross(nn)
        w, h = widths[i], thicks[i]
        ring = []
        for k in range(seg):
            t = 2 * math.pi * k / seg
            c, s = math.cos(t), math.sin(t)
            x = math.copysign(abs(c) ** (2 / n), c) * w
            y = math.copysign(abs(s) ** (2 / n), s) * h
            ring.append(tuple(p + bb * x + nn * y))
        rings.append(ring)

    def dome(ring_list, end, direction, kind):
        if kind != "round":
            return ring_list
        base = ring_list[end]
        c = np.mean(np.array(base), axis=0)
        r = float(np.mean(np.linalg.norm(np.array(base) - c, axis=1)))
        extra = []
        for k in (1, 2, 3):
            ang = k * math.pi / 8
            f = math.cos(ang)
            off = Vector(direction) * r * 0.7 * math.sin(ang)
            extra.append([tuple(Vector(c) + (Vector(q) - Vector(c)) * f + off) for q in base])
        return (list(reversed(extra)) + ring_list) if end == 0 else (ring_list + extra)

    rings = dome(rings, 0, -T[0], cap_start)
    rings = dome(rings, len(rings) - 1, T[-1], cap_end)
    ob = loft(name, rings, collection, cap_bottom=cap_start is not None, cap_top=cap_end is not None, smooth=smooth)
    if cap_end == "point":
        tip = P[-1] + T[-1] * 0.25 * widths[-1]
        ob.data.vertices[-1].co = tip
    return ob


def brush(ob, center, radius, offset, normal_mode=False, power=2.0):
    """Sculpt-like grab/inflate brush on an object's mesh (world space). offset: vector, or a scalar along
    vertex normals when normal_mode."""
    me = ob.data
    mw, mi = ob.matrix_world, ob.matrix_world.inverted()
    c = Vector(center)
    for v in me.vertices:
        w = mw @ v.co
        d = (w - c).length / radius
        if d >= 1:
            continue
        f = (1 - d * d) ** power
        if normal_mode:
            n = (mw.to_3x3() @ v.normal).normalized()
            w = w + n * (offset * f)
        else:
            w = w + Vector(offset) * f
        v.co = mi @ w
    me.update()


def surface_point(ob, origin, direction, max_dist=2.0):
    """First hit of a ray with an object (world space), or None."""
    mi = ob.matrix_world.inverted()
    o = mi @ Vector(origin)
    d = (mi.to_3x3() @ Vector(direction)).normalized()
    ok, loc, nrm, _ = ob.ray_cast(o, d, distance=max_dist)
    if not ok:
        return None, None
    return ob.matrix_world @ loc, (ob.matrix_world.to_3x3() @ nrm).normalized()


_UV_SPHERE_TOPOLOGY = None


def _recorded_uv_sphere_topology(bm, segments, rings):
    """T-158: create_uvsphere returns its faces and edges in a run-dependent order and edge direction (its vertex
    order and face corners are stable), which moves later SUBSURF / bisect results by float ulps. Rebuild the sphere
    with the edge and face order of one recorded run (uv_sphere_topology.json, recorded by
    docs/evaluation/characters/T-158/record_uv_sphere_topology.py), so every build gets that same order. A size
    without a recording keeps the live order."""
    global _UV_SPHERE_TOPOLOGY
    if _UV_SPHERE_TOPOLOGY is None:
        import json
        import os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uv_sphere_topology.json")
        with open(path, encoding="utf-8") as f:
            _UV_SPHERE_TOPOLOGY = json.load(f)["sizes"]
    rec = _UV_SPHERE_TOPOLOGY.get(f"{segments}x{rings}")
    if rec is None:
        print(f"[geom.uv_sphere] no recorded topology for {segments}x{rings}: live (run-dependent) order")
        return bm
    bm.verts.index_update()
    live = sorted(tuple(sorted(v.index for v in f.verts)) for f in bm.faces)
    if len(bm.verts) != rec["vertices"] or live != sorted(tuple(sorted(f)) for f in rec["faces"]):
        raise ValueError(f"uv_sphere {segments}x{rings}: create_uvsphere no longer matches the recorded topology")
    co = [v.co.copy() for v in bm.verts]
    bm.free()
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in co]
    for a, b in rec["edges"]:
        bm.edges.new((vs[a], vs[b]))
    for f in rec["faces"]:
        bm.faces.new([vs[i] for i in f])
    return bm


def uv_sphere(name, center, radius, collection, segments=48, rings=24, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(center)
    bm = _recorded_uv_sphere_topology(bm, segments, rings)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def cut_by_plane(ob, point, normal, keep_positive=True):
    """Removes the part of the mesh on one side of a plane (world space), keeping the cut edge."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    mi = ob.matrix_world.inverted()
    p = mi @ Vector(point)
    nrm = (mi.to_3x3() @ Vector(normal)).normalized()
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    # Verified: keep_positive=True keeps the side the plane normal points to.
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=p, plane_no=nrm, clear_inner=keep_positive, clear_outer=not keep_positive)
    bm.to_mesh(me)
    bm.free()
    me.update()


def add_mod(ob, kind, **props):
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in props.items():
        setattr(m, k, v)
    return m


def apply_mods(ob):
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        if m.type == "ARMATURE":
            continue
        bpy.ops.object.modifier_apply(modifier=m.name)


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def voxel_remesh(ob, voxel, smooth_iter=0):
    m = ob.modifiers.new("remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.use_smooth_shade = True
    if smooth_iter:
        s = ob.modifiers.new("smooth", "SMOOTH")
        s.iterations = smooth_iter
        s.factor = 0.6
    apply_mods(ob)
    ob.data.shade_smooth()


def displace_noise(ob, strength, scale, name="felt", subdiv=1, seed=0):
    if subdiv:
        add_mod(ob, "SUBSURF", levels=subdiv, render_levels=subdiv)
    tex = bpy.data.textures.new(f"{ob.name}_{name}", "CLOUDS")
    tex.noise_scale = scale
    tex.noise_depth = 2
    m = ob.modifiers.new(name, "DISPLACE")
    m.texture = tex
    m.strength = strength
    m.mid_level = 0.5
    m.texture_coords = "GLOBAL"
    return m


# ----------------------------------------------------------------------------------------------- materials
def srgb_to_linear(c):
    c = np.asarray(c, float) / (255.0 if max(c) > 1.0 else 1.0)
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def material(name, base_srgb, roughness=0.8, sheen=0.0, sheen_tint=(1, 1, 1), subsurface=0.0, sss_radius=(1, 0.4, 0.25),
             sss_scale=0.01, coat=0.0, specular=0.3):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*srgb_to_linear(base_srgb), 1)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Specular IOR Level"].default_value = specular
    if sheen:
        p.inputs["Sheen Weight"].default_value = sheen
        p.inputs["Sheen Tint"].default_value = (*sheen_tint, 1)
        p.inputs["Sheen Roughness"].default_value = 0.5
    if subsurface:
        p.inputs["Subsurface Weight"].default_value = subsurface
        p.inputs["Subsurface Radius"].default_value = sss_radius
        p.inputs["Subsurface Scale"].default_value = sss_scale
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.05
    return m


def hair_material(name, base_srgb, roughness=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    h = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    h.parametrization = "COLOR"
    h.inputs["Color"].default_value = (*srgb_to_linear(base_srgb), 1)
    h.inputs["Roughness"].default_value = roughness
    h.inputs["Radial Roughness"].default_value = 0.9
    h.inputs["Coat"].default_value = 0.0
    nt.links.new(h.outputs[0], out.inputs[0])
    return m


def blush_skin_material(name, base_srgb, blush_srgb, spots, radius, subsurface=0.25):
    """Skin with pink blush at world-space spots (object coordinates of an object at the origin)."""
    m = material(name, base_srgb, roughness=0.55, subsurface=subsurface, sss_radius=(1.0, 0.45, 0.3), sss_scale=0.012,
                 specular=0.35)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    acc = None
    for s in spots:
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "DISTANCE"
        vm.inputs[1].default_value = s
        nt.links.new(tc.outputs["Object"], vm.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = radius * 0.2
        mr.inputs["From Max"].default_value = radius
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(vm.outputs["Value"], mr.inputs["Value"])
        if acc is None:
            acc = mr.outputs["Result"]
        else:
            mx = nt.nodes.new("ShaderNodeMath")
            mx.operation = "MAXIMUM"
            nt.links.new(acc, mx.inputs[0])
            nt.links.new(mr.outputs["Result"], mx.inputs[1])
            acc = mx.outputs[0]
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*srgb_to_linear(base_srgb), 1)
    mix.inputs["B"].default_value = (*srgb_to_linear(blush_srgb), 1)
    nt.links.new(acc, mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    return m


def eye_material(name, iris_srgb, iris_dark_srgb, radius, iris_r, pupil_r, scale=(1.0, 1.0, 1.0), highlights=None,
                 sclera_srgb=(235, 228, 220)):
    """Sclera / iris / pupil from the distance to the eye's forward axis (object space: eyeball at origin, -Y forward).
    scale: the eyeball's ellipsoid scale (x, y depth, z); the iris stays circular in the eye's local frame.
    highlights: optional [(x, z, r), ...] in fractions of the radius (local eye frame, +x = the character's left,
    +z up), painted white on the front (they move with the eye). Defaults keep the v6 node graph unchanged."""
    m = material(name, tuple(sclera_srgb), roughness=0.25, coat=1.0, specular=0.5)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    # Undeformed ("Generated", 0..1 over the eyeball's bounding box) coordinates, so the iris follows the eye bone
    # when the armature rotates the eyeball (object coordinates would keep the iris pointing forward).
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = nt.nodes.new("ShaderNodeVectorMath")
    gen.operation = "MULTIPLY_ADD"
    gen.inputs[1].default_value = tuple(2 * radius * k for k in scale)
    gen.inputs[2].default_value = tuple(-radius * k for k in scale)
    nt.links.new(tc.outputs["Generated"], gen.inputs[0])
    if tuple(scale) != (1.0, 1.0, 1.0):  # back to the unit-sphere frame: iris and pupil stay circular
        unsc = nt.nodes.new("ShaderNodeVectorMath")
        unsc.operation = "DIVIDE"
        unsc.inputs[1].default_value = tuple(float(k) for k in scale)
        nt.links.new(gen.outputs[0], unsc.inputs[0])
        gen = unsc
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(gen.outputs[0], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Z"])
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(comb.outputs[0], ln.inputs[0])
    front = nt.nodes.new("ShaderNodeMath")  # 1 on the front half (y < 0)
    front.operation = "LESS_THAN"
    front.inputs[1].default_value = 0.0
    nt.links.new(sep.outputs["Y"], front.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    e = cr.elements
    e[0].position = 0.0
    e[0].color = (0.01, 0.008, 0.007, 1)
    e[1].position = pupil_r / radius
    e[1].color = (0.01, 0.008, 0.007, 1)
    for pos, col in ((pupil_r / radius + 0.02, iris_dark_srgb), ((pupil_r + iris_r) / 2 / radius, iris_srgb),
                     (iris_r / radius - 0.03, iris_dark_srgb), (iris_r / radius, (40, 25, 18)),
                     (iris_r / radius + 0.025, (235, 228, 220)), (1.0, (225, 215, 205))):
        el = cr.elements.new(pos)
        el.color = (*srgb_to_linear(col), 1)
    div = nt.nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    div.inputs[1].default_value = radius
    nt.links.new(ln.outputs["Value"], div.inputs[0])
    nt.links.new(div.outputs[0], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*srgb_to_linear((225, 215, 205)), 1)
    nt.links.new(front.outputs[0], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["B"])
    out = mix.outputs["Result"]
    if highlights:
        acc = None
        for hx, hz, hr in highlights:
            dist = nt.nodes.new("ShaderNodeVectorMath")
            dist.operation = "DISTANCE"
            dist.inputs[1].default_value = (hx * radius, 0.0, hz * radius)
            nt.links.new(comb.outputs[0], dist.inputs[0])
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.inputs["From Min"].default_value = hr * radius * 0.8
            mr.inputs["From Max"].default_value = hr * radius
            mr.inputs["To Min"].default_value = 1.0
            mr.inputs["To Max"].default_value = 0.0
            nt.links.new(dist.outputs["Value"], mr.inputs["Value"])
            if acc is None:
                acc = mr.outputs["Result"]
            else:
                mx = nt.nodes.new("ShaderNodeMath")
                mx.operation = "MAXIMUM"
                nt.links.new(acc, mx.inputs[0])
                nt.links.new(mr.outputs["Result"], mx.inputs[1])
                acc = mx.outputs[0]
        onfront = nt.nodes.new("ShaderNodeMath")
        onfront.operation = "MULTIPLY"
        nt.links.new(acc, onfront.inputs[0])
        nt.links.new(front.outputs[0], onfront.inputs[1])
        hl = nt.nodes.new("ShaderNodeMix")
        hl.data_type = "RGBA"
        hl.inputs["B"].default_value = (1.0, 1.0, 1.0, 1)
        nt.links.new(onfront.outputs[0], hl.inputs["Factor"])
        nt.links.new(out, hl.inputs["A"])
        out = hl.outputs["Result"]
        nt.links.new(onfront.outputs[0], p.inputs["Emission Strength"])  # highlights glow slightly (catch-lights)
        p.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    nt.links.new(out, p.inputs["Base Color"])
    return m


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ----------------------------------------------------------------------------------------------- fur
def add_fur(name, objs, collection, mat, density, length, radius, spread=0.6, gravity=0.0, comb=None, seed=1,
            max_curves=400000):
    """Short fibres on the evaluated surfaces of objs (world space). density: fibres per m²; length: (min, max) m.
    comb: optional (vector) direction blended into the fibre direction. Deterministic for a given seed and mesh."""
    rng = np.random.default_rng(seed)
    deps = bpy.context.evaluated_depsgraph_get()
    tri_p, tri_n = [], []
    for ob in objs:
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        nv = len(me.vertices)
        co = np.empty(nv * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(ob.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        nt = len(me.loop_triangles)
        tri = np.empty(nt * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tri)
        tri = tri.reshape(-1, 3)
        tri_p.append(co[tri])
        ev.to_mesh_clear()
    if not tri_p:
        return None
    T = np.concatenate(tri_p)
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    cr = np.cross(e1, e2)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    nrm = cr / np.maximum(2 * area[:, None], 1e-12)
    total = float(area.sum())
    count = int(min(max_curves, density * total))
    if count < 10:
        return None
    idx = rng.choice(len(T), size=count, p=area / total)
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    P = T[idx, 0] + e1[idx] * u[:, None] + e2[idx] * v[:, None]
    N = nrm[idx]
    rnd = rng.normal(size=(count, 3))
    rnd -= N * np.sum(rnd * N, axis=1, keepdims=True)
    rnd /= np.maximum(np.linalg.norm(rnd, axis=1, keepdims=True), 1e-9)
    D = N + rnd * spread + np.array([0, 0, -gravity])
    if comb is not None:
        D += np.asarray(comb)[None, :]
    D /= np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-9)
    L = rng.uniform(length[0], length[1], count)[:, None]
    bend = rnd * 0.25 * L
    pts = np.stack([P - N * 0.0004, P + D * L * 0.5 + bend * 0.5, P + D * L + bend], axis=1).reshape(-1, 3)
    hc = bpy.data.hair_curves.new(name)
    hc.add_curves([3] * count)
    hc.attributes["position"].data.foreach_set("vector", pts.astype(np.float32).ravel())
    rad = hc.attributes.new("radius", "FLOAT", "POINT")
    rr = np.tile(np.array([radius, radius * 0.8, radius * 0.35], np.float32), count)
    rad.data.foreach_set("value", rr)
    hc.materials.append(mat)
    ob = bpy.data.objects.new(name, hc)
    collection.objects.link(ob)
    return ob


def rotate_about(points, center, axis, angle):
    R = Matrix.Rotation(angle, 3, Vector(axis))
    c = Vector(center)
    return [c + R @ (Vector(p) - c) for p in points]
