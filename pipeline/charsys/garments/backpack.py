"""Backpack garment type (T-068) for ``garment/1``: a small soft backpack worn on the upper back over the clothes
built before it in the spec, with two straps that run over the shoulders, down the front of the chest and back under
the arms. Worn through the clothing list (not ``accessories``) so the straps follow the body through the shared
weight transfer: the bag is rigid to the upper back, every strap vertex copies the weights of the nearest torso
vertex (never an arm vertex), so the straps ride on the shoulders without stretching with the arms.

  main       the bag: a rounded box (superellipsoid) whose body side is flattened onto the outer clothing
  pocket     a front pocket on the lower half of the bag
  zip        the main zip over the top of the bag and the pocket zip, each with a puller
  strap      two straps (flat, rounded edges) from the top of the bag over the shoulders to the bag's lower corners
  handle     a short loop on top (optional)

Spec (``clothing.garments[]`` item, ``type: "backpack"``; every key optional, defaults scale with the torso):
  width_m, height_m, depth_m, top_drop_m (bag top below the shoulder line), clearance_m (gap to the clothing),
  roundness (superellipse exponent: 2 = egg .. 5 = boxy), puff (0..1, rounded front)
  pocket {width, height (shares of the bag), depth_m, drop (share: pocket centre below the bag centre)} or false
  zip {radius_m, puller_m} or false
  straps {width_m, thickness_m, lift_m (gap above the clothing's surface fibres), layer_gap_m (largest gap between
          clothing layers the strap still lies on; a larger one, e.g. to a sleeve, is not crossed), shoulder (0..1: strap position from the neck to the shoulder joint), front_drop_m
          (how far down the chest the strap shows before it turns under the arm)} or false
  handle {radius_m, width_m} or false
  materials {main, pocket (default main), strap (default main), zip (default band, else main), puller (default zip),
             handle (default strap)}
"""
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree

import bpy

from . import generator as GEN
from . import shapes as S

TYPE = "backpack"
_FALLBACK = {"pocket": ("pocket",), "strap": ("strap",), "zip": ("zip", "band"), "puller": ("puller", "zip", "band"),
             "handle": ("handle", "strap")}


def _num(d, key, default):
    return float(d.get(key, default)) if isinstance(d, dict) else float(default)


def validate(raw, name):
    for key in ("width_m", "height_m", "depth_m", "top_drop_m", "clearance_m"):
        if key in raw:
            GEN._number(raw[key], f"garment {name}.{key}", 0.0, 0.5)
    if "roundness" in raw:
        GEN._number(raw["roundness"], f"garment {name}.roundness", 1.5, 8.0)
    if "puff" in raw:
        GEN._number(raw["puff"], f"garment {name}.puff", 0.0, 1.0)
    for block, keys in (("pocket", ("width", "height", "depth_m", "drop")),
                        ("zip", ("radius_m", "puller_m")),
                        ("straps", ("width_m", "thickness_m", "shoulder", "front_drop_m", "lift_m", "layer_gap_m")),
                        ("handle", ("radius_m", "width_m"))):
        v = raw.get(block)
        if v is None or v is False or v is True:
            continue
        if not isinstance(v, dict):
            raise ValueError(f"garment {name}.{block} must be an object or false")
        for key in keys:
            if key in v:
                GEN._number(v[key], f"garment {name}.{block}.{key}", 0.0, 1.0 if key in ("width", "height", "drop",
                                                                                          "shoulder") else 0.3)
    if raw.get("mask_body"):
        raise ValueError(f"garment {name}.mask_body: a backpack covers no skin")


def _part_mat(G, cfg, part, H):
    mats = cfg.get("materials", {})
    key = next((k for k in _FALLBACK.get(part, (part,)) if k in mats), "main")
    return GEN._mat_for(G, cfg, key, H)


def _superellipsoid(G, C, name, centre, radii, n, segs=40, rings=24):
    return S.superellipsoid(G, C, name, centre, radii, n, segs, rings)


def _outer_objects(body, worn, skip=("drawstring", "tip")):
    """BVHs of the body and of every garment piece built before this item (the bag sits over them), except the parts
    in ``skip``."""
    deps = bpy.context.evaluated_depsgraph_get()
    bvhs = [BVHTree.FromObject(body, deps)]
    for ob in worn:
        if ob.type == "MESH" and ob.get("ps_garment_part") not in skip:
            bvhs.append(BVHTree.FromObject(ob, deps))
    return bvhs


def _torso_vertices(body, P, H, fit):
    """Body vertices of the torso and shoulders (no arm, neck or leg vertices): the straps' weight sources."""
    tf = fit.torso
    shoulder_z = P["shoulder"]["z"] * H
    hip_z = P["leg"]["hip_z"] * H
    neck_top = P["neck"]["base_z"] * H + 0.03 * tf
    joint_x = P["shoulder"]["joint_x"] * H
    return [v.index for v in body.data.vertices
            if hip_z < v.co.z < neck_top and abs(v.co.x) < 0.92 * joint_x and
            (v.co.z < shoulder_z - 0.5 * GEN.ARMHOLE_DEPTH_ROOT_RADII * fit.arm_root or abs(v.co.x) < 0.8 * joint_x)]


def build(C, body, cfg, P, H, J, G, fit, worn=()):
    """The backpack over the already built garment pieces ``worn``. Returns (objects, covered body faces = none)."""
    tf = fit.torso
    width = float(cfg.get("width_m", 0.15 * tf))
    height = float(cfg.get("height_m", 0.16 * tf))
    depth = float(cfg.get("depth_m", 0.06 * tf))
    clear = float(cfg.get("clearance_m", 0.003 * tf))
    shoulder_z = P["shoulder"]["z"] * H
    top_z = shoulder_z - float(cfg.get("top_drop_m", 0.03 * tf))
    zc = top_z - 0.5 * height
    roundness = float(cfg.get("roundness", 3.2))
    puff = float(cfg.get("puff", 0.5))
    bvhs = _outer_objects(body, worn)
    body_bvh = bvhs[0]

    def back_y(x, z):
        hit, _ = S.outer_hit(bvhs, Vector((x, 0.0, z)), Vector((0, 1, 0)), 0.6)
        return hit.y if hit is not None else GEN._torso_dims(P, H, z)[2]

    yb = max(back_y(0.0, zc), back_y(0.0, zc + 0.3 * height), back_y(0.0, zc - 0.3 * height))
    yc = yb + clear + 0.5 * depth
    name = cfg["name"]
    bag = _superellipsoid(G, C, f"garment.{name}.main", (0.0, yc, zc), (0.5 * width, 0.5 * depth, 0.5 * height),
                          roundness)
    # flatten the body side onto the clothing; round the outer face (puff)
    for v in bag.data.vertices:
        co = v.co
        floor = back_y(co.x, co.z) + clear
        if co.y < yc:
            share = (yc - co.y) / (0.5 * depth)
            co.y = max(floor, yc - 0.5 * depth * share ** 3 * 0.35 - (yc - floor) * min(1.0, share) * 0.65)
            co.y = max(co.y, floor)
        else:
            u = max(abs(co.x) / (0.5 * width), abs(co.z - zc) / (0.5 * height))
            co.y += (1 - min(1.0, u) ** 2) * puff * 0.12 * depth
    bag.data.update()
    pieces = [("main", bag)]
    deps = bpy.context.evaluated_depsgraph_get()
    bag_bvh = BVHTree.FromObject(bag, deps)

    def on_bag(x, z, lift):
        hit, nrm = S.outer_hit([bag_bvh], Vector((x, yc, z)), Vector((0, 1, 0)), 0.5)
        if hit is None:
            return None, None
        return hit + nrm * lift, nrm

    # front pocket
    pc = cfg.get("pocket", {})
    pocket_top = None
    if pc is not False:
        pc = pc if isinstance(pc, dict) else {}
        pw, ph = _num(pc, "width", 0.72) * width, _num(pc, "height", 0.42) * height
        pd = _num(pc, "depth_m", 0.35 * depth)
        pz = zc - _num(pc, "drop", 0.22) * height
        y_front = max(v.co.y for v in bag.data.vertices)
        pocket = _superellipsoid(G, C, f"garment.{name}.pocket", (0.0, y_front - 0.45 * pd, pz),
                                 (0.5 * pw, 0.5 * pd, 0.5 * ph), max(2.4, roundness - 0.4), 32, 16)
        pieces.append(("pocket", pocket))
        pocket_top = (pw, pz + 0.5 * ph, y_front - 0.45 * pd, pd)
    # zips
    zc_cfg = cfg.get("zip", {})
    if zc_cfg is not False:
        zc_cfg = zc_cfg if isinstance(zc_cfg, dict) else {}
        zr = _num(zc_cfg, "radius_m", 0.0016 * tf)
        pull = _num(zc_cfg, "puller_m", 0.007 * tf)
        # main zip: over the top of the bag from one side to the other, on the front edge of the top
        path = []
        for k in range(25):
            a = math.pi * (0.08 + 0.84 * k / 24)
            x = -0.47 * width * math.cos(a)
            z = zc + 0.47 * height * math.sin(a) ** (2.0 / roundness)
            p, n = on_bag(x, z, zr * 0.6)
            if p is not None:
                path.append(p)
        if len(path) > 4:
            pieces.append(("zip", G.tube(f"garment.{name}.zip.main", path, [zr] * len(path), [zr * 0.7] * len(path),
                                         C, up_hint=(0, 1, 0), seg=6, cap_start="round", cap_end="round")))
            end = path[-1]
            pieces.append(("puller", G.uv_sphere(f"garment.{name}.zip.puller.main", tuple(end + Vector((0, zr, -pull * 0.6))),
                                                 1.0, C, 12, 8, (pull * 0.28, pull * 0.12, pull * 0.6))))
        if pocket_top is not None:
            pw, ptz, pyc, pd = pocket_top
            deps = bpy.context.evaluated_depsgraph_get()
            pocket_ob = next(ob for part, ob in pieces if part == "pocket")
            pbvh = BVHTree.FromObject(pocket_ob, deps)
            pz_path = []
            for k in range(15):
                u = -0.78 + 1.56 * k / 14
                hit, nrm = S.outer_hit([pbvh], Vector((u * 0.5 * pw, pyc, ptz - 0.12 * (ptz - zc))), Vector((0, 1, 0)), 0.5)
                if hit is not None:
                    pz_path.append(hit + nrm * zr * 0.6)
            if len(pz_path) > 4:
                pieces.append(("zip", G.tube(f"garment.{name}.zip.pocket", pz_path, [zr] * len(pz_path),
                                             [zr * 0.7] * len(pz_path), C, up_hint=(0, 1, 0), seg=6)))
                end = pz_path[-1]
                pieces.append(("puller", G.uv_sphere(f"garment.{name}.zip.puller.pocket",
                                                     tuple(end + Vector((0, zr, -pull * 0.6))), 1.0, C, 12, 8,
                                                     (pull * 0.28, pull * 0.12, pull * 0.6))))
    # handle loop on top
    hc = cfg.get("handle", {})
    if hc is not False:
        hc = hc if isinstance(hc, dict) else {}
        hr = _num(hc, "radius_m", 0.0028 * tf)
        hw = _num(hc, "width_m", 0.22 * width)
        top_pt = max((v.co for v in bag.data.vertices if abs(v.co.x) < 0.05 * width), key=lambda c: c.z)
        pts = [Vector((-hw, top_pt.y - 0.1 * depth, top_pt.z - hr)),
               Vector((-0.6 * hw, top_pt.y - 0.1 * depth, top_pt.z + 2.5 * hr)),
               Vector((0.6 * hw, top_pt.y - 0.1 * depth, top_pt.z + 2.5 * hr)),
               Vector((hw, top_pt.y - 0.1 * depth, top_pt.z - hr))]
        pts = S.catmull_rom(pts, 6)
        pieces.append(("handle", G.tube(f"garment.{name}.handle", pts, [hr * 1.6] * len(pts), [hr * 0.7] * len(pts),
                                        C, up_hint=(0, 1, 0), seg=8)))
    # straps
    sc = cfg.get("straps", {})
    strap_objects = []
    if sc is not False:
        sc = sc if isinstance(sc, dict) else {}
        sw = _num(sc, "width_m", 0.02 * tf)
        lift = _num(sc, "lift_m", 0.004 * tf)  # above the clothing's surface fibres
        st = _num(sc, "thickness_m", 0.004 * tf)
        neck_r = P["neck"]["radius"] * H
        joint_x = P["shoulder"]["joint_x"] * H
        xs = neck_r + _num(sc, "shoulder", 0.45) * (joint_x - neck_r)
        arm_bottom = shoulder_z - GEN.ARMHOLE_DEPTH_ROOT_RADII * fit.arm_root
        front_drop = _num(sc, "front_drop_m", 0.6 * (shoulder_z - arm_bottom))
        # straps run under a hood lying on the back (the hood is not a surface they ride on)
        strap_bvhs = _outer_objects(body, worn, skip=("drawstring", "tip", "hood"))[1:]
        # the strap path is projected from the torso skin (never an arm) through the clothing layers lying on it
        torso_set = set(_torso_vertices(body, P, H, fit))
        tfaces = [tuple(p.vertices) for p in body.data.polygons if all(i in torso_set for i in p.vertices)]
        torso_bvh = BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices], tfaces, all_triangles=False)
        stack_gap = _num(sc, "layer_gap_m", 0.02 * tf)
        for sx, side in ((1, "L"), (-1, "R")):
            w_low, f_low, b_low = GEN._torso_dims(P, H, arm_bottom)
            ctrl = [Vector((sx * 0.62 * xs, yb + clear, top_z - 0.12 * height)),   # under the bag's top edge
                    Vector((sx * xs, 0.55 * GEN._torso_dims(P, H, shoulder_z)[2], shoulder_z + 0.02 * tf)),
                    Vector((sx * xs * 1.02, 0.0, shoulder_z + 0.04 * tf)),        # on top of the shoulder
                    Vector((sx * xs * 1.08, -0.6 * GEN._torso_dims(P, H, shoulder_z)[1], shoulder_z)),
                    Vector((sx * xs * 1.18, -f_low * 0.9, shoulder_z - 0.55 * front_drop)),
                    Vector((sx * xs * 1.3, -f_low * 0.75, shoulder_z - front_drop)),  # down the front of the chest
                    Vector((sx * w_low * 0.98, -f_low * 0.1, shoulder_z - front_drop - 0.03 * tf)),  # under the arm
                    Vector((sx * w_low * 0.92, b_low * 0.6, zc - 0.05 * height)),
                    Vector((sx * 0.46 * width, yb + clear, zc - 0.12 * height))]   # into the bag's side
            curve = S.resample(S.catmull_rom(ctrl, 10), 72)
            pts, nrm = [], []
            for p in curve:
                loc, normal, _, _ = torso_bvh.find_nearest(p)
                if loc is None:
                    continue
                hit, hn = S.layer_top(strap_bvhs, loc, normal, max_gap=stack_gap)
                pts.append(hit + hn * (0.5 * st + clear + lift))
                nrm.append(hn)
            # smooth the projected path and its normals a little
            for _ in range(3):
                pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) * 0.25 for i in range(1, len(pts) - 1)] + [pts[-1]]
                nrm = [nrm[0]] + [(nrm[i - 1] + nrm[i] * 2 + nrm[i + 1]).normalized() for i in range(1, len(nrm) - 1)] + [nrm[-1]]
            strap = S.ribbon(G, C, f"garment.{name}.strap.{side}", pts, nrm, sw, st, round_share=0.6)
            pieces.append(("strap", strap))
            strap_objects.append(strap)
    # weights: the bag, pocket, zips and handle are rigid to the upper back; straps copy the nearest torso vertex
    anchor_hit, _, _, _ = body_bvh.find_nearest(Vector((0.0, yb, zc + 0.25 * height)))
    anchor = tuple(anchor_hit) if anchor_hit is not None else (0.0, yb, zc)
    torso = _torso_vertices(body, P, H, fit)
    mats = {}
    objects = []
    for part, ob in pieces:
        if part == "strap":
            S.store_body_vertices(ob, body, torso)
        else:
            ob["ps_weight_anchor"] = anchor
        if part not in mats:
            mats[part] = _part_mat(G, cfg, part, H)
        GEN._feature(objects, ob, cfg, part, mats[part], G)
    for ob in objects:  # the outer-garment clearance is built in; the shared rest clearance must not re-project
        ob[GEN.CLEARANCE_PROP] = 0.0
    cfg["_backpack_report"] = {"bag_centre_m": [0.0, round(yc, 4), round(zc, 4)],
                               "size_m": [round(width, 4), round(depth, 4), round(height, 4)],
                               "straps": len(strap_objects), "torso_weight_sources": len(torso)}
    return objects, set()
