"""Hoodie garment type (T-058) for ``garment/1``: a loose long-sleeved top (the shared ``top`` construction) plus the
parts that make a hoodie, all driven by the garment spec and the generic body measures (no character data here):

  hood          the hood lying down: a thick rolled rim around the neck whose two front edges meet in a V at the
                chest, and the hood bag resting on the upper back
  pocket        kangaroo pocket: one pouch across the lower front with slanted hand openings at its sides
  drawstrings   two cords from the hood's front edges, hanging down the chest, with tips (aglets)
  bands         ribbed cuffs and hem (the shared bands plus rib ridges on the cuffs)

Spec (``clothing.garments[]`` item, ``type: "hoodie"``; every key optional, defaults scale with the body):
  sleeve_length (default 1.0), ease_m, bands {hem, cuff, rib_ridges, cuff_rib_ridges, cuff_radius_m}
  dropped_shoulder {start (0..0.1, sleeve start along the arm), margin_m} or false (the shared top's sleeves)
  hood {rim_radius_m, rim_rise_m, rim_lift_m, v_depth_m, v_overlap_m, bag_width_m, bag_height_m, bag_depth_m, bag_drop_m}
       T-068 volume (all optional; omitted = the T-058 hood exactly):
         rim_back_radius_m  the rim roll is thicker at the back and sides (blends to rim_radius_m at the V)
         bag_fullness (0..1) the bag keeps a rounded pillow shape: its body side hugs the outer surface of the hoodie
                            and the neck (instead of being flattened to 15 % of its depth), its outside stays round
         bag_rise_m          the bag's top stands up behind the neck, above the rim
         bag_taper (0..1)    the bag narrows towards its rounded bottom (a U-shaped hood lying on the back)
         bag_n               superellipse exponent of the bag outline (2 = ellipse, larger = fuller corners)
         bag_gap_m           gap kept between the bag's body side and the hoodie
         edge_radius_m, edge_drop (0..1)  the soft roll along the bag's opening edge (radius, how far down the bag)
  armhole: "cut" (default) or "closed" (T-068: no armhole in the torso panel; with a dropped shoulder the sleeve and
       torso panels then meet under the arm, closing the underarm gap)
  pocket {width_bottom_m, width_top_m, height_m, above_hem_m, depth_m, opening_slant, rim_radius_m} or false
  drawstrings {spacing_m, length_m, radius_m, tip_length_m, tip_radius_m, swing_m} or false
  materials {main, band, hood, pocket, drawstring, tip}: part material assignments (default: main / band)
"""
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import generator as GEN

TYPE = "hoodie"
PARTS = ("hood", "pocket", "drawstring", "tip")


def _num(d, key, default):
    return float(d.get(key, default)) if isinstance(d, dict) else float(default)


def validate(raw, name):
    """Hoodie-specific keys (the shared top keys are validated by generator.validate)."""
    for block, keys, hi in (("hood", ("rim_radius_m", "rim_rise_m", "rim_lift_m", "v_depth_m", "v_overlap_m", "bag_width_m",
                                      "bag_height_m", "bag_depth_m", "bag_drop_m", "rim_back_radius_m", "bag_rise_m",
                                      "bag_gap_m", "edge_radius_m"), 0.3),
                            ("hood", ("bag_fullness", "bag_taper", "edge_drop"), 1.0),
                            ("pocket", ("width_bottom_m", "width_top_m", "height_m", "above_hem_m", "depth_m",
                                        "rim_radius_m", "opening_slant"), 0.4),
                            ("drawstrings", ("spacing_m", "length_m", "radius_m", "tip_length_m", "tip_radius_m",
                                             "swing_m"), 0.3)):
        v = raw.get(block)
        if v is None or v is False or v is True:
            continue
        if not isinstance(v, dict):
            raise ValueError(f"garment {name}.{block} must be an object or false")
        for key in keys:
            if key in v:
                GEN._number(v[key], f"garment {name}.{block}.{key}", 0.0, hi)
    ds = raw.get("dropped_shoulder")
    if ds not in (None, False):
        if not isinstance(ds, dict):
            raise ValueError(f"garment {name}.dropped_shoulder must be an object or false")
        if "start" in ds:
            GEN._number(ds["start"], f"garment {name}.dropped_shoulder.start", 0.0, 0.1)
        if "margin_m" in ds:
            GEN._number(ds["margin_m"], f"garment {name}.dropped_shoulder.margin_m", 0.0, 0.05)
    hood = raw.get("hood")
    if isinstance(hood, dict) and "bag_n" in hood:
        GEN._number(hood["bag_n"], f"garment {name}.hood.bag_n", 1.5, 6.0)
    if raw.get("armhole", "cut") not in GEN.ARMHOLES:
        raise ValueError(f"garment {name}.armhole must be one of {list(GEN.ARMHOLES)}")
    bands = raw.get("bands")
    if isinstance(bands, dict) and "cuff_rib_ridges" in bands:
        if not isinstance(bands["cuff_rib_ridges"], int) or not 0 <= bands["cuff_rib_ridges"] <= 12:
            raise ValueError(f"garment {name}.bands.cuff_rib_ridges must be an integer in [0, 12]")


def _part_mat(G, cfg, part, fallback, H):
    return GEN._mat_for(G, cfg, part if part in cfg.get("materials", {}) else fallback, H)


def _front_y(bvh, x, z, fallback):
    """y of the outermost surface of `bvh` in front (-y) at (x, z)."""
    loc, _, _, _ = bvh.ray_cast(Vector((x, -5.0, z)), Vector((0, 1, 0)), 10.0)
    return loc.y if loc is not None else fallback


def _back_y(bvh, x, z, fallback):
    loc, _, _, _ = bvh.ray_cast(Vector((x, 5.0, z)), Vector((0, -1, 0)), 10.0)
    return loc.y if loc is not None else fallback


def _solidify(ob, thickness):
    mod = ob.modifiers.new("garment_thickness", "SOLIDIFY")
    mod.thickness, mod.offset = thickness, 1.0
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.select_set(False)


def _volume_bag(G, C, cfg, hc, w, h, d, zc, top_z, rim_r, thick, outer):
    """T-068 full hood bag: a superellipsoid whose body side hugs the outer surface (hoodie + neck) and whose outside
    stays round; it narrows towards the bottom (``bag_taper``) and its top stands up behind the neck (``bag_rise_m``)."""
    from . import shapes as S
    fullness = _num(hc, "bag_fullness", 0.6)
    taper = _num(hc, "bag_taper", 0.0)
    rise = _num(hc, "bag_rise_m", 0.0)
    gap = _num(hc, "bag_gap_m", thick)
    n = _num(hc, "bag_n", 2.0)
    zc = zc + 0.5 * rise
    hh = h + 0.5 * rise
    depth = d * (1.0 + 2.0 * fullness)

    def floor(x, z):
        hit, _ = S.outer_hit(outer, Vector((x, 0.0, z)), Vector((0, 1, 0)), 0.6)
        return hit.y if hit is not None else 0.0

    yb = floor(0.0, zc)
    yc = yb + gap + 0.5 * depth
    bag = S.superellipsoid(G, C, f"garment.{cfg['name']}.hood.bag", (0.0, yc, zc), (w, 0.5 * depth, hh), n, 40, 22)
    for v in bag.data.vertices:
        co = v.co
        down = max(0.0, min(1.0, (zc - co.z) / max(hh, 1e-9)))
        co.x *= 1.0 - taper * down ** 1.5
        target = floor(co.x, co.z) + gap
        if co.y < yc:  # the body side: from the silhouette (s = 0) down onto the clothing (s = 1)
            s = (yc - co.y) / (0.5 * depth)
            co.y = yc + (target - yc) * s
        co.y = max(co.y, target)
    bag.data.update()
    return bag


def _bag_edge(bag, hc, w, h, zc, radius):
    """The hood's opening edge: a U-shaped roll on the outside of the bag, from one upper corner down to
    ``edge_drop`` of the bag and up to the other corner."""
    from mathutils.bvhtree import BVHTree
    from . import shapes as S
    deps = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(bag, deps)
    lo_z = min(v.co.z for v in bag.data.vertices)
    hi_z = max(v.co.z for v in bag.data.vertices)
    half = max(abs(v.co.x) for v in bag.data.vertices)
    drop = _num(hc, "edge_drop", 0.55)
    pts = []
    for k in range(17):
        u = -1 + 2 * k / 16
        x = u * half * 0.8
        z = hi_z - (hi_z - lo_z) * (0.18 + drop * math.sqrt(max(0.0, 1 - u * u)))
        hit, nrm = S.outer_hit([tree], Vector((x, 0.0, z)), Vector((0, 1, 0)), 0.6)
        if hit is not None:
            pts.append(hit + nrm * radius * 0.4)
    return pts


def _hood(G, C, cfg, P, H, fit, top_z, te, thick, bvh, outer=None):
    """Rim (thick rolled tube around the neck, V at the front) and the hood bag lying on the upper back."""
    hc = cfg.get("hood") if isinstance(cfg.get("hood"), dict) else {}
    neck_r = P["neck"]["radius"] * H
    rim_r = _num(hc, "rim_radius_m", 0.016 * fit.head)
    rise = _num(hc, "rim_rise_m", 0.03 * fit.head)       # the rim stands higher at the back of the neck
    top_z = top_z + _num(hc, "rim_lift_m", 0.0)           # the whole rim higher up the neck
    v_depth = _num(hc, "v_depth_m", 0.05 * fit.torso)     # how far the V of the front edges drops below the neckline
    overlap = _num(hc, "v_overlap_m", 0.004 * fit.torso)  # the two front edges cross a little at the V
    r0 = neck_r + te + thick + rim_r * 0.9
    out = []
    # the rim: one open tube from the V's bottom up the right front, around the back of the neck, down the left
    # front to the V again (the two ends cross by `overlap` at the bottom)
    gap = _num(hc, "front_gap", 0.55)  # half angle (rad) of the front opening at the neckline
    pts = []
    ends = []
    n = 40
    for k in range(n + 1):
        a = -(math.pi - gap) + 2 * (math.pi - gap) * k / n  # 0 = back centre
        back = 0.5 + 0.5 * math.cos(a)
        pts.append(Vector((math.sin(a) * r0, math.cos(a) * r0 * (1 + 0.15 * back), top_z + rise * back ** 1.5)))
    ends = (pts[0], pts[-1])

    def chest(p0, sx):  # from a front end of the neckline down to the V
        out = []
        for k in range(1, 9):
            t = k / 8
            x = p0.x * (1 - t) + (-sx) * overlap * t
            z = p0.z + (top_z - v_depth - p0.z) * (t ** 0.85)
            y = min(p0.y + (0 - p0.y) * 0, _front_y(bvh, x, z, p0.y) - rim_r * 0.7)
            out.append(Vector((x, y, z)))
        return out
    pts = list(reversed(chest(ends[0], -1))) + pts + chest(ends[1], 1)
    if "rim_back_radius_m" in hc:  # T-068: thicker roll at the back and sides
        rb = _num(hc, "rim_back_radius_m", rim_r)
        radii = []
        for p in pts:
            back = max(0.0, min(1.0, 0.5 + 0.5 * p.y / max(r0, 1e-9)))
            radii.append(rim_r + (rb - rim_r) * back ** 1.2)
        rim = G.tube(f"garment.{cfg['name']}.hood.rim", pts, radii, [r * 0.85 for r in radii], C,
                     up_hint=(0, 0, 1), seg=16, cap_start="round", cap_end="round")
    else:
        rim = G.tube(f"garment.{cfg['name']}.hood.rim", pts, [rim_r] * len(pts), [rim_r * 0.8] * len(pts), C,
                     up_hint=(0, 0, 1), seg=12, cap_start="round", cap_end="round")
    rim["ps_weight_anchor"] = (0.0, 0.0, top_z)
    out.append(("hood", rim))
    # the bag: a flattened half ellipsoid on the upper back, its top tucked under the rim
    w = _num(hc, "bag_width_m", 0.075 * fit.torso)
    h = _num(hc, "bag_height_m", 0.085 * fit.torso)
    d = _num(hc, "bag_depth_m", 0.02 * fit.torso)
    drop = _num(hc, "bag_drop_m", 0.045 * fit.torso)
    zc = top_z - drop
    yb = _back_y(bvh, 0.0, zc, 0.06)
    if "bag_fullness" in hc:  # T-068: a full, rounded hood lying on the back (not collapsed)
        bag = _volume_bag(G, C, cfg, hc, w, h, d, zc, top_z, rim_r, thick, outer)
    else:
        bag = G.uv_sphere(f"garment.{cfg['name']}.hood.bag", (0, yb - d * 0.35, zc), 1.0, C, 32, 16, (w, d * 1.6, h))
        for v in bag.data.vertices:  # flatten the body-side half onto the back
            if v.co.y < yb:
                v.co.y = yb - (yb - v.co.y) * 0.15
    bag["ps_weight_anchor"] = (0.0, yb, zc)
    out.append(("hood", bag))
    # the seam where the bag's opening edge lies on the back (a soft roll across the bag's lower edge)
    if "bag_fullness" in hc:  # T-068: the opening edge lies on the rounded bag
        er = _num(hc, "edge_radius_m", rim_r * 0.45)
        seam = _bag_edge(bag, hc, w, h, zc, er)
        roll = G.tube(f"garment.{cfg['name']}.hood.edge", seam, [er] * len(seam), [er * 0.75] * len(seam), C,
                      up_hint=(0, 1, 0), seg=10, cap_start="round", cap_end="round")
    else:
        seam = []
        for k in range(13):
            u = -1 + 2 * k / 12
            x = u * w * 0.92
            z = zc - h * 0.55 * math.sqrt(max(0.0, 1 - u * u)) + h * 0.15
            seam.append(Vector((x, _back_y(bvh, x, z, yb) + d * 0.6 * (1 - u * u) + rim_r * 0.3, z)))
        roll = G.tube(f"garment.{cfg['name']}.hood.edge", seam, [rim_r * 0.45] * len(seam), [rim_r * 0.35] * len(seam), C,
                      up_hint=(0, 1, 0), seg=8, cap_start="round", cap_end="round")
    roll["ps_weight_anchor"] = (0.0, yb, zc)
    out.append(("hood", roll))
    return out


def _pocket(G, C, cfg, H, fit, hem_z, bvh):
    """Kangaroo pocket: one pouch on the lower front (a trapezoid, wider at the bottom), slanted hand openings."""
    pc = cfg.get("pocket") if isinstance(cfg.get("pocket"), dict) else {}
    wb = _num(pc, "width_bottom_m", 0.075 * fit.torso)
    wt = _num(pc, "width_top_m", 0.05 * fit.torso)
    ph = _num(pc, "height_m", 0.07 * fit.torso)
    z0 = hem_z + _num(pc, "above_hem_m", 0.018 * fit.torso)
    depth = _num(pc, "depth_m", 0.005 * fit.torso)
    slant = _num(pc, "opening_slant", 0.55)  # share of the side that is the slanted opening
    rr = _num(pc, "rim_radius_m", 0.0028 * fit.torso)
    cols, rows = 24, 12
    verts, faces = [], []
    for j in range(rows + 1):
        v = j / rows
        z = z0 + ph * v
        half = wb + (wt - wb) * v
        for i in range(cols + 1):
            u = -1 + 2 * i / cols
            x = u * half
            bulge = depth * (0.55 + 0.45 * math.sqrt(max(0.0, 1 - u ** 4))) * (0.6 + 0.4 * math.sin(math.pi * min(1.0, v * 1.2)))
            verts.append((x, _front_y(bvh, x, z, -0.08) - bulge, z))
    for j in range(rows):
        for i in range(cols):
            a = j * (cols + 1) + i
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    pouch = G.new_object(f"garment.{cfg['name']}.pocket", verts, faces, C)
    _solidify(pouch, max(cfg["thickness_m"], 0.0015))
    pouch["ps_weight_anchor"] = (0.0, verts[len(verts) // 2][1], z0 + ph * 0.5)
    out = [("pocket", pouch)]
    # rolled edges: top edge and the two slanted openings (the bottom and lower sides are sewn flat)
    def edge(points, name):
        ob = G.tube(f"garment.{cfg['name']}.pocket.{name}", points, [rr] * len(points), [rr * 0.8] * len(points), C,
                    up_hint=(0, -1, 0), seg=8, cap_start="round", cap_end="round")
        ob["ps_weight_anchor"] = (0.0, points[len(points) // 2].y, points[len(points) // 2].z)
        out.append(("pocket", ob))
    row_top = rows * (cols + 1)
    edge([Vector(verts[row_top + i]) + Vector((0, -rr * 0.6, 0)) for i in range(cols // 8, cols - cols // 8 + 1)], "edge.top")
    j0 = int(round(rows * (1 - slant)))
    for side, i in (("L", cols), ("R", 0)):
        pts = [Vector(verts[j * (cols + 1) + i]) + Vector((0, -rr * 0.6, 0)) for j in range(j0, rows + 1)]
        # the opening runs diagonally inwards to the top edge
        sx = 1 if side == "L" else -1
        pts = [p + Vector((-sx * (wb - wt) * 0.6 * (k / max(1, len(pts) - 1)), 0, 0)) for k, p in enumerate(pts)]
        edge(pts, f"opening.{side}")
    return out


def _drawstrings(G, C, cfg, H, fit, top_z, v_depth, bvh):
    dc = cfg.get("drawstrings") if isinstance(cfg.get("drawstrings"), dict) else {}
    spacing = _num(dc, "spacing_m", 0.022 * fit.torso)
    length = _num(dc, "length_m", 0.07 * fit.torso)
    r = _num(dc, "radius_m", 0.0022 * fit.torso)
    tl, tr = _num(dc, "tip_length_m", 0.009 * fit.torso), _num(dc, "tip_radius_m", 0.0028 * fit.torso)
    swing = _num(dc, "swing_m", 0.004 * fit.torso)
    out = []
    for sx, side in ((1, "L"), (-1, "R")):
        z0 = top_z - v_depth * 0.55
        pts = []
        for k in range(10):
            t = k / 9
            x = sx * (spacing + swing * math.sin(math.pi * t) * 0.6)
            z = z0 - length * t
            pts.append(Vector((x, _front_y(bvh, x, z, -0.08) - r * 1.6 - 0.0025 * fit.torso * math.sin(math.pi * t * 0.8), z)))
        cord = G.tube(f"garment.{cfg['name']}.drawstring.{side}", pts, [r] * len(pts), [r] * len(pts), C,
                      up_hint=(0, -1, 0), seg=8, cap_start="round", cap_end=None)
        cord["ps_weight_anchor"] = tuple(pts[0])
        out.append(("drawstring", cord))
        d = (pts[-1] - pts[-2]).normalized()
        tip_pts = [pts[-1] + d * (tl * k / 4) for k in range(5)]
        tip = G.tube(f"garment.{cfg['name']}.drawstring.tip.{side}", tip_pts, [tr] * 5, [tr] * 5, C,
                     up_hint=(0, -1, 0), seg=10, cap_start="round", cap_end="round")
        tip["ps_weight_anchor"] = tuple(pts[0])
        out.append(("tip", tip))
    return out


class _DroppedShoulderFit:
    """The body fit with the sleeves starting at the shoulder joint (a hoodie's dropped shoulder) and a wider sleeve
    margin, so the shell covers the whole shoulder cap and underarm when the arm is lowered. Everything else is the
    shared fit."""

    def __init__(self, fit, start, margin):
        self._fit, self._start, self._margin = fit, start, margin

    def __getattr__(self, name):
        return getattr(self._fit, name)

    def in_sleeve(self, c, t0=0.10, t1=1.0, margin=None):
        return self._fit.in_sleeve(c, min(t0, self._start), t1, self._margin if margin is None else margin)


def build(C, body, cfg, P, H, J, G, fit):
    """The hoodie: shared top construction + hood, kangaroo pocket, drawstrings, cuff ribs. Returns (objects, covered
    body faces)."""
    top = dict(cfg)
    top.setdefault("sleeve_length", 1.0)
    bands = top.get("bands", {"hem": True, "cuff": True, "rib_ridges": 3})
    if bands is True:
        bands = {"hem": True, "cuff": True}
    top["bands"] = bands
    top["collar"] = "none"
    shoulder = cfg.get("dropped_shoulder", {"start": 0.0, "margin_m": 0.02})
    top_fit = fit
    if shoulder:
        top_fit = _DroppedShoulderFit(fit, _num(shoulder, "start", 0.0), _num(shoulder, "margin_m", 0.02) * fit.arm)
    objects, covered = GEN._top(C, body, top, P, H, J, G, top_fit)
    for key in ("_embroidery_report", "_buttons_report"):
        if key in top:
            cfg[key] = top[key]
    main = objects[0]
    te, thick = cfg["ease_m"] * fit.torso, cfg["thickness_m"]
    top_z = max(P["neck"]["base_z"], P["torso"]["levels"][-1][0]) * H
    hem_z = float(cfg.get("hem_z_m", P["torso"]["levels"][2][0] * H))
    deps = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(main, deps)
    # ribbed cuffs: ridges up the sleeve from the cuff band
    ridges = int(bands.get("cuff_rib_ridges", 0)) if isinstance(bands, dict) else 0
    sleeve = float(top["sleeve_length"])
    for side in ("L", "R"):
        a, b = J[f"shoulder.{side}"], J[f"wrist.{side}"]
        arm_len = (b - a).length
        for k in range(ridges):
            t = sleeve - (k + 1) * cfg["seam_radius_m"] * 2.4 / max(arm_len, 1e-6)
            ob = GEN._limb_ring(G, C, f"garment.{cfg['name']}.rib.cuff.{side}_{k + 1}", a.lerp(b, t), b - a,
                                GEN._arm_radius(P, H, t), cfg["ease_m"] * fit.arm + thick + 0.002 * fit.arm,
                                cfg["seam_radius_m"] * 0.65)
            GEN._feature(objects, ob, cfg, "band", GEN._mat_for(G, cfg, "band", H), G)
    extra = []
    hood = cfg.get("hood", True)
    hc = hood if isinstance(hood, dict) else {}
    v_depth = _num(hc, "v_depth_m", 0.05 * fit.torso)
    if hood is not False:
        extra += _hood(G, C, cfg, P, H, fit, top_z, te, thick, bvh, outer=[bvh, BVHTree.FromObject(body, deps)])
    if cfg.get("pocket", True) is not False:
        extra += _pocket(G, C, cfg, H, fit, hem_z, bvh)
    if cfg.get("drawstrings", True) is not False:
        extra += _drawstrings(G, C, cfg, H, fit, top_z, v_depth, bvh)
    mats = {}  # parts without their own assignment use the main material (generator._assignment); tips the cord's
    for part, ob in extra:
        key = "drawstring" if part == "tip" and "tip" not in cfg.get("materials", {}) else part
        if key not in mats:
            mats[key] = GEN._mat_for(G, cfg, key, H)
        GEN._feature(objects, ob, cfg, part, mats[key], G)
    return objects, covered
