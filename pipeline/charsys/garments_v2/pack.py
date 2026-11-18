"""``garment/2`` flap backpack (T-093): a rounded lid flap with a tab closure over a ``garment/1`` backpack, and a
flap over its front pocket. The bag, pocket, straps and top grab loop stay ``garment/1`` pieces (set ``zip: false``
for a zip-less flap bag).

Item fields of a ``backpack`` item (every key optional):
  flap        {drop (share of the bag height the flap covers from the top, default 0.45), corner (share of the half
               width rounded at the lower corners, default 0.55), wrap (how far the flap reaches back over the top
               towards the body, share of the half depth, default 0.55), side_cover (share of the half width the flap
               covers, default 0.97), lift_m (gap to the bag, default 0.0008), thickness_m (default 0.003),
               dip_m (the flap's lower edge hangs this much lower at the centre, default 0), edge_m (radius of a
               rolled, piped edge along the flap's lower outline, default 0 = none)} or false
  tab         {width_m (default 0.012), length_m (reach below the flap edge, default 0.03), start (share of the
               flap height above its edge where the tab starts, default 0.35), thickness_m (default 0.003),
               buckle_m (size of the closure at the tab end, default 0.009; 0 = none), buckle ("loop" = a soft
               toggle, default; "ring" = a flat rounded ring the tab passes through)} or false
  pocket_flap {drop (share of the pocket height covered from its top, default 0.5), corner, wrap, side_cover,
               lift_m, thickness_m (as flap)} or false
Material parts: ``flap`` (default main), ``tab`` (default strap, then main), ``buckle`` (default tab, strap, main),
``pocket_flap`` (default flap, pocket, main), ``flap_edge`` / ``pocket_flap_edge`` (the piping; default their flap). New pieces are rigid to the bag's weight anchor (as the bag)."""
import math

from mathutils import Vector

from garments import generator as GEN
from garments import shapes as S
from garments import sneakers as SN

FLAP = {"drop": 0.45, "corner": 0.55, "wrap": 0.55, "side_cover": 0.97, "lift_m": 0.0008, "thickness_m": 0.003,
        "dip_m": 0.0, "edge_m": 0.0}
POCKET_FLAP = dict(FLAP, drop=0.5, wrap=0.2)
TAB = {"width_m": 0.012, "length_m": 0.03, "start": 0.35, "thickness_m": 0.003, "buckle_m": 0.009,
       "buckle": "loop"}
_FALLBACK = {"flap": ("flap",), "tab": ("tab", "strap"), "buckle": ("buckle", "tab", "strap"),
             "pocket_flap": ("pocket_flap", "flap", "pocket"), "flap_edge": ("flap_edge", "flap"),
             "pocket_flap_edge": ("pocket_flap_edge", "pocket_flap", "flap", "pocket")}
_RANGES = {"drop": (0.05, 1.0), "corner": (0.0, 1.0), "wrap": (0.0, 1.0), "side_cover": (0.3, 1.2),
           "lift_m": (0.0, 0.02), "thickness_m": (0.0005, 0.02), "dip_m": (0.0, 0.05), "width_m": (0.002, 0.08),
           "length_m": (0.0, 0.15), "start": (0.0, 1.0), "buckle_m": (0.0, 0.04), "edge_m": (0.0, 0.01)}


def validate(raw, field, name):
    v = raw[field]
    if v is False or v is True:
        return
    if not isinstance(v, dict):
        raise ValueError(f"garment {name}.{field} must be an object or false")
    allowed = TAB if field == "tab" else FLAP
    for key in v:
        if key not in allowed:
            raise ValueError(f"garment {name}.{field}.{key}: unknown field (known: {sorted(allowed)})")
        if key == "buckle":
            if v[key] not in ("loop", "ring"):
                raise ValueError(f"garment {name}.{field}.buckle must be 'loop' or 'ring'")
            continue
        lo, hi = _RANGES[key]
        GEN._number(v[key], f"garment {name}.{field}.{key}", lo, hi)


def _settings(cfg, field, defaults):
    v = cfg.get(field)
    return dict(defaults, **v) if isinstance(v, dict) else dict(defaults)


def _mat(G, cfg, part, H):
    mats = cfg.get("materials", {})
    key = next((k for k in _FALLBACK[part] if k in mats), "main")
    return GEN._mat_for(G, cfg, key, H)


def _bounds(ob):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _flap_value(lo, hi, st):
    """Signed region of a flap on a box-like piece whose outer face is +Y: positive above the rounded lower edge, on
    the outer half (plus ``wrap`` over the top) and within ``side_cover`` of the half width."""
    xc = 0.5 * (lo.x + hi.x)
    hw, hd, hh = 0.5 * (hi.x - lo.x), 0.5 * (hi.y - lo.y), 0.5 * (hi.z - lo.z)
    yc = 0.5 * (lo.y + hi.y)
    zb = hi.z - float(st["drop"]) * 2.0 * hh
    rc = max(1e-6, float(st["corner"]) * hw)
    dip = float(st["dip_m"])
    cover = float(st["side_cover"]) * hw

    def edge(x):
        ax = abs(x - xc)
        z = zb - dip * max(0.0, 1.0 - (ax / max(hw, 1e-6)) ** 2)
        if ax > hw - rc:
            q = min(rc, ax - (hw - rc))
            z += rc - math.sqrt(max(0.0, rc * rc - q * q))
        return z

    def value(c):
        return min(c.z - edge(c.x), c.y - (yc - float(st["wrap"]) * hd), cover - abs(c.x - xc))
    return value, edge, zb


def _patch(G, C, name, src, st):
    lo, hi = _bounds(src)
    value, edge, zb = _flap_value(lo, hi, st)
    ob = SN._offset_patch(G, C, name, src, value, float(st["lift_m"]), float(st["thickness_m"]))
    return ob, edge, zb, lo, hi


def _piping(G, C, name, src, edge, lo, hi, st):
    """A rolled (piped) edge along the flap's lower outline, lying on the flap's outer surface."""
    r = float(st["edge_m"])
    xc, yc = 0.5 * (lo.x + hi.x), 0.5 * (lo.y + hi.y)
    cover = float(st["side_cover"]) * 0.5 * (hi.x - lo.x) * 0.985
    bvh = S.bvh_of(src)
    pts = []
    for k in range(81):
        x = xc - cover + 2 * cover * k / 80
        hit, n = S.outer_hit([bvh], Vector((x, yc, edge(x) + 1.2 * r)), Vector((0, 1, 0)), 0.5)
        if hit is not None:
            pts.append(hit + n * 0.2 * r)
    if len(pts) < 6:
        return None
    pts = S.resample(pts, 72)
    return G.tube(name, pts, [r] * len(pts), [r * 0.8] * len(pts), C, up_hint=(0, 1, 0), seg=8,
                  cap_start="round", cap_end="round")


def add_flaps(C, cfg, mine, G, H, fit):
    """Flap, tab and pocket flap of a backpack item. Returns (new objects, report)."""
    name = cfg["name"]
    bag = next((o for o in mine if o.name == f"garment.{name}.main"), None)
    pocket = next((o for o in mine if o.name == f"garment.{name}.pocket"), None)
    if bag is None:
        raise ValueError(f"garment {name}: the flap needs the garment/1 bag (garment.{name}.main)")
    made, report = [], {}
    mats = {}

    def feature(ob, part):
        if part not in mats:
            mats[part] = _mat(G, cfg, part, H)
        GEN._feature(made, ob, cfg, part, mats[part], G)

    flap_ob = None
    if cfg.get("flap") not in (None, False):
        st = _settings(cfg, "flap", FLAP)
        flap_ob, edge, zb, lo, hi = _patch(G, C, f"garment.{name}.flap", bag, st)
        if flap_ob is None:
            raise ValueError(f"garment {name}.flap covers no face of the bag")
        feature(flap_ob, "flap")
        report["flap"] = {"edge_z_m": round(zb, 4), "faces": len(flap_ob.data.polygons)}
        if float(st["edge_m"]) > 0:
            pipe = _piping(G, C, f"garment.{name}.flap_edge", flap_ob, edge, lo, hi, st)
            if pipe is not None:
                feature(pipe, "flap_edge")
                report["flap"]["edge_m"] = float(st["edge_m"])
        if cfg.get("tab") not in (None, False):
            tb = _settings(cfg, "tab", TAB)
            xc, yc = 0.5 * (lo.x + hi.x), 0.5 * (lo.y + hi.y)
            z_edge = edge(xc)
            z_top = z_edge + float(tb["start"]) * (hi.z - z_edge)
            z_end = z_edge - float(tb["length_m"])
            bvhs = [S.bvh_of(flap_ob), S.bvh_of(bag)]
            if pocket is not None:
                bvhs.append(S.bvh_of(pocket))
            pts, nrm = [], []
            t = float(tb["thickness_m"])
            for k in range(14):
                z = z_top + (z_end - z_top) * k / 13
                hit, n = S.outer_hit(bvhs, Vector((xc, yc, z)), Vector((0, 1, 0)), 0.5)
                if hit is None:
                    continue
                pts.append(hit + n * (0.5 * t + 0.0004))
                nrm.append(n)
            if len(pts) > 3:
                tab = S.ribbon(G, C, f"garment.{name}.tab", pts, nrm, float(tb["width_m"]), t, round_share=0.7)
                feature(tab, "tab")
                report["tab"] = {"from_z_m": round(z_top, 4), "to_z_m": round(z_end, 4)}
                b = float(tb["buckle_m"])
                if b > 0:
                    end, n = pts[-1], nrm[-1]
                    if tb["buckle"] == "ring":  # a flat rounded-rectangle ring the tab passes through
                        rr = 0.12 * b
                        hw, hh = 0.6 * b, 0.42 * b
                        c0 = end + n * (0.5 * t + rr)
                        path = []
                        for k in range(48):
                            a = 2 * math.pi * k / 48
                            ux, uz = S.sgnpow(math.cos(a), 0.35), S.sgnpow(math.sin(a), 0.35)
                            path.append(c0 + Vector((hw * ux, 0.0, hh * uz)))
                        path.append(path[0])
                        loop = G.tube(f"garment.{name}.buckle", path, [rr] * len(path), [rr] * len(path), C,
                                      up_hint=(0, 1, 0), seg=8, cap_start=None, cap_end=None)
                    else:
                        loop = S.superellipsoid(G, C, f"garment.{name}.buckle", tuple(end + n * (0.35 * b)),
                                                (0.5 * b * 1.25, 0.18 * b, 0.5 * b * 0.8), 3.0, 20, 10)
                    feature(loop, "buckle")
                    report["buckle_m"] = b
    if cfg.get("pocket_flap") not in (None, False) and pocket is not None:
        st = _settings(cfg, "pocket_flap", POCKET_FLAP)
        pf, pedge, pz, plo, phi = _patch(G, C, f"garment.{name}.pocket_flap", pocket, st)
        if pf is not None:
            feature(pf, "pocket_flap")
            report["pocket_flap"] = {"edge_z_m": round(pz, 4), "faces": len(pf.data.polygons)}
            if float(st["edge_m"]) > 0:
                pipe = _piping(G, C, f"garment.{name}.pocket_flap_edge", pf, pedge, plo, phi, st)
                if pipe is not None:
                    feature(pipe, "pocket_flap_edge")
    return made, report
