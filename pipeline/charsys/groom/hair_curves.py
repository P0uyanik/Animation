"""T-141 (experiment, opt-in): native Blender hair curves as the fluffy hair surface.

The lock meshes built by groom/* stay as they are (silhouette, rig, dynamics). This module adds, per hair mesh that an
options file names, ONE native Curves object "<mesh>.hair_curves" whose strands lie along the lock (not across it as the
felt fibres do) and are shaped by Blender's own hair node groups (datafiles/assets/nodes/procedural_hair_node_assets.blend:
Interpolate / Clump / Curl / Frizz Hair Curves, Set Hair Curve Profile), appended into the output file.

Nothing calls this module. It is a post-process on an already built .blend and always writes a NEW file:

    blender -b --factory-startup -P pipeline/charsys/groom/hair_curves.py -- \
        --blend <built master or shot .blend> --out <new .blend> --options <options.json> [--report <report.json>]

This folder is a namespace directory on purpose (no __init__.py): `import groom` keeps resolving to groom.py.
Load it by path (importlib) or put this folder on sys.path and `import hair_curves`.

Options ("plush-studio.hair-curves/1"; all lengths in metres, mesh object space; no character data in this file):
  {"schema": "plush-studio.hair-curves/1", "seed": 1,
   "defaults": {<strand settings>},
   "structures": [{"match": "<fnmatch on the hair mesh object name>", "layer": "<name>", "skip": false,
                   <strand settings>}, ...],
                  per layer the first matching entry wins; "skip": true excludes the mesh from that layer. Layer ""
                  (default) builds "<mesh>.hair_curves", layer "x" builds "<mesh>.hair_curves.x".
   "hide_fibre_layers": false | true | ["<ps_groom_fibres layer name>", ...]}   hide felt-fibre layers of those meshes
Strand settings (DEFAULTS below):
  flow            "auto" | "uv" | "chain" | "down": strand direction on the surface. uv = along V of the mesh's
                  "ps_fibre" UV map (metres along the plied rope, groom.py); chain = along the nearest "ps_dyn"
                  dynamics chain; down = gravity projected on the surface. auto = the first of these the mesh has.
  density_per_m2  guide strands per square metre of mesh surface      length_m, length_variation, points
  lift_m, tip_lift_m   height above the surface at the root / extra height at the tip
  min_height_m    final strands (after interpolation, clump, curl, frizz) are kept at least this far above the surface
  overhang        strands that reach the end of a lock run on freely (wispy tips) instead of stopping
  interpolate     null | {"density_per_m2", "guides"}        Interpolate Hair Curves (children between the guides)
  clump           null | {"factor", "shape", "tip_spread"}   Clump Hair Curves (children to their guide)
  curl            null | {"radius", "frequency", "factor", "start"}   Curl Hair Curves
  frizz           null | {"distance", "shape", "factor"}     Frizz Hair Curves
  radius_m, profile_shape                                     Set Hair Curve Profile
  material        "fibres" (material of the mesh's first felt-fibre layer) | "surface" (the mesh's own material)

Motion: every strand is generated in the mesh's rest shape, so the strand set is the same on every frame; the last
modifier ("PS Hair Curves Follow Surface/1") then moves each point with the nearest rest-surface point of the deformed
mesh (position + local frame). The mesh gets `add_rest_position_attribute` and one extra UV map ("ps_hc_atlas", one
cell per polygon, needed by the node groups to attach roots); both only in the output file.
"""
import argparse
import fnmatch
import json
import os
import sys
import time
import zlib

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

SCHEMA = "plush-studio.hair-curves/1"
ASSET_FILE = "procedural_hair_node_assets.blend"
UV_ATLAS = "ps_hc_atlas"
UV_FIBRE = "ps_fibre"
SUFFIX = ".hair_curves"
FOLLOW_GROUP = "PS Hair Curves Follow Surface/1"
MATERIAL_GROUP = "PS Hair Curves Material/1"
DEFAULTS = {
    "flow": "auto", "density_per_m2": 6000.0, "length_m": 0.05, "length_variation": 0.35, "points": 10,
    "lift_m": 0.001, "tip_lift_m": 0.003, "min_height_m": 0.0004, "overhang": True,
    "interpolate": {"density_per_m2": 60000.0, "guides": 3},
    "clump": {"factor": 0.55, "shape": 0.45, "tip_spread": 0.002},
    "curl": None,
    "frizz": {"distance": 0.0015, "shape": 0.5, "factor": 1.0},
    "radius_m": 0.0004, "profile_shape": 0.35, "material": "fibres",
}
_ENTRY_KEYS = ("match", "layer", "skip")
_SUB = {"interpolate": {"density_per_m2", "guides"}, "clump": {"factor", "shape", "tip_spread"},
        "curl": {"radius", "frequency", "factor", "start"}, "frizz": {"distance", "shape", "factor"}}


def validate(options):
    """Returns a list of error strings (empty = valid)."""
    err = []
    if not isinstance(options, dict) or options.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA!r}"]
    for k in options:
        if k not in ("schema", "seed", "defaults", "structures", "hide_fibre_layers", "note"):
            err.append(f"unknown key {k!r}")
    if not isinstance(options.get("seed", 1), int):
        err.append("seed must be an integer")
    hide = options.get("hide_fibre_layers", False)
    if not (isinstance(hide, bool) or (isinstance(hide, list) and all(isinstance(h, str) for h in hide))):
        err.append("hide_fibre_layers must be a bool or a list of layer names")
    structures = options.get("structures")
    if not isinstance(structures, list) or not structures:
        err.append("structures must be a non-empty list")
        structures = []
    for label, block in [("defaults", options.get("defaults", {}))] + [
            (f"structures[{i}]", s) for i, s in enumerate(structures)]:
        if not isinstance(block, dict):
            err.append(f"{label} must be an object")
            continue
        if label != "defaults":
            if not isinstance(block.get("match"), str):
                err.append(f"{label}.match must be a string")
            if not isinstance(block.get("layer", ""), str) or not isinstance(block.get("skip", False), bool):
                err.append(f"{label}: layer must be a string and skip a bool")
        for k, v in block.items():
            if k in _ENTRY_KEYS and label != "defaults":
                continue
            if k not in DEFAULTS:
                err.append(f"{label}: unknown setting {k!r}")
            elif k == "flow":
                if v not in ("auto", "uv", "chain", "down"):
                    err.append(f"{label}.flow must be auto, uv, chain or down")
            elif k == "material":
                if v not in ("fibres", "surface"):
                    err.append(f"{label}.material must be fibres or surface")
            elif k == "overhang":
                if not isinstance(v, bool):
                    err.append(f"{label}.overhang must be a bool")
            elif k in _SUB:
                if v is not None and (not isinstance(v, dict) or set(v) - _SUB[k] or not all(
                        isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0 for x in v.values())):
                    err.append(f"{label}.{k} must be null or an object of non-negative numbers {sorted(_SUB[k])}")
            elif k == "points":
                if not isinstance(v, int) or isinstance(v, bool) or not 3 <= v <= 64:
                    err.append(f"{label}.points must be an integer in [3, 64]")
            elif not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                err.append(f"{label}.{k} must be a non-negative number")
    return err


def settings_for(name, options):
    """{layer: merged strand settings} for a mesh object name (empty when nothing matches)."""
    layers, seen = {}, set()
    for s in options["structures"]:
        layer = s.get("layer", "")
        if layer in seen or not fnmatch.fnmatchcase(name, s["match"]):
            continue
        seen.add(layer)
        if s.get("skip", False):
            continue
        out = json.loads(json.dumps(DEFAULTS))
        for block in (options.get("defaults", {}), s):
            for k, v in block.items():
                if k not in _ENTRY_KEYS:
                    out[k] = {**(out[k] or {}), **v} if k in _SUB and v is not None else v
        layers[layer] = out
    return layers


# ---------------------------------------------------------------------------------------------- mesh -> guides
def _mesh_arrays(me):
    me.calc_loop_triangles()
    nv, nt = len(me.vertices), len(me.loop_triangles)
    co = np.zeros(nv * 3)
    me.vertices.foreach_get("co", co)
    vn = np.zeros(nv * 3)
    me.vertices.foreach_get("normal", vn)
    tv = np.zeros(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", tv)
    tl = np.zeros(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", tl)
    return co.reshape(-1, 3), vn.reshape(-1, 3), tv.reshape(-1, 3), tl.reshape(-1, 3)


def _unit(a):
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    return np.divide(a, n, out=np.zeros_like(a), where=n > 1e-12)


def _flow_uv(me, co, tv, tl):
    """Per-vertex unit direction of increasing V of the "ps_fibre" UV map, or None when the map carries no V."""
    layer = me.uv_layers.get(UV_FIBRE)
    if layer is None:
        return None
    uv = np.zeros(len(me.loops) * 2)
    layer.data.foreach_get("uv", uv)
    v = uv.reshape(-1, 2)[:, 1][tl]
    if float(v.max() - v.min()) < 1e-3:
        return None
    p = co[tv]
    e1, e2 = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
    n = np.cross(e1, e2)
    nn = np.einsum("ij,ij->i", n, n)
    ok = nn > 1e-20
    g = np.zeros_like(n)
    g[ok] = ((v[ok, 1] - v[ok, 0])[:, None] * np.cross(e2[ok], n[ok])
             + (v[ok, 2] - v[ok, 0])[:, None] * np.cross(n[ok], e1[ok])) / nn[ok][:, None]
    mag = np.linalg.norm(g, axis=1)
    ok &= (mag > 0.25) & (mag < 4.0)  # V is in metres along the rope: |grad V| ~ 1 away from UV seams
    w = np.sqrt(nn) * ok
    acc = np.zeros_like(co)
    for k in range(3):
        np.add.at(acc, tv[:, k], _unit(g) * w[:, None])
    return _unit(acc)


def _flow_chain(ob, co):
    """Per-vertex unit tangent of the nearest "ps_dyn" chain segment (root to tip), or None without chains."""
    try:
        chains = json.loads(ob.get("ps_dyn", "{}")).get("chains", [])
    except (TypeError, ValueError):
        chains = []
    a, b = [], []
    for ch in chains:
        j = np.asarray(ch.get("joints", []), dtype=float)
        if j.ndim == 2 and len(j) >= 2:
            a.append(j[:-1])
            b.append(j[1:])
    if not a:
        return None
    a, b = np.concatenate(a), np.concatenate(b)
    ab = b - a
    best = np.full(len(co), np.inf)
    out = np.zeros_like(co)
    for s in range(len(a)):
        t = np.clip(((co - a[s]) @ ab[s]) / max(float(ab[s] @ ab[s]), 1e-12), 0.0, 1.0)
        d = np.linalg.norm(co - (a[s] + t[:, None] * ab[s]), axis=1)
        m = d < best
        best[m] = d[m]
        out[m] = ab[s]
    return _unit(out)


def flow_field(ob, mode, co, tv, tl):
    """(per-vertex flow, source name). Zero vectors fall back to "down" while tracing."""
    order = {"auto": ("uv", "chain", "down"), "uv": ("uv", "down"), "chain": ("chain", "down"), "down": ("down",)}[mode]
    for src in order:
        if src == "uv":
            f = _flow_uv(ob.data, co, tv, tl)
            if f is not None:
                if float(f[:, 2].sum()) > 0.0:  # hanging ropes: run from the scalp downwards
                    f = -f
                return f, "uv"
        elif src == "chain":
            f = _flow_chain(ob, co)
            if f is not None:
                return f, "chain"
        else:
            return np.tile(np.array([0.0, 0.0, -1.0]), (len(co), 1)), "down"
    raise AssertionError("unreachable")


def trace_guides(ob, st, seed, layer=""):
    """Guide strands on the rest mesh. Returns (positions [n, points, 3], root triangle, root weights, stats)."""
    me = ob.data
    co, vn, tv, tl = _mesh_arrays(me)
    flow, source = flow_field(ob, st["flow"], co, tv, tl)
    p = co[tv]
    area = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    total = float(area.sum())
    n = int(round(st["density_per_m2"] * total))
    stats = {"flow": source, "area_m2": round(total, 5), "guides": n, "overhang_points": 0}
    pts = st["points"]
    if n == 0 or total <= 0.0:
        return np.zeros((0, pts, 3)), np.zeros(0, int), np.zeros((0, 3)), stats
    rng = np.random.default_rng([seed, zlib.crc32((ob.name + "\0" + layer).encode())])
    tri = rng.choice(len(area), size=n, p=area / total)
    r1, r2 = np.sqrt(rng.random(n)), rng.random(n)
    w = np.stack([1.0 - r1, r1 * (1.0 - r2), r1 * r2], axis=1)
    roots = np.einsum("nk,nkj->nj", w, p[tri])
    length = st["length_m"] * (1.0 - st["length_variation"] * rng.random(n))
    lift_r = st["lift_m"] * (0.5 + rng.random(n))
    bvh = BVHTree.FromPolygons([tuple(c) for c in co], [tuple(int(i) for i in t) for t in tv])
    down = Vector((0.0, 0.0, -1.0))
    out = np.zeros((n, pts, 3))
    over = 0
    for g in range(n):
        step = length[g] / (pts - 1)
        pos, ti, wt = Vector(roots[g]), int(tri[g]), w[g]
        d_prev, free = None, False
        for i in range(pts):
            t = i / (pts - 1)
            if not free:
                nrm = Vector(wt @ vn[tv[ti]]).normalized()
                out[g, i] = pos + nrm * (lift_r[g] + st["tip_lift_m"] * t * t)
                if i == pts - 1:
                    break
                f = Vector(wt @ flow[tv[ti]])
                d = f - nrm * f.dot(nrm)
                if d.length < 1e-6:
                    d = down - nrm * down.dot(nrm)
                if d.length < 1e-6:
                    d = d_prev if d_prev is not None else nrm.orthogonal()
                d.normalize()
                loc, _, idx, _ = bvh.find_nearest(pos + d * step)
                if loc is None or (loc - pos).length < 0.35 * step:  # ran off the end of the lock
                    if not st["overhang"]:
                        out[g, i + 1:] = out[g, i]
                        break
                    free, d_prev = True, (d * 0.9 + down * 0.1).normalized()
                    continue
                d_prev, pos, ti = d, loc, int(idx)
                wt = np.asarray(poly_3d_calc([Vector(c) for c in co[tv[ti]]], pos))
            else:
                out[g, i] = Vector(out[g, i - 1]) + d_prev * step
                d_prev = (d_prev * 0.92 + down * 0.08).normalized()
                over += 1
    stats["overhang_points"] = over
    return out, tri, w, stats


# ---------------------------------------------------------------------------------------------- Blender objects
def ensure_atlas_uv(me):
    """One UV cell per polygon ("ps_hc_atlas"): unique, non-overlapping, independent of the artistic UV maps."""
    layer = me.uv_layers.get(UV_ATLAS)
    if layer is None:
        active = me.uv_layers.active.name if me.uv_layers.active else None
        render = next((u.name for u in me.uv_layers if u.active_render), None)
        layer = me.uv_layers.new(name=UV_ATLAS, do_init=False)
        if layer is None:
            raise RuntimeError(f"{me.name}: no free UV map slot for {UV_ATLAS}")
        if active:
            me.uv_layers.active = me.uv_layers[active]
        if render:
            me.uv_layers[render].active_render = True
        layer = me.uv_layers[UV_ATLAS]
    npoly = len(me.polygons)
    side = int(np.ceil(np.sqrt(max(npoly, 1))))
    start = np.zeros(npoly, dtype=np.int32)
    total = np.zeros(npoly, dtype=np.int32)
    me.polygons.foreach_get("loop_start", start)
    me.polygons.foreach_get("loop_total", total)
    poly = np.repeat(np.arange(npoly), total)
    corner = np.arange(len(me.loops)) - np.repeat(start, total)
    ang = 2.0 * np.pi * (corner + 0.5) / np.repeat(total, total)  # corners on a circle inside the cell (convex)
    u = (poly % side + 0.5 + 0.45 * np.cos(ang)) / side
    v = (poly // side + 0.5 + 0.45 * np.sin(ang)) / side
    uv = np.stack([u, v], axis=1)
    layer.data.foreach_set("uv", uv.ravel())
    return uv


def _load_group(name):
    g = bpy.data.node_groups.get(name)
    if g is not None:
        return g
    path = os.path.join(bpy.utils.system_resource("DATAFILES"), "assets", "nodes", ASSET_FILE)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        if name not in src.node_groups:
            raise RuntimeError(f"{ASSET_FILE} has no node group {name!r}")
        dst.node_groups = [name]
    return dst.node_groups[0]


def _modifier(obj, label, group, values):
    mod = obj.modifiers.new(label, "NODES")
    mod.node_group = group
    for it in group.interface.items_tree:
        if it.item_type == "SOCKET" and it.in_out == "INPUT" and it.name in values:
            getattr(mod.properties.inputs, it.identifier).value = values[it.name]
    return mod


def follow_group():
    """Node group: move rest-space strands with the deformed surface (nearest rest-surface point + local frame)."""
    g = bpy.data.node_groups.get(FOLLOW_GROUP)
    if g is not None:
        return g
    g = bpy.data.node_groups.new(FOLLOW_GROUP, "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Surface", in_out="INPUT", socket_type="NodeSocketObject")
    g.interface.new_socket("Min Height", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = g.nodes, g.links
    gin, gout = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    info = N.new("GeometryNodeObjectInfo")
    info.transform_space = "RELATIVE"
    L.new(gin.outputs["Surface"], info.inputs["Object"])

    def edge_vector():  # a second, non-normal direction per vertex: its first edge
        eov = N.new("GeometryNodeEdgesOfVertex")
        ev = N.new("GeometryNodeInputMeshEdgeVertices")
        sub = N.new("ShaderNodeVectorMath")
        sub.operation = "SUBTRACT"
        L.new(ev.outputs["Position 2"], sub.inputs[0])
        L.new(ev.outputs["Position 1"], sub.inputs[1])
        at = N.new("GeometryNodeFieldAtIndex")
        at.domain, at.data_type = "EDGE", "FLOAT_VECTOR"
        L.new(eov.outputs["Edge Index"], at.inputs["Index"])
        L.new(sub.outputs[0], at.inputs["Value"])
        return at.outputs["Value"]

    pos, nrm = N.new("GeometryNodeInputPosition"), N.new("GeometryNodeInputNormal")
    geo = info.outputs["Geometry"]
    deformed = []
    for field in (pos.outputs["Position"], nrm.outputs["Normal"], edge_vector()):
        cap = N.new("GeometryNodeCaptureAttribute")
        cap.domain = "POINT"
        cap.capture_items.new("VECTOR", "Value")
        L.new(geo, cap.inputs["Geometry"])
        L.new(field, cap.inputs["Value"])
        geo = cap.outputs["Geometry"]
        deformed.append(cap.outputs["Value"])
    rest_attr = N.new("GeometryNodeInputNamedAttribute")
    rest_attr.data_type = "FLOAT_VECTOR"
    rest_attr.inputs["Name"].default_value = "rest_position"
    rest = N.new("GeometryNodeSetPosition")
    L.new(geo, rest.inputs["Geometry"])
    L.new(rest_attr.outputs["Attribute"], rest.inputs["Position"])

    def sample(field):
        s = N.new("GeometryNodeSampleNearestSurface")
        s.data_type = "FLOAT_VECTOR"
        L.new(rest.outputs["Geometry"], s.inputs["Mesh"])
        L.new(field, s.inputs["Value"])
        L.new(pos.outputs["Position"], s.inputs["Sample Position"])
        return s.outputs["Value"]

    d_pos, d_nrm, d_edge = (sample(f) for f in deformed)
    r_pos, r_nrm, r_edge = sample(pos.outputs["Position"]), sample(nrm.outputs["Normal"]), sample(edge_vector())

    def frame(primary, secondary):
        a = N.new("FunctionNodeAxesToRotation")
        a.primary_axis, a.secondary_axis = "Z", "X"
        L.new(primary, a.inputs["Primary Axis"])
        L.new(secondary, a.inputs["Secondary Axis"])
        return a.outputs["Rotation"]

    inv = N.new("FunctionNodeInvertRotation")
    L.new(frame(r_nrm, r_edge), inv.inputs["Rotation"])
    offset = N.new("ShaderNodeVectorMath")
    offset.operation = "SUBTRACT"
    L.new(pos.outputs["Position"], offset.inputs[0])
    L.new(r_pos, offset.inputs[1])
    # children that interpolation or clumping left below the surface are lifted to Min Height along the rest normal
    height = N.new("ShaderNodeVectorMath")
    height.operation = "DOT_PRODUCT"
    L.new(offset.outputs[0], height.inputs[0])
    L.new(r_nrm, height.inputs[1])
    lack = N.new("ShaderNodeMath")
    lack.operation = "SUBTRACT"
    L.new(gin.outputs["Min Height"], lack.inputs[0])
    L.new(height.outputs["Value"], lack.inputs[1])
    pos_lack = N.new("ShaderNodeMath")
    pos_lack.operation = "MAXIMUM"
    L.new(lack.outputs[0], pos_lack.inputs[0])
    pos_lack.inputs[1].default_value = 0.0
    push = N.new("ShaderNodeVectorMath")
    push.operation = "SCALE"
    L.new(r_nrm, push.inputs[0])
    L.new(pos_lack.outputs[0], push.inputs["Scale"])
    lifted = N.new("ShaderNodeVectorMath")
    lifted.operation = "ADD"
    L.new(offset.outputs[0], lifted.inputs[0])
    L.new(push.outputs[0], lifted.inputs[1])
    local = N.new("FunctionNodeRotateVector")
    L.new(lifted.outputs[0], local.inputs["Vector"])
    L.new(inv.outputs["Rotation"], local.inputs["Rotation"])
    world = N.new("FunctionNodeRotateVector")
    L.new(local.outputs["Vector"], world.inputs["Vector"])
    L.new(frame(d_nrm, d_edge), world.inputs["Rotation"])
    add = N.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    L.new(d_pos, add.inputs[0])
    L.new(world.outputs["Vector"], add.inputs[1])
    setp = N.new("GeometryNodeSetPosition")
    L.new(gin.outputs["Geometry"], setp.inputs["Geometry"])
    L.new(add.outputs[0], setp.inputs["Position"])
    L.new(setp.outputs["Geometry"], gout.inputs["Geometry"])
    return g


def material_group():
    g = bpy.data.node_groups.get(MATERIAL_GROUP)
    if g is not None:
        return g
    g = bpy.data.node_groups.new(MATERIAL_GROUP, "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Material", in_out="INPUT", socket_type="NodeSocketMaterial")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gin, gout = g.nodes.new("NodeGroupInput"), g.nodes.new("NodeGroupOutput")
    sm = g.nodes.new("GeometryNodeSetMaterial")
    g.links.new(gin.outputs["Geometry"], sm.inputs["Geometry"])
    g.links.new(gin.outputs["Material"], sm.inputs["Material"])
    g.links.new(sm.outputs["Geometry"], gout.inputs["Geometry"])
    return g


def _fibre_children(ob):
    return sorted((c for c in ob.children if c.type == "CURVES" and "ps_groom_fibres" in c), key=lambda c: c.name)


def object_name(mesh_name, layer=""):
    return mesh_name + SUFFIX + ("." + layer if layer else "")


def add_hair_curves(ob, st, seed, layer=""):
    """Builds "<mesh>.hair_curves[.<layer>]" for one hair mesh. Returns (curves object, stats)."""
    me = ob.data
    guides, tri, w, stats = trace_guides(ob, st, seed, layer)
    n, pts = guides.shape[0], guides.shape[1]
    atlas = ensure_atlas_uv(me)
    ob.add_rest_position_attribute = True
    _, _, _, tl = _mesh_arrays(me)
    cu = bpy.data.hair_curves.new(object_name(ob.name, layer))
    if n:
        cu.add_curves([pts] * n)
        cu.attributes["position"].data.foreach_set("vector", guides.reshape(-1).astype(np.float32))
        root_uv = np.einsum("nk,nkj->nj", w, atlas[tl[tri]])
        attr = cu.attributes.new("surface_uv_coordinate", "FLOAT2", "CURVE")
        attr.data.foreach_set("vector", root_uv.reshape(-1).astype(np.float32))
    cu.surface, cu.surface_uv_map = ob, UV_ATLAS
    fibres = _fibre_children(ob)
    mat = fibres[0].data.materials[0] if st["material"] == "fibres" and fibres and fibres[0].data.materials else (
        me.materials[0] if me.materials else None)
    if mat is not None:
        cu.materials.append(mat)
    obj = bpy.data.objects.new(object_name(ob.name, layer), cu)
    for coll in ob.users_collection:
        coll.objects.link(obj)
    obj.parent = ob
    obj["ps_hair_curves"] = json.dumps({"schema": SCHEMA, "settings": st, "seed": seed, **stats}, sort_keys=True)
    s = (seed + zlib.crc32(layer.encode())) % 100000
    if st["interpolate"] and n:
        _modifier(obj, "Interpolate", _load_group("Interpolate Hair Curves"), {
            "Resting Surface": True, "Follow Surface Normal": False, "Part by Mesh Islands": False,
            "Interpolation Guides": int(st["interpolate"]["guides"]),
            "Density": float(st["interpolate"]["density_per_m2"]), "Seed": s})
    if st["clump"]:
        _modifier(obj, "Clump", _load_group("Clump Hair Curves"), {
            "Factor": float(st["clump"]["factor"]), "Shape": float(st["clump"]["shape"]),
            "Tip Spread": float(st["clump"]["tip_spread"]), "Existing Guide Map": bool(st["interpolate"]),
            "Guide Distance": 0.012, "Seed": s})
    if st["curl"]:
        c = st["curl"]
        _modifier(obj, "Curl", _load_group("Curl Hair Curves"), {
            "Factor": float(c.get("factor", 1.0)), "Radius": float(c.get("radius", 0.003)),
            "Frequency": float(c.get("frequency", 60.0)), "Curl Start": float(c.get("start", 0.2)),
            "Subdivision": 2, "Existing Guide Map": bool(st["interpolate"]), "Guide Distance": 0.012, "Seed": s})
    if st["frizz"]:
        _modifier(obj, "Frizz", _load_group("Frizz Hair Curves"), {
            "Factor": float(st["frizz"]["factor"]), "Distance": float(st["frizz"]["distance"]),
            "Shape": float(st["frizz"]["shape"]), "Seed": s})
    _modifier(obj, "Profile", _load_group("Set Hair Curve Profile"), {
        "Replace Radius": True, "Radius": float(st["radius_m"]), "Shape": float(st["profile_shape"])})
    _modifier(obj, "Follow Surface", follow_group(), {"Surface": ob, "Min Height": float(st["min_height_m"])})
    if mat is not None:
        _modifier(obj, "Material", material_group(), {"Material": mat})
    return obj, stats


def apply(options, objects=None):
    """Adds hair curves to every hair mesh that an options structure matches. Returns the report dict."""
    errors = validate(options)
    if errors:
        raise ValueError("hair-curves options: " + "; ".join(errors))
    seed = int(options.get("seed", 1))
    hide = options.get("hide_fibre_layers", False)
    report = {"schema": SCHEMA, "seed": seed, "objects": {}, "hidden_fibre_objects": []}
    pool = sorted((o for o in (objects if objects is not None else bpy.data.objects)
                   if o.type == "MESH"), key=lambda o: o.name)
    t0 = time.time()
    for ob in pool:
        layers = settings_for(ob.name, options)
        if not layers:
            continue
        for layer, st in sorted(layers.items()):
            name = object_name(ob.name, layer)
            if bpy.data.objects.get(name) is not None:
                raise RuntimeError(f"{name} already exists")
            _, stats = add_hair_curves(ob, st, seed, layer)
            report["objects"][name] = stats
        if hide:
            for f in _fibre_children(ob):
                if hide is True or f["ps_groom_fibres"] in hide:
                    f.hide_render = f.hide_viewport = True
                    report["hidden_fibre_objects"].append(f.name)
    report["guides_total"] = sum(s["guides"] for s in report["objects"].values())
    report["area_m2_total"] = round(sum(s["area_m2"] for s in report["objects"].values()), 5)
    report["seconds"] = round(time.time() - t0, 2)
    return report


def evaluated_counts(objects=None):
    """{object name: [curves, points]} of the evaluated hair-curves objects (current frame)."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for o in sorted((o for o in (objects or bpy.data.objects) if "ps_hair_curves" in o), key=lambda o: o.name):
        ev = o.evaluated_get(dg).data
        out[o.name] = [len(ev.curves), len(ev.points)]
    return out


def main(argv):
    ap = argparse.ArgumentParser(prog="hair_curves.py")
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--options", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    src, dst = os.path.abspath(a.blend), os.path.abspath(a.out)
    if src == dst or os.path.exists(dst):
        raise SystemExit("hair_curves: --out must be a new file (the input is never changed)")
    if f"{os.sep}assets{os.sep}characters{os.sep}" in dst:
        raise SystemExit("hair_curves: never writes into assets/characters (experiment output only)")
    options = json.load(open(a.options))
    bpy.ops.wm.open_mainfile(filepath=src)
    report = apply(options)
    counts = evaluated_counts()
    report["evaluated"] = counts
    report["curves_total"] = sum(c for c, _ in counts.values())
    report["points_total"] = sum(p for _, p in counts.values())
    report["input"] = os.path.basename(src)
    bpy.ops.wm.save_as_mainfile(filepath=dst, copy=True)
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1, sort_keys=True)
    print(json.dumps({k: report[k] for k in ("guides_total", "curves_total", "points_total", "area_m2_total",
                                              "seconds")}))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
