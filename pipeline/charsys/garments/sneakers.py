"""Sneakers garment type (T-068) for ``garment/1``: a low chunky shoe built around the ``body_generic`` foot, not an
offset copy of it, so the silhouette reads as a sneaker (flat thick sole, boxy toe, opening at the ankle) whatever
the body's foot shape. Everything is spec data scaled by the generic body measures (no character data here):

  upper     a dome over the shoe plan (superellipse plan, toe slightly wider than the heel), open around the ankle
  sole      a thick flat slab under the upper whose rim wraps up the upper's lower edge
  toe_cap   a separate cap over the front of the upper (rubber toe), down into the sole
  laces     bars across the instep between the opening and the toe cap
  collar    a padded roll around the ankle opening
  tongue    a padded strip under the laces, rising into the opening

Spec (``clothing.garments[]`` item, ``type: "sneakers"``; every key optional, defaults scale with the foot):
  ease_m, thickness_m, height_m (upper height above the sole), length_extra_m (toe beyond the foot), width_extra_m,
  plan_n (plan superellipse exponent, 2 = oval .. 4 = boxy), dome_n (side-wall roundness), toe_flare (toe wider than
  the heel, share), toe_drop (toe box lower than the instep, share)
  sole {thickness_m, wrap_m (rim height up the upper), margin_m (wider than the upper)} or false
  opening {radius_m, length_m (forward reach), offset_m (centre in front of the ankle joint)}
  toe_cap {length (share of the shoe length from the tip), slope (0..1: the cap edge runs forwards as it rises),
           thickness_m} or false
  laces {count, radius_m, span (share of the upper width), start, end (shares of the shoe length from the opening
         towards the toe)} or false
  collar {radius_m, rise_m (the upper rises towards the opening, a padded ankle collar), falloff_m, back_share
          (share of the rise kept only at the heel)} or false
  tongue {width_m, thickness_m} or false
  materials {main, sole, toe_cap (default sole), laces (default band, else sole), collar (default main),
             tongue (default main)}
"""
import math

from mathutils import Vector

from . import generator as GEN
from . import shapes as S

TYPE = "sneakers"
PARTS = ("sole", "toe_cap", "laces", "collar", "tongue")
_FALLBACK = {"toe_cap": ("toe_cap", "sole"), "laces": ("laces", "band", "sole"), "collar": ("collar",),
             "tongue": ("tongue",), "sole": ("sole",)}


def _num(d, key, default):
    return float(d.get(key, default)) if isinstance(d, dict) else float(default)


def validate(raw, name):
    for key in ("height_m", "length_extra_m", "width_extra_m"):
        if key in raw:
            GEN._number(raw[key], f"garment {name}.{key}", 0.0, 0.3)
    for key, lo, hi in (("plan_n", 1.5, 6.0), ("dome_n", 1.5, 8.0), ("toe_flare", 0.0, 0.5), ("toe_drop", 0.0, 0.6)):
        if key in raw:
            GEN._number(raw[key], f"garment {name}.{key}", lo, hi)
    for block, keys in (("sole", ("thickness_m", "wrap_m", "margin_m")),
                        ("opening", ("radius_m", "length_m", "offset_m")),
                        ("toe_cap", ("length", "thickness_m", "slope")),
                        ("laces", ("radius_m", "span", "start", "end")),
                        ("collar", ("radius_m", "rise_m", "falloff_m", "back_share")),
                        ("tongue", ("width_m", "thickness_m"))):
        v = raw.get(block)
        if v is None or v is False or v is True:
            continue
        if not isinstance(v, dict):
            raise ValueError(f"garment {name}.{block} must be an object or false")
        for key in keys:
            if key in v:
                hi = 1.0 if key in ("length", "span", "start", "end", "back_share", "slope") else 0.2
                GEN._number(v[key], f"garment {name}.{block}.{key}", 0.0, hi)
    if raw.get("opening") is False:
        raise ValueError(f"garment {name}.opening cannot be false (the leg passes through it)")
    laces = raw.get("laces")
    if isinstance(laces, dict) and "count" in laces and (not isinstance(laces["count"], int) or
                                                         not 0 <= laces["count"] <= 10):
        raise ValueError(f"garment {name}.laces.count must be an integer in [0, 10]")


def _part_mat(G, cfg, part, H):
    mats = cfg.get("materials", {})
    key = next((k for k in _FALLBACK.get(part, (part,)) if k in mats), "main")
    return GEN._mat_for(G, cfg, key, H)


class _Shoe:
    """Analytic shoe surface of one foot: plan superellipse (s = 0 centre .. 1 outline) and dome height."""

    def __init__(self, cfg, P, H, J, side, fit):
        lm = fit.leg
        self.e = cfg["ease_m"] * lm
        self.thick = cfg["thickness_m"]
        fl, fw, fh = P["foot"]["length"] * H, P["foot"]["half_width"] * H, P["foot"]["height"] * H
        self.fl, self.fw, self.fh = fl, fw, fh
        self.hx = J[f"ankle.{side}"].x
        self.side = 1.0 if side == "L" else -1.0
        extra = float(cfg.get("length_extra_m", 0.12 * fw))
        self.A = fw + self.e + float(cfg.get("width_extra_m", 0.0))
        self.B = 0.6 * fl + self.e + 0.5 * extra
        self.cy = -0.3 * fl - 0.5 * extra
        self.plan_n = float(cfg.get("plan_n", 2.6))
        self.dome_n = float(cfg.get("dome_n", 2.8))
        self.flare = float(cfg.get("toe_flare", 0.08))
        self.drop = float(cfg.get("toe_drop", 0.22))
        sole = cfg.get("sole", {})
        sole = sole if isinstance(sole, dict) else {}
        self.st = _num(sole, "thickness_m", max(0.004, 0.17 * fh))
        self.z0 = -self.e
        self.Hz = float(cfg.get("height_m", fh + self.e + self.thick))

    def plan(self, s, a):
        """Plan point at radius share s and angle a (sin a > 0: back, +Y)."""
        e = 2.0 / self.plan_n
        ux, uy = S.sgnpow(math.cos(a), e), S.sgnpow(math.sin(a), e)
        fwd = -uy * s
        x = self.hx + self.A * (1.0 + self.flare * fwd) * s * ux
        y = self.cy + self.B * s * uy
        return x, y

    def fwd(self, y):
        return -(y - self.cy) / self.B

        self.rise = None

    def height(self, s, y, x=None):
        f = max(0.0, min(1.0, self.fwd(y)))
        h = self.Hz * (1.0 - self.drop * f * f)
        s = min(1.0, s)
        z = self.z0 + h * (1.0 - s ** self.dome_n) ** (1.0 / self.dome_n)
        if self.rise is not None and x is not None:
            z += self.rise(x, y) * (1.0 - s ** 24)
        return z

    def plan_s(self, x, y):
        """Inverse of plan(): the radius share of a plan point (approximate through the flare)."""
        uy = (y - self.cy) / self.B
        fwd = -uy
        ux = (x - self.hx) / (self.A * max(0.2, 1.0 + self.flare * fwd))
        return (abs(ux) ** self.plan_n + abs(uy) ** self.plan_n) ** (1.0 / self.plan_n)

    def inside(self, c):
        s = self.plan_s(c.x, c.y)
        return s < 1.0 and c.z < self.height(s, c.y, c.x) and c.z > self.z0 - self.st


def _dome(G, C, name, shoe, rings, segs, keep):
    """Dome mesh over the plan (centre vertex + rings); faces failing ``keep(centroid)`` are left out."""
    verts = [(shoe.hx + 0.0, shoe.cy, shoe.height(0.0, shoe.cy, shoe.hx))]
    params = [(0.0, 0.0)]
    for k in range(1, rings + 1):
        s = math.sin(0.5 * math.pi * k / rings)
        for i in range(segs):
            a = 2 * math.pi * i / segs
            x, y = shoe.plan(s, a)
            verts.append((x, y, shoe.height(s, y, x)))
            params.append((s, a))
    faces = []
    for i in range(segs):
        faces.append((0, 1 + i, 1 + (i + 1) % segs))
    for k in range(1, rings):
        a0, b0 = 1 + (k - 1) * segs, 1 + k * segs
        for i in range(segs):
            j = (i + 1) % segs
            faces.append((a0 + i, b0 + i, b0 + j, a0 + j))
    kept = [f for f in faces if keep(sum((Vector(verts[i]) for i in f), Vector()) / len(f))]
    used = sorted({i for f in kept for i in f})
    remap = {o: n for n, o in enumerate(used)}
    ob = G.new_object(name, [verts[i] for i in used], [tuple(remap[i] for i in f) for f in kept], C)
    return ob


def _offset_patch(G, C, name, src, value, offset, thickness):
    """Copy of the faces of ``src`` around which ``value(point) > 0``, moved ``offset`` along the vertex normals and
    solidified outwards by ``thickness``. Vertices outside the region are slid along their edges onto the zero
    crossing, so the patch edge follows the region boundary smoothly instead of the face grid."""
    me = src.data
    mw = src.matrix_world
    val = [value(mw @ v.co) for v in me.vertices]
    faces = [p for p in me.polygons if any(val[i] > 0 for i in p.vertices)]
    if not faces:
        return None
    used = sorted({i for p in faces for i in p.vertices})
    pos = {i: mw @ (me.vertices[i].co + me.vertices[i].normal * offset) for i in used}
    moved = {}
    for i in used:
        if val[i] > 0:
            continue
        targets = []
        for p in faces:
            if i not in p.vertices:
                continue
            k = list(p.vertices).index(i)
            for j in (p.vertices[k - 1], p.vertices[(k + 1) % len(p.vertices)]):
                if val[j] > 0:
                    t = val[j] / max(val[j] - val[i], 1e-12)
                    targets.append(pos[j].lerp(pos[i], t))
        if targets:
            moved[i] = sum(targets, Vector()) / len(targets)
    pos.update(moved)
    remap = {o: n for n, o in enumerate(used)}
    ob = G.new_object(name, [tuple(pos[i]) for i in used], [tuple(remap[i] for i in p.vertices) for p in faces], C)
    return S.solidify(ob, thickness)


def _boundary(ob):
    """The longest open boundary loop of a mesh, as world points."""
    loops = GEN._boundary_loops([tuple(p.vertices) for p in ob.data.polygons])
    if not loops:
        return []
    loop = max(loops, key=len)
    return [ob.matrix_world @ ob.data.vertices[i].co for i in loop]


def build(C, body, cfg, P, H, J, G, fit):
    """Both sneakers. Returns (objects, covered body faces)."""
    objects, covered = [], set()
    lm = fit.leg
    ankle_r = P["leg"]["radii"][2] * H
    for side in ("L", "R"):
        shoe = _Shoe(cfg, P, H, J, side, fit)
        oc = cfg.get("opening") if isinstance(cfg.get("opening"), dict) else {}
        orx = _num(oc, "radius_m", ankle_r + 0.6 * shoe.e)
        ory = orx + _num(oc, "length_m", 0.35 * orx)
        ocy = -_num(oc, "offset_m", 0.25 * orx)
        open_c = Vector((shoe.hx, ocy - (ory - orx), 0.0))

        def in_opening(c, open_c=open_c, orx=orx, ory=ory):
            return ((c.x - open_c.x) / orx) ** 2 + ((c.y - open_c.y) / ory) ** 2 < 1.0

        cc_d = cfg.get("collar") if isinstance(cfg.get("collar"), dict) else {}
        rise = _num(cc_d, "rise_m", 0.0)
        if rise > 0:
            fall = _num(cc_d, "falloff_m", 0.9 * orx)
            back = _num(cc_d, "back_share", 0.6)

            def rise_fn(x, y, open_c=open_c, orx=orx, ory=ory, rise=rise, fall=fall, back=back):
                q = math.sqrt(((x - open_c.x) / orx) ** 2 + ((y - open_c.y) / ory) ** 2)
                d = max(0.0, q - 1.0) * orx
                w = 1.0 - GEN._smoothstep(d / max(fall, 1e-6))
                b = max(0.0, min(1.0, 0.5 + 0.5 * (y - open_c.y) / ory))
                return rise * w * ((1.0 - back) + back * b)
            shoe.rise = rise_fn

        name = cfg["name"]
        upper = _dome(G, C, f"garment.{name}.main.{side}", shoe, 28, 96, lambda c: not in_opening(c))
        upper["ps_shoe_frame"] = [shoe.hx, shoe.cy, shoe.A, shoe.B, shoe.z0, shoe.Hz]
        rim = _boundary(upper)
        S.solidify(upper, shoe.thick)
        pieces = [("main", upper)]
        # sole: a slab under the plan, its rim wrapping up the upper
        sole_cfg = cfg.get("sole", {})
        if sole_cfg is not False:
            sole_cfg = sole_cfg if isinstance(sole_cfg, dict) else {}
            wrap = _num(sole_cfg, "wrap_m", 0.45 * shoe.st)
            margin = _num(sole_cfg, "margin_m", 0.002 * lm) + shoe.thick
            rings = []
            for z, grow in ((shoe.z0 - shoe.st, -0.6 * margin), (shoe.z0 - 0.82 * shoe.st, margin * 0.6),
                            (shoe.z0 - 0.55 * shoe.st, margin), (shoe.z0 + wrap * 0.6, margin),
                            (shoe.z0 + wrap, margin * 0.55), (shoe.z0 + wrap + 0.15 * shoe.st, -0.4 * margin)):
                ring = []
                for i in range(64):
                    a = 2 * math.pi * i / 64
                    x, y = shoe.plan(1.0, a)
                    d = Vector((x - shoe.hx, y - shoe.cy, 0.0))
                    d = d.normalized() if d.length > 1e-9 else Vector((1, 0, 0))
                    ring.append((x + d.x * grow, y + d.y * grow, z))
                rings.append(ring)
            pieces.append(("sole", G.loft(f"garment.{name}.sole.{side}", rings, C)))
        # toe cap over the front of the upper
        tc = cfg.get("toe_cap", {})
        if tc is not False:
            tc = tc if isinstance(tc, dict) else {}
            share = _num(tc, "length", 0.3)
            limit = 1.0 - 2.0 * share
            slope = _num(tc, "slope", 0.0)  # the cap's top edge runs forwards as it rises

            def in_cap(c, shoe=shoe, limit=limit, slope=slope):
                return shoe.fwd(c.y) - (limit + slope * max(0.0, c.z - shoe.z0) / shoe.Hz)
            cap = _offset_patch(G, C, f"garment.{name}.toe_cap.{side}", upper, in_cap, shoe.thick,
                                _num(tc, "thickness_m", max(0.0015, 0.6 * shoe.thick)))
            if cap is not None:
                pieces.append(("toe_cap", cap))
        # tongue and laces across the instep, from the opening towards the toe cap
        y_open = open_c.y - ory
        y_cap = shoe.cy - shoe.B * (1.0 - 2.0 * _num(tc if isinstance(tc, dict) else {}, "length", 0.3))
        tg = cfg.get("tongue", {})
        lc = cfg.get("laces", {})
        lc_d = lc if isinstance(lc, dict) else {}
        lace_r = _num(lc_d, "radius_m", 0.0022 * lm)
        tongue_t = 0.0
        if tg is not False:
            tg = tg if isinstance(tg, dict) else {}
            tw = _num(tg, "width_m", 0.55 * orx)
            tongue_t = _num(tg, "thickness_m", 0.0025 * lm)
            pts, nrm = [], []
            y_end = y_cap + 0.25 * (y_open - y_cap)
            for k in range(12):
                t = k / 11
                y = y_open + 0.35 * orx + (y_end - y_open - 0.35 * orx) * t
                s = shoe.plan_s(shoe.hx, y)
                z = shoe.height(s, y, shoe.hx) + shoe.thick
                pts.append(Vector((shoe.hx, y, z + tongue_t * 0.5)))
            for k, p in enumerate(pts):
                q = pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]
                nrm.append(Vector((0, -q.z, q.y)).normalized() * (1 if q.y < 0 else -1) if q.length > 0 else Vector((0, 0, 1)))
            nrm = [n if n.z > 0 else -n for n in nrm]
            pieces.append(("tongue", S.ribbon(G, C, f"garment.{name}.tongue.{side}", pts, nrm, 2 * tw, tongue_t,
                                              round_share=0.8)))
        if lc is not False:
            count = int(lc_d.get("count", 4))
            span = _num(lc_d, "span", 0.62)
            y0 = y_open + (y_cap - y_open) * _num(lc_d, "start", 0.06)
            y1 = y_open + (y_cap - y_open) * _num(lc_d, "end", 0.78)
            for k in range(count):
                y = y0 if count == 1 else y0 + (y1 - y0) * k / (count - 1)
                s_edge = 1.0
                half = 0.0
                # half width of the upper at this y (the plan outline), then the lace span
                for i in range(200):
                    s_try = (i + 1) / 200
                    if shoe.plan_s(shoe.hx + s_try * shoe.A * 1.3, y) >= 1.0:
                        half = s_try * shoe.A * 1.3
                        break
                half = (half or shoe.A) * span
                pts = []
                for j in range(9):
                    u = -1 + 2 * j / 8
                    x = shoe.hx + u * half
                    s = shoe.plan_s(x, y)
                    z = shoe.height(min(s, s_edge), y, x) + shoe.thick + tongue_t * (1 - u * u) + lace_r
                    pts.append(Vector((x, y + 0.15 * lace_r * u * (1 if k % 2 else -1), z)))
                ob = G.tube(f"garment.{name}.laces.{side}_{k + 1}", pts, [lace_r * 1.25] * len(pts),
                            [lace_r * 0.8] * len(pts), C, up_hint=(0, 0, 1), seg=8, cap_start="round", cap_end="round")
                pieces.append(("laces", ob))
        # padded collar around the opening
        cc = cfg.get("collar", {})
        if cc is not False and len(rim) > 6:
            cc = cc if isinstance(cc, dict) else {}
            cr = _num(cc, "radius_m", 0.004 * lm)
            path = GEN._smooth_loop([p + Vector((0, 0, cr * 0.4)) for p in rim], 4)
            centre = sum(path, Vector()) / len(path)
            path = [p + (Vector((p.x - centre.x, p.y - centre.y, 0)).normalized() * (shoe.thick * 0.5))
                    for p in path]
            pieces.append(("collar", GEN._closed_tube(G, C, f"garment.{name}.collar.{side}", path, cr)))
        anchor = (shoe.hx, -0.18 * shoe.fl, 0.0)
        mats = {}
        for part, ob in pieces:
            ob["ps_weight_anchor"] = anchor
            if part not in mats:
                mats[part] = _part_mat(G, cfg, part, H)
            GEN._feature(objects, ob, cfg, part, mats[part], G)
        covered |= {p.index for p in body.data.polygons if shoe.inside(GEN._face_centroid(body, p))}
    return objects, covered
