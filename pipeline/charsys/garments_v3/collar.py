"""``garment/3`` ``collar_seat`` (``top`` / ``shirt`` / ``dress`` with a round collar): a collar that sits on the
neckline and lies on the garments under it, at rest and when an arm reaches.

The ``garment/1`` round collar is a flat cone cleared off the body by a fixed lift; over a vest it stands off the
shoulders like a plate, its nearest skin is the neck and the upper arm, so it turns with the head and is carried up
by a reaching arm. ``collar_seat`` rebuilds the collar's shape on its own vertex grid:
  - the inner edge is set on the neckline: the collar's inner radius at the top of the item's main piece, raised
    where an ``over`` item's own neckline stands higher right in front of it;
  - each column of the grid is a strip hinged at the neckline and laid outwards row by row: it starts as drooped as
    it can (at most ``max_droop_deg`` below the horizontal) and each row takes the steepest angle within
    ``bend_deg`` of the row before it that stays clear of what is under it - the body, the item's own main piece
    (``gap_m``), the panels (``over_gap_m``) and rolled edges of the ``over`` items. The collar therefore lies on
    the layers with a bounded bend per row (it rides over a vest's neckline or the head of a puffed sleeve and
    bridges small dips), and the bend is spread over the rows instead of sitting in one crease at the neck;
  - the lay is averaged round the collar ``smooth`` times, so it is one even surface; a strip the averaging pushed
    into a layer is raised back out of it, and no row then droops more than ``step_deg`` below its neighbour's;
  - both sheets of the solidified collar are rebuilt at the collar's thickness along the new surface normals.
Binding (``bind``): the collar is carried by ``chest_bone``; towards the outer edge and the sides up to
``shoulder_share`` of the weight goes to the side's ``shoulder_bone``, so a raised shoulder lifts the collar's side
and the bend is spread towards the tips. No head, neck or arm weight. For the configured reach of each arm
(``reach``: the ``garment/2`` reach corrective settings; ``over`` defaults to the item itself plus the seat's
``over``) a shape key keeps the collar over the posed layers; the push is spread over the collar (``reach_smooth``)
and driven by the arm's forward swing from 0 (``gate`` 0), so a half reach gets about half of it.

  {"over": ["vest"], "gap_m": 0.0015, "over_gap_m": 0.004, "max_droop_deg": 80, "bend_deg": 30, "smooth": 4,
   "step_deg": 6, "reach_smooth": 8, "chest_bone": "DEF-spine.003", "shoulder_bone": "DEF-shoulder.{side}",
   "shoulder_share": 0.35, "reach": {"deg": -75.0}}
Character-agnostic: sizes from the spec's collar block and the body measures, bones by configured name."""
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from garments import generator as GEN
from garments_v2 import correctives as CORR

SEAT = {"over": [], "gap_m": 0.0015, "over_gap_m": 0.004, "max_droop_deg": 80.0, "bend_deg": 30.0, "smooth": 4,
        "step_deg": 6.0, "reach_smooth": 8, "chest_bone": "DEF-spine.003", "shoulder_bone": "DEF-shoulder.{side}",
        "shoulder_share": 0.35, "reach": {"deg": -75.0}}
RANGES = {"gap_m": (0.0, 0.02), "over_gap_m": (0.0, 0.03), "max_droop_deg": (0.0, 89.0), "step_deg": (0.5, 45.0),
          "bend_deg": (0.0, 90.0), "shoulder_share": (0.0, 0.8)}
MIN_DROOP_DEG = -45.0  # a strip may rise this far above the horizontal to clear what is under it
HEAD_GAP = 0.001  # clearance kept from skin that faces down on the collar (jaw, back of the head)
OWN_REACH, OVER_REACH = 0.006, 0.04  # how far above a collar point a piece of the item / an over item is looked for
EDGE_GAP = 0.001  # clearance kept from the rolled edges of the ``over`` items
ROWS = 6  # garment/1 _round_collar: (cols + 1) x (ROWS + 1) grid, column-major, solidified into two sheets


def validate(v, name, item_names=()):
    if v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.collar_seat must be true or an object")
    for key in v:
        if key not in SEAT:
            raise ValueError(f"garment {name}.collar_seat.{key}: unknown field (known: {sorted(SEAT)})")
        if key in RANGES:
            GEN._number(v[key], f"garment {name}.collar_seat.{key}", *RANGES[key])
        if key in ("smooth", "reach_smooth") and (not isinstance(v[key], int) or isinstance(v[key], bool)
                                                  or not 0 <= v[key] <= 40):
            raise ValueError(f"garment {name}.collar_seat.{key} must be an integer in [0, 40]")
    over = v.get("over", [])
    if not isinstance(over, list) or any(not isinstance(x, str) for x in over):
        raise ValueError(f"garment {name}.collar_seat.over must be a list of item names")
    for x in over:
        if item_names and x not in item_names:
            raise ValueError(f"garment {name}.collar_seat.over: no item named {x!r}")
    if not isinstance(v.get("chest_bone", ""), str) or "{side}" not in v.get("shoulder_bone", "{side}"):
        raise ValueError(f"garment {name}.collar_seat: chest_bone is a bone name, shoulder_bone contains '{{side}}'")
    if "reach" in v:
        CORR.validate({"reach": dict(v["reach"])}, f"{name}.collar_seat")


def settings(raw):
    st = dict(SEAT, **(raw if isinstance(raw, dict) else {}))
    st["reach"] = dict(SEAT["reach"], **(st.get("reach") or {}))
    return st


def _bvh(ob):
    mw = ob.matrix_world
    return BVHTree.FromPolygons([mw @ v.co for v in ob.data.vertices], [tuple(p.vertices) for p in ob.data.polygons],
                                all_triangles=False)


class Layers:
    """What lies under a collar. The body is a closed surface (signed distance to its nearest point); garment pieces
    are thin open shells, where the nearest point cannot tell above from below, so they are probed along the collar
    strip's own normal (a piece above the point within that piece's reach, or closer than its gap below it, is in
    the way) and by the strip's segments (``crossed``). The item's own main piece gets a short reach (its puffed
    sleeve may bulge above a collar lying on the shoulder); the ``over`` items a long one: the collar never lies
    under them."""

    def __init__(self, body, floor, shells):
        self.body, self.floor, self.shells = body, floor, shells  # shells: [(bvh, gap, reach above)]

    def height(self, p, n, probe=None):
        """Clearance left at p (strip normal n): >= 0 when p is clear of everything by at least the gaps. With
        ``probe`` (m) the distance down to the nearest shell within it is measured too (for the report)."""
        loc, nrm, _, _ = self.body.find_nearest(p)
        nrm = nrm.normalized()
        # skin under the collar (shoulders, chest) is covered by the item itself: keep the floor from it; skin above
        # it (the jaw and the back of a large head) only must not be touched
        best = (p - loc).dot(nrm) - (self.floor if nrm.dot(n) > 0.0 else HEAD_GAP)
        for bvh, gap, reach in self.shells:
            hit = bvh.ray_cast(p, n, reach)
            if hit[0] is not None:
                return min(best, -hit[3] - gap)
            hit = bvh.ray_cast(p, -n, gap if probe is None else probe)
            if hit[0] is not None:
                best = min(best, hit[3] - gap)
        return best

    def crossed(self, a, b):
        """True when the segment a -> b passes through a garment piece."""
        seg = b - a
        return any(s[0].ray_cast(a, seg.normalized(), seg.length)[0] is not None for s in self.shells)

def _points(p0, d, width, angles):
    """Points of one column: hinged at p0, one segment per row at ``angles`` (rad below the horizontal along d)."""
    pts, step = [p0], width / ROWS
    for a in angles:
        pts.append(pts[-1] + (d * math.cos(a) - Vector((0.0, 0.0, math.sin(a)))) * step)
    return pts


def _strip(layers, p0, d, width, start, lo, hi, bend, fine, budget=600):
    """The most drooped clear strip that starts at ``start`` rad: a depth-first lay, row by row, trying the steepest
    angle within ``bend`` of the row before it first (between lo and hi) and stepping back a row when none keeps the
    new point and its segment clear. None when there is no such strip (or after ``budget`` probes)."""
    step = width / ROWS
    left = [budget]

    def lay(point, prev, k):
        if k == ROWS:
            return []
        a = start if k == 0 else min(hi, prev + bend)
        floor = start if k == 0 else max(lo, prev - bend)
        while a >= floor - 1e-9 and left[0] > 0:
            left[0] -= 1
            q = point + (d * math.cos(a) - Vector((0.0, 0.0, math.sin(a)))) * step
            n = d * math.sin(a) + Vector((0.0, 0.0, math.cos(a)))
            if (not layers.crossed(point, q) and layers.height(q, n) >= 0.0
                    and layers.height(0.5 * (point + q), n) >= 0.0):
                rest = lay(q, a, k + 1)
                if rest is not None:
                    return [a] + rest
            a -= 2.0 * fine
        return None

    return lay(p0, start, 0)


def _clear(layers, pts):
    """True when no segment of a strip passes through a garment piece and every point of it keeps the gaps."""
    for a, b in zip(pts, pts[1:]):
        t = (b - a).normalized()
        n = Vector((0.0, 0.0, 1.0)) - t * t.z
        n = n.normalized() if n.length > 1e-6 else Vector((0.0, 0.0, 1.0))
        if layers.crossed(a, b) or layers.height(b, n) < 0.0 or layers.height(0.5 * (a + b), n) < 0.0:
            return False
    return True


def _widths(cfg, P, H, fit, cols):
    """(inner radius, [(direction, collar width)] per column): the garment/1 round-collar outline."""
    c = cfg.get("collar") if isinstance(cfg.get("collar"), dict) else {}
    ease, thick = cfg["ease_m"] * fit.torso, cfg["thickness_m"]
    width = float(c.get("width_m", 0.035 * fit.head))
    tip = float(c.get("tip_round", 0.35))
    r_in = P["neck"]["radius"] * H + ease + thick + cfg["seam_radius_m"]
    gap = min(math.pi * 0.4, float(c.get("gap_m", 0.008 * fit.head)) / max(r_in, 1e-6))
    half = math.pi - gap
    out = []
    for i in range(cols + 1):
        phi = gap + (2 * math.pi - 2 * gap) * i / cols
        from_tip = min(phi - gap, 2 * math.pi - gap - phi) / max(half, 1e-9)
        q = min(1.0, from_tip / max(tip, 1e-6))
        w = width * math.sqrt(max(0.0, 1.0 - (1.0 - q) ** 2)) if tip > 0 else width
        out.append((Vector((math.sin(phi), -math.cos(phi), 0.0)), max(w, width * 0.08)))
    return r_in, out


def _grid(ob):
    n = len(ob.data.vertices)
    h = n // 2
    if n % 2 or h % (ROWS + 1):
        raise ValueError(f"{ob.name}: not a garment/1 round collar grid")
    return h, h // (ROWS + 1) - 1


def seat(cfg, objects, body, P, H, fit):
    st = settings(cfg["collar_seat"])
    name = cfg["name"]
    ob = next((o for o in objects if o.get("ps_garment_item") == name and o.get("ps_garment_part") == "collar"), None)
    if ob is None:
        raise ValueError(f"garment {name}.collar_seat: the item has no collar piece")
    h, cols = _grid(ob)
    me, mw = ob.data, ob.matrix_world
    inv = mw.inverted()
    pts = [mw @ v.co for v in me.vertices]
    thick = sum((pts[i + h] - pts[i]).length for i in range(h)) / h
    own = [o for o in objects if o.get("ps_garment_item") == name and o.get("ps_garment_part") == "main"
           and o.type == "MESH"]
    over = [o for o in objects if o.get("ps_garment_item") in set(st["over"]) and o.type == "MESH"]
    outer = [o for o in over if o.get("ps_garment_part") == "main"]
    edges = [o for o in over if o.get("ps_garment_part") == "edge"]
    if st["over"] and not outer:
        raise ValueError(f"garment {name}.collar_seat: no main piece of {sorted(st['over'])}")
    gap, ogap = float(st["gap_m"]), float(st["over_gap_m"])
    floor = cfg["ease_m"] * fit.torso + cfg["thickness_m"] + gap
    layers = Layers(_bvh(body), floor, [(_bvh(o), gap, OWN_REACH) for o in own]
                    + [(_bvh(o), ogap, OVER_REACH) for o in outer] + [(_bvh(o), EDGE_GAP, OVER_REACH) for o in edges])
    top_z = max((o.matrix_world @ v.co).z for o in own for v in o.data.vertices) if own else max(p.z for p in pts)
    r_in, outline = _widths(cfg, P, H, fit, cols)
    lo, hi = math.radians(MIN_DROOP_DEG), math.radians(float(st["max_droop_deg"]))
    fine = math.radians(2.5)
    hinge = []
    for d, w in outline:
        p0 = Vector((d.x * r_in, d.y * r_in, top_z + gap))
        for _ in range(30):  # the hinge clear of the neck (moved out along its direction, never in)
            loc, nrm, _, _ = layers.body.find_nearest(p0)
            if (p0 - loc).dot(nrm.normalized()) >= floor:
                break
            p0 += d * 0.001
        for _ in range(40):  # ... and above whatever stands right in front of it (a vest's neckline)
            if not any(s[0].ray_cast(p0, d, 0.5 * w)[0] is not None for s in layers.shells[len(own):]):
                break
            p0.z += 0.001
        hinge.append(p0)
    bend = math.radians(float(st["bend_deg"]))
    rows_a, raised = [], 0
    for i, (d, w) in enumerate(outline):
        got = None
        for lift in range(16):  # a column with no clear lay from its hinge is hinged a little higher
            a = hi
            while got is None and a > lo:
                got = _strip(layers, hinge[i], d, w, a, lo, hi, bend, fine)
                a -= fine
            if got is not None:
                break
            hinge[i] = hinge[i] + Vector((0.0, 0.0, 0.002))
            raised += 1
        rows_a.append(got if got is not None else [0.0] * ROWS)
    for _ in range(int(st["smooth"])):  # one even surface: the lay is averaged round the collar ...
        rows_a = [[(rows_a[max(i - 1, 0)][k] + 2.0 * rows_a[i][k] + rows_a[min(i + 1, cols)][k]) / 4.0
                   for k in range(ROWS)] for i in range(cols + 1)]
        hinge = [Vector((hinge[i].x, hinge[i].y, (hinge[max(i - 1, 0)].z + 2.0 * hinge[i].z
                                                  + hinge[min(i + 1, cols)].z) / 4.0)) for i in range(cols + 1)]
    stiffened = 0
    for i, (d, w) in enumerate(outline):  # ... and any strip the averaging pushed into a layer is raised out of it
        for _ in range(24):
            if _clear(layers, _points(hinge[i], d, w, rows_a[i])):
                break
            rows_a[i] = [a - fine for a in rows_a[i]]
            stiffened += 1
    limit = math.radians(float(st["step_deg"]))
    for _ in range(cols + 1):  # ... evenly: no row droops more than step_deg below the same row of the strip next to it
        changed = False
        for i in range(cols + 1):
            for j in (i - 1, i + 1):
                if not 0 <= j <= cols:
                    continue
                for k in range(ROWS):
                    if rows_a[i][k] > rows_a[j][k] + limit + 1e-9:
                        rows_a[i][k], changed = rows_a[j][k] + limit, True
        if not changed:
            break
    droop = [r[0] for r in rows_a]
    grid = [_points(hinge[i], outline[i][0], outline[i][1], rows_a[i]) for i in range(cols + 1)]
    hover = []
    for i in range(cols + 1):
        for k in range(ROWS + 1):
            a = grid[min(i + 1, cols)][k] - grid[max(i - 1, 0)][k]
            b = grid[i][min(k + 1, ROWS)] - grid[i][max(k - 1, 0)]
            nrm = a.cross(b)
            away = grid[i][k] - Vector(_nearest(layers.body, grid[i][k]))
            nrm = nrm.normalized() if nrm.length > 1e-12 else away.normalized()
            if nrm.dot(away) < 0:
                nrm = -nrm
            j = i * (ROWS + 1) + k
            me.vertices[j].co = inv @ grid[i][k]
            me.vertices[j + h].co = inv @ (grid[i][k] + nrm * thick)
            hover.append(layers.height(grid[i][k], nrm, probe=0.03))
    me.update()
    hover = sorted(x for x in hover if x is not None)
    return {"collar": ob.name, "over": sorted(st["over"]), "columns": cols + 1, "neckline_z_m": round(top_z, 4),
            "inner_radius_m": round(r_in, 4), "thickness_m": round(thick, 5),
            "droop_deg": {"min": round(math.degrees(min(droop)), 1), "max": round(math.degrees(max(droop)), 1)},
            "hinges_raised": raised, "strips_stiffened": stiffened,
            "rest_clearance_over_gap_m": {"p50": round(hover[len(hover) // 2], 5),
                                          "p95": round(hover[int(0.95 * (len(hover) - 1))], 5),
                                          "max": round(hover[-1], 5)} if hover else None}


def _nearest(bvh, p):
    loc = bvh.find_nearest(p)[0]
    return loc if loc is not None else p


def bind(rig, garments, name, raw, max_influences=4):
    """Chest-carried weights and the reach keys of one item's seated collar (see the module docstring)."""
    st = settings(raw)
    ob = next(o for o in garments if o.get("ps_garment_item") == name and o.get("ps_garment_part") == "collar")
    h, cols = _grid(ob)
    chest = st["chest_bone"]
    sides = {s: st["shoulder_bone"].format(side=s) for s in ("L", "R")}
    for bone in [chest] + list(sides.values()):
        if rig.data.bones.get(bone) is None:
            raise ValueError(f"garment {name}.collar_seat: rig has no bone {bone!r}")
    keep = {g.name for g in ob.vertex_groups if g.name.startswith("ps_")}
    for g in list(ob.vertex_groups):
        if g.name not in keep:
            ob.vertex_groups.remove(g)
    groups = {b: ob.vertex_groups.new(name=b) for b in [chest] + list(sides.values())}
    share = float(st["shoulder_share"])
    xs = [abs((ob.matrix_world @ v.co).x) for v in ob.data.vertices]
    half_width = max(max(xs), 1e-6)
    for j in range(h):
        k = j % (ROWS + 1)
        x = (ob.matrix_world @ ob.data.vertices[j].co).x
        s = share * (k / ROWS) * min(1.0, abs(x) / (0.6 * half_width))
        for i in (j, j + h):
            groups[chest].add([i], 1.0 - s, "REPLACE")
            if s > 1e-4:
                groups[sides["L" if x >= 0 else "R"]].add([i], s, "REPLACE")
    over = sorted(set(st["over"]) | {name})
    cfg = {"reach": dict(st["reach"], strength=0.0, over=over, gate=float(st["reach"].get("gate", 0.0)),
                         over_gap_m=float(st["reach"].get("over_gap_m", st["gap_m"])))}
    report = CORR.add(rig, [ob], cfg, max_influences, [o for o in garments if o is not ob])
    spread = _spread_keys(ob, h, cols, int(st["reach_smooth"]))
    return {"collar": ob.name, "carried_by": chest, "shoulder_share": share, "reach": report.get("reach"),
            "keys": spread}


def _spread_keys(ob, h, cols, iterations):
    """Spreads each reach key's push over the collar grid (both sheets move together; no vertex gets less than its
    solved push along that push), so the collar bends towards its tips instead of denting. Returns the key names."""
    if ob.data.shape_keys is None:
        return []
    blocks = ob.data.shape_keys.key_blocks
    basis = blocks[0]
    names = []
    for key in blocks[1:]:
        if not key.name.startswith("corrective."):
            continue
        need = []
        for j in range(h):
            a, b = key.data[j].co - basis.data[j].co, key.data[j + h].co - basis.data[j + h].co
            need.append(a if a.length >= b.length else b)
        delta = [d.copy() for d in need]
        for _ in range(iterations):
            new = []
            for j in range(h):
                i, k = divmod(j, ROWS + 1)
                acc, cnt = Vector((0.0, 0.0, 0.0)), 0
                for a, b in ((i - 1, k), (i + 1, k), (i, k - 1), (i, k + 1)):
                    if 0 <= a <= cols and 0 <= b <= ROWS:
                        acc, cnt = acc + delta[a * (ROWS + 1) + b], cnt + 1
                d = 0.5 * delta[j] + 0.5 * acc / cnt
                if k == 0:
                    d = d * 0.5  # the neckline stays seated
                if need[j].length > 1e-7:  # never less than the solved push along its own direction
                    u = need[j].normalized()
                    short = need[j].length - d.dot(u)
                    if short > 0:
                        d = d + u * short
                new.append(d)
            delta = new
        for j in range(h):
            key.data[j].co = basis.data[j].co + delta[j]
            key.data[j + h].co = basis.data[j + h].co + delta[j]
        names.append(key.name)
    ob.data.update()
    return names
