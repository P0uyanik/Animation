"""T-207 (opt-in): a velvety / flocked hair finish on built groom meshes.

The lock meshes built by groom/* stay as they are (silhouette, rig, dynamics, contact). This module changes only how
their surface reads, from one options object ("plush-studio.hair-flock/1"); every block is optional and an absent or
null block changes nothing:

  velvet   lock shader: softer albedo breakup, more and lighter sheen, a fresnel rim, finer micro-normal (edits the
           named "PS ..." nodes of the hair meshes' own material; nodes a material lacks are reported, not added)
  fibres   the existing felt-fibre layers ("PS Shared Surface Fibres/1" children, by ps_groom_fibres layer name):
           "hide" or {"length": scale, "density": scale}
  flock    a dense layer of short fibres lying at a low angle along the lock flow (one Curves object
           "<mesh>.flock" per mesh), Principled Hair BSDF via the felt-fibre material
  edge     a sparse layer of longer, brighter fuzz only where the rest surface is convex (lock edges, rounded rims,
           tips) or open (sheet borders): "<mesh>.flock.edge". The selection is a mesh attribute of the rest shape,
           never the camera or the light.

Strands are made in numpy in the mesh's rest shape (roots area-weighted, seeded per mesh and layer), so the strand set
is the same on every run and every frame; hair_curves.py's "Follow Surface" node group then moves them with the
deformed mesh. Faces hidden under other hair or the body (a ray along the normal hits something within cull_m) get
no strands. Blender's own hair node groups do frizz and the profile (procedural_hair_node_assets.blend).

Two ways in, both opt-in:
  post-process   blender -b --factory-startup -P pipeline/charsys/groom/flock.py -- \
                     --blend <built .blend> --out <new .blend> --options <options.json> [--report <report.json>]
  build hook     apply_spec(hair_spec, objects): does nothing and returns None when hair_spec has no "flock" key
                 (the groom_r6 patch in docs/evaluation/characters/T-207/ calls it after the groom build).

Options:
  {"schema": "plush-studio.hair-flock/1", "seed": 1, "look": "<label>", "note": "...",
   "match": ["hair_*"], "exclude": ["hair_band*", "hair_flowers*"],          fnmatch on mesh object names
   "velvet": null | {VELVET keys}, "fibres": null | {"<layer>": "hide" | {"length": s, "density": s}},
   "flock": null | {STRAND keys}, "edge": null | {STRAND keys, "mask": {MASK keys}}}
All lengths in metres (mesh object space), angles in degrees.
"""
import argparse
import fnmatch
import hashlib
import importlib.util
import json
import os
import sys
import time
import zlib

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCHEMA = "plush-studio.hair-flock/1"
SUFFIX = ".flock"
SPEC_KEY = "flock"
FIBRE_GROUP = "PS Shared Surface Fibres/1"
STRAND = {
    "density_per_m2": 400000.0, "length_m": 0.003, "length_variation": 0.4, "points": 5,
    "lean_deg": 30.0, "lean_variation_deg": 12.0, "bend": 0.5, "spread_deg": 35.0, "lift_m": 0.0002,
    "radius_m": 0.00007, "profile_shape": 0.3, "frizz": None, "cull_m": 0.004,
    "tone": 1.0, "roughness": 1.0,
}
MASK = {"convex": [60.0, 220.0], "boundary": 1.0, "base": 0.0}
VELVET = {
    "albedo_variation": None, "sheen": None, "sheen_roughness": None, "sheen_lighten": None, "rim_weight": None,
    "rim_power": None, "fibre_bump": None, "micro_bump": None, "micro_scale": None, "roughness": None,
    "clump_value": None,
}
_HC = None


def hair_curves():
    """groom/hair_curves.py loaded by path (this folder is a namespace directory)."""
    global _HC
    if _HC is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hair_curves.py")
        spec = importlib.util.spec_from_file_location("ps_hair_curves_for_flock", path)
        _HC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_HC)
    return _HC


# ---------------------------------------------------------------------------------------------- options
def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _pair(v):
    return isinstance(v, list) and len(v) == 2 and all(_num(x) for x in v)


def validate(options):
    """Returns a list of error strings (empty = valid)."""
    if not isinstance(options, dict) or options.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA!r}"]
    err = []
    for k in options:
        if k not in ("schema", "seed", "look", "note", "match", "exclude", "velvet", "fibres", "flock", "edge"):
            err.append(f"unknown key {k!r}")
    if not isinstance(options.get("seed", 1), int) or isinstance(options.get("seed", 1), bool):
        err.append("seed must be an integer")
    for k in ("match", "exclude"):
        v = options.get(k, [])
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            err.append(f"{k} must be a list of strings")
    vel = options.get("velvet")
    if vel is not None:
        if not isinstance(vel, dict):
            err.append("velvet must be null or an object")
        else:
            for k, v in vel.items():
                if k not in VELVET:
                    err.append(f"velvet: unknown key {k!r}")
                elif k in ("albedo_variation", "sheen", "roughness") and not _pair(v):
                    err.append(f"velvet.{k} must be [lo, hi]")
                elif k not in ("albedo_variation", "sheen", "roughness") and not (_num(v) and v >= 0):
                    err.append(f"velvet.{k} must be a non-negative number")
    fib = options.get("fibres")
    if fib is not None:
        if not isinstance(fib, dict):
            err.append("fibres must be null or an object")
        else:
            for layer, v in fib.items():
                if v == "hide":
                    continue
                if not isinstance(v, dict) or set(v) - {"length", "density"} or not all(
                        _num(x) and x >= 0 for x in v.values()):
                    err.append(f"fibres.{layer} must be \"hide\" or {{length, density}} scales")
    for block in ("flock", "edge"):
        st = options.get(block)
        if st is None:
            continue
        if not isinstance(st, dict):
            err.append(f"{block} must be null or an object")
            continue
        for k, v in st.items():
            if k == "mask" and block == "edge":
                if not isinstance(v, dict) or set(v) - set(MASK):
                    err.append("edge.mask: unknown keys")
                elif "convex" in v and not _pair(v["convex"]):
                    err.append("edge.mask.convex must be [k0, k1] (1/m)")
                elif not all(_num(v.get(x, 0)) and v.get(x, 0) >= 0 for x in ("boundary", "base")):
                    err.append("edge.mask.boundary/base must be non-negative numbers")
            elif k not in STRAND:
                err.append(f"{block}: unknown setting {k!r}")
            elif k == "frizz":
                if v is not None and (not isinstance(v, dict) or set(v) - {"distance", "shape", "factor"} or not all(
                        _num(x) and x >= 0 for x in v.values())):
                    err.append(f"{block}.frizz must be null or {{distance, shape, factor}}")
            elif k == "points":
                if not isinstance(v, int) or isinstance(v, bool) or not 2 <= v <= 16:
                    err.append(f"{block}.points must be an integer in [2, 16]")
            elif not _num(v) or v < 0:
                err.append(f"{block}.{k} must be a non-negative number")
    return err


def strand_settings(options, block):
    st = options.get(block)
    if st is None:
        return None
    out = dict(STRAND, **{k: v for k, v in st.items() if k != "mask"})
    if block == "edge":
        out["mask"] = dict(MASK, **st.get("mask", {}))
    return out


def selected(name, options):
    inc = options.get("match", ["hair_*"])
    exc = options.get("exclude", [])
    return any(fnmatch.fnmatchcase(name, m) for m in inc) and not any(fnmatch.fnmatchcase(name, m) for m in exc)


# ---------------------------------------------------------------------------------------------- velvet shader
def _set(node, sock, value, log, key):
    if node is None:
        log.setdefault("missing", []).append(key)
        return
    s = node.inputs.get(sock) if isinstance(sock, str) else node.inputs[sock]
    if s is None or s.is_linked:
        log.setdefault("missing", []).append(key)
        return
    s.default_value = value
    log.setdefault("set", []).append(key)


def apply_velvet(mat, vel):
    """Edits the hair lock material in place (named PS nodes). Returns {set: [...], missing: [...]}."""
    log = {}
    nt = mat.node_tree
    N = nt.nodes.get
    if vel.get("albedo_variation"):
        lo, hi = vel["albedo_variation"]
        _set(N("PS Fibre Albedo Variation"), "To Min", lo, log, "albedo_variation.lo")
        _set(N("PS Fibre Albedo Variation"), "To Max", hi, log, "albedo_variation.hi")
    if vel.get("roughness"):
        lo, hi = vel["roughness"]
        _set(N("PS Broken Fibre Roughness"), "To Min", lo, log, "roughness.lo")
        _set(N("PS Broken Fibre Roughness"), "To Max", hi, log, "roughness.hi")
    if vel.get("sheen"):
        lo, hi = vel["sheen"]
        _set(N("PS Nap Sheen"), "To Min", lo, log, "sheen.lo")
        _set(N("PS Nap Sheen"), "To Max", hi, log, "sheen.hi")
    if vel.get("clump_value") is not None:
        _set(N("PS Nap Value"), "To Max", 1.0 + vel["clump_value"], log, "clump_value")
    bsdf = N("Principled BSDF")
    if vel.get("sheen_roughness") is not None:
        _set(bsdf, "Sheen Roughness", vel["sheen_roughness"], log, "sheen_roughness")
    if vel.get("sheen_lighten") is not None:
        rim = N("PS Rim Sheen")
        base = list(rim.inputs["Base Color"].default_value) if rim is not None else [0.5, 0.5, 0.5, 1.0]
        k = min(max(vel["sheen_lighten"], 0.0), 1.0)
        tint = [min(1.0, c * (1.0 - k) + k * min(1.0, 3.0 * c + 0.15)) for c in base[:3]] + [1.0]
        _set(bsdf, "Sheen Tint", tint, log, "sheen_tint")
        if rim is not None:
            _set(rim, "Base Color", tint, log, "rim_colour")
    if vel.get("rim_weight") is not None:
        _set(N("PS Rim Weight"), 1, vel["rim_weight"], log, "rim_weight")
    if vel.get("rim_power") is not None:
        _set(N("PS Rim Width"), 1, vel["rim_power"], log, "rim_power")
    if vel.get("fibre_bump") is not None:
        _set(N("PS Fibre Bump"), "Strength", vel["fibre_bump"], log, "fibre_bump")
    if vel.get("micro_bump") is not None:
        _set(N("PS Micro Fibre Normal"), "Strength", vel["micro_bump"], log, "micro_bump")
    if vel.get("micro_scale") is not None:
        _set(N("PS Micro Fibre Relief"), "Scale", vel["micro_scale"], log, "micro_scale")
    return log


# ---------------------------------------------------------------------------------------------- felt fibres
def _fibre_children(ob):
    return sorted((c for c in ob.children if c.type == "CURVES" and "ps_groom_fibres" in c), key=lambda c: c.name)


def _mod_input(mod, name):
    for it in mod.node_group.interface.items_tree:
        if it.item_type == "SOCKET" and it.in_out == "INPUT" and it.name == name:
            return getattr(mod.properties.inputs, it.identifier)
    return None


def apply_fibres(ob, fib, report):
    for f in _fibre_children(ob):
        rule = fib.get(f["ps_groom_fibres"])
        if rule is None:
            continue
        if rule == "hide":
            f.hide_render = f.hide_viewport = True
            report["hidden_fibre_objects"].append(f.name)
            continue
        mod = next((m for m in f.modifiers if m.type == "NODES" and m.node_group
                    and m.node_group.name.startswith(FIBRE_GROUP.split("/")[0])), None)
        if mod is None:
            continue
        for key, sock in (("length", "Length"), ("density", "Density")):
            p = _mod_input(mod, sock)
            if key in rule and p is not None:
                p.value = p.value * float(rule[key])
        report["scaled_fibre_objects"].append(f.name)


# ---------------------------------------------------------------------------------------------- masks
def _edges(me):
    ne = len(me.edges)
    ev = np.zeros(ne * 2, dtype=np.int32)
    me.edges.foreach_get("vertices", ev)
    return ev.reshape(-1, 2)


def convexity(co, vn, edges):
    """Per-vertex mean convex curvature (1/m; a sphere of radius R gives 1/R), from the vertex normals."""
    i, j = edges[:, 0], edges[:, 1]
    e = co[j] - co[i]
    l2 = np.maximum(np.einsum("ij,ij->i", e, e), 1e-14)
    ci = -2.0 * np.einsum("ij,ij->i", vn[i], e) / l2
    cj = 2.0 * np.einsum("ij,ij->i", vn[j], e) / l2
    acc = np.zeros(len(co))
    cnt = np.zeros(len(co))
    np.add.at(acc, i, ci)
    np.add.at(acc, j, cj)
    np.add.at(cnt, i, 1.0)
    np.add.at(cnt, j, 1.0)
    return acc / np.maximum(cnt, 1.0)


def boundary_vertices(me, edges):
    """Vertices on open borders (edges with one face)."""
    use = np.zeros(len(edges), dtype=np.int32)
    ek = np.zeros(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("edge_index", ek)
    np.add.at(use, ek, 1)
    out = np.zeros(len(me.vertices), dtype=bool)
    out[edges[use == 1].ravel()] = True
    return out


def edge_weight(me, co, vn, mask):
    """Per-vertex 0..1 edge-fuzz weight: smoothstep of convexity, open borders, a base level."""
    edges = _edges(me)
    k0, k1 = mask["convex"]
    t = np.clip((convexity(co, vn, edges) - k0) / max(k1 - k0, 1e-9), 0.0, 1.0)
    w = t * t * (3.0 - 2.0 * t)
    w = np.maximum(w, boundary_vertices(me, edges) * float(mask["boundary"]))
    return np.clip(np.maximum(w, float(mask["base"])), 0.0, 1.0)


class Occluders:
    """World-space BVH of every rendered mesh (rest data), for the hidden-face cull."""

    def __init__(self, objects):
        verts, polys, off = [], [], 0
        for o in sorted((o for o in objects if o.type == "MESH" and not o.hide_render), key=lambda o: o.name):
            me = o.data
            n = len(me.vertices)
            if n == 0:
                continue
            co = np.zeros(n * 3)
            me.vertices.foreach_get("co", co)
            m = np.array(o.matrix_world)
            co = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
            me.calc_loop_triangles()
            tv = np.zeros(len(me.loop_triangles) * 3, dtype=np.int32)
            me.loop_triangles.foreach_get("vertices", tv)
            verts.append(co)
            polys.append(tv.reshape(-1, 3) + off)
            off += n
        self.bvh = None
        if verts:
            v, p = np.concatenate(verts), np.concatenate(polys)
            self.bvh = BVHTree.FromPolygons([tuple(x) for x in v.tolist()], [tuple(x) for x in p.tolist()])

    def hidden(self, ob, centres, normals, dist):
        """Bool per triangle: a ray along the (world) normal hits something within dist."""
        out = np.zeros(len(centres), dtype=bool)
        if self.bvh is None or dist <= 0:
            return out
        m = np.array(ob.matrix_world)
        c = centres @ m[:3, :3].T + m[:3, 3]
        n = hair_curves()._unit(normals @ np.linalg.inv(m[:3, :3]))
        eps = 2e-4
        cast = self.bvh.ray_cast
        for k in range(len(c)):
            d = Vector(n[k])
            hit = cast(Vector(c[k]) + d * eps, d, dist)
            out[k] = hit[0] is not None
        return out


# ---------------------------------------------------------------------------------------------- strands
def make_strands(ob, st, seed, layer, occluders):
    """Strand points [n, points, 3] in mesh object space (rest shape), per-strand tone, stats."""
    HC = hair_curves()
    me = ob.data
    co, vn, tv, tl = HC._mesh_arrays(me)
    flow, source = HC.flow_field(ob, "auto", co, tv, tl)
    p = co[tv]
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    weight = np.ones(len(tv))
    stats = {"flow": source, "area_m2": round(float(area.sum()), 5)}
    if "mask" in st:
        weight *= edge_weight(me, co, vn, st["mask"])[tv].mean(axis=1)
    if st["cull_m"] > 0 and occluders is not None:
        hid = occluders.hidden(ob, p.mean(axis=1), HC._unit(cross), st["cull_m"])
        stats["hidden_area_m2"] = round(float(area[hid].sum()), 5)
        weight[hid] = 0.0
    wa = area * weight
    total = float(wa.sum())
    stats["weighted_area_m2"] = round(total, 5)
    n = int(round(st["density_per_m2"] * total))
    stats["strands"] = n
    pts = st["points"]
    if n == 0 or total <= 0.0:
        return np.zeros((0, pts, 3)), np.zeros(0), stats
    rng = np.random.default_rng([seed, zlib.crc32((ob.name + "\0" + layer).encode())])
    tri = rng.choice(len(wa), size=n, p=wa / total)
    r1, r2 = np.sqrt(rng.random(n)), rng.random(n)
    w = np.stack([1.0 - r1, r1 * (1.0 - r2), r1 * r2], axis=1)
    root = np.einsum("nk,nkj->nj", w, p[tri])
    nrm = HC._unit(np.einsum("nk,nkj->nj", w, vn[tv[tri]]))
    fl = np.einsum("nk,nkj->nj", w, flow[tv[tri]])
    d = fl - nrm * np.einsum("ij,ij->i", fl, nrm)[:, None]
    down = np.array([0.0, 0.0, -1.0])
    dd = down - nrm * (nrm @ down)[:, None]
    small = np.linalg.norm(d, axis=1) < 1e-6
    d[small] = dd[small]
    small = np.linalg.norm(d, axis=1) < 1e-6
    d[small] = np.cross(nrm[small], np.array([1.0, 0.0, 0.0]))
    d = HC._unit(d)
    b = np.cross(nrm, d)
    phi = np.radians(st["spread_deg"]) * (2.0 * rng.random(n) - 1.0)
    d = d * np.cos(phi)[:, None] + b * np.sin(phi)[:, None]  # azimuth jitter around the flow, in the tangent plane
    lean = np.radians(st["lean_deg"] + st["lean_variation_deg"] * (2.0 * rng.random(n) - 1.0))
    length = st["length_m"] * (1.0 - st["length_variation"] * rng.random(n))
    tone = rng.random(n)
    out = np.zeros((n, pts, 3))
    pos = root + nrm * st["lift_m"]
    out[:, 0] = pos
    step = length / (pts - 1)
    for i in range(1, pts):
        a = lean * (1.0 - st["bend"] * (i - 0.5) / (pts - 1))  # the fibre lays over towards its tip (nap)
        pos = pos + (d * np.cos(a)[:, None] + nrm * np.sin(a)[:, None]) * step[:, None]
        out[:, i] = pos
    return out, tone, stats


def flock_material(src, st):
    """The fibre material, or a copy "<name>.flock" with tone/roughness scaled (made once per source material)."""
    if src is None or (st["tone"] == 1.0 and st["roughness"] == 1.0):
        return src
    name = f"{src.name}.flock.t{st['tone']:g}.r{st['roughness']:g}"
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = src.copy()
    mat.name = name
    for nd in mat.node_tree.nodes:
        if nd.bl_idname == "ShaderNodeBsdfHairPrincipled":
            r = nd.inputs.get("Roughness")
            if r is not None and r.is_linked and r.links[0].from_node.bl_idname == "ShaderNodeMapRange":
                mr = r.links[0].from_node
                for s in ("To Min", "To Max"):
                    mr.inputs[s].default_value *= st["roughness"]
            elif r is not None:
                r.default_value *= st["roughness"]
        if nd.bl_idname == "ShaderNodeMapRange" and nd.outputs[0].is_linked and any(
                lk.to_node.bl_idname == "ShaderNodeVectorMath" and lk.to_socket.name == "Scale"
                for lk in nd.outputs[0].links):
            for s in ("To Min", "To Max"):  # ps_fibre_tone -> colour scale
                nd.inputs[s].default_value *= st["tone"]
    return mat


def add_layer(ob, st, seed, layer, occluders):
    HC = hair_curves()
    strands, tone, stats = make_strands(ob, st, seed, layer, occluders)
    n, pts = strands.shape[0], strands.shape[1]
    name = ob.name + SUFFIX + ("." + layer if layer else "")
    if bpy.data.objects.get(name) is not None:
        raise RuntimeError(f"{name} already exists")
    ob.add_rest_position_attribute = True
    cu = bpy.data.hair_curves.new(name)
    if n:
        cu.add_curves([pts] * n)
        cu.attributes["position"].data.foreach_set("vector", strands.reshape(-1).astype(np.float32))
        a = cu.attributes.new("ps_fibre_tone", "FLOAT", "CURVE")
        a.data.foreach_set("value", tone.astype(np.float32))
    fibres = _fibre_children(ob)
    src = fibres[0].data.materials[0] if fibres and fibres[0].data.materials else (
        ob.data.materials[0] if ob.data.materials else None)
    mat = flock_material(src, st)
    if mat is not None:
        cu.materials.append(mat)
    obj = bpy.data.objects.new(name, cu)
    for coll in ob.users_collection:
        coll.objects.link(obj)
    obj.parent = ob
    obj["ps_hair_flock"] = json.dumps({"schema": SCHEMA, "layer": layer or "flock", "settings": st, "seed": seed,
                                       **stats}, sort_keys=True)
    s = (seed + zlib.crc32(("flock." + layer).encode())) % 100000
    if st["frizz"]:
        HC._modifier(obj, "Frizz", HC._load_group("Frizz Hair Curves"), {
            "Factor": float(st["frizz"].get("factor", 1.0)), "Distance": float(st["frizz"].get("distance", 0.0005)),
            "Shape": float(st["frizz"].get("shape", 0.5)), "Seed": s})
    HC._modifier(obj, "Profile", HC._load_group("Set Hair Curve Profile"), {
        "Replace Radius": True, "Radius": float(st["radius_m"]), "Shape": float(st["profile_shape"])})
    HC._modifier(obj, "Follow Surface", HC.follow_group(), {"Surface": ob, "Min Height": 0.0})
    if mat is not None:
        HC._modifier(obj, "Material", HC.material_group(), {"Material": mat})
    stats["sha"] = hashlib.sha256(strands.astype(np.float32).tobytes() + tone.astype(np.float32).tobytes()
                                  ).hexdigest()[:16]
    return obj, stats


# ---------------------------------------------------------------------------------------------- entry points
def apply(options, objects=None):
    """Applies the options to every selected hair mesh. Returns the report dict."""
    errors = validate(options)
    if errors:
        raise ValueError("hair-flock options: " + "; ".join(errors))
    t0 = time.time()
    seed = int(options.get("seed", 1))
    allobj = list(objects) if objects is not None else list(bpy.data.objects)
    pool = sorted((o for o in allobj if o.type == "MESH" and selected(o.name, options)), key=lambda o: o.name)
    report = {"schema": SCHEMA, "look": options.get("look"), "seed": seed, "meshes": [o.name for o in pool],
              "velvet": {}, "hidden_fibre_objects": [], "scaled_fibre_objects": [], "layers": {}}
    if options.get("velvet"):
        for mat in sorted({m for o in pool for m in o.data.materials if m is not None and m.node_tree is not None},
                          key=lambda m: m.name):
            report["velvet"][mat.name] = apply_velvet(mat, options["velvet"])
    if options.get("fibres"):
        for ob in pool:
            apply_fibres(ob, options["fibres"], report)
    layers = [(b, strand_settings(options, b)) for b in ("flock", "edge") if options.get(b) is not None]
    if layers:
        occ = Occluders(bpy.data.objects)  # every rendered mesh (body, garments, all hair), not only the pool
        for ob in pool:
            for block, st in layers:
                obj, stats = add_layer(ob, st, seed, "" if block == "flock" else "edge", occ)
                report["layers"][obj.name] = stats
    report["strands_total"] = sum(s["strands"] for s in report["layers"].values())
    h = hashlib.sha256()
    for k in sorted(report["layers"]):
        h.update(report["layers"][k]["sha"].encode())
    report["strand_sha"] = h.hexdigest()[:16]
    report["seconds"] = round(time.time() - t0, 2)
    return report


def apply_spec(hair_spec, objects):
    """Build hook: hair_spec["flock"] (options as above) applied to the built groom objects; None when absent."""
    if not isinstance(hair_spec, dict) or SPEC_KEY not in hair_spec:
        return None
    return apply(hair_spec[SPEC_KEY], objects)


def strip_spec(hair_spec):
    """hair_spec without the "flock" key (for validators that do not know it); the same object when absent."""
    if not isinstance(hair_spec, dict) or SPEC_KEY not in hair_spec:
        return hair_spec
    return {k: v for k, v in hair_spec.items() if k != SPEC_KEY}


def evaluated_hash(objects=None):
    """(curves, points, sha16) over the evaluated "*.flock*" objects at the current frame."""
    dg = bpy.context.evaluated_depsgraph_get()
    h, nc, npnt = hashlib.sha256(), 0, 0
    for o in sorted((o for o in (objects or bpy.data.objects) if "ps_hair_flock" in o), key=lambda o: o.name):
        ev = o.evaluated_get(dg).data
        p = np.zeros(len(ev.points) * 3, dtype=np.float32)
        ev.points.foreach_get("position", p)
        h.update(o.name.encode() + p.tobytes())
        nc += len(ev.curves)
        npnt += len(ev.points)
    return nc, npnt, h.hexdigest()[:16]


def main(argv):
    ap = argparse.ArgumentParser(prog="flock.py")
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--options", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    src, dst = os.path.abspath(a.blend), os.path.abspath(a.out)
    if src == dst or os.path.exists(dst):
        raise SystemExit("flock: --out must be a new file (the input is never changed)")
    if f"{os.sep}assets{os.sep}characters{os.sep}" in dst:
        raise SystemExit("flock: never writes into assets/characters (experiment output only)")
    options = json.load(open(a.options))
    bpy.ops.wm.open_mainfile(filepath=src)
    report = apply(options)
    report["evaluated"] = dict(zip(("curves", "points", "sha"), evaluated_hash()))
    report["input"] = os.path.basename(src)
    bpy.ops.wm.save_as_mainfile(filepath=dst, copy=True)
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1, sort_keys=True)
    print("FLOCK", json.dumps({k: report[k] for k in ("look", "strands_total", "strand_sha", "seconds", "evaluated")}))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
