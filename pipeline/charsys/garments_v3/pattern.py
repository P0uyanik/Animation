"""``garment/3`` ``skirt_pattern`` (``dress``, ``skirt``; T-126): a knitted relief of cables and leaf panels.

A cable or leaf stitch stands proud of its ground by a few millimetres, which a bump map does not show at figure
scale. ``skirt_pattern`` refines the built (and draped) skirt piece and moves its vertices outward by a pattern that
repeats ``panels`` times round the skirt. One panel is a rope cable (``cable_share`` of the panel: two strands that
cross ``twists`` times down the skirt, between two thin edge ribs) and a leaf column (a stem with ``leaf_rows`` leaves,
each a pointed lobe with veins rising outward at ``leaf_slope``). The front centre carries a cable.

  {"panels": 8, "relief_m": 0.003, "cable_share": 0.34, "twists": 3.5, "leaf_rows": 5, "leaf_slope": 0.55,
   "top": 0.94, "bottom_m": 0.02, "subdivide": 2}
``top``: the share of the skirt height below which the pattern is full (it fades out into the waist gathers above);
``bottom_m``: the plain strip at the hem (under a ``hem_rib`` band); ``subdivide``: refinement levels of the piece
(each level halves the edge length; 2 gives about 2 mm on a doll-sized skirt). ``relief_m`` is multiplied by the leg
scale of the body. Both walls of the solidified piece move together and only outward, so the thickness is kept and
nothing moves towards the body.
Character-agnostic: the pattern is laid on the piece's own height and on the angle about its own vertical axis."""
import math

import bmesh

PATTERN = {"panels": 8, "relief_m": 0.003, "cable_share": 0.34, "twists": 3.5, "leaf_rows": 5, "leaf_slope": 0.55,
           "top": 0.94, "bottom_m": 0.02, "subdivide": 2}
RANGES = {"relief_m": (0.0, 0.01), "cable_share": (0.0, 1.0), "twists": (0.0, 12.0), "leaf_slope": (0.0, 2.0),
          "top": (0.2, 1.0), "bottom_m": (0.0, 0.2)}
INTS = {"panels": (1, 32), "leaf_rows": (0, 24), "subdivide": (0, 3)}


def validate(v, name):
    from garments import generator as GEN
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.skirt_pattern must be true or an object")
    for key in v:
        if key not in PATTERN:
            raise ValueError(f"garment {name}.skirt_pattern.{key}: unknown field (known: {sorted(PATTERN)})")
        if key in INTS:
            low, high = INTS[key]
            if not isinstance(v[key], int) or isinstance(v[key], bool) or not low <= v[key] <= high:
                raise ValueError(f"garment {name}.skirt_pattern.{key} must be an integer in [{low}, {high}]")
        else:
            GEN._number(v[key], f"garment {name}.skirt_pattern.{key}", *RANGES[key])


def _dome(d):
    """Yarn-strand profile: 1 on the centre line, 0 from one half-width out, with steep sides (a strand stands on
    the ground stitch like a cord, it does not blend into it)."""
    return max(0.0, 1.0 - d * d) ** 0.3


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def height(u, v, st):
    """Relief 0..1 at panel coordinate ``u`` (0..1 across one panel) and ``v`` (0 hem .. 1 waist)."""
    share = float(st["cable_share"])
    if u < share:
        x = u / share
        rib = 0.5 * max(_dome((x - 0.06) / 0.05), _dome((x - 0.94) / 0.05))
        phi = 2.0 * math.pi * float(st["twists"]) * v
        s, c = math.sin(phi), math.cos(phi)
        a = _dome((x - (0.5 + 0.2 * s)) / 0.21) * (0.72 + 0.28 * c)  # each strand rides over the other in turn
        b = _dome((x - (0.5 - 0.2 * s)) / 0.21) * (0.72 - 0.28 * c)
        return max(rib, a, b)
    rows = int(st["leaf_rows"])
    if rows == 0 or share >= 1.0:
        return 0.0
    d = abs((u - share) / (1.0 - share) - 0.5) * 2.0  # 0 on the stem, 1 at the panel edge
    stem = 0.7 * _dome(d / 0.09)
    r = v * rows
    f = r - math.floor(r)  # 0 at the leaf base, 1 at its tip
    lobe = 0.86 * math.sin(math.pi * min(1.0, f * 1.15)) ** 0.6 * (1.0 - 0.35 * f)  # leaf half-width at this height
    if d >= lobe:
        return stem
    edge = _smooth((lobe - d) / 0.07)
    t = (f * 3.0 - float(st["leaf_slope"]) * d * 3.0) % 1.0  # veins rise from the stem outward
    vein = _dome((t - 0.5) / 0.32)
    return max(stem, edge * (0.3 + 0.7 * vein))


def apply(cfg, mine, fit):
    st = dict(PATTERN, **(cfg["skirt_pattern"] if isinstance(cfg["skirt_pattern"], dict) else {}))
    part = "skirt" if cfg["type"] == "dress" else "main"
    ob = next((o for o in mine if o.get("ps_garment_part") == part and o.type == "MESH"), None)
    if ob is None:
        raise ValueError(f"garment {cfg['name']}.skirt_pattern: the item has no skirt piece")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    level = int(st["subdivide"])
    if level:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2 ** level - 1, use_grid_fill=True)
    n = len(bm.verts)
    cx, cy = sum(v.co.x for v in bm.verts) / n, sum(v.co.y for v in bm.verts) / n
    z0, z1 = min(v.co.z for v in bm.verts), max(v.co.z for v in bm.verts)
    span = max(z1 - z0, 1e-9)
    panels, relief = int(st["panels"]), float(st["relief_m"]) * fit.leg
    plain, top = float(st["bottom_m"]) * fit.leg, float(st["top"])
    shift = 0.5 * float(st["cable_share"])  # the front centre (-Y) is the middle of a cable
    peak = 0.0
    for v in bm.verts:
        dx, dy = v.co.x - cx, v.co.y - cy
        r = math.hypot(dx, dy)
        if r < 1e-9:
            continue
        t = (v.co.z - z0) / span
        fade = _smooth((v.co.z - z0 - 0.6 * plain) / max(0.4 * plain, 1e-9)) * _smooth((1.0 - t) / max(1.0 - top, 1e-9))
        if fade <= 0.0:
            continue
        u = (math.atan2(dx, -dy) / (2.0 * math.pi) * panels + shift) % 1.0
        h = relief * fade * height(u, t, st)
        peak = max(peak, h)
        v.co.x += dx / r * h
        v.co.y += dy / r * h
    bm.normal_update()
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return {"piece": ob.name, "panels": panels, "relief_m": round(relief, 5), "peak_m": round(peak, 5),
            "vertices": len(ob.data.vertices), "subdivide": level}
