"""Scalp cap with a smooth border (T-219, hair step H2, opt-in key `hair.cap_contour` of groom/5).

`hair.scalp_cap` makes the cap by deleting every head face whose centre lies below the hairline or inside the face
opening (`face_cut`), so the cap border follows the head's faces: a stair-step edge at the forehead and in front of
the ear once the fuzz fibres no longer hide it (T-207). This module rebuilds the cap mesh of a built groom from the
same head and the same structure values, but clips the head surface along the zero line of one continuous field
instead of deleting whole faces:

    s(v) = min(z - zmin(|azimuth|), smax(y - face_cut[0], z - face_cut[1]))      (keep where s >= 0)

with zmin the structure's own hairline table (linear in azimuth, as hair.scalp_cap) and smax a rounded maximum (the
face opening's corner gets the radius `corner_round_m`; 0 = the sharp corner of hair.scalp_cap). Edges that cross
the line are split at the crossing (a vertex closer than `snap` of the edge length is moved onto the line instead, no
slivers), faces are split along the line, and the faces with s < 0 go. Then every vertex moves out along its normal
by the structure's offset, as before. The new border lies within one head face of the old one (the old test used
face centres).

    "cap_contour": {"structure": "cap" (name of the scalp_cap structure; default: the only one),
                    "corner_round_m": 0..0.05 (default 0), "snap": 0..0.45 (default 0.2),
                    "hairline_dz_m": -0.03..0.03 (default 0; moves the hairline table up / down)}

Character-independent: every value comes from the spec. Applied by groom_r6 before the fibres are grown (the
fibres, flock and contact steps see the new cap). Absent key = nothing here runs.
"""
import bisect
import math

KEY = "cap_contour"
DEFAULTS = {"structure": None, "corner_round_m": 0.0, "snap": 0.2, "hairline_dz_m": 0.0}
RANGES = {"corner_round_m": (0.0, 0.05), "snap": (0.0, 0.45), "hairline_dz_m": (-0.03, 0.03)}


def has_key(hair_spec):
    return isinstance(hair_spec, dict) and KEY in hair_spec


def strip(hair_spec):
    """The hair spec without the key (what the groom/4 path validates and builds); the same object when absent."""
    if not has_key(hair_spec):
        return hair_spec
    return {k: v for k, v in hair_spec.items() if k != KEY}


def _cap_structures(hair_spec):
    return [s for s in hair_spec.get("structures") or [] if isinstance(s, dict) and s.get("type") == "scalp_cap"]


def validate(hair_spec):
    """Errors of the key (empty when absent or valid)."""
    if not has_key(hair_spec):
        return []
    cfg = hair_spec[KEY]
    if not isinstance(cfg, dict):
        return [f"hair.{KEY} must be an object"]
    errs = [f"hair.{KEY}.{k}: unknown key" for k in sorted(set(cfg) - set(DEFAULTS))]
    for k, (lo, hi) in RANGES.items():
        if k in cfg:
            v = cfg[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= float(v) <= hi:
                errs.append(f"hair.{KEY}.{k} must be a number in [{lo}, {hi}]")
    caps = _cap_structures(hair_spec)
    name = cfg.get("structure")
    if name is None:
        if len(caps) != 1:
            errs.append(f"hair.{KEY}: name the scalp_cap structure (the spec has {len(caps)})")
    elif not any(s.get("name", "scalp_cap") == name for s in caps):
        errs.append(f"hair.{KEY}.structure {name!r} is not a scalp_cap structure")
    return errs


def settings(hair_spec):
    cfg = dict(DEFAULTS, **hair_spec[KEY])
    caps = _cap_structures(hair_spec)
    st = caps[0] if cfg["structure"] is None else next(s for s in caps if s.get("name", "scalp_cap") == cfg["structure"])
    return cfg, st


def field(cfg, st):
    """s(x, y, z) in metres (>= 0 keeps the head surface). The hairline and face_cut defaults are hair.scalp_cap's."""
    face_cut = st.get("face_cut", [-0.05, 0.955])
    hl = sorted(st.get("hairline", [[0, 0.93], [60, 0.86], [90, 0.80], [180, 0.73]]))
    azs = [float(a) for a, _ in hl]
    zs = [float(z) + float(cfg["hairline_dz_m"]) for _, z in hl]
    fy, fz = float(face_cut[0]), float(face_cut[1])
    r = float(cfg["corner_round_m"])

    def zmin(a):
        i = bisect.bisect_left(azs, a)
        if i <= 0:
            return zs[0]
        if i >= len(azs):
            return zs[-1]
        t = (a - azs[i - 1]) / (azs[i] - azs[i - 1])
        return zs[i - 1] + t * (zs[i] - zs[i - 1])

    def smax(a, b):
        if r <= 0:
            return max(a, b)
        return 0.5 * (a + b + math.sqrt((a - b) ** 2 + r * r)) - 0.5 * r  # = max far from the corner, rounded near it

    def s(x, y, z):
        a = abs(math.degrees(math.atan2(x, -y)))
        return min(z - zmin(a), smax(y - fy, z - fz))
    return s


def rebuild(cap_ob, head, cfg, st):
    """Replaces cap_ob's mesh data in place (object, material slots and name kept). Returns report numbers."""
    import bmesh
    s_of = field(cfg, st)
    off = float(st.get("offset", 0.006))
    snap = float(cfg["snap"])
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.transform(head.matrix_world)
    sv = {v: s_of(*v.co) for v in bm.verts}
    eps = 1e-9

    def root(a, b):
        """Edge parameter of the zero of s between a (one sign) and b (the other): bisection (s is not linear)."""
        lo, hi, slo = 0.0, 1.0, sv[a]
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            sm = s_of(*a.co.lerp(b.co, mid))
            if (sm > 0) == (slo > 0):
                lo, slo = mid, sm
            else:
                hi = mid
        return 0.5 * (lo + hi)
    # 1. move vertices that lie close to the line onto it (no slivers), then split the remaining crossing edges
    snapped = 0
    for e in list(bm.edges):
        a, b = e.verts
        sa, sb = sv[a], sv[b]
        if (sa > eps and sb < -eps) or (sa < -eps and sb > eps):
            t = root(a, b)
            if t < snap or t > 1.0 - snap:
                v = a if t < 0.5 else b
                if abs(sv[v]) > eps:
                    v.co = a.co.lerp(b.co, t)
                    sv[v] = 0.0
                    snapped += 1
    split = 0
    for e in list(bm.edges):
        a, b = e.verts
        sa, sb = sv[a], sv[b]
        if (sa > eps and sb < -eps) or (sa < -eps and sb > eps):
            t = root(a, b)
            co = a.co.lerp(b.co, t)
            _e, v = bmesh.utils.edge_split(e, a, t)
            v.co = co
            sv[v] = 0.0
            split += 1
    # 2. split every face along its on-line vertices (two that are not neighbours on the face)
    for f in list(bm.faces):
        on = [v for v in f.verts if abs(sv[v]) <= eps]
        if len(on) == 2 and not any(set(e.verts) == set(on) for e in f.edges):
            bmesh.ops.connect_verts(bm, verts=on)
    # 3. delete the faces on the negative side
    kill = [f for f in bm.faces if sum(sv.get(v, s_of(*v.co)) for v in f.verts) / len(f.verts) < 0]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * off
    old_faces = len(cap_ob.data.polygons)
    bm.to_mesh(cap_ob.data)
    bm.free()
    cap_ob.data.update()
    return {"faces_before": old_faces, "faces": len(cap_ob.data.polygons), "snapped": snapped, "split": split,
            "corner_round_m": float(cfg["corner_round_m"]), "hairline_dz_m": float(cfg["hairline_dz_m"])}


def apply(hair_spec, head, objs):
    """Build hook: rebuilds the cap object of the named scalp_cap structure. None when the key is absent."""
    if not has_key(hair_spec):
        return None
    cfg, st = settings(hair_spec)
    name = "hair_" + st.get("name", "scalp_cap")
    cap = next((o for o in objs if o.name == name), None)
    if cap is None:
        raise SystemExit(f"groom/5 {KEY}: built groom has no object {name}")
    return rebuild(cap, head, cfg, st)
