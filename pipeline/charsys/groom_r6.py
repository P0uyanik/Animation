"""Hair round 6 (`groom/5`, T-160): standing petals with a stable section frame, soft tapered ends.

T-133 / T-116 hair review: tall crown petals (B05, val27) come out ribbed and twisted in groom/3 (the section frame
follows the scalp normal of every path point, so a petal that stands far off the scalp inherits the facets of the
head mesh), and long locks end in thick, hooked tips where the references show soft, thin wisps (17_W04, G06).

groom/5 keeps groom/4 (groom_r5.py, used read-only as a library) and adds two keys. Both are applied to the built
mesh of the structure before the fibres are grown: vertex counts, order and faces do not change, so dynamics
records, binding and the fibre layers stay valid. A hair spec that uses neither key builds through groom/5 exactly
as through groom/4 (`lower` returns it unchanged and the fibre callback is passed through). Character-independent:
every value is spec data.

spec.hair (generator "groom/5"): everything of groom/4 plus
  masses with "stand"   {"smooth": 0..60 (default 12)}: every mass of the structure gets its centre line smoothed
              (that many relaxation passes, both ends fixed) and its sections carried along the smoothed line by
              parallel transport from the root section (no twist about the line). For petals that stand off the
              scalp; a mass that lies on the scalp does not need it.
  masses / locks with "tips"   {"from": 0..0.95 (default 0.6), "scale": 0..1.5 (default 0.4), "power": > 0
              (default 1.5), "flatten": 0..0.9 (default 0), "calm": 0..1 (default 0), "round": 0..1 (default 0)}:
              over the end of every mass or lock, from `from` (fraction of its length) to the tip, the section is
              scaled down to `scale` of its built size (blend q^power, q running 0..1 over the end), its depth by a
              further (1 - flatten q) (a flat, soft wisp instead of a round rope end), and its centre line is
              pulled by calm x q towards the smoothed line (takes the hook out of a waved or curled end).
              "round" > 0 instead ends the taper in a rounded tip: the scale follows a quarter ellipse over the
              last `round` share of the end (soft, blunt clump ends for a fringe edge).
  masses / locks with "clump"  (T-167, natural strand grouping: the references show clumps that differ from their
              neighbours, not a row of equal leaves) {"bend_m": 0..0.05 (default 0), "twist_deg": 0..180 (default
              0), "lumps": 0..0.6 (default 0), "lump_wavelength": 0.05..2 (default 0.4, share of the length),
              "seed": int (default 0)}: every mass or lock of the structure is bent sideways by up to bend_m
              (nothing at the root, growing to the tip, its own direction, sign and wavelength), its section
              turns about its line by up to twist_deg at the tip (either way), and its section swells and thins
              along its length by +-lumps. No random numbers: the per-clump values come from a fixed
              low-discrepancy sequence of the clump's index in the structure and "seed", so the same spec always
              builds the same hair. Applied after "tips" and "stand".

Opt-in keys of T-183 (hair contact; groom_contact.py, absent = nothing changes): hair.ear_keepout (the built hair
surface is moved out of the ear meshes before the fibres are grown) and hair.dynamics.contact (body colliders for the
hair chains, fitted at bind time).
"""
import math

try:
    from mathutils import Vector
except ImportError:  # plain Python (tests, validation): the few vector operations the reshape needs
    class Vector(tuple):
        def __new__(cls, v=(0.0, 0.0, 0.0)):
            return tuple.__new__(cls, (float(v[0]), float(v[1]), float(v[2])))

        x, y, z = (property(lambda s, i=i: s[i]) for i in range(3))
        length = property(lambda s: math.sqrt(s.dot(s)))

        def __add__(s, o):
            return Vector((s[0] + o[0], s[1] + o[1], s[2] + o[2]))

        def __sub__(s, o):
            return Vector((s[0] - o[0], s[1] - o[1], s[2] - o[2]))

        def __mul__(s, f):
            return Vector((s[0] * f, s[1] * f, s[2] * f))

        def __truediv__(s, f):
            return s * (1.0 / f)

        def dot(s, o):
            return s[0] * o[0] + s[1] * o[1] + s[2] * o[2]

        def cross(s, o):
            return Vector((s[1] * o[2] - s[2] * o[1], s[2] * o[0] - s[0] * o[2], s[0] * o[1] - s[1] * o[0]))

        def normalized(s):
            n = s.length
            return s * (1.0 / n) if n > 0 else Vector()

        def copy(s):
            return s

        def orthogonal(s):
            return s.cross(Vector((1, 0, 0)) if abs(s[0]) < 0.9 else Vector((0, 1, 0)))

import groom as G1  # groom/1 as a library (read-only use)
import groom_contact as CT  # T-183 opt-in keys: ear keep-out, contact colliders (inactive without the keys)
import groom_felt as GF  # felt lock defaults (read-only use)
import groom_r5 as R5  # groom/4 as a library (read-only use)

GENERATOR_VERSIONS = ("groom/5",)
GENERATOR = "groom/5"
R6_KEYS = ("stand", "tips", "clump")
STAND_DEFAULT = {"smooth": 12}
TIPS_DEFAULT = {"from": 0.6, "scale": 0.4, "power": 1.5, "flatten": 0.0, "calm": 0.0, "round": 0.0}
CLUMP_DEFAULT = {"bend_m": 0.0, "twist_deg": 0.0, "lumps": 0.0, "lump_wavelength": 0.4, "seed": 0}
CALM_PASSES = 40
_IRR = (0.6180339887, 0.7548776662, 0.5698402910, 0.8191725134, 0.6710436067, 0.4142135624)


# ---------------------------------------------------------------------------------------------------------- lowering
def _segments(st, hair_spec):
    """Vertices per section ring of the structure's meshes (as its groom/3 builder makes them)."""
    if st["type"] == "masses":
        return int(st.get("seg", 18))
    if st.get("finish", hair_spec.get("finish", "felt")) == "felt":
        return int(dict(GF.LOCK_DEFAULT, **(st.get("felt") or {}))["seg"])
    return int(dict(G1.YARN_DEFAULT, **(hair_spec.get("yarn") or {}))["seg"])


def _objects(st):
    """Names of the mesh objects groom/4 builds for a masses or locks structure."""
    name = st.get("name", st["type"])
    if st["type"] == "locks" and st.get("stagger"):
        return [f"hair_{n}" for n, _, _ in R5.lock_names(st)]
    return [f"hair_{name}"]


def lower(hair_spec):
    """The groom/4 form of a groom/5 hair spec and the reshape jobs: (spec, jobs). A spec without groom/5 keys is
    returned as it is (the same object) with no jobs, so its build is groom/4's."""
    sts = hair_spec.get("structures")
    if not isinstance(sts, list) or not any(isinstance(s, dict) and any(k in s for k in R6_KEYS) for s in sts):
        return hair_spec, []
    out, jobs = [], []
    for s in sts:
        if not any(k in s for k in R6_KEYS):
            out.append(s)
            continue
        out.append({k: v for k, v in s.items() if k not in R6_KEYS})
        job = {"structure": s.get("name", s["type"]), "objects": _objects(s), "seg": _segments(s, hair_spec)}
        if s.get("stand") is not None:
            job["stand"] = dict(STAND_DEFAULT, **s["stand"])
        if s.get("tips") is not None:
            job["tips"] = dict(TIPS_DEFAULT, **s["tips"])
        if s.get("clump") is not None:
            job["clump"] = dict(CLUMP_DEFAULT, **s["clump"])
        jobs.append(job)
    return dict(hair_spec, structures=out), jobs


# -------------------------------------------------------------------------------------------------------- validation
def _num(d, k, lo, hi, default):
    try:
        return lo <= float(d.get(k, default)) <= hi
    except (TypeError, ValueError):
        return False


def validate(hair_spec):
    """Errors in a groom/5 hair spec: the groom/5 keys, then the groom/4 rules on the lowered spec. The T-183 contact
    keys (groom_contact.py) are checked first and taken out of what the groom/4 path sees."""
    if CT.has_keys(hair_spec):
        return CT.validate(hair_spec) or validate(CT.strip(hair_spec))
    sts = hair_spec.get("structures")
    if not isinstance(sts, list) or not sts:
        return ["hair.structures must be a non-empty list"]
    errs = []
    for i, s in enumerate(sts):
        where = f"hair.structures[{i}]"
        t = s.get("type")
        if "stand" in s:
            sd = s["stand"]
            if t != "masses":
                errs.append(f"{where}.stand is for masses only")
            elif not (isinstance(sd, dict) and set(sd) <= {"smooth"} and _num(sd, "smooth", 0, 60, 12)
                      and float(sd.get("smooth", 12)) == int(sd.get("smooth", 12))):
                errs.append(f"{where}.stand must be {{\"smooth\": 0..60 (int)}}")
        if "tips" in s:
            tp = s["tips"]
            if t not in ("masses", "locks"):
                errs.append(f"{where}.tips is for masses and locks only")
            elif not (isinstance(tp, dict) and set(tp) <= set(TIPS_DEFAULT) and _num(tp, "from", 0, 0.95, 0.6)
                      and _num(tp, "scale", 0, 1.5, 0.4) and _num(tp, "power", 1e-3, 20, 1.5)
                      and _num(tp, "flatten", 0, 0.9, 0) and _num(tp, "calm", 0, 1, 0) and _num(tp, "round", 0, 1, 0)):
                errs.append(f"{where}.tips must be {{\"from\": 0..0.95, \"scale\": 0..1.5, \"power\": > 0, "
                            f"\"flatten\": 0..0.9, \"calm\": 0..1, \"round\": 0..1}}")
        if "clump" in s:
            cl = s["clump"]
            if t not in ("masses", "locks"):
                errs.append(f"{where}.clump is for masses and locks only")
            elif not (isinstance(cl, dict) and set(cl) <= set(CLUMP_DEFAULT) and _num(cl, "bend_m", 0, 0.05, 0)
                      and _num(cl, "twist_deg", 0, 180, 0) and _num(cl, "lumps", 0, 0.6, 0)
                      and _num(cl, "lump_wavelength", 0.05, 2, 0.4) and isinstance(cl.get("seed", 0), int)
                      and not isinstance(cl.get("seed", 0), bool)):
                errs.append(f"{where}.clump must be {{\"bend_m\": 0..0.05, \"twist_deg\": 0..180, \"lumps\": "
                            f"0..0.6, \"lump_wavelength\": 0.05..2, \"seed\": int}}")
    if errs:
        return errs
    return R5.validate(lower(hair_spec)[0])


# ----------------------------------------------------------------------------------------------------------- reshape
def relax(path, passes, weight=None):
    """Centre line after `passes` relaxation passes (each point towards the mean of its neighbours, ends fixed).
    weight[i] in 0..1 limits how far point i follows (None = fully)."""
    cur = [p.copy() for p in path]
    for _ in range(int(passes)):
        nxt = [cur[0]] + [(cur[i - 1] + cur[i + 1]) * 0.25 + cur[i] * 0.5 for i in range(1, len(cur) - 1)] + [cur[-1]]
        cur = nxt
    if weight is None:
        return cur
    return [p + (c - p) * w for p, c, w in zip(path, cur, weight)]


def _tangents(path):
    n = len(path)
    out = []
    for i in range(n):
        t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
        out.append(t.normalized() if t.length > 1e-12 else Vector((0, 0, 1)))
    return out


def _frames(rings, centres):
    """Section frame (T, B, N) of every ring as built: B towards the ring's first vertex, N = T x B."""
    T = _tangents(centres)
    out = []
    for r, c, t in zip(rings, centres, T):
        b = (r[0] - c) - t * (r[0] - c).dot(t)
        b = b.normalized() if b.length > 1e-9 else t.orthogonal().normalized()
        out.append((t, b, t.cross(b).normalized()))
    return out


def transport(path, b0):
    """Twist-free frames (T, B, N) along path: b0 carried from the first point by parallel transport."""
    T = _tangents(path)
    b = (b0 - T[0] * b0.dot(T[0])).normalized()
    out = [(T[0], b, T[0].cross(b).normalized())]
    for i in range(1, len(path)):
        axis = T[i - 1].cross(T[i])
        if axis.length > 1e-9:
            ang = math.atan2(axis.length, T[i - 1].dot(T[i]))
            k = axis.normalized()  # Rodrigues rotation of b about k by ang
            b = b * math.cos(ang) + k.cross(b) * math.sin(ang) + k * (k.dot(b) * (1 - math.cos(ang)))
        b = (b - T[i] * b.dot(T[i])).normalized()
        out.append((T[i], b, T[i].cross(b).normalized()))
    return out


def tip_scale(u, tp):
    """(section scale, depth scale, calm weight) at length fraction u for a tips setting."""
    f0 = float(tp["from"])
    q = min(1.0, max(0.0, (u - f0) / max(1e-6, 1.0 - f0)))
    s = 1.0 - (1.0 - float(tp["scale"])) * q ** float(tp["power"])
    rd = float(tp.get("round", 0.0))
    if rd > 0.0 and q > 1.0 - rd:  # rounded end: quarter ellipse over the last `round` share of the end
        x = (q - (1.0 - rd)) / rd
        s *= math.sqrt(max(0.0, 1.0 - x * x)) * 0.92 + 0.08
    return s, 1.0 - float(tp["flatten"]) * q, float(tp["calm"]) * q


def clump_values(index, seed=0):
    """Six numbers in 0..1 for clump `index` of a structure: a fixed low-discrepancy sequence, no random draw."""
    k = int(index) + 1 + int(seed)
    return tuple((k * a) % 1.0 for a in _IRR)


def clump_shape(u, cl, vals):
    """(sideways offset in m along the bend direction, bend direction angle, twist in rad, section scale) at
    length fraction u of one clump."""
    r1, r2, r3, r4, r5, r6 = vals
    ph = 2 * math.pi * r3
    bend = float(cl["bend_m"]) * (0.5 + r4) * (math.sin(math.pi * u * (0.6 + 0.8 * r2) + ph) - math.sin(ph)) * u ** 1.5
    twist = math.radians(float(cl["twist_deg"])) * (2 * r5 - 1) * u
    grow = min(1.0, u / 0.12)  # the root keeps its built section (seat on the scalp)
    lump = 1.0 + float(cl["lumps"]) * math.sin(2 * math.pi * (u / float(cl["lump_wavelength"]) + r6)) * grow
    return bend, 2 * math.pi * r1, twist, lump


def reshape_island(rings, poles, stand=None, tips=None, clump=None, index=0):
    """New positions (rings, poles) of one mass or lock: rings = section rings from root to tip, poles = (root
    pole, tip pole); index = its number in the structure (for "clump"). See the module text for the keys."""
    n = len(rings)
    centres = [sum(r, Vector()) / len(r) for r in rings]
    old = _frames(rings, centres)
    path, frames = centres, old
    arc = [0.0]
    for a, b in zip(centres, centres[1:]):
        arc.append(arc[-1] + (b - a).length)
    L = max(arc[-1], 1e-9)
    sc = [(1.0, 1.0, 0.0)] * n
    if tips:
        sc = [tip_scale(a / L, tips) for a in arc]
        if any(c for _, _, c in sc):
            path = relax(path, CALM_PASSES, [c for _, _, c in sc])
    if stand:
        path = relax(path, int(stand["smooth"]))
        frames = transport(path, old[0][1])
    elif path is not centres:
        frames = _frames(rings, path)
    if clump:
        vals = clump_values(index, clump.get("seed", 0))
        path, frames, sc = list(path), list(frames), list(sc)
        for i, a in enumerate(arc):
            bend, th, tw, lump = clump_shape(a / L, clump, vals)
            t1, b1, n1 = frames[i]
            path[i] = path[i] + (b1 * math.cos(th) + n1 * (0.5 * math.sin(th))) * bend
            frames[i] = (t1, b1 * math.cos(tw) + n1 * math.sin(tw), n1 * math.cos(tw) - b1 * math.sin(tw))
            sc[i] = (sc[i][0] * lump, sc[i][1], sc[i][2])
    out = []
    for i, r in enumerate(rings):
        t0, b0, n0 = old[i]
        t1, b1, n1 = frames[i]
        s, d, _ = sc[i]
        ring = []
        for v in r:
            o = v - centres[i]
            ring.append(path[i] + b1 * (o.dot(b0) * s) + n1 * (o.dot(n0) * s * d) + t1 * (o.dot(t0) * s))
        out.append(ring)

    def pole(v, i):
        t0, b0, n0 = old[i]
        t1, b1, n1 = frames[i]
        o = v - centres[i]
        s = sc[i][0]
        return path[i] + b1 * (o.dot(b0) * s) + n1 * (o.dot(n0) * s) + t1 * (o.dot(t0) * s)
    return out, (pole(poles[0], 0), pole(poles[1], n - 1))


def islands(n_verts, edges):
    """Connected vertex sets of a mesh as sorted index lists, in order of their first vertex."""
    parent = list(range(n_verts))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups = {}
    for v in range(n_verts):
        groups.setdefault(find(v), []).append(v)
    return [groups[k] for k in sorted(groups)]


def apply_jobs(jobs, objs):
    """Reshapes the built meshes of the jobs' structures in place; returns the report of what was done."""
    by_name = {o.name: o for o in objs}
    done = {}
    for job in jobs:
        seg = job["seg"]
        count = skipped = index = 0
        for name in job["objects"]:
            ob = by_name.get(name)
            if ob is None:
                skipped += 1
                continue
            me = ob.data
            for isl in islands(len(me.vertices), [tuple(e.vertices) for e in me.edges]):
                m = len(isl)
                # a mass or lock is a contiguous run: rings of `seg` vertices from root to tip, then the two poles
                if m < 2 * seg + 2 or (m - 2) % seg or isl[-1] - isl[0] != m - 1:
                    skipped += 1
                    continue
                co = [me.vertices[i].co.copy() for i in isl]
                rings = [co[k:k + seg] for k in range(0, m - 2, seg)]
                new_rings, new_poles = reshape_island(rings, (co[-2], co[-1]), job.get("stand"), job.get("tips"),
                                                      job.get("clump"), index)
                index += 1
                flat = [v for r in new_rings for v in r] + list(new_poles)
                for i, v in zip(isl, flat):
                    me.vertices[i].co = v
                count += 1
            me.update()
        done[job["structure"]] = dict({k: job[k] for k in R6_KEYS if k in job}, reshaped=count,
                                      **({"skipped": skipped} if skipped else {}))
    return done


# -------------------------------------------------------------------------------------------------------------- build
def build(C, head, frame, hair_spec, material, face_y, fibres=None):
    """As groom_r5.build (same arguments and return value), for groom/5 specs."""
    errs = validate(hair_spec)
    if errs:
        raise SystemExit("groom/5: " + "; ".join(errs))
    contact = hair_spec if CT.has_keys(hair_spec) else None  # T-183 opt-in keys (groom_contact.py)
    low, jobs = lower(CT.strip(hair_spec))
    keepout = contact is not None and "ear_keepout" in contact
    if not jobs and not keepout:
        objs, rep = R5.build(C, head, frame, low, material, face_y, fibres)
        rep["generator"] = GENERATOR
        if contact is not None:
            rep["contact"] = CT.store(contact, objs)
        return objs, rep
    later = R5._Deferred() if fibres is not None else None  # fibres grow on the final (reshaped) geometry
    objs, rep = R5.build(C, head, frame, low, material, face_y, later)
    if jobs:
        rep["reshaped"] = apply_jobs(jobs, objs)
    if keepout:
        rep["ear_keepout"] = CT.apply_ear_keepout(contact, objs)
    if later and later.calls:
        R5._grow_fibres(low, later.calls, fibres, rep)
    rep["generator"] = GENERATOR
    if contact is not None and CT.contact_spec(contact) is not None:
        rep["contact"] = CT.store(contact, objs)
    return objs, rep


def bind(rig, objs, head_bone, chest_bone, binding):
    """As groom.bind; then the T-183 contact colliders when the build stored a contact spec (no-op otherwise)."""
    G1.bind(rig, objs, head_bone, chest_bone, binding)
    CT.bind_contact(rig, objs, head_bone, chest_bone, binding)
